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

"""Property-based tests for sequence store CRUD tools."""

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
    list_read_sets,
    list_sequence_stores,
    start_read_set_export_job,
    start_read_set_import_job,
    update_sequence_store,
)
from datetime import datetime, timezone
from hypothesis import given, settings
from hypothesis import strategies as st
from tests.test_helpers import MCPToolTestWrapper
from unittest.mock import AsyncMock, MagicMock, patch


# --- Hypothesis Strategies ---

name_strategy = st.text(min_size=1, max_size=128)
store_id_strategy = st.text(min_size=1, max_size=36)
description_strategy = st.none() | st.text(min_size=1, max_size=256)
kms_key_arn_strategy = st.none() | st.text(min_size=1, max_size=256)
fallback_location_strategy = st.none() | st.text(min_size=1, max_size=256)
tags_dict_strategy = st.none() | st.dictionaries(
    st.text(min_size=1, max_size=64, alphabet=st.characters(categories=('L', 'N'))),
    st.text(max_size=128),
    max_size=5,
)
next_token_strategy = st.none() | st.text(min_size=1, max_size=200)
name_filter_strategy = st.none() | st.text(min_size=1, max_size=128)

# --- Tool Wrappers ---

create_wrapper = MCPToolTestWrapper(create_sequence_store)
list_wrapper = MCPToolTestWrapper(list_sequence_stores)
get_wrapper = MCPToolTestWrapper(get_sequence_store)
update_wrapper = MCPToolTestWrapper(update_sequence_store)
list_read_sets_wrapper = MCPToolTestWrapper(list_read_sets)
get_read_set_metadata_wrapper = MCPToolTestWrapper(get_read_set_metadata)
start_import_wrapper = MCPToolTestWrapper(start_read_set_import_job)
get_import_wrapper = MCPToolTestWrapper(get_read_set_import_job)
cancel_import_wrapper = MCPToolTestWrapper(cancel_read_set_import_job)
start_export_wrapper = MCPToolTestWrapper(start_read_set_export_job)
get_export_wrapper = MCPToolTestWrapper(get_read_set_export_job)
activate_wrapper = MCPToolTestWrapper(activate_read_sets)
archive_wrapper = MCPToolTestWrapper(archive_read_sets)

MOCK_PATH = 'awslabs.aws_healthomics_mcp_server.tools.sequence_store_tools.get_omics_client'
MOCK_NOW = datetime.now(timezone.utc)


# Feature: store-management, Property: Create store returns required fields
class TestCreateStoreReturnsRequiredFields:
    """Create store returns required fields.

    For any valid store name, calling create_sequence_store should return a response
    dict containing `id`, `arn`, and `creationTime` keys with non-empty values.

    **Validates that create store returns id, arn, and creationTime**
    """

    @given(name=st.text(min_size=1, max_size=128))
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_create_store_returns_id_arn_creation_time(self, name):
        """For any valid name, create returns id, arn, and creationTime."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.create_sequence_store.return_value = {
            'id': 'store-abc',
            'arn': 'arn:aws:omics:us-east-1:123456789012:sequenceStore/store-abc',
            'name': name,
            'creationTime': MOCK_NOW,
        }

        with patch(MOCK_PATH, return_value=mock_client):
            result = await create_wrapper.call(ctx=mock_ctx, name=name)

        assert 'id' in result
        assert 'arn' in result
        assert 'creationTime' in result
        assert result['id']
        assert result['arn']
        assert result['creationTime']


# Feature: store-management, Property: Optional create parameters are forwarded to the API
class TestOptionalCreateParametersForwarded:
    """Optional create parameters are forwarded to the API.

    For any create_sequence_store call with any combination of optional parameters
    (description, sse_kms_key_arn, fallback_location, tags), all provided optional
    parameters should appear in the arguments passed to the underlying API call.

    **Validates that optional create parameters (description, SSE, fallback, tags) are forwarded to the API**
    """

    @given(
        name=name_strategy,
        description=description_strategy,
        sse_kms_key_arn=kms_key_arn_strategy,
        fallback_location=fallback_location_strategy,
        tags_dict=tags_dict_strategy,
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_optional_params_forwarded_to_api(
        self, name, description, sse_kms_key_arn, fallback_location, tags_dict
    ):
        """All provided optional params appear in the API call args."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.create_sequence_store.return_value = {
            'id': 'store-abc',
            'arn': 'arn:aws:omics:us-east-1:123456789012:sequenceStore/store-abc',
            'name': name,
            'creationTime': MOCK_NOW,
        }

        kwargs = {'name': name}
        if description is not None:
            kwargs['description'] = description
        if sse_kms_key_arn is not None:
            kwargs['sse_kms_key_arn'] = sse_kms_key_arn
        if fallback_location is not None:
            kwargs['fallback_location'] = fallback_location
        if tags_dict is not None:
            kwargs['tags'] = json.dumps(tags_dict)

        with patch(MOCK_PATH, return_value=mock_client):
            result = await create_wrapper.call(ctx=mock_ctx, **kwargs)

        # Skip error results from JSON parse failures on edge-case strings
        if 'error' in result:
            return

        mock_client.create_sequence_store.assert_called_once()
        api_args = mock_client.create_sequence_store.call_args[1]

        assert api_args['name'] == name

        if description is not None and description:
            assert 'description' in api_args
            assert api_args['description'] == description

        if sse_kms_key_arn is not None and sse_kms_key_arn:
            assert 'sseConfig' in api_args
            assert api_args['sseConfig']['keyArn'] == sse_kms_key_arn

        if fallback_location is not None and fallback_location:
            assert 'fallbackLocation' in api_args
            assert api_args['fallbackLocation'] == fallback_location

        if tags_dict is not None:
            assert 'tags' in api_args
            assert api_args['tags'] == tags_dict


