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

"""AWS-specific functionality for the AWS API MCP server."""

from .driver import translate_cli_to_ir, get_local_credentials
from .regions import GLOBAL_SERVICE_REGIONS
from .service import (
    interpret_command,
    is_operation_read_only,
)

__all__ = [
    'translate_cli_to_ir',
    'GLOBAL_SERVICE_REGIONS',
    'get_local_credentials',
    'interpret_command',
    'is_operation_read_only',
]
