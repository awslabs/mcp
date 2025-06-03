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
from awslabs.cfn_mcp_server.errors import ServerError


class Context:
    """A singleton which includes context for the MCP server such as startup parameters."""

    _instance = None

    def __init__(self, readonly_mode: bool):
        """Initializes the context."""
        self._readonly_mode = readonly_mode

    @classmethod
    def readonly_mode(cls) -> bool:
        """If a the server was started up with the argument --readonly True, this will be set to True."""
        if cls._instance is None:
            raise ServerError('Context was not initialized')
        return cls._instance._readonly_mode

    @classmethod
    def initialize(cls, readonly_mode: bool):
        """Create the singleton instance of the type."""
        cls._instance = cls(readonly_mode)
