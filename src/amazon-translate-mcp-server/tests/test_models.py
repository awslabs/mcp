"""Unit tests for Amazon Translate MCP Server data models.

This module tests all data models, validation logic, and exception handling.
"""

import pytest
from awslabs.amazon_translate_mcp_server.models import (
    AuthenticationError,
    # Batch models
    BatchInputConfig,
    BatchJobError,
    BatchOutputConfig,
    ContentType,
    # Error models
    ErrorResponse,
    JobConfig,
    # Enums
    JobStatus,
    LanguageDetectionResult,
    LanguageMetrics,
    # Language models
    LanguagePair,
    QuotaExceededError,
    RateLimitError,
    ServiceUnavailableError,
    # Terminology models
    TerminologyData,
    TerminologyDetails,
    TerminologyError,
    TerminologyFormat,
    TerminologySummary,
    # Exceptions
    TranslateException,
    TranslationError,
    TranslationJobStatus,
    TranslationJobSummary,
    # Core models
    TranslationResult,
    TranslationSettings,
    ValidationError,
    ValidationResult,
)
from datetime import datetime


class TestTranslationResult:
    """Test TranslationResult model."""

    def test_valid_translation_result(self):
        """Test creating a valid translation result."""
        result = TranslationResult(
            translated_text='Hola mundo',
            source_language='en',
            target_language='es',
            applied_terminologies=['tech-terms'],
            confidence_score=0.95,
        )

        assert result.translated_text == 'Hola mundo'
        assert result.source_language == 'en'
        assert result.target_language == 'es'
        assert result.applied_terminologies == ['tech-terms']
        assert result.confidence_score == 0.95

    def test_translation_result_minimal(self):
        """Test creating translation result with minimal fields."""
        result = TranslationResult(
            translated_text='Hola', source_language='en', target_language='es'
        )

        assert result.translated_text == 'Hola'
        assert result.applied_terminologies == []
        assert result.confidence_score is None

    def test_empty_translated_text_raises_error(self):
        """Test that empty translated text raises ValueError."""
        with pytest.raises(ValueError, match='translated_text cannot be empty'):
            TranslationResult(translated_text='', source_language='en', target_language='es')

    def test_empty_source_language_raises_error(self):
        """Test that empty source language raises ValueError."""
        with pytest.raises(ValueError, match='source_language cannot be empty'):
            TranslationResult(translated_text='Hola', source_language='', target_language='es')

    def test_empty_target_language_raises_error(self):
        """Test that empty target language raises ValueError."""
        with pytest.raises(ValueError, match='target_language cannot be empty'):
            TranslationResult(translated_text='Hola', source_language='en', target_language='')

    def test_invalid_confidence_score_raises_error(self):
        """Test that invalid confidence score raises ValueError."""
        with pytest.raises(ValueError, match='confidence_score must be between 0.0 and 1.0'):
            TranslationResult(
                translated_text='Hola',
                source_language='en',
                target_language='es',
                confidence_score=1.5,
            )

        with pytest.raises(ValueError, match='confidence_score must be between 0.0 and 1.0'):
            TranslationResult(
                translated_text='Hola',
                source_language='en',
                target_language='es',
                confidence_score=-0.1,
            )


class TestLanguageDetectionResult:
    """Test LanguageDetectionResult model."""

    def test_valid_language_detection_result(self):
        """Test creating a valid language detection result."""
        result = LanguageDetectionResult(
            detected_language='en',
            confidence_score=0.95,
            alternative_languages=[('es', 0.03), ('fr', 0.02)],
        )

        assert result.detected_language == 'en'
        assert result.confidence_score == 0.95
        assert result.alternative_languages == [('es', 0.03), ('fr', 0.02)]

    def test_empty_detected_language_raises_error(self):
        """Test that empty detected language raises ValueError."""
        with pytest.raises(ValueError, match='detected_language cannot be empty'):
            LanguageDetectionResult(detected_language='', confidence_score=0.95)

    def test_invalid_confidence_score_raises_error(self):
        """Test that invalid confidence score raises ValueError."""
        with pytest.raises(ValueError, match='confidence_score must be between 0.0 and 1.0'):
            LanguageDetectionResult(detected_language='en', confidence_score=1.5)

    def test_invalid_alternative_language_raises_error(self):
        """Test that invalid alternative language raises ValueError."""
        with pytest.raises(ValueError, match='Alternative language code cannot be empty'):
            LanguageDetectionResult(
                detected_language='en', confidence_score=0.95, alternative_languages=[('', 0.03)]
            )

        with pytest.raises(
            ValueError, match='Alternative language confidence score must be between 0.0 and 1.0'
        ):
            LanguageDetectionResult(
                detected_language='en', confidence_score=0.95, alternative_languages=[('es', 1.5)]
            )


