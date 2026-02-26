from __future__ import annotations

import logging

from fastapi.responses import JSONResponse

from errors import HTTPError

logger = logging.getLogger(__name__)


def forward_error(error: Exception) -> JSONResponse:
    logger.exception("Error occurred", exc_info=error)

    if isinstance(error, HTTPError):
        return JSONResponse(
            status_code=error.status_code,
            content={
                "error": {
                    "message": error.response_text,
                    "type": "error",
                }
            },
        )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": str(error),
                "type": "error",
            }
        },
    )


def anthropic_error_response(error: Exception) -> JSONResponse:
    logger.exception("Error handling Anthropic request", exc_info=error)

    if isinstance(error, HTTPError):
        etype = (
            "invalid_request_error"
            if 400 <= error.status_code < 500
            else "api_error"
        )
        return JSONResponse(
            status_code=error.status_code,
            content={
                "type": "error",
                "error": {
                    "type": etype,
                    "message": error.message,
                },
            },
        )

    return JSONResponse(
        status_code=500,
        content={
            "type": "error",
            "error": {
                "type": "api_error",
                "message": str(error),
            },
        },
    )
