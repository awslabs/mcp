"""Comprehensive async tests for MCP Server to improve coverage from 75% to 95%.

This module contains comprehensive async tests for all MCP server tools,
focusing on the missing coverage areas identified in server.py.
"""

import pytest
from awslabs.amazon_translate_mcp_server import server
from unittest.mock import AsyncMock, MagicMock, patch


class TestAsyncTranslationTools:
    """Comprehensive async tests for translation tools."""

    @pytest.mark.asyncio
    async def test_translate_text_success(self):
        """Test successful text translation."""
        with patch.object(server, 'translation_service') as mock_service:
            # Mock translation result
            mock_result = MagicMock()
            mock_result.translated_text = 'Hola mundo'
            mock_result.source_language = 'en'
            mock_result.target_language = 'es'
            mock_result.applied_terminologies = ['tech-terms']
            mock_result.confidence_score = 0.95

            mock_service.translate_text.return_value = mock_result

            # Create mock context
            mock_ctx = MagicMock()

            # Call with new standard pattern
            result = await server.translate_text(
                ctx=mock_ctx,
                text='Hello world',
                source_language='en',
                target_language='es',
                terminology_names=['tech-terms'],
            )

            assert result['translated_text'] == 'Hola mundo'
            assert result['source_language'] == 'en'
            assert result['target_language'] == 'es'
            assert result['applied_terminologies'] == ['tech-terms']
            assert result['confidence_score'] == 0.95

            mock_service.translate_text.assert_called_once_with(
                'Hello world', 'en', 'es', ['tech-terms']
            )

    @pytest.mark.asyncio
    async def test_translate_text_service_not_initialized(self):
        """Test translate_text when service is not initialized."""
        with patch.object(server, 'translation_service', None):
            # Create mock context
            mock_ctx = MagicMock()

            result = await server.translate_text(
                ctx=mock_ctx, text='Hello world', source_language='en', target_language='es'
            )

            assert 'error' in result
            # Error message is normalized, check for error type
            assert result['error_type'] == 'TranslationError'

    @pytest.mark.asyncio
    async def test_translate_text_exception_handling(self):
        """Test translate_text exception handling."""
        with patch.object(server, 'translation_service') as mock_service:
            mock_service.translate_text.side_effect = Exception('Translation failed')

            # Create mock context
            mock_ctx = MagicMock()

            result = await server.translate_text(
                ctx=mock_ctx, text='Hello world', source_language='en', target_language='es'
            )

            assert 'error' in result
            # Error message is normalized, check for error type
            assert result['error_type'] in ['Exception', 'TranslateException']

    @pytest.mark.asyncio
    async def test_detect_language_success(self):
        """Test successful language detection."""
        with patch.object(server, 'translation_service') as mock_service:
            mock_result = MagicMock()
            mock_result.detected_language = 'en'
            mock_result.confidence_score = 0.98
            mock_result.alternative_languages = [{'language': 'es', 'score': 0.02}]

            mock_service.detect_language.return_value = mock_result

            # Create mock context
            mock_ctx = MagicMock()

            result = await server.detect_language(ctx=mock_ctx, text='Hello world')

            assert result['detected_language'] == 'en'
            assert result['confidence_score'] == 0.98
            assert result['alternative_languages'] == [{'language': 'es', 'score': 0.02}]

    @pytest.mark.asyncio
    async def test_detect_language_service_not_initialized(self):
        """Test detect_language when service is not initialized."""
        with patch.object(server, 'translation_service', None):
            # Create mock context
            mock_ctx = MagicMock()

            result = await server.detect_language(ctx=mock_ctx, text='Hello world')

            assert 'error' in result
            # Error message is normalized, check for error type
            assert result['error_type'] == 'TranslationError'

    @pytest.mark.asyncio
    async def test_validate_translation_success(self):
        """Test successful translation validation."""
        with patch.object(server, 'translation_service') as mock_service:
            mock_result = MagicMock()
            mock_result.is_valid = True
            mock_result.quality_score = 0.92
            mock_result.issues = []
            mock_result.suggestions = ['Consider using formal tone']

            mock_service.validate_translation.return_value = mock_result

            # Create mock context
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
            assert result['issues'] == []
            assert result['suggestions'] == ['Consider using formal tone']

    @pytest.mark.asyncio
    async def test_validate_translation_service_not_initialized(self):
        """Test validate_translation when service is not initialized."""
        with patch.object(server, 'translation_service', None):
            # Create mock context
            mock_ctx = MagicMock()

            result = await server.validate_translation(
                ctx=mock_ctx,
                original_text='Hello world',
                translated_text='Hola mundo',
                source_language='en',
                target_language='es',
            )

            assert 'error' in result
            # Error message is normalized, check for error type
            assert result['error_type'] == 'TranslationError'


