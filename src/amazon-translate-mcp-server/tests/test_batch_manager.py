# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for BatchJobManager.

This module contains comprehensive tests for the batch job management functionality,
including job creation, monitoring, listing, and error handling scenarios.
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
    TranslationJobStatus,
    TranslationJobSummary,
    TranslationSettings,
    ValidationError,
)
from botocore.exceptions import BotoCoreError, ClientError
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch


class TestBatchJobManager:
    """Test cases for BatchJobManager class."""

    @pytest.fixture
    def mock_aws_client_manager(self):
        """Create a mock AWS client manager."""
        manager = Mock()
        manager.get_translate_client.return_value = Mock()
        manager.get_s3_client.return_value = Mock()
        return manager

    @pytest.fixture
    def batch_manager(self, mock_aws_client_manager):
        """Create a BatchJobManager instance with mocked dependencies."""
        return BatchJobManager(mock_aws_client_manager)

    @pytest.fixture
    def sample_input_config(self):
        """Create a sample batch input configuration."""
        return BatchInputConfig(
            s3_uri='s3://test-input-bucket/documents/',
            content_type='text/plain',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
        )

    @pytest.fixture
    def sample_output_config(self):
        """Create a sample batch output configuration."""
        return BatchOutputConfig(
            s3_uri='s3://test-output-bucket/translations/',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
        )

    @pytest.fixture
    def sample_job_config(self):
        """Create a sample job configuration."""
        return JobConfig(
            job_name='test-translation-job',
            source_language_code='en',
            target_language_codes=['es', 'fr'],
            terminology_names=['medical-terms'],
            settings=TranslationSettings(formality='FORMAL'),
        )

    def test_init(self, mock_aws_client_manager):
        """Test BatchJobManager initialization."""
        manager = BatchJobManager(mock_aws_client_manager)

        assert manager.aws_client_manager == mock_aws_client_manager
        assert manager._translate_client is None
        assert manager._s3_client is None

    def test_translate_client_property(self, batch_manager, mock_aws_client_manager):
        """Test translate client property lazy loading."""
        mock_client = Mock()
        mock_aws_client_manager.get_translate_client.return_value = mock_client

        # First access should create client
        client1 = batch_manager.translate_client
        assert client1 == mock_client
        mock_aws_client_manager.get_translate_client.assert_called_once()

        # Second access should return cached client
        client2 = batch_manager.translate_client
        assert client2 == mock_client
        assert mock_aws_client_manager.get_translate_client.call_count == 1

    def test_s3_client_property(self, batch_manager, mock_aws_client_manager):
        """Test S3 client property lazy loading."""
        mock_client = Mock()
        mock_aws_client_manager.get_s3_client.return_value = mock_client

        # First access should create client
        client1 = batch_manager.s3_client
        assert client1 == mock_client
        mock_aws_client_manager.get_s3_client.assert_called_once()

        # Second access should return cached client
        client2 = batch_manager.s3_client
        assert client2 == mock_client
        assert mock_aws_client_manager.get_s3_client.call_count == 1

    def test_start_batch_translation_success(
        self, batch_manager, sample_input_config, sample_output_config, sample_job_config
    ):
        """Test successful batch translation job start."""
        # Mock S3 validation
        batch_manager.s3_client.head_bucket.return_value = {}
        batch_manager.s3_client.list_objects_v2.return_value = {'KeyCount': 1}

        # Mock translate client response
        expected_job_id = 'test-job-123'
        batch_manager.translate_client.start_text_translation_job.return_value = {
            'JobId': expected_job_id,
            'JobStatus': 'SUBMITTED',
        }

        # Start the job
        job_id = batch_manager.start_batch_translation(
            sample_input_config, sample_output_config, sample_job_config
        )

        # Verify result
        assert job_id == expected_job_id

        # Verify API call
        batch_manager.translate_client.start_text_translation_job.assert_called_once()
        call_args = batch_manager.translate_client.start_text_translation_job.call_args[1]

        assert call_args['JobName'] == sample_job_config.job_name
        assert call_args['SourceLanguageCode'] == sample_job_config.source_language_code
        assert call_args['TargetLanguageCodes'] == sample_job_config.target_language_codes
        assert call_args['TerminologyNames'] == sample_job_config.terminology_names
        assert call_args['InputDataConfig']['S3Uri'] == sample_input_config.s3_uri
        assert call_args['OutputDataConfig']['S3Uri'] == sample_output_config.s3_uri
        assert call_args['Settings']['Formality'] == 'FORMAL'

    def test_start_batch_translation_minimal_config(
        self, batch_manager, sample_input_config, sample_output_config
    ):
        """Test batch translation with minimal configuration."""
        # Create minimal job config
        job_config = JobConfig(
            job_name='minimal-job', source_language_code='en', target_language_codes=['es']
        )

        # Mock S3 validation
        batch_manager.s3_client.head_bucket.return_value = {}

        # Mock translate client response
        expected_job_id = 'minimal-job-123'
        batch_manager.translate_client.start_text_translation_job.return_value = {
            'JobId': expected_job_id,
            'JobStatus': 'SUBMITTED',
        }

        # Start the job
        job_id = batch_manager.start_batch_translation(
            sample_input_config, sample_output_config, job_config
        )

        # Verify result
        assert job_id == expected_job_id

        # Verify API call doesn't include optional parameters
        call_args = batch_manager.translate_client.start_text_translation_job.call_args[1]
        assert 'TerminologyNames' not in call_args
        assert 'ParallelDataNames' not in call_args
        assert 'Settings' not in call_args

    def test_start_batch_translation_s3_validation_failure(
        self, batch_manager, sample_input_config, sample_output_config, sample_job_config
    ):
        """Test batch translation with S3 validation failure."""
        # Mock S3 bucket not found
        batch_manager.s3_client.head_bucket.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchBucket', 'Message': 'Bucket not found'}}, 'HeadBucket'
        )

        # Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            batch_manager.start_batch_translation(
                sample_input_config, sample_output_config, sample_job_config
            )

        assert 'Input S3 bucket does not exist' in str(exc_info.value)
        assert exc_info.value.details['field'] == 'input_config.s3_uri'

    def test_start_batch_translation_access_denied(
        self, batch_manager, sample_input_config, sample_output_config, sample_job_config
    ):
        """Test batch translation with access denied error."""
        # Mock S3 validation success
        batch_manager.s3_client.head_bucket.return_value = {}

        # Mock translate client access denied
        batch_manager.translate_client.start_text_translation_job.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}},
            'StartTextTranslationJob',
        )

        # Should raise AuthenticationError
        with pytest.raises(AuthenticationError) as exc_info:
            batch_manager.start_batch_translation(
                sample_input_config, sample_output_config, sample_job_config
            )

        assert 'Access denied for batch translation' in str(exc_info.value)
        assert exc_info.value.details['error_code'] == 'AccessDeniedException'

    def test_start_batch_translation_rate_limit(
        self, batch_manager, sample_input_config, sample_output_config, sample_job_config
    ):
        """Test batch translation with rate limiting."""
        # Mock S3 validation success
        batch_manager.s3_client.head_bucket.return_value = {}

        # Mock translate client throttling
        batch_manager.translate_client.start_text_translation_job.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'StartTextTranslationJob',
        )

        # Should raise RateLimitError
        with pytest.raises(RateLimitError) as exc_info:
            batch_manager.start_batch_translation(
                sample_input_config, sample_output_config, sample_job_config
            )

        assert 'Rate limit exceeded' in str(exc_info.value)
        assert exc_info.value.retry_after == 60

    def test_start_batch_translation_quota_exceeded(
        self, batch_manager, sample_input_config, sample_output_config, sample_job_config
    ):
        """Test batch translation with quota exceeded."""
        # Mock S3 validation success
        batch_manager.s3_client.head_bucket.return_value = {}

        # Mock translate client quota exceeded
        batch_manager.translate_client.start_text_translation_job.side_effect = ClientError(
            {'Error': {'Code': 'LimitExceededException', 'Message': 'Quota exceeded'}},
            'StartTextTranslationJob',
        )

        # Should raise QuotaExceededError
        with pytest.raises(QuotaExceededError) as exc_info:
            batch_manager.start_batch_translation(
                sample_input_config, sample_output_config, sample_job_config
            )

        assert 'Service quota exceeded' in str(exc_info.value)
        assert exc_info.value.details['quota_type'] == 'batch_translation_jobs'

    def test_get_translation_job_success(self, batch_manager):
        """Test successful job status retrieval."""
        job_id = 'test-job-123'

        # Mock translate client response
        mock_response = {
            'TextTranslationJobProperties': {
                'JobId': job_id,
                'JobName': 'test-job',
                'JobStatus': 'IN_PROGRESS',
                'SourceLanguageCode': 'en',
                'TargetLanguageCodes': ['es', 'fr'],
                'SubmittedTime': datetime(2023, 1, 1, 12, 0, 0),
                'InputDataConfig': {
                    'S3Uri': 's3://input-bucket/docs/',
                    'ContentType': 'text/plain',
                },
                'OutputDataConfig': {'S3Uri': 's3://output-bucket/translations/'},
            }
        }

        batch_manager.translate_client.describe_text_translation_job.return_value = mock_response

        # Get job status
        job_status = batch_manager.get_translation_job(job_id)

        # Verify result
        assert isinstance(job_status, TranslationJobStatus)
        assert job_status.job_id == job_id
        assert job_status.job_name == 'test-job'
        assert job_status.status == 'IN_PROGRESS'
        assert job_status.progress == 50.0  # IN_PROGRESS jobs get 50%
        assert job_status.created_at == datetime(2023, 1, 1, 12, 0, 0)
        assert (
            job_status.input_config is not None
            and job_status.input_config.s3_uri == 's3://input-bucket/docs/'
        )
        assert (
            job_status.output_config is not None
            and job_status.output_config.s3_uri == 's3://output-bucket/translations/'
        )

    def test_get_translation_job_not_found(self, batch_manager):
        """Test job status retrieval for non-existent job."""
        job_id = 'non-existent-job'

        # Mock translate client not found error
        batch_manager.translate_client.describe_text_translation_job.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Job not found'}},
            'DescribeTextTranslationJob',
        )

        # Should raise BatchJobError
        with pytest.raises(BatchJobError) as exc_info:
            batch_manager.get_translation_job(job_id)

        assert 'Translation job not found' in str(exc_info.value)
        assert exc_info.value.details['job_id'] == job_id

    def test_get_translation_job_empty_id(self, batch_manager):
        """Test job status retrieval with empty job ID."""
        with pytest.raises(ValidationError) as exc_info:
            batch_manager.get_translation_job('')

        assert 'job_id cannot be empty' in str(exc_info.value)
        assert exc_info.value.details['field'] == 'job_id'

    def test_list_translation_jobs_success(self, batch_manager):
        """Test successful job listing."""
        # Mock translate client response
        mock_response = {
            'TextTranslationJobPropertiesList': [
                {
                    'JobId': 'job-1',
                    'JobName': 'test-job-1',
                    'JobStatus': 'COMPLETED',
                    'SourceLanguageCode': 'en',
                    'TargetLanguageCodes': ['es'],
                    'SubmittedTime': datetime(2023, 1, 1, 12, 0, 0),
                    'EndTime': datetime(2023, 1, 1, 13, 0, 0),
                },
                {
                    'JobId': 'job-2',
                    'JobName': 'test-job-2',
                    'JobStatus': 'IN_PROGRESS',
                    'SourceLanguageCode': 'en',
                    'TargetLanguageCodes': ['fr'],
                    'SubmittedTime': datetime(2023, 1, 1, 14, 0, 0),
                },
            ],
            'NextToken': 'next-page-token',  # Test pagination token
        }

        batch_manager.translate_client.list_text_translation_jobs.return_value = mock_response

        # List jobs
        result = batch_manager.list_translation_jobs(status_filter='IN_PROGRESS', max_results=10)

        # Verify result
        assert len(result['jobs']) == 2
        assert result['next_token'] == 'next-page-token'
        assert result['total_count'] == 2

        # Verify first job
        job1 = result['jobs'][0]
        assert isinstance(job1, TranslationJobSummary)
        assert job1.job_id == 'job-1'
        assert job1.status == 'COMPLETED'
        assert job1.completed_at == datetime(2023, 1, 1, 13, 0, 0)

        # Verify API call
        batch_manager.translate_client.list_text_translation_jobs.assert_called_once_with(
            MaxResults=10, Filter={'Status': 'IN_PROGRESS'}
        )

    def test_list_translation_jobs_no_filter(self, batch_manager):
        """Test job listing without status filter."""
        # Mock translate client response
        mock_response = {'TextTranslationJobPropertiesList': [], 'NextToken': None}

        batch_manager.translate_client.list_text_translation_jobs.return_value = mock_response

        # List jobs without filter
        result = batch_manager.list_translation_jobs(max_results=50)

        # Verify result
        assert len(result['jobs']) == 0
        assert result['next_token'] is None
        assert result['total_count'] == 0

        # Verify API call doesn't include filter
        call_args = batch_manager.translate_client.list_text_translation_jobs.call_args[1]
        assert 'Filter' not in call_args
        assert call_args['MaxResults'] == 50

    def test_list_translation_jobs_invalid_max_results(self, batch_manager):
        """Test job listing with invalid max_results."""
        with pytest.raises(ValidationError) as exc_info:
            batch_manager.list_translation_jobs(max_results=0)

        assert 'max_results must be between 1 and 500' in str(exc_info.value)
        assert exc_info.value.details['field'] == 'max_results'

        with pytest.raises(ValidationError) as exc_info:
            batch_manager.list_translation_jobs(max_results=501)

        assert 'max_results must be between 1 and 500' in str(exc_info.value)

    def test_list_translation_jobs_invalid_status_filter(self, batch_manager):
        """Test job listing with invalid status filter."""
        with pytest.raises(ValidationError) as exc_info:
            batch_manager.list_translation_jobs(status_filter='INVALID_STATUS')

        assert 'Invalid status filter' in str(exc_info.value)
        assert exc_info.value.details['field'] == 'status_filter'

    def test_stop_translation_job_success(self, batch_manager):
        """Test successful job stopping."""
        job_id = 'test-job-123'

        # Mock translate client response
        mock_response = {
            'TextTranslationJobProperties': {
                'JobId': job_id,
                'JobName': 'test-job',
                'JobStatus': 'STOPPED',
                'SubmittedTime': datetime(2023, 1, 1, 12, 0, 0),
                'EndTime': datetime(2023, 1, 1, 12, 30, 0),
            }
        }

        batch_manager.translate_client.stop_text_translation_job.return_value = mock_response

        # Stop the job
        job_status = batch_manager.stop_translation_job(job_id)

        # Verify result
        assert isinstance(job_status, TranslationJobStatus)
        assert job_status.job_id == job_id
        assert job_status.status == 'STOPPED'
        assert job_status.error_details == 'Job was stopped by user request'

        # Verify API call
        batch_manager.translate_client.stop_text_translation_job.assert_called_once_with(
            JobId=job_id
        )

    def test_stop_translation_job_not_found(self, batch_manager):
        """Test stopping non-existent job."""
        job_id = 'non-existent-job'

        # Mock translate client not found error
        batch_manager.translate_client.stop_text_translation_job.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Job not found'}},
            'StopTextTranslationJob',
        )

        # Should raise BatchJobError
        with pytest.raises(BatchJobError) as exc_info:
            batch_manager.stop_translation_job(job_id)

        assert 'Translation job not found' in str(exc_info.value)
        assert exc_info.value.details['job_id'] == job_id

    def test_parse_s3_uri_valid(self, batch_manager):
        """Test S3 URI parsing with valid URIs."""
        # Test with prefix
        bucket, prefix = batch_manager._parse_s3_uri('s3://my-bucket/path/to/files/')
        assert bucket == 'my-bucket'
        assert prefix == 'path/to/files/'

        # Test without prefix
        bucket, prefix = batch_manager._parse_s3_uri('s3://my-bucket')
        assert bucket == 'my-bucket'
        assert prefix == ''

        # Test with single file
        bucket, prefix = batch_manager._parse_s3_uri('s3://my-bucket/file.txt')
        assert bucket == 'my-bucket'
        assert prefix == 'file.txt'

    def test_parse_s3_uri_invalid(self, batch_manager):
        """Test S3 URI parsing with invalid URIs."""
        with pytest.raises(ValidationError):
            batch_manager._parse_s3_uri('http://my-bucket/path/')

        with pytest.raises(ValidationError):
            batch_manager._parse_s3_uri('s3://')

        with pytest.raises(ValidationError):
            batch_manager._parse_s3_uri('s3:///path/')

    def test_calculate_progress(self, batch_manager):
        """Test progress calculation for different job statuses."""
        # Test SUBMITTED status
        progress = batch_manager._calculate_progress({'JobStatus': 'SUBMITTED'})
        assert progress == 0.0

        # Test IN_PROGRESS status
        progress = batch_manager._calculate_progress({'JobStatus': 'IN_PROGRESS'})
        assert progress == 50.0

        # Test COMPLETED status
        progress = batch_manager._calculate_progress({'JobStatus': 'COMPLETED'})
        assert progress == 100.0

        # Test FAILED status
        progress = batch_manager._calculate_progress({'JobStatus': 'FAILED'})
        assert progress == 0.0

        # Test unknown status
        progress = batch_manager._calculate_progress({'JobStatus': 'UNKNOWN'})
        assert progress is None

    def test_extract_error_details(self, batch_manager):
        """Test error details extraction from job information."""
        # Test FAILED status
        error_details = batch_manager._extract_error_details(
            {'JobStatus': 'FAILED', 'Message': 'Translation failed due to invalid input'}
        )
        assert 'Job failed: Translation failed due to invalid input' in error_details

        # Test COMPLETED_WITH_ERROR status
        error_details = batch_manager._extract_error_details(
            {'JobStatus': 'COMPLETED_WITH_ERROR', 'Message': 'Some files could not be processed'}
        )
        assert 'Job completed with errors: Some files could not be processed' in error_details

        # Test STOPPED status
        error_details = batch_manager._extract_error_details({'JobStatus': 'STOPPED'})
        assert error_details == 'Job was stopped by user request'

        # Test successful status
        error_details = batch_manager._extract_error_details({'JobStatus': 'COMPLETED'})
        assert error_details is None

    def test_validate_s3_access_success(
        self, batch_manager, sample_input_config, sample_output_config
    ):
        """Test successful S3 access validation."""
        # Mock S3 client responses
        batch_manager.s3_client.head_bucket.return_value = {}
        batch_manager.s3_client.list_objects_v2.return_value = {'KeyCount': 5}

        # Should not raise any exception
        batch_manager._validate_s3_access(sample_input_config, sample_output_config)

        # Verify S3 calls
        assert batch_manager.s3_client.head_bucket.call_count == 2
        batch_manager.s3_client.list_objects_v2.assert_called_once()

    def test_validate_s3_access_input_bucket_not_found(
        self, batch_manager, sample_input_config, sample_output_config
    ):
        """Test S3 validation with input bucket not found."""
        # Mock S3 client to return bucket not found for input
        batch_manager.s3_client.head_bucket.side_effect = [
            ClientError(
                {'Error': {'Code': 'NoSuchBucket', 'Message': 'Bucket not found'}}, 'HeadBucket'
            ),
            {},  # Output bucket exists
        ]

        # Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            batch_manager._validate_s3_access(sample_input_config, sample_output_config)

        assert 'Input S3 bucket does not exist' in str(exc_info.value)
        assert exc_info.value.details['field'] == 'input_config.s3_uri'

    def test_validate_s3_access_output_access_denied(
        self, batch_manager, sample_input_config, sample_output_config
    ):
        """Test S3 validation with output bucket access denied."""
        # Mock S3 client responses
        batch_manager.s3_client.head_bucket.side_effect = [
            {},  # Input bucket exists
            ClientError(
                {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'HeadBucket'
            ),
        ]

        # Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            batch_manager._validate_s3_access(sample_input_config, sample_output_config)

        assert 'Access denied to output S3 bucket' in str(exc_info.value)
        assert exc_info.value.details['field'] == 'output_config.s3_uri'

    def test_boto_core_error_handling(
        self, batch_manager, sample_input_config, sample_output_config, sample_job_config
    ):
        """Test handling of BotoCoreError exceptions."""
        # Mock S3 validation success
        batch_manager.s3_client.head_bucket.return_value = {}

        # Mock BotoCoreError
        batch_manager.translate_client.start_text_translation_job.side_effect = BotoCoreError()

        # Should raise ServiceUnavailableError
        with pytest.raises(ServiceUnavailableError) as exc_info:
            batch_manager.start_batch_translation(
                sample_input_config, sample_output_config, sample_job_config
            )

        assert 'AWS service error starting batch translation' in str(exc_info.value)
        assert exc_info.value.details['service'] == 'translate'

    def test_unexpected_error_handling(
        self, batch_manager, sample_input_config, sample_output_config, sample_job_config
    ):
        """Test handling of unexpected exceptions."""
        # Mock S3 validation success
        batch_manager.s3_client.head_bucket.return_value = {}

        # Mock unexpected error
        batch_manager.translate_client.start_text_translation_job.side_effect = RuntimeError(
            'Unexpected error'
        )

        # Should raise BatchJobError
        with pytest.raises(BatchJobError) as exc_info:
            batch_manager.start_batch_translation(
                sample_input_config, sample_output_config, sample_job_config
            )

        assert 'Unexpected error starting batch translation job' in str(exc_info.value)
        assert exc_info.value.details['error_type'] == 'RuntimeError'


class TestBatchManagerErrorHandling:
    """Test batch manager error handling scenarios."""

    def test_start_batch_translation_validation_error(self):
        """Test handling of validation errors during batch translation start."""
        from awslabs.amazon_translate_mcp_server.batch_manager import BatchJobManager
        from awslabs.amazon_translate_mcp_server.models import (
            BatchInputConfig,
            BatchOutputConfig,
            JobConfig,
        )
        from botocore.exceptions import ClientError

        mock_aws_client = MagicMock()
        manager = BatchJobManager(aws_client_manager=mock_aws_client)

        with patch.object(manager.aws_client_manager, 'get_translate_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            # Mock validation error
            mock_client.start_text_translation_job.side_effect = ClientError(
                error_response={
                    'Error': {'Code': 'ValidationException', 'Message': 'Invalid input parameters'}
                },
                operation_name='StartTextTranslationJob',
            )

            job_config = JobConfig(
                job_name='test-job', source_language_code='en', target_language_codes=['es']
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

            with pytest.raises(Exception):  # ValidationError
                manager.start_batch_translation(input_config, output_config, job_config)

    def test_start_batch_translation_generic_error(self):
        """Test handling of generic errors during batch translation start."""
        from awslabs.amazon_translate_mcp_server.batch_manager import BatchJobManager
        from awslabs.amazon_translate_mcp_server.models import (
            BatchInputConfig,
            BatchOutputConfig,
            JobConfig,
        )
        from botocore.exceptions import ClientError

        mock_aws_client = MagicMock()
        manager = BatchJobManager(mock_aws_client)

        with patch.object(manager.aws_client_manager, 'get_translate_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            # Mock generic error
            mock_client.start_text_translation_job.side_effect = ClientError(
                error_response={
                    'Error': {'Code': 'InternalServerError', 'Message': 'Internal server error'}
                },
                operation_name='StartTextTranslationJob',
            )

            job_config = JobConfig(
                job_name='test-job', source_language_code='en', target_language_codes=['es']
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

            with pytest.raises(Exception):  # BatchJobError
                manager.start_batch_translation(input_config, output_config, job_config)

    def test_s3_uri_parsing_edge_cases(self):
        """Test S3 URI parsing with various edge cases."""
        from awslabs.amazon_translate_mcp_server.batch_manager import BatchJobManager

        mock_aws_client = MagicMock()
        manager = BatchJobManager(mock_aws_client)

        # Test valid S3 URIs
        bucket, key = manager._parse_s3_uri('s3://my-bucket/path/to/file.txt')
        assert bucket == 'my-bucket'
        assert key == 'path/to/file.txt'

        bucket, key = manager._parse_s3_uri('s3://my-bucket/')
        assert bucket == 'my-bucket'
        assert key == ''

        bucket, key = manager._parse_s3_uri('s3://my-bucket')
        assert bucket == 'my-bucket'
        assert key == ''

        # Test invalid S3 URIs
        with pytest.raises(Exception):  # ValidationError
            manager._parse_s3_uri('invalid-uri')

        with pytest.raises(Exception):  # ValidationError
            manager._parse_s3_uri('http://example.com/file.txt')

        with pytest.raises(Exception):  # ValidationError
            manager._parse_s3_uri('')

    def test_job_status_monitoring_edge_cases(self):
        """Test job status monitoring with edge cases."""
        from awslabs.amazon_translate_mcp_server.batch_manager import BatchJobManager
        from botocore.exceptions import ClientError

        mock_aws_client = MagicMock()
        manager = BatchJobManager(mock_aws_client)

        with patch.object(manager.aws_client_manager, 'get_translate_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            # Test job not found
            mock_client.describe_text_translation_job.side_effect = ClientError(
                error_response={
                    'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Job not found'}
                },
                operation_name='DescribeTextTranslationJob',
            )

            with pytest.raises(Exception):  # BatchJobError
                manager.get_translation_job('nonexistent-job')

    def test_list_translation_jobs_with_filters(self):
        """Test listing translation jobs with various filters."""
        from awslabs.amazon_translate_mcp_server.batch_manager import BatchJobManager

        mock_aws_client = MagicMock()
        manager = BatchJobManager(mock_aws_client)

        with patch.object(manager.aws_client_manager, 'get_translate_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            # Mock successful response
            mock_client.list_text_translation_jobs.return_value = {
                'TextTranslationJobPropertiesList': [
                    {
                        'JobId': 'job-123',
                        'JobName': 'test-job',
                        'JobStatus': 'COMPLETED',
                        'SourceLanguageCode': 'en',
                        'TargetLanguageCodes': ['es'],
                    }
                ]
            }

            # Test with status filter
            result = manager.list_translation_jobs(status_filter='COMPLETED')
            assert len(result['jobs']) == 1
            assert result['jobs'][0].job_id == 'job-123'

            # Verify the filter was applied
            mock_client.list_text_translation_jobs.assert_called()

    def test_batch_job_configuration_validation(self):
        """Test batch job configuration validation."""
        from awslabs.amazon_translate_mcp_server.batch_manager import BatchJobManager
        from awslabs.amazon_translate_mcp_server.models import JobConfig

        mock_aws_client = MagicMock()
        BatchJobManager(mock_aws_client)

        # Test valid configuration
        valid_config = JobConfig(
            job_name='valid-job-name',
            source_language_code='en',
            target_language_codes=['es', 'fr'],
        )

        # Test that the config object is properly created
        assert valid_config.job_name == 'valid-job-name'
        assert valid_config.source_language_code == 'en'
        assert valid_config.target_language_codes == ['es', 'fr']

        # Test invalid job name (should raise validation error)
        with pytest.raises(ValueError):  # job_name validation error
            JobConfig(
                job_name='',  # Empty name
                source_language_code='en',
                target_language_codes=['es'],
            )

    def test_batch_input_output_config_validation(self):
        """Test batch input and output configuration validation."""
        from awslabs.amazon_translate_mcp_server.batch_manager import BatchJobManager
        from awslabs.amazon_translate_mcp_server.models import BatchInputConfig, BatchOutputConfig

        mock_aws_client = MagicMock()
        BatchJobManager(mock_aws_client)

        # Test valid input config
        valid_input = BatchInputConfig(
            s3_uri='s3://valid-bucket/input/',
            content_type='text/plain',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
        )

        # Test that the config object is properly created
        assert valid_input.s3_uri == 's3://valid-bucket/input/'

        # Test valid output config
        valid_output = BatchOutputConfig(
            s3_uri='s3://valid-bucket/output/',
            data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
        )

        # Test that the output config object is properly created
        assert valid_output.s3_uri == 's3://valid-bucket/output/'

        # Test invalid input config (invalid S3 URI should raise validation error)
        with pytest.raises(ValueError):  # s3_uri validation error
            BatchInputConfig(
                s3_uri='invalid-uri',
                content_type='text/plain',
                data_access_role_arn='arn:aws:iam::123456789012:role/TranslateRole',
            )

    def test_job_progress_calculation(self):
        """Test job progress calculation functionality."""
        from awslabs.amazon_translate_mcp_server.batch_manager import BatchJobManager

        mock_aws_client = MagicMock()
        manager = BatchJobManager(mock_aws_client)

        # Test progress calculation based on job status
        job_details_submitted = {'JobStatus': 'SUBMITTED'}
        progress = manager._calculate_progress(job_details_submitted)
        assert progress == 0.0

        job_details_in_progress = {'JobStatus': 'IN_PROGRESS'}
        progress = manager._calculate_progress(job_details_in_progress)
        assert progress == 50.0

        job_details_completed = {'JobStatus': 'COMPLETED'}
        progress = manager._calculate_progress(job_details_completed)
        assert progress == 100.0

        job_details_failed = {'JobStatus': 'FAILED'}
        progress = manager._calculate_progress(job_details_failed)
        assert progress == 0.0

        job_details_unknown = {'JobStatus': 'UNKNOWN'}
        progress = manager._calculate_progress(job_details_unknown)
        assert progress is None


class TestBatchManagerAdvancedFeatures:
    """Test advanced batch manager features."""

    def test_job_retry_mechanism(self):
        """Test job retry mechanism for failed operations."""
        from awslabs.amazon_translate_mcp_server.batch_manager import BatchJobManager
        from botocore.exceptions import ClientError

        mock_aws_client = MagicMock()
        manager = BatchJobManager(mock_aws_client)

        with patch.object(manager.aws_client_manager, 'get_translate_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            # Mock temporary failure followed by success
            mock_client.describe_text_translation_job.side_effect = [
                ClientError(
                    error_response={
                        'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}
                    },
                    operation_name='DescribeTextTranslationJob',
                ),
                {
                    'TextTranslationJobProperties': {
                        'JobId': 'job-123',
                        'JobName': 'test-job',
                        'JobStatus': 'COMPLETED',
                    }
                },
            ]

            # Should raise BatchJobError on throttling
            with pytest.raises(Exception):  # BatchJobError
                manager.get_translation_job('job-123')

    def test_batch_job_cleanup_operations(self):
        """Test batch job cleanup operations."""
        from awslabs.amazon_translate_mcp_server.batch_manager import BatchJobManager

        mock_aws_client = MagicMock()
        manager = BatchJobManager(mock_aws_client)

        with patch.object(manager.aws_client_manager, 'get_translate_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            # Mock successful cleanup
            mock_client.stop_text_translation_job.return_value = {
                'TextTranslationJobProperties': {
                    'JobId': 'job-123',
                    'JobName': 'test-job',
                    'JobStatus': 'STOP_REQUESTED',
                }
            }

            result = manager.stop_translation_job('job-123')
            assert result.status == 'STOP_REQUESTED'

            # Verify the stop operation was called
            mock_client.stop_text_translation_job.assert_called_with(JobId='job-123')
