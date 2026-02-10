"""Comprehensive tests for Server module.

This module contains tests to achieve high coverage of the server.py module.
"""

import pytest
from awslabs.amazon_translate_mcp_server import server
from awslabs.amazon_translate_mcp_server.exceptions import (
    TranslationError,
)
from awslabs.amazon_translate_mcp_server.models import (
    LanguageDetectionResult,
    LanguagePair,
    TerminologyDetails,
    TranslationJobStatus,
    TranslationResult,
    ValidationResult,
)
from datetime import datetime
from unittest.mock import AsyncMock, patch


class TestServerInitialization:
    """Test server initialization and setup."""

    def test_initialize_services_success(self):
        """Test successful service initialization."""
        with (
            patch('awslabs.amazon_translate_mcp_server.server.AWSClientManager') as mock_aws,
            patch('awslabs.amazon_translate_mcp_server.server.TranslationService') as mock_trans,
            patch('awslabs.amazon_translate_mcp_server.server.BatchJobManager') as mock_batch,
            patch('awslabs.amazon_translate_mcp_server.server.TerminologyManager') as mock_term,
            patch('awslabs.amazon_translate_mcp_server.server.LanguageOperations') as mock_lang,
            patch(
                'awslabs.amazon_translate_mcp_server.server.WorkflowOrchestrator'
            ) as mock_workflow,
        ):
            # Call initialize_services
            server.initialize_services()

            # Verify all services were initialized
            mock_aws.assert_called_once()
            mock_trans.assert_called_once()

            mock_batch.assert_called_once()
            mock_term.assert_called_once()
            mock_lang.assert_called_once()
            mock_workflow.assert_called_once()

    def test_initialize_services_failure(self):
        """Test service initialization failure handling."""
        with patch('awslabs.amazon_translate_mcp_server.server.AWSClientManager') as mock_aws:
            mock_aws.side_effect = Exception('AWS initialization failed')

            # Should raise exception
            with pytest.raises(Exception):
                server.initialize_services()


class TestParameterValidation:
    """Test parameter validation classes."""

    def test_translate_text_params_validation(self):
        """Test TranslateTextParams validation."""
        # Valid parameters
        params = server.TranslateTextParams(
            text='Hello world', source_language='en', target_language='es'
        )
        assert params.text == 'Hello world'
        assert params.source_language == 'en'
        assert params.target_language == 'es'
        assert params.terminology_names is None

        # With terminology
        params_with_term = server.TranslateTextParams(
            text='Hello world',
            source_language='en',
            target_language='es',
            terminology_names=['tech-terms'],
        )
        assert params_with_term.terminology_names == ['tech-terms']

    def test_detect_language_params_validation(self):
        """Test DetectLanguageParams validation."""
        params = server.DetectLanguageParams(text='Hello world')
        assert params.text == 'Hello world'

    def test_validate_translation_params_validation(self):
        """Test ValidateTranslationParams validation."""
        params = server.ValidateTranslationParams(
            original_text='Hello world',
            translated_text='Hola mundo',
            source_language='en',
            target_language='es',
        )
        assert params.original_text == 'Hello world'
        assert params.translated_text == 'Hola mundo'
        assert params.source_language == 'en'
        assert params.target_language == 'es'

    def test_start_batch_translation_params_validation(self):
        """Test StartBatchTranslationParams validation."""
        params = server.StartBatchTranslationParams(
            input_s3_uri='s3://bucket/input/',
            output_s3_uri='s3://bucket/output/',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
            job_name='test-job',
            source_language='en',
            target_languages=['es', 'fr'],
        )
        assert params.input_s3_uri == 's3://bucket/input/'
        assert params.output_s3_uri == 's3://bucket/output/'
        assert params.data_access_role_arn == 'arn:aws:iam::123456789012:role/TranslateRole'
        assert params.job_name == 'test-job'
        assert params.source_language == 'en'
        assert params.target_languages == ['es', 'fr']


class TestServerGlobalVariables:
    """Test server global variables and state."""

    def test_global_service_variables_exist(self):
        """Test that global service variables are defined."""
        # These should be defined as module-level variables
        assert hasattr(server, 'aws_client_manager')
        assert hasattr(server, 'translation_service')

        assert hasattr(server, 'batch_manager')
        assert hasattr(server, 'terminology_manager')
        assert hasattr(server, 'language_operations')
        assert hasattr(server, 'workflow_orchestrator')

    def test_mcp_server_instance_exists(self):
        """Test that the FastMCP server instance exists."""
        assert hasattr(server, 'mcp')
        assert server.mcp is not None


