"""Extended unit tests for Batch Manager.

This module contains additional comprehensive unit tests for the BatchJobManager class
to improve coverage of uncovered areas, especially error handling and edge cases.
"""

import pytest
from awslabs.amazon_translate_mcp_server.batch_manager import BatchJobManager
from awslabs.amazon_translate_mcp_server.models import (
    AuthenticationError,
    BatchInputConfig,
    BatchJobError,
    BatchOutputConfig,
    JobConfig,
    QuotaExceededError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
)
from botocore.exceptions import BotoCoreError, ClientError
from datetime import datetime
from unittest.mock import Mock


class TestBatchJobManagerExtended:
    """Extended tests for BatchJobManager class."""

    @pytest.fixture
    def mock_aws_client_manager(self):
        """Create mock AWS client manager."""
        mock_manager = Mock()
        mock_translate_client = Mock()
        mock_s3_client = Mock()

        mock_manager.get_translate_client.return_value = mock_translate_client
        mock_manager.get_s3_client.return_value = mock_s3_client

        return mock_manager, mock_translate_client, mock_s3_client

    @pytest.fixture
    def batch_manager(self, mock_aws_client_manager):
        """Create BatchJobManager instance with mocked AWS client."""
        mock_manager, _, _ = mock_aws_client_manager
        return BatchJobManager(mock_manager)

    def test_start_batch_translation_with_settings(self, batch_manager, mock_aws_client_manager):
        """Test batch translation start with translation settings."""
        _, mock_translate_client, mock_s3_client = mock_aws_client_manager

        # Mock S3 validation
        mock_s3_client.head_bucket.return_value = {}
        mock_s3_client.list_objects_v2.return_value = {'Contents': [{'Key': 'test.txt'}]}

        # Mock successful job start
        mock_translate_client.start_text_translation_job.return_value = {
            'JobId': 'job-with-settings-123',
            'JobStatus': 'SUBMITTED',
        }

        # Create job config with settings
        from awslabs.amazon_translate_mcp_server.models import TranslationSettings

        settings = TranslationSettings(formality='FORMAL', profanity='MASK', brevity='ON')

        input_config = BatchInputConfig(
            s3_uri='s3://test-bucket/input/',
            content_type='text/plain',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
        )

        output_config = BatchOutputConfig(
            s3_uri='s3://test-bucket/output/',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
        )

        job_config = JobConfig(
            job_name='test-job-with-settings',
            source_language_code='en',
            target_language_codes=['es', 'fr'],
            terminology_names=['tech-terms'],
            parallel_data_names=['parallel-data'],
            settings=settings,
        )

        job_id = batch_manager.start_batch_translation(input_config, output_config, job_config)

        assert job_id == 'job-with-settings-123'

        # Verify the API call included settings
        call_args = mock_translate_client.start_text_translation_job.call_args[1]
        assert 'Settings' in call_args
        assert call_args['Settings']['Formality'] == 'FORMAL'
        assert call_args['Settings']['Profanity'] == 'MASK'
        assert call_args['Settings']['Brevity'] == 'ON'
        assert 'TerminologyNames' in call_args
        assert 'ParallelDataNames' in call_args

    def test_start_batch_translation_throttling_error(
        self, batch_manager, mock_aws_client_manager
    ):
        """Test batch translation start with throttling error."""
        _, mock_translate_client, mock_s3_client = mock_aws_client_manager

        # Mock S3 validation
        mock_s3_client.head_bucket.return_value = {}
        mock_s3_client.list_objects_v2.return_value = {'Contents': [{'Key': 'test.txt'}]}

        # Mock throttling error
        error_response = {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}}
        mock_translate_client.start_text_translation_job.side_effect = ClientError(
            error_response, 'StartTextTranslationJob'
        )

        input_config = BatchInputConfig(
            s3_uri='s3://test-bucket/input/',
            content_type='text/plain',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
        )

        output_config = BatchOutputConfig(
            s3_uri='s3://test-bucket/output/',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
        )

        job_config = JobConfig(
            job_name='throttled-job', source_language_code='en', target_language_codes=['es']
        )

        with pytest.raises(RateLimitError) as exc_info:
            batch_manager.start_batch_translation(input_config, output_config, job_config)

        assert 'Rate limit exceeded' in str(exc_info.value)
        assert exc_info.value.retry_after == 60

    def test_start_batch_translation_quota_exceeded(self, batch_manager, mock_aws_client_manager):
        """Test batch translation start with quota exceeded error."""
        _, mock_translate_client, mock_s3_client = mock_aws_client_manager

        # Mock S3 validation
        mock_s3_client.head_bucket.return_value = {}
        mock_s3_client.list_objects_v2.return_value = {'Contents': [{'Key': 'test.txt'}]}

        # Mock quota exceeded error
        error_response = {
            'Error': {'Code': 'LimitExceededException', 'Message': 'Too many concurrent jobs'}
        }
        mock_translate_client.start_text_translation_job.side_effect = ClientError(
            error_response, 'StartTextTranslationJob'
        )

        input_config = BatchInputConfig(
            s3_uri='s3://test-bucket/input/',
            content_type='text/plain',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
        )

        output_config = BatchOutputConfig(
            s3_uri='s3://test-bucket/output/',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
        )

        job_config = JobConfig(
            job_name='quota-exceeded-job', source_language_code='en', target_language_codes=['es']
        )

        with pytest.raises(QuotaExceededError) as exc_info:
            batch_manager.start_batch_translation(input_config, output_config, job_config)

        assert 'Service quota exceeded' in str(exc_info.value)
        # Check if quota_type is in details if not as direct attribute
        quota_type = getattr(exc_info.value, 'quota_type', None)
        if quota_type is not None:
            assert quota_type == 'batch_translation_jobs'
        else:
            assert exc_info.value.details.get('quota_type') == 'batch_translation_jobs'

    def test_start_batch_translation_service_quota_exceeded(
        self, batch_manager, mock_aws_client_manager
    ):
        """Test batch translation start with service quota exceeded error."""
        _, mock_translate_client, mock_s3_client = mock_aws_client_manager

        # Mock S3 validation
        mock_s3_client.head_bucket.return_value = {}
        mock_s3_client.list_objects_v2.return_value = {'Contents': [{'Key': 'test.txt'}]}

        # Mock service quota exceeded error
        error_response = {
            'Error': {
                'Code': 'ServiceQuotaExceededException',
                'Message': 'Service quota exceeded for translation jobs',
            }
        }
        mock_translate_client.start_text_translation_job.side_effect = ClientError(
            error_response, 'StartTextTranslationJob'
        )

        input_config = BatchInputConfig(
            s3_uri='s3://test-bucket/input/',
            content_type='text/plain',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
        )

        output_config = BatchOutputConfig(
            s3_uri='s3://test-bucket/output/',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
        )

        job_config = JobConfig(
            job_name='service-quota-job', source_language_code='en', target_language_codes=['es']
        )

        with pytest.raises(QuotaExceededError) as exc_info:
            batch_manager.start_batch_translation(input_config, output_config, job_config)

        assert 'Service quota exceeded' in str(exc_info.value)

    def test_start_batch_translation_botocore_error(self, batch_manager, mock_aws_client_manager):
        """Test batch translation start with BotoCoreError."""
        _, mock_translate_client, mock_s3_client = mock_aws_client_manager

        # Mock S3 validation
        mock_s3_client.head_bucket.return_value = {}
        mock_s3_client.list_objects_v2.return_value = {'Contents': [{'Key': 'test.txt'}]}

        # Mock BotoCoreError
        mock_translate_client.start_text_translation_job.side_effect = BotoCoreError()

        input_config = BatchInputConfig(
            s3_uri='s3://test-bucket/input/',
            content_type='text/plain',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
        )

        output_config = BatchOutputConfig(
            s3_uri='s3://test-bucket/output/',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
        )

        job_config = JobConfig(
            job_name='botocore-error-job', source_language_code='en', target_language_codes=['es']
        )

        with pytest.raises(ServiceUnavailableError) as exc_info:
            batch_manager.start_batch_translation(input_config, output_config, job_config)

        assert 'AWS service error' in str(exc_info.value)
        # Check if service is available as attribute or in details
        service = getattr(exc_info.value, 'service', None)
        if service is not None:
            assert service == 'translate'
        else:
            assert exc_info.value.details.get('service') == 'translate'

    def test_get_translation_job_not_found(self, batch_manager, mock_aws_client_manager):
        """Test getting translation job that doesn't exist."""
        _, mock_translate_client, _ = mock_aws_client_manager

        # Mock job not found error
        error_response = {
            'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Job not found'}
        }
        mock_translate_client.describe_text_translation_job.side_effect = ClientError(
            error_response, 'DescribeTextTranslationJob'
        )

        with pytest.raises(BatchJobError) as exc_info:
            batch_manager.get_translation_job('nonexistent-job')

        assert 'Translation job not found' in str(exc_info.value)

    def test_get_translation_job_access_denied(self, batch_manager, mock_aws_client_manager):
        """Test getting translation job with access denied."""
        _, mock_translate_client, _ = mock_aws_client_manager

        # Mock access denied error
        error_response = {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}}
        mock_translate_client.describe_text_translation_job.side_effect = ClientError(
            error_response, 'DescribeTextTranslationJob'
        )

        with pytest.raises(AuthenticationError) as exc_info:
            batch_manager.get_translation_job('access-denied-job')

        assert 'Access denied' in str(exc_info.value)

    def test_get_translation_job_botocore_error(self, batch_manager, mock_aws_client_manager):
        """Test getting translation job with BotoCoreError."""
        _, mock_translate_client, _ = mock_aws_client_manager

        # Mock BotoCoreError
        mock_translate_client.describe_text_translation_job.side_effect = BotoCoreError()

        with pytest.raises(BatchJobError) as exc_info:
            batch_manager.get_translation_job('botocore-error-job')

        assert 'Unexpected error' in str(exc_info.value)

    def test_list_translation_jobs_with_filter(self, batch_manager, mock_aws_client_manager):
        """Test listing translation jobs with status filter."""
        _, mock_translate_client, _ = mock_aws_client_manager

        # Mock successful response
        mock_translate_client.list_text_translation_jobs.return_value = {
            'TextTranslationJobPropertiesList': [
                {
                    'JobId': 'job-1',
                    'JobName': 'test-job-1',
                    'JobStatus': 'COMPLETED',
                    'SourceLanguageCode': 'en',
                    'TargetLanguageCodes': ['es'],
                    'SubmittedTime': datetime.now(),
                    'EndTime': datetime.now(),
                },
                {
                    'JobId': 'job-2',
                    'JobName': 'test-job-2',
                    'JobStatus': 'COMPLETED',
                    'SourceLanguageCode': 'en',
                    'TargetLanguageCodes': ['fr'],
                    'SubmittedTime': datetime.now(),
                    'EndTime': datetime.now(),
                },
            ]
        }

        result = batch_manager.list_translation_jobs(status_filter='COMPLETED', max_results=10)

        assert len(result['jobs']) == 2
        assert all(job.status == 'COMPLETED' for job in result['jobs'])

        # Verify API call
        mock_translate_client.list_text_translation_jobs.assert_called_once_with(
            Filter={'Status': 'COMPLETED'}, MaxResults=10
        )

    def test_list_translation_jobs_no_filter(self, batch_manager, mock_aws_client_manager):
        """Test listing translation jobs without status filter."""
        _, mock_translate_client, _ = mock_aws_client_manager

        # Mock successful response
        mock_translate_client.list_text_translation_jobs.return_value = {
            'TextTranslationJobPropertiesList': []
        }

        result = batch_manager.list_translation_jobs(max_results=50)

        assert len(result['jobs']) == 0

        # Verify API call without filter
        mock_translate_client.list_text_translation_jobs.assert_called_once_with(MaxResults=50)

    def test_list_translation_jobs_client_error(self, batch_manager, mock_aws_client_manager):
        """Test listing translation jobs with client error."""
        _, mock_translate_client, _ = mock_aws_client_manager

        # Mock client error
        error_response = {
            'Error': {'Code': 'InvalidParameterException', 'Message': 'Invalid parameter'}
        }
        mock_translate_client.list_text_translation_jobs.side_effect = ClientError(
            error_response, 'ListTextTranslationJobs'
        )

        with pytest.raises(BatchJobError) as exc_info:
            batch_manager.list_translation_jobs()

        assert 'Failed to list translation jobs' in str(exc_info.value)

    def test_stop_translation_job_success(self, batch_manager, mock_aws_client_manager):
        """Test successful translation job stop."""
        _, mock_translate_client, _ = mock_aws_client_manager

        # Mock successful stop
        mock_translate_client.stop_text_translation_job.return_value = {
            'TextTranslationJobProperties': {
                'JobId': 'job-to-stop',
                'JobName': 'test-job',
                'JobStatus': 'STOP_REQUESTED',
                'SourceLanguageCode': 'en',
                'TargetLanguageCodes': ['es'],
                'SubmittedTime': datetime.now(),
            }
        }

        result = batch_manager.stop_translation_job('job-to-stop')

        assert result.job_id == 'job-to-stop'
        assert result.status == 'STOP_REQUESTED'
        mock_translate_client.stop_text_translation_job.assert_called_once_with(
            JobId='job-to-stop'
        )

    def test_stop_translation_job_not_found(self, batch_manager, mock_aws_client_manager):
        """Test stopping translation job that doesn't exist."""
        _, mock_translate_client, _ = mock_aws_client_manager

        # Mock job not found error
        error_response = {
            'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Job not found'}
        }
        mock_translate_client.stop_text_translation_job.side_effect = ClientError(
            error_response, 'StopTextTranslationJob'
        )

        with pytest.raises(BatchJobError) as exc_info:
            batch_manager.stop_translation_job('nonexistent-job')

        assert 'Translation job not found' in str(exc_info.value)

    def test_stop_translation_job_invalid_state(self, batch_manager, mock_aws_client_manager):
        """Test stopping translation job in invalid state."""
        _, mock_translate_client, _ = mock_aws_client_manager

        # Mock invalid state error
        error_response = {
            'Error': {
                'Code': 'InvalidRequestException',
                'Message': 'Job cannot be stopped in current state',
            }
        }
        mock_translate_client.stop_text_translation_job.side_effect = ClientError(
            error_response, 'StopTextTranslationJob'
        )

        with pytest.raises(BatchJobError) as exc_info:
            batch_manager.stop_translation_job('invalid-state-job')

        assert 'Job cannot be stopped' in str(exc_info.value)


