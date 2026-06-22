"""Comprehensive tests for MCP Server Tools.

This module contains tests that directly test the server tool functions
to achieve high coverage of the server.py module.
"""

import pytest
from awslabs.amazon_translate_mcp_server import server
from awslabs.amazon_translate_mcp_server.exceptions import (
    TranslationError,
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
)
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch


class TestServerToolsExecution:
    """Test actual execution of server tools with mocked services."""

    @pytest.fixture(autouse=True)
    def setup_services(self):
        """Set up mock services for all tests."""
        with (
            patch.object(server, 'translation_service') as mock_trans,
            patch.object(server, 'batch_manager') as mock_batch,
            patch.object(server, 'terminology_manager') as mock_term,
            patch.object(server, 'language_operations') as mock_lang,
            patch.object(server, 'workflow_orchestrator') as mock_workflow,
        ):
            self.mock_services = {
                'translation': mock_trans,
                'batch': mock_batch,
                'terminology': mock_term,
                'language': mock_lang,
                'workflow': mock_workflow,
            }
            yield

    @pytest.mark.asyncio
    async def test_translate_text_tool_success(self):
        """Test translate_text tool execution."""
        # Mock translation result
        mock_result = TranslationResult(
            translated_text='Hola mundo',
            source_language='en',
            target_language='es',
            applied_terminologies=['tech-terms'],
            confidence_score=0.95,
        )
        self.mock_services['translation'].translate_text.return_value = mock_result

        # Execute the actual tool function
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_executor = AsyncMock()
            mock_executor.return_value = mock_result
            mock_loop.return_value.run_in_executor = mock_executor

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            # Call the function directly
            result = await server.translate_text(
                ctx=mock_ctx,
                text='Hello world',
                source_language='en',
                target_language='es',
                terminology_names=['tech-terms'],
            )

        # Verify result
        assert result['translated_text'] == 'Hola mundo'
        assert result['source_language'] == 'en'
        assert result['target_language'] == 'es'
        assert result['applied_terminologies'] == ['tech-terms']
        assert result['confidence_score'] == 0.95
        assert 'error' not in result

    @pytest.mark.asyncio
    async def test_translate_text_tool_service_not_initialized(self):
        """Test translate_text when service is not initialized."""
        # Temporarily set service to None
        original_service = server.translation_service
        server.translation_service = None

        try:
            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.translate_text(
                ctx=mock_ctx, text='Hello world', source_language='en', target_language='es'
            )

            assert 'error' in result
            assert 'Translation service not initialized' in result['error']
            assert result['error_type'] == 'TranslationError'
        finally:
            server.translation_service = original_service

    @pytest.mark.asyncio
    async def test_translate_text_tool_exception_handling(self):
        """Test translate_text exception handling."""
        self.mock_services['translation'].translate_text.side_effect = TranslationError(
            'Translation failed'
        )

        with patch('asyncio.get_event_loop') as mock_loop:
            mock_executor = AsyncMock()
            mock_executor.side_effect = TranslationError('Translation failed')
            mock_loop.return_value.run_in_executor = mock_executor

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.translate_text(
                ctx=mock_ctx, text='Hello world', source_language='en', target_language='es'
            )

        assert 'error' in result
        assert 'Translation failed' in result['error']
        assert result['error_type'] == 'TranslationError'

    @pytest.mark.asyncio
    async def test_detect_language_tool_success(self):
        """Test detect_language tool execution."""
        mock_result = LanguageDetectionResult(
            detected_language='en',
            confidence_score=0.95,
            alternative_languages=[('fr', 0.03), ('de', 0.02)],
        )

        with patch('asyncio.get_event_loop') as mock_loop:
            mock_executor = AsyncMock()
            mock_executor.return_value = mock_result
            mock_loop.return_value.run_in_executor = mock_executor

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.detect_language(ctx=mock_ctx, text='Hello world')

        assert result['detected_language'] == 'en'
        assert result['confidence_score'] == 0.95
        assert len(result['alternative_languages']) == 2
        assert 'error' not in result

    @pytest.mark.asyncio
    async def test_detect_language_tool_service_not_initialized(self):
        """Test detect_language when service is not initialized."""
        original_service = server.translation_service
        server.translation_service = None

        try:
            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.detect_language(ctx=mock_ctx, text='Hello world')

            assert 'error' in result
            assert 'Translation service not initialized' in result['error']
        finally:
            server.translation_service = original_service

    @pytest.mark.asyncio
    async def test_validate_translation_tool_success(self):
        """Test validate_translation tool execution."""
        mock_result = ValidationResult(
            is_valid=True, quality_score=0.92, issues=[], suggestions=['Great translation!']
        )

        with patch('asyncio.get_event_loop') as mock_loop:
            mock_executor = AsyncMock()
            mock_executor.return_value = mock_result
            mock_loop.return_value.run_in_executor = mock_executor

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.validate_translation(
                ctx=mock_ctx,
                original_text='Hello world',
                translated_text='Hola mundo',
                source_language='en',
                target_language='es',
            )

        assert result['is_valid'] is True
        assert result['quality_score'] == 0.92
        assert len(result['suggestions']) == 1
        assert 'error' not in result

    @pytest.mark.asyncio
    async def test_start_batch_translation_tool_success(self):
        """Test start_batch_translation tool execution."""
        self.mock_services['batch'].start_batch_translation.return_value = 'job-123'

        with patch('asyncio.get_event_loop') as mock_loop:
            mock_executor = AsyncMock()
            mock_executor.return_value = 'job-123'
            mock_loop.return_value.run_in_executor = mock_executor

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.start_batch_translation(
                ctx=mock_ctx,
                input_s3_uri='s3://bucket/input/',
                output_s3_uri='s3://bucket/output/',
                data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
                job_name='test-job',
                source_language='en',
                target_languages=['es', 'fr'],
            )

        assert result['job_id'] == 'job-123'
        assert result['status'] == 'SUBMITTED'
        assert result['message'] == 'Batch translation job started successfully'
        assert 'error' not in result

    @pytest.mark.asyncio
    async def test_get_translation_job_tool_success(self):
        """Test get_translation_job tool execution."""
        mock_job = TranslationJobStatus(
            job_id='job-123',
            job_name='test-job',
            status='COMPLETED',
            progress=100.0,
            created_at=datetime.now(),
            completed_at=datetime.now(),
        )

        with patch('asyncio.get_event_loop') as mock_loop:
            mock_executor = AsyncMock()
            mock_executor.return_value = mock_job
            mock_loop.return_value.run_in_executor = mock_executor

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.get_translation_job(ctx=mock_ctx, job_id='job-123')

        assert result['job_id'] == 'job-123'
        assert result['job_name'] == 'test-job'
        assert result['status'] == 'COMPLETED'
        assert result['progress'] == 100.0
        assert 'error' not in result

    @pytest.mark.asyncio
    async def test_list_translation_jobs_tool_success(self):
        """Test list_translation_jobs tool execution."""
        from awslabs.amazon_translate_mcp_server.models import TranslationJobSummary

        mock_jobs = [
            TranslationJobSummary(
                job_id='job-1',
                job_name='test-job-1',
                status='COMPLETED',
                source_language_code='en',
                target_language_codes=['es'],
                created_at=datetime.now(),
            ),
            TranslationJobSummary(
                job_id='job-2',
                job_name='test-job-2',
                status='IN_PROGRESS',
                source_language_code='en',
                target_language_codes=['fr'],
                created_at=datetime.now(),
            ),
        ]

        with patch('asyncio.get_event_loop') as mock_loop:
            mock_executor = AsyncMock()
            mock_executor.return_value = mock_jobs
            mock_loop.return_value.run_in_executor = mock_executor

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.list_translation_jobs(ctx=mock_ctx, max_results=10)

        assert result['total_count'] == 2
        assert len(result['jobs']) == 2
        assert result['jobs'][0]['job_id'] == 'job-1'
        assert result['jobs'][1]['status'] == 'IN_PROGRESS'
        assert 'error' not in result

    @pytest.mark.asyncio
    async def test_list_terminologies_tool_success(self):
        """Test list_terminologies tool execution."""
        mock_terminologies = [
            TerminologyDetails(
                name='tech-terms',
                description='Technical terminology',
                source_language='en',
                target_languages=['es', 'fr'],
                term_count=100,
                created_at=datetime.now(),
            )
        ]

        with patch('asyncio.get_event_loop') as mock_loop:
            mock_executor = AsyncMock()
            mock_executor.return_value = {'terminologies': mock_terminologies, 'next_token': None}
            mock_loop.return_value.run_in_executor = mock_executor

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.list_terminologies(ctx=mock_ctx)

        assert result['total_count'] == 1
        assert len(result['terminologies']) == 1
        assert result['terminologies'][0]['name'] == 'tech-terms'
        assert result['terminologies'][0]['term_count'] == 100
        assert 'error' not in result

    @pytest.mark.asyncio
    async def test_create_terminology_tool_success(self):
        """Test create_terminology tool execution."""
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_executor = AsyncMock()
            mock_executor.return_value = {
                'name': 'new-terminology',
                'status': 'ACTIVE',
                'term_count': 1,
            }
            mock_loop.return_value.run_in_executor = mock_executor

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.create_terminology(
                ctx=mock_ctx,
                name='new-terminology',
                description='New terminology',
                source_language='en',
                target_languages=['es', 'fr'],
                terms=[
                    {'source': 'hello', 'target': 'hola'},
                    {'source': 'world', 'target': 'mundo'},
                ],
            )

        assert result['name'] == 'new-terminology'
        assert result['status'] == 'CREATED'
        assert result['message'] == 'Terminology created successfully'
        assert 'error' not in result

    @pytest.mark.asyncio
    async def test_import_terminology_tool_success(self):
        """Test import_terminology tool execution."""
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_executor = AsyncMock()
            mock_executor.return_value = {
                'name': 'imported-terminology',
                'status': 'IMPORTING',
                'import_job_id': 'import-123',
            }
            mock_loop.return_value.run_in_executor = mock_executor

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.import_terminology(
                ctx=mock_ctx,
                name='imported-terminology',
                description='Imported terminology',
                source_language='en',
                target_languages=['es'],
                file_content='aGVsbG8saG9sYQ==',  # base64 encoded "hello,hola"
                file_format='CSV',
            )

        assert result['name'] == 'imported-terminology'
        assert result['status'] == 'IMPORTED'
        assert result['message'] == 'Terminology imported successfully'
        assert 'error' not in result

    @pytest.mark.asyncio
    async def test_get_terminology_tool_success(self):
        """Test get_terminology tool execution."""
        from awslabs.amazon_translate_mcp_server.models import TerminologyDetails

        mock_terminology = TerminologyDetails(
            name='tech-terms',
            description='Technical terms',
            source_language='en',
            target_languages=['es', 'fr'],
            term_count=100,
            created_at=datetime.now(),
        )

        with patch('asyncio.get_event_loop') as mock_loop:
            mock_executor = AsyncMock()
            mock_executor.return_value = mock_terminology
            mock_loop.return_value.run_in_executor = mock_executor

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.get_terminology(ctx=mock_ctx, name='tech-terms')

        assert result['name'] == 'tech-terms'
        assert result['description'] == 'Technical terms'
        assert result['term_count'] == 100
        assert 'error' not in result

    @pytest.mark.asyncio
    async def test_list_language_pairs_tool_success(self):
        """Test list_language_pairs tool execution."""
        mock_pairs = [
            LanguagePair(
                source_language='en',
                target_language='es',
                supported_formats=['text/plain', 'text/html'],
            ),
            LanguagePair(
                source_language='en', target_language='fr', supported_formats=['text/plain']
            ),
        ]

        with patch('asyncio.get_event_loop') as mock_loop:
            mock_executor = AsyncMock()
            mock_executor.return_value = mock_pairs
            mock_loop.return_value.run_in_executor = mock_executor

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.list_language_pairs(ctx=mock_ctx)

        assert result['total_count'] == 2
        assert len(result['language_pairs']) == 2
        assert result['language_pairs'][0]['source_language'] == 'en'
        assert result['language_pairs'][0]['target_language'] == 'es'
        assert 'error' not in result

    @pytest.mark.asyncio
    async def test_get_language_metrics_tool_success(self):
        """Test get_language_metrics tool execution."""
        mock_metrics = LanguageMetrics(
            language_pair='en-es',
            time_range='24h',
            translation_count=100,
            character_count=5000,
            average_response_time=150.0,
            error_rate=0.02,
        )

        with patch('asyncio.get_event_loop') as mock_loop:
            mock_executor = AsyncMock()
            mock_executor.return_value = mock_metrics
            mock_loop.return_value.run_in_executor = mock_executor

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.get_language_metrics(
                ctx=mock_ctx, language_pair='en-es', time_range='24h'
            )

        assert result['language_pair'] == 'en-es'
        assert result['translation_count'] == 100
        assert result['error_rate'] == 0.02
        assert 'error' not in result


