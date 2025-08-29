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

"""Tests for the S3 Vectors MCP Server."""

import json
import os
import pytest
from awslabs.s3_vectors_mcp_server.server import (
    app,
    get_aws_session,
    get_env_or_param,
    get_optional_env_or_param,
    s3vectors_put,
    s3vectors_query,
)
from unittest.mock import MagicMock, patch


class TestHelperFunctions:
    """Test cases for helper functions."""

    def test_get_aws_session_with_profile(self):
        """Test get_aws_session with profile name."""
        with patch('boto3.Session') as mock_session:
            get_aws_session('test-profile')
            mock_session.assert_called_once_with(profile_name='test-profile')

    def test_get_aws_session_without_profile(self):
        """Test get_aws_session without profile name."""
        with patch('boto3.Session') as mock_session:
            get_aws_session()
            mock_session.assert_called_once_with()

    def test_get_env_or_param_with_param(self):
        """Test get_env_or_param with parameter value."""
        result = get_env_or_param('param_value', 'ENV_VAR', 'param_name')
        assert result == 'param_value'

    def test_get_env_or_param_with_env_var(self):
        """Test get_env_or_param with environment variable."""
        with patch.dict(os.environ, {'TEST_ENV_VAR': 'env_value'}):
            result = get_env_or_param(None, 'TEST_ENV_VAR', 'param_name')
            assert result == 'env_value'

    def test_get_env_or_param_missing(self):
        """Test get_env_or_param with missing values."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match='param_name must be provided'):
                get_env_or_param(None, 'MISSING_ENV_VAR', 'param_name')

    def test_get_optional_env_or_param_with_param(self):
        """Test get_optional_env_or_param with parameter value."""
        result = get_optional_env_or_param('param_value', 'ENV_VAR')
        assert result == 'param_value'

    def test_get_optional_env_or_param_with_env_var(self):
        """Test get_optional_env_or_param with environment variable."""
        with patch.dict(os.environ, {'TEST_ENV_VAR': 'env_value'}):
            result = get_optional_env_or_param(None, 'TEST_ENV_VAR')
            assert result == 'env_value'

    def test_get_optional_env_or_param_missing(self):
        """Test get_optional_env_or_param with missing values."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_optional_env_or_param(None, 'MISSING_ENV_VAR')
            assert result is None


