# Strands Agent Example

This example connects a Strands agent to your local Copilot API proxy using the OpenAI-compatible endpoint.

## Prerequisites

- Copilot API Python server running locally (for example on `http://localhost:4143`)
- Python 3.11+

## Setup

```bash
cd ./examples/strands-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run (single prompt)

```bash
source .venv/bin/activate
python agent.py --prompt "Explain agentic AI in 3 bullets."
```

## Run (interactive)

```bash
source .venv/bin/activate
python agent.py --interactive
```

## Environment Variables

Use defaults or override:

- `COPILOT_API_BASE_URL` (default: `http://localhost:4143/v1`)
- `OPENAI_API_KEY` (default: `dummy-key`)
- `OPENAI_MODEL` (default: `claude-sonnet-4`)
- `OPENAI_TEMPERATURE` (default: `0.2`)