class TestWorkflowTools:
    """Test workflow orchestration tools."""

    @pytest.fixture(autouse=True)
    def setup_workflow_services(self):
        """Set up mock workflow services."""
        with patch.object(server, 'workflow_orchestrator') as mock_workflow:
            self.mock_workflow = mock_workflow
            yield

    @pytest.mark.asyncio
    async def test_smart_translate_workflow_tool_success(self):
        """Test smart_translate_workflow tool execution."""
        mock_result = SmartTranslationWorkflowResult(
            original_text='Hello world',
            translated_text='Hola mundo',
            detected_language='en',
            target_language='es',
            confidence_score=0.95,
            quality_score=0.92,
            applied_terminologies=[],
            language_pair_supported=True,
            validation_issues=[],
            suggestions=[],
            execution_time_ms=150.0,
            workflow_steps=['detect_language', 'translate_text', 'validate_translation'],
        )

        with patch.object(server, 'workflow_orchestrator') as mock_workflow:
            mock_workflow.smart_translate_workflow = AsyncMock(return_value=mock_result)

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.smart_translate_workflow(
                ctx=mock_ctx, text='Hello world', target_language='es', quality_threshold=0.8
            )

        assert result['workflow_type'] == 'smart_translation'
        assert result['translated_text'] == 'Hola mundo'
        assert result['confidence_score'] == 0.95
        assert result['quality_score'] == 0.92
        assert len(result['workflow_steps']) == 3
        assert 'error' not in result

    @pytest.mark.asyncio
    async def test_managed_batch_translation_workflow_tool_success(self):
        """Test managed_batch_translation_workflow tool execution."""
        mock_result = BatchTranslationWorkflowResult(
            job_id='job-123',
            job_name='test-workflow-job',
            status='COMPLETED',
            source_language='en',
            target_languages=['es', 'fr'],
            input_s3_uri='s3://bucket/input/',
            output_s3_uri='s3://bucket/output/',
            terminology_names=[],
            pre_validation_results={'supported_pairs': ['en->es', 'en->fr']},
            monitoring_history=[],
            performance_metrics={'total_monitoring_time': 300.0},
            created_at=datetime.now(),
            completed_at=datetime.now(),
            total_execution_time=300.0,
            workflow_steps=['validate_language_pairs', 'start_batch_job', 'monitor_job_progress'],
        )

        with patch.object(server, 'workflow_orchestrator') as mock_workflow:
            mock_workflow.managed_batch_translation_workflow = AsyncMock(return_value=mock_result)

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.managed_batch_translation_workflow(
                ctx=mock_ctx,
                input_s3_uri='s3://bucket/input/',
                output_s3_uri='s3://bucket/output/',
                data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
                job_name='test-workflow-job',
                source_language='en',
                target_languages=['es', 'fr'],
            )

        assert result['workflow_type'] == 'managed_batch_translation'
        assert result['job_id'] == 'job-123'
        assert result['status'] == 'COMPLETED'
        assert len(result['workflow_steps']) == 3
        assert 'error' not in result

    @pytest.mark.asyncio
    async def test_list_active_workflows_tool_success(self):
        """Test list_active_workflows tool execution."""
        mock_workflows = [
            {
                'workflow_id': 'workflow-1',
                'workflow_type': 'smart_translation',
                'current_step': 'translate_text',
                'started_at': datetime.now().isoformat(),
            }
        ]

        with patch.object(server, 'workflow_orchestrator') as mock_workflow:
            mock_workflow.list_active_workflows.return_value = mock_workflows

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.list_active_workflows(ctx=mock_ctx)

        assert result['total_count'] == 1
        assert len(result['workflows']) == 1
        assert result['workflows'][0]['workflow_id'] == 'workflow-1'
        assert 'error' not in result


