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

"""AWS Agent Registry Tools - Search, list, and inspect AWS Agent Registry records and registries.

Exposes AWS Agent Registry control plane and data plane APIs as MCP tools,
enabling AI assistants to discover MCP servers, A2A agents, agent skills,
and custom resources programmatically.
"""

import boto3
import json
import os
from loguru import logger
from pydantic import Field
from typing import Optional


# Lazily initialized boto3 clients
_cp_client = None
_dp_client = None


def _get_cp_client():
    """Return the control plane client, creating it lazily on first call.

    Creates a boto3 client for the ``bedrock-agentcore-control`` service.
    The AWS region is read from the ``AWS_REGION`` environment variable,
    defaulting to ``us-west-2`` when not set.  The client is cached in the
    module-level ``_cp_client`` variable and reused on subsequent calls.
    """
    global _cp_client
    if _cp_client is None:
        region = os.environ.get('AWS_REGION', 'us-west-2')
        logger.info(f'Creating bedrock-agentcore-control client in {region}')
        session = boto3.Session(region_name=region)
        _cp_client = session.client('bedrock-agentcore-control')
    return _cp_client


def _get_dp_client():
    """Return the data plane client, creating it lazily on first call.

    Creates a boto3 client for the ``bedrock-agentcore-registry`` service
    with a custom endpoint URL of
    ``https://bedrock-agentcore.{region}.amazonaws.com``.  The AWS region
    is read from the ``AWS_REGION`` environment variable, defaulting to
    ``us-west-2`` when not set.  The client is cached in the module-level
    ``_dp_client`` variable and reused on subsequent calls.
    """
    global _dp_client
    if _dp_client is None:
        region = os.environ.get('AWS_REGION', 'us-west-2')
        endpoint_url = f'https://bedrock-agentcore.{region}.amazonaws.com'
        logger.info(
            f'Creating bedrock-agentcore-registry client in {region} (endpoint: {endpoint_url})'
        )
        session = boto3.Session(region_name=region)
        _dp_client = session.client('bedrock-agentcore-registry', endpoint_url=endpoint_url)
    return _dp_client


def _parse_inline_json(content: str) -> Optional[dict]:
    """Safely parse a JSON string, returning None on failure.

    Args:
        content: A string that may contain valid JSON.

    Returns:
        The parsed JSON object, or ``None`` if parsing fails.
    """
    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError):
        logger.debug(f'Failed to parse inline JSON content: {content[:100]}...')
        return None


async def search_registry(
    query: str = Field(..., description='Natural language search query describing what you need'),
    registry_arn: str = Field(..., description='Registry ARN to search within'),
    max_results: int = Field(5, description='Maximum number of results to return (default: 5)'),
) -> str:
    """Search AWS Agent Registry for MCP tools, A2A agents, or custom resources.

    Performs a semantic search across approved registry records, returning
    results ranked by relevance.  For MCP descriptor records the response
    includes parsed connection details (endpoint, transport type, tool names).
    """
    try:
        results = _get_dp_client().search_registry_records(
            registryIds=[registry_arn],
            searchQuery=query,
            maxResults=max_results,
        )

        records = results.get('registryRecords', [])
        if not records:
            return f'No results found for: {query}'

        output = []
        for rec in records:
            entry = {
                'name': rec['name'],
                'description': rec.get('description', ''),
                'type': rec.get('descriptorType', 'N/A'),
                'status': rec.get('status', 'N/A'),
                'score': rec.get('score', 'N/A'),
            }

            # Parse MCP descriptors for connection details
            descriptors = rec.get('descriptors', {})
            if 'mcp' in descriptors:
                server_raw = descriptors['mcp'].get('server', {}).get('inlineContent', '{}')
                server_info = _parse_inline_json(server_raw)
                if server_info:
                    packages = server_info.get('packages', [])
                    if packages:
                        transport = packages[0].get('transport', {})
                        entry['endpoint'] = transport.get('url', 'N/A')
                        entry['transport_type'] = transport.get('type', 'N/A')

                tools_raw = descriptors['mcp'].get('tools', {}).get('inlineContent', '{}')
                tools_info = _parse_inline_json(tools_raw)
                if tools_info:
                    entry['tools'] = [t['name'] for t in tools_info.get('tools', [])]

            output.append(entry)

        return json.dumps(output, indent=2)
    except Exception as e:
        logger.error(f'Error searching registry: {e}')
        return json.dumps({'error': str(e)})


async def list_records(
    registry_id: str = Field(..., description='Registry ID to list records from'),
) -> str:
    """List all records in a specific Agent Registry.

    Returns a JSON array of records with their name, record ID, descriptor
    type, and status.  Returns an empty array when the registry contains
    no records.
    """
    try:
        results = _get_cp_client().list_registry_records(registryId=registry_id)

        records = []
        for rec in results.get('registryRecords', []):
            records.append(
                {
                    'name': rec['name'],
                    'recordId': rec.get('recordId', 'N/A'),
                    'type': rec.get('descriptorType', 'N/A'),
                    'status': rec.get('status', 'N/A'),
                }
            )

        return json.dumps(records, indent=2)
    except Exception as e:
        logger.error(f'Error listing registry records: {e}')
        return json.dumps({'error': str(e)})


async def get_record(
    registry_id: str = Field(..., description='Registry ID'),
    record_id: str = Field(..., description='Record ID'),
) -> str:
    """Get full details of a specific registry record including descriptors.

    Strips ``ResponseMetadata`` from the API response and parses inline
    JSON content in MCP, A2A, and custom descriptors, adding a ``parsed``
    field alongside ``inlineContent`` for readability.  Malformed inline
    JSON is silently skipped.
    """
    try:
        rec = _get_cp_client().get_registry_record(registryId=registry_id, recordId=record_id)

        # Strip ResponseMetadata
        output = {k: v for k, v in rec.items() if k != 'ResponseMetadata'}

        # Parse inline descriptors for readability
        descriptors = output.get('descriptors', {})
        for dtype in ['mcp', 'a2a', 'custom']:
            if dtype in descriptors:
                for field_name in descriptors[dtype]:
                    content = descriptors[dtype][field_name].get('inlineContent')
                    if content:
                        parsed = _parse_inline_json(content)
                        if parsed is not None:
                            descriptors[dtype][field_name]['parsed'] = parsed

        return json.dumps(output, indent=2, default=str)
    except Exception as e:
        logger.error(f'Error getting registry record: {e}')
        return json.dumps({'error': str(e)})


async def list_registries() -> str:
    """List all AgentCore Registries in the AWS account.

    Returns a JSON array of registries with their name, registry ID,
    status, and auto-approval configuration.  Returns an empty array
    when the account contains no registries.
    """
    try:
        results = _get_cp_client().list_registries()

        registries = []
        for reg in results.get('registries', []):
            registries.append(
                {
                    'name': reg['name'],
                    'registryId': reg.get('registryId', 'N/A'),
                    'status': reg.get('status', 'N/A'),
                    'autoApproval': reg.get('approvalConfiguration', {}).get(
                        'autoApproval', 'N/A'
                    ),
                }
            )

        return json.dumps(registries, indent=2)
    except Exception as e:
        logger.error(f'Error listing registries: {e}')
        return json.dumps({'error': str(e)})
