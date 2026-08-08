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

"""Shared pytest fixtures for the Amazon Connect MCP Server tests."""

import pytest


class FakeContext:
    """Minimal stand-in for the MCP Context object used in tests."""

    def __init__(self):
        """Initialize the fake context with an empty error log."""
        self.errors = []

    async def error(self, message: str):
        """Record an error message instead of reporting it to a real client."""
        self.errors.append(message)


@pytest.fixture
def ctx():
    """Provide a fresh FakeContext for each test."""
    return FakeContext()
