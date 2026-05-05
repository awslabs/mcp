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

"""Property-based tests for run group tools."""

import pytest
import uuid
from awslabs.aws_healthomics_mcp_server.tools.run_group import (
    create_run_group,
    get_run_group,
    list_run_groups,
    update_run_group,
)
from datetime import datetime, timezone
from hypothesis import given, settings
from hypothesis import strategies as st
from tests.test_helpers import MCPToolTestWrapper
from unittest.mock import AsyncMock, MagicMock, patch


# --- Hypothesis Strategies ---

name_strategy = st.text(min_size=1, max_size=128)
resource_limit_strategy = st.integers(min_value=1, max_value=100000)
optional_resource_limit_strategy = st.none() | resource_limit_strategy
tags_strategy = st.none() | st.dictionaries(
    st.text(min_size=1, max_size=128),
    st.text(max_size=256),
    max_size=10,
)

# Wrapper for create_run_group
create_run_group_wrapper = MCPToolTestWrapper(create_run_group)

# Strategy and wrapper for get_run_group
run_group_id_strategy = st.text(
    min_size=1, max_size=18, alphabet=st.characters(categories=('Nd',))
)
get_run_group_wrapper = MCPToolTestWrapper(get_run_group)

# Wrapper for list_run_groups
list_run_groups_wrapper = MCPToolTestWrapper(list_run_groups)

# Strategy for pagination tokens
next_token_strategy = st.text(min_size=1, max_size=200)


# Feature: run-group-tools, Property: Create run group forwards only provided optional parameters
class TestCreateRunGroupForwardsOnlyProvidedParams:
    """Create run group forwards only provided optional parameters.

    For any combination of optional parameters (name, maxCpus, maxGpus, maxDuration,
    maxRuns, tags) provided to create_run_group, the HealthOmics API call should contain
    exactly the provided parameters plus the auto-generated requestId, and no other
    optional parameters.

    Validates: optional params forwarded to API, name included when provided, tags included when provided
    """

    @given(
        name=st.none() | name_strategy,
        max_cpus=optional_resource_limit_strategy,
        max_gpus=optional_resource_limit_strategy,
        max_duration=optional_resource_limit_strategy,
        max_runs=optional_resource_limit_strategy,
        tags=tags_strategy,
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_forwards_only_provided_optional_params(
        self, name, max_cpus, max_gpus, max_duration, max_runs, tags
    ):
        """Only provided optional params (plus requestId) are forwarded to the API.

        Validates: optional params forwarded to API, name included when provided, tags included when provided
        """
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.create_run_group.return_value = {
            'id': 'rg-123',
            'arn': 'arn:aws:omics:us-east-1:123456789012:runGroup/rg-123',
            'tags': tags if tags is not None else {},
        }

        kwargs = {}
        if name is not None:
            kwargs['name'] = name
        if max_cpus is not None:
            kwargs['max_cpus'] = max_cpus
        if max_gpus is not None:
            kwargs['max_gpus'] = max_gpus
        if max_duration is not None:
            kwargs['max_duration'] = max_duration
        if max_runs is not None:
            kwargs['max_runs'] = max_runs
        if tags is not None:
            kwargs['tags'] = tags

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_group.get_omics_client',
            return_value=mock_client,
        ):
            await create_run_group_wrapper.call(ctx=mock_ctx, **kwargs)

        # Verify the API was called exactly once
        mock_client.create_run_group.assert_called_once()
        actual_params = mock_client.create_run_group.call_args[1]

        # requestId must always be present
        assert 'requestId' in actual_params

        # Build expected keys: requestId + only the provided optional params
        expected_keys = {'requestId'}
        if name is not None:
            expected_keys.add('name')
            assert actual_params['name'] == name
        if max_cpus is not None:
            expected_keys.add('maxCpus')
            assert actual_params['maxCpus'] == max_cpus
        if max_gpus is not None:
            expected_keys.add('maxGpus')
            assert actual_params['maxGpus'] == max_gpus
        if max_duration is not None:
            expected_keys.add('maxDuration')
            assert actual_params['maxDuration'] == max_duration
        if max_runs is not None:
            expected_keys.add('maxRuns')
            assert actual_params['maxRuns'] == max_runs
        if tags is not None:
            expected_keys.add('tags')
            assert actual_params['tags'] == tags

        # No extra keys beyond what was provided
        assert set(actual_params.keys()) == expected_keys


