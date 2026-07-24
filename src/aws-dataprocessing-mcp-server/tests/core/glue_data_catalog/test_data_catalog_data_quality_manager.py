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

"""Tests for the DataCatalogDataQualityManager class."""

import json
import pytest
from awslabs.aws_dataprocessing_mcp_server.core.glue_data_catalog.data_catalog_data_quality_manager import (
    DataCatalogDataQualityManager,
)
from botocore.exceptions import ClientError
from datetime import datetime
from mcp.types import CallToolResult
from unittest.mock import MagicMock, patch


class TestDataCatalogDataQualityManager:
    """Tests for the DataCatalogDataQualityManager class."""

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock Context."""
        mock = MagicMock()
        mock.request_id = 'test-request-id'
        return mock

    @pytest.fixture
    def mock_glue_client(self):
        """Create a mock Glue client."""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def manager(self, mock_glue_client):
        """Create a DataCatalogDataQualityManager instance with a mocked Glue client."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=mock_glue_client,
        ):
            manager = DataCatalogDataQualityManager(allow_write=True)
            return manager

    @pytest.mark.asyncio
    async def test_list_rulesets_success(self, manager, mock_ctx, mock_glue_client):
        """Test that list_rulesets returns a successful response with rulesets."""
        created_on = datetime(2023, 1, 1, 0, 0, 0)
        mock_glue_client.list_data_quality_rulesets.return_value = {
            'Rulesets': [
                {
                    'Name': 'my-ruleset',
                    'Description': 'test ruleset',
                    'TargetTable': {'DatabaseName': 'test-db', 'TableName': 'test-table'},
                    'CreatedOn': created_on,
                    'RuleCount': 3,
                }
            ],
            'NextToken': 'next-page',
        }

        result = await manager.list_rulesets(
            mock_ctx, database_name='test-db', table_name='test-table'
        )

        mock_glue_client.list_data_quality_rulesets.assert_called_once_with(
            TargetTable={'DatabaseName': 'test-db', 'TableName': 'test-table'}
        )
        assert isinstance(result, CallToolResult)
        assert result.isError is False
        data = json.loads(result.content[1].text)
        assert data['count'] == 1
        assert data['rulesets'][0]['name'] == 'my-ruleset'
        assert data['next_token'] == 'next-page'

    @pytest.mark.asyncio
    async def test_list_rulesets_empty(self, manager, mock_ctx, mock_glue_client):
        """Test that list_rulesets handles a table with no rulesets."""
        mock_glue_client.list_data_quality_rulesets.return_value = {'Rulesets': []}

        result = await manager.list_rulesets(mock_ctx)

        mock_glue_client.list_data_quality_rulesets.assert_called_once_with()
        assert result.isError is False
        data = json.loads(result.content[1].text)
        assert data['count'] == 0

    @pytest.mark.asyncio
    async def test_list_rulesets_error(self, manager, mock_ctx, mock_glue_client):
        """Test that list_rulesets returns an error when the Glue API call fails."""
        mock_glue_client.list_data_quality_rulesets.side_effect = ClientError(
            {'Error': {'Code': 'InternalServiceException', 'Message': 'boom'}},
            'ListDataQualityRulesets',
        )

        result = await manager.list_rulesets(mock_ctx)

        assert result.isError is True
        assert 'Failed to list data quality rulesets' in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_ruleset_success(self, manager, mock_ctx, mock_glue_client):
        """Test that get_ruleset returns a successful response with the ruleset definition."""
        mock_glue_client.get_data_quality_ruleset.return_value = {
            'Name': 'my-ruleset',
            'Description': 'test ruleset',
            'Ruleset': 'Rules = [ColumnCount = 10]',
            'TargetTable': {'DatabaseName': 'test-db', 'TableName': 'test-table'},
        }

        result = await manager.get_ruleset(mock_ctx, name='my-ruleset')

        mock_glue_client.get_data_quality_ruleset.assert_called_once_with(Name='my-ruleset')
        assert result.isError is False
        data = json.loads(result.content[1].text)
        assert data['ruleset'] == 'Rules = [ColumnCount = 10]'

    @pytest.mark.asyncio
    async def test_get_ruleset_not_found(self, manager, mock_ctx, mock_glue_client):
        """Test that get_ruleset returns an error for a non-existent ruleset."""
        mock_glue_client.get_data_quality_ruleset.side_effect = ClientError(
            {'Error': {'Code': 'EntityNotFoundException', 'Message': 'Not found'}},
            'GetDataQualityRuleset',
        )

        result = await manager.get_ruleset(mock_ctx, name='missing-ruleset')

        assert result.isError is True
        assert 'Failed to get data quality ruleset' in result.content[0].text

    @pytest.mark.asyncio
    async def test_create_ruleset_success(self, manager, mock_ctx, mock_glue_client):
        """Test that create_ruleset returns a successful response when the Glue API call succeeds."""
        result = await manager.create_ruleset(
            mock_ctx,
            name='my-ruleset',
            ruleset='Rules = [ColumnCount = 10]',
            database_name='test-db',
            table_name='test-table',
        )

        mock_glue_client.create_data_quality_ruleset.assert_called_once_with(
            Name='my-ruleset',
            Ruleset='Rules = [ColumnCount = 10]',
            TargetTable={'DatabaseName': 'test-db', 'TableName': 'test-table'},
        )
        assert result.isError is False
        assert 'my-ruleset' in result.content[0].text

    @pytest.mark.asyncio
    async def test_delete_ruleset_success(self, manager, mock_ctx, mock_glue_client):
        """Test that delete_ruleset returns a successful response when the Glue API call succeeds."""
        result = await manager.delete_ruleset(mock_ctx, name='my-ruleset')

        mock_glue_client.delete_data_quality_ruleset.assert_called_once_with(Name='my-ruleset')
        assert result.isError is False

    @pytest.mark.asyncio
    async def test_start_ruleset_evaluation_run_success(self, manager, mock_ctx, mock_glue_client):
        """Test that start_ruleset_evaluation_run returns the started run ID."""
        mock_glue_client.start_data_quality_ruleset_evaluation_run.return_value = {
            'RunId': 'dqrun-123'
        }

        result = await manager.start_ruleset_evaluation_run(
            mock_ctx,
            database_name='test-db',
            table_name='test-table',
            ruleset_names=['my-ruleset'],
            role='arn:aws:iam::123456789012:role/GlueDataQualityRole',
        )

        mock_glue_client.start_data_quality_ruleset_evaluation_run.assert_called_once_with(
            DataSource={'GlueTable': {'DatabaseName': 'test-db', 'TableName': 'test-table'}},
            Role='arn:aws:iam::123456789012:role/GlueDataQualityRole',
            RulesetNames=['my-ruleset'],
        )
        assert result.isError is False
        data = json.loads(result.content[1].text)
        assert data['run_id'] == 'dqrun-123'

    @pytest.mark.asyncio
    async def test_get_ruleset_evaluation_run_success(self, manager, mock_ctx, mock_glue_client):
        """Test that get_ruleset_evaluation_run returns the run's status and result IDs."""
        mock_glue_client.get_data_quality_ruleset_evaluation_run.return_value = {
            'Status': 'SUCCEEDED',
            'RulesetNames': ['my-ruleset'],
            'ResultIds': ['dqresult-1'],
        }

        result = await manager.get_ruleset_evaluation_run(mock_ctx, run_id='dqrun-123')

        mock_glue_client.get_data_quality_ruleset_evaluation_run.assert_called_once_with(
            RunId='dqrun-123'
        )
        assert result.isError is False
        data = json.loads(result.content[1].text)
        assert data['status'] == 'SUCCEEDED'
        assert data['result_ids'] == ['dqresult-1']

    @pytest.mark.asyncio
    async def test_get_ruleset_evaluation_run_error(self, manager, mock_ctx, mock_glue_client):
        """Test that get_ruleset_evaluation_run returns an error for a non-existent run."""
        mock_glue_client.get_data_quality_ruleset_evaluation_run.side_effect = ClientError(
            {'Error': {'Code': 'EntityNotFoundException', 'Message': 'Not found'}},
            'GetDataQualityRulesetEvaluationRun',
        )

        result = await manager.get_ruleset_evaluation_run(mock_ctx, run_id='missing-run')

        assert result.isError is True
        assert 'Failed to get data quality evaluation run' in result.content[0].text

    @pytest.mark.asyncio
    async def test_list_ruleset_evaluation_runs_empty(self, manager, mock_ctx, mock_glue_client):
        """Test that list_ruleset_evaluation_runs handles a table with no evaluation runs."""
        mock_glue_client.list_data_quality_ruleset_evaluation_runs.return_value = {'Runs': []}

        result = await manager.list_ruleset_evaluation_runs(
            mock_ctx, database_name='test-db', table_name='test-table'
        )

        assert result.isError is False
        data = json.loads(result.content[1].text)
        assert data['count'] == 0

    @pytest.mark.asyncio
    async def test_get_data_quality_result_success(self, manager, mock_ctx, mock_glue_client):
        """Test that get_data_quality_result returns the result's score and rule results."""
        mock_glue_client.get_data_quality_result.return_value = {
            'ResultId': 'dqresult-1',
            'Score': 0.95,
            'RuleResults': [{'Name': 'rule1', 'Result': 'PASS'}],
        }

        result = await manager.get_data_quality_result(mock_ctx, result_id='dqresult-1')

        mock_glue_client.get_data_quality_result.assert_called_once_with(ResultId='dqresult-1')
        assert result.isError is False
        data = json.loads(result.content[1].text)
        assert data['result']['result_id'] == 'dqresult-1'
        assert data['result']['score'] == 0.95

    @pytest.mark.asyncio
    async def test_get_data_quality_result_not_found(self, manager, mock_ctx, mock_glue_client):
        """Test that get_data_quality_result returns an error for a non-existent result."""
        mock_glue_client.get_data_quality_result.side_effect = ClientError(
            {'Error': {'Code': 'EntityNotFoundException', 'Message': 'Not found'}},
            'GetDataQualityResult',
        )

        result = await manager.get_data_quality_result(mock_ctx, result_id='missing-result')

        assert result.isError is True
        assert 'Failed to get data quality result' in result.content[0].text

    @pytest.mark.asyncio
    async def test_list_data_quality_results_empty(self, manager, mock_ctx, mock_glue_client):
        """Test that list_data_quality_results handles no results gracefully."""
        mock_glue_client.list_data_quality_results.return_value = {'Results': []}

        result = await manager.list_data_quality_results(mock_ctx)

        assert result.isError is False
        data = json.loads(result.content[1].text)
        assert data['count'] == 0

    @pytest.mark.asyncio
    async def test_batch_get_data_quality_result_success(
        self, manager, mock_ctx, mock_glue_client
    ):
        """Test that batch_get_data_quality_result returns found and not-found results."""
        mock_glue_client.batch_get_data_quality_result.return_value = {
            'Results': [{'ResultId': 'dqresult-1', 'Score': 0.9, 'RuleResults': []}],
            'ResultsNotFound': ['dqresult-2'],
        }

        result = await manager.batch_get_data_quality_result(
            mock_ctx, result_ids=['dqresult-1', 'dqresult-2']
        )

        mock_glue_client.batch_get_data_quality_result.assert_called_once_with(
            ResultIds=['dqresult-1', 'dqresult-2']
        )
        assert result.isError is False
        data = json.loads(result.content[1].text)
        assert len(data['results']) == 1
        assert data['results_not_found'] == ['dqresult-2']

    @pytest.mark.asyncio
    async def test_batch_get_data_quality_result_error(self, manager, mock_ctx, mock_glue_client):
        """Test that batch_get_data_quality_result returns an error when the Glue API call fails."""
        mock_glue_client.batch_get_data_quality_result.side_effect = ClientError(
            {'Error': {'Code': 'InternalServiceException', 'Message': 'boom'}},
            'BatchGetDataQualityResult',
        )

        result = await manager.batch_get_data_quality_result(mock_ctx, result_ids=['dqresult-1'])

        assert result.isError is True
        assert 'Failed to batch get data quality results' in result.content[0].text
