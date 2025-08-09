# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Configuration management tools for AWS CloudWAN MCP Server."""

from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

from ..server import aws_config, handle_aws_error, safe_json_dumps
from ..tools.base import AWSBaseTool


class ConfigurationTools:
    """Collection of configuration management tools for CloudWAN."""
    
    def __init__(self, mcp_server: FastMCP) -> None:
        """Initialize configuration tools.
        
        Args:
            mcp_server: FastMCP server instance
        """
        self.mcp = mcp_server
        self._register_tools()
    
    def _register_tools(self) -> None:
        """Register all configuration tools with the MCP server."""
        # Register validate_cloudwan_policy tool
        @self.mcp.tool(name="validate_cloudwan_policy")
        async def validate_cloudwan_policy(policy_document: dict) -> str:
            """Validate CloudWAN policy configurations."""
            return await self._validate_cloudwan_policy(policy_document)
        
        # Register aws_config_manager tool (imported from original server)
        @self.mcp.tool(name="aws_config_manager")
        async def aws_config_manager(operation: str, profile: str | None = None, region: str | None = None) -> str:
            """Manage AWS configuration settings dynamically without server restart."""
            return await self._aws_config_manager(operation, profile, region)

    async def _validate_cloudwan_policy(self, policy_document: dict) -> str:
        """Internal implementation for CloudWAN policy validation."""
        try:
            # Basic policy validation
            required_fields = ["version", "core-network-configuration"]
            validation_results = []

            for field in required_fields:
                if field in policy_document:
                    validation_results.append(
                        {"field": field, "status": "valid", "message": f"Required field '{field}' is present"}
                    )
                else:
                    validation_results.append(
                        {"field": field, "status": "invalid", "message": f"Required field '{field}' is missing"}
                    )

            overall_valid = all(r["status"] == "valid" for r in validation_results)

            result = {
                "success": True,
                "validation_results": validation_results,
                "overall_status": "valid" if overall_valid else "invalid",
                "policy_version": policy_document.get("version", "unknown"),
            }

            return safe_json_dumps(result, indent=2)

        except Exception as e:
            return handle_aws_error(e, "validate_cloudwan_policy")

    async def _aws_config_manager(self, operation: str, profile: str | None = None, region: str | None = None) -> str:
        """Internal implementation for AWS configuration management.
        
        This is imported from the original server implementation to maintain compatibility.
        """
        try:
            # Import the aws_config_manager function from the original server
            from ..server import aws_config_manager as original_aws_config_manager
            
            # Call the original implementation
            return await original_aws_config_manager(operation, profile, region)
            
        except Exception as e:
            return handle_aws_error(e, "aws_config_manager")