class TestUtilityFunctions:
    """Test utility functions in server module."""

    def test_format_translation_result(self):
        """Test translation result formatting."""
        result = TranslationResult(
            translated_text='Hola mundo',
            source_language='en',
            target_language='es',
            applied_terminologies=['tech-terms'],
        )

        # Test the formatting (assuming there's a format function)
        formatted = str(result)
        assert 'Hola mundo' in formatted
        assert 'en' in formatted
        assert 'es' in formatted

    def test_format_language_detection_result(self):
        """Test language detection result formatting."""
        result = LanguageDetectionResult(
            detected_language='en',
            confidence_score=0.95,
            alternative_languages=[('es', 0.05), ('fr', 0.02)],
        )

        formatted = str(result)
        assert 'en' in formatted
        assert '0.95' in formatted

    def test_format_validation_result(self):
        """Test validation result formatting."""
        result = ValidationResult(
            is_valid=True,
            quality_score=0.85,
            issues=['Minor grammar issue'],
            suggestions=['Consider rephrasing'],
        )

        formatted = str(result)
        assert 'true' in formatted.lower() or 'True' in formatted
        assert '0.85' in formatted


class TestMCPToolFunctions:
    """Test MCP tool functions with proper service mocking."""

    @pytest.mark.asyncio
    async def test_translate_text_success(self):
        """Test successful text translation via MCP tool."""
        # Mock the translation service
        mock_result = TranslationResult(
            translated_text='Hola mundo',
            source_language='en',
            target_language='es',
            applied_terminologies=['tech-terms'],
            confidence_score=0.95,
        )

        with patch.object(server, 'translation_service') as mock_service:
            mock_service.translate_text.return_value = mock_result

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            # Call the MCP tool function directly
            result = await server.translate_text(
                ctx=mock_ctx,
                text='Hello world',
                source_language='en',
                target_language='es',
                terminology_names=['tech-terms'],
            )

            # Verify the service was called correctly
            mock_service.translate_text.assert_called_once_with(
                'Hello world', 'en', 'es', ['tech-terms']
            )

            # Verify the result
            assert result['translated_text'] == 'Hola mundo'
            assert result['source_language'] == 'en'
            assert result['target_language'] == 'es'
            assert result['applied_terminologies'] == ['tech-terms']
            assert result['confidence_score'] == 0.95

    @pytest.mark.asyncio
    async def test_translate_text_service_not_initialized(self):
        """Test translation when service is not initialized."""
        with patch.object(server, 'translation_service', None):
            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.translate_text(
                ctx=mock_ctx, text='Hello world', source_language='en', target_language='es'
            )

            assert 'error' in result
            assert 'Translation service not initialized' in result['error']
            assert result['error_type'] == 'TranslationError'

    @pytest.mark.asyncio
    async def test_translate_text_service_error(self):
        """Test translation when service raises an error."""
        with patch.object(server, 'translation_service') as mock_service:
            mock_service.translate_text.side_effect = TranslationError('Translation failed')

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
    async def test_detect_language_success(self):
        """Test successful language detection via MCP tool."""
        # Mock the translation service
        mock_result = LanguageDetectionResult(
            detected_language='en',
            confidence_score=0.95,
            alternative_languages=[('es', 0.05), ('fr', 0.02)],
        )

        with patch.object(server, 'translation_service') as mock_service:
            mock_service.detect_language.return_value = mock_result

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            # Call the MCP tool function
            result = await server.detect_language(ctx=mock_ctx, text='Hello world')

            # Verify the service was called correctly
            mock_service.detect_language.assert_called_once_with('Hello world')

            # Verify the result
            assert result['detected_language'] == 'en'
            assert result['confidence_score'] == 0.95
            assert result['alternative_languages'] == [('es', 0.05), ('fr', 0.02)]

    @pytest.mark.asyncio
    async def test_detect_language_service_not_initialized(self):
        """Test language detection when service is not initialized."""
        with patch.object(server, 'translation_service', None):
            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.detect_language(ctx=mock_ctx, text='Hello world')

            assert 'error' in result
            assert 'Translation service not initialized' in result['error']
            assert result['error_type'] == 'TranslationError'

    @pytest.mark.asyncio
    async def test_validate_translation_success(self):
        """Test successful translation validation via MCP tool."""
        # Mock the translation service
        mock_result = ValidationResult(
            is_valid=True,
            quality_score=0.85,
            issues=['Minor grammar issue'],
            suggestions=['Consider rephrasing'],
        )

        with patch.object(server, 'translation_service') as mock_service:
            mock_service.validate_translation.return_value = mock_result

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            # Call the MCP tool function
            result = await server.validate_translation(
                ctx=mock_ctx,
                original_text='Hello world',
                translated_text='Hola mundo',
                source_language='en',
                target_language='es',
            )

            # Verify the service was called correctly
            mock_service.validate_translation.assert_called_once_with(
                'Hello world', 'Hola mundo', 'en', 'es'
            )

            # Verify the result
            assert result['is_valid']
            assert result['quality_score'] == 0.85
            assert result['issues'] == ['Minor grammar issue']
            assert result['suggestions'] == ['Consider rephrasing']