# Feature: run-group-tools, Property: Create run group auto-generates a valid UUID requestId
class TestCreateRunGroupAutoGeneratesUUID:
    """Create run group auto-generates a valid UUID requestId.

    For any invocation of create_run_group, the requestId passed to the HealthOmics API
    should be a valid UUID v4 string, and the user should not need to provide it.

    Validates: idempotency token auto-generation
    """

    @given(
        name=st.none() | name_strategy,
        max_cpus=optional_resource_limit_strategy,
        max_gpus=optional_resource_limit_strategy,
        max_duration=optional_resource_limit_strategy,
        max_runs=optional_resource_limit_strategy,
        tags=tags_strategy,
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_auto_generates_valid_uuid_request_id(
        self, name, max_cpus, max_gpus, max_duration, max_runs, tags
    ):
        """RequestId is always a valid UUID string, auto-generated without user input.

        Validates: idempotency token auto-generation
        """
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.create_run_group.return_value = {
            'id': 'rg-123',
            'arn': 'arn:aws:omics:us-east-1:123456789012:runGroup/rg-123',
            'tags': {},
        }

        kwargs = {}
        if name is not None:
            kwargs['name'] = name
        if max_cpus is not None:
            kwargs['max_cpus'] = max_cpus
        if max_gpus is not None:
            kwargs['max_gpus'] = max_gpus
        if max_duration is not None:
            kwargs['max_duration'] = max_duration
        if max_runs is not None:
            kwargs['max_runs'] = max_runs
        if tags is not None:
            kwargs['tags'] = tags

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_group.get_omics_client',
            return_value=mock_client,
        ):
            await create_run_group_wrapper.call(ctx=mock_ctx, **kwargs)

        actual_params = mock_client.create_run_group.call_args[1]
        request_id = actual_params['requestId']

        # Validate it's a string
        assert isinstance(request_id, str)

        # Validate it parses as a valid UUID
        parsed = uuid.UUID(request_id)
        assert str(parsed) == request_id


# Feature: run-group-tools, Property: Create run group returns ARN, ID, and tags
class TestCreateRunGroupReturnsArnIdTags:
    """Create run group returns ARN, ID, and tags.

    For any successful create_run_group call, the response dictionary should contain
    the keys id, arn, and tags matching the values returned by the HealthOmics API.

    Validates: successful creation returns run group identifiers and tags
    """

    @given(
        rg_id=st.text(min_size=1, max_size=18, alphabet=st.characters(categories=('Nd',))),
        rg_arn=st.text(min_size=1, max_size=200),
        rg_tags=st.none()
        | st.dictionaries(
            st.text(min_size=1, max_size=128),
            st.text(max_size=256),
            max_size=10,
        ),
        name=st.none() | name_strategy,
        max_cpus=optional_resource_limit_strategy,
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_returns_arn_id_and_tags_from_api(self, rg_id, rg_arn, rg_tags, name, max_cpus):
        """Response contains id, arn, and tags matching the HealthOmics API response.

        Validates: successful creation returns run group identifiers and tags
        """
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.create_run_group.return_value = {
            'id': rg_id,
            'arn': rg_arn,
            'tags': rg_tags,
        }

        kwargs = {}
        if name is not None:
            kwargs['name'] = name
        if max_cpus is not None:
            kwargs['max_cpus'] = max_cpus

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_group.get_omics_client',
            return_value=mock_client,
        ):
            result = await create_run_group_wrapper.call(ctx=mock_ctx, **kwargs)

        # Response must contain exactly id, arn, tags
        assert 'id' in result
        assert 'arn' in result
        assert 'tags' in result

        # Values must match what the API returned
        assert result['id'] == rg_id
        assert result['arn'] == rg_arn
        assert result['tags'] == rg_tags


