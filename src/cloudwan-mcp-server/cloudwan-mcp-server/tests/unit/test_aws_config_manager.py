

<Plan>
1. First replace the config_persistence import section with enhanced error handling and mock implementation
2. Update aws_config_manager tool to handle config persistence availability checks and mock scenarios
3. Add graceful degradation for config persistence operations
4. Improve error reporting when config_manager module is unavailable
</Plan>

<file path="/Users/taylaand/code/mcp/cloud-wan-mcp-server/mcp/src/cloudwan-mcp-server/cloudwan-mcp-server/awslabs/cloudwan_mcp_server/server.py" action="modify">
  
