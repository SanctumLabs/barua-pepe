from fastapi import APIRouter
from app.api.dto import ApiResponse

router = APIRouter()


@router.get("/healthz", tags=["monitoring"])
def healthz():
    return ApiResponse(message="Healthy!")