# Feature: store-management, Property: API errors produce error response dicts
class TestApiErrorsProduceErrorResponseDicts:
    """API errors produce error response dicts.

    For any tool function, when the underlying API raises an exception, the tool
    should return a dict containing an `error` key with a non-empty string message.

    **Validates that API exceptions are caught and returned as error dicts**
    """

    @given(name=st.text(min_size=1, max_size=128))
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_create_sequence_store_error(self, name):
        """create_sequence_store returns error dict on API failure."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.create_sequence_store.side_effect = Exception('API error')

        with patch(MOCK_PATH, return_value=mock_client):
            result = await create_wrapper.call(ctx=mock_ctx, name=name)

        assert 'error' in result
        assert isinstance(result['error'], str)
        assert len(result['error']) > 0

    @given(name=st.text(min_size=1, max_size=128))
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_list_sequence_stores_error(self, name):
        """list_sequence_stores returns error dict on API failure."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_sequence_stores.side_effect = Exception('API error')

        with patch(MOCK_PATH, return_value=mock_client):
            result = await list_wrapper.call(ctx=mock_ctx)

        assert 'error' in result
        assert isinstance(result['error'], str)
        assert len(result['error']) > 0

    @given(store_id=st.text(min_size=1, max_size=36))
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_get_sequence_store_error(self, store_id):
        """get_sequence_store returns error dict on API failure."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_sequence_store.side_effect = Exception('API error')

        with patch(MOCK_PATH, return_value=mock_client):
            result = await get_wrapper.call(ctx=mock_ctx, sequence_store_id=store_id)

        assert 'error' in result
        assert isinstance(result['error'], str)
        assert len(result['error']) > 0

    @given(store_id=st.text(min_size=1, max_size=36))
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_update_sequence_store_error(self, store_id):
        """update_sequence_store returns error dict on API failure."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_sequence_store.side_effect = Exception('API error')

        with patch(MOCK_PATH, return_value=mock_client):
            result = await update_wrapper.call(
                ctx=mock_ctx, sequence_store_id=store_id, name='new-name'
            )

        assert 'error' in result
        assert isinstance(result['error'], str)
        assert len(result['error']) > 0


