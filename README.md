# claude-chatbot

A chatbot with a CLI and a Flask web interface, backed by either Groq or Anthropic's Claude API.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then add your API key(s)
```

## Configuration

Set `PROVIDER` in `.env` to choose a backend:

| Provider | Key | Default model | Override with |
|---|---|---|---|
| `groq` (default) | `GROQ_API_KEY` | `openai/gpt-oss-120b` | `GROQ_MODEL` |
| `anthropic` | `ANTHROPIC_API_KEY` | `claude-opus-5` | `CLAUDE_MODEL` |

## Usage

```bash
python chatbot.py      # interactive CLI
python web_chatbot.py  # web UI at http://localhost:5000
```

CLI commands: `quit` / `exit`, `clear`, `history`.
