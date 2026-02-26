from __future__ import annotations

from typing import Any

import httpx

from api_config import copilot_base_url, copilot_headers
from errors import HTTPError
from state import state


async def create_embeddings(payload: dict[str, Any]) -> dict[str, Any]:
    if not state.copilot_token:
        raise RuntimeError("Copilot token not found")

    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(
            f"{copilot_base_url(state)}/embeddings",
            headers=copilot_headers(state),
            json=payload,
        )

    if not response.is_success:
        raise HTTPError(
            message="Failed to create embeddings",
            status_code=response.status_code,
            response_text=response.text,
        )

    return response.json()
