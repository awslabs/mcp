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

"""awslabs Inspector MCP Server implementation."""

from awslabs.inspector_mcp_server.tools import InspectorTools
from loguru import logger
from mcp.server.fastmcp import FastMCP


mcp = FastMCP(
    'awslabs.inspector-mcp-server',
    instructions='Use this MCP server to query Amazon Inspector findings for vulnerability analysis, security posture monitoring, and compliance reporting. Supports listing and filtering findings by severity, resource type, and time range, retrieving detailed finding information including CVSS scores and remediation guidance, aggregating findings for dashboard views, checking scan coverage across resources, monitoring account scanning status, and generating findings reports exported to S3.',
    dependencies=[
        'boto3',
        'botocore',
        'pydantic',
        'loguru',
    ],
)

# Initialize and register Inspector tools
try:
    inspector_tools = InspectorTools()
    inspector_tools.register(mcp)
    logger.info('Inspector tools registered successfully')
except Exception as e:
    logger.error(f'Error initializing Inspector tools: {str(e)}')
    raise


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == '__main__':
    main()