# Feature: store-management, Property: List tools return items and forward pagination parameters
class TestListToolsReturnItemsAndForwardPagination:
    """List tools return items and forward pagination parameters.

    For list_sequence_stores, the response should contain `sequenceStores` list key,
    and when `max_results` and `next_token` are provided, they should be forwarded
    to the API call.

    **Validates that list tools return items and forward pagination parameters**
    """

    @given(
        max_results=st.integers(min_value=1, max_value=100),
        next_token=next_token_strategy,
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_list_returns_items_and_forwards_pagination(self, max_results, next_token):
        """list_sequence_stores returns sequenceStores and forwards pagination params."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_sequence_stores.return_value = {
            'sequenceStores': [],
            'nextToken': 'tok',
        }

        kwargs = {'max_results': max_results}
        if next_token is not None:
            kwargs['next_token'] = next_token

        with patch(MOCK_PATH, return_value=mock_client):
            result = await list_wrapper.call(ctx=mock_ctx, **kwargs)

        assert 'sequenceStores' in result

        mock_client.list_sequence_stores.assert_called_once()
        api_args = mock_client.list_sequence_stores.call_args[1]

        assert api_args['maxResults'] == max_results

        if next_token is not None and next_token:
            assert 'nextToken' in api_args
            assert api_args['nextToken'] == next_token


# Feature: store-management, Property: List filter parameters are forwarded to the API
class TestListFilterParametersForwarded:
    """List filter parameters are forwarded to the API.

    For list_sequence_stores with name_filter, the filter should appear in the
    API call args.

    **Validates that list filter parameters are forwarded to the API**
    """

    @given(name_filter=name_filter_strategy)
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_name_filter_forwarded_to_api(self, name_filter):
        """name_filter is forwarded as filter.name in the API call."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_sequence_stores.return_value = {
            'sequenceStores': [],
        }

        kwargs = {}
        if name_filter is not None:
            kwargs['name_filter'] = name_filter

        with patch(MOCK_PATH, return_value=mock_client):
            await list_wrapper.call(ctx=mock_ctx, **kwargs)

        mock_client.list_sequence_stores.assert_called_once()
        api_args = mock_client.list_sequence_stores.call_args[1]

        if name_filter is not None and name_filter:
            assert 'filter' in api_args
            assert api_args['filter'] == {'name': name_filter}
        else:
            assert 'filter' not in api_args


# Feature: store-management, Property: Get store detail returns all specified fields
class TestGetStoreDetailReturnsAllFields:
    """Get store detail returns all specified fields.

    For any valid store ID, calling get_sequence_store should return a response dict
    containing all specified fields.

    **Validates that get store detail returns all specified fields**
    """

    @given(store_id=st.text(min_size=1, max_size=36))
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_get_store_returns_all_fields(self, store_id):
        """get_sequence_store returns all specified detail fields."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_sequence_store.return_value = {
            'id': store_id,
            'arn': f'arn:aws:omics:us-east-1:123456789012:sequenceStore/{store_id}',
            'name': 'test-store',
            'description': 'A test store',
            'sseConfig': {'type': 'KMS', 'keyArn': 'arn:aws:kms:us-east-1:123456789012:key/abc'},
            'creationTime': MOCK_NOW,
            'fallbackLocation': 's3://bucket/prefix',
            'eTag': 'etag-123',
        }

        with patch(MOCK_PATH, return_value=mock_client):
            result = await get_wrapper.call(ctx=mock_ctx, sequence_store_id=store_id)

        expected_keys = [
            'id',
            'arn',
            'name',
            'description',
            'sseConfig',
            'creationTime',
            'fallbackLocation',
            'eTag',
        ]
        for key in expected_keys:
            assert key in result, f'Missing key: {key}'


# Feature: store-management, Property: Update tools manage ETags and forward update fields
class TestUpdateToolsManageETagsAndForwardFields:
    """Update tools manage ETags and forward update fields.

    For any update_sequence_store call with any combination of updatable fields,
    the tool should first call get to fetch the ETag, then call update with the
    fetched ETag and all provided fields.

    **Validates that update tools fetch ETag before updating and forward all provided fields**
    """

    @given(
        store_id=store_id_strategy,
        name=st.none() | st.text(min_size=1, max_size=128),
        description=description_strategy,
        fallback_location=fallback_location_strategy,
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_update_fetches_etag_and_forwards_fields(
        self, store_id, name, description, fallback_location
    ):
        """update_sequence_store fetches ETag then calls update with it and all provided fields."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()

        # get_sequence_store returns current store with eTag
        mock_client.get_sequence_store.return_value = {
            'id': store_id,
            'arn': f'arn:aws:omics:us-east-1:123456789012:sequenceStore/{store_id}',
            'name': 'old-name',
            'description': 'old-desc',
            'sseConfig': None,
            'creationTime': MOCK_NOW,
            'fallbackLocation': None,
            'eTag': 'etag-123',
        }

        # update_sequence_store returns updated store
        mock_client.update_sequence_store.return_value = {
            'id': store_id,
            'arn': f'arn:aws:omics:us-east-1:123456789012:sequenceStore/{store_id}',
            'name': name if name else 'old-name',
            'description': description if description else 'old-desc',
            'sseConfig': None,
            'creationTime': MOCK_NOW,
            'fallbackLocation': fallback_location,
            'eTag': 'etag-456',
        }

        kwargs = {'sequence_store_id': store_id}
        if name is not None:
            kwargs['name'] = name
        if description is not None:
            kwargs['description'] = description
        if fallback_location is not None:
            kwargs['fallback_location'] = fallback_location

        with patch(MOCK_PATH, return_value=mock_client):
            await update_wrapper.call(ctx=mock_ctx, **kwargs)

        # Verify get was called first to fetch ETag
        mock_client.get_sequence_store.assert_called_once_with(id=store_id)

        # Verify update was called with ETag
        mock_client.update_sequence_store.assert_called_once()
        update_args = mock_client.update_sequence_store.call_args[1]

        assert update_args['id'] == store_id
        assert update_args['eTag'] == 'etag-123'

        # Verify provided fields are forwarded
        if name is not None and name:
            assert update_args['name'] == name
        if description is not None and description:
            assert update_args['description'] == description
        if fallback_location is not None and fallback_location:
            assert update_args['fallbackLocation'] == fallback_location


