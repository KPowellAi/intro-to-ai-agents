# ============================================================
# EXAMPLE 2: Tool-Using Agent
# ============================================================
# This is an AI AGENT. Unlike Example 1, this agent has TOOLS
# it can use to get real information and perform calculations.
#
# Tools available:
#   - get_weather: Check real weather using wttr.in (free API)
#   - calculator:  Perform math operations
#
# The KEY difference from a chatbot:
#   Claude DECIDES when to use a tool. We don't tell it to.
#   It sees the tools available and chooses the right one.
#
# Flow:
#   You ask a question
#   -> Claude decides if it needs a tool
#   -> If yes: calls the tool, gets the result, then responds
#   -> If no: responds directly (just like Example 1)
#
# Run this file: python examples/02_tool_using_agent.py
# ============================================================

import os
import json
import httpx
from dotenv import load_dotenv
from anthropic import Anthropic

# Load API key from .env file
load_dotenv()

# Create the Anthropic client
client = Anthropic()

MODEL_NAME = "claude-sonnet-4-20250514"


# ---- TOOL FUNCTIONS ----
# These are the actual functions that run when Claude calls a tool.

def get_weather(city):
    """Get real weather data from wttr.in (free, no API key needed)."""
    try:
        # wttr.in is a free weather API -- just send a GET request!
        response = httpx.get(
            f"https://wttr.in/{city}?format=j1",
            timeout=10.0,
        )
        data = response.json()

        # Pull out the current conditions
        current = data["current_condition"][0]
        temp_c = current["temp_C"]
        temp_f = current["temp_F"]
        description = current["weatherDesc"][0]["value"]
        humidity = current["humidity"]
        wind_mph = current["windspeedMiles"]

        return (
            f"Weather in {city}: {temp_c}°C ({temp_f}°F), "
            f"{description}, Humidity: {humidity}%, "
            f"Wind: {wind_mph} mph"
        )
    except Exception as e:
        return f"Could not fetch weather for {city}: {e}"


def calculator(operation, a, b):
    """Perform a math calculation."""
    operations = {
        "add": a + b,
        "subtract": a - b,
        "multiply": a * b,
        "divide": a / b if b != 0 else "Error: Cannot divide by zero",
    }
    result = operations.get(operation, f"Unknown operation: {operation}")
    return f"{a} {operation} {b} = {result}"


# ---- TOOL DEFINITIONS ----
# This is how we tell Claude what tools are available.
# Each tool has a name, description, and input_schema that
# describes what parameters it needs.
# Claude reads these definitions to understand what it can do.

tools = [
    {
        "name": "get_weather",
        "description": "Get the current weather for a city. Use this when the user asks about weather conditions, temperature, or climate in a specific location.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "The city name, e.g. 'London' or 'New York'",
                }
            },
            "required": ["city"],
        },
    },
    {
        "name": "calculator",
        "description": "Perform a basic math calculation. Use this when the user asks you to calculate, add, subtract, multiply, or divide numbers.",
        "input_schema": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"],
                    "description": "The math operation to perform",
                },
                "a": {
                    "type": "number",
                    "description": "The first number",
                },
                "b": {
                    "type": "number",
                    "description": "The second number",
                },
            },
            "required": ["operation", "a", "b"],
        },
    },
]


def run_tool(tool_name, tool_input):
    """Execute a tool and return the result."""
    if tool_name == "get_weather":
        return get_weather(tool_input["city"])
    elif tool_name == "calculator":
        return calculator(tool_input["operation"], tool_input["a"], tool_input["b"])
    else:
        return f"Unknown tool: {tool_name}"


def agent(user_message):
    """
    Send a message to Claude with tools available.
    If Claude decides to use a tool, we run it and return the result.
    """
    print(f"\n\033[94mYou:\033[0m {user_message}\n")

    # Step 1: Send the message to Claude, along with our tool definitions
    messages = [{"role": "user", "content": user_message}]

    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=1024,
        system="You are a helpful assistant with access to weather and calculator tools. Use them when needed to give accurate answers.",
        tools=tools,
        messages=messages,
    )

    # Step 2: Check if Claude wants to use a tool
    # This is the KEY MOMENT -- if stop_reason is "tool_use",
    # Claude is saying "I need to use a tool before I can answer"
    if response.stop_reason == "tool_use":
        # Find the tool_use block in the response
        tool_use = next(
            block for block in response.content if block.type == "tool_use"
        )
        tool_name = tool_use.name
        tool_input = tool_use.input

        print(f"  \033[93m[Agent] Using tool: {tool_name}\033[0m")
        print(f"  \033[93m[Agent] Input: {json.dumps(tool_input)}\033[0m")

        # Step 3: Run the tool
        tool_result = run_tool(tool_name, tool_input)
        print(f"  \033[93m[Agent] Result: {tool_result}\033[0m\n")

        # Step 4: Send the tool result back to Claude
        # We include the full conversation so Claude has context
        messages = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": response.content},
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": tool_result,
                    }
                ],
            },
        ]

        # Step 5: Get Claude's final answer (now with the tool result)
        final_response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=1024,
            system="You are a helpful assistant with access to weather and calculator tools. Use them when needed to give accurate answers.",
            tools=tools,
            messages=messages,
        )

        # Get the text response
        final_text = next(
            (block.text for block in final_response.content if hasattr(block, "text")),
            "No text response received.",
        )
        print(f"\033[92mClaude:\033[0m {final_text}")

    else:
        # Claude didn't need a tool -- respond directly (like Example 1)
        print(f"\033[92mClaude:\033[0m {response.content[0].text}")


def main():
    print("\n" + "=" * 50)
    print("  Tool-Using Agent")
    print("  Watch Claude decide when to use tools!")
    print("=" * 50)

    # Demo questions that show different behaviors:
    demo_questions = [
        # This one will trigger the weather tool (real data!)
        "What's the weather like in London right now?",
        # This one will trigger the calculator tool
        "What is 247 multiplied by 38?",
        # This one needs NO tool -- Claude answers from knowledge
        "What is an AI agent in simple terms?",
    ]

    for question in demo_questions:
        print("\n" + "-" * 50)
        try:
            agent(question)
        except Exception as e:
            print(f"\033[91mError: {e}\033[0m")

    print("\n" + "=" * 50)
    print("  Notice how Claude used tools for weather and math,")
    print("  but answered the knowledge question directly!")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
