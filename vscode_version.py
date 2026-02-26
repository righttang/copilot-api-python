from __future__ import annotations

import logging

from services.get_vscode_version import get_vscode_version
from state import state

logger = logging.getLogger(__name__)


async def cache_vscode_version() -> None:
    version = await get_vscode_version()
    state.vscode_version = version
    logger.info("Using VSCode version: %s", version)
