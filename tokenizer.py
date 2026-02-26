from __future__ import annotations

from typing import Any


def _estimate_tokens(text: str) -> int:
    # Approximation: ~4 characters per token.
    return max(0, (len(text) + 3) // 4)


def _message_text(message: dict[str, Any]) -> str:
    content = message.get("content")

    if isinstance(content, str):
        return content

    if content is None:
        tool_calls = message.get("tool_calls") or []
        if isinstance(tool_calls, list) and tool_calls:
            parts: list[str] = []
            for tc in tool_calls:
                fn = (tc or {}).get("function") or {}
                parts.append(
                    f"Function call: {fn.get('name', '')}({fn.get('arguments', '')})"
                )
            return " ".join(parts)
        if message.get("role") == "tool" and message.get("name"):
            return f"Tool response from {message['name']}"
        return ""

    if isinstance(content, list):
        text_parts: list[str] = []
        for part in content:
            if not isinstance(part, dict):
                continue
            ptype = part.get("type")
            if ptype in {"text", "input_text"} and isinstance(part.get("text"), str):
                text_parts.append(part["text"])
        return " ".join(text_parts)

    return ""


def get_token_count(messages: list[dict[str, Any]]) -> dict[str, int]:
    input_tokens = 0
    output_tokens = 0

    for message in messages:
        role = message.get("role")
        text = _message_text(message)
        tokens = _estimate_tokens(text)

        if role == "assistant":
            output_tokens += tokens
        else:
            input_tokens += tokens

    return {
        "input": input_tokens,
        "output": output_tokens,
    }