class TestS3VectorsPut:
    """Test cases for s3vectors_put function."""

    @pytest.fixture
    def mock_env_vars(self):
        """Mock environment variables for testing."""
        env_vars = {
            'S3VECTORS_BUCKET_NAME': 'test-bucket',
            'S3VECTORS_INDEX_NAME': 'test-index',
            'S3VECTORS_MODEL_ID': 'amazon.titan-embed-text-v1',
            'S3VECTORS_REGION': 'us-east-1',
        }
        with patch.dict(os.environ, env_vars):
            yield env_vars

    @pytest.fixture
    def mock_services(self):
        """Mock AWS services."""
        with (
            patch('awslabs.s3_vectors_mcp_server.server.get_aws_session') as mock_session,
            patch('awslabs.s3_vectors_mcp_server.server.BedrockService') as mock_bedrock,
            patch('awslabs.s3_vectors_mcp_server.server.S3VectorService') as mock_s3vector,
            patch('awslabs.s3_vectors_mcp_server.server.get_region') as mock_get_region,
        ):
            # Setup mock returns
            mock_get_region.return_value = 'us-east-1'
            mock_bedrock_instance = MagicMock()
            mock_bedrock_instance.embed_text.return_value = [0.1, 0.2, 0.3]
            mock_bedrock.return_value = mock_bedrock_instance

            mock_s3vector_instance = MagicMock()
            mock_s3vector_instance.put_vector.return_value = 'test-vector-id'
            mock_s3vector.return_value = mock_s3vector_instance

            yield {
                'session': mock_session,
                'bedrock': mock_bedrock,
                's3vector': mock_s3vector,
                'get_region': mock_get_region,
            }

    @pytest.mark.asyncio
    async def test_s3vectors_put_success(self, mock_env_vars, mock_services):
        """Test successful s3vectors_put operation."""
        result = await s3vectors_put(
            text='Test text for embedding', vector_id='test-id', metadata={'category': 'test'}
        )

        result_dict = json.loads(result)
        assert result_dict['success'] is True
        assert result_dict['vector_id'] == 'test-vector-id'
        assert result_dict['bucket'] == 'test-bucket'
        assert result_dict['index'] == 'test-index'
        assert result_dict['metadata'] == {'category': 'test'}

    @pytest.mark.asyncio
    async def test_s3vectors_put_auto_generate_id(self, mock_env_vars, mock_services):
        """Test s3vectors_put with auto-generated vector ID."""
        result = await s3vectors_put(text='Test text')

        result_dict = json.loads(result)
        assert result_dict['success'] is True
        assert result_dict['vector_id'] == 'test-vector-id'

    @pytest.mark.asyncio
    async def test_s3vectors_put_missing_env_var(self):
        """Test s3vectors_put with missing environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            result = await s3vectors_put(text='Test text')

            result_dict = json.loads(result)
            assert result_dict['success'] is False
            assert 'error' in result_dict
            assert 'S3VECTORS_BUCKET_NAME' in result_dict['error']

    @pytest.mark.asyncio
    async def test_s3vectors_put_service_error(self, mock_env_vars):
        """Test s3vectors_put with service error."""
        with (
            patch('awslabs.s3_vectors_mcp_server.server.get_aws_session'),
            patch(
                'awslabs.s3_vectors_mcp_server.server.BedrockService',
                side_effect=Exception('Service error'),
            ),
            patch('awslabs.s3_vectors_mcp_server.server.get_region', return_value='us-east-1'),
        ):
            result = await s3vectors_put(text='Test text')

            result_dict = json.loads(result)
            assert result_dict['success'] is False
            assert 'Service error' in result_dict['error']


class TestS3VectorsQuery:
    """Test cases for s3vectors_query function."""

    @pytest.fixture
    def mock_env_vars(self):
        """Mock environment variables for testing."""
        env_vars = {
            'S3VECTORS_BUCKET_NAME': 'test-bucket',
            'S3VECTORS_INDEX_NAME': 'test-index',
            'S3VECTORS_MODEL_ID': 'amazon.titan-embed-text-v1',
            'S3VECTORS_REGION': 'us-east-1',
        }
        with patch.dict(os.environ, env_vars):
            yield env_vars

    @pytest.fixture
    def mock_services(self):
        """Mock AWS services for query."""
        with (
            patch('awslabs.s3_vectors_mcp_server.server.get_aws_session') as mock_session,
            patch('awslabs.s3_vectors_mcp_server.server.BedrockService') as mock_bedrock,
            patch('awslabs.s3_vectors_mcp_server.server.S3VectorService') as mock_s3vector,
            patch('awslabs.s3_vectors_mcp_server.server.get_region') as mock_get_region,
        ):
            # Setup mock returns
            mock_get_region.return_value = 'us-east-1'
            mock_bedrock_instance = MagicMock()
            mock_bedrock_instance.embed_text.return_value = [0.1, 0.2, 0.3]
            mock_bedrock.return_value = mock_bedrock_instance

            mock_s3vector_instance = MagicMock()
            mock_s3vector_instance.query_vectors.return_value = [
                {'vectorId': 'vector-1', 'similarity': 0.95, 'metadata': {'category': 'test'}},
                {'vectorId': 'vector-2', 'similarity': 0.85, 'metadata': {'category': 'example'}},
            ]
            mock_s3vector.return_value = mock_s3vector_instance

            yield {
                'session': mock_session,
                'bedrock': mock_bedrock,
                's3vector': mock_s3vector,
                'get_region': mock_get_region,
            }

    @pytest.mark.asyncio
    async def test_s3vectors_query_success(self, mock_env_vars, mock_services):
        """Test successful s3vectors_query operation."""
        result = await s3vectors_query(
            query_text='Find similar vectors', top_k=5, return_metadata=True, return_distance=True
        )

        result_dict = json.loads(result)
        assert result_dict['success'] is True
        assert result_dict['query_text'] == 'Find similar vectors'
        assert result_dict['top_k'] == 5
        assert result_dict['results_count'] == 2
        assert len(result_dict['results']) == 2
        assert result_dict['results'][0]['vector_id'] == 'vector-1'
        assert result_dict['results'][0]['similarity'] == 0.95

    @pytest.mark.asyncio
    async def test_s3vectors_query_with_filter(self, mock_env_vars, mock_services):
        """Test s3vectors_query with filter expression."""
        filter_expr = {'category': {'$eq': 'test'}}
        result = await s3vectors_query(query_text='Find similar vectors', filter_expr=filter_expr)

        result_dict = json.loads(result)
        assert result_dict['success'] is True
        assert result_dict['filter'] == filter_expr

    @pytest.mark.asyncio
    async def test_s3vectors_query_missing_env_var(self):
        """Test s3vectors_query with missing environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            result = await s3vectors_query(query_text='Test query')

            result_dict = json.loads(result)
            assert result_dict['success'] is False
            assert 'error' in result_dict
            assert 'S3VECTORS_BUCKET_NAME' in result_dict['error']


class TestServerApp:
    """Test cases for the server app configuration."""

    def test_app_initialization(self):
        """Test that the app is properly initialized."""
        assert app.name == 's3-vectors-server'
        assert hasattr(app, 'log_dir')

    def test_app_log_dir_configuration(self):
        """Test log directory configuration."""
        # Test that log_dir is set based on platform
        assert app.log_dir is not None

        # The exact path depends on the platform, but it should be a string
        assert isinstance(app.log_dir, str)
