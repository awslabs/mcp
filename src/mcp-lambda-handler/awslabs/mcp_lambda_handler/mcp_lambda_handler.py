from enum import Enum
import functools
import inspect
import json
import logging
from awslabs.mcp_lambda_handler.session import DynamoDBSessionStore, NoOpSessionStore, SessionStore
from awslabs.mcp_lambda_handler.types import (
    Capabilities,
    ErrorContent,
    InitializeResult,
    JSONRPCError,
    JSONRPCRequest,
    JSONRPCResponse,
    ServerInfo,
    TextContent,
)
from contextvars import ContextVar
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar, Union, get_type_hints


logger = logging.getLogger(__name__)

# Context variable to store current session ID
current_session_id: ContextVar[Optional[str]] = ContextVar('current_session_id', default=None)

T = TypeVar('T')


class SessionData(Generic[T]):
    """Helper class for type-safe session data access."""

    def __init__(self, data: Dict[str, Any]):
        """Initialize the class."""
        self._data = data

    def get(self, key: str, default: T = None) -> T:
        """Get a value from session data with type safety."""
        return self._data.get(key, default)

    def set(self, key: str, value: T) -> None:
        """Set a value in session data."""
        self._data[key] = value

    def raw(self) -> Dict[str, Any]:
        """Get the raw dictionary data."""
        return self._data


