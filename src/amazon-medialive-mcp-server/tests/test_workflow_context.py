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

"""Tests for the workflow context tool."""

from awslabs.amazon_medialive_mcp_server.workflow_context import (
    TOOL_DESCRIPTION,
    WORKFLOW_CONTEXT,
    get_media_workflow_context,
)


def test_get_media_workflow_context_returns_string():
    """Verify get_media_workflow_context returns the WORKFLOW_CONTEXT string."""
    result = get_media_workflow_context()
    assert result == WORKFLOW_CONTEXT
    assert isinstance(result, str)
    assert len(result) > 0


def test_tool_description_is_nonempty_string():
    """Verify TOOL_DESCRIPTION is a non-empty string."""
    assert isinstance(TOOL_DESCRIPTION, str)
    assert len(TOOL_DESCRIPTION) > 0
