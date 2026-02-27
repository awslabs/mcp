"""Tests for Amazon Translate MCP Server Workflow Features.

This module contains unit tests for the workflow orchestration features
including parameter validation and workflow execution logic.
"""

import pytest
from awslabs.amazon_translate_mcp_server.models import (
    LanguageDetectionResult,
    LanguagePair,
    TranslationResult,
    ValidationResult,
)
from awslabs.amazon_translate_mcp_server.workflow_orchestrator import (
    BatchTranslationWorkflowResult,
    SmartTranslationWorkflowResult,
    WorkflowContext,
    WorkflowOrchestrator,
)
from datetime import datetime
from unittest.mock import Mock


class TestWorkflowParameterValidation:
    """Test workflow parameter validation."""

    def test_smart_translation_workflow_params(self):
        """Test SmartTranslateWorkflowParams validation."""
        from awslabs.amazon_translate_mcp_server.server import SmartTranslateWorkflowParams

        # Valid parameters
        params = SmartTranslateWorkflowParams(
            text='Hello world',
            target_language='es',
            quality_threshold=0.8,
            terminology_names=['tech-terms'],
            auto_detect_language=True,
        )

        assert params.text == 'Hello world'
        assert params.target_language == 'es'
        assert params.quality_threshold == 0.8
        assert params.terminology_names == ['tech-terms']
        assert params.auto_detect_language is True

    def test_managed_batch_translation_workflow_params(self):
        """Test ManagedBatchTranslationWorkflowParams validation."""
        from awslabs.amazon_translate_mcp_server.server import (
            ManagedBatchTranslationWorkflowParams,
        )

        # Valid parameters
        params = ManagedBatchTranslationWorkflowParams(
            input_s3_uri='s3://input-bucket/docs/',
            output_s3_uri='s3://output-bucket/translated/',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
            job_name='test-job',
            source_language='en',
            target_languages=['es', 'fr'],
            terminology_names=['ui-terms'],
            content_type='text/plain',
            monitor_interval=30,
            max_monitoring_duration=3600,
        )

        assert params.input_s3_uri == 's3://input-bucket/docs/'
        assert params.output_s3_uri == 's3://output-bucket/translated/'
        assert params.job_name == 'test-job'
        assert params.source_language == 'en'
        assert params.target_languages == ['es', 'fr']
        assert params.monitor_interval == 30