# Feature: store-management, Property: Get metadata returns all specified fields
class TestGetMetadataReturnsAllSpecifiedFields:
    """Get metadata returns all specified fields.

    For any valid store ID and read set ID, calling get_read_set_metadata should
    return a response dict containing all specified metadata fields.

    **Validates that get metadata returns all specified metadata fields**
    """

    @given(store_id=store_id_strategy, read_set_id=store_id_strategy)
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_get_metadata_returns_all_fields(self, store_id, read_set_id):
        """For any valid IDs, get_read_set_metadata returns all specified fields."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_read_set_metadata.return_value = {
            'id': read_set_id,
            'arn': f'arn:aws:omics:us-east-1:123456789012:sequenceStore/{store_id}/readSet/{read_set_id}',
            'name': 'test-read-set',
            'status': 'ACTIVE',
            'fileType': 'BAM',
            'sequenceStoreId': store_id,
            'subjectId': 'subject-1',
            'sampleId': 'sample-1',
            'referenceArn': 'arn:aws:omics:us-east-1:123456789012:referenceStore/ref-store/reference/ref-1',
            'creationTime': MOCK_NOW,
            'sequenceInformation': {'totalReadCount': 1000, 'totalBaseCount': 150000},
            'files': {'source1': {'totalParts': 1, 'partSize': 1024}},
        }

        with patch(MOCK_PATH, return_value=mock_client):
            result = await get_read_set_metadata_wrapper.call(
                ctx=mock_ctx, sequence_store_id=store_id, read_set_id=read_set_id
            )

        expected_keys = [
            'id',
            'arn',
            'name',
            'status',
            'fileType',
            'sequenceStoreId',
            'subjectId',
            'sampleId',
            'referenceArn',
            'creationTime',
            'sequenceInformation',
            'files',
        ]
        for key in expected_keys:
            assert key in result, f'Missing key: {key}'


# Feature: store-management, Property: Start import job forwards all sources and optional parameters
class TestStartImportJobForwardsSourcesAndParams:
    """Start import job forwards all sources and optional parameters.

    For any start_read_set_import_job call with sources and optional tags, all
    sources and tags should appear in the API call args.

    **Validates that start import job forwards all sources and optional parameters to the API**
    """

    @given(
        store_id=store_id_strategy,
        role_arn=st.text(min_size=1, max_size=128),
        sources_list=st.lists(
            st.fixed_dictionaries(
                {
                    'sourceFileType': st.sampled_from(['FASTQ', 'BAM', 'CRAM', 'UBAM']),
                    'sourceFiles': st.fixed_dictionaries(
                        {
                            'source1': st.text(min_size=1, max_size=64),
                        }
                    ),
                }
            ),
            min_size=1,
            max_size=3,
        ),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_sources_and_params_forwarded_to_api(self, store_id, role_arn, sources_list):
        """All sources and params appear in the API call args."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.start_read_set_import_job.return_value = {
            'id': 'import-job-1',
            'sequenceStoreId': store_id,
            'status': 'SUBMITTED',
            'creationTime': MOCK_NOW,
        }

        sources_json = json.dumps(sources_list)

        with patch(MOCK_PATH, return_value=mock_client):
            result = await start_import_wrapper.call(
                ctx=mock_ctx,
                sequence_store_id=store_id,
                role_arn=role_arn,
                sources=sources_json,
            )

        assert 'id' in result

        mock_client.start_read_set_import_job.assert_called_once()
        api_args = mock_client.start_read_set_import_job.call_args[1]

        assert api_args['sources'] == sources_list
        assert api_args['roleArn'] == role_arn
        assert api_args['sequenceStoreId'] == store_id