class TestValidationResult:
    """Test ValidationResult model."""

    def test_valid_validation_result(self):
        """Test creating a valid validation result."""
        result = ValidationResult(
            is_valid=True,
            quality_score=0.85,
            issues=['Minor grammar issue'],
            suggestions=['Consider using formal tone'],
        )

        assert result.is_valid is True
        assert result.quality_score == 0.85
        assert result.issues == ['Minor grammar issue']
        assert result.suggestions == ['Consider using formal tone']

    def test_invalid_quality_score_raises_error(self):
        """Test that invalid quality score raises ValueError."""
        with pytest.raises(ValueError, match='quality_score must be between 0.0 and 1.0'):
            ValidationResult(is_valid=True, quality_score=1.5)


class TestBatchInputConfig:
    """Test BatchInputConfig model."""

    def test_valid_batch_input_config(self):
        """Test creating a valid batch input config."""
        config = BatchInputConfig(
            s3_uri='s3://my-bucket/input/',
            content_type='text/plain',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
        )

        assert config.s3_uri == 's3://my-bucket/input/'
        assert config.content_type == 'text/plain'
        assert config.data_access_role_arn == 'arn:aws:iam::123456789012:role/TranslateRole'

    def test_empty_s3_uri_raises_error(self):
        """Test that empty S3 URI raises ValueError."""
        with pytest.raises(ValueError, match='s3_uri cannot be empty'):
            BatchInputConfig(
                s3_uri='',
                content_type='text/plain',
                data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
            )

    def test_invalid_s3_uri_raises_error(self):
        """Test that invalid S3 URI raises ValueError."""
        with pytest.raises(ValueError, match="s3_uri must start with 's3://'"):
            BatchInputConfig(
                s3_uri='https://my-bucket/input/',
                content_type='text/plain',
                data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
            )

    def test_invalid_arn_raises_error(self):
        """Test that invalid ARN raises ValueError."""
        with pytest.raises(ValueError, match='data_access_role_arn must be a valid IAM role ARN'):
            BatchInputConfig(
                s3_uri='s3://my-bucket/input/',
                content_type='text/plain',
                data_access_role_arn='invalid-arn',
            )

    def test_empty_content_type_raises_error(self):
        """Test that empty content type raises ValueError."""
        with pytest.raises(ValueError, match='content_type cannot be empty'):
            BatchInputConfig(
                s3_uri='s3://my-bucket/input/',
                content_type='',
                data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
            )

    def test_empty_data_access_role_arn_raises_error(self):
        """Test that empty data access role ARN raises ValueError."""
        with pytest.raises(ValueError, match='data_access_role_arn cannot be empty'):
            BatchInputConfig(
                s3_uri='s3://my-bucket/input/', content_type='text/plain', data_access_role_arn=''
            )


class TestBatchOutputConfig:
    """Test BatchOutputConfig model."""

    def test_valid_batch_output_config(self):
        """Test creating a valid batch output config."""
        config = BatchOutputConfig(
            s3_uri='s3://my-bucket/output/',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
        )

        assert config.s3_uri == 's3://my-bucket/output/'
        assert config.data_access_role_arn == 'arn:aws:iam::123456789012:role/TranslateRole'

    def test_empty_s3_uri_raises_error(self):
        """Test that empty S3 URI raises ValueError."""
        with pytest.raises(ValueError, match='s3_uri cannot be empty'):
            BatchOutputConfig(
                s3_uri='', data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole'
            )

    def test_invalid_s3_uri_raises_error(self):
        """Test that invalid S3 URI raises ValueError."""
        with pytest.raises(ValueError, match="s3_uri must start with 's3://'"):
            BatchOutputConfig(
                s3_uri='https://my-bucket/output/',
                data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
            )

    def test_empty_data_access_role_arn_raises_error(self):
        """Test that empty data access role ARN raises ValueError."""
        with pytest.raises(ValueError, match='data_access_role_arn cannot be empty'):
            BatchOutputConfig(s3_uri='s3://my-bucket/output/', data_access_role_arn='')

    def test_invalid_arn_raises_error(self):
        """Test that invalid ARN raises ValueError."""
        with pytest.raises(ValueError, match='data_access_role_arn must be a valid IAM role ARN'):
            BatchOutputConfig(s3_uri='s3://my-bucket/output/', data_access_role_arn='invalid-arn')


