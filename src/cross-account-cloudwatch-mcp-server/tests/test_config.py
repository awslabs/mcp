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

"""Tests for config loading helpers."""

from awslabs.cross_account_cloudwatch_mcp_server.config import (
    CONFIG_PATH_ENV_VAR,
    ConfigNotProvidedError,
    load_cloudwatch_config,
    resolve_config_path,
)
from pathlib import Path

import pytest


def test_resolve_config_path_prefers_env_var(monkeypatch):
    """Test that CW_CONFIG_PATH overrides the cwd default."""
    expected_path = '/tmp/custom-cw-config.yaml'
    monkeypatch.setenv(CONFIG_PATH_ENV_VAR, expected_path)

    assert resolve_config_path() == Path(expected_path)


def test_load_cloudwatch_config_raises_when_missing(monkeypatch, tmp_path):
    """Test that missing config raises an actionable exception."""
    monkeypatch.delenv(CONFIG_PATH_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ConfigNotProvidedError) as exc_info:
        load_cloudwatch_config()

    assert 'cw_config.yaml' in str(exc_info.value)
    assert 'cw_config.example.yaml' in str(exc_info.value)


def test_load_cloudwatch_config_reads_env_config(monkeypatch, tmp_path):
    """Test that config is loaded from CW_CONFIG_PATH when provided."""
    config_path = tmp_path / 'custom.yaml'
    config_path.write_text(
        '\n'.join(
            [
                'accounts:',
                '  - accountId: "123456789012"',
                '    region: "us-west-2"',
                '    roleName: "CloudWatchReadOnly"',
                '    logGroups:',
                '      - name: "/aws/lambda/payments-prod"',
                '        description: "Primary payment handler"',
            ]
        ),
        encoding='utf-8',
    )
    monkeypatch.setenv(CONFIG_PATH_ENV_VAR, str(config_path))

    config, loaded_path = load_cloudwatch_config()

    assert loaded_path == config_path
    assert config.accounts[0].accountId == '123456789012'
    assert config.accounts[0].logGroups[0].name == '/aws/lambda/payments-prod'
