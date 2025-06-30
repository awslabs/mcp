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

"""Tests for the context module."""

import pytest
from awslabs.elasticbeanstalk_mcp_server.context import Context


class TestContext:
    """Test class for the Context singleton."""

    def test_initialize(self):
        """Test that initialize creates the singleton instance."""
        # Arrange
        Context._instance = None  # Reset the singleton

        # Act
        Context.initialize(readonly_mode=True)

        # Assert
        assert Context._instance is not None
        assert isinstance(Context._instance, Context)
        assert Context._instance._readonly_mode is True

    def test_readonly_mode(self):
        """Test that readonly_mode returns the correct value."""
        # Arrange
        Context._instance = None  # Reset the singleton
        Context.initialize(readonly_mode=True)

        # Act
        result = Context.readonly_mode()

        # Assert
        assert result is True

    def test_readonly_mode_false(self):
        """Test that readonly_mode returns False when set to False."""
        # Arrange
        Context._instance = None  # Reset the singleton
        Context.initialize(readonly_mode=False)

        # Act
        result = Context.readonly_mode()

        # Assert
        assert result is False

    def test_readonly_mode_not_initialized(self):
        """Test that readonly_mode raises an exception when not initialized."""
        # Arrange
        Context._instance = None  # Reset the singleton

        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            Context.readonly_mode()

        assert 'Context was not initialized' in str(excinfo.value)