# Feature: run-group-tools, Property: Get run group returns all detail fields
class TestGetRunGroupReturnsAllDetailFields:
    """Get run group returns all detail fields.

    For any valid run group ID and API response, get_run_group should return a dictionary
    containing all fields: arn, id, name, maxCpus, maxGpus, maxDuration, maxRuns, tags,
    and creationTime (as ISO string).

    Validates: get run group returns complete details with ISO-formatted creation time
    """

    @given(
        run_group_id=run_group_id_strategy,
        arn=st.text(min_size=1, max_size=200),
        name=st.none() | name_strategy,
        max_cpus=optional_resource_limit_strategy,
        max_gpus=optional_resource_limit_strategy,
        max_duration=optional_resource_limit_strategy,
        max_runs=optional_resource_limit_strategy,
        tags=tags_strategy,
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_returns_all_detail_fields(
        self, run_group_id, arn, name, max_cpus, max_gpus, max_duration, max_runs, tags
    ):
        """Response contains all expected fields with creationTime as ISO string.

        Validates: get run group returns complete details with ISO-formatted creation time
        """
        mock_ctx = AsyncMock()
        mock_client = MagicMock()

        creation_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

        mock_client.get_run_group.return_value = {
            'arn': arn,
            'id': run_group_id,
            'name': name,
            'maxCpus': max_cpus,
            'maxGpus': max_gpus,
            'maxDuration': max_duration,
            'maxRuns': max_runs,
            'tags': tags,
            'creationTime': creation_time,
        }

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_group.get_omics_client',
            return_value=mock_client,
        ):
            result = await get_run_group_wrapper.call(ctx=mock_ctx, run_group_id=run_group_id)

        # Verify the API was called with the correct run group ID
        mock_client.get_run_group.assert_called_once_with(id=run_group_id)

        # All expected fields must be present
        expected_fields = {
            'arn',
            'id',
            'name',
            'maxCpus',
            'maxGpus',
            'maxDuration',
            'maxRuns',
            'tags',
            'creationTime',
        }
        assert set(result.keys()) == expected_fields

        # Values must match the API response
        assert result['arn'] == arn
        assert result['id'] == run_group_id
        assert result['name'] == name
        assert result['maxCpus'] == max_cpus
        assert result['maxGpus'] == max_gpus
        assert result['maxDuration'] == max_duration
        assert result['maxRuns'] == max_runs
        assert result['tags'] == tags

        # creationTime must be converted to ISO format string
        assert result['creationTime'] == creation_time.isoformat()
        assert isinstance(result['creationTime'], str)


# Feature: run-group-tools, Property: List run groups forwards only provided filter parameters
class TestListRunGroupsForwardsOnlyProvidedFilterParams:
    """List run groups forwards only provided filter parameters.

    For any combination of optional parameters (name, next_token) provided to
    list_run_groups, the HealthOmics API call should contain exactly the provided
    filter parameters plus maxResults, and no other optional parameters.

    Validates: name filter, pagination token, and maxResults forwarded to API
    """

    @given(
        name=st.none() | name_strategy,
        max_results=st.integers(min_value=1, max_value=100),
        next_token=st.none() | next_token_strategy,
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_forwards_only_provided_filter_params(self, name, max_results, next_token):
        """Only provided filter params (plus maxResults) are forwarded to the API.

        Validates: name filter, pagination token, and maxResults forwarded to API
        """
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_run_groups.return_value = {
            'items': [],
        }

        kwargs = {'max_results': max_results}
        if name is not None:
            kwargs['name'] = name
        if next_token is not None:
            kwargs['next_token'] = next_token

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_group.get_omics_client',
            return_value=mock_client,
        ):
            await list_run_groups_wrapper.call(ctx=mock_ctx, **kwargs)

        # Verify the API was called exactly once
        mock_client.list_run_groups.assert_called_once()
        actual_params = mock_client.list_run_groups.call_args[1]

        # maxResults must always be present
        assert 'maxResults' in actual_params
        assert actual_params['maxResults'] == max_results

        # Build expected keys: maxResults + only the provided optional params
        expected_keys = {'maxResults'}
        if name is not None:
            expected_keys.add('name')
            assert actual_params['name'] == name
        if next_token is not None:
            expected_keys.add('startingToken')
            assert actual_params['startingToken'] == next_token

        # No extra keys beyond what was provided
        assert set(actual_params.keys()) == expected_keys


