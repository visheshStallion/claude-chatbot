"""
Claude Chatbot Web Interface - Flask application
"""

from flask import Flask, render_template, request, jsonify
from chatbot import Chatbot
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
bot = Chatbot()


@app.route('/')
def index():
    """Render the main chat page."""
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """
    API endpoint to send a message and get a response.
    
    Expected JSON body:
    {
        "message": "user message here"
    }
    """
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400

        response = bot.chat(user_message)
        return jsonify({'response': response}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/clear', methods=['POST'])
def api_clear():
    """Clear conversation history."""
    try:
        bot.clear_history()
        return jsonify({'status': 'success', 'message': 'History cleared'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/history', methods=['GET'])
def api_history():
    """Get conversation history."""
    try:
        history = bot.get_history()
        return jsonify({'history': history}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
