from __future__ import annotations

import httpx

FALLBACK = "1.98.1"
AUR_URL = (
    "https://aur.archlinux.org/cgit/aur.git/plain/PKGBUILD"
    "?h=visual-studio-code-bin"
)


async def get_vscode_version() -> str:
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(AUR_URL)
            response.raise_for_status()
            pkgbuild = response.text
    except Exception:
        return FALLBACK

    for line in pkgbuild.splitlines():
        if line.startswith("pkgver="):
            value = line.removeprefix("pkgver=").strip()
            if value:
                return value

    return FALLBACK
