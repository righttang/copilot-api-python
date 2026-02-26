from __future__ import annotations

import json

import anyio

from errors import HTTPError


async def await_approval() -> None:
    def _ask() -> bool:
        value = input("Accept incoming request? [y/N] ").strip().lower()
        return value in {"y", "yes"}

    accepted = await anyio.to_thread.run_sync(_ask)
    if not accepted:
        raise HTTPError(
            message="Request rejected",
            status_code=403,
            response_text=json.dumps({"message": "Request rejected"}),
        )
