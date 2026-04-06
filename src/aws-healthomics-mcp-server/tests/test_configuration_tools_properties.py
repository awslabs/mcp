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

"""Property-based tests for VPC configuration management tools."""

import pytest
from awslabs.aws_healthomics_mcp_server.tools.configuration_tools import (
    create_configuration,
    delete_configuration,
    get_configuration,
    list_configurations,
)
from awslabs.aws_healthomics_mcp_server.tools.workflow_execution import start_run
from datetime import datetime, timezone
from hypothesis import given, settings
from hypothesis import strategies as st
from tests.test_helpers import MCPToolTestWrapper
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch


# --- Hypothesis Strategies ---

valid_config_name_strategy = st.text(
    min_size=1,
    max_size=50,
    alphabet=st.characters(categories=('L', 'N', 'P')),
).filter(lambda s: s.lower() != 'default')

# --- Tool Wrappers ---

create_wrapper = MCPToolTestWrapper(create_configuration)
get_wrapper = MCPToolTestWrapper(get_configuration)
list_wrapper = MCPToolTestWrapper(list_configurations)
delete_wrapper = MCPToolTestWrapper(delete_configuration)

MOCK_PATH = 'awslabs.aws_healthomics_mcp_server.tools.configuration_tools.get_omics_client'
MOCK_WE_PATH = 'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client'

start_run_wrapper = MCPToolTestWrapper(start_run)
MOCK_NOW = datetime.now(timezone.utc)


# Property: Create configuration returns required fields
class TestCreateConfigurationReturnsRequiredFields:
    """Create configuration returns required fields.

    For any valid configuration name (1-50 characters, not 'default'), calling
    create_configuration with a mocked API response should return a dict containing
    arn, uuid, name, status, and creationTime keys with non-empty values.

    **Validates: Requirements Create Configuration Tool**
    """

    @given(name=valid_config_name_strategy)
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_create_configuration_returns_required_fields(self, name):
        """For any valid config name, create returns arn, uuid, name, status, creationTime."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.create_configuration.return_value = {
            'arn': f'arn:aws:omics:us-east-1:123456789012:configuration/{name}',
            'uuid': 'abc-123-def-456',
            'name': name,
            'status': 'CREATING',
            'creationTime': MOCK_NOW,
        }

        with patch(MOCK_PATH, return_value=mock_client):
            result = await create_wrapper.call(ctx=mock_ctx, name=name)

        required_keys = ['arn', 'uuid', 'name', 'status', 'creationTime']
        for key in required_keys:
            assert key in result, f'Missing key: {key}'
            assert result[key], f'Empty value for key: {key}'


# Property: Configuration name length validation
class TestConfigurationNameLengthValidation:
    """Configuration name length validation.

    For any string longer than 50 characters, calling create_configuration should
    return a validation error and the underlying API should never be called.

    **Validates: Requirements Create Configuration Tool**
    """

    @given(name=st.text(min_size=51, max_size=200))
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_long_name_returns_error_and_api_never_called(self, name):
        """Names exceeding max length return a validation error without calling the API."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()

        with patch(MOCK_PATH, return_value=mock_client):
            result = await create_wrapper.call(ctx=mock_ctx, name=name)

        assert 'error' in result, f'Expected error key in result for name of length {len(name)}'
        mock_client.create_configuration.assert_not_called()


# Strategy: Generate case variations of 'default' using a tuple of booleans
# Each boolean decides upper/lower for the corresponding character in 'default'
_DEFAULT_CHARS = 'default'
case_varied_default_strategy = st.tuples(*[st.booleans() for _ in _DEFAULT_CHARS]).map(
    lambda bools: ''.join(c.upper() if b else c.lower() for c, b in zip(_DEFAULT_CHARS, bools))
)


