"""
Custom exceptions for the API layer.
"""


class EngineError(Exception):
    """Raised when the rule engine encounters an internal error."""

    def __init__(self, detail: str = "Rule engine encountered an internal error"):
        self.detail = detail
        super().__init__(self.detail)


class InvalidInputError(Exception):
    """Raised when input data is invalid or empty."""

    def __init__(self, detail: str = "Invalid input data"):
        self.detail = detail
        super().__init__(self.detail)
