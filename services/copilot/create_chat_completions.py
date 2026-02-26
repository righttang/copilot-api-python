from __future__ import annotations

import json
from typing import Any, AsyncGenerator

import httpx

from api_config import copilot_base_url, copilot_headers
from errors import HTTPError
from state import state


def _into_copilot_message(message: dict[str, Any]) -> None:
    role = message.get("role")

    if role in {"assistant", "tool"}:
        return

    content = message.get("content")
    if isinstance(content, str) or content is None:
        return

    if not isinstance(content, list):
        return

    for part in content:
        if isinstance(part, dict) and part.get("type") == "input_image":
            part["type"] = "image_url"


def _has_vision(messages: list[dict[str, Any]]) -> bool:
    for message in messages:
        content = message.get("content")
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    return True
    return False


async def _stream_openai_sse(
    payload: dict[str, Any],
    vision_enabled: bool,
    tools_enabled: bool,
) -> AsyncGenerator[dict[str, Any] | str, None]:
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "POST",
            f"{copilot_base_url(state)}/chat/completions",
            headers=copilot_headers(state, vision=vision_enabled),
            json=payload,
        ) as response:
            if not response.is_success:
                error_text = await response.aread()
                decoded_error = error_text.decode("utf-8", errors="replace")
                if tools_enabled and response.status_code == 400:
                    raise HTTPError(
                        message=(
                            "Failed to create chat completions. GitHub Copilot may not "
                            f"support tool calls. Error: {decoded_error}"
                        ),
                        status_code=response.status_code,
                        response_text=decoded_error,
                    )
                raise HTTPError(
                    message="Failed to create chat completions",
                    status_code=response.status_code,
                    response_text=decoded_error,
                )

            async for line in response.aiter_lines():
                if not line:
                    continue
                if not line.startswith("data:"):
                    continue

                data = line[5:].strip()
                if data == "[DONE]":
                    yield "[DONE]"
                    return

                try:
                    yield json.loads(data)
                except json.JSONDecodeError:
                    continue


async def create_chat_completions(
    payload: dict[str, Any],
) -> dict[str, Any] | AsyncGenerator[dict[str, Any] | str, None]:
    if not state.copilot_token:
        raise RuntimeError("Copilot token not found")

    messages = payload.get("messages") or []
    if isinstance(messages, list):
        for message in messages:
            if isinstance(message, dict):
                _into_copilot_message(message)

    vision_enabled = _has_vision(messages)
    tools_enabled = bool(payload.get("tools"))

    if payload.get("stream"):
        return _stream_openai_sse(payload, vision_enabled, tools_enabled)

    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.post(
            f"{copilot_base_url(state)}/chat/completions",
            headers=copilot_headers(state, vision=vision_enabled),
            json=payload,
        )

    if not response.is_success:
        error_text = response.text
        if tools_enabled and response.status_code == 400:
            raise HTTPError(
                message=(
                    "Failed to create chat completions. GitHub Copilot may not "
                    f"support tool calls. Error: {error_text}"
                ),
                status_code=response.status_code,
                response_text=error_text,
            )
        raise HTTPError(
            message="Failed to create chat completions",
            status_code=response.status_code,
            response_text=error_text,
        )

    return response.json()
