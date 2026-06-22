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

"""Batch Job Manager for Amazon Translate MCP Server.

This module provides comprehensive batch translation job management including
job creation, monitoring, status tracking, and error handling with S3 integration.
"""

import logging
from .aws_client import AWSClientManager
from .models import (
    AuthenticationError,
    BatchInputConfig,
    BatchJobError,
    BatchOutputConfig,
    JobConfig,
    JobStatus,
    QuotaExceededError,
    RateLimitError,
    ServiceUnavailableError,
    TranslationJobStatus,
    TranslationJobSummary,
    ValidationError,
)
from botocore.exceptions import BotoCoreError, ClientError
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


class BatchJobManager:
    """Manages batch translation jobs with comprehensive monitoring and error handling.

    This class provides methods for starting batch translation jobs, monitoring their
    progress, listing jobs with filtering capabilities, and handling partial failures
    with recovery support.
    """

    def __init__(self, aws_client_manager: AWSClientManager):
        """Initialize the Batch Job Manager.

        Args:
            aws_client_manager: AWS client manager instance for service access

        """
        self.aws_client_manager = aws_client_manager
        self._translate_client = None
        self._s3_client = None

    @property
    def translate_client(self):
        """Get or create Amazon Translate client."""
        if self._translate_client is None:
            self._translate_client = self.aws_client_manager.get_translate_client()
        return self._translate_client

    @property
    def s3_client(self):
        """Get or create Amazon S3 client."""
        if self._s3_client is None:
            self._s3_client = self.aws_client_manager.get_s3_client()
        return self._s3_client

    def start_batch_translation(
        self,
        input_config: BatchInputConfig,
        output_config: BatchOutputConfig,
        job_config: JobConfig,
    ) -> str:
        """Start a batch translation job with S3 integration.

        Args:
            input_config: Configuration for input documents in S3
            output_config: Configuration for output location in S3
            job_config: Job configuration including languages and settings

        Returns:
            Job ID of the started batch translation job

        Raises:
            ValidationError: If input parameters are invalid
            AuthenticationError: If AWS credentials are insufficient
            BatchJobError: If job creation fails
            RateLimitError: If API rate limits are exceeded
            QuotaExceededError: If service quotas are exceeded

        """
        try:
            # Validate S3 access before starting the job
            self._validate_s3_access(input_config, output_config)

            # Prepare the request parameters
            request_params = {
                'JobName': job_config.job_name,
                'InputDataConfig': {
                    'S3Uri': input_config.s3_uri,
                    'ContentType': input_config.content_type,
                },
                'OutputDataConfig': {'S3Uri': output_config.s3_uri},
                'DataAccessRoleArn': input_config.data_access_role_arn,
                'SourceLanguageCode': job_config.source_language_code,
                'TargetLanguageCodes': job_config.target_language_codes,
            }

            # Add optional parameters
            if job_config.terminology_names:
                request_params['TerminologyNames'] = job_config.terminology_names

            if job_config.parallel_data_names:
                request_params['ParallelDataNames'] = job_config.parallel_data_names

            if job_config.settings:
                settings = {}
                if job_config.settings.formality:
                    settings['Formality'] = job_config.settings.formality
                if job_config.settings.profanity:
                    settings['Profanity'] = job_config.settings.profanity
                if job_config.settings.brevity:
                    settings['Brevity'] = job_config.settings.brevity

                if settings:
                    request_params['Settings'] = settings

            # Start the batch translation job
            logger.info(
                'Starting batch translation job: %s, source: %s, targets: %s',
                job_config.job_name,
                job_config.source_language_code,
                job_config.target_language_codes,
            )

            response = self.translate_client.start_text_translation_job(**request_params)
            job_id = response['JobId']

            logger.info(
                'Batch translation job started successfully. Job ID: %s, Status: %s',
                job_id,
                response.get('JobStatus', 'UNKNOWN'),
            )

            return job_id

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))

            if error_code == 'AccessDeniedException':
                raise AuthenticationError(
                    f'Access denied for batch translation: {error_message}',
                    details={'error_code': error_code, 'job_name': job_config.job_name},
                )
            elif error_code == 'ThrottlingException':
                raise RateLimitError(
                    f'Rate limit exceeded for batch translation: {error_message}',
                    retry_after=60,  # Suggest 1 minute retry
                    details={'error_code': error_code, 'job_name': job_config.job_name},
                )
            elif error_code in ['LimitExceededException', 'ServiceQuotaExceededException']:
                raise QuotaExceededError(
                    f'Service quota exceeded: {error_message}',
                    quota_type='batch_translation_jobs',
                    details={'error_code': error_code, 'job_name': job_config.job_name},
                )
            elif error_code == 'ValidationException':
                raise ValidationError(
                    f'Invalid batch translation parameters: {error_message}',
                    details={'error_code': error_code, 'job_name': job_config.job_name},
                )
            else:
                raise BatchJobError(
                    f'Failed to start batch translation job: {error_message}',
                    details={'error_code': error_code, 'job_name': job_config.job_name},
                )

        except BotoCoreError as e:
            raise ServiceUnavailableError(
                f'AWS service error starting batch translation: {str(e)}',
                service='translate',
                details={'error_type': type(e).__name__, 'job_name': job_config.job_name},
            )

        except ValidationError:
            # Re-raise validation errors without wrapping
            raise
        except Exception as e:
            raise BatchJobError(
                f'Unexpected error starting batch translation job: {str(e)}',
                details={'error_type': type(e).__name__, 'job_name': job_config.job_name},
            )

    def get_translation_job(self, job_id: str) -> TranslationJobStatus:
        """Get detailed status information for a translation job.

        Args:
            job_id: ID of the translation job to query

        Returns:
            Detailed job status information

        Raises:
            ValidationError: If job_id is invalid
            BatchJobError: If job retrieval fails
            AuthenticationError: If access is denied

        """
        if not job_id:
            raise ValidationError('job_id cannot be empty', field='job_id')

        try:
            logger.debug('Retrieving translation job status for job ID: %s', job_id)

            response = self.translate_client.describe_text_translation_job(JobId=job_id)
            job_details = response['TextTranslationJobProperties']

            # Parse job status information
            job_status = TranslationJobStatus(
                job_id=job_details['JobId'],
                job_name=job_details['JobName'],
                status=job_details['JobStatus'],
                progress=self._calculate_progress(job_details),
                input_config=self._parse_input_config(job_details.get('InputDataConfig')),
                output_config=self._parse_output_config(job_details.get('OutputDataConfig')),
                created_at=job_details.get('SubmittedTime'),
                completed_at=job_details.get('EndTime'),
                error_details=self._extract_error_details(job_details),
            )

            logger.debug(
                'Retrieved job status: %s, Status: %s, Progress: %s%%',
                job_id,
                job_status.status,
                job_status.progress or 0,
            )

            return job_status

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))

            if error_code == 'ResourceNotFoundException':
                raise BatchJobError(
                    f'Translation job not found: {job_id}',
                    job_id=job_id,
                    details={'error_code': error_code},
                )
            elif error_code == 'AccessDeniedException':
                raise AuthenticationError(
                    f'Access denied for job {job_id}: {error_message}',
                    details={'error_code': error_code, 'job_id': job_id},
                )
            else:
                raise BatchJobError(
                    f'Failed to retrieve job {job_id}: {error_message}',
                    job_id=job_id,
                    details={'error_code': error_code},
                )

        except Exception as e:
            raise BatchJobError(
                f'Unexpected error retrieving job {job_id}: {str(e)}',
                job_id=job_id,
                details={'error_type': type(e).__name__},
            )

    def list_translation_jobs(
        self,
        status_filter: Optional[str] = None,
        max_results: int = 50,
        next_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List translation jobs with filtering capabilities.

        Args:
            status_filter: Filter jobs by status (SUBMITTED, IN_PROGRESS, COMPLETED, FAILED, STOPPED)
            max_results: Maximum number of jobs to return (1-500)
            next_token: Token for pagination

        Returns:
            Dictionary containing job summaries and pagination token

        Raises:
            ValidationError: If parameters are invalid
            BatchJobError: If listing fails
            AuthenticationError: If access is denied

        """
        # Validate parameters
        if max_results < 1 or max_results > 500:
            raise ValidationError('max_results must be between 1 and 500', field='max_results')

        if status_filter and status_filter not in [status.value for status in JobStatus]:
            raise ValidationError(
                f'Invalid status filter: {status_filter}. Must be one of: {[s.value for s in JobStatus]}',
                field='status_filter',
            )

        try:
            request_params: Dict[str, Any] = {'MaxResults': max_results}

            if status_filter:
                request_params['Filter'] = {'Status': status_filter}

            if next_token:
                request_params['NextToken'] = next_token

            logger.debug(
                'Listing translation jobs with filter: %s, max_results: %d',
                status_filter or 'none',
                max_results,
            )

            response = self.translate_client.list_text_translation_jobs(**request_params)

            # Parse job summaries
            job_summaries = []
            for job_props in response.get('TextTranslationJobPropertiesList', []):
                summary = TranslationJobSummary(
                    job_id=job_props['JobId'],
                    job_name=job_props['JobName'],
                    status=job_props['JobStatus'],
                    source_language_code=job_props['SourceLanguageCode'],
                    target_language_codes=job_props['TargetLanguageCodes'],
                    created_at=job_props.get('SubmittedTime'),
                    completed_at=job_props.get('EndTime'),
                )
                job_summaries.append(summary)

            result = {
                'jobs': job_summaries,
                'next_token': response.get('NextToken'),
                'total_count': len(job_summaries),
            }

            logger.debug(
                'Listed %d translation jobs, has_more_pages: %s',
                len(job_summaries),
                'yes' if result['next_token'] else 'no',
            )

            return result

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))

            if error_code == 'AccessDeniedException':
                raise AuthenticationError(
                    f'Access denied for listing jobs: {error_message}',
                    details={'error_code': error_code},
                )
            elif error_code == 'ValidationException':
                raise ValidationError(
                    f'Invalid list parameters: {error_message}', details={'error_code': error_code}
                )
            else:
                raise BatchJobError(
                    f'Failed to list translation jobs: {error_message}',
                    details={'error_code': error_code},
                )

        except Exception as e:
            raise BatchJobError(
                f'Unexpected error listing translation jobs: {str(e)}',
                details={'error_type': type(e).__name__},
            )

    def stop_translation_job(self, job_id: str) -> TranslationJobStatus:
        """Stop a running translation job.

        Args:
            job_id: ID of the job to stop

        Returns:
            Updated job status after stopping

        Raises:
            ValidationError: If job_id is invalid
            BatchJobError: If job stopping fails
            AuthenticationError: If access is denied

        """
        if not job_id:
            raise ValidationError('job_id cannot be empty', field='job_id')

        try:
            logger.info('Stopping translation job: %s', job_id)

            response = self.translate_client.stop_text_translation_job(JobId=job_id)
            job_details = response['TextTranslationJobProperties']

            job_status = TranslationJobStatus(
                job_id=job_details['JobId'],
                job_name=job_details['JobName'],
                status=job_details['JobStatus'],
                progress=self._calculate_progress(job_details),
                created_at=job_details.get('SubmittedTime'),
                completed_at=job_details.get('EndTime'),
                error_details=self._extract_error_details(job_details),
            )

            logger.info('Translation job stopped: %s, Status: %s', job_id, job_status.status)
            return job_status

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))

            if error_code == 'ResourceNotFoundException':
                raise BatchJobError(
                    f'Translation job not found: {job_id}',
                    job_id=job_id,
                    details={'error_code': error_code},
                )
            elif error_code == 'AccessDeniedException':
                raise AuthenticationError(
                    f'Access denied for stopping job {job_id}: {error_message}',
                    details={'error_code': error_code, 'job_id': job_id},
                )
            else:
                raise BatchJobError(
                    f'Failed to stop job {job_id}: {error_message}',
                    job_id=job_id,
                    details={'error_code': error_code},
                )

        except Exception as e:
            raise BatchJobError(
                f'Unexpected error stopping job {job_id}: {str(e)}',
                job_id=job_id,
                details={'error_type': type(e).__name__},
            )

    def _validate_s3_access(
        self, input_config: BatchInputConfig, output_config: BatchOutputConfig
    ) -> None:
        """Validate S3 access for input and output locations.

        Args:
            input_config: Input configuration to validate
            output_config: Output configuration to validate

        Raises:
            ValidationError: If S3 locations are invalid or inaccessible

        """
        try:
            # Parse S3 URIs
            input_bucket, input_prefix = self._parse_s3_uri(input_config.s3_uri)
            output_bucket, output_prefix = self._parse_s3_uri(output_config.s3_uri)

            # Check if input bucket exists and is accessible
            try:
                self.s3_client.head_bucket(Bucket=input_bucket)
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                if error_code == 'NoSuchBucket':
                    raise ValidationError(
                        f'Input S3 bucket does not exist: {input_bucket}',
                        field='input_config.s3_uri',
                    )
                elif error_code in ['AccessDenied', 'Forbidden']:
                    raise ValidationError(
                        f'Access denied to input S3 bucket: {input_bucket}',
                        field='input_config.s3_uri',
                    )
                else:
                    raise ValidationError(
                        f'Cannot access input S3 bucket {input_bucket}: {e.response.get("Error", {}).get("Message", str(e))}',
                        field='input_config.s3_uri',
                    )

            # Check if output bucket exists and is accessible
            try:
                self.s3_client.head_bucket(Bucket=output_bucket)
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                if error_code == 'NoSuchBucket':
                    raise ValidationError(
                        f'Output S3 bucket does not exist: {output_bucket}',
                        field='output_config.s3_uri',
                    )
                elif error_code in ['AccessDenied', 'Forbidden']:
                    raise ValidationError(
                        f'Access denied to output S3 bucket: {output_bucket}',
                        field='output_config.s3_uri',
                    )
                else:
                    raise ValidationError(
                        f'Cannot access output S3 bucket {output_bucket}: {e.response.get("Error", {}).get("Message", str(e))}',
                        field='output_config.s3_uri',
                    )

            # Verify input location has content (optional check)
            if input_prefix:
                try:
                    response = self.s3_client.list_objects_v2(
                        Bucket=input_bucket, Prefix=input_prefix, MaxKeys=1
                    )
                    if response.get('KeyCount', 0) == 0:
                        logger.warning(
                            'No objects found at input location: %s', input_config.s3_uri
                        )
                except ClientError as e:
                    # Log warning but don't fail validation
                    logger.warning(
                        'Could not verify input content at %s: %s', input_config.s3_uri, str(e)
                    )

            logger.debug(
                'S3 access validation successful. Input: %s, Output: %s',
                input_config.s3_uri,
                output_config.s3_uri,
            )

        except ValidationError:
            # Re-raise validation errors
            raise
        except Exception as e:
            raise ValidationError(
                f'Failed to validate S3 access: {str(e)}', details={'error_type': type(e).__name__}
            )

    def _parse_s3_uri(self, s3_uri: str) -> tuple[str, str]:
        """Parse S3 URI into bucket and prefix components.

        Args:
            s3_uri: S3 URI to parse (e.g., 's3://bucket/prefix/')

        Returns:
            Tuple of (bucket_name, prefix)

        Raises:
            ValidationError: If S3 URI format is invalid

        """
        if not s3_uri.startswith('s3://'):
            raise ValidationError(f'Invalid S3 URI format: {s3_uri}')

        # Remove 's3://' prefix
        path = s3_uri[5:]

        # Split into bucket and prefix
        parts = path.split('/', 1)
        bucket = parts[0]
        prefix = parts[1] if len(parts) > 1 else ''

        if not bucket:
            raise ValidationError(f'Invalid S3 URI - missing bucket: {s3_uri}')

        return bucket, prefix

    def _calculate_progress(self, job_details: Dict[str, Any]) -> Optional[float]:
        """Calculate job progress percentage from job details.

        Args:
            job_details: Job details from AWS API response

        Returns:
            Progress percentage (0-100) or None if not available

        """
        status = job_details.get('JobStatus')

        if status == 'SUBMITTED':
            return 0.0
        elif status == 'IN_PROGRESS':
            # Try to get actual progress from job details
            # AWS Translate doesn't provide detailed progress, so we estimate
            return 50.0  # Assume 50% for in-progress jobs
        elif status in ['COMPLETED', 'COMPLETED_WITH_ERROR']:
            return 100.0
        elif status in ['FAILED', 'STOPPED']:
            # Return last known progress or 0 for failed/stopped jobs
            return 0.0
        else:
            return None

    def _parse_input_config(
        self, input_data: Optional[Dict[str, Any]]
    ) -> Optional[BatchInputConfig]:
        """Parse input configuration from job details."""
        if not input_data:
            return None

        # Create a minimal config without validation since AWS doesn't return the role ARN
        # We'll bypass the validation by creating the object directly
        config = object.__new__(BatchInputConfig)
        config.s3_uri = input_data.get('S3Uri', '')
        config.content_type = input_data.get('ContentType', '')
        config.data_access_role_arn = ''  # Not returned in job details
        return config

    def _parse_output_config(
        self, output_data: Optional[Dict[str, Any]]
    ) -> Optional[BatchOutputConfig]:
        """Parse output configuration from job details."""
        if not output_data:
            return None

        # Create a minimal config without validation since AWS doesn't return the role ARN
        # We'll bypass the validation by creating the object directly
        config = object.__new__(BatchOutputConfig)
        config.s3_uri = output_data.get('S3Uri', '')
        config.data_access_role_arn = ''  # Not returned in job details
        return config

    def _extract_error_details(self, job_details: Dict[str, Any]) -> Optional[str]:
        """Extract error details from job information.

        Args:
            job_details: Job details from AWS API response

        Returns:
            Error details string or None if no errors

        """
        status = job_details.get('JobStatus')

        if status == 'FAILED':
            # Try to get error message from job details
            message = job_details.get('Message', 'Job failed without specific error message')
            return f'Job failed: {message}'
        elif status == 'COMPLETED_WITH_ERROR':
            message = job_details.get('Message', 'Job completed with errors')
            return f'Job completed with errors: {message}'
        elif status == 'STOPPED':
            return 'Job was stopped by user request'

        return None
