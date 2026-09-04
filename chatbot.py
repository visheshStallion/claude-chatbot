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

KEY_ENV_VARS = {
    "groq": "GROQ_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


def create_chatbot():
    """Initialize and return a chatbot instance."""
    return Chatbot()


class Chatbot:
    """A chatbot powered by Groq or Claude."""

    def __init__(self, model=None, provider=None):
        """
        Initialize the chatbot.

        The API client is created lazily on first use, so importing this
        module never fails just because a key is missing - important on
        serverless hosts, where an import-time raise takes down the whole
        function instead of returning a readable error.

        Args:
            model: Model to use. Defaults to the GROQ_MODEL / CLAUDE_MODEL
                environment variable, then to the provider's default.
            provider: "groq" or "anthropic". Defaults to the PROVIDER
                environment variable, then to "groq".
        """
        self.provider = (provider or os.getenv("PROVIDER", "groq")).lower()
        if self.provider not in DEFAULT_MODELS:
            raise ValueError(
                f"Unknown PROVIDER {self.provider!r}. Use 'groq' or 'anthropic'."
            )

        env_model = os.getenv("GROQ_MODEL" if self.provider == "groq" else "CLAUDE_MODEL")
        self.model = model or env_model or DEFAULT_MODELS[self.provider]

        self._client = None
        self.conversation_history = []
        self.system_prompt = """You are a helpful, friendly, and knowledgeable AI assistant.
You provide accurate information, engage in thoughtful conversation, and help users with their questions and tasks.
You are honest about your limitations and always try to be helpful."""

    @property
    def client(self):
        """Build the provider client on first use, not at import time."""
        if self._client is None:
            key_name = KEY_ENV_VARS[self.provider]
            if not os.getenv(key_name):
                raise RuntimeError(
                    f"{key_name} is not set. Add it to a .env file in this "
                    f"directory (see .env.example), export it in your shell, or "
                    f"set it in your host's environment variables."
                )
            if self.provider == "groq":
                from groq import Groq
                self._client = Groq()
            else:
                from anthropic import Anthropic
                self._client = Anthropic()
        return self._client

    def set_system_prompt(self, prompt: str):
        """
        Set a custom system prompt for the chatbot.

        Args:
            prompt: The new system prompt
        """
        self.system_prompt = prompt

    def reply(self, messages) -> str:
        """
        Stateless: given a full message list, return the assistant's reply.

        Nothing is stored on the instance, so this is safe to call from a
        serverless handler where the caller owns the conversation.

        Args:
            messages: list of {"role": "user"|"assistant", "content": str}

        Returns:
            The assistant's reply text
        """
        if self.provider == "groq":
            response = self.client.chat.completions.create(
                model=self.model,
                max_completion_tokens=8192,
                messages=[
                    {"role": "system", "content": self.system_prompt}
                ] + list(messages),
            )
            return response.choices[0].message.content

        response = self.client.messages.create(
            model=self.model,
            max_tokens=16000,
            system=self.system_prompt,
            messages=list(messages),
        )
        return next(
            (block.text for block in response.content if block.type == "text"), ""
        )

    def chat(self, user_message: str) -> str:
        """
        Send a message using this instance's own conversation history.

        Used by the CLI, where one process owns one conversation.

        Args:
            user_message: The user's message

        Returns:
            The chatbot's response
        """
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        assistant_message = self.reply(self.conversation_history)

        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })

        return assistant_message

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
