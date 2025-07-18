from typing import Any


class Boto3HistoryHandler:
    """Holds events emitted during boto3 mocked calls."""

    def __init__(self):
        """Initialize the Boto3HistoryHandler with an empty events list."""
        self.events = []

    def emit(
        self,
        operation_name: str,
        payload: dict[str, Any],
        region: str,
        timeout: float,
        endpoint_url: str | None,
    ):
        """Record an emitted event with operation details."""
        self.events.append((operation_name, payload, region, timeout, endpoint_url))


history = Boto3HistoryHandler()
