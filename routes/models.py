from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from forward_error import forward_error
from services.copilot.get_models import get_models

router = APIRouter()


@router.get("")
async def models_route():
    try:
        models = await get_models()
        return JSONResponse(content=models)
    except Exception as error:
        return forward_error(error)