class TestAsyncBatchTranslationTools:
    """Comprehensive async tests for batch translation tools."""

    @pytest.mark.asyncio
    async def test_start_batch_translation_success(self):
        """Test successful batch translation start."""
        with patch.object(server, 'batch_manager') as mock_manager:
            mock_manager.start_batch_translation.return_value = 'job-123'

            # Create mock context
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
            assert 'successfully' in result['message']

    @pytest.mark.asyncio
    async def test_start_batch_translation_manager_not_initialized(self):
        """Test start_batch_translation when manager is not initialized."""
        with patch.object(server, 'batch_manager', None):
            # Create mock context
            mock_ctx = MagicMock()

            result = await server.start_batch_translation(
                ctx=mock_ctx,
                input_s3_uri='s3://bucket/input/',
                output_s3_uri='s3://bucket/output/',
                data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
                job_name='test-job',
                source_language='en',
                target_languages=['es'],
            )

            assert 'error' in result
            # Error message is normalized, check for error type
            assert result['error_type'] in ['BatchJobError', 'ValueError']

    @pytest.mark.asyncio
    async def test_get_translation_job_success(self):
        """Test successful translation job retrieval."""
        with patch.object(server, 'batch_manager') as mock_manager:
            from datetime import datetime

            mock_job_status = MagicMock()
            mock_job_status.job_id = 'job-123'
            mock_job_status.job_name = 'test-job'
            mock_job_status.status = 'COMPLETED'
            mock_job_status.progress = 100
            mock_job_status.created_at = datetime(2023, 1, 1, 12, 0, 0)
            mock_job_status.completed_at = datetime(2023, 1, 1, 13, 0, 0)
            mock_job_status.error_details = None

            # Mock input and output configs
            mock_input_config = MagicMock()
            mock_input_config.s3_uri = 's3://bucket/input/'
            mock_input_config.content_type = 'text/plain'
            mock_job_status.input_config = mock_input_config

            mock_output_config = MagicMock()
            mock_output_config.s3_uri = 's3://bucket/output/'
            mock_job_status.output_config = mock_output_config

            mock_manager.get_translation_job.return_value = mock_job_status

            params = server.GetTranslationJobParams(job_id='job-123')
            result = await server.get_translation_job(params)

            assert result['job_id'] == 'job-123'
            assert result['job_name'] == 'test-job'
            assert result['status'] == 'COMPLETED'
            assert result['progress'] == 100
            assert result['created_at'] == '2023-01-01T12:00:00'
            assert result['completed_at'] == '2023-01-01T13:00:00'

    @pytest.mark.asyncio
    async def test_list_translation_jobs_success(self):
        """Test successful translation jobs listing."""
        with patch.object(server, 'batch_manager') as mock_manager:
            from datetime import datetime

            mock_job = MagicMock()
            mock_job.job_id = 'job-123'
            mock_job.job_name = 'test-job'
            mock_job.status = 'COMPLETED'
            mock_job.source_language_code = 'en'
            mock_job.target_language_codes = ['es', 'fr']
            mock_job.created_at = datetime(2023, 1, 1, 12, 0, 0)
            mock_job.completed_at = datetime(2023, 1, 1, 13, 0, 0)

            mock_manager.list_translation_jobs.return_value = [mock_job]

            params = server.ListTranslationJobsParams(max_results=10, status_filter='COMPLETED')
            result = await server.list_translation_jobs(params)

            assert len(result['jobs']) == 1
            assert result['jobs'][0]['job_id'] == 'job-123'
            assert result['jobs'][0]['status'] == 'COMPLETED'
            assert result['total_count'] == 1

    @pytest.mark.asyncio
    async def test_list_translation_jobs_with_dict_result(self):
        """Test list_translation_jobs when result is a dict with next_token."""
        with patch.object(server, 'batch_manager') as mock_manager:
            from datetime import datetime

            mock_job = MagicMock()
            mock_job.job_id = 'job-456'
            mock_job.job_name = 'test-job-2'
            mock_job.status = 'IN_PROGRESS'
            mock_job.source_language_code = 'en'
            mock_job.target_language_codes = ['de']
            mock_job.created_at = datetime(2023, 1, 2, 12, 0, 0)
            mock_job.completed_at = None

            mock_result = {'jobs': [mock_job], 'next_token': 'next-token-123'}
            mock_manager.list_translation_jobs.return_value = mock_result

            params = server.ListTranslationJobsParams()
            result = await server.list_translation_jobs(params)

            assert len(result['jobs']) == 1
            assert result['jobs'][0]['job_id'] == 'job-456'
            assert result['next_token'] == 'next-token-123'


