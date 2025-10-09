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
"""Tests for data import tools."""

import pytest
from awslabs.aws_healthomics_mcp_server.tools.data_import_tools import (
    discover_aho_genomic_files,
    get_aho_s3_file_metadata,
    list_aho_s3_bucket_contents,
    parse_s3_uri,
    prepare_aho_import_sources,
    validate_aho_s3_uri_format,
)
from mcp.server.fastmcp import Context
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    return MagicMock(spec=Context)


@pytest.fixture
def mock_s3_client():
    """Create a mock S3 client."""
    client = MagicMock()
    return client


class TestDataImportTools:
    """Test data import tools functionality."""

    def test_parse_s3_uri_valid(self):
        """Test parsing valid S3 URIs."""
        # Test basic S3 URI
        result = parse_s3_uri('s3://my-bucket/path/to/file.txt')
        assert result['bucket'] == 'my-bucket'
        assert result['key'] == 'path/to/file.txt'

        # Test S3 URI with just bucket
        result = parse_s3_uri('s3://my-bucket/')
        assert result['bucket'] == 'my-bucket'
        assert result['key'] == ''

        # Test S3 URI with nested path
        result = parse_s3_uri('s3://my-bucket/deep/nested/path/file.fastq.gz')
        assert result['bucket'] == 'my-bucket'
        assert result['key'] == 'deep/nested/path/file.fastq.gz'

    def test_parse_s3_uri_invalid(self):
        """Test parsing invalid S3 URIs."""
        with pytest.raises(ValueError):
            parse_s3_uri('http://bucket/file.txt')

        with pytest.raises(ValueError):
            parse_s3_uri('bucket/file.txt')

        with pytest.raises(ValueError):
            parse_s3_uri('')

    @pytest.mark.asyncio
    async def test_validate_aho_s3_uri_format_valid(self, mock_context):
        """Test validation of valid S3 URIs."""
        # Test valid S3 URI
        result = await validate_aho_s3_uri_format(
            mock_context, 's3://my-genomics-bucket/data/sample1.fastq.gz'
        )

        assert result['valid'] is True
        assert result['bucket'] == 'my-genomics-bucket'
        assert result['key'] == 'data/sample1.fastq.gz'

    @pytest.mark.asyncio
    async def test_validate_aho_s3_uri_format_invalid(self, mock_context):
        """Test validation of invalid S3 URIs."""
        # Test invalid protocol
        result = await validate_aho_s3_uri_format(mock_context, 'http://bucket/file.txt')
        assert result['valid'] is False
        assert 'must start with s3://' in result['error']

        # Test non-string input
        result = await validate_aho_s3_uri_format(mock_context, 123)
        assert result['valid'] is False
        assert 'must be a string' in result['error']

        # Test empty bucket
        result = await validate_aho_s3_uri_format(mock_context, 's3:///file.txt')
        assert result['valid'] is False
        assert 'cannot be empty' in result['error']

    @patch('awslabs.aws_healthomics_mcp_server.tools.data_import_tools.create_aws_client')
    @pytest.mark.asyncio
    async def test_discover_aho_genomic_files_success(
        self, mock_create_client, mock_context, mock_s3_client
    ):
        """Test successful genomic file discovery."""
        # Arrange
        mock_create_client.return_value = mock_s3_client

        # Mock paginator
        mock_paginator = MagicMock()
        mock_s3_client.get_paginator.return_value = mock_paginator

        from datetime import datetime

        mock_page = {
            'Contents': [
                {
                    'Key': 'genomics/sample1_R1.fastq.gz',
                    'Size': 1024000,
                    'LastModified': datetime(2023, 10, 1, 12, 0, 0),
                    'ETag': '"abc123"',
                },
                {
                    'Key': 'genomics/sample1_R2.fastq.gz',
                    'Size': 1024000,
                    'LastModified': datetime(2023, 10, 1, 12, 0, 0),
                    'ETag': '"def456"',
                },
                {
                    'Key': 'genomics/variants.vcf.gz',
                    'Size': 512000,
                    'LastModified': datetime(2023, 10, 1, 13, 0, 0),
                    'ETag': '"ghi789"',
                },
            ]
        }
        mock_paginator.paginate.return_value = [mock_page]

        # Act
        result = await discover_aho_genomic_files(
            mock_context, 's3://test-bucket/genomics/', file_types=['FASTQ', 'VCF'], max_files=100
        )

        # Assert
        assert 'discoveredFiles' in result
        assert 'totalCount' in result
        assert result['totalCount'] == 3
        assert len(result['discoveredFiles']) == 3

        # Check FASTQ files
        fastq_files = [f for f in result['discoveredFiles'] if f['fileType'] == 'FASTQ']
        assert len(fastq_files) == 2

        # Check VCF files
        vcf_files = [f for f in result['discoveredFiles'] if f['fileType'] == 'VCF']
        assert len(vcf_files) == 1

        # Verify S3 URIs are correctly formed
        for file_info in result['discoveredFiles']:
            assert file_info['s3Uri'].startswith('s3://test-bucket/')

    @patch('awslabs.aws_healthomics_mcp_server.tools.data_import_tools.create_aws_client')
    @pytest.mark.asyncio
    async def test_list_aho_s3_bucket_contents_success(
        self, mock_create_client, mock_context, mock_s3_client
    ):
        """Test successful S3 bucket content listing."""
        # Arrange
        mock_create_client.return_value = mock_s3_client

        mock_paginator = MagicMock()
        mock_s3_client.get_paginator.return_value = mock_paginator

        from datetime import datetime

        mock_page = {
            'Contents': [
                {
                    'Key': 'data/file1.txt',
                    'Size': 1024,
                    'LastModified': datetime(2023, 10, 1, 12, 0, 0),
                    'ETag': '"abc123"',
                    'StorageClass': 'STANDARD',
                },
                {
                    'Key': 'data/file2.txt',
                    'Size': 2048,
                    'LastModified': datetime(2023, 10, 1, 13, 0, 0),
                    'ETag': '"def456"',
                    'StorageClass': 'STANDARD',
                },
            ]
        }
        mock_paginator.paginate.return_value = [mock_page]

        # Act
        result = await list_aho_s3_bucket_contents(
            mock_context, 's3://test-bucket/data/', pattern='*.txt', max_keys=1000
        )

        # Assert
        assert 'objects' in result
        assert 'totalCount' in result
        assert result['totalCount'] == 2
        assert len(result['objects']) == 2
        assert result['appliedPattern'] == '*.txt'

        for obj in result['objects']:
            assert 's3Uri' in obj
            assert 'fileName' in obj
            assert 'size' in obj

    @patch('awslabs.aws_healthomics_mcp_server.tools.data_import_tools.create_aws_client')
    @pytest.mark.asyncio
    async def test_get_aho_s3_file_metadata_success(
        self, mock_create_client, mock_context, mock_s3_client
    ):
        """Test successful S3 file metadata retrieval."""
        # Arrange
        mock_create_client.return_value = mock_s3_client

        from datetime import datetime

        mock_response = {
            'ContentLength': 1024000,
            'LastModified': datetime(2023, 10, 1, 12, 0, 0),
            'ETag': '"abc123def456"',  # pragma: allowlist secret
            'ContentType': 'application/gzip',
            'StorageClass': 'STANDARD',
            'Metadata': {'sample-id': 'sample-001', 'experiment': 'rna-seq'},
        }
        mock_s3_client.head_object.return_value = mock_response

        # Act
        result = await get_aho_s3_file_metadata(
            mock_context, 's3://test-bucket/data/sample1.fastq.gz'
        )

        # Assert
        assert 'fileMetadata' in result
        metadata = result['fileMetadata']
        assert metadata['s3Uri'] == 's3://test-bucket/data/sample1.fastq.gz'
        assert metadata['bucket'] == 'test-bucket'
        assert metadata['key'] == 'data/sample1.fastq.gz'
        assert metadata['fileName'] == 'sample1.fastq.gz'
        assert metadata['size'] == 1024000
        assert metadata['contentType'] == 'application/gzip'
        assert 'sample-id' in metadata['metadata']

    @patch('awslabs.aws_healthomics_mcp_server.tools.data_import_tools.create_aws_client')
    @pytest.mark.asyncio
    async def test_get_aho_s3_file_metadata_not_found(
        self, mock_create_client, mock_context, mock_s3_client
    ):
        """Test S3 file metadata retrieval for non-existent file."""
        # Arrange
        from botocore.exceptions import ClientError

        mock_create_client.return_value = mock_s3_client

        error_response = {
            'Error': {'Code': 'NoSuchKey', 'Message': 'The specified key does not exist.'}
        }
        mock_s3_client.head_object.side_effect = ClientError(error_response, 'HeadObject')

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await get_aho_s3_file_metadata(mock_context, 's3://test-bucket/nonexistent.txt')

        assert 'File not found' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_prepare_aho_import_sources_success(self, mock_context):
        """Test successful preparation of import sources."""
        # Arrange
        files = [
            {'s3Uri': 's3://test-bucket/sample1_R1.fastq.gz', 'fileType': 'FASTQ'},
            {'s3Uri': 's3://test-bucket/sample1_R2.fastq.gz', 'fileType': 'FASTQ'},
        ]

        # Act
        result = await prepare_aho_import_sources(
            mock_context,
            files=files,
            sample_id='sample-001',
            subject_id='patient-123',
            reference_arn='arn:aws:omics:us-east-1:123456789012:referenceStore/123456789012345678/reference/1234567890123456',
        )

        # Assert
        assert 'importSources' in result
        assert 'totalFiles' in result
        assert 'configuration' in result

        assert result['totalFiles'] == 2
        assert result['configuration']['sampleId'] == 'sample-001'
        assert result['configuration']['subjectId'] == 'patient-123'

        # Check that paired-end FASTQ files are properly configured
        sources = result['importSources']
        assert len(sources) == 2

        for source in sources:
            assert 'sourceFileType' in source
            assert 'sourceFiles' in source
            assert source['sourceFileType'] == 'FASTQ'
            assert 'sampleId' in source
            assert 'subjectId' in source

    @pytest.mark.asyncio
    async def test_prepare_aho_import_sources_paired_end(self, mock_context):
        """Test preparation of paired-end FASTQ import sources."""
        # Arrange
        files = [
            {'s3Uri': 's3://test-bucket/sample1_R1.fastq.gz', 'fileType': 'FASTQ'},
            {'s3Uri': 's3://test-bucket/sample1_R2.fastq.gz', 'fileType': 'FASTQ'},
        ]

        # Act
        result = await prepare_aho_import_sources(
            mock_context, files=files, sample_id='sample-001'
        )

        # Assert
        sources = result['importSources']

        # Find the R1 file source
        r1_source = next(
            (s for s in sources if 'sample1_R1.fastq.gz' in s['sourceFiles']['source1']), None
        )
        assert r1_source is not None

        # Check if R2 was automatically paired
        if 'source2' in r1_source['sourceFiles']:
            assert 'sample1_R2.fastq.gz' in r1_source['sourceFiles']['source2']