class TestSeparateBatchTools:
    """Test separate batch translation tools."""

    @pytest.fixture(autouse=True)
    def setup_batch_services(self):
        """Set up mock services for batch tools."""
        with (
            patch.object(server, 'workflow_orchestrator') as mock_workflow,
            patch.object(server, 'batch_manager') as mock_batch,
            patch.object(server, 'language_operations') as mock_lang,
            patch.object(server, 'terminology_manager') as mock_term,
        ):
            self.mock_services = {
                'workflow': mock_workflow,
                'batch': mock_batch,
                'language': mock_lang,
                'terminology': mock_term,
            }
            yield

    @pytest.mark.asyncio
    async def test_trigger_batch_translation_tool_success(self):
        """Test trigger_batch_translation tool execution."""
        # Mock language pairs validation
        mock_pairs = [
            LanguagePair(
                source_language='en', target_language='es', supported_formats=['text/plain']
            )
        ]

        # Mock batch job start
        mock_job_status = TranslationJobStatus(
            job_id='job-456',
            job_name='test-trigger-job',
            status='SUBMITTED',
            progress=0.0,
            created_at=datetime.now(),
        )

        with patch('asyncio.get_event_loop') as mock_loop:
            # Mock the validation and job creation
            mock_executor = AsyncMock()
            mock_executor.side_effect = [
                mock_pairs,  # list_language_pairs
                'job-456',  # start_batch_translation
                mock_job_status,  # get_translation_job
            ]
            mock_loop.return_value.run_in_executor = mock_executor

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.trigger_batch_translation(
                ctx=mock_ctx,
                input_s3_uri='s3://bucket/input/',
                output_s3_uri='s3://bucket/output/',
                data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
                job_name='test-trigger-job',
                source_language='en',
                target_languages=['es'],
                terminology_names=None,
            )

        assert result['job_id'] == 'job-456'
        assert result['status'] == 'SUBMITTED'
        assert 'validation_results' in result
        assert 'message' in result
        assert 'error' not in result

    @pytest.mark.asyncio
    async def test_monitor_batch_translation_tool_success(self):
        """Test monitor_batch_translation tool execution."""
        # Mock job status progression
        job_statuses = [
            TranslationJobStatus(
                job_id='job-456',
                job_name='test-job',
                status='IN_PROGRESS',
                progress=25.0,
                created_at=datetime.now(),
            ),
            TranslationJobStatus(
                job_id='job-456',
                job_name='test-job',
                status='IN_PROGRESS',
                progress=50.0,
                created_at=datetime.now(),
            ),
            TranslationJobStatus(
                job_id='job-456',
                job_name='test-job',
                status='COMPLETED',
                progress=100.0,
                created_at=datetime.now(),
                completed_at=datetime.now(),
            ),
        ]

        with (
            patch('asyncio.get_event_loop') as mock_loop,
            patch('asyncio.sleep', new_callable=AsyncMock),
        ):
            mock_executor = AsyncMock()
            mock_executor.side_effect = job_statuses
            mock_loop.return_value.run_in_executor = mock_executor

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.monitor_batch_translation(
                ctx=mock_ctx,
                job_id='job-456',
                output_s3_uri='s3://bucket/output/',
                monitor_interval=1,
                max_monitoring_duration=10,
            )

        assert result['job_id'] == 'job-456'
        assert result['final_status'] == 'COMPLETED'
        assert 'monitoring_history' in result
        assert 'performance_metrics' in result
        assert 'error' not in result

    @pytest.mark.asyncio
    async def test_analyze_batch_translation_errors_tool_success(self):
        """Test analyze_batch_translation_errors tool execution."""
        mock_error_analysis = {
            'job_id': 'failed-job-123',
            'error_files_found': ['error1.json', 'error2.json'],
            'error_details': [
                {
                    'file': 'error1.json',
                    'error_data': {
                        'sourceLanguageCode': 'en',
                        'targetLanguageCode': 'es',
                        'documentCountWithCustomerError': '1',
                    },
                }
            ],
            'suggested_actions': ['Check file encoding', 'Verify file format'],
        }

        with patch.object(server, 'workflow_orchestrator') as mock_workflow:
            mock_workflow._analyze_job_errors = AsyncMock(return_value=mock_error_analysis)

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.analyze_batch_translation_errors(
                ctx=mock_ctx, job_id='failed-job-123', output_s3_uri='s3://bucket/output/'
            )

        assert result['job_id'] == 'failed-job-123'
        assert len(result['error_files_found']) == 2
        assert len(result['suggested_actions']) == 2
        assert 'error_summary' in result
        assert 'error' not in result


