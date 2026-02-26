from __future__ import annotations

from typing import Any

import httpx

from api_config import copilot_base_url, copilot_headers
from errors import HTTPError
from state import state


async def get_models() -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{copilot_base_url(state)}/models",
            headers=copilot_headers(state),
        )

    if not response.is_success:
        raise HTTPError(
            message="Failed to get models",
            status_code=response.status_code,
            response_text=response.text,
        )

    return response.json()
