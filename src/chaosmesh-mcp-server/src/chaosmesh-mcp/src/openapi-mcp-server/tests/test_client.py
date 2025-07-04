#!/usr/bin/env python3
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
#!/usr/bin/env python3
"""Test client for OpenAPI MCP Server."""

import asyncio
import httpx
import json
import logging
import sys
from typing import Any, Dict, List


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
)
logger = logging.getLogger('test_client')


async def list_prompts(client: httpx.AsyncClient) -> List[str]:
    """List all prompts available from the server."""
    try:
        response = await client.get('/prompts')
        if response.status_code == 200:
            data = response.json()
            logger.info(f'Found {len(data)} prompts')
            return data
        else:
            logger.error(f'Failed to list prompts: {response.status_code}')
            return []
    except Exception as e:
        logger.error(f'Error listing prompts: {e}')
        return []


async def get_prompt_content(client: httpx.AsyncClient, prompt_name: str) -> Dict[str, Any]:
    """Get the content of a specific prompt."""
    try:
        response = await client.get(f'/prompts/{prompt_name}')
        if response.status_code == 200:
            data = response.json()
            logger.info(f'Retrieved prompt: {prompt_name}')
            return data
        else:
            logger.error(f'Failed to get prompt {prompt_name}: {response.status_code}')
            return {}
    except Exception as e:
        logger.error(f'Error getting prompt {prompt_name}: {e}')
        return {}


async def list_tools(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """List all tools available from the server."""
    try:
        response = await client.get('/tools')
        if response.status_code == 200:
            data = response.json()
            logger.info(f'Found {len(data)} tools')
            return data
        else:
            logger.error(f'Failed to list tools: {response.status_code}')
            return []
    except Exception as e:
        logger.error(f'Error listing tools: {e}')
        return []


async def main() -> None:
    """Test the OpenAPI MCP Server."""
    # Create HTTP client
    async with httpx.AsyncClient(base_url='http://localhost:8002') as client:
        logger.info('Connected to MCP server')

        # List all prompts
        prompts = await list_prompts(client)
        logger.info('Available prompts:')
        for prompt in prompts:
            logger.info(f'- {prompt}')

        # Check for operation prompts
        operation_prompts = [p for p in prompts if p.endswith('_prompt')]
        logger.info(f'\nFound {len(operation_prompts)} operation prompts')

        # Get content of a few sample prompts
        sample_prompts = operation_prompts[:3] if len(operation_prompts) >= 3 else operation_prompts
        for prompt_name in sample_prompts:
            logger.info(f'\nContent of {prompt_name}:')
            prompt_content = await get_prompt_content(client, prompt_name)
            if prompt_content:
                logger.info(json.dumps(prompt_content, indent=2))

        # List all tools
        tools = await list_tools(client)
        logger.info('\nAvailable tools:')
        for tool in tools:
            logger.info(f'- {tool.get("name")}: {tool.get("description")}')


if __name__ == '__main__':
    asyncio.run(main())
