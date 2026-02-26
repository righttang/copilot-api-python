from __future__ import annotations

import json
import logging
import math
import time

from errors import HTTPError
from state import RuntimeState

logger = logging.getLogger(__name__)


async def check_rate_limit(state: RuntimeState) -> None:
    if state.rate_limit_seconds is None:
        return

    now = time.time()

    with state.rate_limit_lock:
        if state.last_request_timestamp is None:
            state.last_request_timestamp = now
            return

        elapsed_seconds = now - state.last_request_timestamp

        if elapsed_seconds > state.rate_limit_seconds:
            state.last_request_timestamp = now
            return

        wait_time_seconds = math.ceil(state.rate_limit_seconds - elapsed_seconds)

    if not state.rate_limit_wait:
        logger.warning(
            "Rate limit exceeded. Need to wait %s more seconds.", wait_time_seconds
        )
        raise HTTPError(
            message="Rate limit exceeded",
            status_code=429,
            response_text=json.dumps({"message": "Rate limit exceeded"}),
        )

    logger.warning(
        "Rate limit reached. Waiting %s seconds before proceeding...",
        wait_time_seconds,
    )
    await anyio_sleep(wait_time_seconds)

    with state.rate_limit_lock:
        state.last_request_timestamp = time.time()

    logger.info("Rate limit wait completed, proceeding with request")


async def anyio_sleep(seconds: int) -> None:
    import anyio

    await anyio.sleep(seconds)
