"""
MCP Protocol Handler Module.

This module provides the MCPProtocolHandler class for managing MCP protocol
operations including request/response handling, error management, and
protocol compliance validation.
"""

import logging
from typing import Any, Dict, List, Optional, Callable, Union

# Import with fallback for different import contexts
try:
    from error_mapping import MCPError, MCPErrorCode, map_aws_error_to_mcp
    from negotiation import (
        ProtocolNegotiator,
        ProtocolConfiguration,
        get_protocol_negotiator,
        get_compliance_checker,
    )
    from heartbeat import MCPHeartbeatManager
except ImportError:
    try:
        from .error_mapping import MCPError, MCPErrorCode, map_aws_error_to_mcp
        from .negotiation import (
            ProtocolNegotiator,
            ProtocolConfiguration,
            get_protocol_negotiator,
            get_compliance_checker,
        )
        from .heartbeat import MCPHeartbeatManager
    except ImportError:
        # Fallback when dependencies not available
        MCPError = Exception
        MCPErrorCode = None
        ProtocolNegotiator = None
        ProtocolConfiguration = None
        MCPHeartbeatManager = None

        def map_aws_error_to_mcp(*args, **kwargs):
            return Exception("Protocol handler dependencies not available")

        def get_protocol_negotiator():
            return None

        def get_compliance_checker():
            return None


logger = logging.getLogger(__name__)