class TestTranslationSettings:
    """Test TranslationSettings model."""

    def test_valid_translation_settings(self):
        """Test creating valid translation settings."""
        settings = TranslationSettings(formality='FORMAL', profanity='MASK', brevity='ON')

        assert settings.formality == 'FORMAL'
        assert settings.profanity == 'MASK'
        assert settings.brevity == 'ON'

    def test_invalid_formality_raises_error(self):
        """Test that invalid formality raises ValueError."""
        with pytest.raises(ValueError, match="formality must be 'FORMAL' or 'INFORMAL'"):
            TranslationSettings(formality='INVALID')

    def test_invalid_profanity_raises_error(self):
        """Test that invalid profanity setting raises ValueError."""
        with pytest.raises(ValueError, match="profanity must be 'MASK'"):
            TranslationSettings(profanity='INVALID')

    def test_invalid_brevity_raises_error(self):
        """Test that invalid brevity setting raises ValueError."""
        with pytest.raises(ValueError, match="brevity must be 'ON'"):
            TranslationSettings(brevity='INVALID')


class TestJobConfig:
    """Test JobConfig model."""

    def test_valid_job_config(self):
        """Test creating a valid job config."""
        config = JobConfig(
            job_name='test-job',
            source_language_code='en',
            target_language_codes=['es', 'fr'],
            terminology_names=['tech-terms'],
            settings=TranslationSettings(formality='FORMAL'),
        )

        assert config.job_name == 'test-job'
        assert config.source_language_code == 'en'
        assert config.target_language_codes == ['es', 'fr']
        assert config.terminology_names == ['tech-terms']
        assert config.settings is not None and config.settings.formality == 'FORMAL'

    def test_empty_job_name_raises_error(self):
        """Test that empty job name raises ValueError."""
        with pytest.raises(ValueError, match='job_name cannot be empty'):
            JobConfig(job_name='', source_language_code='en', target_language_codes=['es'])

    def test_empty_source_language_code_raises_error(self):
        """Test that empty source language code raises ValueError."""
        with pytest.raises(ValueError, match='source_language_code cannot be empty'):
            JobConfig(job_name='test-job', source_language_code='', target_language_codes=['es'])

    def test_empty_target_language_codes_raises_error(self):
        """Test that empty target language codes raises ValueError."""
        with pytest.raises(ValueError, match='target_language_codes cannot be empty'):
            JobConfig(job_name='test-job', source_language_code='en', target_language_codes=[])

    def test_too_many_target_languages_raises_error(self):
        """Test that too many target languages raises ValueError."""
        with pytest.raises(ValueError, match='Cannot specify more than 10 target languages'):
            JobConfig(
                job_name='test-job',
                source_language_code='en',
                target_language_codes=[
                    'es',
                    'fr',
                    'de',
                    'it',
                    'pt',
                    'ru',
                    'ja',
                    'ko',
                    'zh',
                    'ar',
                    'hi',
                ],
            )

    def test_invalid_language_code_raises_error(self):
        """Test that invalid language code raises ValueError."""
        with pytest.raises(ValueError, match='Invalid source language code format'):
            JobConfig(
                job_name='test-job', source_language_code='invalid', target_language_codes=['es']
            )

        with pytest.raises(ValueError, match='Invalid target language code format'):
            JobConfig(
                job_name='test-job', source_language_code='en', target_language_codes=['invalid']
            )


