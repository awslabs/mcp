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

"""Tests for S3File model and related utilities."""

import pytest
from awslabs.aws_healthomics_mcp_server.models import (
    GenomicsFile,
    GenomicsFileType,
    S3File,
    build_s3_uri,
    create_genomics_file_from_s3_object,
    create_s3_file_from_object,
    get_s3_file_associations,
    parse_s3_uri,
)
from datetime import datetime


class TestS3File:
    """Test cases for S3File model."""

    def test_s3_file_creation(self):
        """Test basic S3File creation."""
        s3_file = S3File(
            bucket='test-bucket', key='path/to/file.txt', size_bytes=1024, storage_class='STANDARD'
        )

        assert s3_file.bucket == 'test-bucket'
        assert s3_file.key == 'path/to/file.txt'
        assert s3_file.uri == 's3://test-bucket/path/to/file.txt'
        assert s3_file.filename == 'file.txt'
        assert s3_file.directory == 'path/to'
        assert s3_file.extension == 'txt'

    def test_s3_file_from_uri(self):
        """Test creating S3File from URI."""
        uri = 's3://my-bucket/data/sample.fastq.gz'
        s3_file = S3File.from_uri(uri, size_bytes=2048)

        assert s3_file.bucket == 'my-bucket'
        assert s3_file.key == 'data/sample.fastq.gz'
        assert s3_file.uri == uri
        assert s3_file.filename == 'sample.fastq.gz'
        assert s3_file.extension == 'gz'
        assert s3_file.size_bytes == 2048

    def test_s3_file_validation(self):
        """Test S3File validation."""
        # Test invalid bucket name
        with pytest.raises(ValueError, match='Bucket name must be between 3 and 63 characters'):
            S3File(bucket='ab', key='test.txt')

        # Test empty key
        with pytest.raises(ValueError, match='Object key cannot be empty'):
            S3File(bucket='test-bucket', key='')

        # Test invalid URI
        with pytest.raises(ValueError, match='Invalid S3 URI format'):
            S3File.from_uri('http://example.com/file.txt')

    def test_s3_file_properties(self):
        """Test S3File properties and methods."""
        s3_file = S3File(
            bucket='genomics-data', key='samples/patient1/reads.bam', version_id='abc123'
        )

        assert (
            s3_file.arn == 'arn:aws:s3:::genomics-data/samples/patient1/reads.bam?versionId=abc123'
        )
        assert 'genomics-data' in s3_file.console_url
        assert s3_file.filename == 'reads.bam'
        assert s3_file.directory == 'samples/patient1'
        assert s3_file.extension == 'bam'

    def test_s3_file_key_manipulation(self):
        """Test S3File key manipulation methods."""
        s3_file = S3File(bucket='test-bucket', key='data/sample.fastq')

        # Test with_key
        new_file = s3_file.with_key('data/sample2.fastq')
        assert new_file.key == 'data/sample2.fastq'
        assert new_file.bucket == 'test-bucket'

        # Test with_suffix
        index_file = s3_file.with_suffix('.bai')
        assert index_file.key == 'data/sample.fastq.bai'

        # Test with_extension
        bam_file = s3_file.with_extension('bam')
        assert bam_file.key == 'data/sample.bam'

    def test_s3_file_directory_operations(self):
        """Test S3File directory-related operations."""
        s3_file = S3File(bucket='test-bucket', key='project/samples/file.txt')

        assert s3_file.is_in_directory('project')
        assert s3_file.is_in_directory('project/samples')
        assert not s3_file.is_in_directory('other')

        assert s3_file.get_relative_path('project') == 'samples/file.txt'
        assert s3_file.get_relative_path('project/samples') == 'file.txt'
        assert s3_file.get_relative_path('') == 'project/samples/file.txt'


