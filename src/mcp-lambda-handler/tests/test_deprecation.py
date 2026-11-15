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

"""Tests for the deprecation signal of the MCP Lambda Handler library."""

import awslabs.mcp_lambda_handler as package
import importlib
import os
import subprocess
import sys
import warnings
from awslabs.mcp_lambda_handler import DEPRECATION_NOTICE


def test_deprecation_notice_names_replacement_and_guide():
    """The notice names the package, the replacement, and the migration guide."""
    assert DEPRECATION_NOTICE.startswith('awslabs.mcp-lambda-handler is deprecated')
    assert 'Amazon Bedrock AgentCore Gateway' in DEPRECATION_NOTICE
    assert (
        'https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html'
        in DEPRECATION_NOTICE
    )
    assert (
        'https://github.com/awslabs/mcp/blob/main/docs/migration-mcp-lambda-handler.md'
        in DEPRECATION_NOTICE
    )


def test_import_emits_one_deprecation_warning():
    """Importing the package emits exactly one DeprecationWarning carrying the notice."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        importlib.reload(package)
    deprecation_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert len(deprecation_warnings) == 1
    assert DEPRECATION_NOTICE in str(deprecation_warnings[0].message)


def test_import_warning_is_shown_by_default_in_main():
    """With default filters, an import from __main__ shows the warning at the import line."""
    env = {key: value for key, value in os.environ.items() if key != 'PYTHONWARNINGS'}
    result = subprocess.run(
        [sys.executable, '-c', 'import awslabs.mcp_lambda_handler'],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr.count(DEPRECATION_NOTICE) == 1, result.stderr
    assert result.stderr.startswith('<string>:1: DeprecationWarning: '), result.stderr
