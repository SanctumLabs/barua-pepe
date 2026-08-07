"""
Monitoring routs
"""
from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse
from starlette.status import HTTP_200_OK

from app.metrics import generate_latest, CONTENT_TYPE_LATEST

router = APIRouter()


@router.get("/healthz", tags=["monitoring"])
def healthz():
    """
    Router to check health of application
    """
    return JSONResponse(status_code=HTTP_200_OK, content={"message": "Healthy!"})


@router.get("/metrics", tags=["monitoring"])
def metrics():
    """Prometheus metrics endpoint"""
    if not generate_latest:
        return JSONResponse(status_code=HTTP_200_OK, content={"message": "Metrics not available"})
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
