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
"""Authentication package for OpenAPI MCP Server."""

# Import register module to auto-register providers
import awslabs.openapi_mcp_server.auth.register  # noqa: F401
from awslabs.openapi_mcp_server.auth.auth_factory import get_auth_provider, is_auth_type_available
from awslabs.openapi_mcp_server.auth.auth_provider import AuthProvider, NullAuthProvider

# Define public exports
__all__ = [
    'get_auth_provider',
    'is_auth_type_available',
    'AuthProvider',
    'NullAuthProvider',
]
