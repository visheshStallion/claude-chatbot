"""
Vercel Python entrypoint.

Vercel looks for a WSGI/ASGI callable named `app` in files under api/.
The application itself lives in web_chatbot.py at the repo root, so this
module only puts the root on sys.path and re-exports it.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_chatbot import app  # noqa: E402

__all__ = ["app"]
