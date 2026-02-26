from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class HTTPError(Exception):
    message: str
    status_code: int
    response_text: str

    def __str__(self) -> str:
        return self.message


def parse_json_text(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return text
