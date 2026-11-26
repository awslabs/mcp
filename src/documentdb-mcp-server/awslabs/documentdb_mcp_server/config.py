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

"""Configuration settings for DocumentDB MCP Server."""

from awslabs.documentdb_mcp_server.errors import SafeToolError
from loguru import logger
from typing import Any, Dict, List, Optional


# Upper bound on documents returned by find/aggregate and sampled by analyzeSchema.
MAX_RESULTS = 1000

# Aggregation stages that write to the database.
WRITE_STAGES = ('$out', '$merge')


class ServerConfig:
    """Configuration class for DocumentDB MCP Server.

    This class contains configuration options that control the server's behavior.
    """

    def __init__(self):
        """Initialize server configuration with default values.

        By default, the server starts in read-only mode for safety.
        """
        self.read_only_mode = True
        self.connection_string: Optional[str] = None


# Singleton instance
serverConfig = ServerConfig()


def assert_pipeline_readonly(pipeline: List[Dict[str, Any]]) -> None:
    """Reject aggregation write stages while the server is in read-only mode.

    Every tool that accepts an aggregation pipeline must call this before the
    pipeline reaches the database.

    Args:
        pipeline: The aggregation pipeline supplied by the client.

    Raises:
        SafeToolError: If read-only mode is on and the pipeline contains $out or $merge.
    """
    if not serverConfig.read_only_mode:
        return

    for stage in pipeline:
        denied = next((s for s in WRITE_STAGES if s in stage), None)
        if denied:
            logger.warning(f'Pipeline denied: contains write stage ({denied}) in read-only mode')
            raise SafeToolError(
                'Operation not permitted: Server is configured in read-only mode. '
                'Aggregation pipeline contains write stages ($out or $merge) which are not allowed.'
            )


def bounded_limit(limit: int) -> int:
    """Clamp a client-supplied result limit to the range [1, MAX_RESULTS]."""
    return max(1, min(limit, MAX_RESULTS))
