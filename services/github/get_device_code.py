from __future__ import annotations

from typing import Any

import httpx

from api_config import (
    GITHUB_APP_SCOPES,
    GITHUB_BASE_URL,
    GITHUB_CLIENT_ID,
    standard_headers,
)
from errors import HTTPError


async def get_device_code() -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"{GITHUB_BASE_URL}/login/device/code",
            headers=standard_headers(),
            json={
                "client_id": GITHUB_CLIENT_ID,
                "scope": GITHUB_APP_SCOPES,
            },
        )

    if not response.is_success:
        raise HTTPError(
            message="Failed to get device code",
            status_code=response.status_code,
            response_text=response.text,
        )

    return response.json()
