from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from forward_error import forward_error
from services.copilot.create_embeddings import create_embeddings

router = APIRouter()


@router.post("")
async def embeddings_route(request: Request):
    try:
        payload = await request.json()
        response = await create_embeddings(payload)
        return JSONResponse(content=response)
    except Exception as error:
        return forward_error(error)
