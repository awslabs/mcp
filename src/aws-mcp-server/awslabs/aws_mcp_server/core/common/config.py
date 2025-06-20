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

import os


TRUTHY_VALUES = frozenset(['true', 'yes', '1'])
READ_ONLY_KEY = 'READ_OPERATIONS_ONLY'


def get_env_bool(env_key: str, default: bool) -> bool:
    """Get a boolean value from an environment variable, with a default."""
    return os.getenv(env_key, str(default)).casefold() in TRUTHY_VALUES


FASTMCP_LOG_LEVEL = os.getenv('FASTMCP_LOG_LEVEL', 'WARNING')
DEFAULT_REGION = os.getenv('AWS_REGION')
MAX_OUTPUT_TOKENS = os.getenv('MAX_OUTPUT_TOKENS')
BYPASS_TOOL_CONSENT = get_env_bool('BYPASS_TOOL_CONSENT', False)
READ_OPERATIONS_ONLY_MODE = get_env_bool(READ_ONLY_KEY, True)
RAG_TYPE = os.getenv('RAG_TYPE', 'DENSE_RETRIEVER')
