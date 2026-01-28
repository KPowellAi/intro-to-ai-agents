# ============================================================
# EXAMPLE 1: Simple Chatbot (NOT an Agent)
# ============================================================
# This is a regular chatbot. It can answer questions using
# Claude's knowledge, but it CANNOT use tools or take actions.
#
# Flow: You type a message -> Claude responds -> repeat
#
# Run this file: python examples/01_simple_chatbot.py
# ============================================================

import os
from dotenv import load_dotenv
from anthropic import Anthropic

# Load API key from .env file
load_dotenv()

# Create the Anthropic client (it automatically uses ANTHROPIC_API_KEY)
client = Anthropic()

# We'll use Claude Sonnet -- capable and widely available
MODEL_NAME = "claude-sonnet-4-20250514"

# This list keeps track of our conversation.
# Each message has a "role" (user or assistant) and "content" (the text).
conversation_history = []


def chat(user_message):
    """Send a message to Claude and get a response."""

    # Add the user's message to our conversation history
    conversation_history.append({
        "role": "user",
        "content": user_message,
    })

    # Send the conversation to Claude and get a response
    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=1024,
        system="You are a friendly, helpful assistant. Keep your responses concise and clear.",
        messages=conversation_history,
    )

    # Get Claude's text response
    assistant_message = response.content[0].text

    # Add Claude's response to the conversation history
    # (so Claude remembers what was said in future messages)
    conversation_history.append({
        "role": "assistant",
        "content": assistant_message,
    })

    return assistant_message


def main():
    """Run the chatbot in an interactive loop."""

    print("\n" + "=" * 50)
    print("  Simple Chatbot (NOT an Agent)")
    print("  Type 'quit' to exit")
    print("=" * 50 + "\n")

    while True:
        # Get input from the user
        user_input = input("\033[94mYou: \033[0m")

        # Check if the user wants to quit
        if user_input.lower() in ["quit", "exit", "q"]:
            print("\nGoodbye!")
            break

        # Skip empty input
        if not user_input.strip():
            continue

        # Get Claude's response
        try:
            response = chat(user_input)
            print(f"\n\033[92mClaude:\033[0m {response}\n")
        except Exception as e:
            print(f"\n\033[91mError: {e}\033[0m")
            print("Make sure your API key is set in the .env file.\n")


# This runs the main function when you execute this file
if __name__ == "__main__":
    main()
