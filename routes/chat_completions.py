from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from approval import await_approval
from forward_error import forward_error
from is_nullish import is_nullish
from rate_limit import check_rate_limit
from state import state
from tokenizer import get_token_count
from services.copilot.create_chat_completions import create_chat_completions

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("")
async def completion_route(request: Request):
    try:
        await check_rate_limit(state)
        payload = await request.json()

        if isinstance(payload.get("messages"), list):
            logger.info("Current token count: %s", get_token_count(payload["messages"]))

        if state.manual_approve:
            await await_approval()

        if is_nullish(payload.get("max_tokens")):
            selected_model = None
            if state.models and isinstance(state.models.get("data"), list):
                selected_model = next(
                    (
                        model
                        for model in state.models["data"]
                        if isinstance(model, dict)
                        and model.get("id") == payload.get("model")
                    ),
                    None,
                )

            max_output = (
                (selected_model or {})
                .get("capabilities", {})
                .get("limits", {})
                .get("max_output_tokens")
            )
            payload["max_tokens"] = max_output

        response = await create_chat_completions(payload)

        if isinstance(response, dict):
            return JSONResponse(content=response)

        async def sse_stream():
            async for chunk in response:
                if isinstance(chunk, str) and chunk == "[DONE]":
                    yield "data: [DONE]\n\n"
                    return
                if isinstance(chunk, dict):
                    yield f"data: {json.dumps(chunk)}\n\n"

        return StreamingResponse(sse_stream(), media_type="text/event-stream")

    except Exception as error:
        return forward_error(error)
