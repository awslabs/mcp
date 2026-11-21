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

"""Tests for the package version fallback in awslabs.db2_mcp_server."""

import importlib
import re


def test_init_version_fallback(monkeypatch):
    """When importlib.metadata.version raises, __version__ falls back to the literal in __init__."""
    import awslabs.db2_mcp_server as pkg

    def raise_(_):
        raise Exception('not installed')

    monkeypatch.setattr('importlib.metadata.version', raise_)
    reloaded = importlib.reload(pkg)
    try:
        # Assert the fallback is a valid semver literal rather than a specific
        # value, so the test survives release version bumps of __init__.py.
        assert re.fullmatch(r'\d+\.\d+\.\d+', reloaded.__version__)
        assert reloaded.__user_agent__.endswith(reloaded.__version__)
        assert 'db2-mcp-server' in reloaded.__user_agent__
    finally:
        # Reload once more with the real metadata available so later tests
        # see the normal __version__ again.
        monkeypatch.undo()
        importlib.reload(pkg)
