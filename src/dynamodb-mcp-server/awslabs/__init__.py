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

# This file is part of the awslabs namespace.
# It is intentionally minimal to support PEP 420 namespace packages.

# Namespace Package Configuration
#
# This line resolves namespace conflicts when multiple packages share the 'awslabs' namespace prefix.
# Without this configuration, test suites fail and build issues occur because Python cannot properly
# resolve which package owns the 'awslabs' namespace when both 'awslabs.dynamodb-mcp-server' and
# 'awslabs.mysql-mcp-server' are installed in the same environment.
#
# The extend_path() function implements PEP 420 namespace packages, allowing multiple distributions
# to contribute modules to the same namespace. This ensures that:
# 1. Both DynamoDB and MySQL MCP servers can coexist in the same Python environment
# 2. Import statements like 'from awslabs.dynamodb_mcp_server import ...' work correctly
# 3. Test discovery and execution functions properly across both packages
# 4. Build processes complete successfully without namespace collision errors
#
# This is the standard solution for namespace packages in Python and is required for proper
# multi-package namespace support in the awslabs ecosystem.

# Extend namespace to include installed packages
__path__ = __import__('pkgutil').extend_path(__path__, __name__)
