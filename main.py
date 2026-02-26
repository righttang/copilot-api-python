from __future__ import annotations

import asyncio
import logging

import typer
import uvicorn

from model_cache import cache_models
from paths import GITHUB_TOKEN_PATH, ensure_paths
from server import server
from state import state
from copilot_token import (
    setup_copilot_token,
    setup_github_token,
    stop_copilot_token_refresh,
)
from vscode_version import cache_vscode_version

app = typer.Typer(
    name="copilot-api",
    help=(
        "A wrapper around GitHub Copilot API to make it OpenAI compatible, "
        "making it usable for other tools."
    ),
    no_args_is_help=False,
)

logger = logging.getLogger(__name__)


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")
    if verbose:
        logger.info("Verbose logging enabled")


async def _run_server(
    port: int,
    verbose: bool,
    business: bool,
    enterprise: bool,
    manual: bool,
    rate_limit: int | None,
    wait: bool,
    github_token: str | None,
) -> None:
    # Default to business endpoints unless enterprise is explicitly requested.
    state.account_type = "business"

    if business:
        state.account_type = "business"
        logger.info("Using business plan GitHub account")
    elif enterprise:
        state.account_type = "enterprise"
        logger.info("Using enterprise plan GitHub account")
    else:
        logger.info("Using business plan GitHub account (default)")

    state.manual_approve = manual
    state.rate_limit_seconds = rate_limit
    state.rate_limit_wait = wait

    ensure_paths()
    await cache_vscode_version()

    if github_token:
        state.github_token = github_token
        logger.info("Using provided GitHub token")
    else:
        await setup_github_token()

    await setup_copilot_token()
    await cache_models()

    server_url = f"http://localhost:{port}"
    logger.info("Server started at %s", server_url)


@app.command()
def start(
    port: int = typer.Option(4141, "--port", "-p", help="Port to listen on"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
    business: bool = typer.Option(
        False, "--business", help="Use a business plan GitHub account"
    ),
    enterprise: bool = typer.Option(
        False, "--enterprise", help="Use an enterprise plan GitHub account"
    ),
    manual: bool = typer.Option(
        False, "--manual", help="Enable manual request approval"
    ),
    rate_limit: int | None = typer.Option(
        None, "--rate-limit", "-r", help="Rate limit in seconds between requests"
    ),
    wait: bool = typer.Option(
        False,
        "--wait",
        "-w",
        help="Wait instead of error when rate limit is hit",
    ),
    github_token: str | None = typer.Option(
        None,
        "--github-token",
        "-g",
        help=(
            "Provide GitHub token directly (must be generated using the `auth` subcommand)"
        ),
    ),
) -> None:
    _setup_logging(verbose)

    try:
        asyncio.run(
            _run_server(
                port=port,
                verbose=verbose,
                business=business,
                enterprise=enterprise,
                manual=manual,
                rate_limit=rate_limit,
                wait=wait,
                github_token=github_token,
            )
        )
        uvicorn.run(server, host="0.0.0.0", port=port, log_level="info")
    finally:
        stop_copilot_token_refresh()


@app.command()
def auth(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    )
) -> None:
    _setup_logging(verbose)

    async def _run_auth() -> None:
        ensure_paths()
        await setup_github_token(force=True)
        logger.info("GitHub token written to %s", GITHUB_TOKEN_PATH)

    asyncio.run(_run_auth())


def run() -> None:
    app()


if __name__ == "__main__":
    run()
