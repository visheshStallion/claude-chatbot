"""
Chatbot Web Interface - Flask application

The conversation lives with the client, not the server: each /api/chat call
carries the history it wants continued. That keeps the app correct on
serverless hosts, where instances are stateless and concurrent, and a
module-level history would be shared between unrelated visitors.
"""

import os
import re
import smtplib
from email.message import EmailMessage

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

# Fields the chatbot is told (in chatbot.py's system prompt) to gather before
# it offers to send a partnership enquiry, in the order they're emailed.
LEAD_FIELDS = (
    ("company", "Company"),
    ("contact_name", "Contact name"),
    ("contact", "Email or phone"),
    ("division", "Division"),
    ("message", "Enquiry"),
)
LEAD_FIELD_MAX_CHARS = 2000
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^[\d\s+()-]{6,20}$")


def send_lead_email(fields):
    """
    Email a partnership enquiry gathered in chat. Raises on any failure -
    missing SMTP config included - so the caller can report it rather than
    silently drop the enquiry.
    """
    host = os.environ["SMTP_HOST"]
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]
    sender = os.getenv("SMTP_FROM", user)
    recipient = os.environ["LEAD_EMAIL_TO"]

    msg = EmailMessage()
    msg["Subject"] = f"Stallion Concierge enquiry - {fields['company']}"
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(
        "\n".join(f"{label}: {fields[key]}" for key, label in LEAD_FIELDS)
    )

    with smtplib.SMTP(host, port, timeout=10) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(msg)


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


@app.route('/api/lead', methods=['POST'])
def api_lead():
    """
    Deliver a partnership/business enquiry the chatbot gathered in chat.

    Expected JSON body: {"company", "contact_name", "contact", "division",
    "message", "website"}. "website" is a honeypot: it's never shown to a
    real visitor, so a non-empty value means a bot filled in every input.
    """
    data = request.get_json(silent=True) or {}

    if str(data.get('website', '')).strip():
        # Pretend success so a bot doesn't learn to leave it blank; nothing
        # is actually sent.
        return jsonify({'status': 'ok'}), 200

    fields = {}
    for key, _label in LEAD_FIELDS:
        value = str(data.get(key, '')).strip()
        if not value:
            return jsonify({'error': f'{key.replace("_", " ")} is required'}), 400
        fields[key] = value[:LEAD_FIELD_MAX_CHARS]

    contact = fields['contact']
    if not (_EMAIL_RE.match(contact) or _PHONE_RE.match(contact)):
        return jsonify({'error': 'contact must be an email address or phone number'}), 400

    try:
        send_lead_email(fields)
    except Exception:
        app.logger.exception("lead email failed")
        return jsonify({
            'error': 'Could not send the enquiry. Please use /contact-us/ instead.',
        }), 502

    return jsonify({'status': 'ok'}), 200


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
