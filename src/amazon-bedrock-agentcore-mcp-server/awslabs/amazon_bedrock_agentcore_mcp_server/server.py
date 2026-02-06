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

"""awslabs AWS Bedrock AgentCore MCP Server implementation."""
import logging
import sys
from .tools import docs, gateway, memory, runtime
from .utils import cache
from mcp.server.fastmcp import FastMCP
from .config import doc_config

#Structured Logging Configuration
logging.basicConfig(
    level=doc_config.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger('amazon-bedrock-mcp')

APP_NAME = 'amazon-bedrock-agentcore-mcp-server'
mcp = FastMCP(APP_NAME)

#Tool Registration
logger.info("Registering AgentCore tools...")
mcp.tool()(docs.search_agentcore_docs)
mcp.tool()(docs.fetch_agentcore_doc)
mcp.tool()(runtime.manage_agentcore_runtime)
mcp.tool()(memory.manage_agentcore_memory)
mcp.tool()(gateway.manage_agentcore_gateway)


def main() -> None:
    """Main entry point for the MCP server.

    Initializes the document cache and starts the FastMCP server.
    The cache is loaded with document titles only for fast startup,
    with full content fetched on-demand.
    """
    try:
            logger.info(f"Starting server {APP_NAME}...")
            
            # Inicialização do cache com rastreabilidade
            logger.debug("Checking cache readiness...")
            cache.ensure_ready()
            
            logger.info("Server ready and waiting for connections via STDIO.")
            mcp.run()
    except Exception as e:
            logger.error(f"Critical server initialization failure: {str(e)}", exc_info=True)
            sys.exit(1)


if __name__ == '__main__':
    main()
