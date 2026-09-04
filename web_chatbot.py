"""
Chatbot Web Interface - Flask application

The conversation lives with the client, not the server: each /api/chat call
carries the history it wants continued. That keeps the app correct on
serverless hosts, where instances are stateless and concurrent, and a
module-level history would be shared between unrelated visitors.
"""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from chatbot import Chatbot

load_dotenv()

# Absolute path so templates resolve no matter which directory the WSGI
# entrypoint is imported from (e.g. api/index.py on Vercel).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))

# Safe to build at import time - the API client itself is created lazily on
# the first request, so a missing key surfaces as a 500 with a readable
# message rather than crashing the whole function on import.
bot = Chatbot()

# Cap what a caller can replay back at us, so one request can't push an
# unbounded history into the model.
MAX_HISTORY_MESSAGES = 40
MAX_MESSAGE_CHARS = 20000


def clean_history(raw):
    """Validate and trim client-supplied conversation history."""
    if not isinstance(raw, list):
        return []

    cleaned = []
    for msg in raw:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        content = msg.get("content")
        if role not in ("user", "assistant") or not isinstance(content, str):
            continue
        if not content:
            continue
        cleaned.append({"role": role, "content": content[:MAX_MESSAGE_CHARS]})

    return cleaned[-MAX_HISTORY_MESSAGES:]


@app.route('/')
def index():
    """Render the main chat page."""
    return render_template('index.html')


@app.route('/<path:subpath>')
def catch_all(subpath):
    """
    Serve the chat page for any unmatched path.

    A host that rewrites requests to an internal entrypoint can hand the WSGI
    app a path other than "/", which would otherwise 404 the whole frontend.
    API routes are matched before this one, so they still fail honestly.
    """
    # "api/index" is an entrypoint path some hosts rewrite to, not a real
    # API route, so it renders the page rather than 404ing.
    if subpath.startswith('api/') and subpath != 'api/index':
        return jsonify({'error': 'Not found'}), 404
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """
    Send a message and get a response.

    Expected JSON body:
    {
        "message": "user message here",
        "history": [{"role": "user"|"assistant", "content": "..."}, ...]
    }

    `history` is optional; omit it to start a fresh conversation.
    """
    try:
        data = request.get_json(silent=True) or {}
        user_message = str(data.get('message', '')).strip()

        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400

        messages = clean_history(data.get('history'))
        messages.append({"role": "user", "content": user_message[:MAX_MESSAGE_CHARS]})

        response = bot.reply(messages)
        return jsonify({'response': response}), 200

    except Exception as e:
        app.logger.exception("chat request failed")
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def api_health():
    """Report provider wiring without calling the model."""
    key_present = bool(os.getenv(
        "GROQ_API_KEY" if bot.provider == "groq" else "ANTHROPIC_API_KEY"
    ))
    return jsonify({
        'status': 'ok' if key_present else 'missing_api_key',
        'provider': bot.provider,
        'model': bot.model,
    }), 200 if key_present else 503


if __name__ == '__main__':
    app.run(debug=True, port=5000)
