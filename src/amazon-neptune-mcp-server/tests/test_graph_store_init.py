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
"""Tests for the graph_store package initialization."""

from awslabs.amazon_neptune_mcp_server.graph_store import (
    NeptuneAnalytics,
    NeptuneDatabase,
    NeptuneGraph,
)


class TestGraphStoreInit:
    """Test class for the graph_store package initialization."""

    def test_imports(self):
        """Test that the graph_store package exports the expected classes.

        This test verifies that:
        1. The NeptuneGraph abstract base class is exported
        2. The NeptuneAnalytics implementation class is exported
        3. The NeptuneDatabase implementation class is exported
        """
        # Act & Assert
        assert NeptuneGraph is not None
        assert NeptuneAnalytics is not None
        assert NeptuneDatabase is not None

    def test_class_hierarchy(self):
        """Test that the implementation classes inherit from the base class.

        This test verifies that:
        1. NeptuneAnalytics is a subclass of NeptuneGraph
        2. NeptuneDatabase is a subclass of NeptuneGraph
        """
        # Act & Assert
        assert issubclass(NeptuneAnalytics, NeptuneGraph)
        assert issubclass(NeptuneDatabase, NeptuneGraph)
