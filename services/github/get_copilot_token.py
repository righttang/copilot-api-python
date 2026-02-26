from __future__ import annotations

from typing import Any

import httpx

from api_config import GITHUB_API_BASE_URL, github_headers
from errors import HTTPError
from state import state


async def get_copilot_token() -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{GITHUB_API_BASE_URL}/copilot_internal/v2/token",
            headers=github_headers(state),
        )

    if not response.is_success:
        raise HTTPError(
            message="Failed to get Copilot token",
            status_code=response.status_code,
            response_text=response.text,
        )

    return response.json()