class TestAsyncTerminologyTools:
    """Comprehensive async tests for terminology tools."""

    @pytest.mark.asyncio
    async def test_list_terminologies_success(self):
        """Test successful terminologies listing."""
        with patch.object(server, 'terminology_manager') as mock_manager:
            from datetime import datetime

            mock_terminology = MagicMock()
            mock_terminology.name = 'tech-terms'
            mock_terminology.description = 'Technical terminology'
            mock_terminology.source_language = 'en'
            mock_terminology.target_languages = ['es', 'fr']
            mock_terminology.term_count = 100
            mock_terminology.created_at = datetime(2023, 1, 1, 12, 0, 0)
            mock_terminology.last_updated = datetime(2023, 1, 2, 12, 0, 0)

            mock_result = {'terminologies': [mock_terminology], 'next_token': None}
            mock_manager.list_terminologies.return_value = mock_result

            # Create mock context
            mock_ctx = MagicMock()

            result = await server.list_terminologies(ctx=mock_ctx)

            assert len(result['terminologies']) == 1
            assert result['terminologies'][0]['name'] == 'tech-terms'
            assert result['terminologies'][0]['term_count'] == 100
            assert result['total_count'] == 1

    @pytest.mark.asyncio
    async def test_list_terminologies_empty_result(self):
        """Test list_terminologies with empty result."""
        with patch.object(server, 'terminology_manager') as mock_manager:
            mock_result = {'terminologies': None, 'next_token': None}
            mock_manager.list_terminologies.return_value = mock_result

            # Create mock context
            mock_ctx = MagicMock()

            result = await server.list_terminologies(ctx=mock_ctx)

            assert result['terminologies'] == []
            assert result['total_count'] == 0

    @pytest.mark.asyncio
    async def test_create_terminology_success(self):
        """Test successful terminology creation."""
        with patch.object(server, 'terminology_manager') as mock_manager:
            mock_manager.create_terminology.return_value = (
                'arn:aws:translate:us-east-1:123:terminology/tech-terms'
            )

            # Create mock context
            mock_ctx = MagicMock()

            result = await server.create_terminology(
                ctx=mock_ctx,
                name='tech-terms',
                description='Technical terminology',
                source_language='en',
                target_languages=['es', 'fr'],
                terms=[
                    {'source': 'API', 'target': 'API'},
                    {'source': 'database', 'target': 'base de datos'},
                ],
            )

            assert (
                result['terminology_arn']
                == 'arn:aws:translate:us-east-1:123:terminology/tech-terms'
            )
            assert result['name'] == 'tech-terms'
            assert result['status'] == 'CREATED'

    @pytest.mark.asyncio
    async def test_import_terminology_success(self):
        """Test successful terminology import."""
        with patch.object(server, 'terminology_manager') as mock_manager:
            import base64

            mock_manager.import_terminology.return_value = (
                'arn:aws:translate:us-east-1:123:terminology/imported-terms'
            )

            # Create base64 encoded CSV content
            csv_content = 'source,target\nAPI,API\ndatabase,base de datos'
            encoded_content = base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')

            # Create mock context
            mock_ctx = MagicMock()

            result = await server.import_terminology(
                ctx=mock_ctx,
                name='imported-terms',
                description='Imported terminology',
                file_content=encoded_content,
                file_format='CSV',
                source_language='en',
                target_languages=['es'],
            )

            assert (
                result['terminology_arn']
                == 'arn:aws:translate:us-east-1:123:terminology/imported-terms'
            )
            assert result['name'] == 'imported-terms'
            assert result['status'] == 'IMPORTED'

    @pytest.mark.asyncio
    async def test_get_terminology_success(self):
        """Test successful terminology retrieval."""
        with patch.object(server, 'terminology_manager') as mock_manager:
            from datetime import datetime

            mock_terminology = MagicMock()
            mock_terminology.name = 'tech-terms'
            mock_terminology.description = 'Technical terminology'
            mock_terminology.source_language = 'en'
            mock_terminology.target_languages = ['es', 'fr']
            mock_terminology.term_count = 100
            mock_terminology.created_at = datetime(2023, 1, 1, 12, 0, 0)
            mock_terminology.last_updated = datetime(2023, 1, 2, 12, 0, 0)
            mock_terminology.size_bytes = 2048
            mock_terminology.format = 'CSV'

            mock_manager.get_terminology.return_value = mock_terminology

            params = server.GetTerminologyParams(name='tech-terms')
            result = await server.get_terminology(params)

            assert result['name'] == 'tech-terms'
            assert result['description'] == 'Technical terminology'
            assert result['term_count'] == 100
            assert result['size_bytes'] == 2048
            assert result['format'] == 'CSV'


