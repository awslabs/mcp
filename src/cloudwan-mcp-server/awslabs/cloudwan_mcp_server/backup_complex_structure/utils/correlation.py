"""
Correlation ID system for request tracing in CloudWAN MCP Server.

This module provides a correlation ID context management system for tracing
requests across asynchronous operations, AWS API calls, and component boundaries.
"""

import asyncio
import contextvars
import functools
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar

# Setup module logger
logger = logging.getLogger(__name__)

# Create context variables for storing correlation information
# These will be propagated automatically across async tasks
correlation_id = contextvars.ContextVar("correlation_id", default=None)
request_path = contextvars.ContextVar("request_path", default=None)
request_start_time = contextvars.ContextVar("request_start_time", default=None)
parent_correlation_id = contextvars.ContextVar("parent_correlation_id", default=None)
operation_name = contextvars.ContextVar("operation_name", default=None)
operation_context = contextvars.ContextVar("operation_context", default={})

# Type variable for function return type
T = TypeVar("T")


class CorrelationSource(Enum):
    """Source of a correlation ID."""

    NEW = "new"  # Generated new ID
    PARENT = "parent"  # Inherited from parent context
    EXTERNAL = "external"  # Provided externally (e.g. from HTTP header)


@dataclass
class SpanContext:
    """Context for a tracing span within a request."""

    span_id: str
    parent_span_id: Optional[str] = None
    span_name: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)

    def add_event(self, name: str, **attributes: Any) -> None:
        """Add an event to this span."""
        self.events.append({"name": name, "timestamp": time.time(), "attributes": attributes})

    def end(self) -> None:
        """Mark the span as ended."""
        self.end_time = time.time()

    @property
    def duration_ms(self) -> Optional[float]:
        """Get the span duration in milliseconds."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000


class CorrelationContext:
    """
    Context manager for tracking correlation IDs across asynchronous operations.

    This class provides a way to propagate correlation IDs and other context
    information across asynchronous boundaries, making it possible to trace
    requests through different components of the system.

    Correlation context can be created in three ways:
    1. Generate a new correlation ID (default)
    2. Inherit from a parent context
    3. Use an externally provided correlation ID

    Example usage:
    ```python
    async def handle_request(request):
        # Create a new correlation context
        with CorrelationContext(operation_name="handle_request") as ctx:
            # Log with correlation ID
            logger.info(f"Handling request {request.id}")

            # The correlation ID is now set in the current context
            # and will be propagated to any async tasks created here
            result = await process_request(request)

            # Add attributes to the context
            ctx.add_attribute("status_code", 200)

            return result
    ```

    For AWS API calls, the correlation ID will be automatically added to
    request headers when using the AWSClientManager.
    """

    _active_spans: Dict[str, SpanContext] = {}
    _thread_local = threading.local()

    def __init__(
        self,
        correlation_id_value: Optional[str] = None,
        operation_name_value: Optional[str] = None,
        parent_id: Optional[str] = None,
        path: Optional[str] = None,
        context_attributes: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a new correlation context.

        Args:
            correlation_id_value: Optional correlation ID to use
            operation_name_value: Name of the operation being performed
            parent_id: Optional parent correlation ID
            path: Optional request path
            context_attributes: Optional initial context attributes
        """
        self.previous_correlation_id = None
        self.previous_parent_id = None
        self.previous_operation_name = None
        self.previous_request_path = None
        self.previous_start_time = None
        self.previous_context = None
        self.source = CorrelationSource.NEW

        # Store values to set when entering context
        self._correlation_id = correlation_id_value or f"corr-{uuid.uuid4()}"
        self._parent_id = parent_id
        self._operation = operation_name_value
        self._path = path
        self._context_attrs = context_attributes or {}

        # Span tracking
        self._span_id = f"span-{uuid.uuid4().hex[:8]}"
        self._parent_span_id = None

    def __enter__(self):
        """Enter the correlation context."""
        # Save current values for restoration later
        self.previous_correlation_id = correlation_id.get()
        self.previous_parent_id = parent_correlation_id.get()
        self.previous_operation_name = operation_name.get()
        self.previous_request_path = request_path.get()
        self.previous_start_time = request_start_time.get()
        self.previous_context = operation_context.get()

        # Determine correlation ID source
        if self._correlation_id:
            self.source = CorrelationSource.EXTERNAL
        elif self.previous_correlation_id:
            self._correlation_id = self.previous_correlation_id
            self.source = CorrelationSource.PARENT
            if not self._parent_id:
                self._parent_id = self.previous_parent_id

        # Set new context values
        correlation_id.set(self._correlation_id)
        parent_correlation_id.set(self._parent_id)

        # Set operation name if provided, otherwise keep existing
        if self._operation:
            operation_name.set(self._operation)

        # Set path if provided, otherwise keep existing
        if self._path:
            request_path.set(self._path)

        # Set start time if not already set
        if not request_start_time.get():
            request_start_time.set(time.time())

        # Merge context attributes
        current_context = operation_context.get().copy()
        current_context.update(self._context_attrs)
        operation_context.set(current_context)

        # Create and track span
        parent_span = self._get_current_span()
        if parent_span:
            self._parent_span_id = parent_span.span_id

        span = SpanContext(
            span_id=self._span_id,
            parent_span_id=self._parent_span_id,
            span_name=self._operation or "unknown",
            attributes=current_context,
        )
        self._active_spans[self._span_id] = span
        self._set_current_span(span)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the correlation context."""
        # End current span
        current_span = self._get_current_span()
        if current_span:
            current_span.end()
            if exc_type:
                current_span.add_event(
                    "exception",
                    exception_type=exc_type.__name__,
                    exception_message=str(exc_val),
                )

        # Restore previous values
        if self.previous_correlation_id is not None:
            correlation_id.set(self.previous_correlation_id)
        if self.previous_parent_id is not None:
            parent_correlation_id.set(self.previous_parent_id)
        if self.previous_operation_name is not None:
            operation_name.set(self.previous_operation_name)
        if self.previous_request_path is not None:
            request_path.set(self.previous_request_path)
        if self.previous_start_time is not None:
            request_start_time.set(self.previous_start_time)
        if self.previous_context is not None:
            operation_context.set(self.previous_context)

        # Restore parent span as current
        if self._parent_span_id:
            parent_span = self._active_spans.get(self._parent_span_id)
            if parent_span:
                self._set_current_span(parent_span)

    async def __aenter__(self):
        """Enter the correlation context in async context."""
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the correlation context in async context."""
        return self.__exit__(exc_type, exc_val, exc_tb)

    def add_attribute(self, key: str, value: Any) -> None:
        """Add an attribute to the current operation context."""
        current_context = operation_context.get().copy()
        current_context[key] = value
        operation_context.set(current_context)

        # Update span attributes too
        current_span = self._get_current_span()
        if current_span:
            current_span.attributes[key] = value

    def add_event(self, name: str, **attributes: Any) -> None:
        """Add an event to the current span."""
        current_span = self._get_current_span()
        if current_span:
            current_span.add_event(name, **attributes)

    @property
    def correlation_id(self) -> str:
        """Get the current correlation ID."""
        return self._correlation_id

    @property
    def operation(self) -> Optional[str]:
        """Get the current operation name."""
        return self._operation

    @property
    def attributes(self) -> Dict[str, Any]:
        """Get the current operation attributes."""
        return operation_context.get().copy()

    @staticmethod
    def current_correlation_id() -> Optional[str]:
        """Get the current correlation ID from context."""
        return correlation_id.get()

    @staticmethod
    def current_operation_name() -> Optional[str]:
        """Get the current operation name from context."""
        return operation_name.get()

    @staticmethod
    def current_request_path() -> Optional[str]:
        """Get the current request path from context."""
        return request_path.get()

    @staticmethod
    def current_context_attributes() -> Dict[str, Any]:
        """Get the current context attributes."""
        return operation_context.get().copy()

    @staticmethod
    def get_request_duration_ms() -> Optional[float]:
        """
        Get the duration of the current request in milliseconds.

        Returns:
            Duration in milliseconds, or None if no start time is set
        """
        start = request_start_time.get()
        if start is None:
            return None

        return (time.time() - start) * 1000

    def _get_current_span(self) -> Optional[SpanContext]:
        """Get the current span for this thread/task."""
        thread_id = threading.get_ident()
        task = asyncio.current_task()
        key = f"{thread_id}-{id(task) if task else 'sync'}"

        if not hasattr(self._thread_local, "spans"):
            self._thread_local.spans = {}

        return self._thread_local.spans.get(key)

    def _set_current_span(self, span: SpanContext) -> None:
        """Set the current span for this thread/task."""
        thread_id = threading.get_ident()
        task = asyncio.current_task()
        key = f"{thread_id}-{id(task) if task else 'sync'}"

        if not hasattr(self._thread_local, "spans"):
            self._thread_local.spans = {}

        self._thread_local.spans[key] = span