# Feature: run-group-tools, Property: List run groups forwards nextToken from API response
class TestListRunGroupsForwardsNextToken:
    """List run groups forwards nextToken from API response.

    For any API response from list_run_groups, if the response contains a nextToken,
    the tool response should include it; if the API response does not contain a
    nextToken, the tool response should not include it.

    Validates: list run groups returns summaries and pagination token handling
    """

    @given(
        next_token=next_token_strategy,
        max_results=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_includes_next_token_when_present(self, next_token, max_results):
        """When API response contains nextToken, tool response includes it.

        Validates: pagination token forwarded from API response
        """
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_run_groups.return_value = {
            'items': [],
            'nextToken': next_token,
        }

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_group.get_omics_client',
            return_value=mock_client,
        ):
            result = await list_run_groups_wrapper.call(ctx=mock_ctx, max_results=max_results)

        assert 'nextToken' in result
        assert result['nextToken'] == next_token

    @given(
        max_results=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_excludes_next_token_when_absent(self, max_results):
        """When API response does not contain nextToken, tool response omits it.

        Validates: pagination token omitted when absent from API response
        """
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_run_groups.return_value = {
            'items': [],
        }

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_group.get_omics_client',
            return_value=mock_client,
        ):
            result = await list_run_groups_wrapper.call(ctx=mock_ctx, max_results=max_results)

        assert 'nextToken' not in result
        assert 'runGroups' in result


# Wrapper for update_run_group
update_run_group_wrapper = MCPToolTestWrapper(update_run_group)


# Feature: run-group-tools, Property: Update run group forwards only provided update parameters
class TestUpdateRunGroupForwardsOnlyProvidedParams:
    """Update run group forwards only provided update parameters.

    For any combination of optional update parameters (name, maxCpus, maxGpus,
    maxDuration, maxRuns) provided to update_run_group, the HealthOmics API call
    should contain the id plus exactly the provided parameters, and the response
    should contain the run group ID with a success status.

    Validates: update forwards only provided params and returns success confirmation
    """

    @given(
        run_group_id=run_group_id_strategy,
        name=st.none() | name_strategy,
        max_cpus=optional_resource_limit_strategy,
        max_gpus=optional_resource_limit_strategy,
        max_duration=optional_resource_limit_strategy,
        max_runs=optional_resource_limit_strategy,
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_forwards_only_provided_update_params(
        self, run_group_id, name, max_cpus, max_gpus, max_duration, max_runs
    ):
        """Only provided update params (plus id) are forwarded to the API.

        Also verifies response contains {id, status: 'updated'}.

        Validates: update forwards only provided params and returns success confirmation
        """
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.update_run_group.return_value = {}

        kwargs = {'run_group_id': run_group_id}
        if name is not None:
            kwargs['name'] = name
        if max_cpus is not None:
            kwargs['max_cpus'] = max_cpus
        if max_gpus is not None:
            kwargs['max_gpus'] = max_gpus
        if max_duration is not None:
            kwargs['max_duration'] = max_duration
        if max_runs is not None:
            kwargs['max_runs'] = max_runs

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_group.get_omics_client',
            return_value=mock_client,
        ):
            result = await update_run_group_wrapper.call(ctx=mock_ctx, **kwargs)

        # Verify the API was called exactly once
        mock_client.update_run_group.assert_called_once()
        actual_params = mock_client.update_run_group.call_args[1]

        # id must always be present
        assert 'id' in actual_params
        assert actual_params['id'] == run_group_id

        # Build expected keys: id + only the provided optional params
        expected_keys = {'id'}
        if name is not None:
            expected_keys.add('name')
            assert actual_params['name'] == name
        if max_cpus is not None:
            expected_keys.add('maxCpus')
            assert actual_params['maxCpus'] == max_cpus
        if max_gpus is not None:
            expected_keys.add('maxGpus')
            assert actual_params['maxGpus'] == max_gpus
        if max_duration is not None:
            expected_keys.add('maxDuration')
            assert actual_params['maxDuration'] == max_duration
        if max_runs is not None:
            expected_keys.add('maxRuns')
            assert actual_params['maxRuns'] == max_runs

        # No extra keys beyond what was provided
        assert set(actual_params.keys()) == expected_keys

        # Response must contain id and status
        assert result == {'id': run_group_id, 'status': 'updated'}


