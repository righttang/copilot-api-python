# Copilot API Python

⚠️ **EDUCATIONAL PURPOSE ONLY** ⚠️

Python implementation of a reverse-engineered GitHub Copilot API wrapper, compatible with OpenAI-style and Anthropic-style client APIs.

## Endpoints

### OpenAI-compatible

- `POST /chat/completions`
- `POST /v1/chat/completions`
- `GET /models`
- `GET /v1/models`
- `POST /embeddings`
- `POST /v1/embeddings`

### Anthropic-compatible

- `POST /v1/messages`
- `POST /v1/messages/count_tokens`

### Status

- `GET /`

## CLI

- `python -m copilot_api start [options]`
- `python -m copilot_api auth [options]`

### Start options

- `--port`, `-p` (default: `4141`)
- `--verbose`, `-v`
- `--business` (default behavior)
- `--enterprise`
- `--manual`
- `--rate-limit`, `-r`
- `--wait`, `-w`
- `--github-token`, `-g`

### Auth options

- `--verbose`, `-v`

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Run

```bash
python -m copilot_api start --port 4143 --verbose
```

Or run auth-only flow:

```bash
python -m copilot_api auth --verbose
```