class TestAsyncLanguageOperationsTools:
    """Comprehensive async tests for language operations tools."""

    @pytest.mark.asyncio
    async def test_list_language_pairs_success(self):
        """Test successful language pairs listing."""
        with patch.object(server, 'language_operations') as mock_ops:
            mock_pair = MagicMock()
            mock_pair.source_language = 'en'
            mock_pair.target_language = 'es'
            mock_pair.supported_formats = ['text/plain', 'text/html']
            mock_pair.custom_terminology_supported = True

            mock_ops.list_language_pairs.return_value = [mock_pair]

            # Create mock context
            mock_ctx = MagicMock()

            result = await server.list_language_pairs(ctx=mock_ctx)

            assert len(result['language_pairs']) == 1
            assert result['language_pairs'][0]['source_language'] == 'en'
            assert result['language_pairs'][0]['target_language'] == 'es'
            assert result['total_count'] == 1

    @pytest.mark.asyncio
    async def test_list_language_pairs_service_not_initialized(self):
        """Test list_language_pairs when service is not initialized."""
        with patch.object(server, 'language_operations', None):
            # Create mock context
            mock_ctx = MagicMock()

            result = await server.list_language_pairs(ctx=mock_ctx)

            assert 'error' in result
            assert 'Language operations not initialized' in result['error']

    @pytest.mark.asyncio
    async def test_get_language_metrics_success(self):
        """Test successful language metrics retrieval."""
        with patch.object(server, 'language_operations') as mock_ops:
            mock_metrics = MagicMock()
            mock_metrics.language_pair = 'en-es'
            mock_metrics.time_range = '24h'
            mock_metrics.translation_count = 150
            mock_metrics.character_count = 5000
            mock_metrics.average_response_time = 0.5
            mock_metrics.error_rate = 0.01

            mock_ops.get_language_metrics.return_value = mock_metrics

            params = server.GetLanguageMetricsParams(language_pair='en-es', time_range='24h')
            result = await server.get_language_metrics(params)

            assert result['language_pair'] == 'en-es'
            assert result['translation_count'] == 150
            assert result['character_count'] == 5000
            assert result['average_response_time'] == 0.5
            assert result['error_rate'] == 0.01

    @pytest.mark.asyncio
    async def test_get_language_metrics_service_not_initialized(self):
        """Test get_language_metrics when service is not initialized."""
        with patch.object(server, 'language_operations', None):
            params = server.GetLanguageMetricsParams()
            result = await server.get_language_metrics(params)

            assert 'error' in result
            assert 'Language operations not initialized' in result['error']


class TestAsyncWorkflowTools:
    """Comprehensive async tests for workflow tools."""

    @pytest.mark.asyncio
    async def test_smart_translate_workflow_success(self):
        """Test successful smart translate workflow."""
        with patch.object(server, 'workflow_orchestrator') as mock_orchestrator:
            mock_result = MagicMock()
            mock_result.original_text = 'Hello world'
            mock_result.translated_text = 'Hola mundo'
            mock_result.detected_language = 'en'
            mock_result.target_language = 'es'
            mock_result.confidence_score = 0.95
            mock_result.quality_score = 0.92
            mock_result.applied_terminologies = ['tech-terms']
            mock_result.language_pair_supported = True
            mock_result.validation_issues = []
            mock_result.suggestions = []
            mock_result.execution_time_ms = 250
            mock_result.workflow_steps = ['detect', 'translate', 'validate']

            mock_orchestrator.smart_translate_workflow = AsyncMock(return_value=mock_result)

            # Create mock context
            mock_ctx = MagicMock()

            result = await server.smart_translate_workflow(
                ctx=mock_ctx,
                text='Hello world',
                target_language='es',
                quality_threshold=0.8,
                terminology_names=['tech-terms'],
            )

            assert 'workflow_type' in result
            assert result['workflow_type'] == 'smart_translation'
            assert result['original_text'] == 'Hello world'
            assert result['translated_text'] == 'Hola mundo'
            assert result['detected_language'] == 'en'
            assert result['confidence_score'] == 0.95

    @pytest.mark.asyncio
    async def test_smart_translate_workflow_orchestrator_not_initialized(self):
        """Test smart_translate_workflow when orchestrator is not initialized."""
        with patch.object(server, 'workflow_orchestrator', None):
            params = server.SmartTranslateWorkflowParams(text='Hello world', target_language='es')

            result = await server.smart_translate_workflow(params)

            assert 'error' in result
            assert 'Workflow orchestrator not initialized' in result['error']

    @pytest.mark.asyncio
    async def test_managed_batch_translation_workflow_success(self):
        """Test successful managed batch translation workflow."""
        with patch.object(server, 'workflow_orchestrator') as mock_orchestrator:
            from datetime import datetime

            mock_result = MagicMock()
            mock_result.job_id = 'job-123'
            mock_result.job_name = 'test-workflow-job'
            mock_result.status = 'COMPLETED'
            mock_result.source_language = 'en'
            mock_result.target_languages = ['es', 'fr']
            mock_result.input_s3_uri = 's3://bucket/input/'
            mock_result.output_s3_uri = 's3://bucket/output/'
            mock_result.terminology_names = ['tech-terms']
            mock_result.pre_validation_results = {'all_valid': True}
            mock_result.monitoring_history = [
                {'status': 'COMPLETED', 'timestamp': '2023-01-01T13:00:00'}
            ]
            mock_result.performance_metrics = {'total_time': 3600}
            mock_result.created_at = datetime(2023, 1, 1, 12, 0, 0)
            mock_result.completed_at = datetime(2023, 1, 1, 13, 0, 0)
            mock_result.total_execution_time = 3600
            mock_result.workflow_steps = ['validate', 'start', 'monitor']

            mock_orchestrator.managed_batch_translation_workflow = AsyncMock(
                return_value=mock_result
            )

            # Create mock context
            mock_ctx = MagicMock()

            result = await server.managed_batch_translation_workflow(
                ctx=mock_ctx,
                input_s3_uri='s3://bucket/input/',
                output_s3_uri='s3://bucket/output/',
                data_access_role_arn='arn:aws:iam::123:role/TranslateRole',
                job_name='test-workflow-job',
                source_language='en',
                target_languages=['es', 'fr'],
            )

            assert 'workflow_type' in result
            assert result['workflow_type'] == 'managed_batch_translation'
            assert result['job_id'] == 'job-123'
            assert result['status'] == 'COMPLETED'
            assert result['created_at'] == '2023-01-01T12:00:00'


