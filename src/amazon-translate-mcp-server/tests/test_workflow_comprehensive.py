"""Comprehensive tests for Workflow Orchestrator.

This module contains tests to achieve high coverage of the workflow_orchestrator.py module.
"""

import asyncio
import pytest
import time
from awslabs.amazon_translate_mcp_server.exceptions import (
    TranslationError,
    ValidationError,
)
from awslabs.amazon_translate_mcp_server.models import (
    LanguageDetectionResult,
    LanguageMetrics,
    LanguagePair,
    TerminologyDetails,
    TranslationJobStatus,
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
from unittest.mock import Mock, patch


class TestWorkflowContext:
    """Test WorkflowContext class."""

    def test_workflow_context_creation(self):
        """Test WorkflowContext creation."""
        context = WorkflowContext(
            workflow_id='test-workflow-123',
            workflow_type='smart_translation',
            started_at=datetime.now(),
            current_step='translate_text',
            completed_steps=['detect_language'],
            metadata={'text_length': 100},
        )

        assert context.workflow_id == 'test-workflow-123'
        assert context.workflow_type == 'smart_translation'
        assert context.current_step == 'translate_text'
        assert len(context.completed_steps) == 1
        assert context.completed_steps[0] == 'detect_language'
        assert context.metadata['text_length'] == 100
        assert context.error_count == 0

    def test_workflow_context_defaults(self):
        """Test WorkflowContext with default values."""
        context = WorkflowContext(
            workflow_id='test-workflow',
            workflow_type='batch_translation',
            started_at=datetime.now(),
        )

        assert context.workflow_id == 'test-workflow'
        assert context.workflow_type == 'batch_translation'
        assert context.current_step == ''  # Default is empty string, not None
        assert context.completed_steps == []
        assert context.metadata == {}
        assert context.error_count == 0


class TestWorkflowOrchestratorInitialization:
    """Test WorkflowOrchestrator initialization."""

    def test_workflow_orchestrator_initialization(self):
        """Test WorkflowOrchestrator initialization."""
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

        assert orchestrator.translation_service == translation_service
        assert orchestrator.batch_manager == batch_manager
        assert orchestrator.terminology_manager == terminology_manager
        assert orchestrator.language_operations == language_operations
        assert orchestrator._active_workflows == {}
        assert orchestrator._workflow_results == {}


class TestSmartTranslationWorkflowComprehensive:
    """Comprehensive tests for smart translation workflow."""

    @pytest.fixture
    def orchestrator(self):
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
    async def test_smart_translate_workflow_full_success(self, orchestrator):
        """Test complete smart translation workflow success."""
        # Mock language detection
        detection_result = LanguageDetectionResult(
            detected_language='en', confidence_score=0.95, alternative_languages=[('fr', 0.03)]
        )
        orchestrator.translation_service.detect_language.return_value = detection_result

        # Mock language pairs
        language_pairs = [
            LanguagePair(
                source_language='en', target_language='es', supported_formats=['text/plain']
            )
        ]
        orchestrator.language_operations.list_language_pairs.return_value = language_pairs

        # Mock translation
        translation_result = TranslationResult(
            translated_text='Hola mundo',
            source_language='en',
            target_language='es',
            applied_terminologies=['tech-terms'],
        )
        orchestrator.translation_service.translate_text.return_value = translation_result

        # Mock validation
        validation_result = ValidationResult(
            is_valid=True, quality_score=0.92, issues=[], suggestions=['Great translation!']
        )
        orchestrator.translation_service.validate_translation.return_value = validation_result

        # Execute workflow
        result = await orchestrator.smart_translate_workflow(
            text='Hello world',
            target_language='es',
            quality_threshold=0.8,
            terminology_names=['tech-terms'],
            auto_detect_language=True,
        )

        # Verify result
        assert result.original_text == 'Hello world'
        assert result.translated_text == 'Hola mundo'
        assert result.detected_language == 'en'
        assert result.target_language == 'es'
        assert result.confidence_score == 0.95
        assert result.quality_score == 0.92
        assert result.applied_terminologies == ['tech-terms']
        assert result.language_pair_supported is True
        assert len(result.workflow_steps) == 4
        assert 'detect_language' in result.workflow_steps
        assert 'validate_language_pair' in result.workflow_steps
        assert 'translate_text' in result.workflow_steps
        assert 'validate_translation' in result.workflow_steps

    @pytest.mark.asyncio
    async def test_smart_translate_workflow_without_auto_detect(self, orchestrator):
        """Test smart translation workflow without auto-detection."""
        # Mock language detection (still called even without auto-detect)
        detection_result = LanguageDetectionResult(
            detected_language='en', confidence_score=0.90, alternative_languages=[]
        )
        orchestrator.translation_service.detect_language.return_value = detection_result

        # Mock language pairs
        language_pairs = [
            LanguagePair(
                source_language='en', target_language='fr', supported_formats=['text/plain']
            )
        ]
        orchestrator.language_operations.list_language_pairs.return_value = language_pairs

        # Mock translation
        translation_result = TranslationResult(
            translated_text='Bonjour le monde',
            source_language='en',
            target_language='fr',
            applied_terminologies=[],
        )
        orchestrator.translation_service.translate_text.return_value = translation_result

        # Mock validation
        validation_result = ValidationResult(
            is_valid=True, quality_score=0.88, issues=[], suggestions=[]
        )
        orchestrator.translation_service.validate_translation.return_value = validation_result

        # Execute workflow without auto-detection
        result = await orchestrator.smart_translate_workflow(
            text='Hello world',
            target_language='fr',
            quality_threshold=0.8,
            terminology_names=None,
            auto_detect_language=False,
        )

        # Verify result
        assert result.translated_text == 'Bonjour le monde'
        assert result.detected_language == 'en'
        assert result.target_language == 'fr'
        assert result.applied_terminologies == []

    @pytest.mark.asyncio
    async def test_smart_translate_workflow_unsupported_language_pair(self, orchestrator):
        """Test workflow with unsupported language pair."""
        # Mock language detection
        detection_result = LanguageDetectionResult(
            detected_language='en', confidence_score=0.95, alternative_languages=[]
        )
        orchestrator.translation_service.detect_language.return_value = detection_result

        # Mock empty language pairs (unsupported)
        orchestrator.language_operations.list_language_pairs.return_value = []

        # Execute workflow - should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            await orchestrator.smart_translate_workflow(
                text='Hello world',
                target_language='xx',  # Unsupported language
                quality_threshold=0.8,
            )

        assert 'Language pair en->xx is not supported' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_smart_translate_workflow_low_quality_warning(self, orchestrator):
        """Test workflow with low quality translation."""
        # Mock services for successful workflow but low quality
        detection_result = LanguageDetectionResult(
            detected_language='en', confidence_score=0.95, alternative_languages=[]
        )
        orchestrator.translation_service.detect_language.return_value = detection_result

        language_pairs = [
            LanguagePair(
                source_language='en', target_language='es', supported_formats=['text/plain']
            )
        ]
        orchestrator.language_operations.list_language_pairs.return_value = language_pairs

        translation_result = TranslationResult(
            translated_text='Hola mundo',
            source_language='en',
            target_language='es',
            applied_terminologies=[],
        )
        orchestrator.translation_service.translate_text.return_value = translation_result

        # Mock low quality validation
        validation_result = ValidationResult(
            is_valid=True,
            quality_score=0.5,
            issues=['Low quality'],
            suggestions=['Improve translation'],
        )
        orchestrator.translation_service.validate_translation.return_value = validation_result

        result = await orchestrator.smart_translate_workflow(
            text='Hello world',
            target_language='es',
            quality_threshold=0.8,  # Higher than actual quality
        )

        # Should still complete but with quality warning
        assert result.quality_score == 0.5
        assert len(result.validation_issues) == 1
        assert 'Low quality' in result.validation_issues

    @pytest.mark.asyncio
    async def test_smart_translate_workflow_translation_error(self, orchestrator):
        """Test workflow with translation service error."""
        # Mock language detection
        detection_result = LanguageDetectionResult(
            detected_language='en', confidence_score=0.95, alternative_languages=[]
        )
        orchestrator.translation_service.detect_language.return_value = detection_result

        # Mock language pairs
        language_pairs = [
            LanguagePair(
                source_language='en', target_language='es', supported_formats=['text/plain']
            )
        ]
        orchestrator.language_operations.list_language_pairs.return_value = language_pairs

        # Mock translation error
        orchestrator.translation_service.translate_text.side_effect = TranslationError(
            'Translation service error'
        )

        with pytest.raises(TranslationError) as exc_info:
            await orchestrator.smart_translate_workflow(
                text='Hello world', target_language='es', quality_threshold=0.8
            )

        assert 'Translation service error' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_smart_translate_workflow_validation_error(self, orchestrator):
        """Test workflow with validation service error."""
        # Mock successful detection, language pairs, and translation
        detection_result = LanguageDetectionResult(
            detected_language='en', confidence_score=0.95, alternative_languages=[]
        )
        orchestrator.translation_service.detect_language.return_value = detection_result

        language_pairs = [
            LanguagePair(
                source_language='en', target_language='es', supported_formats=['text/plain']
            )
        ]
        orchestrator.language_operations.list_language_pairs.return_value = language_pairs

        translation_result = TranslationResult(
            translated_text='Hola mundo',
            source_language='en',
            target_language='es',
            applied_terminologies=[],
        )
        orchestrator.translation_service.translate_text.return_value = translation_result

        # Mock validation error
        orchestrator.translation_service.validate_translation.side_effect = ValidationError(
            'Validation service error'
        )

        with pytest.raises(ValidationError) as exc_info:
            await orchestrator.smart_translate_workflow(
                text='Hello world', target_language='es', quality_threshold=0.8
            )

        assert 'Validation service error' in str(exc_info.value)


