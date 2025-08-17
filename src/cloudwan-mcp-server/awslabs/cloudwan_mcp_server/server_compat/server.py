# Compatibility shim module to satisfy imports of:
#   awslabs.cloudwan_mcp_server.server.server
# Delegate all symbols to the historical module location.
from ..server import *  # noqa: F401,F403
