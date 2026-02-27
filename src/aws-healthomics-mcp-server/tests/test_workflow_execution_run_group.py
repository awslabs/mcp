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

"""Property-based tests for start_run and list_runs run_group_id handling."""

import pytest
from awslabs.aws_healthomics_mcp_server.tools.workflow_execution import list_runs, start_run
from hypothesis import given, settings
from hypothesis import strategies as st
from unittest.mock import AsyncMock, MagicMock, patch


# --- Hypothesis Strategies ---

run_group_id_strategy = st.text(
    min_size=1, max_size=18, alphabet=st.characters(categories=('Nd',))
)
optional_run_group_id_strategy = st.none() | run_group_id_strategy


# Feature: run-group-tools, Property: start_run conditionally includes run_group_id
class TestStartRunConditionallyIncludesRunGroupId:
    """start_run conditionally includes run_group_id.

    For any invocation of start_run, if run_group_id is provided (non-None),
    the API call should include runGroupId and the response should include runGroupId;
    if run_group_id is None, the API call and response should not contain runGroupId.

    Validates: run group association on start run, preserving existing behavior when omitted
    """

    @given(run_group_id=optional_run_group_id_strategy)
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_conditionally_includes_run_group_id(self, run_group_id):
        """start_run includes runGroupId in API call and response only when provided.

        Validates: run group association on start run, preserving existing behavior when omitted
        """
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.start_run.return_value = {
            'id': 'run-12345',
            'arn': 'arn:aws:omics:us-east-1:123456789012:run/run-12345',
            'status': 'PENDING',
        }

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
            return_value=mock_client,
        ):
            result = await start_run(
                ctx=mock_ctx,
                workflow_id='wf-123',
                role_arn='arn:aws:iam::123456789012:role/OmicsRole',
                name='test-run',
                output_uri='s3://bucket/output/',
                parameters={'input': 's3://bucket/input.bam'},
                storage_type='DYNAMIC',
                storage_capacity=None,
                workflow_version_name=None,
                cache_id=None,
                cache_behavior=None,
                run_group_id=run_group_id,
            )

        mock_client.start_run.assert_called_once()
        actual_params = mock_client.start_run.call_args[1]

        if run_group_id is not None:
            # runGroupId included in API call when provided
            assert 'runGroupId' in actual_params
            assert actual_params['runGroupId'] == run_group_id
            # runGroupId included in response when provided
            assert result['runGroupId'] == run_group_id
        else:
            # runGroupId omitted from API call when not provided
            assert 'runGroupId' not in actual_params
            # Response should have runGroupId as None
            assert result.get('runGroupId') is None


# Feature: run-group-tools, Property: list_runs conditionally includes run_group_id filter
class TestListRunsConditionallyIncludesRunGroupIdFilter:
    """list_runs conditionally includes run_group_id filter.

    For any invocation of list_runs, if run_group_id is provided (non-None),
    the API call should include runGroupId; if run_group_id is None, the API
    call should not contain runGroupId.

    Validates: run group filter on list runs, preserving existing behavior when omitted
    """

    @given(run_group_id=optional_run_group_id_strategy)
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_conditionally_includes_run_group_id_filter(self, run_group_id):
        """list_runs includes runGroupId in API call only when provided.

        Validates: run group filter on list runs, preserving existing behavior when omitted
        """
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_runs.return_value = {
            'items': [],
        }

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
            return_value=mock_client,
        ):
            result = await list_runs(
                ctx=mock_ctx,
                max_results=10,
                next_token=None,
                status=None,
                created_after=None,
                created_before=None,
                run_group_id=run_group_id,
            )

        mock_client.list_runs.assert_called_once()
        actual_params = mock_client.list_runs.call_args[1]

        if run_group_id is not None:
            # runGroupId included in API call when provided
            assert 'runGroupId' in actual_params
            assert actual_params['runGroupId'] == run_group_id
        else:
            # runGroupId omitted from API call when not provided
            assert 'runGroupId' not in actual_params

        # Verify we got a valid response regardless
        assert 'runs' in result


# --- Unit Tests for start_run and list_runs run_group_id handling ---


