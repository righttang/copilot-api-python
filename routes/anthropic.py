from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from approval import await_approval
from forward_error import anthropic_error_response
from is_nullish import is_nullish
from rate_limit import check_rate_limit
from state import state
from tokenizer import get_token_count
from services.anthropic.converters import (
    convert_anthropic_to_openai_messages,
    convert_anthropic_tool_choice_to_openai,
    convert_anthropic_tools_to_openai,
    convert_openai_to_anthropic_response,
)
from services.anthropic.streaming import convert_openai_stream_to_anthropic
from services.copilot.create_chat_completions import create_chat_completions

logger = logging.getLogger(__name__)

router = APIRouter()


def select_copilot_model(anthropic_model: str) -> str:
    model_name = anthropic_model.lower()

    if not state.models or not isinstance(state.models.get("data"), list):
        return "claude-3-5-sonnet-20241022"

    models = [m for m in state.models["data"] if isinstance(m, dict)]

    exact_match = next(
        (m for m in models if str(m.get("id", "")).lower() == model_name),
        None,
    )
    if exact_match:
        logger.debug("Found exact model match: %s", exact_match.get("id"))
        return str(exact_match.get("id"))

    preferred_model = next(
        (m for m in models if str(m.get("id", "")).lower() == "claude-3.7-sonnet"),
        None,
    )
    if preferred_model:
        logger.debug("Using preferred model: %s", preferred_model.get("id"))
        return str(preferred_model.get("id"))

    claude_model = next(
        (m for m in models if "claude" in str(m.get("id", "")).lower()),
        None,
    )
    if claude_model:
        logger.debug("Using claude model: %s", claude_model.get("id"))
        return str(claude_model.get("id"))

    fallback_model = str(models[0].get("id", "claude-3-5-sonnet-20241022"))
    logger.debug("Using fallback model: %s", fallback_model)
    return fallback_model


@router.post("")
async def anthropic_messages(request: Request):
    await check_rate_limit(state)

    request_id = str(uuid4())

    try:
        anthropic_request = await request.json()

        logger.info(
            "Received Anthropic messages request, requestModel: %s",
            anthropic_request.get("model"),
        )

        if anthropic_request.get("messages"):
            token_count = get_token_count(
                convert_anthropic_to_openai_messages(
                    anthropic_request.get("messages", []),
                    anthropic_request.get("system"),
                )
            )
            logger.info("Estimated token count: %s", token_count)

        if state.manual_approve:
            await await_approval()

        openai_messages = convert_anthropic_to_openai_messages(
            anthropic_request.get("messages", []),
            anthropic_request.get("system"),
        )
        openai_tools = convert_anthropic_tools_to_openai(anthropic_request.get("tools"))
        openai_tool_choice = convert_anthropic_tool_choice_to_openai(
            anthropic_request.get("tool_choice")
        )

        openai_payload: dict[str, object] = {
            "model": select_copilot_model(str(anthropic_request.get("model", ""))),
            "messages": openai_messages,
            "stream": bool(anthropic_request.get("stream", False)),
        }

        if is_nullish(anthropic_request.get("max_tokens")):
            selected_model = None
            if state.models and isinstance(state.models.get("data"), list):
                selected_model = next(
                    (
                        model
                        for model in state.models["data"]
                        if isinstance(model, dict)
                        and model.get("id") == openai_payload["model"]
                    ),
                    None,
                )
            openai_payload["max_tokens"] = (
                (selected_model or {})
                .get("capabilities", {})
                .get("limits", {})
                .get("max_output_tokens")
            )
        else:
            openai_payload["max_tokens"] = anthropic_request.get("max_tokens")

        if anthropic_request.get("temperature") is not None:
            openai_payload["temperature"] = anthropic_request.get("temperature")
        if anthropic_request.get("top_p") is not None:
            openai_payload["top_p"] = anthropic_request.get("top_p")
        if anthropic_request.get("stop_sequences"):
            openai_payload["stop"] = anthropic_request.get("stop_sequences")
        if openai_tools:
            openai_payload["tools"] = openai_tools
        if openai_tool_choice:
            openai_payload["tool_choice"] = openai_tool_choice

        logger.debug(
            "Converted to OpenAI payload model=%s messageCount=%s hasTools=%s requestId=%s",
            openai_payload["model"],
            len(openai_payload["messages"]),
            bool(openai_payload.get("tools")),
            request_id,
        )

        response = await create_chat_completions(openai_payload)

        if anthropic_request.get("stream") and not isinstance(response, dict):
            estimated_input_tokens = get_token_count(openai_messages)["input"]
            sse_stream = convert_openai_stream_to_anthropic(
                response,
                str(anthropic_request.get("model", "")),
                estimated_input_tokens,
                request_id,
            )
            return StreamingResponse(sse_stream, media_type="text/event-stream")

        if isinstance(response, dict):
            anthropic_response = convert_openai_to_anthropic_response(
                response,
                str(anthropic_request.get("model", "")),
                request_id,
            )
            logger.info(
                "Anthropic messages request completed model=%s stopReason=%s inputTokens=%s outputTokens=%s requestId=%s",
                anthropic_response.get("model"),
                anthropic_response.get("stop_reason"),
                anthropic_response.get("usage", {}).get("input_tokens"),
                anthropic_response.get("usage", {}).get("output_tokens"),
                request_id,
            )
            return JSONResponse(content=anthropic_response)

        raise RuntimeError("Unexpected response type from OpenAI")

    except Exception as error:
        return anthropic_error_response(error)


@router.post("/count_tokens")
async def anthropic_token_count(request: Request):
    try:
        payload = await request.json()

        logger.info(
            "Received Anthropic token count request model=%s messageCount=%s",
            payload.get("model"),
            len(payload.get("messages", [])),
        )

        openai_messages = convert_anthropic_to_openai_messages(
            payload.get("messages", []),
            payload.get("system"),
        )
        token_count = get_token_count(openai_messages)

        response = {
            "input_tokens": token_count["input"],
        }

        logger.info(
            "Token count completed tokens=%s model=%s",
            response["input_tokens"],
            payload.get("model"),
        )

        return JSONResponse(content=response)

    except Exception as error:
        logger.exception("Error counting tokens", exc_info=error)
        return JSONResponse(
            status_code=400,
            content={
                "type": "error",
                "error": {
                    "type": "invalid_request_error",
                    "message": str(error),
                },
            },
        )