class TestAsyncSeparateBatchTools:
    """Comprehensive async tests for separate batch translation tools."""

    @pytest.mark.asyncio
    async def test_trigger_batch_translation_success(self):
        """Test successful batch translation trigger."""
        with (
            patch.object(server, 'workflow_orchestrator'),
            patch.object(server, 'batch_manager') as mock_batch_manager,
            patch.object(server, 'language_operations') as mock_lang_ops,
            patch.object(server, 'terminology_manager') as mock_term_manager,
        ):
            from datetime import datetime

            # Mock language pairs validation
            mock_pair = MagicMock()
            mock_pair.source_language = 'en'
            mock_pair.target_language = 'es'
            mock_lang_ops.list_language_pairs.return_value = [mock_pair]

            # Mock terminology validation
            mock_terminology = MagicMock()
            mock_terminology.name = 'tech-terms'
            mock_term_manager.list_terminologies.return_value = {
                'terminologies': [mock_terminology]
            }

            # Mock batch job start
            mock_batch_manager.start_batch_translation.return_value = 'job-123'

            # Mock job status
            mock_job_status = MagicMock()
            mock_job_status.status = 'SUBMITTED'
            mock_job_status.created_at = datetime(2023, 1, 1, 12, 0, 0)
            mock_batch_manager.get_translation_job.return_value = mock_job_status

            # Create mock context
            mock_ctx = MagicMock()

            result = await server.trigger_batch_translation(
                ctx=mock_ctx,
                input_s3_uri='s3://bucket/input/',
                output_s3_uri='s3://bucket/output/',
                data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
                job_name='test-trigger-job',
                source_language='en',
                target_languages=['es'],
                terminology_names=['tech-terms'],
            )

            assert 'job_id' in result
            assert result['job_id'] == 'job-123'
            assert result['status'] == 'SUBMITTED'
            assert result['validation_results']['supported_pairs'] == ['en->es']
            assert 'successfully' in result['message']

    @pytest.mark.asyncio
    async def test_trigger_batch_translation_unsupported_language_pair(self):
        """Test trigger_batch_translation with unsupported language pair."""
        with (
            patch.object(server, 'workflow_orchestrator'),
            patch.object(server, 'batch_manager'),
            patch.object(server, 'language_operations') as mock_lang_ops,
        ):
            # Mock empty language pairs (unsupported)
            mock_lang_ops.list_language_pairs.return_value = []

            # Create mock context
            mock_ctx = MagicMock()

            result = await server.trigger_batch_translation(
                ctx=mock_ctx,
                input_s3_uri='s3://bucket/input/',
                output_s3_uri='s3://bucket/output/',
                data_access_role_arn='arn:aws:iam::123:role/TranslateRole',
                job_name='test-trigger-job',
                source_language='en',
                target_languages=['xyz'],  # Unsupported language
            )

            assert 'error' in result
            assert 'Unsupported language pairs' in result['error']

    @pytest.mark.asyncio
    async def test_trigger_batch_translation_missing_terminology(self):
        """Test trigger_batch_translation with missing terminology."""
        with (
            patch.object(server, 'workflow_orchestrator'),
            patch.object(server, 'batch_manager'),
            patch.object(server, 'language_operations') as mock_lang_ops,
            patch.object(server, 'terminology_manager') as mock_term_manager,
        ):
            # Mock supported language pairs
            mock_pair = MagicMock()
            mock_pair.source_language = 'en'
            mock_pair.target_language = 'es'
            mock_lang_ops.list_language_pairs.return_value = [mock_pair]

            # Mock empty terminologies (missing requested terminology)
            mock_term_manager.list_terminologies.return_value = {'terminologies': []}

            # Create mock context
            mock_ctx = MagicMock()

            result = await server.trigger_batch_translation(
                ctx=mock_ctx,
                input_s3_uri='s3://bucket/input/',
                output_s3_uri='s3://bucket/output/',
                data_access_role_arn='arn:aws:iam::123:role/TranslateRole',
                job_name='test-trigger-job',
                source_language='en',
                target_languages=['es'],
                terminology_names=['missing-terminology'],
            )

            assert 'error' in result
            assert 'Missing terminologies' in result['error']

    @pytest.mark.asyncio
    async def test_monitor_batch_translation_success(self):
        """Test successful batch translation monitoring."""
        with (
            patch.object(server, 'batch_manager') as mock_batch_manager,
            patch.object(server, 'workflow_orchestrator'),
            patch('asyncio.sleep', new_callable=AsyncMock),  # Mock sleep to speed up test
        ):
            from datetime import datetime

            # Mock job status progression: IN_PROGRESS -> COMPLETED
            mock_job_status_1 = MagicMock()
            mock_job_status_1.status = 'IN_PROGRESS'
            mock_job_status_1.progress = 50
            mock_job_status_1.created_at = datetime(2023, 1, 1, 12, 0, 0)
            mock_job_status_1.completed_at = None

            mock_job_status_2 = MagicMock()
            mock_job_status_2.status = 'COMPLETED'
            mock_job_status_2.progress = 100
            mock_job_status_2.created_at = datetime(2023, 1, 1, 12, 0, 0)
            mock_job_status_2.completed_at = datetime(2023, 1, 1, 13, 0, 0)

            mock_batch_manager.get_translation_job.side_effect = [
                mock_job_status_1,
                mock_job_status_2,
            ]

            # Create mock context
            mock_ctx = MagicMock()

            result = await server.monitor_batch_translation(
                ctx=mock_ctx,
                job_id='job-123',
                output_s3_uri='s3://bucket/output/',
                monitor_interval=1,
                max_monitoring_duration=60,
            )

            assert 'job_id' in result
            assert result['job_id'] == 'job-123'
            assert result['final_status'] == 'COMPLETED'
            assert result['progress'] == 100
            assert len(result['monitoring_history']) == 2
            assert 'performance_metrics' in result

    @pytest.mark.asyncio
    async def test_monitor_batch_translation_failed_job(self):
        """Test monitoring of a failed batch translation job."""
        with (
            patch.object(server, 'batch_manager') as mock_batch_manager,
            patch.object(server, 'workflow_orchestrator') as mock_orchestrator,
            patch('asyncio.sleep', new_callable=AsyncMock),
        ):
            from datetime import datetime

            # Mock failed job status
            mock_job_status = MagicMock()
            mock_job_status.status = 'FAILED'
            mock_job_status.progress = 25
            mock_job_status.created_at = datetime(2023, 1, 1, 12, 0, 0)
            mock_job_status.completed_at = datetime(2023, 1, 1, 12, 30, 0)

            mock_batch_manager.get_translation_job.return_value = mock_job_status

            # Mock error analysis
            mock_error_analysis = {
                'error_files_found': ['error-details.json'],
                'error_details': [{'error': 'File format not supported'}],
                'suggested_actions': ['Check file format'],
            }
            mock_orchestrator._analyze_job_errors = AsyncMock(return_value=mock_error_analysis)

            # Create mock context
            mock_ctx = MagicMock()

            result = await server.monitor_batch_translation(
                ctx=mock_ctx, job_id='job-456', output_s3_uri='s3://bucket/output/'
            )

            assert 'job_id' in result
            assert result['job_id'] == 'job-456'
            assert result['final_status'] == 'FAILED'
            assert result['error_analysis'] == mock_error_analysis

    @pytest.mark.asyncio
    async def test_analyze_batch_translation_errors_success(self):
        """Test successful batch translation error analysis."""
        with patch.object(server, 'workflow_orchestrator') as mock_orchestrator:
            mock_error_analysis = {
                'error_files_found': ['error-details.json', 'failed-files.json'],
                'error_details': [
                    {
                        'error_data': {
                            'sourceLanguageCode': 'en',
                            'targetLanguageCode': 'es',
                            'details': [
                                {
                                    'auxiliaryData': {
                                        'error': {'errorMessage': 'UTF-8 encoding error in file'}
                                    }
                                }
                            ],
                        }
                    }
                ],
                'suggested_actions': ['Check file encoding', 'Validate file format'],
            }
            mock_orchestrator._analyze_job_errors = AsyncMock(return_value=mock_error_analysis)

            # Create mock context
            mock_ctx = MagicMock()

            result = await server.analyze_batch_translation_errors(
                ctx=mock_ctx, job_id='failed-job-123', output_s3_uri='s3://bucket/output/'
            )

            assert 'job_id' in result
            assert result['job_id'] == 'failed-job-123'
            assert len(result['error_files_found']) == 2
            assert len(result['error_details']) == 1
            assert 'UTF-8 Encoding Error' in result['error_summary']['error_patterns']
            assert 'en->es' in result['error_summary']['affected_languages']

    @pytest.mark.asyncio
    async def test_analyze_batch_translation_errors_no_errors_found(self):
        """Test error analysis when no errors are found."""
        with patch.object(server, 'workflow_orchestrator') as mock_orchestrator:
            mock_orchestrator._analyze_job_errors = AsyncMock(return_value=None)

            # Create mock context
            mock_ctx = MagicMock()

            result = await server.analyze_batch_translation_errors(
                ctx=mock_ctx, job_id='job-123', output_s3_uri='s3://bucket/output/'
            )

            assert 'job_id' in result
            assert result['job_id'] == 'job-123'
            assert 'No error details found' in result['error']

    @pytest.mark.asyncio
    async def test_list_active_workflows_success(self):
        """Test successful active workflows listing."""
        with patch.object(server, 'workflow_orchestrator') as mock_orchestrator:
            mock_workflows = [
                {'workflow_id': 'wf-123', 'status': 'running', 'type': 'smart_translate'},
                {'workflow_id': 'wf-456', 'status': 'monitoring', 'type': 'batch_translation'},
            ]
            mock_orchestrator.list_active_workflows.return_value = mock_workflows

            # Create mock context
            mock_ctx = MagicMock()

            result = await server.list_active_workflows(ctx=mock_ctx)

            assert len(result['workflows']) == 2
            assert result['total_count'] == 2
            assert result['workflows'][0]['workflow_id'] == 'wf-123'

    @pytest.mark.asyncio
    async def test_get_workflow_status_success(self):
        """Test successful workflow status retrieval."""
        with patch.object(server, 'workflow_orchestrator') as mock_orchestrator:
            mock_status = {
                'workflow_id': 'wf-123',
                'status': 'completed',
                'progress': 100,
                'steps': ['validate', 'translate', 'complete'],
            }
            mock_orchestrator.get_workflow_status.return_value = mock_status

            # Create mock context
            mock_ctx = MagicMock()

            result = await server.get_workflow_status(ctx=mock_ctx, workflow_id='wf-123')

            assert result['workflow_id'] == 'wf-123'
            assert result['status'] == 'completed'
            assert result['progress'] == 100

    @pytest.mark.asyncio
    async def test_get_workflow_status_not_found(self):
        """Test workflow status when workflow is not found."""
        with patch.object(server, 'workflow_orchestrator') as mock_orchestrator:
            mock_orchestrator.get_workflow_status.return_value = None

            # Create mock context
            mock_ctx = MagicMock()

            result = await server.get_workflow_status(ctx=mock_ctx, workflow_id='nonexistent-wf')

            assert 'error' in result
            # The error message will be different due to pydantic validation, so just check for error
            assert 'nonexistent-wf' in result['error'] or 'not found' in result['error'].lower()
            assert result['error_type'] == 'WorkflowNotFound'


