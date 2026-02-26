from __future__ import annotations

import argparse
import os

from strands import Agent
from strands.models import OpenAIModel


def build_agent() -> Agent:
    base_url = os.getenv("COPILOT_API_BASE_URL", "http://localhost:4143/v1")
    api_key = os.getenv("OPENAI_API_KEY", "dummy-key")
    model_id = os.getenv("OPENAI_MODEL", "claude-sonnet-4")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))

    model = OpenAIModel(
        model_id=model_id,
        client_args={
            "api_key": api_key,
            "base_url": base_url,
        },
        params={"temperature": temperature},
    )

    return Agent(model=model)


def run_single_prompt(agent: Agent, prompt: str) -> None:
    result = agent(prompt)
    print(result)


def run_interactive(agent: Agent) -> None:
    print("Interactive mode. Type 'exit' to quit.")
    while True:
        prompt = input("> ").strip()
        if not prompt:
            continue
        if prompt.lower() in {"exit", "quit"}:
            break
        result = agent(prompt)
        print(result)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Strands agent client for local copilot-api-python server."
    )
    parser.add_argument(
        "--prompt",
        default="Tell me about agentic AI in 3 bullets.",
        help="Prompt for one-shot mode.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run interactive chat loop.",
    )
    args = parser.parse_args()

    agent = build_agent()
    if args.interactive:
        run_interactive(agent)
    else:
        run_single_prompt(agent, args.prompt)


if __name__ == "__main__":
    main()

