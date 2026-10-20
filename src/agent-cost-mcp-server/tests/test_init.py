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

"""Tests for the package __init__ module."""

import importlib
from awslabs.agent_cost_mcp_server import __version__


def test_version_exists():
    """The package exposes a version string."""
    assert __version__ is not None
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_module_reload():
    """The module can be reloaded without error."""
    module = importlib.import_module('awslabs.agent_cost_mcp_server')
    reloaded = importlib.reload(module)
    assert reloaded.__version__ == __version__
