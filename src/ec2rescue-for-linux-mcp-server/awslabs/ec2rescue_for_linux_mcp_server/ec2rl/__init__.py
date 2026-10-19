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

"""ec2rl package facade — re-exports the public symbols used by server.py and tests."""

from awslabs.ec2rescue_for_linux_mcp_server.ec2rl.commands import (
    validate_command,
    validate_log_read_command,
)
from awslabs.ec2rescue_for_linux_mcp_server.ec2rl.grep_strategy import (
    GatheredKvGrep,
    GrepStrategy,
    LogFixedGrep,
    LogSysctlGrep,
)
from awslabs.ec2rescue_for_linux_mcp_server.ec2rl.module import Ec2rlModule
from awslabs.ec2rescue_for_linux_mcp_server.ec2rl.registry import (
    DEFAULT_MODULES,
    EC2RL_MODULES,
    GATHEREDDIR_FILES,
    GREP_KEYS_MODULES,
    LARGE_OUTPUT_MODULES,
    READ_LOG_ON_NONZERO_EXIT_MODULES,
    STRIP_COMMENTS_MODULES,
    TAIL_MODULES,
    is_gathered_module,
)

__all__ = [
    'DEFAULT_MODULES',
    'EC2RL_MODULES',
    'Ec2rlModule',
    'GATHEREDDIR_FILES',
    'GREP_KEYS_MODULES',
    'GatheredKvGrep',
    'GrepStrategy',
    'LARGE_OUTPUT_MODULES',
    'LogFixedGrep',
    'LogSysctlGrep',
    'READ_LOG_ON_NONZERO_EXIT_MODULES',
    'STRIP_COMMENTS_MODULES',
    'TAIL_MODULES',
    'is_gathered_module',
    'validate_command',
    'validate_log_read_command',
]
