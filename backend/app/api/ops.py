import time

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api")


class EmgBody(BaseModel):
    declare: bool = True
    text: str = "declared by controller"


class PriBody(BaseModel):
    priority: int


@router.get("/ops")
def ops(request: Request):
    return request.app.state.ops.last


@router.post("/alerts/{alert_id}/ack")
def ack(alert_id: str, request: Request):
    o = request.app.state.ops
    if not o.alerts.ack(alert_id):
        raise HTTPException(404, "unknown alert")
    o.audit.log("alert_ack", {"id": alert_id})
    return {"ok": True}


@router.post("/advisories/{adv_id}/approve")
def approve(adv_id: str, request: Request):
    rec = request.app.state.ops.conf.approve(adv_id, time.time())
    if rec is None:
        raise HTTPException(404, "advisory not available")
    return rec


@router.post("/advisories/{adv_id}/reject")
def reject(adv_id: str, request: Request):
    if not request.app.state.ops.conf.reject(adv_id, time.time()):
        raise HTTPException(404, "advisory not available")
    return {"ok": True}


@router.post("/flights/{hex}/emergency")
def emergency(hex: str, body: EmgBody, request: Request):
    o, hx = request.app.state.ops, hex.lower()
    if request.app.state.tracker.get(hx) is None:
        raise HTTPException(404, "unknown flight")
    if body.declare:
        o.emg.manual_emg[hx] = body.text
    else:
        o.emg.manual_emg.pop(hx, None)
    o.audit.log("emergency_declared" if body.declare else "emergency_cleared", {"hex": hx, "text": body.text})
    return {"ok": True}


@router.post("/flights/{hex}/priority")
def priority(hex: str, body: PriBody, request: Request):
    from app.schemas.aircraft import Priority
    o, hx = request.app.state.ops, hex.lower()
    if request.app.state.tracker.get(hx) is None or not 0 <= body.priority <= 4:
        raise HTTPException(404, "unknown flight or priority")
    o.emg.manual_pri[hx] = Priority(body.priority)
    o.audit.log("priority_set", {"hex": hx, "priority": body.priority})
    return {"ok": True}


@router.get("/weather")
def weather(request: Request):
    return request.app.state.weather.payload(request.app.state.ops.last["finals"])

class ClosureBody(BaseModel):
    id: str
    closed: bool = True


@router.post("/runways/closure")
def closure(body: ClosureBody, request: Request):
    if not request.app.state.ops.rwy.set_closed(body.id, body.closed, time.time()):
        raise HTTPException(404, "unknown runway")
    return {"ok": True}


@router.get("/sequence")
def sequence(request: Request):
    return request.app.state.ops.last["sequence"]


@router.get("/runways")
def runways(request: Request):
    return request.app.state.ops.last["runways"]