class TestTranslationJobStatus:
    """Test TranslationJobStatus model."""

    def test_valid_translation_job_status(self):
        """Test creating a valid translation job status."""
        now = datetime.now()
        status = TranslationJobStatus(
            job_id='job-123',
            job_name='test-job',
            status='IN_PROGRESS',
            progress=50.0,
            created_at=now,
        )

        assert status.job_id == 'job-123'
        assert status.job_name == 'test-job'
        assert status.status == 'IN_PROGRESS'
        assert status.progress == 50.0
        assert status.created_at == now

    def test_invalid_progress_raises_error(self):
        """Test that invalid progress raises ValueError."""
        with pytest.raises(ValueError, match='progress must be between 0.0 and 100.0'):
            TranslationJobStatus(
                job_id='job-123', job_name='test-job', status='IN_PROGRESS', progress=150.0
            )

    def test_empty_job_id_raises_error(self):
        """Test that empty job ID raises ValueError."""
        with pytest.raises(ValueError, match='job_id cannot be empty'):
            TranslationJobStatus(job_id='', job_name='test-job', status='IN_PROGRESS')

    def test_empty_job_name_raises_error(self):
        """Test that empty job name raises ValueError."""
        with pytest.raises(ValueError, match='job_name cannot be empty'):
            TranslationJobStatus(job_id='job-123', job_name='', status='IN_PROGRESS')

    def test_empty_status_raises_error(self):
        """Test that empty status raises ValueError."""
        with pytest.raises(ValueError, match='status cannot be empty'):
            TranslationJobStatus(job_id='job-123', job_name='test-job', status='')


class TestTranslationJobSummary:
    """Test TranslationJobSummary model."""

    def test_valid_translation_job_summary(self):
        """Test creating a valid translation job summary."""
        now = datetime.now()
        summary = TranslationJobSummary(
            job_id='job-123',
            job_name='test-job',
            status='COMPLETED',
            source_language_code='en',
            target_language_codes=['es', 'fr'],
            created_at=now,
            completed_at=now,
        )

        assert summary.job_id == 'job-123'
        assert summary.job_name == 'test-job'
        assert summary.status == 'COMPLETED'
        assert summary.source_language_code == 'en'
        assert summary.target_language_codes == ['es', 'fr']
        assert summary.created_at == now
        assert summary.completed_at == now

    def test_empty_job_id_raises_error(self):
        """Test that empty job ID raises ValueError."""
        with pytest.raises(ValueError, match='job_id cannot be empty'):
            TranslationJobSummary(
                job_id='',
                job_name='test-job',
                status='COMPLETED',
                source_language_code='en',
                target_language_codes=['es'],
            )

    def test_empty_job_name_raises_error(self):
        """Test that empty job name raises ValueError."""
        with pytest.raises(ValueError, match='job_name cannot be empty'):
            TranslationJobSummary(
                job_id='job-123',
                job_name='',
                status='COMPLETED',
                source_language_code='en',
                target_language_codes=['es'],
            )

    def test_empty_status_raises_error(self):
        """Test that empty status raises ValueError."""
        with pytest.raises(ValueError, match='status cannot be empty'):
            TranslationJobSummary(
                job_id='job-123',
                job_name='test-job',
                status='',
                source_language_code='en',
                target_language_codes=['es'],
            )

    def test_empty_source_language_code_raises_error(self):
        """Test that empty source language code raises ValueError."""
        with pytest.raises(ValueError, match='source_language_code cannot be empty'):
            TranslationJobSummary(
                job_id='job-123',
                job_name='test-job',
                status='COMPLETED',
                source_language_code='',
                target_language_codes=['es'],
            )

    def test_empty_target_language_codes_raises_error(self):
        """Test that empty target language codes raises ValueError."""
        with pytest.raises(ValueError, match='target_language_codes cannot be empty'):
            TranslationJobSummary(
                job_id='job-123',
                job_name='test-job',
                status='COMPLETED',
                source_language_code='en',
                target_language_codes=[],
            )


