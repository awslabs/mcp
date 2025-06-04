# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
import os
import sys
from loguru import logger


# Set up logging
logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))

PARTITION = os.getenv('AWS_DOCUMENTATION_PARTITION', 'aws').lower()


def main():
    """Run the MCP server with CLI argument support."""
    if PARTITION == 'aws':
        from awslabs.aws_documentation_mcp_server.server_aws import main
    elif PARTITION == 'aws-cn':
        from awslabs.aws_documentation_mcp_server.server_aws_cn import main
    else:
        raise ValueError(f'Unsupported AWS documentation partition: {PARTITION}.')

    main()


if __name__ == '__main__':
    main()
