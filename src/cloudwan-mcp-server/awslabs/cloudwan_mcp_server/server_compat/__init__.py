# Compatibility shim to support imports like:
#   awslabs.cloudwan_mcp_server.server.server.get_aws_client
# The actual implementation historically lived in awslabs.cloudwan_mcp_server.server (a module).
# We re-export everything here so both package and module forms work.
from ..server import *  # noqa: F401,F403