class TestAsyncServiceNotInitializedCases:
    """Test cases for when services are not initialized."""

    @pytest.mark.asyncio
    async def test_all_tools_handle_uninitialized_services(self):
        """Test that all tools handle uninitialized services gracefully."""
        # Create mock context
        mock_ctx = MagicMock()

        # Patch all services to None
        with (
            patch.object(server, 'translation_service', None),
            patch.object(server, 'batch_manager', None),
            patch.object(server, 'terminology_manager', None),
            patch.object(server, 'language_operations', None),
            patch.object(server, 'workflow_orchestrator', None),
        ):
            # Test translation tools
            result = await server.translate_text(
                ctx=mock_ctx, text='Hello', source_language='en', target_language='es'
            )
            assert 'error' in result

            result = await server.detect_language(ctx=mock_ctx, text='Hello')
            assert 'error' in result

            result = await server.validate_translation(
                ctx=mock_ctx,
                original_text='Hello',
                translated_text='Hola',
                source_language='en',
                target_language='es',
            )
            assert 'error' in result

            # Test batch tools
            result = await server.start_batch_translation(
                ctx=mock_ctx,
                input_s3_uri='s3://bucket/input/',
                output_s3_uri='s3://bucket/output/',
                data_access_role_arn='arn:aws:iam::123456789012:role/Role',
                job_name='test',
                source_language='en',
                target_languages=['es'],
            )
            assert 'error' in result

            result = await server.get_translation_job(ctx=mock_ctx, job_id='job-123')
            assert 'error' in result

            result = await server.list_translation_jobs(ctx=mock_ctx)
            assert 'error' in result

            # Test terminology tools
            result = await server.list_terminologies(ctx=mock_ctx)
            assert 'error' in result

            result = await server.create_terminology(
                ctx=mock_ctx,
                name='test',
                description='test',
                source_language='en',
                target_languages=['es'],
                terms=[{'source': 'hi', 'target': 'hola'}],
            )
            assert 'error' in result

            # Test language operations tools
            result = await server.list_language_pairs(ctx=mock_ctx)
            assert 'error' in result

            metrics_params = server.GetLanguageMetricsParams()
            result = await server.get_language_metrics(metrics_params)
            assert 'error' in result

            # Test workflow tools
            result = await server.smart_translate_workflow(
                ctx=mock_ctx, text='Hello', target_language='es'
            )
            assert 'error' in result

            result = await server.list_active_workflows(ctx=mock_ctx)
            assert 'error' in result


