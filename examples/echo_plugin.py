"""Echo Plugin — The simplest possible ZeroClaw plugin.

Accepts any JSON input and returns it unchanged. Great as a starting template.
"""

from zeroclaw_plugin_sdk import plugin_fn


@plugin_fn
def tool_echo(input):
    """Accepts any JSON object and returns it unchanged."""
    return input