class TestMCPToolErrorHandling:
    """Test error handling in MCP tool functions."""

    @pytest.mark.asyncio
    async def test_translate_text_with_none_terminology(self):
        """Test translation with None terminology names."""
        mock_result = TranslationResult(
            translated_text='Hola mundo',
            source_language='en',
            target_language='es',
            applied_terminologies=[],
        )

        with patch.object(server, 'translation_service') as mock_service:
            mock_service.translate_text.return_value = mock_result

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.translate_text(
                ctx=mock_ctx,
                text='Hello world',
                source_language='en',
                target_language='es',
                terminology_names=None,
            )

            # Verify the service was called with empty list when terminology_names is None
            mock_service.translate_text.assert_called_once_with(
                'Hello world',
                'en',
                'es',
                [],  # Should convert None to empty list
            )

            assert result['translated_text'] == 'Hola mundo'

    @pytest.mark.asyncio
    async def test_generic_exception_handling(self):
        """Test handling of generic exceptions in MCP tools."""
        with patch.object(server, 'translation_service') as mock_service:
            mock_service.detect_language.side_effect = Exception('Unexpected error')

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.detect_language(ctx=mock_ctx, text='Hello world')

            assert 'error' in result
            # The error message is wrapped by normalize_exception
            assert 'Exception' in result['error'] or 'error occurred' in result['error']
            assert result['error_type'] in ['Exception', 'TranslateException']


class TestMCPToolIntegration:
    """Test integration aspects of MCP tools."""

    @pytest.mark.asyncio
    async def test_translate_text_with_asyncio_executor(self):
        """Test that translate_text properly uses asyncio executor."""
        mock_result = TranslationResult(
            translated_text='Hola mundo',
            source_language='en',
            target_language='es',
            applied_terminologies=[],
        )

        with (
            patch.object(server, 'translation_service') as mock_service,
            patch('asyncio.get_event_loop') as mock_get_loop,
        ):
            # Mock the event loop and executor
            mock_loop = AsyncMock()
            mock_get_loop.return_value = mock_loop
            mock_loop.run_in_executor.return_value = mock_result

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.translate_text(
                ctx=mock_ctx, text='Hello world', source_language='en', target_language='es'
            )

            # Verify executor was used
            mock_get_loop.assert_called_once()
            mock_loop.run_in_executor.assert_called_once()

            # Verify the call arguments to run_in_executor
            call_args = mock_loop.run_in_executor.call_args
            assert call_args[0][0] is None  # executor=None (default thread pool)
            assert call_args[0][1] == mock_service.translate_text  # function
            # The args now include the individual parameters
            assert len(call_args[0]) >= 5  # Should have at least executor, function, and 3+ args

            assert result['translated_text'] == 'Hola mundo'

    @pytest.mark.asyncio
    async def test_detect_language_with_asyncio_executor(self):
        """Test that detect_language properly uses asyncio executor."""
        mock_result = LanguageDetectionResult(
            detected_language='en', confidence_score=0.95, alternative_languages=[]
        )

        with (
            patch.object(server, 'translation_service') as mock_service,
            patch('asyncio.get_event_loop') as mock_get_loop,
        ):
            # Mock the event loop and executor
            mock_loop = AsyncMock()
            mock_get_loop.return_value = mock_loop
            mock_loop.run_in_executor.return_value = mock_result

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.detect_language(ctx=mock_ctx, text='Hello world')

            # Verify executor was used
            mock_get_loop.assert_called_once()
            mock_loop.run_in_executor.assert_called_once()

            # Verify the call arguments to run_in_executor
            call_args = mock_loop.run_in_executor.call_args
            assert call_args[0][0] is None  # executor=None (default thread pool)
            assert call_args[0][1] == mock_service.detect_language  # function
            assert call_args[0][2] == 'Hello world'  # text argument

            assert result['detected_language'] == 'en'