def with_correlation(f: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to ensure a function runs within a correlation context.

    If a correlation context already exists, it will be reused.
    Otherwise, a new one will be created.

    Args:
        f: Function to decorate

    Returns:
        Decorated function that ensures a correlation context
    """

    @functools.wraps(f)
    def sync_wrapper(*args: Any, **kwargs: Any) -> T:
        current_id = correlation_id.get()
        if current_id is not None:
            # Already in a correlation context
            return f(*args, **kwargs)

        # Create a new correlation context
        with CorrelationContext(operation_name=f.__name__) as ctx:
            logger.debug(f"Created correlation context: {ctx.correlation_id} for {f.__name__}")
            return f(*args, **kwargs)

    @functools.wraps(f)
    async def async_wrapper(*args: Any, **kwargs: Any) -> T:
        current_id = correlation_id.get()
        if current_id is not None:
            # Already in a correlation context
            return await f(*args, **kwargs)

        # Create a new correlation context
        async with CorrelationContext(operation_name=f.__name__) as ctx:
            logger.debug(f"Created correlation context: {ctx.correlation_id} for {f.__name__}")
            return await f(*args, **kwargs)

    if asyncio.iscoroutinefunction(f):
        return async_wrapper
    return sync_wrapper


class CorrelationLogAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds correlation ID to log records.

    This adapter automatically adds the current correlation ID, operation name,
    and other relevant context information to log records when logging messages.

    Example usage:
    ```python
    logger = logging.getLogger(__name__)
    logger = CorrelationLogAdapter(logger)

    # Log with correlation context
    with CorrelationContext():
        logger.info("Processing request")  # Will include correlation ID
    ```
    """

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """Process log record to add correlation information."""
        # Get current context values
        corr_id = correlation_id.get()
        op_name = operation_name.get()

        # Skip if no correlation info is present
        if corr_id is None:
            return msg, kwargs

        # Create or update the 'extra' dictionary in kwargs
        if "extra" not in kwargs:
            kwargs["extra"] = {}

        # Add correlation information to extra
        kwargs["extra"]["correlation_id"] = corr_id
        if op_name:
            kwargs["extra"]["operation_name"] = op_name

        # Add request duration if available
        duration = CorrelationContext.get_request_duration_ms()
        if duration is not None:
            kwargs["extra"]["duration_ms"] = f"{duration:.2f}"

        # Add context attributes
        context_attrs = operation_context.get()
        if context_attrs:
            for key, value in context_attrs.items():
                if key not in kwargs["extra"]:
                    kwargs["extra"][key] = value

        return msg, kwargs


class CorrelationFilter(logging.Filter):
    """
    Logging filter that adds correlation information to log records.

    This filter can be added to any logger or handler to automatically
    add correlation ID, operation name, and other context information
    to log records even without using the CorrelationLogAdapter.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation information to the log record."""
        # Get current context values
        corr_id = correlation_id.get()
        op_name = operation_name.get()
        req_path = request_path.get()

        # Add correlation information if available
        if not hasattr(record, "correlation_id") and corr_id is not None:
            record.correlation_id = corr_id

        if not hasattr(record, "operation_name") and op_name is not None:
            record.operation_name = op_name

        if not hasattr(record, "request_path") and req_path is not None:
            record.request_path = req_path

        # Add request duration if available
        duration = CorrelationContext.get_request_duration_ms()
        if duration is not None and not hasattr(record, "duration_ms"):
            record.duration_ms = f"{duration:.2f}"

        # Add context attributes
        context_attrs = operation_context.get()
        if context_attrs:
            for key, value in context_attrs.items():
                if not hasattr(record, key):
                    setattr(record, key, value)

        return True


def create_correlation_id() -> str:
    """
    Create a new correlation ID.

    Returns:
        A unique correlation ID string
    """
    return f"corr-{uuid.uuid4().hex}"


def get_correlation_headers() -> Dict[str, str]:
    """
    Get HTTP headers with correlation information for the current context.

    These headers can be used to propagate correlation information across
    service boundaries.

    Returns:
        Dictionary of HTTP headers with correlation information
    """
    headers = {}

    corr_id = correlation_id.get()
    if corr_id:
        headers["X-Correlation-ID"] = corr_id

    parent_id = parent_correlation_id.get()
    if parent_id:
        headers["X-Parent-Correlation-ID"] = parent_id

    op = operation_name.get()
    if op:
        headers["X-Operation-Name"] = op

    return headers


def setup_correlation_logging() -> None:
    """
    Configure the default root logger with correlation ID support.

    This function adds a CorrelationFilter to the root logger to ensure
    correlation information is included in all log records.

    It also sets up a custom formatter that includes correlation information
    in the log output format.
    """
    root_logger = logging.getLogger()

    # Add correlation filter to root logger if not already added
    for filter in root_logger.filters:
        if isinstance(filter, CorrelationFilter):
            return  # Already configured

    # Add filter to root logger
    correlation_filter = CorrelationFilter()
    root_logger.addFilter(correlation_filter)

    # Configure handlers with correlation formatter
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(correlation_id)s] " "[%(name)s] %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    for handler in root_logger.handlers:
        handler.setFormatter(formatter)
