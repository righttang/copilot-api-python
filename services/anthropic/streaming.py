from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator
from uuid import uuid4

logger = logging.getLogger(__name__)


def _estimate_token_count(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


async def convert_openai_stream_to_anthropic(
    openai_stream: AsyncGenerator[dict[str, Any] | str, None],
    original_anthropic_model: str,
    estimated_input_tokens: int,
    request_id: str,
) -> AsyncGenerator[str, None]:
    anthropic_message_id = f"msg_stream_{request_id}_{str(uuid4())[:8]}"

    next_anthropic_block_idx = 0
    text_block_anthropic_idx: int | None = None
    openai_tool_idx_to_anthropic_block_idx: dict[int, int] = {}
    tool_states: dict[int, dict[str, Any]] = {}
    sent_tool_block_starts: set[int] = set()

    output_token_count = 0
    final_anthropic_stop_reason = "end_turn"

    stop_reason_map = {
        "stop": "end_turn",
        "length": "max_tokens",
        "tool_calls": "tool_use",
        "function_call": "tool_use",
        "content_filter": "stop_sequence",
    }

    try:
        message_start_event = {
            "type": "message_start",
            "message": {
                "id": anthropic_message_id,
                "type": "message",
                "role": "assistant",
                "model": original_anthropic_model,
                "content": [],
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {
                    "input_tokens": estimated_input_tokens,
                    "output_tokens": 0,
                },
            },
        }
        yield f"event: message_start\ndata: {json.dumps(message_start_event)}\n\n"

        ping_event = {"type": "ping"}
        yield f"event: ping\ndata: {json.dumps(ping_event)}\n\n"

        async for parsed_chunk in openai_stream:
            if isinstance(parsed_chunk, str):
                if parsed_chunk == "[DONE]":
                    break
                continue

            choices = parsed_chunk.get("choices") or []
            if not choices:
                continue

            delta = choices[0].get("delta") or {}
            openai_finish_reason = choices[0].get("finish_reason")

            if delta.get("content"):
                content = str(delta["content"])
                output_token_count += _estimate_token_count(content)

                if text_block_anthropic_idx is None:
                    text_block_anthropic_idx = next_anthropic_block_idx
                    next_anthropic_block_idx += 1

                    start_text_event = {
                        "type": "content_block_start",
                        "index": text_block_anthropic_idx,
                        "content_block": {"type": "text", "text": ""},
                    }
                    yield (
                        "event: content_block_start\n"
                        f"data: {json.dumps(start_text_event)}\n\n"
                    )

                text_delta_event = {
                    "type": "content_block_delta",
                    "index": text_block_anthropic_idx,
                    "delta": {
                        "type": "text_delta",
                        "text": content,
                    },
                }
                yield f"event: content_block_delta\ndata: {json.dumps(text_delta_event)}\n\n"

            for tool_delta in delta.get("tool_calls") or []:
                openai_tc_idx = int(tool_delta.get("index", 0))

                if openai_tc_idx not in openai_tool_idx_to_anthropic_block_idx:
                    current_idx = next_anthropic_block_idx
                    next_anthropic_block_idx += 1
                    openai_tool_idx_to_anthropic_block_idx[openai_tc_idx] = current_idx
                    tool_states[current_idx] = {
                        "id": f"tool_ph_{request_id}_{current_idx}",
                        "name": "",
                        "arguments_buffer": "",
                    }

                current_idx = openai_tool_idx_to_anthropic_block_idx[openai_tc_idx]
                tool_state = tool_states[current_idx]

                if tool_delta.get("id") and tool_state["id"].startswith("tool_ph_"):
                    tool_state["id"] = tool_delta["id"]

                fn = tool_delta.get("function") or {}
                if fn.get("name"):
                    tool_state["name"] = fn["name"]
                if fn.get("arguments"):
                    args_part = str(fn["arguments"])
                    tool_state["arguments_buffer"] += args_part
                    output_token_count += _estimate_token_count(args_part)

                if (
                    current_idx not in sent_tool_block_starts
                    and tool_state["id"]
                    and not tool_state["id"].startswith("tool_ph_")
                    and tool_state["name"]
                ):
                    start_tool_event = {
                        "type": "content_block_start",
                        "index": current_idx,
                        "content_block": {
                            "type": "tool_use",
                            "id": tool_state["id"],
                            "name": tool_state["name"],
                            "input": {},
                        },
                    }
                    yield (
                        "event: content_block_start\n"
                        f"data: {json.dumps(start_tool_event)}\n\n"
                    )
                    sent_tool_block_starts.add(current_idx)

                if fn.get("arguments") and current_idx in sent_tool_block_starts:
                    args_delta_event = {
                        "type": "content_block_delta",
                        "index": current_idx,
                        "delta": {
                            "type": "input_json_delta",
                            "partial_json": fn["arguments"],
                        },
                    }
                    yield (
                        "event: content_block_delta\n"
                        f"data: {json.dumps(args_delta_event)}\n\n"
                    )

            if openai_finish_reason:
                final_anthropic_stop_reason = stop_reason_map.get(
                    openai_finish_reason, "end_turn"
                )
                if openai_finish_reason == "tool_calls":
                    final_anthropic_stop_reason = "tool_use"
                break

        if text_block_anthropic_idx is not None:
            stop_event = {
                "type": "content_block_stop",
                "index": text_block_anthropic_idx,
            }
            yield f"event: content_block_stop\ndata: {json.dumps(stop_event)}\n\n"

        for anthropic_tool_idx in sent_tool_block_starts:
            stop_event = {
                "type": "content_block_stop",
                "index": anthropic_tool_idx,
            }
            yield f"event: content_block_stop\ndata: {json.dumps(stop_event)}\n\n"

        message_delta_event = {
            "type": "message_delta",
            "delta": {
                "stop_reason": final_anthropic_stop_reason,
                "stop_sequence": None,
            },
            "usage": {
                "output_tokens": output_token_count,
            },
        }
        yield f"event: message_delta\ndata: {json.dumps(message_delta_event)}\n\n"

        message_stop_event = {"type": "message_stop"}
        yield f"event: message_stop\ndata: {json.dumps(message_stop_event)}\n\n"

    except Exception as error:
        logger.exception("Error in stream conversion", exc_info=error)
        error_event = {
            "type": "error",
            "error": {
                "type": "api_error",
                "message": str(error),
            },
        }
        yield f"event: error\ndata: {json.dumps(error_event)}\n\n"
