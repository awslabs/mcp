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
"""Windows event loop configuration tests."""

from unittest.mock import Mock, patch

import awslabs.postgres_mcp_server.server as server_module


def test_windows_uses_selector_event_loop_policy(monkeypatch):
    """The Windows startup policy is compatible with psycopg async mode."""
    selector_policy = Mock()
    policy_factory = Mock(return_value=selector_policy)
    monkeypatch.setattr(server_module.sys, 'platform', 'win32')
    monkeypatch.setattr(
        server_module.asyncio,
        'WindowsSelectorEventLoopPolicy',
        policy_factory,
        raising=False,
    )

    with patch.object(server_module.asyncio, 'set_event_loop_policy') as set_policy:
        server_module._configure_windows_event_loop_policy()

    policy_factory.assert_called_once_with()
    set_policy.assert_called_once_with(selector_policy)


def test_non_windows_keeps_default_event_loop_policy(monkeypatch):
    """Other platforms retain their existing event loop policy."""
    monkeypatch.setattr(server_module.sys, 'platform', 'linux')

    with patch.object(server_module.asyncio, 'set_event_loop_policy') as set_policy:
        server_module._configure_windows_event_loop_policy()

    set_policy.assert_not_called()
