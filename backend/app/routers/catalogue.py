from fastapi import APIRouter

from ..services import catalogue

router = APIRouter(tags=["catalogue"])


@router.get("/catalogue")
def get_catalogue():
    """Crops the farmer can choose from (with whether the AI covers them) and the diseases experts can pick from."""
    return {"crops": [{k: c[k] for k in ("id", "name", "ai_supported", "diseases")} for c in catalogue.crops()]}
