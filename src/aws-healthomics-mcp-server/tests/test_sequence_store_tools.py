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

"""Unit tests for sequence store management tools."""

import json
import pytest
from awslabs.aws_healthomics_mcp_server.tools.sequence_store_tools import (
    activate_read_sets,
    archive_read_sets,
    cancel_read_set_import_job,
    create_sequence_store,
    get_read_set_export_job,
    get_read_set_import_job,
    get_read_set_metadata,
    get_sequence_store,
    list_read_set_export_jobs,
    list_read_set_import_jobs,
    list_read_sets,
    list_sequence_stores,
    start_read_set_export_job,
    start_read_set_import_job,
    update_sequence_store,
)
from datetime import datetime, timezone
from tests.test_helpers import MCPToolTestWrapper
from unittest.mock import AsyncMock, MagicMock, patch


MOCK_PATH = 'awslabs.aws_healthomics_mcp_server.tools.sequence_store_tools.get_omics_client'

NOW = datetime.now(timezone.utc)


# =============================================================================
# TestCreateSequenceStore
# =============================================================================


class TestCreateSequenceStore:
    """Tests for create_sequence_store tool."""

    wrapper = MCPToolTestWrapper(create_sequence_store)

    @pytest.mark.asyncio
    async def test_happy_path_all_params(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.create_sequence_store.return_value = {
            'id': 'seq-store-123',
            'arn': 'arn:aws:omics:us-east-1:123456789012:sequenceStore/seq-store-123',
            'name': 'my-seq-store',
            'creationTime': NOW,
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                name='my-seq-store',
                description='A test sequence store',
                sse_kms_key_arn='arn:aws:kms:us-east-1:123456789012:key/abc-123',
                fallback_location='s3://my-bucket/fallback/',
                tags='{"env": "test"}',
            )
        assert result['id'] == 'seq-store-123'
        assert result['arn'] is not None
        assert result['name'] == 'my-seq-store'
        assert result['creationTime'] is not None
        call_args = mock_client.create_sequence_store.call_args[1]
        assert call_args['name'] == 'my-seq-store'
        assert call_args['description'] == 'A test sequence store'
        assert call_args['sseConfig'] == {
            'type': 'KMS',
            'keyArn': 'arn:aws:kms:us-east-1:123456789012:key/abc-123',
        }
        assert call_args['fallbackLocation'] == 's3://my-bucket/fallback/'
        assert call_args['tags'] == {'env': 'test'}

    @pytest.mark.asyncio
    async def test_happy_path_minimal_params(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.create_sequence_store.return_value = {
            'id': 'seq-store-456',
            'arn': 'arn:aws:omics:us-east-1:123456789012:sequenceStore/seq-store-456',
            'name': 'minimal-store',
            'creationTime': NOW,
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(ctx=mock_ctx, name='minimal-store')
        assert result['id'] == 'seq-store-456'
        assert result['name'] == 'minimal-store'
        call_args = mock_client.create_sequence_store.call_args[1]
        assert 'description' not in call_args
        assert 'sseConfig' not in call_args
        assert 'fallbackLocation' not in call_args
        assert 'tags' not in call_args

    @pytest.mark.asyncio
    async def test_api_error(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.create_sequence_store.side_effect = Exception('AccessDeniedException')
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(ctx=mock_ctx, name='fail-store')
        assert 'error' in result
        assert len(result['error']) > 0

    @pytest.mark.asyncio
    async def test_invalid_tags_json(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(ctx=mock_ctx, name='store', tags='not-valid-json')
        assert 'error' in result
        assert len(result['error']) > 0
        mock_client.create_sequence_store.assert_not_called()


# =============================================================================
# TestListSequenceStores
# =============================================================================


class TestListSequenceStores:
    """Tests for list_sequence_stores tool."""

    wrapper = MCPToolTestWrapper(list_sequence_stores)

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_sequence_stores.return_value = {
            'sequenceStores': [
                {
                    'id': 'seq-store-1',
                    'arn': 'arn:aws:omics:us-east-1:123456789012:sequenceStore/seq-store-1',
                    'name': 'store-one',
                    'description': 'First store',
                    'creationTime': NOW,
                    'fallbackLocation': 's3://bucket/fallback/',
                },
                {
                    'id': 'seq-store-2',
                    'arn': 'arn:aws:omics:us-east-1:123456789012:sequenceStore/seq-store-2',
                    'name': 'store-two',
                    'creationTime': NOW,
                },
            ]
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(ctx=mock_ctx)
        assert len(result['sequenceStores']) == 2
        assert result['sequenceStores'][0]['id'] == 'seq-store-1'
        assert result['sequenceStores'][1]['name'] == 'store-two'
        assert 'nextToken' not in result

    @pytest.mark.asyncio
    async def test_empty_results(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_sequence_stores.return_value = {'sequenceStores': []}
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(ctx=mock_ctx)
        assert result['sequenceStores'] == []

    @pytest.mark.asyncio
    async def test_with_name_filter(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_sequence_stores.return_value = {
            'sequenceStores': [
                {
                    'id': 'seq-store-1',
                    'arn': 'arn:aws:omics:us-east-1:123456789012:sequenceStore/seq-store-1',
                    'name': 'wgs-store',
                    'creationTime': NOW,
                }
            ]
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(ctx=mock_ctx, name_filter='wgs-store')
        assert len(result['sequenceStores']) == 1
        call_args = mock_client.list_sequence_stores.call_args[1]
        assert call_args['filter'] == {'name': 'wgs-store'}

    @pytest.mark.asyncio
    async def test_with_pagination(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_sequence_stores.return_value = {
            'sequenceStores': [
                {
                    'id': 'seq-store-1',
                    'arn': 'arn:aws:omics:us-east-1:123456789012:sequenceStore/seq-store-1',
                    'name': 'store-one',
                    'creationTime': NOW,
                }
            ],
            'nextToken': 'page2-token',
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(ctx=mock_ctx, max_results=1, next_token='page1-token')
        assert result['nextToken'] == 'page2-token'
        call_args = mock_client.list_sequence_stores.call_args[1]
        assert call_args['maxResults'] == 1
        assert call_args['nextToken'] == 'page1-token'

    @pytest.mark.asyncio
    async def test_api_error(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_sequence_stores.side_effect = Exception('ServiceUnavailable')
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(ctx=mock_ctx)
        assert 'error' in result
        assert len(result['error']) > 0


# =============================================================================
# TestGetSequenceStore
# =============================================================================


class TestGetSequenceStore:
    """Tests for get_sequence_store tool."""

    wrapper = MCPToolTestWrapper(get_sequence_store)

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_sequence_store.return_value = {
            'id': 'seq-store-123',
            'arn': 'arn:aws:omics:us-east-1:123456789012:sequenceStore/seq-store-123',
            'name': 'my-seq-store',
            'description': 'A sequence store',
            'sseConfig': {'type': 'KMS', 'keyArn': 'arn:aws:kms:us-east-1:123456789012:key/k1'},
            'creationTime': NOW,
            'fallbackLocation': 's3://bucket/fallback/',
            'eTag': 'etag-abc',
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(ctx=mock_ctx, sequence_store_id='seq-store-123')
        assert result['id'] == 'seq-store-123'
        assert result['name'] == 'my-seq-store'
        assert result['description'] == 'A sequence store'
        assert result['sseConfig'] is not None
        assert result['creationTime'] is not None
        assert result['fallbackLocation'] == 's3://bucket/fallback/'
        assert result['eTag'] == 'etag-abc'

    @pytest.mark.asyncio
    async def test_not_found_error(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_sequence_store.side_effect = Exception(
            'ResourceNotFoundException: Sequence store not found'
        )
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(ctx=mock_ctx, sequence_store_id='nonexistent')
        assert 'error' in result
        assert len(result['error']) > 0


# =============================================================================
# TestUpdateSequenceStore
# =============================================================================


class TestUpdateSequenceStore:
    """Tests for update_sequence_store tool."""

    wrapper = MCPToolTestWrapper(update_sequence_store)

    @pytest.mark.asyncio
    async def test_happy_path_all_fields(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_sequence_store.return_value = {
            'id': 'seq-store-123',
            'eTag': 'etag-v1',
        }
        mock_client.update_sequence_store.return_value = {
            'id': 'seq-store-123',
            'arn': 'arn:aws:omics:us-east-1:123456789012:sequenceStore/seq-store-123',
            'name': 'updated-name',
            'description': 'updated-desc',
            'sseConfig': None,
            'creationTime': NOW,
            'fallbackLocation': 's3://new-bucket/fallback/',
            'eTag': 'etag-v2',
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                sequence_store_id='seq-store-123',
                name='updated-name',
                description='updated-desc',
                fallback_location='s3://new-bucket/fallback/',
            )
        assert result['id'] == 'seq-store-123'
        assert result['name'] == 'updated-name'
        assert result['description'] == 'updated-desc'
        assert result['fallbackLocation'] == 's3://new-bucket/fallback/'
        assert result['eTag'] == 'etag-v2'

    @pytest.mark.asyncio
    async def test_etag_management(self):
        """Verify get is called before update to fetch ETag."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_sequence_store.return_value = {
            'id': 'seq-store-123',
            'eTag': 'etag-current',
        }
        mock_client.update_sequence_store.return_value = {
            'id': 'seq-store-123',
            'arn': 'arn:aws:omics:us-east-1:123456789012:sequenceStore/seq-store-123',
            'name': 'new-name',
            'creationTime': NOW,
            'eTag': 'etag-new',
        }
        with patch(MOCK_PATH, return_value=mock_client):
            await self.wrapper.call(
                ctx=mock_ctx, sequence_store_id='seq-store-123', name='new-name'
            )
        # Verify get was called first to fetch ETag
        mock_client.get_sequence_store.assert_called_once_with(id='seq-store-123')
        # Verify update was called with the fetched ETag
        update_args = mock_client.update_sequence_store.call_args[1]
        assert update_args['eTag'] == 'etag-current'
        assert update_args['name'] == 'new-name'

    @pytest.mark.asyncio
    async def test_api_error_on_get(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_sequence_store.side_effect = Exception(
            'ResourceNotFoundException: Store not found'
        )
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx, sequence_store_id='nonexistent', name='new-name'
            )
        assert 'error' in result
        assert len(result['error']) > 0
        mock_client.update_sequence_store.assert_not_called()

    @pytest.mark.asyncio
    async def test_api_error_on_update_etag_conflict(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_sequence_store.return_value = {
            'id': 'seq-store-123',
            'eTag': 'etag-v1',
        }
        mock_client.update_sequence_store.side_effect = Exception(
            'ConflictException: ETag mismatch'
        )
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx, sequence_store_id='seq-store-123', name='new-name'
            )
        assert 'error' in result
        assert len(result['error']) > 0

    @pytest.mark.asyncio
    async def test_update_without_etag(self):
        """Verify update works when get response has no eTag."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_sequence_store.return_value = {
            'id': 'seq-store-123',
        }
        mock_client.update_sequence_store.return_value = {
            'id': 'seq-store-123',
            'arn': 'arn:aws:omics:us-east-1:123456789012:sequenceStore/seq-store-123',
            'name': 'new-name',
            'creationTime': NOW,
            'eTag': 'etag-v1',
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx, sequence_store_id='seq-store-123', name='new-name'
            )
        assert result['id'] == 'seq-store-123'
        update_args = mock_client.update_sequence_store.call_args[1]
        assert 'eTag' not in update_args
        assert update_args['name'] == 'new-name'


# =============================================================================
# TestListReadSets
# =============================================================================


class TestListReadSets:
    """Tests for list_read_sets tool."""

    wrapper = MCPToolTestWrapper(list_read_sets)

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_read_sets.return_value = {
            'readSets': [
                {
                    'id': 'rs-001',
                    'arn': 'arn:aws:omics:us-east-1:123456789012:sequenceStore/s1/readSet/rs-001',
                    'sequenceStoreId': 'seq-store-123',
                    'name': 'sample-reads',
                    'status': 'ACTIVE',
                    'fileType': 'FASTQ',
                    'subjectId': 'subject-1',
                    'sampleId': 'sample-1',
                    'referenceArn': 'arn:aws:omics:us-east-1:123456789012:referenceStore/r1/reference/ref-1',
                    'creationTime': NOW,
                }
            ]
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(ctx=mock_ctx, sequence_store_id='seq-store-123')
        assert len(result['readSets']) == 1
        assert result['readSets'][0]['id'] == 'rs-001'
        assert result['readSets'][0]['name'] == 'sample-reads'
        assert result['readSets'][0]['status'] == 'ACTIVE'
        assert result['readSets'][0]['fileType'] == 'FASTQ'

    @pytest.mark.asyncio
    async def test_with_sample_id_filter(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_read_sets.return_value = {'readSets': []}
        with patch(MOCK_PATH, return_value=mock_client):
            await self.wrapper.call(
                ctx=mock_ctx, sequence_store_id='seq-store-123', sample_id='sample-1'
            )
        call_args = mock_client.list_read_sets.call_args[1]
        assert call_args['filter'] == {'sampleId': 'sample-1'}

    @pytest.mark.asyncio
    async def test_with_subject_id_filter(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_read_sets.return_value = {'readSets': []}
        with patch(MOCK_PATH, return_value=mock_client):
            await self.wrapper.call(
                ctx=mock_ctx, sequence_store_id='seq-store-123', subject_id='subject-1'
            )
        call_args = mock_client.list_read_sets.call_args[1]
        assert call_args['filter'] == {'subjectId': 'subject-1'}

    @pytest.mark.asyncio
    async def test_with_status_filter(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_read_sets.return_value = {'readSets': []}
        with patch(MOCK_PATH, return_value=mock_client):
            await self.wrapper.call(
                ctx=mock_ctx, sequence_store_id='seq-store-123', status='ACTIVE'
            )
        call_args = mock_client.list_read_sets.call_args[1]
        assert call_args['filter'] == {'status': 'ACTIVE'}

    @pytest.mark.asyncio
    async def test_with_file_type_filter(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_read_sets.return_value = {'readSets': []}
        with patch(MOCK_PATH, return_value=mock_client):
            await self.wrapper.call(
                ctx=mock_ctx, sequence_store_id='seq-store-123', file_type='BAM'
            )
        call_args = mock_client.list_read_sets.call_args[1]
        assert call_args['filter'] == {'fileType': 'BAM'}

    @pytest.mark.asyncio
    async def test_with_reference_arn_filter(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_read_sets.return_value = {'readSets': []}
        with patch(MOCK_PATH, return_value=mock_client):
            await self.wrapper.call(
                ctx=mock_ctx,
                sequence_store_id='seq-store-123',
                reference_arn='arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store/reference/ref-001',
            )
        call_args = mock_client.list_read_sets.call_args[1]
        assert call_args['filter'] == {
            'referenceArn': 'arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store/reference/ref-001'
        }

    @pytest.mark.asyncio
    async def test_with_created_after_filter(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_read_sets.return_value = {'readSets': []}
        with patch(MOCK_PATH, return_value=mock_client):
            await self.wrapper.call(
                ctx=mock_ctx,
                sequence_store_id='seq-store-123',
                created_after='2024-01-01T00:00:00Z',
            )
        call_args = mock_client.list_read_sets.call_args[1]
        assert call_args['filter'] == {'createdAfter': '2024-01-01T00:00:00Z'}

    @pytest.mark.asyncio
    async def test_with_created_before_filter(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_read_sets.return_value = {'readSets': []}
        with patch(MOCK_PATH, return_value=mock_client):
            await self.wrapper.call(
                ctx=mock_ctx,
                sequence_store_id='seq-store-123',
                created_before='2024-12-31T23:59:59Z',
            )
        call_args = mock_client.list_read_sets.call_args[1]
        assert call_args['filter'] == {'createdBefore': '2024-12-31T23:59:59Z'}

    @pytest.mark.asyncio
    async def test_with_pagination(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_read_sets.return_value = {
            'readSets': [],
            'nextToken': 'next-page',
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                sequence_store_id='seq-store-123',
                max_results=10,
                next_token='prev-token',
            )
        assert result['nextToken'] == 'next-page'
        call_args = mock_client.list_read_sets.call_args[1]
        assert call_args['maxResults'] == 10
        assert call_args['nextToken'] == 'prev-token'

    @pytest.mark.asyncio
    async def test_api_error(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_read_sets.side_effect = Exception('ResourceNotFoundException')
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(ctx=mock_ctx, sequence_store_id='nonexistent')
        assert 'error' in result
        assert len(result['error']) > 0


# =============================================================================
# TestGetReadSetMetadata
# =============================================================================


class TestGetReadSetMetadata:
    """Tests for get_read_set_metadata tool."""

    wrapper = MCPToolTestWrapper(get_read_set_metadata)

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_read_set_metadata.return_value = {
            'id': 'rs-001',
            'arn': 'arn:aws:omics:us-east-1:123456789012:sequenceStore/s1/readSet/rs-001',
            'name': 'sample-reads',
            'status': 'ACTIVE',
            'fileType': 'FASTQ',
            'sequenceStoreId': 'seq-store-123',
            'subjectId': 'subject-1',
            'sampleId': 'sample-1',
            'referenceArn': 'arn:aws:omics:us-east-1:123456789012:referenceStore/r1/reference/ref-1',
            'creationTime': NOW,
            'sequenceInformation': {
                'totalReadCount': 1000000,
                'totalBaseCount': 150000000,
                'alignment': 'ALIGNED',
            },
            'files': {
                'source1': {
                    'totalParts': 1,
                    'partSize': 104857600,
                    'contentLength': 5000000000,
                }
            },
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx, sequence_store_id='seq-store-123', read_set_id='rs-001'
            )
        assert result['id'] == 'rs-001'
        assert result['name'] == 'sample-reads'
        assert result['status'] == 'ACTIVE'
        assert result['fileType'] == 'FASTQ'
        assert result['sequenceStoreId'] == 'seq-store-123'
        assert result['subjectId'] == 'subject-1'
        assert result['sampleId'] == 'sample-1'
        assert result['referenceArn'] is not None
        assert result['creationTime'] is not None
        assert result['sequenceInformation'] is not None
        assert result['files'] is not None

    @pytest.mark.asyncio
    async def test_not_found_error(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_read_set_metadata.side_effect = Exception(
            'ResourceNotFoundException: Read set not found'
        )
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx, sequence_store_id='seq-store-123', read_set_id='nonexistent'
            )
        assert 'error' in result
        assert len(result['error']) > 0


# =============================================================================
# TestStartReadSetImportJob
# =============================================================================


class TestStartReadSetImportJob:
    """Tests for start_read_set_import_job tool."""

    wrapper = MCPToolTestWrapper(start_read_set_import_job)

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.start_read_set_import_job.return_value = {
            'id': 'import-job-001',
            'sequenceStoreId': 'seq-store-123',
            'status': 'SUBMITTED',
            'creationTime': NOW,
        }
        sources = json.dumps(
            [
                {
                    'sourceFileType': 'FASTQ',
                    'sourceFiles': {'source1': 's3://bucket/sample_R1.fastq.gz'},
                    'sampleId': 'sample-1',
                    'subjectId': 'subject-1',
                    'name': 'sample-reads',
                }
            ]
        )
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                sequence_store_id='seq-store-123',
                role_arn='arn:aws:iam::123456789012:role/OmicsRole',
                sources=sources,
            )
        assert result['id'] == 'import-job-001'
        assert result['sequenceStoreId'] == 'seq-store-123'
        assert result['status'] == 'SUBMITTED'
        assert result['creationTime'] is not None
        call_args = mock_client.start_read_set_import_job.call_args[1]
        assert call_args['sequenceStoreId'] == 'seq-store-123'
        assert len(call_args['sources']) == 1

    @pytest.mark.asyncio
    async def test_with_tags(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.start_read_set_import_job.return_value = {
            'id': 'import-job-002',
            'sequenceStoreId': 'seq-store-123',
            'status': 'SUBMITTED',
            'creationTime': NOW,
        }
        sources = json.dumps(
            [
                {
                    'sourceFileType': 'BAM',
                    'sourceFiles': {'source1': 's3://bucket/sample.bam'},
                }
            ]
        )
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                sequence_store_id='seq-store-123',
                role_arn='arn:aws:iam::123456789012:role/OmicsRole',
                sources=sources,
                tags='{"project": "wgs"}',
            )
        assert result['id'] == 'import-job-002'
        call_args = mock_client.start_read_set_import_job.call_args[1]
        assert call_args['tags'] == {'project': 'wgs'}

    @pytest.mark.asyncio
    async def test_invalid_sources_json(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                sequence_store_id='seq-store-123',
                role_arn='arn:aws:iam::123456789012:role/OmicsRole',
                sources='not-valid-json[',
            )
        assert 'error' in result
        assert len(result['error']) > 0
        mock_client.start_read_set_import_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_tags_json(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        sources = json.dumps(
            [{'sourceFileType': 'FASTQ', 'sourceFiles': {'source1': 's3://bucket/r1.fastq.gz'}}]
        )
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                sequence_store_id='seq-store-123',
                role_arn='arn:aws:iam::123456789012:role/OmicsRole',
                sources=sources,
                tags='not-valid-json{',
            )
        assert 'error' in result
        assert len(result['error']) > 0
        mock_client.start_read_set_import_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_api_error(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.start_read_set_import_job.side_effect = Exception('ValidationException')
        sources = json.dumps(
            [{'sourceFileType': 'FASTQ', 'sourceFiles': {'source1': 's3://bucket/r1.fastq.gz'}}]
        )
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                sequence_store_id='seq-store-123',
                role_arn='arn:aws:iam::123456789012:role/OmicsRole',
                sources=sources,
            )
        assert 'error' in result
        assert len(result['error']) > 0


# =============================================================================
# TestGetReadSetImportJob
# =============================================================================


class TestGetReadSetImportJob:
    """Tests for get_read_set_import_job tool."""

    wrapper = MCPToolTestWrapper(get_read_set_import_job)

    @pytest.mark.asyncio
    async def test_happy_path_with_sources(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        completion = datetime(2025, 6, 15, 12, 30, 0, tzinfo=timezone.utc)
        mock_client.get_read_set_import_job.return_value = {
            'id': 'import-job-001',
            'status': 'COMPLETED',
            'sources': [
                {
                    'sourceFileType': 'FASTQ',
                    'sourceFiles': {'source1': 's3://bucket/sample_R1.fastq.gz'},
                    'status': 'COMPLETED',
                    'statusMessage': '',
                }
            ],
            'creationTime': NOW,
            'completionTime': completion,
            'roleArn': 'arn:aws:iam::123456789012:role/OmicsRole',
            'sequenceStoreId': 'seq-store-123',
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                sequence_store_id='seq-store-123',
                import_job_id='import-job-001',
            )
        assert result['id'] == 'import-job-001'
        assert result['status'] == 'COMPLETED'
        assert result['sources'] is not None
        assert len(result['sources']) == 1
        assert result['creationTime'] is not None
        assert result['completionTime'] is not None
        assert result['roleArn'] == 'arn:aws:iam::123456789012:role/OmicsRole'
        assert result['sequenceStoreId'] == 'seq-store-123'

    @pytest.mark.asyncio
    async def test_not_found_error(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_read_set_import_job.side_effect = Exception(
            'ResourceNotFoundException: Import job not found'
        )
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                sequence_store_id='seq-store-123',
                import_job_id='nonexistent',
            )
        assert 'error' in result
        assert len(result['error']) > 0


# =============================================================================
# TestListReadSetImportJobs
# =============================================================================


class TestListReadSetImportJobs:
    """Tests for list_read_set_import_jobs tool."""

    wrapper = MCPToolTestWrapper(list_read_set_import_jobs)

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        completion = datetime(2025, 6, 15, 12, 30, 0, tzinfo=timezone.utc)
        mock_client.list_read_set_import_jobs.return_value = {
            'importJobs': [
                {
                    'id': 'import-job-001',
                    'sequenceStoreId': 'seq-store-123',
                    'status': 'COMPLETED',
                    'roleArn': 'arn:aws:iam::123456789012:role/OmicsRole',
                    'creationTime': NOW,
                    'completionTime': completion,
                },
                {
                    'id': 'import-job-002',
                    'sequenceStoreId': 'seq-store-123',
                    'status': 'IN_PROGRESS',
                    'roleArn': 'arn:aws:iam::123456789012:role/OmicsRole',
                    'creationTime': NOW,
                    'completionTime': None,
                },
            ]
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(ctx=mock_ctx, sequence_store_id='seq-store-123')
        assert len(result['importJobs']) == 2
        assert result['importJobs'][0]['id'] == 'import-job-001'
        assert result['importJobs'][0]['status'] == 'COMPLETED'
        assert result['importJobs'][1]['status'] == 'IN_PROGRESS'
        assert 'nextToken' not in result

    @pytest.mark.asyncio
    async def test_with_pagination(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_read_set_import_jobs.return_value = {
            'importJobs': [
                {
                    'id': 'import-job-001',
                    'sequenceStoreId': 'seq-store-123',
                    'status': 'COMPLETED',
                    'roleArn': 'arn:aws:iam::123456789012:role/OmicsRole',
                    'creationTime': NOW,
                    'completionTime': NOW,
                }
            ],
            'nextToken': 'page2-token',
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                sequence_store_id='seq-store-123',
                max_results=1,
                next_token='page1-token',
            )
        assert result['nextToken'] == 'page2-token'
        call_args = mock_client.list_read_set_import_jobs.call_args[1]
        assert call_args['maxResults'] == 1
        assert call_args['nextToken'] == 'page1-token'

    @pytest.mark.asyncio
    async def test_api_error(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_read_set_import_jobs.side_effect = Exception(
            'ResourceNotFoundException: Store not found'
        )
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(ctx=mock_ctx, sequence_store_id='nonexistent')
        assert 'error' in result
        assert len(result['error']) > 0


# =============================================================================
# TestCancelReadSetImportJob
# =============================================================================


class TestCancelReadSetImportJob:
    """Tests for cancel_read_set_import_job tool."""

    wrapper = MCPToolTestWrapper(cancel_read_set_import_job)

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.cancel_read_set_import_job.return_value = {}
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                sequence_store_id='seq-store-123',
                import_job_id='import-job-001',
            )
        assert 'message' in result
        assert 'import-job-001' in result['message']
        mock_client.cancel_read_set_import_job.assert_called_once_with(
            sequenceStoreId='seq-store-123', id='import-job-001'
        )

    @pytest.mark.asyncio
    async def test_non_cancellable_job_error(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.cancel_read_set_import_job.side_effect = Exception(
            'ConflictException: Job is not in a cancellable state'
        )
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                sequence_store_id='seq-store-123',
                import_job_id='completed-job',
            )
        assert 'error' in result
        assert len(result['error']) > 0

    @pytest.mark.asyncio
    async def test_not_found_error(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.cancel_read_set_import_job.side_effect = Exception(
            'ResourceNotFoundException: Import job not found'
        )
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                sequence_store_id='seq-store-123',
                import_job_id='nonexistent',
            )
        assert 'error' in result
        assert len(result['error']) > 0


# =============================================================================
# TestStartReadSetExportJob
# =============================================================================


class TestStartReadSetExportJob:
    """Tests for start_read_set_export_job tool."""

    wrapper = MCPToolTestWrapper(start_read_set_export_job)

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.start_read_set_export_job.return_value = {
            'id': 'export-job-001',
            'sequenceStoreId': 'seq-store-123',
            'status': 'SUBMITTED',
            'destination': {'s3': {'s3Uri': 's3://export-bucket/output/'}},
        }
        read_set_ids = json.dumps(['rs-001', 'rs-002'])
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                sequence_store_id='seq-store-123',
                destination_s3_uri='s3://export-bucket/output/',
                role_arn='arn:aws:iam::123456789012:role/OmicsRole',
                read_set_ids=read_set_ids,
            )
        assert result['id'] == 'export-job-001'
        assert result['sequenceStoreId'] == 'seq-store-123'
        assert result['status'] == 'SUBMITTED'
        assert result['destination'] is not None
        call_args = mock_client.start_read_set_export_job.call_args[1]
        assert call_args['sequenceStoreId'] == 'seq-store-123'
        assert call_args['destination'] == {'s3': {'s3Uri': 's3://export-bucket/output/'}}
        assert call_args['roleArn'] == 'arn:aws:iam::123456789012:role/OmicsRole'
        assert len(call_args['sources']) == 2
        assert call_args['sources'][0] == {'readSetId': 'rs-001'}
        assert call_args['sources'][1] == {'readSetId': 'rs-002'}

    @pytest.mark.asyncio
    async def test_invalid_read_set_ids_json(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                sequence_store_id='seq-store-123',
                destination_s3_uri='s3://export-bucket/output/',
                role_arn='arn:aws:iam::123456789012:role/OmicsRole',
                read_set_ids='not-valid-json[',
            )
        assert 'error' in result
        assert len(result['error']) > 0
        mock_client.start_read_set_export_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_api_error(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.start_read_set_export_job.side_effect = Exception('ValidationException')
        read_set_ids = json.dumps(['rs-001'])
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                sequence_store_id='seq-store-123',
                destination_s3_uri='s3://export-bucket/output/',
                role_arn='arn:aws:iam::123456789012:role/OmicsRole',
                read_set_ids=read_set_ids,
            )
        assert 'error' in result
        assert len(result['error']) > 0


# =============================================================================
# TestGetReadSetExportJob
# =============================================================================


class TestGetReadSetExportJob:
    """Tests for get_read_set_export_job tool."""

    wrapper = MCPToolTestWrapper(get_read_set_export_job)

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        completion = datetime(2025, 6, 15, 12, 30, 0, tzinfo=timezone.utc)
        mock_client.get_read_set_export_job.return_value = {
            'id': 'export-job-001',
            'status': 'COMPLETED',
            'destination': {'s3': {'s3Uri': 's3://export-bucket/output/'}},
            'creationTime': NOW,
            'completionTime': completion,
            'sequenceStoreId': 'seq-store-123',
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                sequence_store_id='seq-store-123',
                export_job_id='export-job-001',
            )
        assert result['id'] == 'export-job-001'
        assert result['status'] == 'COMPLETED'
        assert result['destination'] is not None
        assert result['creationTime'] is not None
        assert result['completionTime'] is not None
        assert result['sequenceStoreId'] == 'seq-store-123'

    @pytest.mark.asyncio
    async def test_not_found_error(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_read_set_export_job.side_effect = Exception(
            'ResourceNotFoundException: Export job not found'
        )
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                sequence_store_id='seq-store-123',
                export_job_id='nonexistent',
            )
        assert 'error' in result
        assert len(result['error']) > 0


# =============================================================================
# TestListReadSetExportJobs
# =============================================================================


class TestListReadSetExportJobs:
    """Tests for list_read_set_export_jobs tool."""

    wrapper = MCPToolTestWrapper(list_read_set_export_jobs)

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        completion = datetime(2025, 6, 15, 12, 30, 0, tzinfo=timezone.utc)
        mock_client.list_read_set_export_jobs.return_value = {
            'exportJobs': [
                {
                    'id': 'export-job-001',
                    'sequenceStoreId': 'seq-store-123',
                    'status': 'COMPLETED',
                    'destination': {'s3': {'s3Uri': 's3://export-bucket/output/'}},
                    'creationTime': NOW,
                    'completionTime': completion,
                },
                {
                    'id': 'export-job-002',
                    'sequenceStoreId': 'seq-store-123',
                    'status': 'IN_PROGRESS',
                    'destination': {'s3': {'s3Uri': 's3://export-bucket/output2/'}},
                    'creationTime': NOW,
                    'completionTime': None,
                },
            ]
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(ctx=mock_ctx, sequence_store_id='seq-store-123')
        assert len(result['exportJobs']) == 2
        assert result['exportJobs'][0]['id'] == 'export-job-001'
        assert result['exportJobs'][0]['status'] == 'COMPLETED'
        assert result['exportJobs'][1]['status'] == 'IN_PROGRESS'
        assert 'nextToken' not in result

    @pytest.mark.asyncio
    async def test_with_pagination(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_read_set_export_jobs.return_value = {
            'exportJobs': [
                {
                    'id': 'export-job-001',
                    'sequenceStoreId': 'seq-store-123',
                    'status': 'COMPLETED',
                    'destination': {'s3': {'s3Uri': 's3://export-bucket/output/'}},
                    'creationTime': NOW,
                    'completionTime': NOW,
                }
            ],
            'nextToken': 'page2-token',
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                sequence_store_id='seq-store-123',
                max_results=1,
                next_token='page1-token',
            )
        assert result['nextToken'] == 'page2-token'
        call_args = mock_client.list_read_set_export_jobs.call_args[1]
        assert call_args['maxResults'] == 1
        assert call_args['nextToken'] == 'page1-token'

    @pytest.mark.asyncio
    async def test_api_error(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_read_set_export_jobs.side_effect = Exception(
            'ResourceNotFoundException: Store not found'
        )
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(ctx=mock_ctx, sequence_store_id='nonexistent')
        assert 'error' in result
        assert len(result['error']) > 0


# =============================================================================
# TestActivateReadSets
# =============================================================================


class TestActivateReadSets:
    """Tests for activate_read_sets tool."""

    wrapper = MCPToolTestWrapper(activate_read_sets)

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.start_read_set_activation_job.return_value = {
            'sequenceStoreId': 'seq-store-123',
            'status': 'SUBMITTED',
        }
        read_set_ids = json.dumps(['rs-001', 'rs-002'])
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                sequence_store_id='seq-store-123',
                read_set_ids=read_set_ids,
            )
        assert result['sequenceStoreId'] == 'seq-store-123'
        assert result['status'] == 'SUBMITTED'
        assert result['readSetIds'] == ['rs-001', 'rs-002']
        call_args = mock_client.start_read_set_activation_job.call_args[1]
        assert call_args['sequenceStoreId'] == 'seq-store-123'
        assert len(call_args['sources']) == 2
        assert call_args['sources'][0] == {'readSetId': 'rs-001'}
        assert call_args['sources'][1] == {'readSetId': 'rs-002'}

    @pytest.mark.asyncio
    async def test_invalid_json(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                sequence_store_id='seq-store-123',
                read_set_ids='not-valid-json',
            )
        assert 'error' in result
        assert len(result['error']) > 0
        mock_client.start_read_set_activation_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_api_error_invalid_state(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.start_read_set_activation_job.side_effect = Exception(
            'ValidationException: Read set is not in ARCHIVED state'
        )
        read_set_ids = json.dumps(['rs-001'])
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                sequence_store_id='seq-store-123',
                read_set_ids=read_set_ids,
            )
        assert 'error' in result
        assert len(result['error']) > 0


# =============================================================================
# TestArchiveReadSets
# =============================================================================


class TestArchiveReadSets:
    """Tests for archive_read_sets tool."""

    wrapper = MCPToolTestWrapper(archive_read_sets)

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.start_read_set_archive_job.return_value = {
            'sequenceStoreId': 'seq-store-123',
            'status': 'SUBMITTED',
        }
        read_set_ids = json.dumps(['rs-001', 'rs-002'])
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                sequence_store_id='seq-store-123',
                read_set_ids=read_set_ids,
            )
        assert result['sequenceStoreId'] == 'seq-store-123'
        assert result['status'] == 'SUBMITTED'
        assert result['readSetIds'] == ['rs-001', 'rs-002']
        call_args = mock_client.start_read_set_archive_job.call_args[1]
        assert call_args['sequenceStoreId'] == 'seq-store-123'
        assert len(call_args['sources']) == 2
        assert call_args['sources'][0] == {'readSetId': 'rs-001'}
        assert call_args['sources'][1] == {'readSetId': 'rs-002'}

    @pytest.mark.asyncio
    async def test_invalid_json(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                sequence_store_id='seq-store-123',
                read_set_ids='not-valid-json',
            )
        assert 'error' in result
        assert len(result['error']) > 0
        mock_client.start_read_set_archive_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_api_error_invalid_state(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.start_read_set_archive_job.side_effect = Exception(
            'ValidationException: Read set is not in ACTIVE state'
        )
        read_set_ids = json.dumps(['rs-001'])
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                sequence_store_id='seq-store-123',
                read_set_ids=read_set_ids,
            )
        assert 'error' in result
        assert len(result['error']) > 0
