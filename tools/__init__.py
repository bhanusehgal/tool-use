"""The agent's tools. Each one is a plain Python function that knows nothing about LLMs."""


class ToolError(Exception):
    """A tool failed in an expected way (bad input, no results...).

    The agent loop catches this and sends the message back to the model as an
    error result, so the model can try again instead of the program crashing.
    """
