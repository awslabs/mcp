"""Unit tests for Workflow Orchestrator.

This module contains comprehensive unit tests for the WorkflowOrchestrator class,
including smart translation workflows, batch translation workflows, and error analysis.
"""

import asyncio
import pytest
import time
from awslabs.amazon_translate_mcp_server.exceptions import (
    ValidationError,
)
from awslabs.amazon_translate_mcp_server.models import (
    LanguageDetectionResult,
    LanguagePair,
    TerminologyDetails,
    TranslationJobStatus,
    TranslationResult,
    ValidationResult,
)
from awslabs.amazon_translate_mcp_server.workflow_orchestrator import WorkflowOrchestrator
from datetime import datetime
from unittest.mock import Mock, patch


class TestWorkflowOrchestrator:
    """Test WorkflowOrchestrator initialization and basic functionality."""

    @pytest.fixture
    def mock_services(self):
        """Create mock services for testing."""
        translation_service = Mock()
        batch_manager = Mock()
        terminology_manager = Mock()
        language_operations = Mock()

        return {
            'translation': translation_service,
            'batch': batch_manager,
            'terminology': terminology_manager,
            'language': language_operations,
        }

    @pytest.fixture
    def workflow_orchestrator(self, mock_services):
        """Create WorkflowOrchestrator instance with mocked services."""
        return WorkflowOrchestrator(
            translation_service=mock_services['translation'],
            batch_manager=mock_services['batch'],
            terminology_manager=mock_services['terminology'],
            language_operations=mock_services['language'],
        )

    def test_initialization(self, workflow_orchestrator, mock_services):
        """Test WorkflowOrchestrator initialization."""
        assert workflow_orchestrator.translation_service == mock_services['translation']
        assert workflow_orchestrator.batch_manager == mock_services['batch']
        assert workflow_orchestrator.terminology_manager == mock_services['terminology']
        assert workflow_orchestrator.language_operations == mock_services['language']
        assert workflow_orchestrator._active_workflows == {}
        assert workflow_orchestrator._workflow_results == {}


class TestSmartTranslationWorkflow:
    """Test smart translation workflow functionality."""

    @pytest.fixture
    def workflow_orchestrator(self):
        """Create WorkflowOrchestrator with mocked services."""
        translation_service = Mock()
        batch_manager = Mock()
        terminology_manager = Mock()
        language_operations = Mock()

        return WorkflowOrchestrator(
            translation_service=translation_service,
            batch_manager=batch_manager,
            terminology_manager=terminology_manager,
            language_operations=language_operations,
        )

    @pytest.mark.asyncio
    async def test_smart_translate_workflow_success(self, workflow_orchestrator):
        """Test successful smart translation workflow execution."""
        # Mock language detection
        detection_result = LanguageDetectionResult(
            detected_language='en', confidence_score=0.95, alternative_languages=[]
        )
        workflow_orchestrator.translation_service.detect_language.return_value = detection_result

        # Mock language pairs
        language_pairs = [
            LanguagePair(
                source_language='en', target_language='es', supported_formats=['text/plain']
            )
        ]
        workflow_orchestrator.language_operations.list_language_pairs.return_value = language_pairs

        # Mock translation
        translation_result = TranslationResult(
            translated_text='Hola mundo',
            source_language='en',
            target_language='es',
            applied_terminologies=[],
        )
        workflow_orchestrator.translation_service.translate_text.return_value = translation_result

        # Mock validation
        validation_result = ValidationResult(
            is_valid=True, quality_score=0.92, issues=[], suggestions=['Great translation!']
        )
        workflow_orchestrator.translation_service.validate_translation.return_value = (
            validation_result
        )

        # Execute workflow
        result = await workflow_orchestrator.smart_translate_workflow(
            text='Hello world',
            target_language='es',
            quality_threshold=0.8,
            terminology_names=[],
            auto_detect_language=True,
        )

        # Verify result
        assert result.original_text == 'Hello world'
        assert result.translated_text == 'Hola mundo'
        assert result.detected_language == 'en'
        assert result.target_language == 'es'
        assert result.confidence_score == 0.95
        assert result.quality_score == 0.92
        assert result.language_pair_supported is True
        assert len(result.workflow_steps) > 0
        assert 'detect_language' in result.workflow_steps
        assert 'translate_text' in result.workflow_steps
        assert 'validate_translation' in result.workflow_steps

    @pytest.mark.asyncio
    async def test_smart_translate_workflow_unsupported_language_pair(self, workflow_orchestrator):
        """Test workflow with unsupported language pair."""
        # Mock language detection
        detection_result = LanguageDetectionResult(
            detected_language='en', confidence_score=0.95, alternative_languages=[]
        )
        workflow_orchestrator.translation_service.detect_language.return_value = detection_result

        # Mock empty language pairs (unsupported)
        workflow_orchestrator.language_operations.list_language_pairs.return_value = []

        # Execute workflow - should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            await workflow_orchestrator.smart_translate_workflow(
                text='Hello world',
                target_language='xx',  # Unsupported language
                quality_threshold=0.8,
            )

        assert 'not supported' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_smart_translate_workflow_low_quality(self, workflow_orchestrator):
        """Test workflow with low quality translation."""
        # Mock services for successful workflow but low quality
        detection_result = LanguageDetectionResult(
            detected_language='en', confidence_score=0.95, alternative_languages=[]
        )
        workflow_orchestrator.translation_service.detect_language.return_value = detection_result

        language_pairs = [
            LanguagePair(
                source_language='en', target_language='es', supported_formats=['text/plain']
            )
        ]
        workflow_orchestrator.language_operations.list_language_pairs.return_value = language_pairs

        translation_result = TranslationResult(
            translated_text='Hola mundo',
            source_language='en',
            target_language='es',
            applied_terminologies=[],
        )
        workflow_orchestrator.translation_service.translate_text.return_value = translation_result

        # Mock low quality validation
        validation_result = ValidationResult(
            is_valid=True,
            quality_score=0.5,
            issues=['Low quality'],
            suggestions=['Improve translation'],
        )
        workflow_orchestrator.translation_service.validate_translation.return_value = (
            validation_result
        )

        result = await workflow_orchestrator.smart_translate_workflow(
            text='Hello world',
            target_language='es',
            quality_threshold=0.8,  # Higher than actual quality
        )

        # Should still complete but with quality warning
        assert result.quality_score == 0.5
        assert len(result.validation_issues) == 1
        assert 'Low quality' in result.validation_issues


