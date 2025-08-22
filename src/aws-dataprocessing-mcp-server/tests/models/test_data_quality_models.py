import pytest
from awslabs.aws_dataprocessing_mcp_server.models.glue_models import (
    DataQualityRulesetResponse,
    DataQualityEvaluationRunResponse,
    DataQualityRecommendationRunResponse,
    DataQualityMetricsResponse,
    RulesetSummary,
    EvaluationRunSummary,
    RecommendationRunSummary,
    DataQualityResult,
)

from pydantic import ValidationError


class TestDataQualityModels:
    """Test class for Data Quality model functionality."""

    def test_ruleset_summary_creation(self):
        """Test creation of RulesetSummary model."""
        ruleset = RulesetSummary(
            name='test-ruleset',
            description='Test ruleset description',
            target_table='test-db.test-table',
            created_on='2023-01-01T00:00:00Z',
            last_modified_on='2023-01-01T00:00:00Z',
            ruleset_definition='Rules = [IsComplete "column1"]',
            rule_count=1,
        )

        assert ruleset.name == 'test-ruleset'
        assert ruleset.description == 'Test ruleset description'
        assert ruleset.target_table == 'test-db.test-table'
        assert ruleset.created_on == '2023-01-01T00:00:00Z'
        assert ruleset.last_modified_on == '2023-01-01T00:00:00Z'
        assert ruleset.ruleset_definition == 'Rules = [IsComplete "column1"]'
        assert ruleset.rule_count == 1
        assert ruleset.error == ''

    def test_ruleset_summary_defaults(self):
        """Test RulesetSummary with default values."""
        ruleset = RulesetSummary(name='test-ruleset')

        assert ruleset.name == 'test-ruleset'
        assert ruleset.description == ''
        assert ruleset.target_table == ''
        assert ruleset.created_on == ''
        assert ruleset.last_modified_on == ''
        assert ruleset.ruleset_definition == ''
        assert ruleset.rule_count == 0
        assert ruleset.error == ''

    def test_evaluation_run_summary_creation(self):
        """Test creation of EvaluationRunSummary model."""
        run = EvaluationRunSummary(
            run_id='test-run-id',
            status='SUCCEEDED',
            database_name='test-db',
            table_name='test-table',
            started_on='2023-01-01T00:00:00Z',
            completed_on='2023-01-01T01:00:00Z',
            execution_time=3600,
        )

        assert run.run_id == 'test-run-id'
        assert run.status == 'SUCCEEDED'
        assert run.database_name == 'test-db'
        assert run.table_name == 'test-table'
        assert run.started_on == '2023-01-01T00:00:00Z'
        assert run.completed_on == '2023-01-01T01:00:00Z'
        assert run.execution_time == 3600

    def test_evaluation_run_summary_execution_time_validation(self):
        """Test EvaluationRunSummary execution_time validation."""
        # Test with None value
        run = EvaluationRunSummary(
            run_id='test-run-id',
            status='RUNNING',
            execution_time=None,
        )
        assert run.execution_time == 0

        # Test with valid value
        run = EvaluationRunSummary(
            run_id='test-run-id',
            status='SUCCEEDED',
            execution_time=3600,
        )
        assert run.execution_time == 3600

    def test_recommendation_run_summary_creation(self):
        """Test creation of RecommendationRunSummary model."""
        run = RecommendationRunSummary(
            run_id='test-rec-run-id',
            status='SUCCEEDED',
            database_name='test-db',
            table_name='test-table',
            started_on='2023-01-01T00:00:00Z',
            completed_on='2023-01-01T01:00:00Z',
            execution_time=3600,
            recommendation_count=5,
        )

        assert run.run_id == 'test-rec-run-id'
        assert run.status == 'SUCCEEDED'
        assert run.database_name == 'test-db'
        assert run.table_name == 'test-table'
        assert run.started_on == '2023-01-01T00:00:00Z'
        assert run.completed_on == '2023-01-01T01:00:00Z'
        assert run.execution_time == 3600
        assert run.recommendation_count == 5

    def test_recommendation_run_summary_execution_time_validation(self):
        """Test RecommendationRunSummary execution_time validation."""
        # Test with None value
        run = RecommendationRunSummary(
            run_id='test-rec-run-id',
            status='RUNNING',
            execution_time=None,
        )
        assert run.execution_time == 0

    def test_data_quality_result_creation(self):
        """Test creation of DataQualityResult model."""
        result = DataQualityResult(
            name='IsComplete_column1',
            description='Check if column1 is complete',
            evaluation_message='Rule passed successfully',
            result='PASS',
        )

        assert result.name == 'IsComplete_column1'
        assert result.description == 'Check if column1 is complete'
        assert result.evaluation_message == 'Rule passed successfully'
        assert result.result == 'PASS'

    def test_data_quality_result_defaults(self):
        """Test DataQualityResult with default values."""
        result = DataQualityResult(
            name='IsComplete_column1',
            result='PASS',
        )

        assert result.name == 'IsComplete_column1'
        assert result.description == ''
        assert result.evaluation_message == ''
        assert result.result == 'PASS'

    def test_data_quality_ruleset_response_creation(self):
        """Test creation of DataQualityRulesetResponse model."""
        response = DataQualityRulesetResponse(
            ruleset_name='test-ruleset',
            description='Test ruleset',
            ruleset_definition='Rules = [IsComplete "column1"]',
            target_table='test-db.test-table',
            created_on='2023-01-01T00:00:00Z',
            last_modified_on='2023-01-01T00:00:00Z',
            status='CREATED',
            message='Ruleset created successfully',
        )

        assert response.ruleset_name == 'test-ruleset'
        assert response.description == 'Test ruleset'
        assert response.ruleset_definition == 'Rules = [IsComplete "column1"]'
        assert response.target_table == 'test-db.test-table'
        assert response.created_on == '2023-01-01T00:00:00Z'
        assert response.last_modified_on == '2023-01-01T00:00:00Z'
        assert response.status == 'CREATED'
        assert response.message == 'Ruleset created successfully'
        # Content is now populated by the handler, not the model
        assert len(response.content) == 0

    def test_data_quality_ruleset_response_with_rulesets(self):
        """Test DataQualityRulesetResponse with rulesets list."""
        rulesets = [
            RulesetSummary(name='ruleset-1', description='First ruleset'),
            RulesetSummary(name='ruleset-2', description='Second ruleset'),
        ]

        response = DataQualityRulesetResponse(
            rulesets=rulesets,
            ruleset_count=2,
            status='LISTED',
            message='Found 2 rulesets',
        )

        assert len(response.rulesets) == 2
        assert response.ruleset_count == 2
        assert response.rulesets[0].name == 'ruleset-1'
        assert response.rulesets[1].name == 'ruleset-2'
        assert response.status == 'LISTED'
        assert response.message == 'Found 2 rulesets'

    def test_data_quality_ruleset_response_defaults(self):
        """Test DataQualityRulesetResponse with default values."""
        response = DataQualityRulesetResponse(
            status='SUCCESS',
            message='Operation completed',
        )

        assert response.ruleset_name == ''
        assert response.description == ''
        assert response.ruleset_definition == ''
        assert response.target_table == ''
        assert response.created_on == ''
        assert response.last_modified_on == ''
        assert response.rulesets == []
        assert response.ruleset_count == 0
        assert response.status == 'SUCCESS'
        assert response.message == 'Operation completed'

    def test_data_quality_evaluation_run_response_creation(self):
        """Test creation of DataQualityEvaluationRunResponse model."""
        response = DataQualityEvaluationRunResponse(
            run_id='test-run-id',
            status='SUCCEEDED',
            database_name='test-db',
            table_name='test-table',
            ruleset_names=['test-ruleset'],
            role_arn='arn:aws:iam::123456789012:role/GlueRole',
            number_of_workers=5,
            timeout=2880,
            started_on='2023-01-01T00:00:00Z',
            completed_on='2023-01-01T01:00:00Z',
            execution_time=3600,
            result_ids=['result-1', 'result-2'],
            message='Evaluation run completed successfully',
        )

        assert response.run_id == 'test-run-id'
        assert response.status == 'SUCCEEDED'
        assert response.database_name == 'test-db'
        assert response.table_name == 'test-table'
        assert response.ruleset_names == ['test-ruleset']
        assert response.role_arn == 'arn:aws:iam::123456789012:role/GlueRole'
        assert response.number_of_workers == 5
        assert response.timeout == 2880
        assert response.started_on == '2023-01-01T00:00:00Z'
        assert response.completed_on == '2023-01-01T01:00:00Z'
        assert response.execution_time == 3600
        assert response.result_ids == ['result-1', 'result-2']
        assert response.message == 'Evaluation run completed successfully'
        # Content is now populated by the handler, not the model
        assert len(response.content) == 0

    def test_data_quality_evaluation_run_response_with_runs(self):
        """Test DataQualityEvaluationRunResponse with evaluation runs list."""
        runs = [
            EvaluationRunSummary(run_id='run-1', status='SUCCEEDED'),
            EvaluationRunSummary(run_id='run-2', status='RUNNING'),
        ]

        response = DataQualityEvaluationRunResponse(
            evaluation_runs=runs,
            run_count=2,
            status='LISTED',
            message='Found 2 evaluation runs',
        )

        assert len(response.evaluation_runs) == 2
        assert response.run_count == 2
        assert response.evaluation_runs[0].run_id == 'run-1'
        assert response.evaluation_runs[1].run_id == 'run-2'
        assert response.status == 'LISTED'

    def test_data_quality_evaluation_run_response_defaults(self):
        """Test DataQualityEvaluationRunResponse with default values."""
        response = DataQualityEvaluationRunResponse(
            status='SUCCESS',
            message='Operation completed',
        )

        assert response.run_id == ''
        assert response.database_name == ''
        assert response.table_name == ''
        assert response.ruleset_names == []
        assert response.role_arn == ''
        assert response.number_of_workers == 0
        assert response.timeout == 0
        assert response.started_on == ''
        assert response.completed_on == ''
        assert response.execution_time == 0
        assert response.result_ids == []
        assert response.error_string == ''
        assert response.evaluation_runs == []
        assert response.run_count == 0

    def test_data_quality_recommendation_run_response_creation(self):
        """Test creation of DataQualityRecommendationRunResponse model."""
        response = DataQualityRecommendationRunResponse(
            run_id='test-rec-run-id',
            status='SUCCEEDED',
            database_name='test-db',
            table_name='test-table',
            role_arn='arn:aws:iam::123456789012:role/GlueRole',
            number_of_workers=5,
            timeout=2880,
            started_on='2023-01-01T00:00:00Z',
            completed_on='2023-01-01T01:00:00Z',
            execution_time=3600,
            created_ruleset_name='recommended-ruleset',
            recommended_ruleset='Rules = [IsComplete "column1", IsUnique "column2"]',
            recommendation_count=2,
            message='Recommendation run completed successfully',
        )

        assert response.run_id == 'test-rec-run-id'
        assert response.status == 'SUCCEEDED'
        assert response.database_name == 'test-db'
        assert response.table_name == 'test-table'
        assert response.role_arn == 'arn:aws:iam::123456789012:role/GlueRole'
        assert response.number_of_workers == 5
        assert response.timeout == 2880
        assert response.started_on == '2023-01-01T00:00:00Z'
        assert response.completed_on == '2023-01-01T01:00:00Z'
        assert response.execution_time == 3600
        assert response.created_ruleset_name == 'recommended-ruleset'
        assert 'IsComplete "column1"' in response.recommended_ruleset
        assert response.recommendation_count == 2
        assert response.message == 'Recommendation run completed successfully'

    def test_data_quality_recommendation_run_response_with_runs(self):
        """Test DataQualityRecommendationRunResponse with recommendation runs list."""
        runs = [
            RecommendationRunSummary(run_id='rec-run-1', status='SUCCEEDED', recommendation_count=3),
            RecommendationRunSummary(run_id='rec-run-2', status='RUNNING', recommendation_count=0),
        ]

        response = DataQualityRecommendationRunResponse(
            recommendation_runs=runs,
            run_count=2,
            status='LISTED',
            message='Found 2 recommendation runs',
        )

        assert len(response.recommendation_runs) == 2
        assert response.run_count == 2
        assert response.recommendation_runs[0].run_id == 'rec-run-1'
        assert response.recommendation_runs[0].recommendation_count == 3
        assert response.recommendation_runs[1].run_id == 'rec-run-2'

    def test_data_quality_recommendation_run_response_defaults(self):
        """Test DataQualityRecommendationRunResponse with default values."""
        response = DataQualityRecommendationRunResponse(
            status='SUCCESS',
            message='Operation completed',
        )

        assert response.run_id == ''
        assert response.database_name == ''
        assert response.table_name == ''
        assert response.role_arn == ''
        assert response.number_of_workers == 0
        assert response.timeout == 0
        assert response.started_on == ''
        assert response.completed_on == ''
        assert response.execution_time == 0
        assert response.created_ruleset_name == ''
        assert response.recommended_ruleset == ''
        assert response.recommendation_count == 0
        assert response.error_string == ''
        assert response.recommendation_runs == []
        assert response.run_count == 0

    def test_data_quality_metrics_response_creation(self):
        """Test creation of DataQualityMetricsResponse model."""
        rule_results = [
            DataQualityResult(
                name='IsComplete_column1',
                description='Check completeness',
                evaluation_message='Rule passed',
                result='PASS',
            ),
            DataQualityResult(
                name='IsUnique_column2',
                description='Check uniqueness',
                evaluation_message='Rule failed',
                result='FAIL',
            ),
        ]

        response = DataQualityMetricsResponse(
            result_id='test-result-id',
            ruleset_name='test-ruleset',
            evaluation_context='test-context',
            started_on='2023-01-01T00:00:00Z',
            completed_on='2023-01-01T01:00:00Z',
            job_name='test-job',
            job_run_id='test-job-run-id',
            ruleset_evaluation_run_id='test-eval-run-id',
            data_source={'GlueTable': {'DatabaseName': 'test-db', 'TableName': 'test-table'}},
            role_arn='arn:aws:iam::123456789012:role/GlueRole',
            score=0.75,
            rule_results=rule_results,
            message='Data quality metrics retrieved successfully',
        )

        assert response.result_id == 'test-result-id'
        assert response.ruleset_name == 'test-ruleset'
        assert response.evaluation_context == 'test-context'
        assert response.started_on == '2023-01-01T00:00:00Z'
        assert response.completed_on == '2023-01-01T01:00:00Z'
        assert response.job_name == 'test-job'
        assert response.job_run_id == 'test-job-run-id'
        assert response.ruleset_evaluation_run_id == 'test-eval-run-id'
        assert response.data_source['GlueTable']['DatabaseName'] == 'test-db'
        assert response.role_arn == 'arn:aws:iam::123456789012:role/GlueRole'
        assert response.score == 0.75
        assert len(response.rule_results) == 2
        assert response.rule_results[0].name == 'IsComplete_column1'
        assert response.rule_results[1].result == 'FAIL'
        assert response.message == 'Data quality metrics retrieved successfully'

    def test_data_quality_metrics_response_with_result_ids(self):
        """Test DataQualityMetricsResponse with result IDs list."""
        response = DataQualityMetricsResponse(
            result_ids=['result-1', 'result-2', 'result-3'],
            result_count=3,
            status='LISTED',
            message='Found 3 data quality results',
        )

        assert response.result_ids == ['result-1', 'result-2', 'result-3']
        assert response.result_count == 3
        assert response.message == 'Found 3 data quality results'

    def test_data_quality_metrics_response_defaults(self):
        """Test DataQualityMetricsResponse with default values."""
        response = DataQualityMetricsResponse(
            message='Operation completed',
        )

        assert response.result_id == ''
        assert response.ruleset_name == ''
        assert response.evaluation_context == ''
        assert response.started_on == ''
        assert response.completed_on == ''
        assert response.job_name == ''
        assert response.job_run_id == ''
        assert response.ruleset_evaluation_run_id == ''
        assert response.data_source == {}
        assert response.role_arn == ''
        assert response.score == 0.0
        assert response.rule_results == []
        assert response.result_ids == []
        assert response.result_count == 0

    def test_response_content_manual_population(self):
        """Test that content field defaults to empty list and can be manually set."""
        # Test DataQualityRulesetResponse without content (default behavior)
        response = DataQualityRulesetResponse(
            status='SUCCESS',
            message='Test message',
        )
        # Content is not auto-populated anymore, it's handled by the handler
        assert len(response.content) == 0
        assert response.status == 'SUCCESS'
        assert response.message == 'Test message'

        # Test DataQualityEvaluationRunResponse without content (default behavior)
        response = DataQualityEvaluationRunResponse(
            status='SUCCESS',
            message='Evaluation message',
        )
        # Content is not auto-populated anymore, it's handled by the handler
        assert len(response.content) == 0

        # Test DataQualityRecommendationRunResponse without content (default behavior)
        response = DataQualityRecommendationRunResponse(
            status='SUCCESS',
            message='Recommendation message',
        )
        assert len(response.content) == 0

        # Test DataQualityMetricsResponse without content (default behavior)
        response = DataQualityMetricsResponse(
            message='Metrics message',
        )
        assert len(response.content) == 0

    def test_response_content_manual_override(self):
        """Test that manually provided empty content list is preserved."""
        # Test that we can manually set content to an empty list
        response = DataQualityRulesetResponse(
            content=[],
            status='SUCCESS',
            message='Test message',
        )
        
        assert len(response.content) == 0
        assert response.status == 'SUCCESS'
        assert response.message == 'Test message'

    def test_required_fields_validation(self):
        """Test validation of required fields."""
        # Test DataQualityResult requires name and result
        with pytest.raises(ValidationError):
            DataQualityResult(description='Test')

        # Test responses require status and message
        with pytest.raises(ValidationError):
            DataQualityRulesetResponse(status='SUCCESS')

        with pytest.raises(ValidationError):
            DataQualityEvaluationRunResponse(message='Test')

    def test_field_types_validation(self):
        """Test validation of field types."""
        # Test that score must be a float
        response = DataQualityMetricsResponse(
            score='0.95',  # String that can be converted to float
            message='Test',
        )
        assert response.score == 0.95

        # Test that counts must be integers
        response = DataQualityRulesetResponse(
            ruleset_count='5',  # String that can be converted to int
            status='SUCCESS',
            message='Test',
        )
        assert response.ruleset_count == 5