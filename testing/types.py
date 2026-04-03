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
"""Type definitions for the MCP testing framework."""

from enum import Enum


class TestType(Enum):
    """Enum for different types of MCP tests."""

    TOOL_CALL = 'tool_call'
    RESOURCE_READ = 'resource_read'
    PROMPT_GET = 'prompt_get'


# Prevent pytest from collecting this as a test class
TestType.__test__ = False
