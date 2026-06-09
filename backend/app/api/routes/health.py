from fastapi import APIRouter

router = APIRouter(tags=["Saude"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
