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

"""Unit tests for store management data models."""

import pytest
from awslabs.aws_healthomics_mcp_server.models.store import (
    ImportJobStatus,
    ReadSetFileType,
    ReadSetImportSource,
    ReadSetStatus,
    ReadSetSummary,
    ReferenceImportSource,
    ReferenceStatus,
    ReferenceStoreDetail,
    ReferenceStoreSummary,
    ReferenceSummary,
    SequenceStoreDetail,
    SequenceStoreSummary,
)
from datetime import datetime, timezone
from pydantic import ValidationError


# --- Enum Tests ---


class TestReadSetFileTypeEnum:
    """Tests for ReadSetFileType enum."""

    def test_values(self):
        assert ReadSetFileType.FASTQ == 'FASTQ'
        assert ReadSetFileType.BAM == 'BAM'
        assert ReadSetFileType.CRAM == 'CRAM'
        assert ReadSetFileType.UBAM == 'UBAM'

    def test_membership(self):
        assert ReadSetFileType.FASTQ in ReadSetFileType
        assert 'INVALID' not in [e.value for e in ReadSetFileType]


class TestReadSetStatusEnum:
    """Tests for ReadSetStatus enum."""

    def test_values(self):
        assert ReadSetStatus.ARCHIVED == 'ARCHIVED'
        assert ReadSetStatus.ACTIVATING == 'ACTIVATING'
        assert ReadSetStatus.ACTIVE == 'ACTIVE'
        assert ReadSetStatus.DELETING == 'DELETING'
        assert ReadSetStatus.DELETED == 'DELETED'
        assert ReadSetStatus.PROCESSING_UPLOAD == 'PROCESSING_UPLOAD'
        assert ReadSetStatus.UPLOAD_FAILED == 'UPLOAD_FAILED'

    def test_membership(self):
        assert ReadSetStatus.ACTIVE in ReadSetStatus
        assert 'INVALID' not in [e.value for e in ReadSetStatus]


class TestImportJobStatusEnum:
    """Tests for ImportJobStatus enum."""

    def test_values(self):
        assert ImportJobStatus.SUBMITTED == 'SUBMITTED'
        assert ImportJobStatus.IN_PROGRESS == 'IN_PROGRESS'
        assert ImportJobStatus.CANCELLING == 'CANCELLING'
        assert ImportJobStatus.CANCELLED == 'CANCELLED'
        assert ImportJobStatus.FAILED == 'FAILED'
        assert ImportJobStatus.COMPLETED == 'COMPLETED'
        assert ImportJobStatus.COMPLETED_WITH_FAILURES == 'COMPLETED_WITH_FAILURES'

    def test_membership(self):
        assert ImportJobStatus.COMPLETED in ImportJobStatus
        assert 'INVALID' not in [e.value for e in ImportJobStatus]


class TestReferenceStatusEnum:
    """Tests for ReferenceStatus enum."""

    def test_values(self):
        assert ReferenceStatus.ACTIVE == 'ACTIVE'
        assert ReferenceStatus.DELETING == 'DELETING'
        assert ReferenceStatus.DELETED == 'DELETED'

    def test_membership(self):
        assert ReferenceStatus.ACTIVE in ReferenceStatus
        assert 'INVALID' not in [e.value for e in ReferenceStatus]


# --- Sequence Store Model Tests ---


class TestSequenceStoreSummary:
    """Tests for SequenceStoreSummary model."""

    def test_all_fields(self):
        creation_time = datetime.now(timezone.utc)
        store = SequenceStoreSummary(
            id='store-123',
            arn='arn:aws:omics:us-east-1:123456789012:sequenceStore/store-123',
            name='my-store',
            description='A test store',
            creationTime=creation_time,
            fallbackLocation='s3://my-bucket/fallback',
        )
        assert store.id == 'store-123'
        assert store.arn == 'arn:aws:omics:us-east-1:123456789012:sequenceStore/store-123'
        assert store.name == 'my-store'
        assert store.description == 'A test store'
        assert store.creationTime == creation_time
        assert store.fallbackLocation == 's3://my-bucket/fallback'

    def test_minimal_fields(self):
        creation_time = datetime.now(timezone.utc)
        store = SequenceStoreSummary(
            id='store-123',
            arn='arn:aws:omics:us-east-1:123456789012:sequenceStore/store-123',
            name='my-store',
            creationTime=creation_time,
        )
        assert store.description is None
        assert store.fallbackLocation is None

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            SequenceStoreSummary()  # type: ignore

    def test_serialization(self):
        creation_time = datetime.now(timezone.utc)
        store = SequenceStoreSummary(
            id='store-123',
            arn='arn:aws:omics:us-east-1:123456789012:sequenceStore/store-123',
            name='my-store',
            description='A test store',
            creationTime=creation_time,
        )
        data = store.model_dump()
        assert data['id'] == 'store-123'
        assert data['name'] == 'my-store'
        assert data['description'] == 'A test store'
        assert isinstance(data['creationTime'], datetime)

    def test_serialization_exclude_none(self):
        creation_time = datetime.now(timezone.utc)
        store = SequenceStoreSummary(
            id='store-123',
            arn='arn:aws:omics:us-east-1:123456789012:sequenceStore/store-123',
            name='my-store',
            creationTime=creation_time,
        )
        data = store.model_dump(exclude_none=True)
        assert 'description' not in data
        assert 'fallbackLocation' not in data
        assert data['id'] == 'store-123'


