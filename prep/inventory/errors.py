"""Common exceptions used by the inventory domain."""


class ConnectorError(RuntimeError):
    """Raised when a third-party inventory connector fails to fetch data."""

    def __init__(self, system: str, message: str, *, status_code: int | None = None) -> None:
        self.system = system
        self.status_code = status_code
        detail = message
        if status_code is not None:
            detail = f"{message} (status={status_code})"
        super().__init__(detail)


__all__ = ["ConnectorError"]
