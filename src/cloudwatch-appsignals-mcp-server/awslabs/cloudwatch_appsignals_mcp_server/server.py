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

"""Deprecated: redirects to cloudwatch-applicationsignals-mcp-server."""

import sys
import warnings


def main():
    """Run the MCP server via the new cloudwatch-applicationsignals-mcp-server package."""
    warnings.warn(
        'awslabs.cloudwatch-appsignals-mcp-server is deprecated. '
        'Please update your MCP configuration to use '
        'awslabs.cloudwatch-applicationsignals-mcp-server instead. '
        'See: https://awslabs.github.io/mcp/servers/cloudwatch-applicationsignals-mcp-server/',
        DeprecationWarning,
        stacklevel=1,
    )
    print(
        'WARNING: awslabs.cloudwatch-appsignals-mcp-server is deprecated. '
        'Please switch to awslabs.cloudwatch-applicationsignals-mcp-server.',
        file=sys.stderr,
    )
    from awslabs.cloudwatch_applicationsignals_mcp_server.server import main as _main

    _main()


if __name__ == '__main__':
    main()