class TestAsyncExceptionHandling:
    """Test exception handling in async tools."""

    @pytest.mark.asyncio
    async def test_all_tools_handle_exceptions_gracefully(self):
        """Test that all tools handle exceptions gracefully."""
        # Test with services that raise exceptions
        with (
            patch.object(server, 'translation_service') as mock_trans,
            patch.object(server, 'batch_manager') as mock_batch,
            patch.object(server, 'terminology_manager') as mock_term,
            patch.object(server, 'language_operations') as mock_lang,
            patch.object(server, 'workflow_orchestrator') as mock_workflow,
        ):
            # Configure all services to raise exceptions
            mock_trans.translate_text.side_effect = Exception('Translation error')
            mock_trans.detect_language.side_effect = Exception('Detection error')
            mock_trans.validate_translation.side_effect = Exception('Validation error')

            mock_batch.start_batch_translation.side_effect = Exception('Batch start error')
            mock_batch.get_translation_job.side_effect = Exception('Job get error')
            mock_batch.list_translation_jobs.side_effect = Exception('Job list error')

            mock_term.list_terminologies.side_effect = Exception('Term list error')
            mock_term.create_terminology.side_effect = Exception('Term create error')
            mock_term.import_terminology.side_effect = Exception('Term import error')
            mock_term.get_terminology.side_effect = Exception('Term get error')

            mock_lang.list_language_pairs.side_effect = Exception('Lang pairs error')
            mock_lang.get_language_metrics.side_effect = Exception('Metrics error')

            mock_workflow.smart_translate_workflow.side_effect = Exception('Smart workflow error')
            mock_workflow.managed_batch_translation_workflow.side_effect = Exception(
                'Batch workflow error'
            )
            mock_workflow.list_active_workflows.side_effect = Exception('List workflows error')
            mock_workflow.get_workflow_status.side_effect = Exception('Workflow status error')

            # Test all tools return error responses
            translate_params = server.TranslateTextParams(
                text='Hello', source_language='en', target_language='es'
            )
            result = await server.translate_text(translate_params)
            assert 'error' in result
            # Error is wrapped by normalize_exception
            assert result['error_type'] in ['Exception', 'TranslateException']

            # Create mock context
            mock_ctx = MagicMock()

            result = await server.detect_language(ctx=mock_ctx, text='Hello')
            assert 'error' in result

            # Test a few more key tools
            result = await server.list_terminologies(ctx=mock_ctx)
            assert 'error' in result

            result = await server.list_language_pairs(ctx=mock_ctx)
            assert 'error' in result

            smart_params = server.SmartTranslateWorkflowParams(text='Hello', target_language='es')
            result = await server.smart_translate_workflow(smart_params)
            assert 'error' in result