# Property: Reserved name rejection across case variations
class TestReservedNameRejection:
    """Reserved name rejection across case variations.

    For any case variation of the string 'default' (e.g., 'Default', 'DEFAULT',
    'dEfAuLt'), calling create_configuration should return a validation error
    indicating the name is reserved, and the underlying API should never be called.

    **Validates: Requirements Create Configuration Tool**
    """

    @given(name=case_varied_default_strategy)
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_reserved_name_rejected_across_case_variations(self, name):
        """Any case variation of 'default' returns a validation error without calling the API."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()

        with patch(MOCK_PATH, return_value=mock_client):
            result = await create_wrapper.call(ctx=mock_ctx, name=name)

        assert 'error' in result, f'Expected error for reserved name variation: {name}'
        mock_client.create_configuration.assert_not_called()


# Property: Optional create parameters forwarded to API
class TestOptionalCreateParametersForwarded:
    """Optional create parameters forwarded to API.

    For any combination of optional parameters (description, tags) provided to
    create_configuration, all provided parameters should appear in the arguments
    passed to the underlying API call.

    **Validates: Requirements Create Configuration Tool**
    """

    @given(
        name=valid_config_name_strategy,
        description=st.one_of(st.none(), st.text(min_size=1, max_size=100)),
        tags=st.one_of(
            st.none(),
            st.dictionaries(
                st.text(min_size=1, max_size=20, alphabet=st.characters(categories=('L',))),
                st.text(min_size=1, max_size=20, alphabet=st.characters(categories=('L',))),
                min_size=1,
                max_size=3,
            ),
        ),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_optional_params_forwarded_to_api(self, name, description, tags):
        """All provided optional parameters appear in the API call arguments."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.create_configuration.return_value = {
            'arn': f'arn:aws:omics:us-east-1:123456789012:configuration/{name}',
            'uuid': 'abc-123-def-456',
            'name': name,
            'status': 'CREATING',
            'creationTime': MOCK_NOW,
        }

        kwargs = {'ctx': mock_ctx, 'name': name}
        if description is not None:
            kwargs['description'] = description
        if tags is not None:
            kwargs['tags'] = tags

        with patch(MOCK_PATH, return_value=mock_client):
            await create_wrapper.call(**kwargs)

        # Name should always be in the API call
        call_kwargs = mock_client.create_configuration.call_args
        assert call_kwargs is not None, 'API should have been called'
        assert 'name' in call_kwargs.kwargs or (
            call_kwargs.args and 'name' in call_kwargs.kwargs
        ), 'name should always be in API call'

        # Check that description is forwarded when provided
        if description is not None:
            assert 'description' in call_kwargs.kwargs, (
                f'description should be in API call when provided, got {call_kwargs.kwargs}'
            )

        # Check that tags are forwarded when provided
        if tags is not None:
            assert 'tags' in call_kwargs.kwargs, (
                f'tags should be in API call when provided, got {call_kwargs.kwargs}'
            )