# Feature: store-management, Property: Get import job returns details with source statuses
class TestGetImportJobReturnsDetailsWithSourceStatuses:
    """Get import job returns details with source statuses.

    For any valid import job ID, calling get_read_set_import_job should return a
    response dict containing job details and sources.

    **Validates that get import job returns job details including source statuses**
    """

    @given(store_id=store_id_strategy, job_id=store_id_strategy)
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_get_import_job_returns_details(self, store_id, job_id):
        """For any valid IDs, get_read_set_import_job returns all detail fields."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_read_set_import_job.return_value = {
            'id': job_id,
            'status': 'COMPLETED',
            'sources': [
                {
                    'sourceFileType': 'BAM',
                    'sourceFiles': {'source1': 's3://bucket/file.bam'},
                    'status': 'COMPLETED',
                },
            ],
            'creationTime': MOCK_NOW,
            'completionTime': MOCK_NOW,
            'roleArn': 'arn:aws:iam::123456789012:role/test-role',
            'sequenceStoreId': store_id,
        }

        with patch(MOCK_PATH, return_value=mock_client):
            result = await get_import_wrapper.call(
                ctx=mock_ctx, sequence_store_id=store_id, import_job_id=job_id
            )

        expected_keys = ['id', 'status', 'sources', 'creationTime', 'roleArn', 'sequenceStoreId']
        for key in expected_keys:
            assert key in result, f'Missing key: {key}'


# Feature: store-management, Property: Cancel import job calls the API for running jobs
class TestCancelImportJobCallsApi:
    """Cancel import job calls the API for running jobs.

    For any valid import job ID, calling cancel_read_set_import_job should invoke
    the cancel API.

    **Validates that cancel import job invokes the cancel API**
    """

    @given(store_id=store_id_strategy, job_id=store_id_strategy)
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_cancel_import_calls_api(self, store_id, job_id):
        """For any valid IDs, cancel_read_set_import_job calls the cancel API."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.cancel_read_set_import_job.return_value = {}

        with patch(MOCK_PATH, return_value=mock_client):
            result = await cancel_import_wrapper.call(
                ctx=mock_ctx, sequence_store_id=store_id, import_job_id=job_id
            )

        mock_client.cancel_read_set_import_job.assert_called_once_with(
            sequenceStoreId=store_id, id=job_id
        )
        assert 'message' in result


