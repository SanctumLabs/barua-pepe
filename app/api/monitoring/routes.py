"""
Monitoring routs
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response
from starlette.status import HTTP_200_OK

from app.metrics import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter()


@router.get("/healthz", tags=["monitoring"])
def healthz():
    """
    Router to check health of application
    """
    return JSONResponse(status_code=HTTP_200_OK, content={"message": "Healthy!"})


@router.get("/metrics", tags=["monitoring"])
def metrics():
    """Expose application and Celery metrics in Prometheus format."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
