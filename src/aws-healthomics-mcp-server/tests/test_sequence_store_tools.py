# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Tests for sequence store tools."""

import pytest
from awslabs.aws_healthomics_mcp_server.tools.sequence_store_tools import (
    get_aho_read_set,
    get_aho_read_set_import_job,
    list_aho_read_sets,
    list_aho_sequence_stores,
    start_aho_read_set_import_job,
)
from mcp.server.fastmcp import Context
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    return MagicMock(spec=Context)


@pytest.fixture
def mock_omics_client():
    """Create a mock HealthOmics client."""
    client = MagicMock()
    return client


class TestSequenceStoreTools:
    """Test sequence store tools functionality."""

    @patch('awslabs.aws_healthomics_mcp_server.tools.sequence_store_tools.get_omics_client')
    @pytest.mark.asyncio
    async def test_list_aho_sequence_stores_success(
        self, mock_get_client, mock_context, mock_omics_client
    ):
        """Test successful listing of sequence stores."""
        # Arrange
        mock_get_client.return_value = mock_omics_client
        mock_response = {
            'sequenceStores': [
                {
                    'id': 'test-store-1',
                    'name': 'Test Store 1',
                    'arn': 'arn:aws:omics:us-east-1:123456789012:sequenceStore/test-store-1',
                }
            ]
        }
        mock_omics_client.list_sequence_stores.return_value = mock_response

        # Act
        result = await list_aho_sequence_stores(mock_context, max_results=10)

        # Assert
        assert 'sequenceStores' in result
        assert 'totalCount' in result
        assert result['totalCount'] == 1
        assert len(result['sequenceStores']) == 1
        assert result['sequenceStores'][0]['id'] == 'test-store-1'
        mock_omics_client.list_sequence_stores.assert_called_once_with(maxResults=10)

    @patch('awslabs.aws_healthomics_mcp_server.tools.sequence_store_tools.get_omics_client')
    @pytest.mark.asyncio
    async def test_list_aho_read_sets_success(
        self, mock_get_client, mock_context, mock_omics_client
    ):
        """Test successful listing of read sets."""
        # Arrange
        mock_get_client.return_value = mock_omics_client
        mock_response = {
            'readSets': [
                {
                    'id': 'test-readset-1',
                    'arn': 'arn:aws:omics:us-east-1:123456789012:readSet/test-readset-1',
                    'sequenceStoreId': 'test-store-1',
                    'sampleId': 'sample-1',
                    'subjectId': 'subject-1',
                }
            ]
        }
        mock_omics_client.list_read_sets.return_value = mock_response

        # Act
        result = await list_aho_read_sets(
            mock_context, sequence_store_id='test-store-1', max_results=10
        )

        # Assert
        assert 'readSets' in result
        assert 'totalCount' in result
        assert 'sequenceStoreId' in result
        assert result['sequenceStoreId'] == 'test-store-1'
        assert result['totalCount'] == 1
        assert len(result['readSets']) == 1
        assert result['readSets'][0]['id'] == 'test-readset-1'
        mock_omics_client.list_read_sets.assert_called_once()

    @patch('awslabs.aws_healthomics_mcp_server.tools.sequence_store_tools.get_omics_client')
    @pytest.mark.asyncio
    async def test_get_aho_read_set_success(
        self, mock_get_client, mock_context, mock_omics_client
    ):
        """Test successful retrieval of read set metadata."""
        # Arrange
        mock_get_client.return_value = mock_omics_client
        mock_response = {
            'id': 'test-readset-1',
            'arn': 'arn:aws:omics:us-east-1:123456789012:readSet/test-readset-1',
            'sequenceStoreId': 'test-store-1',
            'name': 'Test Read Set',
            'sampleId': 'sample-1',
            'subjectId': 'subject-1',
            'status': 'ACTIVE',
            'fileType': 'FASTQ',
        }
        mock_omics_client.get_read_set_metadata.return_value = mock_response

        # Act
        result = await get_aho_read_set(
            mock_context, sequence_store_id='test-store-1', read_set_id='test-readset-1'
        )

        # Assert
        assert 'readSet' in result
        assert 'sequenceStoreId' in result
        assert result['sequenceStoreId'] == 'test-store-1'
        assert result['readSet']['id'] == 'test-readset-1'
        assert result['readSet']['status'] == 'ACTIVE'
        mock_omics_client.get_read_set_metadata.assert_called_once_with(
            sequenceStoreId='test-store-1', id='test-readset-1'
        )

    @patch('awslabs.aws_healthomics_mcp_server.tools.sequence_store_tools.get_omics_client')
    @pytest.mark.asyncio
    async def test_start_aho_read_set_import_job_success(
        self, mock_get_client, mock_context, mock_omics_client
    ):
        """Test successful start of read set import job."""
        # Arrange
        mock_get_client.return_value = mock_omics_client
        mock_response = {
            'id': 'import-job-123',
            'sequenceStoreId': 'test-store-1',
            'roleArn': 'arn:aws:iam::123456789012:role/HealthOmicsRole',
            'status': 'SUBMITTED',
            'creationTime': '2023-10-01T12:00:00Z',
        }
        mock_omics_client.start_read_set_import_job.return_value = mock_response

        sources = [
            {
                'sourceFileType': 'FASTQ',
                'sourceFiles': {
                    'source1': 's3://test-bucket/sample1_R1.fastq.gz',
                    'source2': 's3://test-bucket/sample1_R2.fastq.gz',
                },
                'sampleId': 'sample-1',
                'subjectId': 'subject-1',
            }
        ]

        # Act
        result = await start_aho_read_set_import_job(
            mock_context,
            sequence_store_id='test-store-1',
            role_arn='arn:aws:iam::123456789012:role/HealthOmicsRole',
            sources=sources,
        )

        # Assert
        assert 'id' in result
        assert 'status' in result
        assert result['id'] == 'import-job-123'
        assert result['status'] == 'SUBMITTED'
        assert result['sequenceStoreId'] == 'test-store-1'
        mock_omics_client.start_read_set_import_job.assert_called_once()

    @patch('awslabs.aws_healthomics_mcp_server.tools.sequence_store_tools.get_omics_client')
    @pytest.mark.asyncio
    async def test_list_aho_sequence_stores_client_error(
        self, mock_get_client, mock_context, mock_omics_client
    ):
        """Test handling of AWS client errors."""
        # Arrange
        from botocore.exceptions import ClientError

        mock_get_client.return_value = mock_omics_client
        error_response = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'User is not authorized to perform this operation',
            }
        }
        mock_omics_client.list_sequence_stores.side_effect = ClientError(
            error_response, 'ListSequenceStores'
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await list_aho_sequence_stores(mock_context, max_results=10)

        assert 'AccessDeniedException' in str(exc_info.value)
        assert 'User is not authorized' in str(exc_info.value)

    @patch('awslabs.aws_healthomics_mcp_server.tools.sequence_store_tools.get_omics_client')
    @pytest.mark.asyncio
    async def test_list_aho_read_sets_with_filters(
        self, mock_get_client, mock_context, mock_omics_client
    ):
        """Test read set listing with filters applied."""
        # Arrange
        mock_get_client.return_value = mock_omics_client
        mock_response = {
            'readSets': [
                {'id': 'test-readset-1', 'subjectId': 'human-sample-1', 'sampleId': 'sample-1'}
            ]
        }
        mock_omics_client.list_read_sets.return_value = mock_response

        # Act
        result = await list_aho_read_sets(
            mock_context,
            sequence_store_id='test-store-1',
            species='human',
            chromosome='chr1',
            uploaded_after='2023-01-01T00:00:00Z',
            max_results=10,
        )

        # Assert
        assert 'appliedFilters' in result
        assert result['appliedFilters']['species'] == 'human'
        assert result['appliedFilters']['chromosome'] == 'chr1'
        assert result['appliedFilters']['uploadedAfter'] == '2023-01-01T00:00:00Z'
        mock_omics_client.list_read_sets.assert_called_once()

    @patch('awslabs.aws_healthomics_mcp_server.tools.sequence_store_tools.get_omics_client')
    @pytest.mark.asyncio
    async def test_get_aho_read_set_import_job_success(
        self, mock_get_client, mock_context, mock_omics_client
    ):
        """Test successful retrieval of import job status."""
        # Arrange
        mock_get_client.return_value = mock_omics_client
        mock_response = {
            'id': 'import-job-123',
            'sequenceStoreId': 'test-store-1',
            'roleArn': 'arn:aws:iam::123456789012:role/HealthOmicsRole',
            'status': 'COMPLETED',
            'creationTime': '2023-10-01T12:00:00Z',
            'completionTime': '2023-10-01T12:30:00Z',
            'sources': [],
        }
        mock_omics_client.get_read_set_import_job.return_value = mock_response

        # Act
        result = await get_aho_read_set_import_job(
            mock_context, sequence_store_id='test-store-1', import_job_id='import-job-123'
        )

        # Assert
        assert result['id'] == 'import-job-123'
        assert result['status'] == 'COMPLETED'
        assert 'completionTime' in result
        mock_omics_client.get_read_set_import_job.assert_called_once_with(
            sequenceStoreId='test-store-1', id='import-job-123'
        )
