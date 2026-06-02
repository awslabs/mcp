"""Tests to cover specific missing lines for 100% coverage."""

import base64
import os
import pytest
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch


class TestServerMissingLines:
    """Test specific missing lines in server.py."""

    @pytest.mark.asyncio
    async def test_import_terminology_missing_lines(self):
        """Test import_terminology function missing lines."""
        from awslabs.amazon_translate_mcp_server.server import import_terminology

        # Test with terminology manager not initialized (line 658)
        with patch('awslabs.amazon_translate_mcp_server.server.terminology_manager', None):
            mock_ctx = MagicMock()

            result = await import_terminology(
                ctx=mock_ctx,
                name='test-terminology',
                file_content='dGVzdA==',  # base64 'test'
                file_format='CSV',
                description='Test',
                source_language='en',
                target_languages=['es'],
            )

            assert 'error' in result
            assert 'not initialized' in result['error']

    @pytest.mark.asyncio
    async def test_import_terminology_success_path(self):
        """Test import_terminology success path (lines 661-701)."""
        from awslabs.amazon_translate_mcp_server.server import import_terminology

        with patch(
            'awslabs.amazon_translate_mcp_server.server.terminology_manager'
        ) as mock_term_mgr:
            with patch('tempfile.NamedTemporaryFile') as mock_temp_file:
                with patch('os.path.exists') as mock_exists:
                    with patch('os.unlink'):
                        with patch('asyncio.get_event_loop') as mock_loop:
                            # Setup mocks
                            temp_dir = tempfile.gettempdir()
                            mock_temp_file.return_value.__enter__.return_value.name = os.path.join(
                                temp_dir, 'test.csv'
                            )
                            mock_exists.return_value = True
                            mock_term_mgr.import_terminology.return_value = 'arn:test'

                            mock_executor = MagicMock()
                            mock_executor.return_value = 'arn:test'
                            mock_loop.return_value.run_in_executor = AsyncMock(
                                return_value='arn:test'
                            )

                            mock_ctx = MagicMock()

                            result = await import_terminology(
                                ctx=mock_ctx,
                                name='test-terminology',
                                file_content=base64.b64encode(b'test content').decode(),
                                file_format='CSV',
                                description='Test',
                                source_language='en',
                                target_languages=['es'],
                            )

                            assert result['status'] == 'IMPORTED'
                            assert result['name'] == 'test-terminology'

    @pytest.mark.asyncio
    async def test_get_terminology_missing_lines(self):
        """Test get_terminology function missing lines (lines 714, 734-736)."""
        from awslabs.amazon_translate_mcp_server.server import get_terminology

        # Test with terminology manager not initialized
        with patch('awslabs.amazon_translate_mcp_server.server.terminology_manager', None):
            mock_ctx = MagicMock()

            result = await get_terminology(ctx=mock_ctx, name='test')

            assert 'error' in result
            assert 'not initialized' in result['error']

    @pytest.mark.asyncio
    async def test_get_language_metrics_missing_lines(self):
        """Test get_language_metrics function missing lines."""
        from awslabs.amazon_translate_mcp_server.server import get_language_metrics

        # Test with language operations not initialized
        with patch('awslabs.amazon_translate_mcp_server.server.language_operations', None):
            mock_ctx = MagicMock()

            result = await get_language_metrics(ctx=mock_ctx, language_pair='en-es')

            assert 'error' in result
            assert 'not initialized' in result['error']


class TestTerminologyManagerMissingLines:
    """Test specific missing lines in terminology_manager.py."""

    def test_terminology_manager_initialization(self):
        """Test terminology manager initialization."""
        from awslabs.amazon_translate_mcp_server.terminology_manager import TerminologyManager

        mock_aws_client = MagicMock()
        manager = TerminologyManager(aws_client_manager=mock_aws_client)

        # Test that manager is properly initialized
        assert manager._aws_client_manager == mock_aws_client
        assert manager._translate_client is None

        # Test get translate client
        mock_aws_client.get_translate_client.return_value = MagicMock()
        client = manager._get_translate_client()
        assert client is not None

    def test_terminology_constants_and_patterns(self):
        """Test terminology constants and patterns."""
        from awslabs.amazon_translate_mcp_server.terminology_manager import TerminologyManager

        # Test class constants
        assert TerminologyManager.MAX_TERMINOLOGY_SIZE == 10 * 1024 * 1024
        assert TerminologyManager.MAX_TERMINOLOGIES == 100
        assert TerminologyManager.MAX_TERM_PAIRS == 10000
        assert 'CSV' in TerminologyManager.SUPPORTED_FORMATS
        assert 'TMX' in TerminologyManager.SUPPORTED_FORMATS

        # Test language code pattern
        pattern = TerminologyManager.LANGUAGE_CODE_PATTERN
        assert pattern.match('en') is not None
        assert pattern.match('zh-CN') is not None


