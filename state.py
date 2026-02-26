from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Any


@dataclass
class RuntimeState:
    github_token: str | None = None
    copilot_token: str | None = None

    account_type: str = "business"
    models: dict[str, Any] | None = None
    vscode_version: str | None = None

    manual_approve: bool = False
    rate_limit_wait: bool = False
    rate_limit_seconds: int | None = None
    last_request_timestamp: float | None = None

    rate_limit_lock: Lock = field(default_factory=Lock)


state = RuntimeState()
