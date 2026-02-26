from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from api_config import GITHUB_BASE_URL, GITHUB_CLIENT_ID, standard_headers

logger = logging.getLogger(__name__)


async def poll_access_token(device_code: dict[str, Any]) -> str:
    interval = int(device_code.get("interval", 5)) + 1
    sleep_duration = interval
    logger.debug("Polling access token with interval of %sms", sleep_duration * 1000)

    while True:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{GITHUB_BASE_URL}/login/oauth/access_token",
                headers=standard_headers(),
                json={
                    "client_id": GITHUB_CLIENT_ID,
                    "device_code": device_code["device_code"],
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
            )

        if not response.is_success:
            logger.error("Failed to poll access token: %s", response.text)
            await asyncio.sleep(sleep_duration)
            continue

        payload = response.json()
        logger.debug("Polling access token response: %s", payload)

        access_token = payload.get("access_token")
        if access_token:
            return str(access_token)

        await asyncio.sleep(sleep_duration)
