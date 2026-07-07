from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.models import WrappedResult
from app.card_generator import generate_card

router = APIRouter()


@router.post("/api/card")
async def card(result: WrappedResult):
    """Takes the WrappedResult the frontend already has (from whichever path
    it called) and renders it into a downloadable PNG. Stateless on purpose -
    the frontend is the source of truth for what to draw, so this endpoint
    doesn't need session/auth at all."""
    buffer = generate_card(result)
    return StreamingResponse(
        buffer,
        media_type="image/png",
        headers={"Content-Disposition": "attachment; filename=youtube-wrapped.png"},
    )
