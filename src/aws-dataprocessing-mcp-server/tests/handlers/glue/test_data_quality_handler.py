import pytest
from awslabs.aws_dataprocessing_mcp_server.handlers.glue.data_quality_handler import GlueDataQualityHandler
from botocore.exceptions import ClientError
from unittest.mock import Mock, patch
from mcp.types import TextContent


@pytest.fixture
def mock_mcp():
    """Create a mock MCP server instance for testing."""
    mcp = Mock()
    mcp.tool = Mock(return_value=lambda x: x)
    return mcp


@pytest.fixture
def mock_context():
    """Create a mock context for testing."""
    context = Mock()
    context.request_id = 'test-request-id'
    return context


@pytest.fixture
def handler(mock_mcp):
    """Create a GlueDataQualityHandler instance with write access for testing."""
    with patch(
        'awslabs.aws_dataprocessing_mcp_server.handlers.glue.data_quality_handler.AwsHelper'
    ) as mock_aws_helper:
        mock_aws_helper.create_boto3_client.return_value = Mock()
        handler = GlueDataQualityHandler(mock_mcp, allow_write=True, allow_sensitive_data_access=True)
        return handler


@pytest.fixture
def no_write_handler(mock_mcp):
    """Create a GlueDataQualityHandler instance without write access for testing."""
    with patch(
        'awslabs.aws_dataprocessing_mcp_server.handlers.glue.data_quality_handler.AwsHelper'
    ) as mock_aws_helper:
        mock_aws_helper.create_boto3_client.return_value = Mock()
        handler = GlueDataQualityHandler(mock_mcp, allow_write=False)
        return handler