class TestWorkflowOrchestrator:
    """Test workflow orchestrator functionality."""

    @pytest.fixture
    def mock_services(self):
        """Create mock services for testing."""
        translation_service = Mock()
        batch_manager = Mock()
        terminology_manager = Mock()
        language_operations = Mock()

        return {
            'translation_service': translation_service,
            'batch_manager': batch_manager,
            'terminology_manager': terminology_manager,
            'language_operations': language_operations,
        }

    @pytest.fixture
    def workflow_orchestrator(self, mock_services):
        """Create workflow orchestrator with mock services."""
        return WorkflowOrchestrator(
            translation_service=mock_services['translation_service'],
            batch_manager=mock_services['batch_manager'],
            terminology_manager=mock_services['terminology_manager'],
            language_operations=mock_services['language_operations'],
        )

    @pytest.mark.asyncio
    async def test_smart_translate_workflow_success(self, workflow_orchestrator, mock_services):
        """Test successful smart translation workflow execution."""
        # Mock service responses
        mock_services[
            'translation_service'
        ].detect_language.return_value = LanguageDetectionResult(
            detected_language='fr', confidence_score=0.95, alternative_languages=[('es', 0.05)]
        )

        mock_services['language_operations'].list_language_pairs.return_value = [
            LanguagePair(source_language='fr', target_language='en')
        ]

        mock_services['translation_service'].translate_text.return_value = TranslationResult(
            translated_text='Hello, how are you?',
            source_language='fr',
            target_language='en',
            applied_terminologies=[],
            confidence_score=0.92,
        )

        mock_services['translation_service'].validate_translation.return_value = ValidationResult(
            is_valid=True, quality_score=0.88, issues=[], suggestions=[]
        )

        # Execute workflow
        result = await workflow_orchestrator.smart_translate_workflow(
            text='Bonjour, comment allez-vous?', target_language='en', quality_threshold=0.8
        )

        # Verify result
        assert isinstance(result, SmartTranslationWorkflowResult)
        assert result.original_text == 'Bonjour, comment allez-vous?'
        assert result.translated_text == 'Hello, how are you?'
        assert result.detected_language == 'fr'
        assert result.target_language == 'en'
        assert result.confidence_score == 0.95
        assert result.quality_score == 0.88
        assert result.language_pair_supported is True
        assert len(result.workflow_steps) == 4

        # Verify service calls
        mock_services['translation_service'].detect_language.assert_called_once()
        mock_services['language_operations'].list_language_pairs.assert_called_once()
        mock_services['translation_service'].translate_text.assert_called_once()
        mock_services['translation_service'].validate_translation.assert_called_once()

    @pytest.mark.asyncio
    async def test_smart_translate_workflow_unsupported_language_pair(
        self, workflow_orchestrator, mock_services
    ):
        """Test smart translation workflow with unsupported language pair."""
        # Mock service responses
        mock_services[
            'translation_service'
        ].detect_language.return_value = LanguageDetectionResult(
            detected_language='xyz',  # Unsupported language
            confidence_score=0.95,
        )

        mock_services['language_operations'].list_language_pairs.return_value = [
            LanguagePair(source_language='en', target_language='es')
        ]

        # Execute workflow and expect ValidationError
        with pytest.raises(Exception) as exc_info:
            await workflow_orchestrator.smart_translate_workflow(
                text='Some text in unsupported language', target_language='en'
            )

        # Verify error handling
        assert 'not supported' in str(exc_info.value)

    def test_workflow_context_creation(self):
        """Test workflow context creation and management."""
        context = WorkflowContext(
            workflow_id='test_workflow_123',
            workflow_type='smart_translation',
            started_at=datetime.now(),
            current_step='detect_language',
            metadata={'test': 'data'},
        )

        assert context.workflow_id == 'test_workflow_123'
        assert context.workflow_type == 'smart_translation'
        assert context.current_step == 'detect_language'
        assert context.metadata['test'] == 'data'
        assert context.error_count == 0
        assert context.retry_count == 0

    def test_workflow_management_methods(self, workflow_orchestrator):
        """Test workflow management methods."""
        # Test with no active workflows
        active_workflows = workflow_orchestrator.list_active_workflows()
        assert len(active_workflows) == 0

        # Test getting non-existent workflow status
        status = workflow_orchestrator.get_workflow_status('non_existent')
        assert status is None

        # Test getting non-existent workflow result
        result = workflow_orchestrator.get_workflow_result('non_existent')
        assert result is None

        # Test cleanup with no results
        cleaned_count = workflow_orchestrator.cleanup_old_results()
        assert cleaned_count == 0


class TestWorkflowResultModels:
    """Test workflow result data models."""

    def test_smart_translation_workflow_result(self):
        """Test SmartTranslationWorkflowResult model."""
        result = SmartTranslationWorkflowResult(
            original_text='Bonjour',
            translated_text='Hello',
            detected_language='fr',
            target_language='en',
            confidence_score=0.95,
            quality_score=0.88,
            applied_terminologies=['tech-terms'],
            language_pair_supported=True,
            validation_issues=[],
            suggestions=['Consider using formal tone'],
            execution_time_ms=1250.5,
            workflow_steps=['detect_language', 'translate_text'],
        )

        assert result.original_text == 'Bonjour'
        assert result.translated_text == 'Hello'
        assert result.detected_language == 'fr'
        assert result.target_language == 'en'
        assert result.confidence_score == 0.95
        assert result.quality_score == 0.88
        assert result.applied_terminologies == ['tech-terms']
        assert result.language_pair_supported is True
        assert result.suggestions == ['Consider using formal tone']
        assert result.execution_time_ms == 1250.5
        assert len(result.workflow_steps) == 2

    def test_batch_translation_workflow_result(self):
        """Test BatchTranslationWorkflowResult model."""
        result = BatchTranslationWorkflowResult(
            job_id='job-123',
            job_name='test-job',
            status='COMPLETED',
            source_language='en',
            target_languages=['es', 'fr'],
            input_s3_uri='s3://input/',
            output_s3_uri='s3://output/',
            terminology_names=['ui-terms'],
            pre_validation_results={'supported_pairs': ['en->es', 'en->fr']},
            monitoring_history=[{'timestamp': '2024-01-15T10:00:00Z', 'status': 'SUBMITTED'}],
            performance_metrics={'total_monitoring_time': 1200},
            created_at=datetime.now(),
            total_execution_time=1200.5,
            workflow_steps=['validate_language_pairs', 'start_batch_job'],
        )

        assert result.job_id == 'job-123'
        assert result.job_name == 'test-job'
        assert result.status == 'COMPLETED'
        assert result.source_language == 'en'
        assert result.target_languages == ['es', 'fr']
        assert result.terminology_names == ['ui-terms']
        assert len(result.monitoring_history) == 1
        assert result.total_execution_time == 1200.5
        assert len(result.workflow_steps) == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