# Strategy for error messages
error_message_strategy = st.text(min_size=1, max_size=200)


# Feature: run-group-tools, Property: All run group tools return structured errors on API failure
class TestAllRunGroupToolsReturnStructuredErrorsOnApiFailure:
    """All run group tools return structured errors on API failure.

    For any run group tool (create, get, list, update), when the HealthOmics API
    raises an exception, the tool should return a structured error response via
    handle_tool_error rather than propagating the exception.

    Validates: structured error handling for all run group tools
    """

    @given(error_msg=error_message_strategy)
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_create_run_group_returns_structured_error(self, error_msg):
        """create_run_group returns structured error on API failure.

        Validates: create run group error handling
        """
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.create_run_group.side_effect = Exception(error_msg)

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_group.get_omics_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_group.handle_tool_error',
                new_callable=AsyncMock,
                return_value={'error': f'Error creating run group: {error_msg}'},
            ) as mock_handle_error,
        ):
            result = await create_run_group_wrapper.call(ctx=mock_ctx)

        # handle_tool_error must have been called
        mock_handle_error.assert_called_once()
        call_args = mock_handle_error.call_args
        assert call_args[0][0] is mock_ctx
        assert isinstance(call_args[0][1], Exception)
        assert str(call_args[0][1]) == error_msg
        assert call_args[0][2] == 'Error creating run group'

        # Result is a structured error dict, not a raised exception
        assert isinstance(result, dict)
        assert 'error' in result

    @given(
        run_group_id=run_group_id_strategy,
        error_msg=error_message_strategy,
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_get_run_group_returns_structured_error(self, run_group_id, error_msg):
        """get_run_group returns structured error on API failure.

        Validates: get run group error handling
        """
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_run_group.side_effect = Exception(error_msg)

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_group.get_omics_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_group.handle_tool_error',
                new_callable=AsyncMock,
                return_value={'error': f'Error getting run group: {error_msg}'},
            ) as mock_handle_error,
        ):
            result = await get_run_group_wrapper.call(ctx=mock_ctx, run_group_id=run_group_id)

        mock_handle_error.assert_called_once()
        call_args = mock_handle_error.call_args
        assert call_args[0][0] is mock_ctx
        assert isinstance(call_args[0][1], Exception)
        assert str(call_args[0][1]) == error_msg
        assert call_args[0][2] == 'Error getting run group'

        assert isinstance(result, dict)
        assert 'error' in result

    @given(error_msg=error_message_strategy)
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_list_run_groups_returns_structured_error(self, error_msg):
        """list_run_groups returns structured error on API failure.

        Validates: list run groups error handling
        """
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_run_groups.side_effect = Exception(error_msg)

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_group.get_omics_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_group.handle_tool_error',
                new_callable=AsyncMock,
                return_value={'error': f'Error listing run groups: {error_msg}'},
            ) as mock_handle_error,
        ):
            result = await list_run_groups_wrapper.call(ctx=mock_ctx)

        mock_handle_error.assert_called_once()
        call_args = mock_handle_error.call_args
        assert call_args[0][0] is mock_ctx
        assert isinstance(call_args[0][1], Exception)
        assert str(call_args[0][1]) == error_msg
        assert call_args[0][2] == 'Error listing run groups'

        assert isinstance(result, dict)
        assert 'error' in result

    @given(
        run_group_id=run_group_id_strategy,
        error_msg=error_message_strategy,
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_update_run_group_returns_structured_error(self, run_group_id, error_msg):
        """update_run_group returns structured error on API failure.

        Validates: update run group error handling
        """
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.update_run_group.side_effect = Exception(error_msg)

        with (
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_group.get_omics_client',
                return_value=mock_client,
            ),
            patch(
                'awslabs.aws_healthomics_mcp_server.tools.run_group.handle_tool_error',
                new_callable=AsyncMock,
                return_value={'error': f'Error updating run group: {error_msg}'},
            ) as mock_handle_error,
        ):
            result = await update_run_group_wrapper.call(ctx=mock_ctx, run_group_id=run_group_id)

        mock_handle_error.assert_called_once()
        call_args = mock_handle_error.call_args
        assert call_args[0][0] is mock_ctx
        assert isinstance(call_args[0][1], Exception)
        assert str(call_args[0][1]) == error_msg
        assert call_args[0][2] == 'Error updating run group'

        assert isinstance(result, dict)
        assert 'error' in result