class TestBatchTranslationMCPTools:
    """Test batch translation MCP tools."""

    @pytest.mark.asyncio
    async def test_start_batch_translation_success(self):
        """Test successful batch translation start."""
        with patch.object(server, 'batch_manager') as mock_batch:
            mock_batch.start_batch_translation.return_value = 'job-123'

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
            assert 'successfully' in result['message']

            # Verify service was called with correct config objects
            mock_batch.start_batch_translation.assert_called_once()
            call_args = mock_batch.start_batch_translation.call_args[0]
            assert call_args[0].s3_uri == 's3://bucket/input/'
            assert call_args[1].s3_uri == 's3://bucket/output/'
            assert call_args[2].job_name == 'test-job'

    @pytest.mark.asyncio
    async def test_start_batch_translation_service_not_initialized(self):
        """Test batch translation when service not initialized."""
        with patch.object(server, 'batch_manager', None):
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
                target_languages=['es'],
            )

            assert 'error' in result
            assert 'Batch manager not initialized' in result['error']
            assert result['error_type'] == 'BatchJobError'

    @pytest.mark.asyncio
    async def test_get_translation_job_success(self):
        """Test successful translation job retrieval."""
        mock_job_status = TranslationJobStatus(
            job_id='job-123',
            job_name='test-job',
            status='COMPLETED',
            progress=100.0,
            created_at=datetime.now(),
        )

        with patch.object(server, 'batch_manager') as mock_batch:
            mock_batch.get_translation_job.return_value = mock_job_status

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.get_translation_job(ctx=mock_ctx, job_id='job-123')

            assert result['job_id'] == 'job-123'
            assert result['job_name'] == 'test-job'
            assert result['status'] == 'COMPLETED'
            assert result['progress'] == 100.0

            mock_batch.get_translation_job.assert_called_once_with('job-123')

    @pytest.mark.asyncio
    async def test_list_translation_jobs_success(self):
        """Test successful translation jobs listing."""
        from awslabs.amazon_translate_mcp_server.models import TranslationJobSummary

        mock_jobs = [
            TranslationJobSummary(
                job_id='job-1',
                job_name='job-1',
                status='COMPLETED',
                source_language_code='en',
                target_language_codes=['es'],
                created_at=datetime.now(),
            ),
            TranslationJobSummary(
                job_id='job-2',
                job_name='job-2',
                status='IN_PROGRESS',
                source_language_code='en',
                target_language_codes=['fr'],
                created_at=datetime.now(),
            ),
        ]

        with patch.object(server, 'batch_manager') as mock_batch:
            mock_batch.list_translation_jobs.return_value = mock_jobs

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.list_translation_jobs(
                ctx=mock_ctx, status_filter='ALL', max_results=50
            )

            assert result['total_count'] == 2
            assert len(result['jobs']) == 2
            assert result['jobs'][0]['job_id'] == 'job-1'
            assert result['jobs'][1]['job_id'] == 'job-2'

            mock_batch.list_translation_jobs.assert_called_once_with('ALL', 50)


