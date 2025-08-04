"""CloudWAN Policy Management Tools for MCP Server.

This module provides comprehensive tools for managing CloudWAN Core Network policies,
including policy retrieval, change set management, and change event tracking.
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from pydantic import Field

from mcp.types import CallToolResult, TextContent
from ...models.base import BaseResponse
from ..base import BaseMCPTool, handle_errors
from ...aws.client_manager import AWSClientManager
from ...config import CloudWANConfig


class CoreNetworkPolicyResponse(BaseResponse):
    """Response model for Core Network policy operations."""
    
    core_network_id: str
    policy_version_id: Optional[str] = None
    policy_document: Optional[Dict[str, Any]] = None
    creation_timestamp: Optional[str] = None
    description: Optional[str] = None


class CoreNetworkChangeSetResponse(BaseResponse):
    """Response model for Core Network change set operations."""
    
    core_network_id: str
    policy_version_id: str
    change_set_id: str
    change_set_state: str
    change_sets: List[Dict[str, Any]] = Field(default_factory=list)
    start_time: Optional[str] = None


class CoreNetworkChangeEventsResponse(BaseResponse):
    """Response model for Core Network change events."""
    
    core_network_id: str
    change_events: List[Dict[str, Any]] = Field(default_factory=list)
    max_results: int = 50
    next_token: Optional[str] = None


class GetCoreNetworkPolicyTool(BaseMCPTool):
    """Tool for retrieving Core Network policy documents."""
    
    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig = None):
        super().__init__(aws_manager, config or CloudWANConfig())
        self._tool_name = "get_core_network_policy"
        self._description = "Retrieve the policy document for a CloudWAN Core Network"

    @property
    def tool_name(self) -> str:
        return self._tool_name

    @property
    def description(self) -> str:
        return self._description

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "core_network_id": {
                    "type": "string",
                    "description": "Core Network ID to retrieve policy for",
                },
                "policy_version_id": {
                    "type": "string",
                    "description": "Specific policy version ID (optional - gets current if not specified)",
                },
                "alias": {
                    "type": "string", 
                    "description": "Policy version alias (LIVE or LATEST)",
                    "enum": ["LIVE", "LATEST"],
                },
            },
            "required": ["core_network_id"],
        }

    @handle_errors
    async def execute(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Execute Core Network policy retrieval."""
        core_network_id = arguments["core_network_id"]
        policy_version_id = arguments.get("policy_version_id")
        alias = arguments.get("alias")
        
        self.logger.info(f"Retrieving policy for Core Network: {core_network_id}")
        
        try:
            # NetworkManager is a global service, use us-west-2
            async with self.aws_manager.client_context("networkmanager", "us-west-2") as nm:
                # Build parameters
                params = {"CoreNetworkId": core_network_id}
                if policy_version_id:
                    params["PolicyVersionId"] = policy_version_id
                elif alias:
                    params["Alias"] = alias
                
                response = await nm.get_core_network_policy(**params)
                policy_info = response.get("CoreNetworkPolicy", {})
                
                # Parse policy document if it's a string
                policy_document = policy_info.get("PolicyDocument")
                if isinstance(policy_document, str):
                    policy_document = json.loads(policy_document)
                
                result = CoreNetworkPolicyResponse(
                    core_network_id=core_network_id,
                    policy_version_id=str(policy_info.get("PolicyVersionId")) if policy_info.get("PolicyVersionId") else None,
                    policy_document=policy_document,
                    creation_timestamp=policy_info.get("CreationTimestamp").isoformat() if policy_info.get("CreationTimestamp") else None,
                    description=policy_info.get("Description"),
                )
                
                return CallToolResult(
                    content=[TextContent(type="text", text=result.model_dump_json(indent=2))]
                )
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve Core Network policy: {e}")
            error_response = {
                "error": f"Failed to retrieve policy for Core Network {core_network_id}: {str(e)}",
                "core_network_id": core_network_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(error_response, indent=2))]
            )


