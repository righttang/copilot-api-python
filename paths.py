from __future__ import annotations

from pathlib import Path

APP_DIR = Path.home() / ".local" / "share" / "copilot-api"
GITHUB_TOKEN_PATH = APP_DIR / "github_token"


def ensure_paths() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    if not GITHUB_TOKEN_PATH.exists():
        GITHUB_TOKEN_PATH.write_text("", encoding="utf-8")
        GITHUB_TOKEN_PATH.chmod(0o600)

    # Ensure secure mode even when file already exists.
    try:
        GITHUB_TOKEN_PATH.chmod(0o600)
    except OSError:
        pass