class TestSequenceStoreDetail:
    """Tests for SequenceStoreDetail model."""

    def test_all_fields(self):
        creation_time = datetime.now(timezone.utc)
        detail = SequenceStoreDetail(
            id='store-123',
            arn='arn:aws:omics:us-east-1:123456789012:sequenceStore/store-123',
            name='my-store',
            description='A test store',
            creationTime=creation_time,
            fallbackLocation='s3://my-bucket/fallback',
            sseConfig={'type': 'KMS', 'keyArn': 'arn:aws:kms:us-east-1:123456789012:key/abc'},
            eTag='etag-abc123',
        )
        assert detail.sseConfig == {
            'type': 'KMS',
            'keyArn': 'arn:aws:kms:us-east-1:123456789012:key/abc',
        }
        assert detail.eTag == 'etag-abc123'
        # Inherited fields
        assert detail.id == 'store-123'
        assert detail.name == 'my-store'

    def test_minimal_fields(self):
        creation_time = datetime.now(timezone.utc)
        detail = SequenceStoreDetail(
            id='store-123',
            arn='arn:aws:omics:us-east-1:123456789012:sequenceStore/store-123',
            name='my-store',
            creationTime=creation_time,
        )
        assert detail.sseConfig is None
        assert detail.eTag is None
        assert detail.description is None
        assert detail.fallbackLocation is None

    def test_serialization(self):
        creation_time = datetime.now(timezone.utc)
        detail = SequenceStoreDetail(
            id='store-123',
            arn='arn:aws:omics:us-east-1:123456789012:sequenceStore/store-123',
            name='my-store',
            creationTime=creation_time,
            sseConfig={'type': 'KMS'},
            eTag='etag-abc',
        )
        data = detail.model_dump()
        assert data['sseConfig'] == {'type': 'KMS'}
        assert data['eTag'] == 'etag-abc'


class TestReadSetSummary:
    """Tests for ReadSetSummary model."""

    def test_all_fields(self):
        creation_time = datetime.now(timezone.utc)
        read_set = ReadSetSummary(
            id='rs-123',
            arn='arn:aws:omics:us-east-1:123456789012:sequenceStore/store-123/readSet/rs-123',
            sequenceStoreId='store-123',
            name='sample-reads',
            status='ACTIVE',
            fileType='FASTQ',
            subjectId='subject-001',
            sampleId='sample-001',
            referenceArn='arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store/reference/ref-123',
            creationTime=creation_time,
        )
        assert read_set.id == 'rs-123'
        assert read_set.sequenceStoreId == 'store-123'
        assert read_set.name == 'sample-reads'
        assert read_set.status == 'ACTIVE'
        assert read_set.fileType == 'FASTQ'
        assert read_set.subjectId == 'subject-001'
        assert read_set.sampleId == 'sample-001'
        assert read_set.referenceArn is not None
        assert read_set.creationTime == creation_time

    def test_minimal_fields(self):
        creation_time = datetime.now(timezone.utc)
        read_set = ReadSetSummary(
            id='rs-123',
            arn='arn:aws:omics:us-east-1:123456789012:sequenceStore/store-123/readSet/rs-123',
            sequenceStoreId='store-123',
            status='ACTIVE',
            fileType='BAM',
            creationTime=creation_time,
        )
        assert read_set.name is None
        assert read_set.subjectId is None
        assert read_set.sampleId is None
        assert read_set.referenceArn is None

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            ReadSetSummary()  # type: ignore

    def test_serialization(self):
        creation_time = datetime.now(timezone.utc)
        read_set = ReadSetSummary(
            id='rs-123',
            arn='arn:aws:omics:us-east-1:123456789012:sequenceStore/store-123/readSet/rs-123',
            sequenceStoreId='store-123',
            status='ACTIVE',
            fileType='CRAM',
            creationTime=creation_time,
        )
        data = read_set.model_dump()
        assert data['id'] == 'rs-123'
        assert data['fileType'] == 'CRAM'
        assert data['status'] == 'ACTIVE'

    def test_serialization_exclude_none(self):
        creation_time = datetime.now(timezone.utc)
        read_set = ReadSetSummary(
            id='rs-123',
            arn='arn:aws:omics:us-east-1:123456789012:sequenceStore/store-123/readSet/rs-123',
            sequenceStoreId='store-123',
            status='ACTIVE',
            fileType='UBAM',
            creationTime=creation_time,
        )
        data = read_set.model_dump(exclude_none=True)
        assert 'name' not in data
        assert 'subjectId' not in data
        assert 'sampleId' not in data
        assert 'referenceArn' not in data