class TestGenomicsFileIntegration:
    """Test GenomicsFile integration with S3File."""

    def test_genomics_file_s3_integration(self):
        """Test GenomicsFile with S3 path integration."""
        genomics_file = GenomicsFile(
            path='s3://genomics-bucket/sample.fastq',
            file_type=GenomicsFileType.FASTQ,
            size_bytes=1000000,
            storage_class='STANDARD',
            last_modified=datetime.now(),
            tags={'sample_id': 'S001'},
        )

        # Test s3_file property
        s3_file = genomics_file.s3_file
        assert s3_file is not None
        assert s3_file.bucket == 'genomics-bucket'
        assert s3_file.key == 'sample.fastq'
        assert s3_file.size_bytes == 1000000

        # Test filename and extension properties
        assert genomics_file.filename == 'sample.fastq'
        assert genomics_file.extension == 'fastq'

    def test_genomics_file_from_s3_file(self):
        """Test creating GenomicsFile from S3File."""
        s3_file = S3File(
            bucket='test-bucket',
            key='data/reads.bam',
            size_bytes=5000000,
            storage_class='STANDARD_IA',
        )

        genomics_file = GenomicsFile.from_s3_file(
            s3_file=s3_file, file_type=GenomicsFileType.BAM, source_system='s3'
        )

        assert genomics_file.path == 's3://test-bucket/data/reads.bam'
        assert genomics_file.file_type == GenomicsFileType.BAM
        assert genomics_file.size_bytes == 5000000
        assert genomics_file.storage_class == 'STANDARD_IA'
        assert genomics_file.source_system == 's3'


class TestS3Utilities:
    """Test S3 utility functions."""

    def test_create_s3_file_from_object(self):
        """Test creating S3File from S3 object dictionary."""
        s3_object = {
            'Key': 'data/sample.vcf',
            'Size': 2048,
            'LastModified': datetime.now(),
            'StorageClass': 'STANDARD',
            'ETag': '"abc123def456"',  # pragma: allowlist secret
        }

        s3_file = create_s3_file_from_object(
            bucket='genomics-bucket', s3_object=s3_object, tags={'project': 'cancer_study'}
        )

        assert s3_file.bucket == 'genomics-bucket'
        assert s3_file.key == 'data/sample.vcf'
        assert s3_file.size_bytes == 2048
        assert s3_file.storage_class == 'STANDARD'
        assert s3_file.etag == 'abc123def456'  # ETag quotes removed  # pragma: allowlist secret
        assert s3_file.tags['project'] == 'cancer_study'

    def test_create_genomics_file_from_s3_object(self):
        """Test creating GenomicsFile from S3 object dictionary."""
        s3_object = {
            'Key': 'samples/patient1.bam',
            'Size': 10000000,
            'LastModified': datetime.now(),
            'StorageClass': 'STANDARD',
        }

        genomics_file = create_genomics_file_from_s3_object(
            bucket='genomics-data',
            s3_object=s3_object,
            file_type=GenomicsFileType.BAM,
            tags={'patient_id': 'P001'},
        )

        assert genomics_file.path == 's3://genomics-data/samples/patient1.bam'
        assert genomics_file.file_type == GenomicsFileType.BAM
        assert genomics_file.size_bytes == 10000000
        assert genomics_file.tags['patient_id'] == 'P001'

    def test_build_and_parse_s3_uri(self):
        """Test S3 URI building and parsing utilities."""
        bucket = 'my-bucket'
        key = 'path/to/file.txt'

        # Test building URI
        uri = build_s3_uri(bucket, key)
        assert uri == 's3://my-bucket/path/to/file.txt'

        # Test parsing URI
        parsed_bucket, parsed_key = parse_s3_uri(uri)
        assert parsed_bucket == bucket
        assert parsed_key == key

        # Test error cases
        with pytest.raises(ValueError, match='Bucket name cannot be empty'):
            build_s3_uri('', key)

        with pytest.raises(ValueError, match='Invalid S3 URI format'):
            parse_s3_uri('http://example.com/file.txt')

    def test_get_s3_file_associations(self):
        """Test S3 file association detection."""
        # Test BAM file associations
        bam_file = S3File(bucket='test-bucket', key='data/sample.bam')
        associations = get_s3_file_associations(bam_file)

        # Should find potential index files
        index_keys = [assoc.key for assoc in associations]
        assert 'data/sample.bam.bai' in index_keys
        assert 'data/sample.bai' in index_keys

        # Test FASTQ R1/R2 associations
        r1_file = S3File(bucket='test-bucket', key='reads/sample_R1_001.fastq.gz')
        associations = get_s3_file_associations(r1_file)

        r2_keys = [assoc.key for assoc in associations]
        assert 'reads/sample_R2_001.fastq.gz' in r2_keys

        # Test FASTA index associations
        fasta_file = S3File(bucket='test-bucket', key='reference/genome.fasta')
        associations = get_s3_file_associations(fasta_file)

        fai_keys = [assoc.key for assoc in associations]
        assert 'reference/genome.fasta.fai' in fai_keys
        assert 'reference/genome.fai' in fai_keys
