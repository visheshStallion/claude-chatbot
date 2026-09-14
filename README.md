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

## Deploying to Vercel

`vercel.json` builds `web_chatbot.py` with `@vercel/python` and routes every
request to it, bundling `templates/` and `chatbot.py` alongside the function.

`.env` is gitignored, so your key never ships with the code — set it in the
Vercel project instead:

1. **Settings → Environment Variables** → add `GROQ_API_KEY` (and `PROVIDER`
   if you want `anthropic` rather than the `groq` default). Tick **Production**,
   or the live site won't receive it.
2. **Redeploy.** Vercel injects environment variables at deploy time, so an
   existing deployment cannot pick up a variable added after it was built.

Check the wiring at `/api/health` without spending a token on the model:

```json
{"status": "ok", "provider": "groq", "model": "openai/gpt-oss-120b"}
```

A `503` with `"status": "missing_api_key"` means step 1 or 2 is incomplete.

### Conversation state

The server is stateless — each `/api/chat` call carries the history it wants
continued, and the browser keeps that history in `localStorage`. Serverless
instances are concurrent and recycled, so a server-side history would be shared
between unrelated visitors and lost without warning.

### Partnership enquiries (`/api/lead`)

When a visitor asks to submit a partnership enquiry in chat, the system
prompt has the model gather company, contact name, contact email/phone,
division, and a short message, then end its reply with a fenced ` ```lead `
JSON block once the visitor confirms. The frontend turns that block into a
review-and-send card — the model never sends anything itself, and never
claims an enquiry was received.

Sending requires `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, and
`LEAD_EMAIL_TO` in `.env` (see `.env.example`). Without them, `/api/lead`
returns a `502` and the card tells the visitor to use `/contact-us/` instead
— the rest of the app is unaffected.
