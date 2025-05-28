"""Authentication package for OpenAPI MCP Server."""

# Import register module to auto-register providers
import awslabs.openapi_mcp_server.auth.register  # noqa: F401
from awslabs.openapi_mcp_server.auth.auth_factory import get_auth_provider, is_auth_type_available
from awslabs.openapi_mcp_server.auth.auth_provider import AuthProvider, NullAuthProvider

# Define public exports
__all__ = [
    'get_auth_provider',
    'is_auth_type_available',
    'AuthProvider',
    'NullAuthProvider',
]