class TestWorkflowOrchestratorMissingLines:
    """Test specific missing lines in workflow_orchestrator.py."""

    def test_workflow_context_creation(self):
        """Test workflow context creation (lines 186-187)."""
        from awslabs.amazon_translate_mcp_server.workflow_orchestrator import WorkflowContext
        from datetime import datetime

        context = WorkflowContext(
            workflow_id='test-id', workflow_type='smart_translation', started_at=datetime.now()
        )

        assert context.workflow_id == 'test-id'
        assert context.workflow_type == 'smart_translation'
        assert context.started_at is not None

    def test_workflow_orchestrator_initialization(self):
        """Test workflow orchestrator initialization."""
        from awslabs.amazon_translate_mcp_server.workflow_orchestrator import WorkflowOrchestrator

        mock_translation_service = MagicMock()
        mock_batch_manager = MagicMock()
        mock_terminology_manager = MagicMock()
        mock_language_operations = MagicMock()

        orchestrator = WorkflowOrchestrator(
            translation_service=mock_translation_service,
            batch_manager=mock_batch_manager,
            terminology_manager=mock_terminology_manager,
            language_operations=mock_language_operations,
        )

        # Test that orchestrator is properly initialized
        assert orchestrator.translation_service == mock_translation_service
        assert orchestrator.batch_manager == mock_batch_manager
        assert orchestrator.terminology_manager == mock_terminology_manager
        assert orchestrator.language_operations == mock_language_operations
        assert isinstance(orchestrator._active_workflows, dict)
        assert isinstance(orchestrator._workflow_results, dict)


class TestBatchManagerMissingLines:
    """Test specific missing lines in batch_manager.py."""

    def test_batch_manager_error_handling(self):
        """Test batch manager error handling (lines 177-183)."""
        from awslabs.amazon_translate_mcp_server.batch_manager import BatchJobManager
        from awslabs.amazon_translate_mcp_server.models import (
            BatchInputConfig,
            BatchOutputConfig,
            JobConfig,
        )
        from botocore.exceptions import ClientError

        mock_aws_client = MagicMock()
        manager = BatchJobManager(aws_client_manager=mock_aws_client)

        # Mock validation error
        mock_aws_client.get_translate_client.return_value.start_text_translation_job.side_effect = ClientError(
            error_response={
                'Error': {'Code': 'ValidationException', 'Message': 'Invalid parameters'}
            },
            operation_name='StartTextTranslationJob',
        )

        job_config = JobConfig(
            job_name='test-job', source_language_code='en', target_language_codes=['es']
        )

        input_config = BatchInputConfig(
            s3_uri='s3://test/input/',
            content_type='text/plain',
            data_access_role_arn='arn:aws:iam::123456789012:role/TestRole',
        )

        output_config = BatchOutputConfig(
            s3_uri='s3://test/output/',
            data_access_role_arn='arn:aws:iam::123456789012:role/TestRole',
        )

        with pytest.raises(Exception):  # ValidationError
            manager.start_batch_translation(input_config, output_config, job_config)

    def test_s3_uri_parsing(self):
        """Test S3 URI parsing functionality."""
        from awslabs.amazon_translate_mcp_server.batch_manager import BatchJobManager

        mock_aws_client = MagicMock()
        manager = BatchJobManager(aws_client_manager=mock_aws_client)

        # Test valid S3 URI parsing
        bucket, key = manager._parse_s3_uri('s3://my-bucket/path/to/file.txt')
        assert bucket == 'my-bucket'
        assert key == 'path/to/file.txt'

        # Test invalid URI
        with pytest.raises(Exception):
            manager._parse_s3_uri('invalid-uri')


