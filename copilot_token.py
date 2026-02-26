from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from threading import Event, Thread

from errors import HTTPError
from paths import GITHUB_TOKEN_PATH
from services.github.get_copilot_token import get_copilot_token
from services.github.get_device_code import get_device_code
from services.github.get_user import get_github_user
from services.github.poll_access_token import poll_access_token
from state import state

logger = logging.getLogger(__name__)

_refresh_thread: Thread | None = None
_refresh_stop_event = Event()
_refresh_failure_count = 0
MAX_REFRESH_FAILURES = 3


def _format_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _read_github_token() -> str:
    return GITHUB_TOKEN_PATH.read_text(encoding="utf-8").strip()


def _write_github_token(token: str) -> None:
    GITHUB_TOKEN_PATH.write_text(token, encoding="utf-8")
    try:
        GITHUB_TOKEN_PATH.chmod(0o600)
    except OSError:
        pass


async def _log_user() -> None:
    user = await get_github_user()
    logger.info("Logged in as %s", user.get("login"))


async def setup_github_token(force: bool = False) -> None:
    try:
        github_token = _read_github_token()

        if github_token and not force:
            state.github_token = github_token
            await _log_user()
            return

        logger.info("Not logged in, getting new access token")
        response = await get_device_code()
        logger.debug("Device code response: %s", response)

        logger.info(
            'Please enter the code "%s" in %s',
            response.get("user_code"),
            response.get("verification_uri"),
        )

        token = await poll_access_token(response)
        _write_github_token(token)
        state.github_token = token
        await _log_user()

    except HTTPError as error:
        logger.error("Failed to get GitHub token: %s", error.response_text)
        raise
    except Exception:
        logger.exception("Failed to get GitHub token")
        raise


async def setup_copilot_token() -> None:
    global _refresh_failure_count

    stop_copilot_token_refresh()

    token_payload = await get_copilot_token()
    state.copilot_token = str(token_payload.get("token"))
    _refresh_failure_count = 0

    refresh_in = int(token_payload.get("refresh_in", 3600))
    logger.info(
        "[%s] Copilot token will refresh in %s seconds",
        _format_timestamp(),
        max(0, refresh_in - 60),
    )

    _start_copilot_token_refresh_loop(refresh_in)


def _start_copilot_token_refresh_loop(initial_refresh_in: int) -> None:
    global _refresh_thread

    _refresh_stop_event.clear()

    def _refresh_loop() -> None:
        global _refresh_failure_count

        refresh_in = initial_refresh_in
        while not _refresh_stop_event.is_set():
            wait_seconds = max(1, refresh_in - 60)
            if _refresh_stop_event.wait(wait_seconds):
                return

            logger.info("[%s] Refreshing Copilot token", _format_timestamp())
            try:
                payload = asyncio.run(get_copilot_token())
                state.copilot_token = str(payload.get("token"))
                refresh_in = int(payload.get("refresh_in", 3600))
                _refresh_failure_count = 0
                logger.info(
                    "[%s] Copilot token refreshed successfully", _format_timestamp()
                )
                logger.debug(
                    "[%s] Next refresh in %s seconds",
                    _format_timestamp(),
                    max(0, refresh_in - 60),
                )
            except Exception:
                _refresh_failure_count += 1
                logger.exception(
                    "[%s] Failed to refresh Copilot token (attempt %s/%s)",
                    _format_timestamp(),
                    _refresh_failure_count,
                    MAX_REFRESH_FAILURES,
                )
                if _refresh_failure_count >= MAX_REFRESH_FAILURES:
                    logger.error(
                        "[%s] Multiple refresh failures detected. This might indicate an expired GitHub token.",
                        _format_timestamp(),
                    )
                    logger.info(
                        "[%s] Consider running the 'auth' command to refresh your GitHub token",
                        _format_timestamp(),
                    )
                    _refresh_failure_count = 0

    _refresh_thread = Thread(target=_refresh_loop, daemon=True, name="copilot-token-refresh")
    _refresh_thread.start()


def stop_copilot_token_refresh() -> None:
    global _refresh_thread

    _refresh_stop_event.set()
    if _refresh_thread and _refresh_thread.is_alive():
        _refresh_thread.join(timeout=1)
    _refresh_thread = None
