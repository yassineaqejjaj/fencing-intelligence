from typing import Any


class AppError(Exception):
    def __init__(self, code: str, status_code: int, message: str, details: dict[str, Any] | None = None):
        self.code = code
        self.status_code = status_code
        self.message = message
        self.details = details or {}
        super().__init__(message)
