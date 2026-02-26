from __future__ import annotations

import json
import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


def convert_anthropic_to_openai_messages(
    anthropic_messages: list[dict[str, Any]],
    anthropic_system: str | list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    openai_messages: list[dict[str, Any]] = []

    system_text_content = ""
    if isinstance(anthropic_system, str):
        system_text_content = anthropic_system
    elif isinstance(anthropic_system, list):
        system_text_content = "\n".join(
            block.get("text", "")
            for block in anthropic_system
            if isinstance(block, dict) and block.get("type") == "text"
        )

    if system_text_content:
        openai_messages.append({"role": "system", "content": system_text_content})

    for msg in anthropic_messages:
        role = msg.get("role")
        content = msg.get("content")

        if isinstance(content, str):
            openai_messages.append({"role": role, "content": content})
            continue

        if not isinstance(content, list):
            continue

        openai_parts_for_user_message: list[dict[str, Any]] = []
        assistant_tool_calls: list[dict[str, Any]] = []
        text_content_for_assistant: list[str] = []

        if not content:
            openai_messages.append({"role": role, "content": ""})
            continue

        for block in content:
            if not isinstance(block, dict):
                continue

            btype = block.get("type")

            if btype == "text":
                if role == "user":
                    openai_parts_for_user_message.append(
                        {"type": "text", "text": block.get("text", "")}
                    )
                elif role == "assistant":
                    text_content_for_assistant.append(str(block.get("text", "")))

            elif btype == "image" and role == "user":
                source = block.get("source") or {}
                if source.get("type") == "base64":
                    openai_parts_for_user_message.append(
                        {
                            "type": "image_url",
                            "image_url": (
                                f"data:{source.get('media_type')};base64,{source.get('data')}"
                            ),
                        }
                    )

            elif btype == "tool_use" and role == "assistant":
                try:
                    args_str = json.dumps(block.get("input", {}))
                except Exception:
                    logger.warning("Failed to serialize tool input for %s", block.get("name"))
                    args_str = "{}"

                assistant_tool_calls.append(
                    {
                        "id": block.get("id"),
                        "type": "function",
                        "function": {
                            "name": block.get("name"),
                            "arguments": args_str,
                        },
                    }
                )

            elif btype == "tool_result" and role == "user":
                serialized_content = serialize_tool_result_content(block.get("content"))
                openai_messages.append(
                    {
                        "role": "tool",
                        "content": serialized_content,
                        "tool_call_id": block.get("tool_use_id"),
                    }
                )

        if role == "user" and openai_parts_for_user_message:
            is_multimodal = any(
                part.get("type") == "image_url" for part in openai_parts_for_user_message
            )
            if is_multimodal or len(openai_parts_for_user_message) > 1:
                openai_messages.append(
                    {"role": "user", "content": openai_parts_for_user_message}
                )
            elif len(openai_parts_for_user_message) == 1:
                one = openai_parts_for_user_message[0]
                if one.get("type") == "text":
                    openai_messages.append(
                        {"role": "user", "content": one.get("text", "")}
                    )

        if role == "assistant":
            assistant_text = "\n".join(t for t in text_content_for_assistant if t)
            if assistant_text and assistant_tool_calls:
                openai_messages.append({"role": "assistant", "content": assistant_text})
                openai_messages.append(
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": assistant_tool_calls,
                    }
                )
            elif assistant_text:
                openai_messages.append({"role": "assistant", "content": assistant_text})
            elif assistant_tool_calls:
                openai_messages.append(
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": assistant_tool_calls,
                    }
                )
            else:
                openai_messages.append({"role": "assistant", "content": ""})

    return openai_messages


def convert_anthropic_tools_to_openai(
    anthropic_tools: list[dict[str, Any]] | None,
) -> list[dict[str, Any]] | None:
    if not anthropic_tools:
        return None

    converted = []
    for tool in anthropic_tools:
        converted.append(
            {
                "type": "function",
                "function": {
                    "name": tool.get("name"),
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema"),
                },
            }
        )
    return converted


def convert_anthropic_tool_choice_to_openai(
    anthropic_choice: dict[str, Any] | None,
) -> str | dict[str, Any] | None:
    if not anthropic_choice:
        return None

    ctype = anthropic_choice.get("type")
    if ctype in {"auto", "any"}:
        return "auto"
    if ctype == "tool" and anthropic_choice.get("name"):
        return {
            "type": "function",
            "function": {
                "name": anthropic_choice.get("name"),
            },
        }
    return "auto"


def convert_openai_to_anthropic_response(
    openai_response: dict[str, Any],
    original_anthropic_model: str,
    request_id: str | None = None,
) -> dict[str, Any]:
    anthropic_content: list[dict[str, Any]] = []
    anthropic_stop_reason = "end_turn"

    stop_reason_map = {
        "stop": "end_turn",
        "length": "max_tokens",
        "tool_calls": "tool_use",
        "function_call": "tool_use",
        "content_filter": "stop_sequence",
    }

    choices = openai_response.get("choices") or []
    if choices:
        choice = choices[0]
        message = choice.get("message") or {}
        finish_reason = choice.get("finish_reason")

        anthropic_stop_reason = stop_reason_map.get(finish_reason, "end_turn")

        if message.get("content"):
            anthropic_content.append(
                {
                    "type": "text",
                    "text": message.get("content"),
                }
            )

        for call in message.get("tool_calls") or []:
            if call.get("type") != "function":
                continue

            args = call.get("function", {}).get("arguments", "{}")
            try:
                parsed_input = json.loads(args)
                if not isinstance(parsed_input, dict):
                    parsed_input = {"value": parsed_input}
            except Exception:
                logger.warning("Failed to parse tool arguments for %s", call)
                parsed_input = {"error_parsing_arguments": args}

            anthropic_content.append(
                {
                    "type": "tool_use",
                    "id": call.get("id"),
                    "name": call.get("function", {}).get("name"),
                    "input": parsed_input,
                }
            )

        if finish_reason == "tool_calls":
            anthropic_stop_reason = "tool_use"

    if not anthropic_content:
        anthropic_content.append({"type": "text", "text": ""})

    response_id = (
        f"msg_{openai_response.get('id')}"
        if openai_response.get("id")
        else f"msg_{request_id or uuid4()}_completed"
    )

    return {
        "id": response_id,
        "type": "message",
        "role": "assistant",
        "model": original_anthropic_model,
        "content": anthropic_content,
        "stop_reason": anthropic_stop_reason,
        "usage": {
            "input_tokens": 0,
            "output_tokens": 0,
        },
    }


def serialize_tool_result_content(content: Any) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        processed_parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text" and "text" in item:
                processed_parts.append(str(item["text"]))
            else:
                try:
                    processed_parts.append(json.dumps(item))
                except Exception:
                    processed_parts.append(f"<unserializable_item type='{type(item).__name__}'>")
        return "\n".join(processed_parts)

    try:
        return json.dumps(content)
    except Exception:
        return json.dumps(
            {
                "error": "Serialization failed",
                "original_type": type(content).__name__,
            }
        )