class TestTerminologyData:
    """Test TerminologyData model."""

    def test_valid_terminology_data(self):
        """Test creating valid terminology data."""
        data = TerminologyData(
            terminology_data=b'source,target\nhello,hola', format='CSV', directionality='UNI'
        )

        assert data.terminology_data == b'source,target\nhello,hola'
        assert data.format == 'CSV'
        assert data.directionality == 'UNI'

    def test_invalid_format_raises_error(self):
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError, match="format must be 'CSV' or 'TMX'"):
            TerminologyData(terminology_data=b'data', format='INVALID')

    def test_invalid_directionality_raises_error(self):
        """Test that invalid directionality raises ValueError."""
        with pytest.raises(ValueError, match="directionality must be 'UNI' or 'MULTI'"):
            TerminologyData(terminology_data=b'data', format='CSV', directionality='INVALID')

    def test_empty_terminology_data_raises_error(self):
        """Test that empty terminology data raises ValueError."""
        with pytest.raises(ValueError, match='terminology_data cannot be empty'):
            TerminologyData(terminology_data=b'', format='CSV')


class TestTerminologyDetails:
    """Test TerminologyDetails model."""

    def test_valid_terminology_details(self):
        """Test creating valid terminology details."""
        now = datetime.now()
        details = TerminologyDetails(
            name='tech-terms',
            description='Technical terminology',
            source_language='en',
            target_languages=['es', 'fr'],
            term_count=100,
            created_at=now,
            size_bytes=1024,
        )

        assert details.name == 'tech-terms'
        assert details.description == 'Technical terminology'
        assert details.source_language == 'en'
        assert details.target_languages == ['es', 'fr']
        assert details.term_count == 100
        assert details.created_at == now
        assert details.size_bytes == 1024

    def test_negative_term_count_raises_error(self):
        """Test that negative term count raises ValueError."""
        with pytest.raises(ValueError, match='term_count cannot be negative'):
            TerminologyDetails(
                name='tech-terms',
                description='Technical terminology',
                source_language='en',
                target_languages=['es'],
                term_count=-1,
            )

    def test_empty_name_raises_error(self):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match='name cannot be empty'):
            TerminologyDetails(
                name='',
                description='Technical terminology',
                source_language='en',
                target_languages=['es'],
                term_count=100,
            )

    def test_empty_source_language_raises_error(self):
        """Test that empty source language raises ValueError."""
        with pytest.raises(ValueError, match='source_language cannot be empty'):
            TerminologyDetails(
                name='tech-terms',
                description='Technical terminology',
                source_language='',
                target_languages=['es'],
                term_count=100,
            )

    def test_empty_target_languages_raises_error(self):
        """Test that empty target languages raises ValueError."""
        with pytest.raises(ValueError, match='target_languages cannot be empty'):
            TerminologyDetails(
                name='tech-terms',
                description='Technical terminology',
                source_language='en',
                target_languages=[],
                term_count=100,
            )

    def test_negative_size_bytes_raises_error(self):
        """Test that negative size bytes raises ValueError."""
        with pytest.raises(ValueError, match='size_bytes cannot be negative'):
            TerminologyDetails(
                name='tech-terms',
                description='Technical terminology',
                source_language='en',
                target_languages=['es'],
                term_count=100,
                size_bytes=-1,
            )


class TestTerminologySummary:
    """Test TerminologySummary model."""

    def test_valid_terminology_summary(self):
        """Test creating a valid terminology summary."""
        now = datetime.now()
        summary = TerminologySummary(
            name='tech-terms',
            description='Technical terminology',
            source_language='en',
            target_languages=['es', 'fr'],
            term_count=100,
            created_at=now,
        )

        assert summary.name == 'tech-terms'
        assert summary.description == 'Technical terminology'
        assert summary.source_language == 'en'
        assert summary.target_languages == ['es', 'fr']
        assert summary.term_count == 100
        assert summary.created_at == now

    def test_empty_name_raises_error(self):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match='name cannot be empty'):
            TerminologySummary(
                name='',
                description='Technical terminology',
                source_language='en',
                target_languages=['es'],
                term_count=100,
            )

    def test_empty_source_language_raises_error(self):
        """Test that empty source language raises ValueError."""
        with pytest.raises(ValueError, match='source_language cannot be empty'):
            TerminologySummary(
                name='tech-terms',
                description='Technical terminology',
                source_language='',
                target_languages=['es'],
                term_count=100,
            )

    def test_empty_target_languages_raises_error(self):
        """Test that empty target languages raises ValueError."""
        with pytest.raises(ValueError, match='target_languages cannot be empty'):
            TerminologySummary(
                name='tech-terms',
                description='Technical terminology',
                source_language='en',
                target_languages=[],
                term_count=100,
            )

    def test_negative_term_count_raises_error(self):
        """Test that negative term count raises ValueError."""
        with pytest.raises(ValueError, match='term_count cannot be negative'):
            TerminologySummary(
                name='tech-terms',
                description='Technical terminology',
                source_language='en',
                target_languages=['es'],
                term_count=-1,
            )


