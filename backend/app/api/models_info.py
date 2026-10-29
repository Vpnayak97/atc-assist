from fastapi import APIRouter, Request

router = APIRouter(prefix="/api")


@router.get("/models")
def models(request: Request):
    reg = request.app.state.registry
    return {**reg.status(), "cards": reg.cards}