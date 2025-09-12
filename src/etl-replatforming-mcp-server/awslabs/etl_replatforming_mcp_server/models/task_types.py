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

"""FLEX Task Type Constants"""

from typing import List, Set

# Core task types for data processing
CORE_TASK_TYPES = {
    'sql',  # SQL query execution
    'python',  # Python script execution
    'bash',  # Shell command execution
    'container',  # Container/Docker execution
}

# Control flow task types
CONTROL_FLOW_TASK_TYPES = {
    'branch',  # Conditional branching (Choice in Step Functions)
    'for_each',  # Loop iteration (Map in Step Functions)
    'while',  # While loop
    'parallel',  # Parallel execution
    'wait',  # Wait/delay task
}

# Data movement task types
DATA_TASK_TYPES = {
    'copy',  # Data copy/transfer
    'file_transfer',  # File operations
    'extract',  # Data extraction
    'transform',  # Data transformation
    'load',  # Data loading
}

# Integration task types
INTEGRATION_TASK_TYPES = {
    'email',  # Email notifications
    'http',  # HTTP API calls
    'webhook',  # Webhook calls
    'sns',  # SNS notifications
    'sqs',  # SQS operations
}

# Monitoring and utility task types
UTILITY_TASK_TYPES = {
    'sensor',  # Wait for condition
    'check',  # Data quality check
    'validate',  # Validation task
    'cleanup',  # Cleanup operations
    'dummy',  # No-op placeholder
}

# All valid task types
ALL_TASK_TYPES: Set[str] = (
    CORE_TASK_TYPES
    | CONTROL_FLOW_TASK_TYPES
    | DATA_TASK_TYPES
    | INTEGRATION_TASK_TYPES
    | UTILITY_TASK_TYPES
)

# Task types that support loops/iteration
LOOP_TASK_TYPES = {'for_each', 'while', 'parallel'}

# Task types that support branching
BRANCH_TASK_TYPES = {'branch'}

# Task types that require external scripts
SCRIPT_TASK_TYPES = {'python', 'bash', 'container'}


def get_all_task_types() -> List[str]:
    """Get all valid FLEX task types"""
    return sorted(list(ALL_TASK_TYPES))


def is_valid_task_type(task_type: str) -> bool:
    """Check if task type is valid"""
    return task_type in ALL_TASK_TYPES


def is_loop_task_type(task_type: str) -> bool:
    """Check if task type supports loops"""
    return task_type in LOOP_TASK_TYPES


def is_branch_task_type(task_type: str) -> bool:
    """Check if task type supports branching"""
    return task_type in BRANCH_TASK_TYPES


def requires_script_file(task_type: str) -> bool:
    """Check if task type requires external script file"""
    return task_type in SCRIPT_TASK_TYPES