class MCPLambdaHandler:
    """A class to handle MCP (Model Context Protocol) HTTP events in AWS Lambda."""

    def __init__(
        self,
        name: str,
        version: str = '1.0.0',
        session_store: Optional[Union[SessionStore, str]] = None,
    ):
        """Initialize the MCP handler.

        Args:
            name: Handler name
            version: Handler version
            session_store: Optional session storage. Can be:
                         - None for no sessions
                         - A SessionStore instance
                         - A string for DynamoDB table name (for backwards compatibility)

        """
        self.name = name
        self.version = version
        self.tools: Dict[str, Dict] = {}
        self.tool_implementations: Dict[str, Callable] = {}

        # Configure session storage
        if session_store is None:
            self.session_store = NoOpSessionStore()
        elif isinstance(session_store, str):
            # Backwards compatibility - treat string as DynamoDB table name
            self.session_store = DynamoDBSessionStore(table_name=session_store)
        else:
            self.session_store = session_store

    def get_session(self) -> Optional[SessionData]:
        """Get the current session data wrapper.

        Returns:
            SessionData object or None if no session exists

        """
        session_id = current_session_id.get()
        if not session_id:
            return None
        data = self.session_store.get_session(session_id)
        return SessionData(data) if data is not None else None

    def set_session(self, data: Dict[str, Any]) -> bool:
        """Set the entire session data.

        Args:
            data: New session data

        Returns:
            True if successful, False if no session exists

        """
        session_id = current_session_id.get()
        if not session_id:
            return False
        return self.session_store.update_session(session_id, data)

    def update_session(self, updater_func: Callable[[SessionData], None]) -> bool:
        """Update session data using a function.

        Args:
            updater_func: Function that takes SessionData and updates it in place

        Returns:
            True if successful, False if no session exists

        """
        session = self.get_session()
        if not session:
            return False

        # Update the session data
        updater_func(session)

        # Save back to storage
        return self.set_session(session.raw())

    def tool(self):
        """Create a decorator for a function as an MCP tool.

        Uses function name, docstring, and type hints to generate the MCP tool schema.
        """

        def decorator(func: Callable):
            # Get function name and convert to camelCase for tool name
            func_name = func.__name__
            tool_name = ''.join(
                [func_name.split('_')[0]]
                + [word.capitalize() for word in func_name.split('_')[1:]]
            )

            # Get docstring and parse into description
            doc = inspect.getdoc(func) or ''
            description = doc.split('\n\n')[0]  # First paragraph is description

            # Get type hints
            hints = get_type_hints(func)
            # return_type = hints.pop('return', Any)
            hints.pop('return', Any)

            # Build input schema from type hints and docstring
            properties = {}
            required = []

            # Parse docstring for argument descriptions
            arg_descriptions = {}
            if doc:
                lines = doc.split('\n')
                in_args = False
                for line in lines:
                    if line.strip().startswith('Args:'):
                        in_args = True
                        continue
                    if in_args:
                        if not line.strip() or line.strip().startswith('Returns:'):
                            break
                        if ':' in line:
                            arg_name, arg_desc = line.split(':', 1)
                            arg_descriptions[arg_name.strip()] = arg_desc.strip()

            # Build properties from type hints
            for param_name, param_type in hints.items():
                param_schema = {'type': 'string'}  # Default to string
                if param_type is int:
                    param_schema['type'] = 'integer'
                elif param_type is float:
                    param_schema['type'] = 'number'
                elif param_type is bool:
                    param_schema['type'] = 'boolean'
                elif isinstance(param_type, type) and issubclass(param_type, Enum):
                    param_schema["type"] = "string"
                    param_schema["enum"] = [e.value for e in param_type]

                if param_name in arg_descriptions:
                    param_schema['description'] = arg_descriptions[param_name]

                properties[param_name] = param_schema
                required.append(param_name)

            # Create tool schema
            tool_schema = {
                'name': tool_name,
                'description': description,
                'inputSchema': {'type': 'object', 'properties': properties, 'required': required},
            }

            # Register the tool
            self.tools[tool_name] = tool_schema
            self.tool_implementations[tool_name] = func

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper

        return decorator

    def _create_error_response(
        self,
        code: int,
        message: str,
        request_id: Optional[str] = None,
        error_content: Optional[List[Dict]] = None,
        session_id: Optional[str] = None,
        status_code: Optional[int] = None,
    ) -> Dict:
        """Create a standardized error response."""
        error = JSONRPCError(code=code, message=message)
        response = JSONRPCResponse(
            jsonrpc='2.0', id=request_id, error=error, errorContent=error_content
        )

        headers = {'Content-Type': 'application/json', 'MCP-Version': '0.6'}
        if session_id:
            headers['MCP-Session-Id'] = session_id

        return {
            'statusCode': status_code or self._error_code_to_http_status(code),
            'body': response.model_dump_json(),
            'headers': headers,
        }

    def _error_code_to_http_status(self, error_code: int) -> int:
        """Map JSON-RPC error codes to HTTP status codes."""
        error_map = {
            -32700: 400,  # Parse error
            -32600: 400,  # Invalid Request
            -32601: 404,  # Method not found
            -32602: 400,  # Invalid params
            -32603: 500,  # Internal error
        }
        return error_map.get(error_code, 500)

    def _create_success_response(
        self, result: Any, request_id: str | None, session_id: Optional[str] = None
    ) -> Dict:
        """Create a standardized success response."""
        response = JSONRPCResponse(jsonrpc='2.0', id=request_id, result=result)

        headers = {'Content-Type': 'application/json', 'MCP-Version': '0.6'}
        if session_id:
            headers['MCP-Session-Id'] = session_id

        return {'statusCode': 200, 'body': response.model_dump_json(), 'headers': headers}

    def handle_request(self, event: Dict, context: Any) -> Dict:
        """Handle an incoming Lambda request."""
        request_id = None
        session_id = None

        try:
            # Log the full event for debugging
            logger.debug(f'Received event: {event}')

            # Get headers (case-insensitive)
            headers = {k.lower(): v for k, v in event.get('headers', {}).items()}

            # Get session ID from headers if present
            session_id = headers.get('mcp-session-id')

            # Set current session ID in context
            if session_id:
                current_session_id.set(session_id)
            else:
                current_session_id.set(None)

            # Check HTTP method for session deletion
            if event.get('httpMethod') == 'DELETE' and session_id:
                if self.session_store.delete_session(session_id):
                    return {'statusCode': 204}
                else:
                    return {'statusCode': 404}

            # Validate content type
            if headers.get('content-type') != 'application/json':
                return self._create_error_response(-32700, 'Unsupported Media Type')

            try:
                body = json.loads(event['body'])
                logger.debug(f'Parsed request body: {body}')
                request_id = body.get('id') if isinstance(body, dict) else None

                # Check if this is a notification (no id field)
                if isinstance(body, dict) and 'id' not in body:
                    logger.debug('Request is a notification')
                    return {
                        'statusCode': 204,
                        'body': '',
                        'headers': {'Content-Type': 'application/json', 'MCP-Version': '0.6'},
                    }

                # Validate basic JSON-RPC structure
                if (
                    not isinstance(body, dict)
                    or body.get('jsonrpc') != '2.0'
                    or 'method' not in body
                ):
                    return self._create_error_response(-32700, 'Parse error', request_id)

            except json.JSONDecodeError:
                return self._create_error_response(-32700, 'Parse error')

            # Parse and validate the request
            request = JSONRPCRequest.model_validate(body)
            logger.debug(f'Validated request: {request}')

            # Handle initialization request
            if request.method == 'initialize':
                logger.info('Handling initialize request')
                # Create new session
                session_id = self.session_store.create_session()
                current_session_id.set(session_id)
                result = InitializeResult(
                    protocolVersion='2024-11-05',
                    serverInfo=ServerInfo(name=self.name, version=self.version),
                    capabilities=Capabilities(tools={'list': True, 'call': True}),
                )
                return self._create_success_response(result.model_dump(), request.id, session_id)

            # For all other requests, validate session if provided
            if session_id:
                session_data = self.session_store.get_session(session_id)
                if session_data is None:
                    return self._create_error_response(
                        -32000, 'Invalid or expired session', request.id, status_code=404
                    )
            elif request.method != 'initialize' and not isinstance(
                self.session_store, NoOpSessionStore
            ):
                return self._create_error_response(
                    -32000, 'Session required', request.id, status_code=400
                )

            # Handle tools/list request
            if request.method == 'tools/list':
                logger.info('Handling tools/list request')
                return self._create_success_response(
                    {'tools': list(self.tools.values())}, request.id, session_id
                )

            # Handle tool calls
            if request.method == 'tools/call' and request.params:
                tool_name = request.params.get('name')
                tool_args = request.params.get('arguments', {})

                if tool_name not in self.tools:
                    return self._create_error_response(
                        -32601, f"Tool '{tool_name}' not found", request.id, session_id=session_id
                    )

                try:
                    # Convert enum string values to enum objects
                    converted_args = {}
                    tool_func = self.tool_implementations[tool_name]
                    hints = get_type_hints(tool_func)

                    for arg_name, arg_value in tool_args.items():
                        arg_type = hints.get(arg_name)
                        if isinstance(arg_type, type) and issubclass(arg_type, Enum):
                            converted_args[arg_name] = arg_type(arg_value)
                        else:
                            converted_args[arg_name] = arg_value

                    result = tool_func(**converted_args)
                    content = [TextContent(text=str(result)).model_dump()]
                    return self._create_success_response(
                        {'content': content}, request.id, session_id
                    )
                except Exception as e:
                    logger.error(f'Error executing tool {tool_name}: {e}')
                    error_content = [ErrorContent(text=str(e)).model_dump()]
                    return self._create_error_response(
                        -32603,
                        f'Error executing tool: {str(e)}',
                        request.id,
                        error_content,
                        session_id,
                    )
            
            # Hanlde pings
            if request.method == "ping":
                return self._create_success_response({}, request.id, session_id)

            # Handle unknown methods
            return self._create_error_response(
                -32601, f'Method not found: {request.method}', request.id, session_id=session_id
            )

        except Exception as e:
            logger.error(f'Error processing request: {str(e)}', exc_info=True)
            return self._create_error_response(-32000, str(e), request_id, session_id=session_id)
        finally:
            # Clear session context
            current_session_id.set(None)