class TestBatchTranslationWorkflow:
    """Test batch translation workflow functionality."""

    @pytest.fixture
    def workflow_orchestrator(self):
        """Create WorkflowOrchestrator with mocked services."""
        translation_service = Mock()
        batch_manager = Mock()
        terminology_manager = Mock()
        language_operations = Mock()

        return WorkflowOrchestrator(
            translation_service=translation_service,
            batch_manager=batch_manager,
            terminology_manager=terminology_manager,
            language_operations=language_operations,
        )

    @pytest.mark.asyncio
    async def test_managed_batch_translation_workflow_success(self, workflow_orchestrator):
        """Test successful managed batch translation workflow."""
        # Mock language pairs validation
        language_pairs = [
            LanguagePair(
                source_language='en', target_language='es', supported_formats=['text/plain']
            ),
            LanguagePair(
                source_language='en', target_language='fr', supported_formats=['text/plain']
            ),
        ]
        workflow_orchestrator.language_operations.list_language_pairs.return_value = language_pairs

        # Mock terminology validation
        workflow_orchestrator.terminology_manager.list_terminologies.return_value = {
            'terminologies': [],
            'next_token': None,
        }

        # Mock batch job start
        workflow_orchestrator.batch_manager.start_batch_translation.return_value = 'job-123'

        # Mock job monitoring - simulate job progression
        job_statuses = [
            TranslationJobStatus(
                job_id='job-123', job_name='test-job', status='SUBMITTED', progress=0.0
            ),
            TranslationJobStatus(
                job_id='job-123', job_name='test-job', status='IN_PROGRESS', progress=50.0
            ),
            TranslationJobStatus(
                job_id='job-123',
                job_name='test-job',
                status='COMPLETED',
                progress=100.0,
                created_at=datetime.now(),
                completed_at=datetime.now(),
            ),
        ]
        workflow_orchestrator.batch_manager.get_translation_job.side_effect = job_statuses

        # Mock language metrics
        from awslabs.amazon_translate_mcp_server.models import LanguageMetrics

        mock_metrics = LanguageMetrics(
            language_pair='en-es',
            time_range='24h',
            translation_count=100,
            character_count=5000,
            average_response_time=150.0,
            error_rate=0.02,
        )
        workflow_orchestrator.language_operations.get_language_metrics.return_value = mock_metrics

        # Execute workflow
        result = await workflow_orchestrator.managed_batch_translation_workflow(
            input_s3_uri='s3://bucket/input/',
            output_s3_uri='s3://bucket/output/',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
            job_name='test-job',
            source_language='en',
            target_languages=['es', 'fr'],
            terminology_names=[],
            content_type='text/plain',
            monitor_interval=1,  # Fast for testing
            max_monitoring_duration=10,
        )

        # Verify result
        assert result.job_id == 'job-123'
        assert result.job_name == 'test-job'
        assert result.status == 'COMPLETED'
        assert result.source_language == 'en'
        assert result.target_languages == ['es', 'fr']
        assert len(result.monitoring_history) == 3
        assert result.performance_metrics is not None
        assert 'validate_language_pairs' in result.workflow_steps
        assert 'start_batch_job' in result.workflow_steps
        assert 'monitor_job_progress' in result.workflow_steps

    @pytest.mark.asyncio
    async def test_managed_batch_translation_workflow_with_terminology(
        self, workflow_orchestrator
    ):
        """Test workflow with terminology validation."""
        # Mock language pairs
        language_pairs = [
            LanguagePair(
                source_language='en', target_language='es', supported_formats=['text/plain']
            )
        ]
        workflow_orchestrator.language_operations.list_language_pairs.return_value = language_pairs

        # Mock terminology validation - terminology exists
        mock_terminology = TerminologyDetails(
            name='tech-terms',
            description='Technical terms',
            source_language='en',
            target_languages=['es'],
            term_count=100,
            created_at=datetime.now(),
        )
        workflow_orchestrator.terminology_manager.list_terminologies.return_value = {
            'terminologies': [mock_terminology],
            'next_token': None,
        }

        # Mock batch job
        workflow_orchestrator.batch_manager.start_batch_translation.return_value = 'job-456'
        workflow_orchestrator.batch_manager.get_translation_job.return_value = (
            TranslationJobStatus(
                job_id='job-456',
                job_name='test-job-456',
                status='COMPLETED',
                progress=100.0,
                created_at=datetime.now(),
                completed_at=datetime.now(),
            )
        )

        # Mock metrics
        from awslabs.amazon_translate_mcp_server.models import LanguageMetrics

        mock_metrics = LanguageMetrics(
            language_pair='en-es',
            time_range='24h',
            translation_count=50,
            character_count=2500,
            average_response_time=120.0,
            error_rate=0.01,
        )
        workflow_orchestrator.language_operations.get_language_metrics.return_value = mock_metrics

        result = await workflow_orchestrator.managed_batch_translation_workflow(
            input_s3_uri='s3://bucket/input/',
            output_s3_uri='s3://bucket/output/',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
            job_name='test-terminology-job',
            source_language='en',
            target_languages=['es'],
            terminology_names=['tech-terms'],
            content_type='text/plain',
            monitor_interval=1,
            max_monitoring_duration=5,
        )

        assert result.terminology_names == ['tech-terms']
        assert 'validate_terminologies' in result.workflow_steps

    @pytest.mark.asyncio
    async def test_managed_batch_translation_workflow_failed_job(self, workflow_orchestrator):
        """Test workflow with failed batch job and error analysis."""
        # Mock validations
        language_pairs = [
            LanguagePair(
                source_language='en', target_language='es', supported_formats=['text/plain']
            )
        ]
        workflow_orchestrator.language_operations.list_language_pairs.return_value = language_pairs
        workflow_orchestrator.terminology_manager.list_terminologies.return_value = {
            'terminologies': [],
            'next_token': None,
        }

        # Mock batch job that fails
        workflow_orchestrator.batch_manager.start_batch_translation.return_value = 'failed-job-789'
        workflow_orchestrator.batch_manager.get_translation_job.return_value = (
            TranslationJobStatus(
                job_id='failed-job-789',
                job_name='failed-job-789',
                status='FAILED',
                progress=25.0,
                created_at=datetime.now(),
            )
        )

        # Mock error analysis
        mock_error_analysis = {
            'job_id': 'failed-job-789',
            'error_files_found': ['error.json'],
            'error_details': [
                {'file': 'error.json', 'error_data': {'error': 'File format not supported'}}
            ],
            'suggested_actions': ['Convert files to supported format'],
        }

        with patch.object(
            workflow_orchestrator, '_analyze_job_errors', return_value=mock_error_analysis
        ):
            result = await workflow_orchestrator.managed_batch_translation_workflow(
                input_s3_uri='s3://bucket/input/',
                output_s3_uri='s3://bucket/output/',
                data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
                job_name='failed-job',
                source_language='en',
                target_languages=['es'],
                monitor_interval=1,
                max_monitoring_duration=5,
            )

        assert result.status == 'FAILED'
        assert result.error_analysis is not None
        assert len(result.error_analysis['suggested_actions']) > 0