class TestLanguageOperationsMissingLines:
    """Test specific missing lines in language_operations.py."""

    def test_language_operations_initialization(self):
        """Test language operations initialization."""
        from awslabs.amazon_translate_mcp_server.language_operations import LanguageOperations

        mock_aws_client = MagicMock()
        lang_ops = LanguageOperations(aws_client_manager=mock_aws_client)

        # Test initialization
        assert lang_ops.aws_client_manager == mock_aws_client
        assert lang_ops._language_cache is None
        assert lang_ops._cache_timestamp is None

        # Test constants
        assert 'text/plain' in LanguageOperations.SUPPORTED_FORMATS
        assert 'auto' in LanguageOperations.NO_TERMINOLOGY_LANGUAGES

    def test_language_operations_constants(self):
        """Test language operations constants and patterns."""
        from awslabs.amazon_translate_mcp_server.language_operations import LanguageOperations

        # Test supported formats
        formats = LanguageOperations.SUPPORTED_FORMATS
        assert 'text/plain' in formats
        assert 'text/html' in formats

        # Test no terminology languages
        no_term_langs = LanguageOperations.NO_TERMINOLOGY_LANGUAGES
        assert 'auto' in no_term_langs

        # Test that constants are properly defined
        assert len(formats) > 0
        assert len(no_term_langs) > 0


class TestConfigMissingLines:
    """Test specific missing lines in config.py."""

    def test_config_validation_edge_cases(self):
        """Test config validation edge cases."""
        from awslabs.amazon_translate_mcp_server.config import ServerConfig

        # Test config with edge case values
        config = ServerConfig(max_text_length=1, max_file_size=1, cache_ttl=1)

        # Test that config accepts edge case values
        assert config.max_text_length == 1
        assert config.max_file_size == 1
        assert config.cache_ttl == 1

    def test_environment_variable_processing(self):
        """Test environment variable processing."""
        import os
        from awslabs.amazon_translate_mcp_server.config import load_config_from_env

        # Test with blocked patterns environment variable
        with patch.dict(os.environ, {'TRANSLATE_BLOCKED_PATTERNS': 'pattern1,pattern2'}):
            config = load_config_from_env()
            assert 'pattern1' in config.blocked_patterns
            assert 'pattern2' in config.blocked_patterns


class TestExceptionsMissingLines:
    """Test specific missing lines in exceptions.py."""

    def test_exception_properties(self):
        """Test exception properties."""
        from awslabs.amazon_translate_mcp_server.exceptions import TranslationError

        error = TranslationError(
            message='Test error', error_code='TEST_ERROR', details={'key': 'value'}
        )

        # Test exception properties
        assert error.message == 'Test error'
        assert error.error_code == 'TEST_ERROR'
        assert error.details == {'key': 'value'}
        assert error.correlation_id is not None
        assert error.timestamp is not None

    def test_rate_limit_error_retry_after(self):
        """Test rate limit error with retry_after."""
        from awslabs.amazon_translate_mcp_server.exceptions import RateLimitError

        error = RateLimitError(
            message='Rate limit exceeded', error_code='RATE_LIMIT', retry_after=60
        )

        response = error.to_error_response()
        assert response.retry_after == 60


class TestRetryHandlerMissingLines:
    """Test specific missing lines in retry_handler.py."""

    def test_retry_config_edge_cases(self):
        """Test retry config edge cases."""
        from awslabs.amazon_translate_mcp_server.retry_handler import RetryConfig

        # Test with custom configuration
        config = RetryConfig(
            max_attempts=1, base_delay=0.1, max_delay=1.0, exponential_base=1.5, jitter=False
        )

        # Test delay calculation
        delay = config.calculate_delay(attempt=1)
        assert delay >= 0.1

    def test_async_retry_decorator(self):
        """Test async retry decorator."""
        from awslabs.amazon_translate_mcp_server.retry_handler import RetryConfig, with_async_retry

        config = RetryConfig(max_attempts=2)

        @with_async_retry(config)
        async def test_async_function():
            return 'success'

        # Test that decorator is applied
        assert hasattr(test_async_function, '__wrapped__')


class TestLoggingConfigMissingLines:
    """Test specific missing lines in logging_config.py."""

    def test_correlation_id_context_management(self):
        """Test correlation ID context management."""
        from awslabs.amazon_translate_mcp_server.logging_config import (
            clear_correlation_id,
            get_correlation_id,
            set_correlation_id,
        )

        # Test setting and getting correlation ID
        set_correlation_id('test-correlation-id')
        assert get_correlation_id() == 'test-correlation-id'

        # Test clearing correlation ID
        clear_correlation_id()
        # Should generate new ID when none exists
        new_id = get_correlation_id()
        assert new_id is not None
        assert new_id != 'test-correlation-id'

    def test_structured_formatter_edge_cases(self):
        """Test structured formatter edge cases."""
        import logging
        from awslabs.amazon_translate_mcp_server.logging_config import StructuredFormatter

        formatter = StructuredFormatter()

        # Test formatting with exception
        record = logging.LogRecord(
            name='test',
            level=logging.ERROR,
            pathname='test.py',
            lineno=1,
            msg='Test error',
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        assert 'Test error' in formatted