class TestTerminologyMCPTools:
    """Test terminology management MCP tools."""

    @pytest.mark.asyncio
    async def test_list_terminologies_success(self):
        """Test successful terminologies listing."""
        mock_terminologies = [
            TerminologyDetails(
                name='tech-terms',
                description='Technical terminology',
                source_language='en',
                target_languages=['es', 'fr'],
                term_count=100,
                created_at=datetime.now(),
                last_updated=datetime.now(),
            )
        ]

        with patch.object(server, 'terminology_manager') as mock_term:
            mock_term.list_terminologies.return_value = {
                'terminologies': mock_terminologies,
                'next_token': None,
            }

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.list_terminologies(ctx=mock_ctx)

            assert result['total_count'] == 1
            assert len(result['terminologies']) == 1
            assert result['terminologies'][0]['name'] == 'tech-terms'
            assert result['terminologies'][0]['term_count'] == 100
            assert result['next_token'] is None

            mock_term.list_terminologies.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_terminology_success(self):
        """Test successful terminology creation."""
        with patch.object(server, 'terminology_manager') as mock_term:
            mock_term.create_terminology.return_value = (
                'arn:aws:translate:us-east-1:123:terminology/tech-terms'
            )

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.create_terminology(
                ctx=mock_ctx,
                name='tech-terms',
                description='Technical terminology',
                source_language='en',
                target_languages=['es', 'fr'],
                terms=[
                    {'source': 'API', 'target': 'API'},
                    {'source': 'server', 'target': 'servidor'},
                ],
            )

            assert result['name'] == 'tech-terms'
            assert result['status'] == 'CREATED'
            assert 'successfully' in result['message']
            assert 'arn:aws:translate' in result['terminology_arn']

            mock_term.create_terminology.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_terminology_success(self):
        """Test successful terminology retrieval."""
        mock_terminology = TerminologyDetails(
            name='tech-terms',
            description='Technical terminology',
            source_language='en',
            target_languages=['es', 'fr'],
            term_count=100,
            size_bytes=1024,
            format='CSV',
            created_at=datetime.now(),
            last_updated=datetime.now(),
        )

        with patch.object(server, 'terminology_manager') as mock_term:
            mock_term.get_terminology.return_value = mock_terminology

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.get_terminology(ctx=mock_ctx, name='tech-terms')

            assert result['name'] == 'tech-terms'
            assert result['description'] == 'Technical terminology'
            assert result['term_count'] == 100
            assert result['size_bytes'] == 1024
            assert result['format'] == 'CSV'

            mock_term.get_terminology.assert_called_once_with('tech-terms')

    @pytest.mark.asyncio
    async def test_import_terminology_success(self):
        """Test successful terminology import."""
        import base64

        # Create mock CSV content
        csv_content = 'source,target\nAPI,API\nserver,servidor'
        encoded_content = base64.b64encode(csv_content.encode()).decode()

        with (
            patch.object(server, 'terminology_manager') as mock_term,
            patch('tempfile.NamedTemporaryFile') as mock_temp,
            patch('os.path.exists', return_value=True),
            patch('os.unlink'),
        ):
            import os
            import tempfile

            temp_csv_file = os.path.join(tempfile.gettempdir(), 'test.csv')
            mock_temp.return_value.__enter__.return_value.name = temp_csv_file
            mock_term.import_terminology.return_value = (
                'arn:aws:translate:us-east-1:123:terminology/imported-terms'
            )

            # Create mock context
            from unittest.mock import MagicMock

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

            assert result['name'] == 'imported-terms'
            assert result['status'] == 'IMPORTED'
            assert 'successfully' in result['message']

            mock_term.import_terminology.assert_called_once()


class TestLanguageOperationsMCPTools:
    """Test language operations MCP tools."""

    @pytest.mark.asyncio
    async def test_list_language_pairs_success(self):
        """Test successful language pairs listing."""
        mock_pairs = [
            LanguagePair(
                source_language='en',
                target_language='es',
                supported_formats=['text/plain', 'text/html'],
                custom_terminology_supported=True,
            ),
            LanguagePair(
                source_language='en',
                target_language='fr',
                supported_formats=['text/plain'],
                custom_terminology_supported=True,
            ),
        ]

        with patch.object(server, 'language_operations') as mock_lang:
            mock_lang.list_language_pairs.return_value = mock_pairs

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.list_language_pairs(ctx=mock_ctx)

            assert result['total_count'] == 2
            assert len(result['language_pairs']) == 2
            assert result['language_pairs'][0]['source_language'] == 'en'
            assert result['language_pairs'][0]['target_language'] == 'es'
            assert result['language_pairs'][0]['custom_terminology_supported']

            mock_lang.list_language_pairs.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_language_metrics_success(self):
        """Test successful language metrics retrieval."""
        from awslabs.amazon_translate_mcp_server.models import LanguageMetrics

        mock_metrics = LanguageMetrics(
            language_pair='en-es',
            time_range='24h',
            translation_count=1000,
            character_count=50000,
            average_response_time=0.5,
            error_rate=0.01,
        )

        with patch.object(server, 'language_operations') as mock_lang:
            mock_lang.get_language_metrics.return_value = mock_metrics

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.get_language_metrics(
                ctx=mock_ctx, language_pair='en-es', time_range='24h'
            )

            assert result['language_pair'] == 'en-es'
            assert result['time_range'] == '24h'
            assert result['translation_count'] == 1000
            assert result['character_count'] == 50000
            assert result['error_rate'] == 0.01

            mock_lang.get_language_metrics.assert_called_once_with('en-es', '24h')


