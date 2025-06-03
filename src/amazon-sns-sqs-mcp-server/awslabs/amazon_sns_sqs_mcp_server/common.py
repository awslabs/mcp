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
#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

"""Common utilities for MCP server."""

from typing import Dict, Tuple


# Tag name constant
MCP_SERVER_VERSION_TAG = 'mcp_server_version'


def validate_mcp_server_version_tag(tags: Dict[str, str]) -> Tuple[bool, str]:
    """Check if the tags contain the mcp_server_version tag.

    Args:
        tags: Dictionary where keys are tag names and values are tag values

    Returns:
        Tuple of (is_valid, error_message)

    """
    return (
        (True, '')
        if MCP_SERVER_VERSION_TAG in tags
        else (False, 'mutating a resource without the mcp_server_version tag is not allowed')
    )
