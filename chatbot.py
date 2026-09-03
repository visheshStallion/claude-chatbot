"""
Claude Chatbot - A conversational AI chatbot using Anthropic's Claude API
"""

import os
from anthropic import Anthropic


def create_chatbot():
    """Initialize and return a Claude chatbot instance."""
    return Chatbot()


class Chatbot:
    """A chatbot powered by Claude AI."""

    def __init__(self, model="claude-3-5-sonnet-20241022"):
        """
        Initialize the chatbot with Claude API.
        
        Args:
            model: The Claude model to use (default: claude-3-5-sonnet-20241022)
        """
        self.client = Anthropic()
        self.model = model
        self.conversation_history = []
        self.system_prompt = """You are a helpful, friendly, and knowledgeable AI assistant. 
You provide accurate information, engage in thoughtful conversation, and help users with their questions and tasks. 
You are honest about your limitations and always try to be helpful."""

    def set_system_prompt(self, prompt: str):
        """
        Set a custom system prompt for the chatbot.
        
        Args:
            prompt: The new system prompt
        """
        self.system_prompt = prompt

    def chat(self, user_message: str) -> str:
        """
        Send a message to Claude and get a response.
        
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

        # Get response from Claude
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=self.system_prompt,
            messages=self.conversation_history
        )

        # Extract assistant response
        assistant_message = response.content[0].text

        # Add assistant response to conversation history
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
    print("🤖 Claude Chatbot")
    print("=" * 50)
    print("Type 'quit' or 'exit' to end the conversation")
    print("Type 'clear' to clear conversation history")
    print("Type 'history' to see conversation history")
    print("=" * 50)
    print()

    bot = create_chatbot()

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
                        role = "You" if msg["role"] == "user" else "Claude"
                        print(f"{i}. {role}: {msg['content'][:100]}...")
                    print("-" * 50 + "\n")
                continue

            print("Claude: ", end="", flush=True)
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
