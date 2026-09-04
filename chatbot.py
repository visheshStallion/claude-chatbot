"""
Chatbot - A conversational AI chatbot backed by Groq or Anthropic's Claude API

Set PROVIDER=groq (default) or PROVIDER=anthropic in .env to switch backends.
"""

import os
from dotenv import load_dotenv

# Load API keys and provider settings from .env
load_dotenv()

DEFAULT_MODELS = {
    "groq": "openai/gpt-oss-120b",
    "anthropic": "claude-opus-5",
}


def create_chatbot():
    """Initialize and return a chatbot instance."""
    return Chatbot()


class Chatbot:
    """A chatbot powered by Groq or Claude."""

    def __init__(self, model=None, provider=None):
        """
        Initialize the chatbot.

        Args:
            model: Model to use. Defaults to the GROQ_MODEL / CLAUDE_MODEL
                environment variable, then to the provider's default.
            provider: "groq" or "anthropic". Defaults to the PROVIDER
                environment variable, then to "groq".
        """
        self.provider = (provider or os.getenv("PROVIDER", "groq")).lower()

        if self.provider == "groq":
            self._require_key("GROQ_API_KEY")
            from groq import Groq

            self.client = Groq()
            self.model = model or os.getenv("GROQ_MODEL") or DEFAULT_MODELS["groq"]
        elif self.provider == "anthropic":
            self._require_key("ANTHROPIC_API_KEY")
            from anthropic import Anthropic

            self.client = Anthropic()
            self.model = model or os.getenv("CLAUDE_MODEL") or DEFAULT_MODELS["anthropic"]
        else:
            raise ValueError(
                f"Unknown PROVIDER {self.provider!r}. Use 'groq' or 'anthropic'."
            )

        self.conversation_history = []
        self.system_prompt = """You are a helpful, friendly, and knowledgeable AI assistant.
You provide accurate information, engage in thoughtful conversation, and help users with their questions and tasks.
You are honest about your limitations and always try to be helpful."""

    @staticmethod
    def _require_key(name: str):
        """Fail early with a readable message if the API key is missing."""
        if not os.getenv(name):
            raise RuntimeError(
                f"{name} is not set. Add it to a .env file in this directory "
                f"(see .env.example) or export it in your shell."
            )

    def set_system_prompt(self, prompt: str):
        """
        Set a custom system prompt for the chatbot.

        Args:
            prompt: The new system prompt
        """
        self.system_prompt = prompt

    def chat(self, user_message: str) -> str:
        """
        Send a message to the model and get a response.

        Args:
            user_message: The user's message

        Returns:
            The chatbot's response
        """
        # Add user message to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        if self.provider == "groq":
            assistant_message = self._chat_groq()
        else:
            assistant_message = self._chat_anthropic()

        # Add assistant response to conversation history
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })

        return assistant_message

    def _chat_groq(self) -> str:
        """Send the conversation to Groq's OpenAI-compatible chat endpoint."""
        response = self.client.chat.completions.create(
            model=self.model,
            max_completion_tokens=8192,
            messages=[
                {"role": "system", "content": self.system_prompt}
            ] + self.conversation_history,
        )
        return response.choices[0].message.content

    def _chat_anthropic(self) -> str:
        """Send the conversation to the Anthropic Messages API."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=16000,
            system=self.system_prompt,
            messages=self.conversation_history,
        )
        return next(
            (block.text for block in response.content if block.type == "text"), ""
        )

    def clear_history(self):
        """Clear the conversation history."""
        self.conversation_history = []

    def get_history(self):
        """Get the full conversation history."""
        return self.conversation_history


def main():
    """Main function to run the chatbot in interactive mode."""
    bot = create_chatbot()

    print("🤖 Chatbot")
    print("=" * 50)
    print(f"Provider: {bot.provider}  |  Model: {bot.model}")
    print("Type 'quit' or 'exit' to end the conversation")
    print("Type 'clear' to clear conversation history")
    print("Type 'history' to see conversation history")
    print("=" * 50)
    print()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit']:
                print("Goodbye! 👋")
                break

            if user_input.lower() == 'clear':
                bot.clear_history()
                print("✓ Conversation history cleared\n")
                continue

            if user_input.lower() == 'history':
                history = bot.get_history()
                if not history:
                    print("No conversation history yet.\n")
                else:
                    print("\n📋 Conversation History:")
                    print("-" * 50)
                    for i, msg in enumerate(history, 1):
                        role = "You" if msg["role"] == "user" else "Bot"
                        print(f"{i}. {role}: {msg['content'][:100]}...")
                    print("-" * 50 + "\n")
                continue

            print("Bot: ", end="", flush=True)
            response = bot.chat(user_input)
            print(response)
            print()

        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"Error: {e}")
            print("Please try again.\n")


if __name__ == "__main__":
    main()