class TestErrorAnalysis:
    """Test error analysis functionality."""

    @pytest.fixture
    def workflow_orchestrator(self):
        """Create WorkflowOrchestrator with mocked services."""
        translation_service = Mock()
        batch_manager = Mock()
        terminology_manager = Mock()
        language_operations = Mock()

        orchestrator = WorkflowOrchestrator(
            translation_service=translation_service,
            batch_manager=batch_manager,
            terminology_manager=terminology_manager,
            language_operations=language_operations,
        )

        # Mock S3 client
        batch_manager.s3_client = Mock()

        return orchestrator

    @pytest.mark.asyncio
    async def test_analyze_job_errors_success(self, workflow_orchestrator):
        """Test successful error analysis."""
        # Mock S3 responses
        s3_client = workflow_orchestrator.batch_manager.s3_client

        # Mock folder listing
        s3_client.list_objects_v2.side_effect = [
            # First call - find job folder
            {
                'CommonPrefixes': [
                    {
                        'Prefix': 'output/123456789012-TranslateText-job-123/'
                    }  # pragma: allowlist secret
                ]
            },
            # Second call - list error files
            {
                'Contents': [
                    {
                        'Key': 'output/123456789012-TranslateText-job-123/details/es.error.json'
                    },  # Test S3 key path
                    {
                        'Key': 'output/123456789012-TranslateText-job-123/details/fr.error.json'
                    },  # Test S3 key path
                ]
            },
        ]

        # Mock error file content
        error_content = {
            'sourceLanguageCode': 'en',
            'targetLanguageCode': 'es',
            'documentCountWithCustomerError': '1',
            'details': [
                {
                    'sourceFile': 'test.pdf',
                    'auxiliaryData': {
                        'error': {
                            'errorCode': 'InvalidRequestException',
                            'errorMessage': 'Invalid utf-8 encoded texts detected',
                        }
                    },
                }
            ],
        }

        s3_client.get_object.return_value = {
            'Body': Mock(read=Mock(return_value=str(error_content).encode('utf-8')))
        }

        # Mock json.loads to return proper dict
        with patch('json.loads', return_value=error_content):
            loop = asyncio.get_event_loop()
            result = await workflow_orchestrator._analyze_job_errors(
                'job-123', 's3://bucket/output/', loop
            )

        assert result is not None
        assert result['job_id'] == 'job-123'
        assert len(result['error_files_found']) == 2
        assert len(result['suggested_actions']) > 0

    @pytest.mark.asyncio
    async def test_analyze_job_errors_no_details_folder(self, workflow_orchestrator):
        """Test error analysis when no details folder exists."""
        s3_client = workflow_orchestrator.batch_manager.s3_client

        # Mock no job folder found
        s3_client.list_objects_v2.return_value = {}

        loop = asyncio.get_event_loop()
        result = await workflow_orchestrator._analyze_job_errors(
            'nonexistent-job', 's3://bucket/output/', loop
        )

        assert result is None

    def test_generate_error_suggestions_utf8_error(self, workflow_orchestrator):
        """Test error suggestion generation for UTF-8 errors."""
        error_data = {'errorMessage': 'Invalid utf-8 encoded texts detected'}

        suggestions = workflow_orchestrator._generate_error_suggestions(error_data)

        assert len(suggestions) > 0
        assert any('encoding' in suggestion.lower() for suggestion in suggestions)
        assert any('format' in suggestion.lower() for suggestion in suggestions)

    def test_generate_error_suggestions_permission_error(self, workflow_orchestrator):
        """Test error suggestion generation for permission errors."""
        error_data = {'errorMessage': 'Access denied to S3 bucket'}

        suggestions = workflow_orchestrator._generate_error_suggestions(error_data)

        assert len(suggestions) > 0
        assert any('permission' in suggestion.lower() for suggestion in suggestions)
        assert any('iam' in suggestion.lower() for suggestion in suggestions)

    def test_generate_error_suggestions_language_error(self, workflow_orchestrator):
        """Test error suggestion generation for language errors."""
        error_data = {'errorMessage': 'Unsupported language pair detected'}

        suggestions = workflow_orchestrator._generate_error_suggestions(error_data)

        assert len(suggestions) > 0
        assert any('language' in suggestion.lower() for suggestion in suggestions)

    def test_generate_error_suggestions_size_error(self, workflow_orchestrator):
        """Test error suggestion generation for size limit errors."""
        error_data = {'errorMessage': 'File size exceeds the limit'}

        suggestions = workflow_orchestrator._generate_error_suggestions(error_data)

        assert len(suggestions) > 0
        assert any('size' in suggestion.lower() for suggestion in suggestions)
        assert any('split' in suggestion.lower() for suggestion in suggestions)