class TestReadSetImportSource:
    """Tests for ReadSetImportSource model."""

    def test_all_fields(self):
        source = ReadSetImportSource(
            sourceFileType='FASTQ',
            sourceFiles={
                'source1': 's3://bucket/file1.fastq',
                'source2': 's3://bucket/file2.fastq',
            },
            referenceArn='arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store/reference/ref-123',
            sampleId='sample-001',
            subjectId='subject-001',
            name='my-import',
            tags={'project': 'genomics', 'env': 'dev'},
        )
        assert source.sourceFileType == 'FASTQ'
        assert len(source.sourceFiles) == 2
        assert source.referenceArn is not None
        assert source.sampleId == 'sample-001'
        assert source.subjectId == 'subject-001'
        assert source.name == 'my-import'
        assert source.tags == {'project': 'genomics', 'env': 'dev'}

    def test_minimal_fields(self):
        source = ReadSetImportSource(
            sourceFileType='BAM',
            sourceFiles={'source1': 's3://bucket/file.bam'},
        )
        assert source.referenceArn is None
        assert source.sampleId is None
        assert source.subjectId is None
        assert source.name is None
        assert source.tags is None

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            ReadSetImportSource()  # type: ignore

    def test_serialization(self):
        source = ReadSetImportSource(
            sourceFileType='CRAM',
            sourceFiles={'source1': 's3://bucket/file.cram'},
            name='test-import',
        )
        data = source.model_dump()
        assert data['sourceFileType'] == 'CRAM'
        assert data['sourceFiles'] == {'source1': 's3://bucket/file.cram'}
        assert data['name'] == 'test-import'

    def test_serialization_exclude_none(self):
        source = ReadSetImportSource(
            sourceFileType='BAM',
            sourceFiles={'source1': 's3://bucket/file.bam'},
        )
        data = source.model_dump(exclude_none=True)
        assert 'referenceArn' not in data
        assert 'sampleId' not in data
        assert 'subjectId' not in data
        assert 'name' not in data
        assert 'tags' not in data


# --- Reference Store Model Tests ---


class TestReferenceStoreSummary:
    """Tests for ReferenceStoreSummary model."""

    def test_all_fields(self):
        creation_time = datetime.now(timezone.utc)
        store = ReferenceStoreSummary(
            id='ref-store-123',
            arn='arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store-123',
            name='my-ref-store',
            description='A reference store',
            creationTime=creation_time,
        )
        assert store.id == 'ref-store-123'
        assert store.arn == 'arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store-123'
        assert store.name == 'my-ref-store'
        assert store.description == 'A reference store'
        assert store.creationTime == creation_time

    def test_minimal_fields(self):
        creation_time = datetime.now(timezone.utc)
        store = ReferenceStoreSummary(
            id='ref-store-123',
            arn='arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store-123',
            name='my-ref-store',
            creationTime=creation_time,
        )
        assert store.description is None

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            ReferenceStoreSummary()  # type: ignore

    def test_serialization(self):
        creation_time = datetime.now(timezone.utc)
        store = ReferenceStoreSummary(
            id='ref-store-123',
            arn='arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store-123',
            name='my-ref-store',
            description='Test ref store',
            creationTime=creation_time,
        )
        data = store.model_dump()
        assert data['id'] == 'ref-store-123'
        assert data['description'] == 'Test ref store'

    def test_serialization_exclude_none(self):
        creation_time = datetime.now(timezone.utc)
        store = ReferenceStoreSummary(
            id='ref-store-123',
            arn='arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store-123',
            name='my-ref-store',
            creationTime=creation_time,
        )
        data = store.model_dump(exclude_none=True)
        assert 'description' not in data