class TestLanguagePair:
    """Test LanguagePair model."""

    def test_valid_language_pair(self):
        """Test creating a valid language pair."""
        pair = LanguagePair(
            source_language='en',
            target_language='es',
            supported_formats=['text/plain', 'text/html'],
            custom_terminology_supported=True,
        )

        assert pair.source_language == 'en'
        assert pair.target_language == 'es'
        assert pair.supported_formats == ['text/plain', 'text/html']
        assert pair.custom_terminology_supported is True

    def test_same_source_target_raises_error(self):
        """Test that same source and target language raises ValueError."""
        with pytest.raises(
            ValueError, match='source_language and target_language cannot be the same'
        ):
            LanguagePair(source_language='en', target_language='en')

    def test_empty_source_language_raises_error(self):
        """Test that empty source language raises ValueError."""
        with pytest.raises(ValueError, match='source_language cannot be empty'):
            LanguagePair(source_language='', target_language='es')

    def test_empty_target_language_raises_error(self):
        """Test that empty target language raises ValueError."""
        with pytest.raises(ValueError, match='target_language cannot be empty'):
            LanguagePair(source_language='en', target_language='')


class TestLanguageMetrics:
    """Test LanguageMetrics model."""

    def test_valid_language_metrics(self):
        """Test creating valid language metrics."""
        metrics = LanguageMetrics(
            language_pair='en-es',
            translation_count=100,
            character_count=5000,
            average_response_time=0.5,
            error_rate=0.01,
            time_range='24h',
        )

        assert metrics.language_pair == 'en-es'
        assert metrics.translation_count == 100
        assert metrics.character_count == 5000
        assert metrics.average_response_time == 0.5
        assert metrics.error_rate == 0.01
        assert metrics.time_range == '24h'

    def test_negative_values_raise_error(self):
        """Test that negative values raise ValueError."""
        with pytest.raises(ValueError, match='translation_count cannot be negative'):
            LanguageMetrics(translation_count=-1)

        with pytest.raises(ValueError, match='character_count cannot be negative'):
            LanguageMetrics(character_count=-1)

        with pytest.raises(ValueError, match='average_response_time cannot be negative'):
            LanguageMetrics(average_response_time=-1.0)

    def test_invalid_error_rate_raises_error(self):
        """Test that invalid error rate raises ValueError."""
        with pytest.raises(ValueError, match='error_rate must be between 0.0 and 1.0'):
            LanguageMetrics(error_rate=1.5)


class TestErrorResponse:
    """Test ErrorResponse model."""

    def test_valid_error_response(self):
        """Test creating a valid error response."""
        error = ErrorResponse(
            error_type='ValidationError',
            error_code='VALIDATION_ERROR',
            message='Invalid input',
            details={'field': 'source_language'},
            retry_after=30,
        )

        assert error.error_type == 'ValidationError'
        assert error.error_code == 'VALIDATION_ERROR'
        assert error.message == 'Invalid input'
        assert error.details == {'field': 'source_language'}
        assert error.retry_after == 30

    def test_negative_retry_after_raises_error(self):
        """Test that negative retry_after raises ValueError."""
        with pytest.raises(ValueError, match='retry_after cannot be negative'):
            ErrorResponse(
                error_type='RateLimitError',
                error_code='RATE_LIMIT_ERROR',
                message='Rate limit exceeded',
                retry_after=-1,
            )

    def test_empty_error_type_raises_error(self):
        """Test that empty error type raises ValueError."""
        with pytest.raises(ValueError, match='error_type cannot be empty'):
            ErrorResponse(error_type='', error_code='VALIDATION_ERROR', message='Invalid input')

    def test_empty_error_code_raises_error(self):
        """Test that empty error code raises ValueError."""
        with pytest.raises(ValueError, match='error_code cannot be empty'):
            ErrorResponse(error_type='ValidationError', error_code='', message='Invalid input')

    def test_empty_message_raises_error(self):
        """Test that empty message raises ValueError."""
        with pytest.raises(ValueError, match='message cannot be empty'):
            ErrorResponse(error_type='ValidationError', error_code='VALIDATION_ERROR', message='')


