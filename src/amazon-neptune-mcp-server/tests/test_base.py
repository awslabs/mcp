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
"""Tests for the NeptuneGraph abstract base class."""

import pytest
from awslabs.amazon_neptune_mcp_server.graph_store.base import NeptuneGraph


class TestNeptuneGraph:
    """Test class for the NeptuneGraph abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that NeptuneGraph cannot be instantiated directly.

        This test verifies that:
        1. NeptuneGraph is an abstract class that cannot be instantiated
        2. Attempting to instantiate it raises TypeError
        """
        # Act & Assert
        with pytest.raises(TypeError, match=r"Can't instantiate abstract class NeptuneGraph"):
            NeptuneGraph()

    def test_abstract_methods_defined(self):
        """Test that NeptuneGraph defines the required abstract methods.

        This test verifies that:
        1. The abstract methods are defined in the NeptuneGraph class
        2. The methods have the expected signatures
        """
        # Arrange
        abstract_methods = [
            'get_lpg_schema',
            'get_rdf_schema',
            'query_opencypher',
            'query_gremlin',
            'query_sparql',
        ]

        # Act & Assert
        for method_name in abstract_methods:
            assert hasattr(NeptuneGraph, method_name), f'NeptuneGraph should define {method_name}'
            method = getattr(NeptuneGraph, method_name)
            assert callable(method), f'{method_name} should be callable'

    def test_concrete_implementation_required(self):
        """Test that concrete implementations must implement all abstract methods.

        This test verifies that:
        1. A concrete subclass that doesn't implement all abstract methods cannot be instantiated
        2. The error message correctly indicates which methods are not implemented
        """

        # Arrange
        class IncompleteNeptuneGraph(NeptuneGraph):
            """Incomplete implementation of NeptuneGraph for testing."""

            def get_lpg_schema(self):
                """Implemented method."""
                return {}

        # Act & Assert
        with pytest.raises(TypeError) as excinfo:
            IncompleteNeptuneGraph()

        # Check that the error message mentions the missing methods
        error_message = str(excinfo.value)
        assert "Can't instantiate abstract class IncompleteNeptuneGraph" in error_message
        assert 'get_rdf_schema' in error_message
        assert 'query_opencypher' in error_message
        assert 'query_gremlin' in error_message
        assert 'query_sparql' in error_message
