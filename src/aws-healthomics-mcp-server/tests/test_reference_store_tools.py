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

"""Unit tests for reference store management tools."""

import json
import pytest
from awslabs.aws_healthomics_mcp_server.tools.reference_store_tools import (
    cancel_reference_import_job,
    create_reference_store,
    get_reference_import_job,
    get_reference_metadata,
    get_reference_store,
    list_reference_import_jobs,
    list_reference_stores,
    list_references,
    start_reference_import_job,
    update_reference_store,
)
from datetime import datetime, timezone
from tests.test_helpers import MCPToolTestWrapper
from unittest.mock import AsyncMock, MagicMock, patch


MOCK_PATH = 'awslabs.aws_healthomics_mcp_server.tools.reference_store_tools.get_omics_client'

NOW = datetime.now(timezone.utc)


# =============================================================================
# TestCreateReferenceStore
# =============================================================================


class TestCreateReferenceStore:
    """Tests for create_reference_store tool."""

    wrapper = MCPToolTestWrapper(create_reference_store)

    @pytest.mark.asyncio
    async def test_happy_path_all_params(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.create_reference_store.return_value = {
            'id': 'ref-store-123',
            'arn': 'arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store-123',
            'name': 'my-ref-store',
            'creationTime': NOW,
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                name='my-ref-store',
                description='A test reference store',
                sse_kms_key_arn='arn:aws:kms:us-east-1:123456789012:key/abc-123',
                tags='{"env": "test"}',
            )
        assert result['id'] == 'ref-store-123'
        assert result['arn'] is not None
        assert result['name'] == 'my-ref-store'
        assert result['creationTime'] is not None
        call_args = mock_client.create_reference_store.call_args[1]
        assert call_args['name'] == 'my-ref-store'
        assert call_args['description'] == 'A test reference store'
        assert call_args['sseConfig'] == {
            'type': 'KMS',
            'keyArn': 'arn:aws:kms:us-east-1:123456789012:key/abc-123',
        }
        assert call_args['tags'] == {'env': 'test'}

    @pytest.mark.asyncio
    async def test_happy_path_minimal_params(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.create_reference_store.return_value = {
            'id': 'ref-store-456',
            'arn': 'arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store-456',
            'name': 'minimal-store',
            'creationTime': NOW,
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(ctx=mock_ctx, name='minimal-store')
        assert result['id'] == 'ref-store-456'
        assert result['name'] == 'minimal-store'
        call_args = mock_client.create_reference_store.call_args[1]
        assert 'description' not in call_args
        assert 'sseConfig' not in call_args
        assert 'tags' not in call_args

    @pytest.mark.asyncio
    async def test_api_error(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.create_reference_store.side_effect = Exception('AccessDeniedException')
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
        mock_client.create_reference_store.assert_not_called()


# =============================================================================
# TestListReferenceStores
# =============================================================================


class TestListReferenceStores:
    """Tests for list_reference_stores tool."""

    wrapper = MCPToolTestWrapper(list_reference_stores)

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_reference_stores.return_value = {
            'referenceStores': [
                {
                    'id': 'ref-store-1',
                    'arn': 'arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store-1',
                    'name': 'store-one',
                    'description': 'First store',
                    'creationTime': NOW,
                },
                {
                    'id': 'ref-store-2',
                    'arn': 'arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store-2',
                    'name': 'store-two',
                    'creationTime': NOW,
                },
            ]
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(ctx=mock_ctx)
        assert len(result['referenceStores']) == 2
        assert result['referenceStores'][0]['id'] == 'ref-store-1'
        assert result['referenceStores'][1]['name'] == 'store-two'
        assert 'nextToken' not in result

    @pytest.mark.asyncio
    async def test_empty_results(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_reference_stores.return_value = {'referenceStores': []}
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(ctx=mock_ctx)
        assert result['referenceStores'] == []

    @pytest.mark.asyncio
    async def test_with_name_filter(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_reference_stores.return_value = {
            'referenceStores': [
                {
                    'id': 'ref-store-1',
                    'arn': 'arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store-1',
                    'name': 'grch38',
                    'creationTime': NOW,
                }
            ]
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(ctx=mock_ctx, name_filter='grch38')
        assert len(result['referenceStores']) == 1
        call_args = mock_client.list_reference_stores.call_args[1]
        assert call_args['filter'] == {'name': 'grch38'}

    @pytest.mark.asyncio
    async def test_with_pagination(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_reference_stores.return_value = {
            'referenceStores': [
                {
                    'id': 'ref-store-1',
                    'arn': 'arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store-1',
                    'name': 'store-one',
                    'creationTime': NOW,
                }
            ],
            'nextToken': 'page2-token',
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(ctx=mock_ctx, max_results=1, next_token='page1-token')
        assert result['nextToken'] == 'page2-token'
        call_args = mock_client.list_reference_stores.call_args[1]
        assert call_args['maxResults'] == 1
        assert call_args['nextToken'] == 'page1-token'

    @pytest.mark.asyncio
    async def test_api_error(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_reference_stores.side_effect = Exception('ServiceUnavailable')
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(ctx=mock_ctx)
        assert 'error' in result
        assert len(result['error']) > 0


# =============================================================================
# TestGetReferenceStore
# =============================================================================


class TestGetReferenceStore:
    """Tests for get_reference_store tool."""

    wrapper = MCPToolTestWrapper(get_reference_store)

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_reference_store.return_value = {
            'id': 'ref-store-123',
            'arn': 'arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store-123',
            'name': 'my-ref-store',
            'description': 'A reference store',
            'sseConfig': {'type': 'KMS', 'keyArn': 'arn:aws:kms:us-east-1:123456789012:key/k1'},
            'creationTime': NOW,
            'eTag': 'etag-abc',
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(ctx=mock_ctx, reference_store_id='ref-store-123')
        assert result['id'] == 'ref-store-123'
        assert result['name'] == 'my-ref-store'
        assert result['description'] == 'A reference store'
        assert result['sseConfig'] is not None
        assert result['creationTime'] is not None
        assert result['eTag'] == 'etag-abc'

    @pytest.mark.asyncio
    async def test_not_found_error(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_reference_store.side_effect = Exception(
            'ResourceNotFoundException: Reference store not found'
        )
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(ctx=mock_ctx, reference_store_id='nonexistent')
        assert 'error' in result
        assert len(result['error']) > 0


# =============================================================================
# TestUpdateReferenceStore
# =============================================================================


class TestUpdateReferenceStore:
    """Tests for update_reference_store tool."""

    wrapper = MCPToolTestWrapper(update_reference_store)

    @pytest.mark.asyncio
    async def test_happy_path_name_and_description(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_reference_store.return_value = {
            'id': 'ref-store-123',
            'eTag': 'etag-v1',
        }
        mock_client.update_reference_store.return_value = {
            'id': 'ref-store-123',
            'arn': 'arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store-123',
            'name': 'updated-name',
            'description': 'updated-desc',
            'sseConfig': None,
            'creationTime': NOW,
            'eTag': 'etag-v2',
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                reference_store_id='ref-store-123',
                name='updated-name',
                description='updated-desc',
            )
        assert result['id'] == 'ref-store-123'
        assert result['name'] == 'updated-name'
        assert result['description'] == 'updated-desc'
        assert result['eTag'] == 'etag-v2'

    @pytest.mark.asyncio
    async def test_etag_management(self):
        """Verify get is called before update to fetch ETag."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_reference_store.return_value = {
            'id': 'ref-store-123',
            'eTag': 'etag-current',
        }
        mock_client.update_reference_store.return_value = {
            'id': 'ref-store-123',
            'arn': 'arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store-123',
            'name': 'new-name',
            'creationTime': NOW,
            'eTag': 'etag-new',
        }
        with patch(MOCK_PATH, return_value=mock_client):
            await self.wrapper.call(
                ctx=mock_ctx, reference_store_id='ref-store-123', name='new-name'
            )
        # Verify get was called first to fetch ETag
        mock_client.get_reference_store.assert_called_once_with(id='ref-store-123')
        # Verify update was called with the fetched ETag
        update_args = mock_client.update_reference_store.call_args[1]
        assert update_args['eTag'] == 'etag-current'
        assert update_args['name'] == 'new-name'

    @pytest.mark.asyncio
    async def test_api_error_on_get(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_reference_store.side_effect = Exception(
            'ResourceNotFoundException: Store not found'
        )
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx, reference_store_id='nonexistent', name='new-name'
            )
        assert 'error' in result
        assert len(result['error']) > 0
        mock_client.update_reference_store.assert_not_called()

    @pytest.mark.asyncio
    async def test_api_error_on_update(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_reference_store.return_value = {
            'id': 'ref-store-123',
            'eTag': 'etag-v1',
        }
        mock_client.update_reference_store.side_effect = Exception(
            'ConflictException: ETag mismatch'
        )
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx, reference_store_id='ref-store-123', name='new-name'
            )
        assert 'error' in result
        assert len(result['error']) > 0

    @pytest.mark.asyncio
    async def test_update_without_etag(self):
        """Verify update works when get response has no eTag."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_reference_store.return_value = {
            'id': 'ref-store-123',
        }
        mock_client.update_reference_store.return_value = {
            'id': 'ref-store-123',
            'arn': 'arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store-123',
            'name': 'new-name',
            'creationTime': NOW,
            'eTag': 'etag-v1',
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx, reference_store_id='ref-store-123', name='new-name'
            )
        assert result['id'] == 'ref-store-123'
        update_args = mock_client.update_reference_store.call_args[1]
        assert 'eTag' not in update_args
        assert update_args['name'] == 'new-name'


# =============================================================================
# TestListReferences
# =============================================================================


class TestListReferences:
    """Tests for list_references tool."""

    wrapper = MCPToolTestWrapper(list_references)

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_references.return_value = {
            'references': [
                {
                    'id': 'ref-001',
                    'arn': 'arn:aws:omics:us-east-1:123456789012:referenceStore/s1/reference/ref-001',
                    'referenceStoreId': 'ref-store-123',
                    'name': 'GRCh38',
                    'status': 'ACTIVE',
                    'description': 'Human reference genome',
                    'md5': 'abc123md5',
                    'creationTime': NOW,
                }
            ]
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(ctx=mock_ctx, reference_store_id='ref-store-123')
        assert len(result['references']) == 1
        assert result['references'][0]['id'] == 'ref-001'
        assert result['references'][0]['name'] == 'GRCh38'
        assert result['references'][0]['status'] == 'ACTIVE'

    @pytest.mark.asyncio
    async def test_with_name_filter(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_references.return_value = {'references': []}
        with patch(MOCK_PATH, return_value=mock_client):
            await self.wrapper.call(
                ctx=mock_ctx, reference_store_id='ref-store-123', name_filter='GRCh38'
            )
        call_args = mock_client.list_references.call_args[1]
        assert call_args['filter'] == {'name': 'GRCh38'}

    @pytest.mark.asyncio
    async def test_with_status_filter(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_references.return_value = {'references': []}
        with patch(MOCK_PATH, return_value=mock_client):
            await self.wrapper.call(
                ctx=mock_ctx, reference_store_id='ref-store-123', status_filter='ACTIVE'
            )
        call_args = mock_client.list_references.call_args[1]
        assert call_args['filter'] == {'status': 'ACTIVE'}

    @pytest.mark.asyncio
    async def test_with_pagination(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_references.return_value = {
            'references': [],
            'nextToken': 'next-page',
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                reference_store_id='ref-store-123',
                max_results=10,
                next_token='prev-token',
            )
        assert result['nextToken'] == 'next-page'
        call_args = mock_client.list_references.call_args[1]
        assert call_args['maxResults'] == 10
        assert call_args['nextToken'] == 'prev-token'

    @pytest.mark.asyncio
    async def test_api_error(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_references.side_effect = Exception('ResourceNotFoundException')
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(ctx=mock_ctx, reference_store_id='nonexistent')
        assert 'error' in result
        assert len(result['error']) > 0


# =============================================================================
# TestGetReferenceMetadata
# =============================================================================


class TestGetReferenceMetadata:
    """Tests for get_reference_metadata tool."""

    wrapper = MCPToolTestWrapper(get_reference_metadata)

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_reference_metadata.return_value = {
            'id': 'ref-001',
            'arn': 'arn:aws:omics:us-east-1:123456789012:referenceStore/s1/reference/ref-001',
            'name': 'GRCh38',
            'status': 'ACTIVE',
            'description': 'Human reference genome build 38',
            'md5': 'abc123md5hash',
            'creationTime': NOW,
            'files': {
                'source': {
                    'totalParts': 1,
                    'partSize': 104857600,
                    'contentLength': 3200000000,
                }
            },
            'referenceStoreId': 'ref-store-123',
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx, reference_store_id='ref-store-123', reference_id='ref-001'
            )
        assert result['id'] == 'ref-001'
        assert result['name'] == 'GRCh38'
        assert result['status'] == 'ACTIVE'
        assert result['description'] == 'Human reference genome build 38'
        assert result['md5'] == 'abc123md5hash'
        assert result['creationTime'] is not None
        assert result['files'] is not None
        assert result['referenceStoreId'] == 'ref-store-123'

    @pytest.mark.asyncio
    async def test_not_found_error(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_reference_metadata.side_effect = Exception(
            'ResourceNotFoundException: Reference not found'
        )
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx, reference_store_id='ref-store-123', reference_id='nonexistent'
            )
        assert 'error' in result
        assert len(result['error']) > 0


# =============================================================================
# TestStartReferenceImportJob
# =============================================================================


class TestStartReferenceImportJob:
    """Tests for start_reference_import_job tool."""

    wrapper = MCPToolTestWrapper(start_reference_import_job)

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.start_reference_import_job.return_value = {
            'id': 'import-job-001',
            'referenceStoreId': 'ref-store-123',
            'status': 'SUBMITTED',
            'creationTime': NOW,
        }
        sources = json.dumps(
            [
                {
                    'sourceFile': 's3://bucket/GRCh38.fasta',
                    'name': 'GRCh38',
                    'description': 'Human reference genome',
                    'tags': {'build': '38'},
                }
            ]
        )
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                reference_store_id='ref-store-123',
                role_arn='arn:aws:iam::123456789012:role/OmicsRole',
                sources=sources,
            )
        assert result['id'] == 'import-job-001'
        assert result['referenceStoreId'] == 'ref-store-123'
        assert result['status'] == 'SUBMITTED'
        assert result['creationTime'] is not None
        call_args = mock_client.start_reference_import_job.call_args[1]
        assert call_args['referenceStoreId'] == 'ref-store-123'
        assert len(call_args['sources']) == 1

    @pytest.mark.asyncio
    async def test_invalid_sources_json(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                reference_store_id='ref-store-123',
                role_arn='arn:aws:iam::123456789012:role/OmicsRole',
                sources='not-valid-json[',
            )
        assert 'error' in result
        assert len(result['error']) > 0
        mock_client.start_reference_import_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_api_error(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.start_reference_import_job.side_effect = Exception('ValidationException')
        sources = json.dumps([{'sourceFile': 's3://bucket/ref.fasta', 'name': 'ref'}])
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                reference_store_id='ref-store-123',
                role_arn='arn:aws:iam::123456789012:role/OmicsRole',
                sources=sources,
            )
        assert 'error' in result
        assert len(result['error']) > 0


# =============================================================================
# TestGetReferenceImportJob
# =============================================================================


class TestGetReferenceImportJob:
    """Tests for get_reference_import_job tool."""

    wrapper = MCPToolTestWrapper(get_reference_import_job)

    @pytest.mark.asyncio
    async def test_happy_path_with_sources(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        completion = datetime(2025, 6, 15, 12, 30, 0, tzinfo=timezone.utc)
        mock_client.get_reference_import_job.return_value = {
            'id': 'import-job-001',
            'status': 'COMPLETED',
            'sources': [
                {
                    'sourceFile': 's3://bucket/GRCh38.fasta',
                    'name': 'GRCh38',
                    'status': 'COMPLETED',
                    'statusMessage': '',
                }
            ],
            'creationTime': NOW,
            'completionTime': completion,
            'roleArn': 'arn:aws:iam::123456789012:role/OmicsRole',
            'referenceStoreId': 'ref-store-123',
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                reference_store_id='ref-store-123',
                import_job_id='import-job-001',
            )
        assert result['id'] == 'import-job-001'
        assert result['status'] == 'COMPLETED'
        assert result['sources'] is not None
        assert len(result['sources']) == 1
        assert result['creationTime'] is not None
        assert result['completionTime'] is not None
        assert result['roleArn'] == 'arn:aws:iam::123456789012:role/OmicsRole'
        assert result['referenceStoreId'] == 'ref-store-123'

    @pytest.mark.asyncio
    async def test_not_found_error(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_reference_import_job.side_effect = Exception(
            'ResourceNotFoundException: Import job not found'
        )
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                reference_store_id='ref-store-123',
                import_job_id='nonexistent',
            )
        assert 'error' in result
        assert len(result['error']) > 0


# =============================================================================
# TestListReferenceImportJobs
# =============================================================================


class TestListReferenceImportJobs:
    """Tests for list_reference_import_jobs tool."""

    wrapper = MCPToolTestWrapper(list_reference_import_jobs)

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        completion = datetime(2025, 6, 15, 12, 30, 0, tzinfo=timezone.utc)
        mock_client.list_reference_import_jobs.return_value = {
            'importJobs': [
                {
                    'id': 'import-job-001',
                    'referenceStoreId': 'ref-store-123',
                    'status': 'COMPLETED',
                    'roleArn': 'arn:aws:iam::123456789012:role/OmicsRole',
                    'creationTime': NOW,
                    'completionTime': completion,
                },
                {
                    'id': 'import-job-002',
                    'referenceStoreId': 'ref-store-123',
                    'status': 'IN_PROGRESS',
                    'roleArn': 'arn:aws:iam::123456789012:role/OmicsRole',
                    'creationTime': NOW,
                    'completionTime': None,
                },
            ]
        }
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(ctx=mock_ctx, reference_store_id='ref-store-123')
        assert len(result['importJobs']) == 2
        assert result['importJobs'][0]['id'] == 'import-job-001'
        assert result['importJobs'][0]['status'] == 'COMPLETED'
        assert result['importJobs'][1]['status'] == 'IN_PROGRESS'
        assert 'nextToken' not in result

    @pytest.mark.asyncio
    async def test_with_pagination(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_reference_import_jobs.return_value = {
            'importJobs': [
                {
                    'id': 'import-job-001',
                    'referenceStoreId': 'ref-store-123',
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
                reference_store_id='ref-store-123',
                max_results=1,
                next_token='page1-token',
            )
        assert result['nextToken'] == 'page2-token'
        call_args = mock_client.list_reference_import_jobs.call_args[1]
        assert call_args['maxResults'] == 1
        assert call_args['nextToken'] == 'page1-token'

    @pytest.mark.asyncio
    async def test_api_error(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_reference_import_jobs.side_effect = Exception(
            'ResourceNotFoundException: Store not found'
        )
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(ctx=mock_ctx, reference_store_id='nonexistent')
        assert 'error' in result
        assert len(result['error']) > 0


# =============================================================================
# TestCancelReferenceImportJob
# =============================================================================


class TestCancelReferenceImportJob:
    """Tests for cancel_reference_import_job tool."""

    wrapper = MCPToolTestWrapper(cancel_reference_import_job)

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.cancel_reference_import_job.return_value = {}
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                reference_store_id='ref-store-123',
                import_job_id='import-job-001',
            )
        assert 'message' in result
        assert 'import-job-001' in result['message']
        mock_client.cancel_reference_import_job.assert_called_once_with(
            referenceStoreId='ref-store-123', id='import-job-001'
        )

    @pytest.mark.asyncio
    async def test_non_cancellable_job_error(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.cancel_reference_import_job.side_effect = Exception(
            'ConflictException: Job is not in a cancellable state'
        )
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                reference_store_id='ref-store-123',
                import_job_id='completed-job',
            )
        assert 'error' in result
        assert len(result['error']) > 0

    @pytest.mark.asyncio
    async def test_not_found_error(self):
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.cancel_reference_import_job.side_effect = Exception(
            'ResourceNotFoundException: Import job not found'
        )
        with patch(MOCK_PATH, return_value=mock_client):
            result = await self.wrapper.call(
                ctx=mock_ctx,
                reference_store_id='ref-store-123',
                import_job_id='nonexistent',
            )
        assert 'error' in result
        assert len(result['error']) > 0