class TestExceptions:
    """Test exception hierarchy."""

    def test_translate_exception(self):
        """Test base TranslateException."""
        exc = TranslateException('Test error', 'TEST_ERROR', {'key': 'value'})

        assert str(exc) == 'Test error'
        assert exc.message == 'Test error'
        assert exc.error_code == 'TEST_ERROR'
        assert exc.details == {'key': 'value'}

        error_response = exc.to_error_response()
        assert error_response.error_type == 'TranslateException'
        assert error_response.error_code == 'TEST_ERROR'
        assert error_response.message == 'Test error'
        assert error_response.details == {'key': 'value'}

    def test_authentication_error(self):
        """Test AuthenticationError."""
        exc = AuthenticationError('Auth failed', {'reason': 'invalid_credentials'})

        assert exc.error_code == 'AUTH_ERROR'
        assert exc.details == {'reason': 'invalid_credentials'}

    def test_validation_error(self):
        """Test ValidationError."""
        exc = ValidationError('Invalid field', field='source_language')

        assert exc.error_code == 'VALIDATION_ERROR'
        assert exc.details == {'field': 'source_language'}

    def test_translation_error(self):
        """Test TranslationError."""
        exc = TranslationError('Translation failed', source_lang='en', target_lang='es')

        assert exc.error_code == 'TRANSLATION_ERROR'
        assert exc.details == {'source_language': 'en', 'target_language': 'es'}

    def test_terminology_error(self):
        """Test TerminologyError."""
        exc = TerminologyError('Terminology not found', terminology_name='tech-terms')

        assert exc.error_code == 'TERMINOLOGY_ERROR'
        assert exc.details == {'terminology_name': 'tech-terms'}

    def test_batch_job_error(self):
        """Test BatchJobError."""
        exc = BatchJobError('Job failed', job_id='job-123')

        assert exc.error_code == 'BATCH_JOB_ERROR'
        assert exc.details == {'job_id': 'job-123'}

    def test_rate_limit_error(self):
        """Test RateLimitError."""
        exc = RateLimitError('Rate limit exceeded', retry_after=60)

        assert exc.error_code == 'RATE_LIMIT_ERROR'
        assert exc.retry_after == 60

        error_response = exc.to_error_response()
        assert error_response.retry_after == 60

    def test_service_unavailable_error(self):
        """Test ServiceUnavailableError."""
        exc = ServiceUnavailableError('Service down', service='translate')

        assert exc.error_code == 'SERVICE_UNAVAILABLE'
        assert exc.details == {'service': 'translate'}

    def test_quota_exceeded_error(self):
        """Test QuotaExceededError."""
        exc = QuotaExceededError('Quota exceeded', quota_type='translation_requests')

        assert exc.error_code == 'QUOTA_EXCEEDED'
        assert exc.details == {'quota_type': 'translation_requests'}


class TestEnums:
    """Test enum values."""

    def test_job_status_enum(self):
        """Test JobStatus enum values."""
        assert JobStatus.SUBMITTED.value == 'SUBMITTED'
        assert JobStatus.IN_PROGRESS.value == 'IN_PROGRESS'
        assert JobStatus.COMPLETED.value == 'COMPLETED'
        assert JobStatus.FAILED.value == 'FAILED'
        assert JobStatus.STOPPED.value == 'STOPPED'

    def test_content_type_enum(self):
        """Test ContentType enum values."""
        assert ContentType.TEXT_PLAIN.value == 'text/plain'
        assert ContentType.TEXT_HTML.value == 'text/html'
        assert (
            ContentType.APPLICATION_DOCX.value
            == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    def test_terminology_format_enum(self):
        """Test TerminologyFormat enum values."""
        assert TerminologyFormat.CSV.value == 'CSV'
        assert TerminologyFormat.TMX.value == 'TMX'
