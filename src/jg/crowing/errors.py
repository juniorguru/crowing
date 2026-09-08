"""Domain errors raised by the functional core."""


class InvalidInputError(ValueError):
    """Raised when the user passes a syntactically wrong handbook URL."""


class LLMError(RuntimeError):
    """Raised when no LLM provider is available or content generation fails."""