# ============================================================================
# Unit Tests for Run Group Tools
# ============================================================================


# --- create_run_group unit tests ---


@pytest.mark.asyncio
async def test_create_run_group_success_all_params():
    """Test create_run_group with all parameters provided."""
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.create_run_group.return_value = {
        'id': '1234567890',
        'arn': 'arn:aws:omics:us-east-1:123456789012:runGroup/1234567890',
        'tags': {'env': 'prod', 'team': 'genomics'},
    }

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.run_group.get_omics_client',
        return_value=mock_client,
    ):
        result = await create_run_group_wrapper.call(
            ctx=mock_ctx,
            name='my-run-group',
            max_cpus=256,
            max_gpus=4,
            max_duration=600,
            max_runs=10,
            tags={'env': 'prod', 'team': 'genomics'},
        )

    mock_client.create_run_group.assert_called_once()
    call_kwargs = mock_client.create_run_group.call_args[1]
    assert call_kwargs['name'] == 'my-run-group'
    assert call_kwargs['maxCpus'] == 256
    assert call_kwargs['maxGpus'] == 4
    assert call_kwargs['maxDuration'] == 600
    assert call_kwargs['maxRuns'] == 10
    assert call_kwargs['tags'] == {'env': 'prod', 'team': 'genomics'}
    assert 'requestId' in call_kwargs

    assert result['id'] == '1234567890'
    assert result['arn'] == 'arn:aws:omics:us-east-1:123456789012:runGroup/1234567890'
    assert result['tags'] == {'env': 'prod', 'team': 'genomics'}


@pytest.mark.asyncio
async def test_create_run_group_success_minimal_params():
    """Test create_run_group with no optional parameters."""
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.create_run_group.return_value = {
        'id': '9999',
        'arn': 'arn:aws:omics:us-east-1:123456789012:runGroup/9999',
        'tags': None,
    }

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.run_group.get_omics_client',
        return_value=mock_client,
    ):
        result = await create_run_group_wrapper.call(ctx=mock_ctx)

    call_kwargs = mock_client.create_run_group.call_args[1]
    # Only requestId should be present
    assert set(call_kwargs.keys()) == {'requestId'}

    assert result['id'] == '9999'
    assert result['arn'] == 'arn:aws:omics:us-east-1:123456789012:runGroup/9999'
    assert result['tags'] is None


@pytest.mark.asyncio
async def test_create_run_group_api_error():
    """Test create_run_group returns structured error on API failure."""
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.create_run_group.side_effect = Exception('Access denied')

    with (
        patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_group.get_omics_client',
            return_value=mock_client,
        ),
        patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_group.handle_tool_error',
            new_callable=AsyncMock,
            return_value={'error': 'Error creating run group: Access denied'},
        ) as mock_handle_error,
    ):
        result = await create_run_group_wrapper.call(ctx=mock_ctx)

    mock_handle_error.assert_called_once()
    assert result == {'error': 'Error creating run group: Access denied'}


# --- get_run_group unit tests ---


