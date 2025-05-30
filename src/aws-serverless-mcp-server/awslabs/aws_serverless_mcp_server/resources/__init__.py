"""
MCP Resources Index

Exports all resource implementations for the AWS Serverless MCP server.
"""

from awslabs.aws_serverless_mcp_server.resources.deployment_details import (
    handle_deployment_details,
)
from awslabs.aws_serverless_mcp_server.resources.deployment_list import handle_deployments_list
from awslabs.aws_serverless_mcp_server.resources.template_details import handle_template_details
from awslabs.aws_serverless_mcp_server.resources.template_list import handle_template_list

__all__ = [
    handle_deployment_details,
    handle_deployments_list,
    handle_template_details,
    handle_template_list,
]