class TestHealthCheckAndUtilities:
    """Test health check and utility functions."""

    def test_health_check_all_services_healthy(self):
        """Test health check when all services are healthy."""
        with (
            patch.object(server, 'aws_client_manager') as mock_aws,
            patch.object(server, 'translation_service'),
            patch.object(server, 'batch_manager'),
            patch.object(server, 'terminology_manager'),
            patch.object(server, 'language_operations'),
            patch.object(server, 'workflow_orchestrator'),
        ):
            # Mock successful credential validation
            mock_aws.validate_credentials.return_value = None

            result = server.health_check()

            assert result['status'] == 'healthy'
            assert result['components']['aws_client'] == 'healthy'
            assert result['components']['translation_service'] == 'healthy'
            assert result['components']['batch_manager'] == 'healthy'
            assert result['components']['terminology_manager'] == 'healthy'
            assert result['components']['language_operations'] == 'healthy'

            assert result['components']['workflow_orchestrator'] == 'healthy'

    def test_health_check_aws_client_unhealthy(self):
        """Test health check when AWS client is unhealthy."""
        with patch.object(server, 'aws_client_manager') as mock_aws:
            mock_aws.validate_credentials.side_effect = Exception('Credential error')
            server.translation_service = None
            server.batch_manager = None
            server.terminology_manager = None
            server.language_operations = None

            server.workflow_orchestrator = None

            result = server.health_check()

            assert result['status'] == 'unhealthy'
            assert 'Credential error' in result['components']['aws_client']
            assert result['components']['translation_service'] == 'not_initialized'
            assert result['components']['batch_manager'] == 'not_initialized'

    def test_health_check_mixed_service_states(self):
        """Test health check with mixed service states."""
        with patch.object(server, 'aws_client_manager') as mock_aws:
            mock_aws.validate_credentials.return_value = None

            # Set some services to None
            server.translation_service = Mock()
            server.batch_manager = None
            server.terminology_manager = Mock()
            server.language_operations = None

            server.workflow_orchestrator = Mock()

            result = server.health_check()

            assert result['status'] == 'degraded'
            assert result['components']['aws_client'] == 'healthy'
            assert result['components']['translation_service'] == 'healthy'
            assert result['components']['batch_manager'] == 'not_initialized'
            assert result['components']['terminology_manager'] == 'healthy'
            assert result['components']['language_operations'] == 'not_initialized'