class TestS3ValidationExtended:
    """Extended tests for S3 validation functionality."""

    @pytest.fixture
    def batch_manager(self):
        """Create BatchJobManager with mocked AWS client."""
        mock_aws_manager = Mock()
        mock_s3_client = Mock()
        mock_aws_manager.get_s3_client.return_value = mock_s3_client
        mock_aws_manager.get_translate_client.return_value = Mock()

        manager = BatchJobManager(mock_aws_manager)
        return manager, mock_s3_client

    def test_validate_s3_access_input_bucket_not_found(self, batch_manager):
        """Test S3 validation when input bucket doesn't exist."""
        manager, mock_s3_client = batch_manager

        # Mock bucket not found error
        error_response = {
            'Error': {'Code': 'NoSuchBucket', 'Message': 'The specified bucket does not exist'}
        }
        mock_s3_client.head_bucket.side_effect = ClientError(error_response, 'HeadBucket')

        input_config = BatchInputConfig(
            s3_uri='s3://nonexistent-bucket/input/',
            content_type='text/plain',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
        )

        output_config = BatchOutputConfig(
            s3_uri='s3://test-bucket/output/',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
        )

        with pytest.raises(ValidationError) as exc_info:
            manager._validate_s3_access(input_config, output_config)

        assert 'Input S3 bucket does not exist' in str(exc_info.value)

    def test_validate_s3_access_input_bucket_access_denied(self, batch_manager):
        """Test S3 validation when input bucket access is denied."""
        manager, mock_s3_client = batch_manager

        # Mock access denied error
        error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}
        mock_s3_client.head_bucket.side_effect = ClientError(error_response, 'HeadBucket')

        input_config = BatchInputConfig(
            s3_uri='s3://access-denied-bucket/input/',
            content_type='text/plain',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
        )

        output_config = BatchOutputConfig(
            s3_uri='s3://test-bucket/output/',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
        )

        with pytest.raises(ValidationError) as exc_info:
            manager._validate_s3_access(input_config, output_config)

        assert 'Access denied to input S3 bucket' in str(exc_info.value)

    def test_validate_s3_access_no_input_files(self, batch_manager):
        """Test S3 validation when no input files are found."""
        manager, mock_s3_client = batch_manager

        # Mock successful bucket access but no files
        mock_s3_client.head_bucket.return_value = {}
        mock_s3_client.list_objects_v2.return_value = {'KeyCount': 0}  # No files found

        input_config = BatchInputConfig(
            s3_uri='s3://empty-bucket/input/',
            content_type='text/plain',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
        )

        output_config = BatchOutputConfig(
            s3_uri='s3://test-bucket/output/',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
        )

        # This should not raise an error, just log a warning
        manager._validate_s3_access(input_config, output_config)  # Should succeed

    def test_validate_s3_access_output_bucket_creation_failed(self, batch_manager):
        """Test S3 validation when output bucket doesn't exist."""
        manager, mock_s3_client = batch_manager

        # Mock input validation success
        mock_s3_client.head_bucket.side_effect = [
            {},  # Input bucket exists
            ClientError(
                {'Error': {'Code': 'NoSuchBucket'}}, 'HeadBucket'
            ),  # Output bucket doesn't exist
        ]
        mock_s3_client.list_objects_v2.return_value = {'Contents': [{'Key': 'test.txt'}]}

        input_config = BatchInputConfig(
            s3_uri='s3://test-bucket/input/',
            content_type='text/plain',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
        )

        output_config = BatchOutputConfig(
            s3_uri='s3://new-bucket/output/',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
        )

        # Should raise ValidationError for missing output bucket
        with pytest.raises(ValidationError) as exc_info:
            manager._validate_s3_access(input_config, output_config)

        assert 'Output S3 bucket does not exist' in str(exc_info.value)

    def test_validate_s3_access_output_bucket_creation_access_denied(self, batch_manager):
        """Test S3 validation when output bucket access is denied."""
        manager, mock_s3_client = batch_manager

        # Mock input validation success
        mock_s3_client.head_bucket.side_effect = [
            {},  # Input bucket exists
            ClientError(
                {'Error': {'Code': 'AccessDenied'}}, 'HeadBucket'
            ),  # Output bucket access denied
        ]
        mock_s3_client.list_objects_v2.return_value = {'Contents': [{'Key': 'test.txt'}]}

        input_config = BatchInputConfig(
            s3_uri='s3://test-bucket/input/',
            content_type='text/plain',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
        )

        output_config = BatchOutputConfig(
            s3_uri='s3://denied-bucket/output/',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
        )

        with pytest.raises(ValidationError) as exc_info:
            manager._validate_s3_access(input_config, output_config)

        assert 'Access denied to output S3 bucket' in str(exc_info.value)