class TestWorkflowStateManagement:
    """Test workflow state management functionality."""

    @pytest.fixture
    def workflow_orchestrator(self):
        """Create WorkflowOrchestrator with mocked services."""
        translation_service = Mock()
        batch_manager = Mock()
        terminology_manager = Mock()
        language_operations = Mock()

        return WorkflowOrchestrator(
            translation_service=translation_service,
            batch_manager=batch_manager,
            terminology_manager=terminology_manager,
            language_operations=language_operations,
        )

    def test_get_workflow_status_existing(self, workflow_orchestrator):
        """Test getting status of existing workflow."""
        from awslabs.amazon_translate_mcp_server.workflow_orchestrator import WorkflowContext

        # Add a workflow to active workflows
        workflow_id = 'test-workflow-123'
        context = WorkflowContext(
            workflow_id=workflow_id,
            workflow_type='smart_translation',
            started_at=datetime.now(),
            current_step='translate_text',
            completed_steps=['detect_language'],
            metadata={'text_length': 100},
        )
        workflow_orchestrator._active_workflows[workflow_id] = context

        status = workflow_orchestrator.get_workflow_status(workflow_id)

        assert status is not None
        assert status['workflow_id'] == workflow_id
        assert status['workflow_type'] == 'smart_translation'
        assert status['current_step'] == 'translate_text'
        assert len(status['completed_steps']) == 1

    def test_get_workflow_status_nonexistent(self, workflow_orchestrator):
        """Test getting status of non-existent workflow."""
        status = workflow_orchestrator.get_workflow_status('nonexistent-workflow')
        assert status is None

    def test_list_active_workflows(self, workflow_orchestrator):
        """Test listing active workflows."""
        from awslabs.amazon_translate_mcp_server.workflow_orchestrator import WorkflowContext

        # Add multiple workflows
        for i in range(3):
            workflow_id = f'workflow-{i}'
            context = WorkflowContext(
                workflow_id=workflow_id,
                workflow_type='smart_translation',
                started_at=datetime.now(),
                current_step=f'step-{i}',
            )
            workflow_orchestrator._active_workflows[workflow_id] = context

        active_workflows = workflow_orchestrator.list_active_workflows()

        assert len(active_workflows) == 3
        assert all(
            workflow['workflow_id'].startswith('workflow-') for workflow in active_workflows
        )

    def test_get_workflow_result(self, workflow_orchestrator):
        """Test getting workflow result."""
        workflow_id = 'completed-workflow-456'
        mock_result = {'status': 'completed', 'result': 'success'}

        workflow_orchestrator._workflow_results[workflow_id] = mock_result

        result = workflow_orchestrator.get_workflow_result(workflow_id)
        assert result == mock_result

        # Test non-existent result
        nonexistent_result = workflow_orchestrator.get_workflow_result('nonexistent')
        assert nonexistent_result is None

    def test_cleanup_old_results(self, workflow_orchestrator):
        """Test cleanup of old workflow results."""
        # Add some workflow results with timestamp-based IDs
        current_time = int(time.time() * 1000)
        old_time = current_time - (25 * 60 * 60 * 1000)  # 25 hours ago

        workflow_orchestrator._workflow_results[f'old_workflow_{old_time}'] = {'old': True}
        workflow_orchestrator._workflow_results[f'new_workflow_{current_time}'] = {'new': True}
        workflow_orchestrator._workflow_results['invalid_format'] = {'invalid': True}

        cleaned_count = workflow_orchestrator.cleanup_old_results(max_age_hours=24)

        assert cleaned_count == 1  # Only the old one should be cleaned
        assert f'old_workflow_{old_time}' not in workflow_orchestrator._workflow_results
        assert f'new_workflow_{current_time}' in workflow_orchestrator._workflow_results
        assert (
            'invalid_format' in workflow_orchestrator._workflow_results
        )  # Invalid format preserved
