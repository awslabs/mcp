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

"""
AWS Knowledge Proxy module for ECS MCP Server.
This module handles the setup and configuration of the AWS Knowledge MCP Server proxy integration.
"""

import logging
from typing import Optional

from fastmcp import FastMCP
from fastmcp.server.proxy import ProxyClient
from fastmcp.tools.tool_transform import ToolTransformConfig

# Guidance to append to tool descriptions
# ruff: noqa: E501
ECS_TOOL_GUIDANCE = """

    ## ECS DOCUMENTATION GUIDANCE:
    This tool provides up-to-date ECS documentation and implementation guidance, including new ECS features beyond standard LLM training data.

    New ECS features include:
    - ECS Native Blue-Green Deployments (different from CodeDeploy blue-green, launched 2025)
    - ECS Managed Instances (launched 2025)
"""

logger = logging.getLogger(__name__)


def register_proxy(mcp: FastMCP) -> Optional[bool]:
    """
    Sets up the AWS Knowledge MCP Server proxy integration using transport bridging
    -> https://gofastmcp.com/servers/proxy#transport-bridging

    Args:
        mcp: The FastMCP server instance to mount the proxy on

    Returns:
        bool: True if setup was successful, False otherwise
    """
    try:
        logger.info("Setting up AWS Knowledge MCP Server proxy")
        aws_knowledge_proxy = FastMCP.as_proxy(
            ProxyClient("https://knowledge-mcp.global.api.aws"), name="AWS-Knowledge-Bridge"
        )
        mcp.mount(aws_knowledge_proxy, prefix="aws_knowledge")

        # Add prompt patterns for blue-green deployments
        register_ecs_prompts(mcp)

        logger.info("Successfully mounted AWS Knowledge MCP Server")
        return True

    except Exception as e:
        logger.error(f"Failed to setup AWS Knowledge MCP Server proxy: {e}")
        return False


async def apply_tool_transformations(mcp: FastMCP) -> None:
    """
    Apply tool transformations to the AWS Knowledge proxy tools.

    Args:
        mcp: The FastMCP server instance to apply transformations to
    """
    logger.info("Applying tool transformations...")
    await _add_ecs_guidance_to_knowledge_tools(mcp)


async def _add_ecs_guidance_to_knowledge_tools(mcp: FastMCP) -> None:
    """Add ECS documentation guidance to specific tools if they exist."""
    try:
        tools = await mcp.get_tools()

        knowledge_tools = [
            "aws_knowledge_aws___search_documentation",
            "aws_knowledge_aws___read_documentation",
            "aws_knowledge_aws___recommend",
        ]

        for tool_name in knowledge_tools:
            if tool_name not in tools:
                logger.warning(f"Tool {tool_name} not found in MCP tools")
                continue

            original_desc = tools[tool_name].description or ""
            config = ToolTransformConfig(
                name=tool_name, description=original_desc + ECS_TOOL_GUIDANCE
            )
            mcp.add_tool_transformation(tool_name, config)

        logger.debug("Added ECS guidance to AWS Knowledge tools")
    except Exception as e:
        logger.error(f"Error applying tool transformations: {e}")
        raise


def register_ecs_prompts(mcp: FastMCP) -> None:
    """
    Register ECS-related prompt patterns with AWS Knowledge proxy tools.

    Covers blue-green deployments, new ECS features, and comparisons based on ECS_TOOL_GUIDANCE.

    Args:
        mcp: The FastMCP server instance to register prompts with
    """

    prompts = [
        {
            "patterns": [
                "what are blue green deployments",
                "what are b/g deployments",
                "native ecs blue green",
                "native ecs b/g",
                "ecs native blue green deployments",
                "difference between codedeploy and native blue green",
                "how to setup blue green",
                "setup ecs blue green",
                "configure ecs blue green deployments",
                "configure blue green",
                "configure b/g",
                "create blue green deployment",
            ],
            "response": [
                {
                    "name": "aws_knowledge_aws___search_documentation",
                }
            ],
        },
        {
            "patterns": [
                "ecs best practices",
                "ecs implementation guide",
                "ecs guidance",
                "ecs recommendations",
                "how to use ecs effectively",
                "new ecs feature",
                "latest ecs feature",
            ],
            "response": [
                {
                    "name": "aws_knowledge_aws___search_documentation",
                }
            ],
        },
        {
            "patterns": [
                "what are ecs managed instances",
                "how to setup ecs managed instances",
                "ecs managed instances",
                "ecs MI",
                "managed instances ecs",
                "ecs specialized instance types",
                "ecs custom instance types",
                "ecs instance type selection",
                "What alternatives do I have for Fargate?",
                "How do I migrate from Fargate to Managed Instances",
            ],
            "response": [
                {
                    "name": "aws_knowledge_aws___search_documentation",
                }
            ],
        },
    ]

    # Register all prompt patterns using loops
    total_patterns = 0
    for prompt_group in prompts:
        patterns = prompt_group["patterns"]
        response = prompt_group["response"]

        for pattern in patterns:

            def create_prompt_handler(response_data):
                def prompt_handler():
                    return response_data

                return prompt_handler

            handler = create_prompt_handler(response)
            mcp.prompt(pattern)(handler)
            total_patterns += 1

    logger.info(
        f"Registered {total_patterns} ECS-related prompt patterns with AWS Knowledge proxy tools"
    )