# Property: API errors produce error dicts across all configuration tools
class TestApiErrorsProduceErrorDicts:
    """API errors produce error dicts across all configuration tools.

    For any configuration tool function (create, get, list, delete), when the
    underlying API raises an exception, the tool should return a dict containing
    an `error` key with a non-empty string message.

    **Validates: Requirements Create Configuration Tool, Get Configuration Tool, Delete Configuration Tool**
    """

    @given(error_msg=st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_create_configuration_api_error_returns_error_dict(self, error_msg):
        """Create configuration returns error dict when API raises an exception."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.create_configuration.side_effect = Exception(error_msg)

        with patch(MOCK_PATH, return_value=mock_client):
            result = await create_wrapper.call(ctx=mock_ctx, name='valid-name')

        assert isinstance(result, dict)
        assert 'error' in result
        assert isinstance(result['error'], str)
        assert len(result['error']) > 0

    @given(error_msg=st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_get_configuration_api_error_returns_error_dict(self, error_msg):
        """Get configuration returns error dict when API raises an exception."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_configuration.side_effect = Exception(error_msg)

        with patch(MOCK_PATH, return_value=mock_client):
            result = await get_wrapper.call(ctx=mock_ctx, name='some-config')

        assert isinstance(result, dict)
        assert 'error' in result
        assert isinstance(result['error'], str)
        assert len(result['error']) > 0

    @given(error_msg=st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_list_configurations_api_error_returns_error_dict(self, error_msg):
        """List configurations returns error dict when API raises an exception."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_configurations.side_effect = Exception(error_msg)

        with patch(MOCK_PATH, return_value=mock_client):
            result = await list_wrapper.call(ctx=mock_ctx)

        assert isinstance(result, dict)
        assert 'error' in result
        assert isinstance(result['error'], str)
        assert len(result['error']) > 0

    @given(error_msg=st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_delete_configuration_api_error_returns_error_dict(self, error_msg):
        """Delete configuration returns error dict when API raises an exception."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.delete_configuration.side_effect = Exception(error_msg)

        with patch(MOCK_PATH, return_value=mock_client):
            result = await delete_wrapper.call(ctx=mock_ctx, name='some-config')

        assert isinstance(result, dict)
        assert 'error' in result
        assert isinstance(result['error'], str)
        assert len(result['error']) > 0


# Property: Get configuration returns all specified fields
class TestGetConfigurationReturnsAllFields:
    """Get configuration returns all specified fields.

    For any valid configuration name, calling get_configuration with a mocked API
    response should return a dict containing arn, uuid, name, runConfigurations,
    status, creationTime, and tags keys.

    **Validates: Requirements Get Configuration Tool**
    """

    @given(name=valid_config_name_strategy)
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_get_configuration_returns_all_fields(self, name):
        """For any valid config name, get returns arn, uuid, name, runConfigurations, status, creationTime, tags."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_configuration.return_value = {
            'arn': f'arn:aws:omics:us-east-1:123456789012:configuration/{name}',
            'uuid': 'abc-123-def-456',
            'name': name,
            'runConfigurations': {
                'securityGroupIds': ['sg-12345'],
                'subnetIds': ['subnet-12345'],
            },
            'status': 'ACTIVE',
            'creationTime': MOCK_NOW,
            'tags': {'env': 'test'},
        }

        with patch(MOCK_PATH, return_value=mock_client):
            result = await get_wrapper.call(ctx=mock_ctx, name=name)

        expected_keys = [
            'arn',
            'uuid',
            'name',
            'runConfigurations',
            'status',
            'creationTime',
            'tags',
        ]
        for key in expected_keys:
            assert key in result, f'Missing key: {key}'


# Property: List configurations returns items and forwards pagination
class TestListConfigurationsReturnsItemsAndPagination:
    """List configurations returns items and forwards pagination.

    For any max_results (1-100) and optional next_token, calling list_configurations
    should return a dict with a configurations list, forward maxResults and nextToken
    to the API, and include nextToken in the response when the API response contains one.

    **Validates: Requirements List Configurations Tool**
    """

    @given(
        max_results=st.integers(min_value=1, max_value=100),
        next_token=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_list_configurations_returns_items_and_forwards_pagination(
        self, max_results, next_token
    ):
        """List returns configurations list and forwards pagination params to API."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()

        api_response: dict[str, Any] = {
            'items': [
                {
                    'arn': 'arn:aws:omics:us-east-1:123456789012:configuration/test-config',
                    'name': 'test-config',
                    'description': 'A test configuration',
                    'status': 'ACTIVE',
                    'creationTime': MOCK_NOW,
                },
            ],
        }
        if next_token is not None:
            api_response['nextToken'] = 'next-page-token'

        mock_client.list_configurations.return_value = api_response

        kwargs = {'ctx': mock_ctx, 'max_results': max_results}
        if next_token is not None:
            kwargs['next_token'] = next_token

        with patch(MOCK_PATH, return_value=mock_client):
            result = await list_wrapper.call(**kwargs)

        # Result contains configurations list
        assert 'configurations' in result
        assert isinstance(result['configurations'], list)

        # maxResults was forwarded to the API call
        call_kwargs = mock_client.list_configurations.call_args
        assert call_kwargs is not None
        assert call_kwargs.kwargs.get('maxResults') == max_results

        # next_token forwarded when provided
        if next_token is not None:
            assert call_kwargs.kwargs.get('nextToken') == next_token

        # nextToken in response when API returned one
        if 'nextToken' in api_response:
            assert 'nextToken' in result


# Property: Delete configuration returns confirmation
class TestDeleteConfigurationReturnsConfirmation:
    """Delete configuration returns confirmation.

    For any valid configuration name, calling delete_configuration with a mocked API
    should return a confirmation dict containing the configuration name and status.

    **Validates: Requirements Delete Configuration Tool**
    """

    @given(name=valid_config_name_strategy)
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_delete_configuration_returns_confirmation(self, name):
        """For any valid config name, delete returns name and status DELETING."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.delete_configuration.return_value = {}

        with patch(MOCK_PATH, return_value=mock_client):
            result = await delete_wrapper.call(ctx=mock_ctx, name=name)

        assert 'name' in result, 'Missing key: name'
        assert 'status' in result, 'Missing key: status'
        assert result['status'] == 'DELETING'


# Property: Networking mode and configuration name mutual validation
class TestNetworkingModeConfigNameValidation:
    """Networking mode and configuration name mutual validation.

    For any combination of networking_mode and configuration_name:
    - VPC + no config_name → error
    - RESTRICTED + config_name → error
    - invalid mode → error
    - valid combos → no error

    **Validates: Requirements Start Run VPC Networking Support**
    """

    # Common required params for start_run
    _base_params = {
        'workflow_id': 'wf-12345',
        'role_arn': 'arn:aws:iam::123456789012:role/test-role',
        'name': 'test-run',
        'output_uri': 's3://bucket/output/',
        'parameters': {'input': 's3://bucket/input.bam'},
    }

    @given(st.just(None))
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_vpc_mode_without_config_name_returns_error(self, _):
        """VPC mode without configuration_name returns a validation error."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()

        with patch(MOCK_WE_PATH, return_value=mock_client):
            result = await start_run_wrapper.call(
                ctx=mock_ctx,
                **self._base_params,
                networking_mode='VPC',
                configuration_name=None,
            )

        assert 'error' in result

    @given(config_name=st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_restricted_mode_with_config_name_returns_error(self, config_name):
        """RESTRICTED mode with a configuration_name returns a validation error."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()

        with patch(MOCK_WE_PATH, return_value=mock_client):
            result = await start_run_wrapper.call(
                ctx=mock_ctx,
                **self._base_params,
                networking_mode='RESTRICTED',
                configuration_name=config_name,
            )

        assert 'error' in result

    @given(mode=st.text(min_size=1, max_size=20).filter(lambda s: s not in ['RESTRICTED', 'VPC']))
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_invalid_mode_returns_error(self, mode):
        """An invalid networking mode returns a validation error."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()

        with patch(MOCK_WE_PATH, return_value=mock_client):
            result = await start_run_wrapper.call(
                ctx=mock_ctx,
                **self._base_params,
                networking_mode=mode,
            )

        assert 'error' in result

    @given(
        data=st.sampled_from(
            [
                ('VPC', 'my-vpc-config'),
                ('RESTRICTED', None),
                (None, None),
            ]
        ),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_valid_combinations_no_error(self, data):
        """Valid networking_mode / configuration_name combos do not produce errors."""
        mode, config_name = data
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.start_run.return_value = {
            'id': 'run-12345',
            'arn': 'arn:aws:omics:us-east-1:123456789012:run/run-12345',
            'status': 'PENDING',
        }

        call_kwargs = {**self._base_params}
        if mode is not None:
            call_kwargs['networking_mode'] = mode
        if config_name is not None:
            call_kwargs['configuration_name'] = config_name

        with patch(MOCK_WE_PATH, return_value=mock_client):
            result = await start_run_wrapper.call(ctx=mock_ctx, **call_kwargs)

        assert 'error' not in result, (
            f'Unexpected error for mode={mode}, config_name={config_name}: {result}'
        )


# Property: Start run correctly includes or omits networking params in API call
class TestStartRunNetworkingParams:
    """Start run correctly includes or omits networking params in API call.

    For any valid networking_mode/configuration_name pair that passes validation:
    - VPC mode with a configuration_name includes networkingMode and configurationName in API call
    - RESTRICTED or None mode omits both from API call

    **Validates: Requirements Start Run VPC Networking Support**
    """

    _base_params = {
        'workflow_id': 'wf-12345',
        'role_arn': 'arn:aws:iam::123456789012:role/test-role',
        'name': 'test-run',
        'output_uri': 's3://bucket/output/',
        'parameters': {'input': 's3://bucket/input.bam'},
    }

    @given(
        config_name=st.text(min_size=1, max_size=50, alphabet=st.characters(categories=('L', 'N')))
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_vpc_mode_includes_networking_params(self, config_name):
        """VPC mode with a configuration_name includes networkingMode and configurationName in API call."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.start_run.return_value = {
            'id': 'run-12345',
            'arn': 'arn:aws:omics:us-east-1:123456789012:run/run-12345',
            'status': 'PENDING',
        }

        with patch(MOCK_WE_PATH, return_value=mock_client):
            result = await start_run_wrapper.call(
                ctx=mock_ctx,
                **self._base_params,
                networking_mode='VPC',
                configuration_name=config_name,
            )

        assert 'error' not in result, f'Unexpected error: {result}'
        call_kwargs = mock_client.start_run.call_args.kwargs
        assert 'networkingMode' in call_kwargs, 'networkingMode should be in API call for VPC mode'
        assert call_kwargs['networkingMode'] == 'VPC'
        assert 'configurationName' in call_kwargs, (
            'configurationName should be in API call for VPC mode'
        )
        assert call_kwargs['configurationName'] == config_name

    @given(mode=st.sampled_from([None, 'RESTRICTED']))
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_restricted_or_none_mode_omits_networking_params(self, mode):
        """RESTRICTED or None mode omits networkingMode and configurationName from API call."""
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.start_run.return_value = {
            'id': 'run-12345',
            'arn': 'arn:aws:omics:us-east-1:123456789012:run/run-12345',
            'status': 'PENDING',
        }

        call_kwargs = {**self._base_params}
        if mode is not None:
            call_kwargs['networking_mode'] = mode

        with patch(MOCK_WE_PATH, return_value=mock_client):
            result = await start_run_wrapper.call(ctx=mock_ctx, **call_kwargs)

        assert 'error' not in result, f'Unexpected error: {result}'
        api_kwargs = mock_client.start_run.call_args.kwargs
        assert 'networkingMode' not in api_kwargs, (
            'networkingMode should NOT be in API call for RESTRICTED/None mode'
        )
        assert 'configurationName' not in api_kwargs, (
            'configurationName should NOT be in API call for RESTRICTED/None mode'
        )
