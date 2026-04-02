"""Smart Greeter Plugin — Demonstrates all SDK modules.

A complete example showing how to use:
- context: Get session and user information
- memory: Store and recall persistent data
- messaging: Discover available channels
- tools: Delegate to other tools

When invoked, the plugin greets the user with a personalized message
that includes session context and remembers returning visitors.
"""

from zeroclaw_plugin_sdk import plugin_fn
from zeroclaw_plugin_sdk import context, memory, messaging, tools


@plugin_fn
def smart_greet(input):
    """Greet the user with context-aware, personalized messages."""
    name = (input or {}).get("name", "friend")

    # 1. Get session context
    try:
        session = context.session()
        channel_name = session.channel_name
        conversation_id = session.conversation_id
    except Exception:
        channel_name = "unknown"
        conversation_id = "unknown"

    # 2. Check if we've seen this conversation before
    memory_key = f"greeted:{conversation_id}"
    try:
        previous = memory.recall(memory_key)
        first_visit = not previous
    except Exception:
        first_visit = True

    # 3. Query available channels
    try:
        channels = messaging.get_channels()
    except Exception:
        channels = []

    # 4. Build the greeting
    greeting = f"Hello, {name}! You're on the {channel_name} channel."

    if channels:
        greeting += f" Available channels: {', '.join(channels)}."

    if first_visit:
        # 5. For first visits, try to fetch a fun fact via tool delegation
        try:
            fact = tools.tool_call("fun_fact", {"topic": "greeting"})
            greeting += f" Welcome! Here's a fun fact: {fact}"
        except Exception:
            greeting += " Welcome!"

        # Remember this conversation
        try:
            memory.store(memory_key, name)
        except Exception:
            pass
    else:
        greeting += " Welcome back!"

    return {
        "greeting": greeting,
        "channel": channel_name,
        "conversation_id": conversation_id,
        "first_visit": first_visit,
        "available_channels": channels,
    }
