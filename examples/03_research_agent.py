# ============================================================
# EXAMPLE 3: Research Agent (Full Agent Loop)
# ============================================================
# This is a FULL AI AGENT with an autonomous loop.
# Unlike Example 2, this agent can use MULTIPLE tools in
# sequence and keeps going until it decides the task is done.
#
# Tools available:
#   - search_web:       Search the web using DuckDuckGo (free)
#   - get_page_content: Read the contents of a web page
#   - save_report:      Save a report to a file
#
# The KEY difference from Example 2:
#   Example 2: One tool call, then done
#   Example 3: The agent LOOPS -- it keeps calling tools until
#              it decides the task is complete
#
# This is the "while loop" pattern -- the core of all agents:
#   while claude_wants_to_use_tools:
#       run the tool
#       give the result back to claude
#       ask claude what to do next
#
# Run this file: python examples/03_research_agent.py
# ============================================================

import os
import json
from datetime import datetime
from dotenv import load_dotenv
from anthropic import Anthropic
from ddgs import DDGS
import httpx
import re

# Load API key from .env file
load_dotenv()

# Create the Anthropic client
client = Anthropic()

MODEL_NAME = "claude-sonnet-4-20250514"


# ---- TOOL FUNCTIONS ----
# These use real, free APIs -- no extra API keys needed!

def search_web(query):
    """Search the web using DuckDuckGo (free, no API key needed)."""
    try:
        results = DDGS().text(query, max_results=5)
        # Format the results nicely
        formatted = []
        for r in results:
            formatted.append({
                "title": r.get("title", "No title"),
                "url": r.get("href", ""),
                "snippet": r.get("body", "No description"),
            })
        return json.dumps(formatted, indent=2)
    except Exception as e:
        return json.dumps([{"title": "Search error", "url": "", "snippet": str(e)}])


def get_page_content(url):
    """Fetch the text content of a web page."""
    try:
        response = httpx.get(url, timeout=15.0, follow_redirects=True)
        html = response.text

        # Simple HTML tag removal to get readable text
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        # Limit to first 3000 characters to stay within token limits
        if len(text) > 3000:
            text = text[:3000] + "... [content truncated]"

        return text if text else "Could not extract text content from this page."
    except Exception as e:
        return f"Could not fetch page content: {e}"


def save_report(filename, content):
    """Save a research report to the outputs directory."""
    os.makedirs("outputs", exist_ok=True)

    filepath = os.path.join("outputs", filename)
    with open(filepath, "w") as f:
        f.write(content)

    return f"Report saved successfully to {filepath} ({len(content)} characters)"


# ---- TOOL DEFINITIONS ----
# Tell Claude what tools it has access to.

tools = [
    {
        "name": "search_web",
        "description": "Search the web for information on a topic. Returns a list of search results with titles, URLs, and snippets. Use this to find relevant sources for research.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query, e.g. 'benefits of renewable energy'",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_page_content",
        "description": "Get the text content of a web page. Use this after search_web to read the full content of a promising search result.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL of the page to read",
                }
            },
            "required": ["url"],
        },
    },
    {
        "name": "save_report",
        "description": "Save a research report to a file. Use this when you have gathered enough information and are ready to save your findings. Write the report in markdown format with clear headings.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "The filename for the report, e.g. 'ai_agents_report.md'",
                },
                "content": {
                    "type": "string",
                    "description": "The full content of the report in markdown format",
                },
            },
            "required": ["filename", "content"],
        },
    },
]


def run_tool(tool_name, tool_input):
    """Execute a tool by name and return the result."""
    if tool_name == "search_web":
        return search_web(tool_input["query"])
    elif tool_name == "get_page_content":
        return get_page_content(tool_input["url"])
    elif tool_name == "save_report":
        return save_report(tool_input["filename"], tool_input["content"])
    else:
        return f"Unknown tool: {tool_name}"


def research_agent(task):
    """
    A research agent that autonomously completes a task.

    THIS IS THE AGENT LOOP -- the most important concept in this workshop.

    The loop works like this:
    1. Send the task to Claude (with tools available)
    2. If Claude wants to use a tool -> run it, give the result back
    3. If Claude is done (stop_reason == "end_turn") -> show the final answer
    4. Repeat steps 2-3 until Claude is done

    Claude decides:
      - WHICH tools to use
      - In WHAT ORDER to use them
      - WHEN it has enough information to stop
    """
    print(f"\n\033[94mTask:\033[0m {task}\n")
    print("\033[90m--- Agent starting work ---\033[0m\n")

    # Build the initial message
    messages = [{"role": "user", "content": task}]

    system_prompt = """You are a research agent. When given a research task:
1. Search the web to find relevant information (use at least 2 different searches)
2. Read the content of 1-2 promising search results
3. Synthesize your findings into a well-structured report
4. Save the report to a file using save_report

Write your report in markdown format with clear headings and bullet points.
Keep the report concise but informative."""

    # Keep track of how many tool calls the agent makes
    tool_call_count = 0

    # Safety limit to prevent infinite loops
    max_iterations = 15

    # ========================================
    # THE AGENT LOOP
    # ========================================
    # This is where the magic happens.
    # We keep looping as long as Claude wants to use tools.

    while tool_call_count < max_iterations:
        # Send the conversation to Claude
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=4096,
            system=system_prompt,
            tools=tools,
            messages=messages,
        )

        # Check: does Claude want to use a tool, or is it done?
        if response.stop_reason == "end_turn":
            # Claude is DONE -- no more tools needed
            final_text = next(
                (block.text for block in response.content if hasattr(block, "text")),
                "Task complete.",
            )
            print(f"\n\033[90m--- Agent finished ({tool_call_count} tool calls) ---\033[0m\n")
            print(f"\033[92mClaude:\033[0m {final_text}\n")
            break

        elif response.stop_reason == "tool_use":
            # Claude wants to use one or more tools -- let's run them!

            # Add Claude's response to the conversation
            messages.append({"role": "assistant", "content": response.content})

            # Process ALL tool calls in this response
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    tool_call_count += 1

                    print(f"  \033[93m[Step {tool_call_count}] Using tool: {tool_name}\033[0m")

                    # Show what the agent is doing
                    if tool_name == "search_web":
                        print(f"           Searching for: \"{tool_input['query']}\"")
                    elif tool_name == "get_page_content":
                        print(f"           Reading: {tool_input['url']}")
                    elif tool_name == "save_report":
                        print(f"           Saving report: {tool_input['filename']}")

                    # Run the tool
                    tool_result = run_tool(tool_name, tool_input)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(tool_result),
                    })

            # Add all tool results to the conversation
            messages.append({"role": "user", "content": tool_results})

            # The loop continues -- Claude will decide what to do next!

        else:
            # Unexpected stop reason -- break to avoid infinite loop
            print(f"Unexpected stop reason: {response.stop_reason}")
            break

    if tool_call_count >= max_iterations:
        print("\033[91mAgent reached maximum iterations. Stopping.\033[0m")


def main():
    print("\n" + "=" * 50)
    print("  Research Agent (Full Agent Loop)")
    print("  Watch the agent research a topic step by step!")
    print("=" * 50)

    # Give the agent a research task
    research_task = (
        "Research the topic of AI agents: what they are, how they work, "
        "and their real-world applications. Save a comprehensive report."
    )

    try:
        research_agent(research_task)
    except Exception as e:
        print(f"\n\033[91mError: {e}\033[0m")
        print("Make sure your API key is set in the .env file.")

    print("=" * 50)
    print("  Check the 'outputs/' folder for the saved report!")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