class TestReferenceStoreDetail:
    """Tests for ReferenceStoreDetail model."""

    def test_all_fields(self):
        creation_time = datetime.now(timezone.utc)
        detail = ReferenceStoreDetail(
            id='ref-store-123',
            arn='arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store-123',
            name='my-ref-store',
            description='A reference store',
            creationTime=creation_time,
            sseConfig={'type': 'KMS', 'keyArn': 'arn:aws:kms:us-east-1:123456789012:key/xyz'},
            eTag='etag-xyz789',
        )
        assert detail.sseConfig == {
            'type': 'KMS',
            'keyArn': 'arn:aws:kms:us-east-1:123456789012:key/xyz',
        }
        assert detail.eTag == 'etag-xyz789'
        assert detail.id == 'ref-store-123'
        assert detail.name == 'my-ref-store'

    def test_minimal_fields(self):
        creation_time = datetime.now(timezone.utc)
        detail = ReferenceStoreDetail(
            id='ref-store-123',
            arn='arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store-123',
            name='my-ref-store',
            creationTime=creation_time,
        )
        assert detail.sseConfig is None
        assert detail.eTag is None
        assert detail.description is None

    def test_serialization(self):
        creation_time = datetime.now(timezone.utc)
        detail = ReferenceStoreDetail(
            id='ref-store-123',
            arn='arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store-123',
            name='my-ref-store',
            creationTime=creation_time,
            sseConfig={'type': 'KMS'},
            eTag='etag-abc',
        )
        data = detail.model_dump()
        assert data['sseConfig'] == {'type': 'KMS'}
        assert data['eTag'] == 'etag-abc'


class TestReferenceSummary:
    """Tests for ReferenceSummary model."""

    def test_all_fields(self):
        creation_time = datetime.now(timezone.utc)
        ref = ReferenceSummary(
            id='ref-123',
            arn='arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store/reference/ref-123',
            referenceStoreId='ref-store-123',
            name='hg38',
            status='ACTIVE',
            description='Human reference genome GRCh38',
            md5='anMd5',
            creationTime=creation_time,
        )
        assert ref.id == 'ref-123'
        assert ref.referenceStoreId == 'ref-store-123'
        assert ref.name == 'hg38'
        assert ref.status == 'ACTIVE'
        assert ref.description == 'Human reference genome GRCh38'
        assert ref.md5 == 'anMd5'
        assert ref.creationTime == creation_time

    def test_minimal_fields(self):
        creation_time = datetime.now(timezone.utc)
        ref = ReferenceSummary(
            id='ref-123',
            arn='arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store/reference/ref-123',
            referenceStoreId='ref-store-123',
            status='ACTIVE',
            creationTime=creation_time,
        )
        assert ref.name is None
        assert ref.description is None
        assert ref.md5 is None

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            ReferenceSummary()  # type: ignore

    def test_serialization(self):
        creation_time = datetime.now(timezone.utc)
        ref = ReferenceSummary(
            id='ref-123',
            arn='arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store/reference/ref-123',
            referenceStoreId='ref-store-123',
            status='ACTIVE',
            name='hg38',
            creationTime=creation_time,
        )
        data = ref.model_dump()
        assert data['id'] == 'ref-123'
        assert data['status'] == 'ACTIVE'
        assert data['name'] == 'hg38'

    def test_serialization_exclude_none(self):
        creation_time = datetime.now(timezone.utc)
        ref = ReferenceSummary(
            id='ref-123',
            arn='arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store/reference/ref-123',
            referenceStoreId='ref-store-123',
            status='ACTIVE',
            creationTime=creation_time,
        )
        data = ref.model_dump(exclude_none=True)
        assert 'name' not in data
        assert 'description' not in data
        assert 'md5' not in data


class TestReferenceImportSource:
    """Tests for ReferenceImportSource model."""

    def test_all_fields(self):
        source = ReferenceImportSource(
            sourceFile='s3://bucket/reference.fasta',
            name='hg38',
            description='Human reference genome',
            tags={'project': 'genomics', 'version': 'v1'},
        )
        assert source.sourceFile == 's3://bucket/reference.fasta'
        assert source.name == 'hg38'
        assert source.description == 'Human reference genome'
        assert source.tags == {'project': 'genomics', 'version': 'v1'}

    def test_minimal_fields(self):
        source = ReferenceImportSource(
            sourceFile='s3://bucket/reference.fasta',
            name='hg38',
        )
        assert source.description is None
        assert source.tags is None

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            ReferenceImportSource()  # type: ignore

    def test_serialization(self):
        source = ReferenceImportSource(
            sourceFile='s3://bucket/reference.fasta',
            name='hg38',
            description='Test reference',
        )
        data = source.model_dump()
        assert data['sourceFile'] == 's3://bucket/reference.fasta'
        assert data['name'] == 'hg38'
        assert data['description'] == 'Test reference'

    def test_serialization_exclude_none(self):
        source = ReferenceImportSource(
            sourceFile='s3://bucket/reference.fasta',
            name='hg38',
        )
        data = source.model_dump(exclude_none=True)
        assert 'description' not in data
        assert 'tags' not in data
