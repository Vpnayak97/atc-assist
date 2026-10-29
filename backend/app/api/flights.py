from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api")


@router.get("/flights")
def flights(request: Request):
    tr = request.app.state.tracker
    return [t.model_dump(mode="json", exclude={"predictions"}) for t in tr.tracks.values()]


@router.get("/flights/{hex}")
def flight(hex: str, request: Request):
    t = request.app.state.tracker.get(hex)
    if t is None:
        raise HTTPException(404, "unknown flight")
    return t.model_dump(mode="json")