class TestStartRunWithRunGroupIdUnit:
    """Unit tests for start_run run_group_id parameter."""

    @pytest.mark.asyncio
    async def test_start_run_with_run_group_id(self):
        """Verify runGroupId is included in API params and response when provided.

        Validates: run group association included in API call and response
        """
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.start_run.return_value = {
            'id': 'run-abc',
            'arn': 'arn:aws:omics:us-east-1:123456789012:run/run-abc',
            'status': 'PENDING',
        }

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
            return_value=mock_client,
        ):
            result = await start_run(
                ctx=mock_ctx,
                workflow_id='wf-100',
                role_arn='arn:aws:iam::123456789012:role/OmicsRole',
                name='unit-test-run',
                output_uri='s3://bucket/output/',
                parameters={'input': 's3://bucket/data.bam'},
                storage_type='DYNAMIC',
                storage_capacity=None,
                workflow_version_name=None,
                cache_id=None,
                cache_behavior=None,
                run_group_id='12345',
            )

        actual_params = mock_client.start_run.call_args[1]
        assert 'runGroupId' in actual_params
        assert actual_params['runGroupId'] == '12345'
        assert result['runGroupId'] == '12345'

    @pytest.mark.asyncio
    async def test_start_run_without_run_group_id(self):
        """Verify runGroupId is NOT in API params and response is None when not provided.

        Validates: existing behavior preserved when run group omitted
        """
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.start_run.return_value = {
            'id': 'run-def',
            'arn': 'arn:aws:omics:us-east-1:123456789012:run/run-def',
            'status': 'PENDING',
        }

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
            return_value=mock_client,
        ):
            result = await start_run(
                ctx=mock_ctx,
                workflow_id='wf-200',
                role_arn='arn:aws:iam::123456789012:role/OmicsRole',
                name='unit-test-run-no-rg',
                output_uri='s3://bucket/output/',
                parameters={'input': 's3://bucket/data.bam'},
                storage_type='DYNAMIC',
                storage_capacity=None,
                workflow_version_name=None,
                cache_id=None,
                cache_behavior=None,
                run_group_id=None,
            )

        actual_params = mock_client.start_run.call_args[1]
        assert 'runGroupId' not in actual_params
        assert result.get('runGroupId') is None


class TestListRunsWithRunGroupIdUnit:
    """Unit tests for list_runs run_group_id parameter."""

    @pytest.mark.asyncio
    async def test_list_runs_with_run_group_id_filter(self):
        """Verify runGroupId is included in API params when provided.

        Validates: run group filter included in list runs API call
        """
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_runs.return_value = {
            'items': [
                {
                    'id': 'run-1',
                    'arn': 'arn:aws:omics:us-east-1:123456789012:run/run-1',
                    'name': 'filtered-run',
                    'status': 'COMPLETED',
                    'workflowId': 'wf-1',
                    'workflowType': 'PRIVATE',
                    'creationTime': None,
                }
            ],
        }

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
            return_value=mock_client,
        ):
            result = await list_runs(
                ctx=mock_ctx,
                max_results=10,
                next_token=None,
                status=None,
                created_after=None,
                created_before=None,
                run_group_id='99999',
            )

        actual_params = mock_client.list_runs.call_args[1]
        assert 'runGroupId' in actual_params
        assert actual_params['runGroupId'] == '99999'
        assert 'runs' in result

    @pytest.mark.asyncio
    async def test_list_runs_without_run_group_id_filter(self):
        """Verify runGroupId is NOT in API params when not provided.

        Validates: existing list runs behavior preserved when run group filter omitted
        """
        mock_ctx = AsyncMock()
        mock_client = MagicMock()
        mock_client.list_runs.return_value = {
            'items': [],
        }

        with patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_execution.get_omics_client',
            return_value=mock_client,
        ):
            result = await list_runs(
                ctx=mock_ctx,
                max_results=10,
                next_token=None,
                status=None,
                created_after=None,
                created_before=None,
                run_group_id=None,
            )

        actual_params = mock_client.list_runs.call_args[1]
        assert 'runGroupId' not in actual_params
        assert 'runs' in result
