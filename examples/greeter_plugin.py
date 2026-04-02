"""Greeter Plugin — A simple greeting plugin.

Demonstrates basic @plugin_fn usage with input handling.
"""

from zeroclaw_plugin_sdk import plugin_fn


@plugin_fn
def greet(input):
    """Generate a personalized greeting.

    Input:
        {"name": "Alice"}  # optional, defaults to "world"

    Output:
        {"message": "Hello, Alice!", "name": "Alice"}
    """
    name = (input or {}).get("name", "world")
    return {
        "message": f"Hello, {name}!",
        "name": name,
    }
