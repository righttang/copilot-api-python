from __future__ import annotations

from typing import Any

import httpx

from api_config import GITHUB_API_BASE_URL, standard_headers
from errors import HTTPError
from state import state


async def get_github_user() -> dict[str, Any]:
    headers = {
        "authorization": f"token {state.github_token}",
        **standard_headers(),
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(f"{GITHUB_API_BASE_URL}/user", headers=headers)

    if not response.is_success:
        raise HTTPError(
            message="Failed to get GitHub user",
            status_code=response.status_code,
            response_text=response.text,
        )

    return response.json()