class TestWorkflowMCPTools:
    """Test workflow orchestration MCP tools."""

    @pytest.mark.asyncio
    async def test_smart_translate_workflow_success(self):
        """Test successful smart translation workflow."""
        from awslabs.amazon_translate_mcp_server.workflow_orchestrator import (
            SmartTranslationWorkflowResult,
        )

        mock_result = SmartTranslationWorkflowResult(
            original_text='Hello world',
            translated_text='Hola mundo',
            detected_language='en',
            target_language='es',
            confidence_score=0.95,
            quality_score=0.88,
            applied_terminologies=[],
            language_pair_supported=True,
            validation_issues=[],
            suggestions=[],
            execution_time_ms=150,
            workflow_steps=['detect_language', 'translate', 'validate'],
        )

        with patch.object(server, 'workflow_orchestrator') as mock_workflow:
            mock_workflow.smart_translate_workflow = AsyncMock(return_value=mock_result)

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.smart_translate_workflow(
                ctx=mock_ctx,
                text='Hello world',
                target_language='es',
                quality_threshold=0.8,
                auto_detect_language=True,
            )

            assert result['workflow_type'] == 'smart_translation'
            assert result['original_text'] == 'Hello world'
            assert result['translated_text'] == 'Hola mundo'
            assert result['detected_language'] == 'en'
            assert result['confidence_score'] == 0.95
            assert result['quality_score'] == 0.88

            mock_workflow.smart_translate_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_managed_batch_translation_workflow_success(self):
        """Test successful managed batch translation workflow."""
        from awslabs.amazon_translate_mcp_server.workflow_orchestrator import (
            BatchTranslationWorkflowResult,
        )

        mock_result = BatchTranslationWorkflowResult(
            job_id='batch-job-123',
            job_name='test-batch',
            status='COMPLETED',
            source_language='en',
            target_languages=['es', 'fr'],
            input_s3_uri='s3://bucket/input/',
            output_s3_uri='s3://bucket/output/',
            terminology_names=[],
            pre_validation_results={'supported_pairs': ['en->es', 'en->fr']},
            monitoring_history=[],
            performance_metrics={'total_monitoring_time': 300},
            error_analysis=None,
            created_at=datetime.now(),
            completed_at=datetime.now(),
            total_execution_time=300.5,
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
                job_name='test-batch',
                source_language='en',
                target_languages=['es', 'fr'],
                monitor_interval=30,
                max_monitoring_duration=3600,
            )

            assert result['job_id'] == 'batch-job-123'
            assert result['status'] == 'COMPLETED'
            assert result['source_language'] == 'en'
            assert result['target_languages'] == ['es', 'fr']
            assert result['total_execution_time'] == 300.5

            mock_workflow.managed_batch_translation_workflow.assert_called_once()


class TestMCPToolAsyncioIntegration:
    """Test asyncio executor integration for all MCP tools."""

    @pytest.mark.asyncio
    async def test_batch_translation_with_executor(self):
        """Test batch translation uses asyncio executor properly."""
        with (
            patch.object(server, 'batch_manager') as mock_batch,
            patch('asyncio.get_event_loop') as mock_get_loop,
        ):
            mock_loop = AsyncMock()
            mock_get_loop.return_value = mock_loop
            mock_loop.run_in_executor.return_value = 'job-123'

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
                target_languages=['es'],
            )

            # Verify executor was used
            mock_get_loop.assert_called_once()
            mock_loop.run_in_executor.assert_called_once()

            # Verify the call arguments
            call_args = mock_loop.run_in_executor.call_args
            assert call_args[0][0] is None  # executor=None (default thread pool)
            assert call_args[0][1] == mock_batch.start_batch_translation

            assert result['job_id'] == 'job-123'

    @pytest.mark.asyncio
    async def test_terminology_operations_with_executor(self):
        """Test terminology operations use asyncio executor properly."""
        with (
            patch.object(server, 'terminology_manager') as mock_term,
            patch('asyncio.get_event_loop') as mock_get_loop,
        ):
            mock_loop = AsyncMock()
            mock_get_loop.return_value = mock_loop
            mock_loop.run_in_executor.return_value = {'terminologies': [], 'next_token': None}

            # Create mock context
            from unittest.mock import MagicMock

            mock_ctx = MagicMock()

            result = await server.list_terminologies(ctx=mock_ctx)

            # Verify executor was used
            mock_get_loop.assert_called_once()
            mock_loop.run_in_executor.assert_called_once()

            # Verify the call arguments
            call_args = mock_loop.run_in_executor.call_args
            assert call_args[0][0] is None  # executor=None
            assert call_args[0][1] == mock_term.list_terminologies

            assert result['total_count'] == 0
