from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from routes.anthropic import router as anthropic_router
from routes.chat_completions import router as completion_router
from routes.embeddings import router as embeddings_router
from routes.models import router as models_router

logger = logging.getLogger(__name__)

server = FastAPI()

server.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@server.middleware("http")
async def request_logger(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = int((time.time() - start) * 1000)
    logger.info(
        "%s %s -> %s (%sms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@server.get("/")
async def health() -> PlainTextResponse:
    return PlainTextResponse("Server running")


# OpenAI-compatible endpoints
server.include_router(completion_router, prefix="/chat/completions")
server.include_router(models_router, prefix="/models")
server.include_router(embeddings_router, prefix="/embeddings")

# Compatibility with tools that expect v1/ prefix
server.include_router(completion_router, prefix="/v1/chat/completions")
server.include_router(models_router, prefix="/v1/models")
server.include_router(embeddings_router, prefix="/v1/embeddings")

# Anthropic-compatible endpoints
server.include_router(anthropic_router, prefix="/v1/messages")
