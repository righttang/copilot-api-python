from __future__ import annotations

import logging

from services.copilot.get_models import get_models
from state import state

logger = logging.getLogger(__name__)


async def cache_models() -> None:
    models = await get_models()
    state.models = models
    model_ids = [m.get("id") for m in models.get("data", []) if isinstance(m, dict)]
    logger.info("Available models:\n%s", "\n".join(f"- {m}" for m in model_ids))