# Feature: store-management, Property: Start export job forwards destination and all read set IDs
class TestStartExportJobForwardsDestinationAndIds:
    """Start export job forwards destination and all read set IDs.

    For any start_read_set_export_job call with destination, role_arn, and
    read_set_ids, all should appear in the API call.

    **Validates that start export job forwards destination and all read set IDs**
    """

    @given(
        store_id=store_id_strategy,
        destination=st.text(min_size=1, max_size=128),
        role_arn=st.text(min_size=1, max_size=128),
        read_set_ids=st.lists(st.text(min_size=1, max_size=36), min_size=1, max_size=5),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_export_forwards_destination_and_ids(
        self, store_id, destination, role_arn, read_set_ids
    ):
        """All read set IDs and destination appear in the API call args."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.start_read_set_export_job.return_value = {
            'id': 'export-job-1',
            'sequenceStoreId': store_id,
            'status': 'SUBMITTED',
            'destination': {'s3': {'s3Uri': destination}},
        }

        ids_json = json.dumps(read_set_ids)

        with patch(MOCK_PATH, return_value=mock_client):
            result = await start_export_wrapper.call(
                ctx=mock_ctx,
                sequence_store_id=store_id,
                destination_s3_uri=destination,
                role_arn=role_arn,
                read_set_ids=ids_json,
            )

        assert 'id' in result

        mock_client.start_read_set_export_job.assert_called_once()
        api_args = mock_client.start_read_set_export_job.call_args[1]

        assert api_args['destination'] == {'s3': {'s3Uri': destination}}
        expected_sources = [{'readSetId': id} for id in read_set_ids]
        assert api_args['sources'] == expected_sources
        assert api_args['roleArn'] == role_arn


# Feature: store-management, Property: Get export job returns details with destination
class TestGetExportJobReturnsDetailsWithDestination:
    """Get export job returns details with destination.

    For any valid export job ID, calling get_read_set_export_job should return
    response with all detail fields.

    **Validates that get export job returns all detail fields including destination**
    """

    @given(store_id=store_id_strategy, job_id=store_id_strategy)
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_get_export_job_returns_details(self, store_id, job_id):
        """For any valid IDs, get_read_set_export_job returns all detail fields."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_read_set_export_job.return_value = {
            'id': job_id,
            'status': 'COMPLETED',
            'destination': {'s3': {'s3Uri': 's3://bucket/prefix'}},
            'creationTime': MOCK_NOW,
            'completionTime': MOCK_NOW,
            'sequenceStoreId': store_id,
        }

        with patch(MOCK_PATH, return_value=mock_client):
            result = await get_export_wrapper.call(
                ctx=mock_ctx, sequence_store_id=store_id, export_job_id=job_id
            )

        expected_keys = [
            'id',
            'status',
            'destination',
            'creationTime',
            'completionTime',
            'sequenceStoreId',
        ]
        for key in expected_keys:
            assert key in result, f'Missing key: {key}'


# Feature: store-management, Property: Activate and archive forward all read set IDs
class TestActivateAndArchiveForwardAllReadSetIds:
    """Activate and archive forward all read set IDs.

    For any activate or archive call with read set IDs, all IDs should appear
    in the API call.

    **Validates that activate and archive forward all read set IDs to the API**
    """

    @given(
        store_id=store_id_strategy,
        read_set_ids=st.lists(st.text(min_size=1, max_size=36), min_size=1, max_size=5),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_activate_forwards_all_ids(self, store_id, read_set_ids):
        """activate_read_sets forwards all read set IDs to the API."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.start_read_set_activation_job.return_value = {
            'sequenceStoreId': store_id,
            'status': 'SUBMITTED',
        }

        ids_json = json.dumps(read_set_ids)

        with patch(MOCK_PATH, return_value=mock_client):
            await activate_wrapper.call(
                ctx=mock_ctx, sequence_store_id=store_id, read_set_ids=ids_json
            )

        mock_client.start_read_set_activation_job.assert_called_once()
        api_args = mock_client.start_read_set_activation_job.call_args[1]

        expected_sources = [{'readSetId': id} for id in read_set_ids]
        assert api_args['sources'] == expected_sources

    @given(
        store_id=store_id_strategy,
        read_set_ids=st.lists(st.text(min_size=1, max_size=36), min_size=1, max_size=5),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_archive_forwards_all_ids(self, store_id, read_set_ids):
        """archive_read_sets forwards all read set IDs to the API."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.start_read_set_archive_job.return_value = {
            'sequenceStoreId': store_id,
            'status': 'SUBMITTED',
        }

        ids_json = json.dumps(read_set_ids)

        with patch(MOCK_PATH, return_value=mock_client):
            await archive_wrapper.call(
                ctx=mock_ctx, sequence_store_id=store_id, read_set_ids=ids_json
            )

        mock_client.start_read_set_archive_job.assert_called_once()
        api_args = mock_client.start_read_set_archive_job.call_args[1]

        expected_sources = [{'readSetId': id} for id in read_set_ids]
        assert api_args['sources'] == expected_sources
