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

"""Base task class for Application Signals MCP evaluation."""

from evals.core import Task
from pathlib import Path


# Samples root: base.py -> applicationsignals/ -> tasks/ -> evals/ -> cloudwatch-applicationsignals-mcp-server/ -> src/ -> root/ -> samples/cloudwatch-applicationsignals-mcp
SAMPLES_ROOT = (
    Path(__file__).parent.parent.parent.parent.parent.parent
    / 'samples'
    / 'cloudwatch-applicationsignals-mcp'
)


class ApplicationSignalsTask(Task):
    """Base class for Application Signals evaluation tasks.

    Provides common configuration for all Application Signals tasks.
    """

    def get_server_root_directory(self) -> Path:
        """Return MCP server root directory.

        MCP server working directory: base.py -> applicationsignals/ -> tasks/ -> evals/ -> cloudwatch-applicationsignals-mcp-server/
        """
        return Path(__file__).parent.parent.parent.parent

    def get_server_file(self) -> Path:
        """Return MCP server file path."""
        return (
            self.get_server_root_directory()
            / 'awslabs'
            / 'cloudwatch_applicationsignals_mcp_server'
            / 'server.py'
        )