class MCPProtocolHandler:
    """
    MCP Protocol Handler for managing protocol operations.

    Handles:
    - Request/response processing
    - Error handling and mapping
    - Protocol compliance validation
    - Heartbeat management
    - Version negotiation coordination
    """

    def __init__(
        self,
        server_name: str = "CloudWAN-MCP",
        server_version: str = "1.0.0",
        enable_heartbeat: bool = True,
        heartbeat_interval: int = 30,
    ):
        """
        Initialize MCP Protocol Handler.

        Args:
            server_name: Name of the MCP server
            server_version: Version of the MCP server
            enable_heartbeat: Whether to enable heartbeat management
            heartbeat_interval: Heartbeat interval in seconds
        """
        self.server_name = server_name
        self.server_version = server_version
        self.enable_heartbeat = enable_heartbeat

        # Initialize protocol negotiator
        self.negotiator = ProtocolNegotiator(server_name, server_version)
        self.protocol_config: Optional[ProtocolConfiguration] = None

        # Initialize heartbeat manager if enabled
        self.heartbeat_manager = None
        if enable_heartbeat and MCPHeartbeatManager:
            try:
                self.heartbeat_manager = MCPHeartbeatManager(
                    server_name=server_name, heartbeat_interval=heartbeat_interval
                )
            except Exception as e:
                logger.warning(f"Failed to initialize heartbeat manager: {e}")
                self.heartbeat_manager = None

        # Request handlers
        self.request_handlers: Dict[str, Callable] = {}
        self.middleware_stack: List[Callable] = []

        logger.info(f"MCP Protocol Handler initialized for {server_name} v{server_version}")

    def register_handler(self, method: str, handler: Callable) -> None:
        """
        Register a handler for a specific MCP method.

        Args:
            method: MCP method name (e.g., 'tools/list', 'tools/call')
            handler: Handler function
        """
        self.request_handlers[method] = handler
        logger.debug(f"Registered handler for method: {method}")

    def add_middleware(self, middleware: Callable) -> None:
        """
        Add middleware to the processing stack.

        Args:
            middleware: Middleware function
        """
        self.middleware_stack.append(middleware)
        logger.debug("Added middleware to protocol handler")

    async def negotiate_protocol(
        self,
        client_versions: List[str],
        client_capabilities: Optional[Dict[str, Any]] = None,
        client_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Negotiate protocol with client.

        Args:
            client_versions: Versions supported by client
            client_capabilities: Capabilities requested by client
            client_context: Additional client context for audit logging

        Returns:
            Protocol negotiation response
        """
        try:
            # Extract context for audit logging
            client_ip = client_context.get("client_ip") if client_context else None
            user_agent = client_context.get("user_agent") if client_context else None
            security_level = (
                client_context.get("security_level", "development")
                if client_context
                else "development"
            )

            # Negotiate protocol
            self.protocol_config = self.negotiator.negotiate_protocol(
                client_supported_versions=client_versions,
                client_capabilities=client_capabilities,
                client_ip=client_ip,
                user_agent=user_agent,
                security_level=security_level,
            )

            # Start heartbeat if enabled and supported
            if (
                self.heartbeat_manager
                and self.protocol_config.capabilities.supports_progress_reporting
            ):
                await self.heartbeat_manager.start()

            return {
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": self.protocol_config.version,
                    "capabilities": {
                        "tools": {"listChanged": True},
                        "resources": {
                            "subscribe": self.protocol_config.capabilities.supports_resource_subscriptions
                        },
                        "prompts": {"listChanged": False},
                        "streaming": self.protocol_config.capabilities.supports_streaming,
                        "progress": self.protocol_config.capabilities.supports_progress_reporting,
                    },
                    "serverInfo": {
                        "name": self.protocol_config.server_name,
                        "version": self.protocol_config.server_version,
                    },
                },
            }

        except Exception as e:
            logger.error(f"Protocol negotiation failed: {e}")
            return self._create_error_response(
                error_code=MCPErrorCode.INTERNAL_ERROR,
                message=f"Protocol negotiation failed: {str(e)}",
            )

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming MCP request.

        Args:
            request: MCP request

        Returns:
            MCP response
        """
        try:
            # Validate protocol negotiation
            if not self.protocol_config:
                return self._create_error_response(
                    request_id=request.get("id"),
                    error_code=MCPErrorCode.INVALID_REQUEST,
                    message="Protocol not negotiated",
                )

            # Validate request format
            if not self.negotiator.validate_request(request):
                return self._create_error_response(
                    request_id=request.get("id"),
                    error_code=MCPErrorCode.INVALID_REQUEST,
                    message="Invalid request format",
                )

            # Apply middleware
            for middleware in self.middleware_stack:
                request = await middleware(request) if hasattr(middleware, "__call__") else request

            # Get method and handler
            method = request.get("method")
            if not method:
                return self._create_error_response(
                    request_id=request.get("id"),
                    error_code=MCPErrorCode.INVALID_REQUEST,
                    message="Missing method field",
                )

            handler = self.request_handlers.get(method)
            if not handler:
                return self._create_error_response(
                    request_id=request.get("id"),
                    error_code=MCPErrorCode.METHOD_NOT_FOUND,
                    message=f"Method not found: {method}",
                )

            # Call handler
            result = await handler(request.get("params", {}))

            # Create success response
            response = {"jsonrpc": "2.0", "id": request.get("id"), "result": result}

            # Validate response compliance
            compliance_checker = get_compliance_checker()
            if compliance_checker:
                compliance_checker.check_response_compliance(response)

            return response

        except MCPError as e:
            return self._create_error_response(
                request_id=request.get("id"),
                error_code=e.code,
                message=e.message,
                data=e.data,
            )

        except Exception as e:
            logger.error(f"Request handling failed: {e}")

            # Try to map AWS errors
            mcp_error = map_aws_error_to_mcp(e)

            return self._create_error_response(
                request_id=request.get("id"),
                error_code=mcp_error.code,
                message=mcp_error.message,
                data=mcp_error.data,
            )

    def _create_error_response(
        self,
        request_id: Optional[Union[str, int]] = None,
        error_code: MCPErrorCode = MCPErrorCode.INTERNAL_ERROR,
        message: str = "Internal error",
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create standardized MCP error response.

        Args:
            request_id: Request ID
            error_code: MCP error code
            message: Error message
            data: Additional error data

        Returns:
            MCP error response
        """
        error_response = {
            "jsonrpc": "2.0",
            "error": {"code": error_code.value, "message": message},
        }

        if request_id is not None:
            error_response["id"] = request_id

        if data:
            error_response["error"]["data"] = data

        return error_response

    async def handle_notification(self, notification: Dict[str, Any]) -> None:
        """
        Handle incoming MCP notification.

        Args:
            notification: MCP notification
        """
        try:
            method = notification.get("method")
            params = notification.get("params", {})

            logger.debug(f"Received notification: {method}")

            # Handle standard notifications
            if method == "notifications/cancelled":
                # Handle request cancellation
                request_id = params.get("requestId")
                if request_id:
                    logger.info(f"Request cancelled: {request_id}")

            elif method == "notifications/progress":
                # Handle progress updates
                progress_token = params.get("progressToken")
                progress = params.get("progress", 0)
                total = params.get("total", 100)
                logger.debug(f"Progress update {progress_token}: {progress}/{total}")

        except Exception as e:
            logger.error(f"Notification handling failed: {e}")

    def get_protocol_info(self) -> Dict[str, Any]:
        """
        Get current protocol information.

        Returns:
            Protocol information
        """
        base_info = self.negotiator.get_protocol_info()

        # Add handler information
        base_info["registered_methods"] = list(self.request_handlers.keys())
        base_info["middleware_count"] = len(self.middleware_stack)

        # Add heartbeat information
        if self.heartbeat_manager:
            base_info["heartbeat"] = {
                "enabled": True,
                "interval": self.heartbeat_manager.interval,
                "is_running": self.heartbeat_manager.is_running,
                "status": self.heartbeat_manager.get_status(),
            }

        return base_info

    async def shutdown(self) -> None:
        """Shutdown protocol handler and cleanup resources."""
        try:
            # Stop heartbeat manager
            if self.heartbeat_manager:
                await self.heartbeat_manager.stop()

            # Clear handlers
            self.request_handlers.clear()
            self.middleware_stack.clear()

            logger.info("MCP Protocol Handler shutdown complete")

        except Exception as e:
            logger.error(f"Error during protocol handler shutdown: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()