@pytest.mark.asyncio
async def test_get_run_group_success():
    """Test get_run_group returns all detail fields."""
    creation_time = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.get_run_group.return_value = {
        'arn': 'arn:aws:omics:us-east-1:123456789012:runGroup/12345',
        'id': '12345',
        'name': 'production-group',
        'maxCpus': 512,
        'maxGpus': 8,
        'maxDuration': 1440,
        'maxRuns': 20,
        'tags': {'env': 'prod'},
        'creationTime': creation_time,
    }

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.run_group.get_omics_client',
        return_value=mock_client,
    ):
        result = await get_run_group_wrapper.call(ctx=mock_ctx, run_group_id='12345')

    mock_client.get_run_group.assert_called_once_with(id='12345')
    assert result['arn'] == 'arn:aws:omics:us-east-1:123456789012:runGroup/12345'
    assert result['id'] == '12345'
    assert result['name'] == 'production-group'
    assert result['maxCpus'] == 512
    assert result['maxGpus'] == 8
    assert result['maxDuration'] == 1440
    assert result['maxRuns'] == 20
    assert result['tags'] == {'env': 'prod'}
    assert result['creationTime'] == creation_time.isoformat()


@pytest.mark.asyncio
async def test_get_run_group_api_error():
    """Test get_run_group returns structured error on API failure."""
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.get_run_group.side_effect = Exception('Not found')

    with (
        patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_group.get_omics_client',
            return_value=mock_client,
        ),
        patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_group.handle_tool_error',
            new_callable=AsyncMock,
            return_value={'error': 'Error getting run group: Not found'},
        ) as mock_handle_error,
    ):
        result = await get_run_group_wrapper.call(ctx=mock_ctx, run_group_id='99999')

    mock_handle_error.assert_called_once()
    assert result == {'error': 'Error getting run group: Not found'}


# --- list_run_groups unit tests ---


@pytest.mark.asyncio
async def test_list_run_groups_success():
    """Test list_run_groups returns run group summaries."""
    creation_time = datetime(2024, 3, 10, 8, 0, 0, tzinfo=timezone.utc)
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_run_groups.return_value = {
        'items': [
            {
                'id': '111',
                'arn': 'arn:aws:omics:us-east-1:123456789012:runGroup/111',
                'name': 'group-a',
                'maxCpus': 100,
                'maxGpus': None,
                'maxDuration': 60,
                'maxRuns': 5,
                'creationTime': creation_time,
            },
        ],
    }

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.run_group.get_omics_client',
        return_value=mock_client,
    ):
        result = await list_run_groups_wrapper.call(ctx=mock_ctx, max_results=10)

    mock_client.list_run_groups.assert_called_once_with(maxResults=10)
    assert len(result['runGroups']) == 1
    assert result['runGroups'][0]['id'] == '111'
    assert result['runGroups'][0]['name'] == 'group-a'
    assert result['runGroups'][0]['maxCpus'] == 100
    assert result['runGroups'][0]['creationTime'] == creation_time.isoformat()
    assert 'nextToken' not in result


@pytest.mark.asyncio
async def test_list_run_groups_with_filters():
    """Test list_run_groups passes name filter and pagination token."""
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_run_groups.return_value = {
        'items': [],
        'nextToken': 'page2',
    }

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.run_group.get_omics_client',
        return_value=mock_client,
    ):
        result = await list_run_groups_wrapper.call(
            ctx=mock_ctx, name='prod', max_results=5, next_token='page1'
        )

    mock_client.list_run_groups.assert_called_once_with(
        maxResults=5, name='prod', startingToken='page1'
    )
    assert result['nextToken'] == 'page2'


@pytest.mark.asyncio
async def test_list_run_groups_empty_response():
    """Test list_run_groups with no items returned."""
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_run_groups.return_value = {'items': []}

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.run_group.get_omics_client',
        return_value=mock_client,
    ):
        result = await list_run_groups_wrapper.call(ctx=mock_ctx, max_results=10)

    assert result['runGroups'] == []
    assert 'nextToken' not in result