class TestBatchTranslationWorkflowComprehensive:
    """Comprehensive tests for batch translation workflow."""

    @pytest.fixture
    def orchestrator(self):
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
    async def test_managed_batch_translation_workflow_success(self, orchestrator):
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
        orchestrator.language_operations.list_language_pairs.return_value = language_pairs

        # Mock terminology validation
        orchestrator.terminology_manager.list_terminologies.return_value = {
            'terminologies': [],
            'next_token': None,
        }

        # Mock batch job start
        orchestrator.batch_manager.start_batch_translation.return_value = 'job-123'

        # Mock job monitoring - simulate job progression
        job_statuses = [
            TranslationJobStatus(
                job_id='job-123',
                job_name='test-job',
                status='SUBMITTED',
                progress=0.0,
                created_at=datetime.now(),
            ),
            TranslationJobStatus(
                job_id='job-123',
                job_name='test-job',
                status='IN_PROGRESS',
                progress=50.0,
                created_at=datetime.now(),
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
        orchestrator.batch_manager.get_translation_job.side_effect = job_statuses

        # Mock language metrics
        mock_metrics = LanguageMetrics(
            language_pair='en-es',
            time_range='24h',
            translation_count=100,
            character_count=5000,
            average_response_time=150.0,
        )
        orchestrator.language_operations.get_language_metrics.return_value = mock_metrics

        # Execute workflow
        result = await orchestrator.managed_batch_translation_workflow(
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
    async def test_managed_batch_translation_workflow_with_terminology(self, orchestrator):
        """Test workflow with terminology validation."""
        # Mock language pairs
        language_pairs = [
            LanguagePair(
                source_language='en', target_language='es', supported_formats=['text/plain']
            )
        ]
        orchestrator.language_operations.list_language_pairs.return_value = language_pairs

        # Mock terminology validation - terminology exists
        mock_terminology = TerminologyDetails(
            name='tech-terms',
            description='Technical terms',
            source_language='en',
            target_languages=['es'],
            term_count=100,
            created_at=datetime.now(),
        )
        orchestrator.terminology_manager.list_terminologies.return_value = {
            'terminologies': [mock_terminology],
            'next_token': None,
        }

        # Mock batch job
        orchestrator.batch_manager.start_batch_translation.return_value = 'job-456'
        orchestrator.batch_manager.get_translation_job.return_value = TranslationJobStatus(
            job_id='job-456',
            job_name='test-job',
            status='COMPLETED',
            progress=100.0,
            created_at=datetime.now(),
            completed_at=datetime.now(),
        )

        # Mock metrics
        mock_metrics = LanguageMetrics(
            language_pair='en-es',
            time_range='24h',
            translation_count=50,
            character_count=2500,
            average_response_time=120.0,
        )
        orchestrator.language_operations.get_language_metrics.return_value = mock_metrics

        result = await orchestrator.managed_batch_translation_workflow(
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
    async def test_managed_batch_translation_workflow_failed_job(self, orchestrator):
        """Test workflow with failed batch job and error analysis."""
        # Mock validations
        language_pairs = [
            LanguagePair(
                source_language='en', target_language='es', supported_formats=['text/plain']
            )
        ]
        orchestrator.language_operations.list_language_pairs.return_value = language_pairs
        orchestrator.terminology_manager.list_terminologies.return_value = {
            'terminologies': [],
            'next_token': None,
        }

        # Mock batch job that fails
        orchestrator.batch_manager.start_batch_translation.return_value = 'failed-job-789'
        orchestrator.batch_manager.get_translation_job.return_value = TranslationJobStatus(
            job_id='failed-job-789',
            job_name='failed-job',
            status='FAILED',
            progress=25.0,
            created_at=datetime.now(),
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

        with patch.object(orchestrator, '_analyze_job_errors', return_value=mock_error_analysis):
            result = await orchestrator.managed_batch_translation_workflow(
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

    @pytest.mark.asyncio
    async def test_managed_batch_translation_workflow_unsupported_language_pair(
        self, orchestrator
    ):
        """Test workflow with unsupported language pair."""
        # Mock empty language pairs (unsupported)
        orchestrator.language_operations.list_language_pairs.return_value = []

        with pytest.raises(ValidationError) as exc_info:
            await orchestrator.managed_batch_translation_workflow(
                input_s3_uri='s3://bucket/input/',
                output_s3_uri='s3://bucket/output/',
                data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
                job_name='test-job',
                source_language='en',
                target_languages=['xx'],  # Unsupported
                monitor_interval=1,
                max_monitoring_duration=5,
            )

        assert "Unsupported language pairs: ['en->xx']" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_managed_batch_translation_workflow_invalid_terminology(self, orchestrator):
        """Test workflow with invalid terminology."""
        # Mock language pairs
        language_pairs = [
            LanguagePair(
                source_language='en', target_language='es', supported_formats=['text/plain']
            )
        ]
        orchestrator.language_operations.list_language_pairs.return_value = language_pairs

        # Mock terminology validation - terminology doesn't exist
        orchestrator.terminology_manager.list_terminologies.return_value = {
            'terminologies': [],  # Empty - terminology not found
            'next_token': None,
        }

        with pytest.raises(ValidationError) as exc_info:
            await orchestrator.managed_batch_translation_workflow(
                input_s3_uri='s3://bucket/input/',
                output_s3_uri='s3://bucket/output/',
                data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
                job_name='test-job',
                source_language='en',
                target_languages=['es'],
                terminology_names=['nonexistent-terminology'],
                monitor_interval=1,
                max_monitoring_duration=5,
            )

        assert "Missing terminologies: ['nonexistent-terminology']" in str(exc_info.value)


class TestWorkflowStateManagement:
    """Test workflow state management functionality."""

    @pytest.fixture
    def orchestrator(self):
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

    def test_get_workflow_status_existing(self, orchestrator):
        """Test getting status of existing workflow."""
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
        orchestrator._active_workflows[workflow_id] = context

        status = orchestrator.get_workflow_status(workflow_id)

        assert status is not None
        assert status['workflow_id'] == workflow_id
        assert status['workflow_type'] == 'smart_translation'
        assert status['current_step'] == 'translate_text'
        assert len(status['completed_steps']) == 1

    def test_get_workflow_status_nonexistent(self, orchestrator):
        """Test getting status of non-existent workflow."""
        status = orchestrator.get_workflow_status('nonexistent-workflow')
        assert status is None

    def test_list_active_workflows(self, orchestrator):
        """Test listing active workflows."""
        # Add multiple workflows
        for i in range(3):
            workflow_id = f'workflow-{i}'
            context = WorkflowContext(
                workflow_id=workflow_id,
                workflow_type='smart_translation',
                started_at=datetime.now(),
                current_step=f'step-{i}',
            )
            orchestrator._active_workflows[workflow_id] = context

        active_workflows = orchestrator.list_active_workflows()

        assert len(active_workflows) == 3
        assert all(
            workflow['workflow_id'].startswith('workflow-') for workflow in active_workflows
        )

    def test_get_workflow_result(self, orchestrator):
        """Test getting workflow result."""
        workflow_id = 'completed-workflow-456'
        mock_result = {'status': 'completed', 'result': 'success'}

        orchestrator._workflow_results[workflow_id] = mock_result

        result = orchestrator.get_workflow_result(workflow_id)
        assert result == mock_result

        # Test non-existent result
        nonexistent_result = orchestrator.get_workflow_result('nonexistent')
        assert nonexistent_result is None

    def test_cleanup_old_results(self, orchestrator):
        """Test cleanup of old workflow results."""
        # Add some workflow results with timestamp-based IDs
        current_time = int(time.time() * 1000)
        old_time = current_time - (25 * 60 * 60 * 1000)  # 25 hours ago

        orchestrator._workflow_results[f'old_workflow_{old_time}'] = {'old': True}
        orchestrator._workflow_results[f'new_workflow_{current_time}'] = {'new': True}
        orchestrator._workflow_results['invalid_format'] = {'invalid': True}

        cleaned_count = orchestrator.cleanup_old_results(max_age_hours=24)

        assert cleaned_count == 1  # Only the old one should be cleaned
        assert f'old_workflow_{old_time}' not in orchestrator._workflow_results
        assert f'new_workflow_{current_time}' in orchestrator._workflow_results
        assert 'invalid_format' in orchestrator._workflow_results  # Invalid format preserved


class TestErrorAnalysisComprehensive:
    """Comprehensive tests for error analysis functionality."""

    @pytest.fixture
    def orchestrator(self):
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
    async def test_analyze_job_errors_success(self, orchestrator):
        """Test successful error analysis."""
        # Mock S3 responses
        s3_client = orchestrator.batch_manager.s3_client

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
            result = await orchestrator._analyze_job_errors('job-123', 's3://bucket/output/', loop)

        assert result is not None
        assert result['job_id'] == 'job-123'
        assert len(result['error_files_found']) == 2
        assert len(result['suggested_actions']) > 0

    @pytest.mark.asyncio
    async def test_analyze_job_errors_no_details_folder(self, orchestrator):
        """Test error analysis when no details folder exists."""
        s3_client = orchestrator.batch_manager.s3_client

        # Mock no job folder found
        s3_client.list_objects_v2.return_value = {}

        loop = asyncio.get_event_loop()
        result = await orchestrator._analyze_job_errors(
            'nonexistent-job', 's3://bucket/output/', loop
        )

        assert result is None

    def test_generate_error_suggestions_utf8_error(self, orchestrator):
        """Test error suggestion generation for UTF-8 errors."""
        error_data = {'errorMessage': 'Invalid utf-8 encoded texts detected'}

        suggestions = orchestrator._generate_error_suggestions(error_data)

        assert len(suggestions) > 0
        # Check for encoding-related suggestions
        suggestion_text = ' '.join(suggestions).lower()
        assert any(keyword in suggestion_text for keyword in ['encoding', 'utf-8', 'format'])

    def test_generate_error_suggestions_permission_error(self, orchestrator):
        """Test error suggestion generation for permission errors."""
        error_data = {'errorMessage': 'Access denied to S3 bucket'}

        suggestions = orchestrator._generate_error_suggestions(error_data)

        assert len(suggestions) > 0
        suggestion_text = ' '.join(suggestions).lower()
        assert any(keyword in suggestion_text for keyword in ['permission', 'access', 'iam'])

    def test_generate_error_suggestions_language_error(self, orchestrator):
        """Test error suggestion generation for language errors."""
        error_data = {'errorMessage': 'Unsupported language pair detected'}

        suggestions = orchestrator._generate_error_suggestions(error_data)

        assert len(suggestions) > 0
        suggestion_text = ' '.join(suggestions).lower()
        assert 'language' in suggestion_text

    def test_generate_error_suggestions_size_error(self, orchestrator):
        """Test error suggestion generation for size limit errors."""
        error_data = {'errorMessage': 'File size exceeds the limit'}

        suggestions = orchestrator._generate_error_suggestions(error_data)

        assert len(suggestions) > 0
        suggestion_text = ' '.join(suggestions).lower()
        assert any(keyword in suggestion_text for keyword in ['size', 'split', 'limit'])

    def test_generate_error_suggestions_generic_error(self, orchestrator):
        """Test error suggestion generation for generic errors."""
        error_data = {'errorMessage': 'Unknown processing error'}

        suggestions = orchestrator._generate_error_suggestions(error_data)

        assert len(suggestions) > 0
        # Should provide generic suggestions
        suggestion_text = ' '.join(suggestions).lower()
        assert any(keyword in suggestion_text for keyword in ['check', 'verify', 'review'])


class TestWorkflowResultClasses:
    """Test workflow result dataclasses."""

    def test_smart_translation_workflow_result_creation(self):
        """Test SmartTranslationWorkflowResult creation."""
        result = SmartTranslationWorkflowResult(
            original_text='Hello world',
            translated_text='Hola mundo',
            detected_language='en',
            target_language='es',
            confidence_score=0.95,
            quality_score=0.92,
            applied_terminologies=['tech-terms'],
            language_pair_supported=True,
            validation_issues=[],
            suggestions=['Great translation!'],
            execution_time_ms=150.0,
            workflow_steps=['detect_language', 'translate_text', 'validate_translation'],
        )

        assert result.original_text == 'Hello world'
        assert result.translated_text == 'Hola mundo'
        assert result.detected_language == 'en'
        assert result.target_language == 'es'
        assert result.confidence_score == 0.95
        assert result.quality_score == 0.92
        assert result.applied_terminologies == ['tech-terms']
        assert result.language_pair_supported is True
        assert len(result.suggestions) == 1
        assert result.execution_time_ms == 150.0
        assert len(result.workflow_steps) == 3

    def test_batch_translation_workflow_result_creation(self):
        """Test BatchTranslationWorkflowResult creation."""
        created_at = datetime.now()
        completed_at = datetime.now()

        result = BatchTranslationWorkflowResult(
            job_id='job-123',
            job_name='test-job',
            status='COMPLETED',
            source_language='en',
            target_languages=['es', 'fr'],
            input_s3_uri='s3://bucket/input/',
            output_s3_uri='s3://bucket/output/',
            terminology_names=['tech-terms'],
            pre_validation_results={'supported_pairs': ['en->es', 'en->fr']},
            monitoring_history=[{'status': 'IN_PROGRESS', 'progress': 50.0}],
            performance_metrics={'total_monitoring_time': 300.0},
            created_at=created_at,
            completed_at=completed_at,
            total_execution_time=300.0,
            workflow_steps=['validate_language_pairs', 'start_batch_job', 'monitor_job_progress'],
        )

        assert result.job_id == 'job-123'
        assert result.job_name == 'test-job'
        assert result.status == 'COMPLETED'
        assert result.source_language == 'en'
        assert result.target_languages == ['es', 'fr']
        assert result.input_s3_uri == 's3://bucket/input/'
        assert result.output_s3_uri == 's3://bucket/output/'
        assert result.terminology_names == ['tech-terms']
        assert len(result.monitoring_history) == 1
        assert result.total_execution_time == 300.0
        assert len(result.workflow_steps) == 3