class TestGlueDataQualityHandler:
    """Test class for GlueDataQualityHandler functionality."""

    @pytest.mark.asyncio
    async def test_init(self, mock_mcp):
        """Test initialization of GlueDataQualityHandler."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.handlers.glue.data_quality_handler.AwsHelper'
        ) as mock_aws_helper:
            mock_aws_helper.create_boto3_client.return_value = Mock()

            handler = GlueDataQualityHandler(mock_mcp, allow_write=True, allow_sensitive_data_access=True)

            assert handler.mcp == mock_mcp
            assert handler.allow_write is True
            assert handler.allow_sensitive_data_access is True
            mock_aws_helper.create_boto3_client.assert_called_once_with('glue')

            assert mock_mcp.tool.call_count == 4

            call_args_list = mock_mcp.tool.call_args_list
            tool_names = [call_args[1]['name'] for call_args in call_args_list]

            assert 'manage_aws_glue_data_quality_rulesets' in tool_names
            assert 'manage_aws_glue_data_quality_evaluation_runs' in tool_names
            assert 'manage_aws_glue_data_quality_recommendation_runs' in tool_names
            assert 'manage_aws_glue_data_quality_metrics' in tool_names

    # Tests for manage_aws_glue_data_quality_rulesets
    @pytest.mark.asyncio
    async def test_create_ruleset_success(self, handler, mock_context):
        """Test successful creation of a data quality ruleset."""
        # Setup
        handler.glue_client.create_data_quality_ruleset.return_value = {}

        # Mock AwsHelper methods
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.handlers.glue.data_quality_handler.AwsHelper'
        ) as mock_aws_helper:
            mock_aws_helper.prepare_resource_tags.return_value = {
                'ManagedBy': 'DataprocessingMcpServer'
            }

            # Test
            result = await handler.manage_aws_glue_data_quality_rulesets(
                mock_context,
                operation='create-ruleset',
                ruleset_name='test-ruleset',
                database_name='test-db',
                table_name='test-table',
                ruleset_definition='Rules = [IsComplete "column1"]',
                description='Test ruleset',
                tags={'custom': 'tag'},
            )

            # Assertions
            assert result.isError is False
            assert 'test-ruleset' in result.ruleset_name
            assert result.status == 'CREATED'
            assert result.description == 'Test ruleset'
            assert result.target_table == 'test-db.test-table'
            handler.glue_client.create_data_quality_ruleset.assert_called_once()
            mock_aws_helper.prepare_resource_tags.assert_called_once_with('DataQualityRuleset', {'custom': 'tag'})

    @pytest.mark.asyncio
    async def test_create_ruleset_no_write_access(self, no_write_handler, mock_context):
        """Test that creating a ruleset fails when write access is disabled."""
        result = await no_write_handler.manage_aws_glue_data_quality_rulesets(
            mock_context,
            operation='create-ruleset',
            ruleset_name='test-ruleset',
            database_name='test-db',
            table_name='test-table',
            ruleset_definition='Rules = [IsComplete "column1"]',
        )

        assert isinstance(result, TextContent)
        assert 'Write access is required' in result.text

    @pytest.mark.asyncio
    async def test_get_ruleset_success(self, handler, mock_context):
        """Test successful retrieval of a data quality ruleset."""
        # Setup
        ruleset_details = {
            'Name': 'test-ruleset',
            'Description': 'Test ruleset',
            'Ruleset': 'Rules = [IsComplete "column1"]',
            'TargetTable': {'DatabaseName': 'test-db', 'TableName': 'test-table'},
            'CreatedOn': '2023-01-01T00:00:00Z',
            'LastModifiedOn': '2023-01-01T00:00:00Z',
        }
        handler.glue_client.get_data_quality_ruleset.return_value = ruleset_details

        # Test
        result = await handler.manage_aws_glue_data_quality_rulesets(
            mock_context, operation='get-ruleset', ruleset_name='test-ruleset'
        )

        # Assertions
        assert result.isError is False
        assert result.ruleset_name == 'test-ruleset'
        assert result.description == 'Test ruleset'
        assert result.ruleset_definition == 'Rules = [IsComplete "column1"]'
        assert result.target_table == 'test-db.test-table'
        assert result.status == 'RETRIEVED'
        handler.glue_client.get_data_quality_ruleset.assert_called_once_with(Name='test-ruleset')

    @pytest.mark.asyncio
    async def test_list_rulesets_success(self, handler, mock_context):
        """Test successful listing of data quality rulesets."""
        # Setup
        rulesets = [
            {
                'Name': 'test-ruleset-1',
                'Description': 'Test ruleset 1',
                'TargetTable': {'DatabaseName': 'test-db', 'TableName': 'test-table'},
                'CreatedOn': '2023-01-01T00:00:00Z',
                'LastModifiedOn': '2023-01-01T00:00:00Z',
            },
            {
                'Name': 'test-ruleset-2',
                'Description': 'Test ruleset 2',
                'TargetTable': {'DatabaseName': 'test-db', 'TableName': 'test-table'},
                'CreatedOn': '2023-01-01T00:00:00Z',
                'LastModifiedOn': '2023-01-01T00:00:00Z',
            },
        ]
        handler.glue_client.list_data_quality_rulesets.return_value = {'Rulesets': rulesets}

        # Test
        result = await handler.manage_aws_glue_data_quality_rulesets(
            mock_context, operation='list-rulesets'
        )

        # Assertions
        assert result.isError is False
        assert result.ruleset_count == 2
        assert len(result.rulesets) == 2
        assert result.rulesets[0].name == 'test-ruleset-1'
        assert result.rulesets[1].name == 'test-ruleset-2'
        assert result.status == 'LISTED'
        handler.glue_client.list_data_quality_rulesets.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_ruleset_success(self, handler, mock_context):
        """Test successful update of a data quality ruleset."""
        # Setup
        handler.glue_client.update_data_quality_ruleset.return_value = {}

        # Test
        result = await handler.manage_aws_glue_data_quality_rulesets(
            mock_context,
            operation='update-ruleset',
            ruleset_name='test-ruleset',
            ruleset_definition='Rules = [IsComplete "column1", IsUnique "column2"]',
            description='Updated test ruleset',
        )

        # Assertions
        assert result.isError is False
        assert result.ruleset_name == 'test-ruleset'
        assert result.description == 'Updated test ruleset'
        assert result.status == 'UPDATED'
        handler.glue_client.update_data_quality_ruleset.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_ruleset_no_write_access(self, no_write_handler, mock_context):
        """Test that updating a ruleset fails when write access is disabled."""
        result = await no_write_handler.manage_aws_glue_data_quality_rulesets(
            mock_context,
            operation='update-ruleset',
            ruleset_name='test-ruleset',
            ruleset_definition='Rules = [IsComplete "column1"]',
        )

        assert isinstance(result, TextContent)
        assert 'Write access is required' in result.text

    @pytest.mark.asyncio
    async def test_delete_ruleset_success(self, handler, mock_context):
        """Test successful deletion of a data quality ruleset."""
        # Setup
        handler.glue_client.get_data_quality_ruleset.return_value = {'Name': 'test-ruleset'}
        handler.glue_client.delete_data_quality_ruleset.return_value = {}

        # Test
        result = await handler.manage_aws_glue_data_quality_rulesets(
            mock_context, operation='delete-ruleset', ruleset_name='test-ruleset'
        )

        # Assertions
        assert result.isError is False
        assert result.ruleset_name == 'test-ruleset'
        assert result.status == 'DELETED'
        handler.glue_client.delete_data_quality_ruleset.assert_called_once_with(Name='test-ruleset')

    @pytest.mark.asyncio
    async def test_delete_ruleset_not_found(self, handler, mock_context):
        """Test deletion of a non-existent ruleset."""
        # Setup
        error_response = {'Error': {'Code': 'EntityNotFoundException', 'Message': 'Ruleset not found'}}
        handler.glue_client.get_data_quality_ruleset.side_effect = ClientError(error_response, 'GetDataQualityRuleset')

        # Test
        result = await handler.manage_aws_glue_data_quality_rulesets(
            mock_context, operation='delete-ruleset', ruleset_name='test-ruleset'
        )

        # Assertions
        assert isinstance(result, TextContent)
        assert 'Ruleset test-ruleset not found' in result.text

    @pytest.mark.asyncio
    async def test_delete_ruleset_no_write_access(self, no_write_handler, mock_context):
        """Test that deleting a ruleset fails when write access is disabled."""
        result = await no_write_handler.manage_aws_glue_data_quality_rulesets(
            mock_context, operation='delete-ruleset', ruleset_name='test-ruleset'
        )

        assert isinstance(result, TextContent)
        assert 'Write access is required' in result.text

    @pytest.mark.asyncio
    async def test_append_ruleset_success(self, handler, mock_context):
        """Test successful appending to a data quality ruleset."""
        # Setup
        handler.glue_client.get_data_quality_ruleset.return_value = {
            'Ruleset': 'Rules = [\n    IsComplete "column1"\n]'
        }
        handler.glue_client.update_data_quality_ruleset.return_value = {}

        # Test
        result = await handler.manage_aws_glue_data_quality_rulesets(
            mock_context,
            operation='append-ruleset',
            ruleset_name='test-ruleset',
            ruleset_definition='IsUnique "column2"',
        )

        # Assertions
        assert result.isError is False
        assert result.ruleset_name == 'test-ruleset'
        assert result.status == 'APPENDED'
        assert 'IsUnique "column2"' in result.ruleset_definition
        handler.glue_client.update_data_quality_ruleset.assert_called_once()

    @pytest.mark.asyncio
    async def test_append_ruleset_no_write_access(self, no_write_handler, mock_context):
        """Test that appending to a ruleset fails when write access is disabled."""
        result = await no_write_handler.manage_aws_glue_data_quality_rulesets(
            mock_context,
            operation='append-ruleset',
            ruleset_name='test-ruleset',
            ruleset_definition='IsUnique "column2"',
        )

        assert isinstance(result, TextContent)
        assert 'Write access is required' in result.text

    @pytest.mark.asyncio
    async def test_get_table_rulesets_success(self, handler, mock_context):
        """Test successful retrieval of rulesets for a table."""
        # Setup
        rulesets = [
            {
                'Name': 'test-ruleset-1',
                'Description': 'Test ruleset 1',
                'CreatedOn': '2023-01-01T00:00:00Z',
                'LastModifiedOn': '2023-01-01T00:00:00Z',
            }
        ]
        handler.glue_client.list_data_quality_rulesets.return_value = {'Rulesets': rulesets}
        handler.glue_client.get_data_quality_ruleset.return_value = {
            'Ruleset': 'Rules = [IsComplete "column1"]'
        }

        # Test
        result = await handler.manage_aws_glue_data_quality_rulesets(
            mock_context,
            operation='get-table-rulesets',
            database_name='test-db',
            table_name='test-table',
        )

        # Assertions
        assert result.isError is False
        assert result.ruleset_count == 1
        assert len(result.rulesets) == 1
        assert result.rulesets[0].name == 'test-ruleset-1'
        handler.glue_client.list_data_quality_rulesets.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_operation(self, handler, mock_context):
        """Test handling of invalid operation."""
        result = await handler.manage_aws_glue_data_quality_rulesets(
            mock_context, operation='invalid-operation'
        )

        assert isinstance(result, TextContent)
        assert 'Unsupported operation: invalid-operation' in result.text

    @pytest.mark.asyncio
    async def test_error_handling(self, handler, mock_context):
        """Test error handling when Glue API calls raise exceptions."""
        # Setup
        handler.glue_client.get_data_quality_ruleset.side_effect = Exception('Test error')

        # Test
        result = await handler.manage_aws_glue_data_quality_rulesets(
            mock_context, operation='get-ruleset', ruleset_name='test-ruleset'
        )

        # Assertions
        assert isinstance(result, TextContent)
        assert 'Error managing data quality rulesets: Test error' in result.text

    # Tests for manage_aws_glue_data_quality_evaluation_runs
    @pytest.mark.asyncio
    async def test_start_evaluation_run_success(self, handler, mock_context):
        """Test successful start of a data quality evaluation run."""
        # Setup
        handler.glue_client.start_data_quality_ruleset_evaluation_run.return_value = {
            'RunId': 'test-run-id'
        }

        # Test
        result = await handler.manage_aws_glue_data_quality_evaluation_runs(
            mock_context,
            operation='start-evaluation-run',
            database_name='test-db',
            table_name='test-table',
            ruleset_names=['test-ruleset'],
            role_arn='arn:aws:iam::123456789012:role/GlueRole',
            number_of_workers=5,
            timeout=2880,
        )

        # Assertions
        assert result.isError is False
        assert result.run_id == 'test-run-id'
        assert result.status == 'STARTED'
        assert result.database_name == 'test-db'
        assert result.table_name == 'test-table'
        handler.glue_client.start_data_quality_ruleset_evaluation_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_evaluation_run_no_write_access(self, no_write_handler, mock_context):
        """Test that starting an evaluation run fails when write access is disabled."""
        result = await no_write_handler.manage_aws_glue_data_quality_evaluation_runs(
            mock_context,
            operation='start-evaluation-run',
            database_name='test-db',
            table_name='test-table',
            ruleset_names=['test-ruleset'],
            role_arn='arn:aws:iam::123456789012:role/GlueRole',
        )

        assert isinstance(result, TextContent)
        assert 'Write access is required' in result.text

    @pytest.mark.asyncio
    async def test_get_evaluation_run_success(self, handler, mock_context):
        """Test successful retrieval of a data quality evaluation run."""
        # Setup
        run_details = {
            'RunId': 'test-run-id',
            'Status': 'SUCCEEDED',
            'DataSource': {'GlueTable': {'DatabaseName': 'test-db', 'TableName': 'test-table'}},
            'RoleArn': 'arn:aws:iam::123456789012:role/GlueRole',
            'NumberOfWorkers': 5,
            'Timeout': 2880,
            'StartedOn': '2023-01-01T00:00:00Z',
            'CompletedOn': '2023-01-01T01:00:00Z',
            'ExecutionTime': 3600,
            'ResultIds': ['result-1', 'result-2'],
        }
        handler.glue_client.get_data_quality_ruleset_evaluation_run.return_value = run_details

        # Test
        result = await handler.manage_aws_glue_data_quality_evaluation_runs(
            mock_context, operation='get-evaluation-run', run_id='test-run-id'
        )

        # Assertions
        assert result.isError is False
        assert result.run_id == 'test-run-id'
        assert result.status == 'SUCCEEDED'
        assert result.database_name == 'test-db'
        assert result.table_name == 'test-table'
        assert result.execution_time == 3600
        handler.glue_client.get_data_quality_ruleset_evaluation_run.assert_called_once_with(RunId='test-run-id')

    @pytest.mark.asyncio
    async def test_list_evaluation_runs_success(self, handler, mock_context):
        """Test successful listing of data quality evaluation runs."""
        # Setup
        runs = [
            {
                'RunId': 'test-run-1',
                'Status': 'SUCCEEDED',
                'StartedOn': '2023-01-01T00:00:00Z',
                'CompletedOn': '2023-01-01T01:00:00Z',
                'ExecutionTime': 3600,
            },
            {
                'RunId': 'test-run-2',
                'Status': 'RUNNING',
                'StartedOn': '2023-01-01T02:00:00Z',
                'ExecutionTime': 0,
            },
        ]
        handler.glue_client.list_data_quality_ruleset_evaluation_runs.return_value = {'Runs': runs}

        # Test
        result = await handler.manage_aws_glue_data_quality_evaluation_runs(
            mock_context,
            operation='list-evaluation-runs',
            database_name='test-db',
            table_name='test-table',
        )

        # Assertions
        assert result.isError is False
        assert result.run_count == 2
        assert len(result.evaluation_runs) == 2
        assert result.evaluation_runs[0].run_id == 'test-run-1'
        assert result.evaluation_runs[1].run_id == 'test-run-2'
        handler.glue_client.list_data_quality_ruleset_evaluation_runs.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_evaluation_run_success(self, handler, mock_context):
        """Test successful cancellation of a data quality evaluation run."""
        # Setup
        handler.glue_client.cancel_data_quality_ruleset_evaluation_run.return_value = {}

        # Test
        result = await handler.manage_aws_glue_data_quality_evaluation_runs(
            mock_context, operation='cancel-evaluation-run', run_id='test-run-id'
        )

        # Assertions
        assert result.isError is False
        assert result.run_id == 'test-run-id'
        assert result.status == 'CANCELLED'
        handler.glue_client.cancel_data_quality_ruleset_evaluation_run.assert_called_once_with(RunId='test-run-id')

    @pytest.mark.asyncio
    async def test_cancel_evaluation_run_no_write_access(self, no_write_handler, mock_context):
        """Test that cancelling an evaluation run fails when write access is disabled."""
        result = await no_write_handler.manage_aws_glue_data_quality_evaluation_runs(
            mock_context, operation='cancel-evaluation-run', run_id='test-run-id'
        )

        assert isinstance(result, TextContent)
        assert 'Write access is required' in result.text

    # Tests for manage_aws_glue_data_quality_recommendation_runs
    @pytest.mark.asyncio
    async def test_start_recommendation_run_success(self, handler, mock_context):
        """Test successful start of a data quality recommendation run."""
        # Setup
        handler.glue_client.start_data_quality_rule_recommendation_run.return_value = {
            'RunId': 'test-rec-run-id'
        }

        # Test
        result = await handler.manage_aws_glue_data_quality_recommendation_runs(
            mock_context,
            operation='start-recommendation-run',
            database_name='test-db',
            table_name='test-table',
            role_arn='arn:aws:iam::123456789012:role/GlueRole',
            created_ruleset_name='recommended-ruleset',
            number_of_workers=5,
            timeout=2880,
        )

        # Assertions
        assert result.isError is False
        assert result.run_id == 'test-rec-run-id'
        assert result.status == 'STARTED'
        assert result.database_name == 'test-db'
        assert result.table_name == 'test-table'
        handler.glue_client.start_data_quality_rule_recommendation_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_recommendation_run_no_write_access(self, no_write_handler, mock_context):
        """Test that starting a recommendation run fails when write access is disabled."""
        result = await no_write_handler.manage_aws_glue_data_quality_recommendation_runs(
            mock_context,
            operation='start-recommendation-run',
            database_name='test-db',
            table_name='test-table',
            role_arn='arn:aws:iam::123456789012:role/GlueRole',
        )

        assert isinstance(result, TextContent)
        assert 'Write access is required' in result.text

    @pytest.mark.asyncio
    async def test_get_recommendation_run_success(self, handler, mock_context):
        """Test successful retrieval of a data quality recommendation run."""
        # Setup
        run_details = {
            'RunId': 'test-rec-run-id',
            'Status': 'SUCCEEDED',
            'DataSource': {'GlueTable': {'DatabaseName': 'test-db', 'TableName': 'test-table'}},
            'RoleArn': 'arn:aws:iam::123456789012:role/GlueRole',
            'NumberOfWorkers': 5,
            'Timeout': 2880,
            'StartedOn': '2023-01-01T00:00:00Z',
            'CompletedOn': '2023-01-01T01:00:00Z',
            'ExecutionTime': 3600,
            'CreatedRulesetName': 'recommended-ruleset',
            'RecommendedRuleset': 'Rules = [IsComplete "column1", IsUnique "column2"]',
        }
        handler.glue_client.get_data_quality_rule_recommendation_run.return_value = run_details

        # Test
        result = await handler.manage_aws_glue_data_quality_recommendation_runs(
            mock_context, operation='get-recommendation-run', run_id='test-rec-run-id'
        )

        # Assertions
        assert result.isError is False
        assert result.run_id == 'test-rec-run-id'
        assert result.status == 'SUCCEEDED'
        assert result.database_name == 'test-db'
        assert result.table_name == 'test-table'
        assert result.created_ruleset_name == 'recommended-ruleset'
        assert 'IsComplete "column1"' in result.recommended_ruleset
        handler.glue_client.get_data_quality_rule_recommendation_run.assert_called_once_with(RunId='test-rec-run-id')

    @pytest.mark.asyncio
    async def test_cancel_recommendation_run_success(self, handler, mock_context):
        """Test successful cancellation of a data quality recommendation run."""
        # Setup
        handler.glue_client.cancel_data_quality_rule_recommendation_run.return_value = {}

        # Test
        result = await handler.manage_aws_glue_data_quality_recommendation_runs(
            mock_context, operation='cancel-recommendation-run', run_id='test-rec-run-id'
        )

        # Assertions
        assert result.isError is False
        assert result.run_id == 'test-rec-run-id'
        assert result.status == 'CANCELLED'
        handler.glue_client.cancel_data_quality_rule_recommendation_run.assert_called_once_with(RunId='test-rec-run-id')

    @pytest.mark.asyncio
    async def test_cancel_recommendation_run_no_write_access(self, no_write_handler, mock_context):
        """Test that cancelling a recommendation run fails when write access is disabled."""
        result = await no_write_handler.manage_aws_glue_data_quality_recommendation_runs(
            mock_context, operation='cancel-recommendation-run', run_id='test-rec-run-id'
        )

        assert isinstance(result, TextContent)
        assert 'Write access is required' in result.text

    # Tests for manage_aws_glue_data_quality_metrics
    @pytest.mark.asyncio
    async def test_get_data_quality_result_success(self, handler, mock_context):
        """Test successful retrieval of a data quality result."""
        # Setup
        result_details = {
            'ResultId': 'test-result-id',
            'RulesetName': 'test-ruleset',
            'EvaluationContext': 'test-context',
            'StartedOn': '2023-01-01T00:00:00Z',
            'CompletedOn': '2023-01-01T01:00:00Z',
            'JobName': 'test-job',
            'JobRunId': 'test-job-run-id',
            'RulesetEvaluationRunId': 'test-eval-run-id',
            'DataSource': {'GlueTable': {'DatabaseName': 'test-db', 'TableName': 'test-table'}},
            'RoleArn': 'arn:aws:iam::123456789012:role/GlueRole',
            'Score': 0.95,
            'RuleResults': [
                {
                    'Name': 'IsComplete_column1',
                    'Description': 'Check if column1 is complete',
                    'EvaluationMessage': 'Rule passed',
                    'Result': 'PASS',
                }
            ],
        }
        handler.glue_client.get_data_quality_result.return_value = result_details

        # Test
        result = await handler.manage_aws_glue_data_quality_metrics(
            mock_context, operation='get-result', result_id='test-result-id'
        )

        # Assertions
        assert result.isError is False
        assert result.result_id == 'test-result-id'
        assert result.ruleset_name == 'test-ruleset'
        assert result.score == 0.95
        assert len(result.rule_results) == 1
        assert result.rule_results[0].name == 'IsComplete_column1'
        handler.glue_client.get_data_quality_result.assert_called_once_with(ResultId='test-result-id')

    @pytest.mark.asyncio
    async def test_list_data_quality_results_success(self, handler, mock_context):
        """Test successful listing of data quality results."""
        # Setup - Mock the evaluation runs list and individual run details
        runs = [
            {
                'RunId': 'test-run-1',
                'Status': 'SUCCEEDED',
            },
            {
                'RunId': 'test-run-2',
                'Status': 'SUCCEEDED',
            },
        ]
        handler.glue_client.list_data_quality_ruleset_evaluation_runs.return_value = {'Runs': runs}
        
        # Mock individual run details to return result IDs
        def mock_get_run_details(RunId):
            if RunId == 'test-run-1':
                return {'ResultIds': ['test-result-1', 'test-result-2']}
            elif RunId == 'test-run-2':
                return {'ResultIds': ['test-result-3']}
            return {'ResultIds': []}
        
        handler.glue_client.get_data_quality_ruleset_evaluation_run.side_effect = mock_get_run_details

        # Test
        result = await handler.manage_aws_glue_data_quality_metrics(
            mock_context,
            operation='list-results',
            database_name='test-db',
            table_name='test-table',
        )

        # Assertions
        assert result.isError is False
        assert result.result_count == 3
        assert len(result.result_ids) == 3
        assert 'test-result-1' in result.result_ids
        assert 'test-result-2' in result.result_ids
        assert 'test-result-3' in result.result_ids
        handler.glue_client.list_data_quality_ruleset_evaluation_runs.assert_called_once()

    @pytest.mark.asyncio
    async def test_metrics_invalid_operation(self, handler, mock_context):
        """Test handling of invalid operation for metrics."""
        result = await handler.manage_aws_glue_data_quality_metrics(
            mock_context, operation='invalid-operation'
        )

        assert isinstance(result, TextContent)
        assert 'Unsupported operation: invalid-operation' in result.text

    @pytest.mark.asyncio
    async def test_metrics_error_handling(self, handler, mock_context):
        """Test error handling for metrics operations."""
        # Setup
        handler.glue_client.get_data_quality_result.side_effect = Exception('Test error')

        # Test
        result = await handler.manage_aws_glue_data_quality_metrics(
            mock_context, operation='get-result', result_id='test-result-id'
        )

        # Assertions
        assert isinstance(result, TextContent)
        assert 'Error managing data quality metrics: Test error' in result.text