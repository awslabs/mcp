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

"""Tests for the Context class in the AWS IAM MCP Server."""

from awslabs.iam_mcp_server.context import Context


def test_context_initialization():
    """Test Context initialization."""
    Context.initialize(readonly=True)
    assert Context.is_readonly() is True

    Context.initialize(readonly=False)
    assert Context.is_readonly() is False


def test_context_region():
    """Test Context region management."""
    # Test default region
    assert Context.get_region() is None

    # Test setting region
    Context.set_region('us-west-2')
    assert Context.get_region() == 'us-west-2'

    # Test changing region
    Context.set_region('eu-west-1')
    assert Context.get_region() == 'eu-west-1'


def test_context_readonly_mode():
    """Test Context readonly mode."""
    # Test setting readonly mode
    Context.initialize(readonly=True)
    assert Context.is_readonly() is True

    # Test disabling readonly mode
    Context.initialize(readonly=False)
    assert Context.is_readonly() is False