class GetCoreNetworkChangeSetTool(BaseMCPTool):
    """Tool for retrieving Core Network policy change sets."""
    
    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig = None):
        super().__init__(aws_manager, config or CloudWANConfig())
        self._tool_name = "get_core_network_change_set"
        self._description = "Retrieve policy change sets for a CloudWAN Core Network"

    @property
    def tool_name(self) -> str:
        return self._tool_name

    @property
    def description(self) -> str:
        return self._description

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "core_network_id": {
                    "type": "string",
                    "description": "Core Network ID to retrieve change sets for",
                },
                "policy_version_id": {
                    "type": "string", 
                    "description": "Policy version ID for the change set",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of change sets to return",
                    "minimum": 1,
                    "maximum": 20,
                    "default": 10,
                },
                "next_token": {
                    "type": "string",
                    "description": "Token for pagination",
                },
            },
            "required": ["core_network_id", "policy_version_id"],
        }

    @handle_errors  
    async def execute(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Execute Core Network change set retrieval."""
        core_network_id = arguments["core_network_id"]
        policy_version_id = arguments["policy_version_id"]
        max_results = arguments.get("max_results", 10)
        next_token = arguments.get("next_token")
        
        self.logger.info(f"Retrieving change sets for Core Network: {core_network_id}, Policy: {policy_version_id}")
        
        try:
            async with self.aws_manager.client_context("networkmanager", "us-west-2") as nm:
                params = {
                    "CoreNetworkId": core_network_id,
                    "PolicyVersionId": policy_version_id,
                    "MaxResults": max_results,
                }
                if next_token:
                    params["NextToken"] = next_token
                
                response = await nm.get_core_network_change_set(**params)
                
                result = CoreNetworkChangeSetResponse(
                    core_network_id=core_network_id,
                    policy_version_id=policy_version_id,
                    change_set_id=response.get("CoreNetworkChanges", {}).get("ChangeSetId", ""),
                    change_set_state=response.get("CoreNetworkChanges", {}).get("ChangeSetState", ""),
                    change_sets=response.get("CoreNetworkChanges", []),
                    start_time=response.get("CoreNetworkChanges", {}).get("StartTime", "").isoformat() if response.get("CoreNetworkChanges", {}).get("StartTime") else None,
                )
                
                # Add pagination info if available
                if response.get("NextToken"):
                    result_dict = result.model_dump()
                    result_dict["next_token"] = response["NextToken"]
                    return CallToolResult(
                        content=[TextContent(type="text", text=json.dumps(result_dict, indent=2))]
                    )
                
                return CallToolResult(
                    content=[TextContent(type="text", text=result.model_dump_json(indent=2))]
                )
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve Core Network change sets: {e}")
            error_response = {
                "error": f"Failed to retrieve change sets for Core Network {core_network_id}: {str(e)}",
                "core_network_id": core_network_id,
                "policy_version_id": policy_version_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(error_response, indent=2))]
            )


class GetCoreNetworkChangeEventsTool(BaseMCPTool):
    """Tool for retrieving Core Network change events."""
    
    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig = None):
        super().__init__(aws_manager, config or CloudWANConfig())
        self._tool_name = "get_core_network_change_events"
        self._description = "Retrieve change events for a CloudWAN Core Network"

    @property
    def tool_name(self) -> str:
        return self._tool_name

    @property
    def description(self) -> str:
        return self._description

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "core_network_id": {
                    "type": "string",
                    "description": "Core Network ID to retrieve change events for",
                },
                "policy_version_id": {
                    "type": "string",
                    "description": "Policy version ID to filter events",
                },
                "max_results": {
                    "type": "integer", 
                    "description": "Maximum number of events to return",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 20,
                },
                "next_token": {
                    "type": "string",
                    "description": "Token for pagination",
                },
            },
            "required": ["core_network_id", "policy_version_id"],
        }

    @handle_errors
    async def execute(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Execute Core Network change events retrieval."""
        core_network_id = arguments["core_network_id"]
        policy_version_id = arguments["policy_version_id"]
        max_results = arguments.get("max_results", 20)
        next_token = arguments.get("next_token")
        
        self.logger.info(f"Retrieving change events for Core Network: {core_network_id}, Policy: {policy_version_id}")
        
        try:
            async with self.aws_manager.client_context("networkmanager", "us-west-2") as nm:
                params = {
                    "CoreNetworkId": core_network_id,
                    "PolicyVersionId": policy_version_id,
                    "MaxResults": max_results,
                }
                if next_token:
                    params["NextToken"] = next_token
                
                response = await nm.get_core_network_change_events(**params)
                
                result = CoreNetworkChangeEventsResponse(
                    core_network_id=core_network_id,
                    change_events=response.get("CoreNetworkChangeEvents", []),
                    max_results=max_results,
                    next_token=response.get("NextToken"),
                )
                
                return CallToolResult(
                    content=[TextContent(type="text", text=result.model_dump_json(indent=2))]
                )
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve Core Network change events: {e}")
            error_response = {
                "error": f"Failed to retrieve change events for Core Network {core_network_id}: {str(e)}",
                "core_network_id": core_network_id,
                "policy_version_id": policy_version_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(error_response, indent=2))]
            )