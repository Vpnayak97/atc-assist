
from __future__ import annotations

import asyncio
import json
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.health import health_payload

log = logging.getLogger("atc.ws")
router = APIRouter()


class Hub:
    def __init__(self):
        self.clients: set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.clients.add(ws)

    def disconnect(self, ws: WebSocket):
        self.clients.discard(ws)

    async def broadcast(self, msg: dict):
        if not self.clients:
            return
        text = json.dumps(msg, separators=(",", ":"))
        dead = []
        for ws in list(self.clients):
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


def snapshot(app, now: float) -> dict:
    live = app.state.live
    return {"type": "snapshot", "t": now, "airport": live.airport_payload(), "tracks": live.tick(now),
            "ops": app.state.ops.last, "health": health_payload(app)}


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    app = ws.app
    hub: Hub = app.state.hub
    await hub.connect(ws)
    try:
        await ws.send_text(json.dumps(snapshot(app, time.time()), separators=(",", ":")))
        while True:
            await ws.receive_text()      # subscribe/ack messages arrive in later phases
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(ws)


async def push_loop(app, stop: asyncio.Event) -> None:
    n, last_sig = 0, ""
    while not stop.is_set():
        t0 = time.monotonic()
        try:
            now = time.time()
            tracks = app.state.live.tick(now)
            ops = app.state.ops.update(tracks, now)
            await app.state.hub.broadcast({"type": "tracks", "t": now, "tracks": tracks})
            sig = json.dumps(ops, sort_keys=True, separators=(",", ":"))
            if sig != last_sig or n % 5 == 0:
                await app.state.hub.broadcast({"type": "ops", "ops": ops})
                last_sig = sig
            n += 1
            if n % 5 == 0:
                await app.state.hub.broadcast({"type": "health", "health": health_payload(app)})
        except Exception:
            log.exception("push cycle failed")
        await asyncio.sleep(max(0.0, 1.0 - (time.monotonic() - t0)))
