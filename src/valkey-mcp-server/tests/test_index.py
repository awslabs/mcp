"""Unit tests for index module."""

import pytest
from awslabs.valkey_mcp_server.tools.index import (
    DistanceMetric,
    IndexType,
    StructureType,
    create_vector_index,
)
from unittest.mock import Mock, patch


class TestCreateVectorIndex:
    """Test cases for create_vector_index function."""

    @pytest.fixture
    def mock_connection(self):
        """Mock Valkey connection."""
        with patch(
            'awslabs.valkey_mcp_server.tools.index.ValkeyConnectionManager.get_connection'
        ) as mock:
            mock_conn = Mock()
            mock.return_value = mock_conn
            yield mock_conn

    @pytest.mark.asyncio
    async def test_create_vector_index_basic(self, mock_connection):
        """Test basic vector index creation with defaults."""
        await create_vector_index('test_index', 768)

        mock_connection.execute_command.assert_called_once()
        args = mock_connection.execute_command.call_args[0]

        assert args[0] == 'FT.CREATE'
        assert args[1] == 'test_index'
        assert 'ON' in args
        assert 'HASH' in args
        assert 'VECTOR' in args
        assert 'FLAT' in args

    @pytest.mark.asyncio
    async def test_create_vector_index_with_enums(self, mock_connection):
        """Test vector index creation with enum parameters."""
        await create_vector_index(
            'test_index',
            1536,
            index_type=IndexType.JSON,
            structure_type=StructureType.HNSW,
            distance_metric=DistanceMetric.COSINE,
        )

        args = mock_connection.execute_command.call_args[0]
        assert 'JSON' in args
        assert 'HNSW' in args
        assert 'COSINE' in args

    @pytest.mark.asyncio
    async def test_create_vector_index_with_strings(self, mock_connection):
        """Test vector index creation with string parameters."""
        await create_vector_index(
            'test_index', 1536, index_type='JSON', structure_type='HNSW', distance_metric='COSINE'
        )

        args = mock_connection.execute_command.call_args[0]
        assert 'JSON' in args
        assert 'HNSW' in args
        assert 'COSINE' in args

    @pytest.mark.asyncio
    async def test_create_vector_index_invalid_index_type(self, mock_connection):
        """Test error handling for invalid index type."""
        with pytest.raises(ValueError, match='Invalid index_type: INVALID'):
            await create_vector_index('test_index', 768, index_type='INVALID')

    @pytest.mark.asyncio
    async def test_create_vector_index_invalid_structure_type(self, mock_connection):
        """Test error handling for invalid structure type."""
        with pytest.raises(ValueError, match='Invalid structure_type: INVALID'):
            await create_vector_index('test_index', 768, structure_type='INVALID')

    @pytest.mark.asyncio
    async def test_create_vector_index_invalid_distance_metric(self, mock_connection):
        """Test error handling for invalid distance metric."""
        with pytest.raises(ValueError, match='Invalid distance_metric: INVALID'):
            await create_vector_index('test_index', 768, distance_metric='INVALID')

    @pytest.mark.asyncio
    async def test_create_vector_index_with_prefix(self, mock_connection):
        """Test vector index creation with prefix."""
        await create_vector_index('test_index', 768, prefix=['doc:', 'item:'])

        args = mock_connection.execute_command.call_args[0]
        assert 'PREFIX' in args
        assert '2' in args  # Number of prefixes
        assert 'doc:' in args
        assert 'item:' in args

    @pytest.mark.asyncio
    async def test_create_vector_index_hnsw_parameters(self, mock_connection):
        """Test HNSW-specific parameters."""
        await create_vector_index(
            'test_index',
            768,
            structure_type=StructureType.HNSW,
            initial_size=1000,
            max_outgoing_edges=16,
            ef_construction=200,
            ef_runtime=10,
        )

        args = mock_connection.execute_command.call_args[0]
        assert 'INITIAL_CAP' in args
        assert '1000' in args
        assert 'M' in args
        assert '16' in args
        assert 'EF_CONSTRUCTION' in args
        assert '200' in args
        assert 'EF_RUNTIME' in args
        assert '10' in args

    @pytest.mark.asyncio
    async def test_create_vector_index_with_field_alias(self, mock_connection):
        """Test vector index creation with field alias."""
        await create_vector_index(
            'test_index', 768, embedding_field='vector_data', embedding_field_alias='vec'
        )

        args = mock_connection.execute_command.call_args[0]
        assert 'vector_data' in args
        assert 'AS' in args
        assert 'vec' in args
