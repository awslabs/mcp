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

"""Configuration settings for DocumentDB MCP Server."""


class ServerConfig:
    """Configuration class for DocumentDB MCP Server.

    This class contains configuration options that control the server's behavior.
    """

    def __init__(self):
        """Initialize server configuration with default values.

        By default, the server starts in read-only mode for safety.
        """
        self.read_only_mode = True


# Singleton instance
serverConfig = ServerConfig()