@pytest.mark.asyncio
async def test_list_run_groups_pagination():
    """Test list_run_groups includes nextToken when present in API response."""
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_run_groups.return_value = {
        'items': [
            {
                'id': '222',
                'arn': 'arn:aws:omics:us-east-1:123456789012:runGroup/222',
                'name': 'group-b',
                'creationTime': datetime(2024, 1, 1, tzinfo=timezone.utc),
            },
        ],
        'nextToken': 'token-abc',
    }

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.run_group.get_omics_client',
        return_value=mock_client,
    ):
        result = await list_run_groups_wrapper.call(ctx=mock_ctx, max_results=1)

    assert result['nextToken'] == 'token-abc'
    assert len(result['runGroups']) == 1


@pytest.mark.asyncio
async def test_list_run_groups_api_error():
    """Test list_run_groups returns structured error on API failure."""
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_run_groups.side_effect = Exception('Service unavailable')

    with (
        patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_group.get_omics_client',
            return_value=mock_client,
        ),
        patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_group.handle_tool_error',
            new_callable=AsyncMock,
            return_value={'error': 'Error listing run groups: Service unavailable'},
        ) as mock_handle_error,
    ):
        result = await list_run_groups_wrapper.call(ctx=mock_ctx)

    mock_handle_error.assert_called_once()
    assert result == {'error': 'Error listing run groups: Service unavailable'}


# --- update_run_group unit tests ---


@pytest.mark.asyncio
async def test_update_run_group_success_all_params():
    """Test update_run_group with all optional parameters."""
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.update_run_group.return_value = {}

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.run_group.get_omics_client',
        return_value=mock_client,
    ):
        result = await update_run_group_wrapper.call(
            ctx=mock_ctx,
            run_group_id='12345',
            name='updated-name',
            max_cpus=1024,
            max_gpus=16,
            max_duration=2880,
            max_runs=50,
        )

    call_kwargs = mock_client.update_run_group.call_args[1]
    assert call_kwargs == {
        'id': '12345',
        'name': 'updated-name',
        'maxCpus': 1024,
        'maxGpus': 16,
        'maxDuration': 2880,
        'maxRuns': 50,
    }
    assert result == {'id': '12345', 'status': 'updated'}


@pytest.mark.asyncio
async def test_update_run_group_success_partial_params():
    """Test update_run_group with only some optional parameters."""
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.update_run_group.return_value = {}

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.run_group.get_omics_client',
        return_value=mock_client,
    ):
        result = await update_run_group_wrapper.call(
            ctx=mock_ctx,
            run_group_id='67890',
            max_cpus=512,
        )

    call_kwargs = mock_client.update_run_group.call_args[1]
    assert call_kwargs == {'id': '67890', 'maxCpus': 512}
    assert result == {'id': '67890', 'status': 'updated'}


@pytest.mark.asyncio
async def test_update_run_group_success_name_only():
    """Test update_run_group with only name parameter."""
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.update_run_group.return_value = {}

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.run_group.get_omics_client',
        return_value=mock_client,
    ):
        result = await update_run_group_wrapper.call(
            ctx=mock_ctx,
            run_group_id='11111',
            name='new-name',
        )

    call_kwargs = mock_client.update_run_group.call_args[1]
    assert call_kwargs == {'id': '11111', 'name': 'new-name'}
    assert result == {'id': '11111', 'status': 'updated'}


@pytest.mark.asyncio
async def test_update_run_group_api_error():
    """Test update_run_group returns structured error on API failure."""
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.update_run_group.side_effect = Exception('Throttling')

    with (
        patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_group.get_omics_client',
            return_value=mock_client,
        ),
        patch(
            'awslabs.aws_healthomics_mcp_server.tools.run_group.handle_tool_error',
            new_callable=AsyncMock,
            return_value={'error': 'Error updating run group: Throttling'},
        ) as mock_handle_error,
    ):
        result = await update_run_group_wrapper.call(ctx=mock_ctx, run_group_id='12345')

    mock_handle_error.assert_called_once()
    assert result == {'error': 'Error updating run group: Throttling'}
