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

"""Workflow Orchestrator for Amazon Translate MCP Server.

This module provides intelligent workflow orchestration that combines multiple
translation operations into cohesive, automated workflows for enhanced user experience.
"""

import asyncio
import json
import logging
import time
from .batch_manager import BatchJobManager
from .exceptions import BatchJobError, TranslationError, ValidationError
from .language_operations import LanguageOperations
from .models import (
    BatchInputConfig,
    BatchOutputConfig,
    JobConfig,
)
from .terminology_manager import TerminologyManager
from .translation_service import TranslationService
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


@dataclass
class SmartTranslationWorkflowResult:
    """Result of smart translation workflow execution."""

    original_text: str
    translated_text: str
    detected_language: str
    target_language: str
    confidence_score: float
    quality_score: Optional[float] = None
    applied_terminologies: List[str] = field(default_factory=list)
    language_pair_supported: bool = True
    validation_issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    execution_time_ms: Optional[float] = None
    workflow_steps: List[str] = field(default_factory=list)


@dataclass
class BatchTranslationWorkflowResult:
    """Result of batch translation workflow execution."""

    job_id: str
    job_name: str
    status: str
    source_language: str
    target_languages: List[str]
    input_s3_uri: str
    output_s3_uri: str
    terminology_names: List[str] = field(default_factory=list)
    pre_validation_results: Dict[str, Any] = field(default_factory=dict)
    monitoring_history: List[Dict[str, Any]] = field(default_factory=list)
    performance_metrics: Optional[Dict[str, Any]] = None
    error_analysis: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_execution_time: Optional[float] = None
    workflow_steps: List[str] = field(default_factory=list)


@dataclass
class WorkflowContext:
    """Context for workflow execution with state management."""

    workflow_id: str
    workflow_type: str
    started_at: datetime
    current_step: str = ''
    completed_steps: List[str] = field(default_factory=list)
    error_count: int = 0
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkflowOrchestrator:
    """Orchestrates intelligent translation workflows combining multiple operations.

    Provides two main workflow types:
    1. Smart Translation Workflow - Automated language detection, validation, and translation
    2. Batch Translation with Progress Monitoring - Complete batch job lifecycle management
    """

    def __init__(
        self,
        translation_service: TranslationService,
        batch_manager: BatchJobManager,
        terminology_manager: TerminologyManager,
        language_operations: LanguageOperations,
    ):
        """Initialize the workflow orchestrator with required services."""
        self.translation_service = translation_service
        self.batch_manager = batch_manager
        self.terminology_manager = terminology_manager
        self.language_operations = language_operations

        # Workflow state management
        self._active_workflows: Dict[str, WorkflowContext] = {}
        self._workflow_results: Dict[str, Any] = {}

        logger.info('Workflow orchestrator initialized successfully')

    async def _analyze_job_errors(
        self, job_id: str, output_s3_uri: str, loop: asyncio.AbstractEventLoop
    ) -> Optional[Dict[str, Any]]:
        """Analyze failed batch translation job by checking S3 details folder for error information.

        Args:
            job_id: The failed job ID
            output_s3_uri: Output S3 URI where details folder should be
            loop: Event loop for async execution

        Returns:
            Dictionary with error analysis and suggested actions, or None if no errors found

        """
        try:
            logger.info(f'Analyzing errors for failed job {job_id}')

            # Parse S3 URI to get bucket and prefix
            s3_parts = output_s3_uri.replace('s3://', '').split('/', 1)
            bucket_name = s3_parts[0]
            output_prefix = s3_parts[1] if len(s3_parts) > 1 else ''

            # Get S3 client first
            s3_client = self.batch_manager.s3_client

            # Look for details folder in the output location
            # AWS Translate creates folders with format: {account_id}-TranslateText-{job_id}/
            # First, find the actual job folder by searching for the job_id pattern
            job_folder_prefix = f'{output_prefix}'

            # List folders to find the one containing our job_id
            def list_job_folders():
                return s3_client.list_objects_v2(
                    Bucket=bucket_name, Prefix=job_folder_prefix, Delimiter='/'
                )

            folders_response = await loop.run_in_executor(None, list_job_folders)

            job_folder = None
            if 'CommonPrefixes' in folders_response:
                for prefix_info in folders_response['CommonPrefixes']:
                    folder_name = prefix_info['Prefix']
                    if job_id in folder_name:
                        job_folder = folder_name
                        break

            if not job_folder:
                logger.warning(
                    f'Could not find job folder for job_id {job_id} in {job_folder_prefix}'
                )
                return None

            details_prefix = f'{job_folder}details/'

            logger.debug(f'Checking for error details in s3://{bucket_name}/{details_prefix}')

            def list_error_files():
                return s3_client.list_objects_v2(Bucket=bucket_name, Prefix=details_prefix)

            response = await loop.run_in_executor(None, list_error_files)

            if 'Contents' not in response:
                logger.warning(f'No error details found in s3://{bucket_name}/{details_prefix}')
                return None

            error_analysis = {
                'job_id': job_id,
                'error_files_found': [],
                'error_details': [],
                'suggested_actions': [],
            }

            # Process each error file
            for obj in response['Contents']:
                if obj['Key'].endswith('.json'):
                    logger.debug(f'Reading error file: {obj["Key"]}')

                    # Download and parse error file
                    def get_error_file():
                        return s3_client.get_object(Bucket=bucket_name, Key=obj['Key'])

                    error_content = await loop.run_in_executor(None, get_error_file)

                    error_text = error_content['Body'].read().decode('utf-8')

                    try:
                        error_data = json.loads(error_text)

                        error_analysis['error_files_found'].append(obj['Key'])
                        error_analysis['error_details'].append(
                            {'file': obj['Key'], 'error_data': error_data}
                        )

                        # Analyze error and suggest actions
                        suggestions = self._generate_error_suggestions(error_data)
                        error_analysis['suggested_actions'].extend(suggestions)

                    except json.JSONDecodeError as e:
                        logger.warning(f'Failed to parse error file {obj["Key"]}: {e}')
                        error_analysis['error_details'].append(
                            {'file': obj['Key'], 'raw_content': error_text, 'parse_error': str(e)}
                        )

            logger.info(
                f'Error analysis completed for job {job_id}: found {len(error_analysis["error_files_found"])} error files'
            )
            return error_analysis

        except Exception as e:
            logger.error(f'Failed to analyze job errors for {job_id}: {e}')
            return {
                'job_id': job_id,
                'analysis_error': str(e),
                'suggested_actions': [
                    'Check AWS CloudWatch logs for the translation job',
                    'Verify S3 bucket permissions and access',
                    'Ensure input files are in supported format',
                ],
            }

    def _generate_error_suggestions(self, error_data: Dict[str, Any]) -> List[str]:
        """Generate actionable suggestions based on error data.

        Args:
            error_data: Parsed error data from S3 details file

        Returns:
            List of suggested actions to resolve the error

        """
        suggestions = []

        # Convert error data to string for analysis
        error_str = str(error_data).lower()

        # Common error patterns and suggestions
        if 'utf-8' in error_str or 'encoding' in error_str:
            suggestions.extend(
                [
                    'Check file encoding - ensure all files use UTF-8 encoding',
                    'Convert files to UTF-8 format before uploading',
                    'Remove or replace non-UTF-8 characters in input files',
                ]
            )

        if 'unsupported' in error_str and 'format' in error_str:
            suggestions.extend(
                [
                    'Convert input files to supported format (txt, html, docx, pptx, xlsx)',
                    'Check file encoding - use UTF-8 encoding',
                    'Verify file is not corrupted or empty',
                ]
            )

        if 'permission' in error_str or 'access' in error_str:
            suggestions.extend(
                [
                    'Check IAM role has s3:GetObject permission for input bucket',
                    'Check IAM role has s3:PutObject permission for output bucket',
                    'Verify the IAM role trust policy allows translate.amazonaws.com',
                ]
            )

        if 'language' in error_str and ('unsupported' in error_str or 'invalid' in error_str):
            suggestions.extend(
                [
                    'Verify source language is supported by Amazon Translate',
                    'Check target languages are valid language codes',
                    'Ensure language pair combination is supported',
                ]
            )

        if 'size' in error_str or 'limit' in error_str:
            suggestions.extend(
                [
                    'Reduce file size - maximum 20MB per file',
                    'Split large documents into smaller files',
                    "Check total job size doesn't exceed limits",
                ]
            )

        if 'terminology' in error_str:
            suggestions.extend(
                [
                    'Verify custom terminology exists and is active',
                    'Check terminology supports the language pair',
                    'Ensure terminology format is correct',
                ]
            )

        if not suggestions:
            suggestions.extend(
                [
                    'Check AWS CloudWatch logs for detailed error information',
                    'Verify input file format and content',
                    'Ensure all AWS service permissions are correctly configured',
                    'Contact AWS Support if the issue persists',
                ]
            )

        return suggestions

    async def smart_translate_workflow(
        self,
        text: str,
        target_language: str,
        quality_threshold: float = 0.8,
        terminology_names: Optional[List[str]] = None,
        auto_detect_language: bool = True,
    ) -> SmartTranslationWorkflowResult:
        """Execute smart translation workflow with automatic language detection and quality validation.

        Workflow Steps:
        1. Detect source language (if auto_detect_language=True)
        2. Validate language pair support
        3. Translate text with terminology
        4. Validate translation quality
        5. Return comprehensive results

        Args:
            text: Text to translate
            target_language: Target language code
            quality_threshold: Minimum quality score threshold (0.0-1.0)
            terminology_names: Optional list of terminology names to apply
            auto_detect_language: Whether to auto-detect source language

        Returns:
            SmartTranslationWorkflowResult with comprehensive translation data

        """
        workflow_id = f'smart_translate_{int(time.time() * 1000)}'
        start_time = time.time()

        # Initialize workflow context
        context = WorkflowContext(
            workflow_id=workflow_id,
            workflow_type='smart_translation',
            started_at=datetime.now(),
            metadata={
                'text_length': len(text),
                'target_language': target_language,
                'quality_threshold': quality_threshold,
                'terminology_names': terminology_names or [],
            },
        )

        self._active_workflows[workflow_id] = context

        try:
            logger.info(f'Starting smart translation workflow {workflow_id}')

            # Step 1: Language Detection
            detected_language = None
            detection_confidence = 0.0

            if auto_detect_language:
                context.current_step = 'detect_language'
                logger.debug(f'Step 1: Detecting language for workflow {workflow_id}')

                # Run synchronous method in thread pool
                loop = asyncio.get_event_loop()
                detection_result = await loop.run_in_executor(
                    None, self.translation_service.detect_language, text
                )
                detected_language = detection_result.detected_language
                detection_confidence = detection_result.confidence_score

                context.completed_steps.append('detect_language')
                logger.debug(
                    f'Language detected: {detected_language} (confidence: {detection_confidence})'
                )
            else:
                # Use provided source language or attempt detection
                context.current_step = 'detect_language'
                loop = asyncio.get_event_loop()
                detection_result = await loop.run_in_executor(
                    None, self.translation_service.detect_language, text
                )
                detected_language = detection_result.detected_language
                detection_confidence = detection_result.confidence_score
                context.completed_steps.append('detect_language')

            # Step 2: Validate Language Pair Support
            context.current_step = 'validate_language_pair'
            logger.debug(
                f'Step 2: Validating language pair {detected_language}->{target_language}'
            )

            # Run synchronous method in thread pool
            loop = asyncio.get_event_loop()
            language_pairs = await loop.run_in_executor(
                None, self.language_operations.list_language_pairs
            )
            language_pair_supported = any(
                pair.source_language == detected_language
                and pair.target_language == target_language
                for pair in language_pairs
            )

            if not language_pair_supported:
                raise ValidationError(
                    f'Language pair {detected_language}->{target_language} is not supported',
                    details={
                        'source_language': detected_language,
                        'target_language': target_language,
                    },
                )

            context.completed_steps.append('validate_language_pair')

            # Step 3: Translate Text
            context.current_step = 'translate_text'
            logger.debug(f'Step 3: Translating text for workflow {workflow_id}')

            # Run synchronous method in thread pool
            loop = asyncio.get_event_loop()
            translation_result = await loop.run_in_executor(
                None,
                self.translation_service.translate_text,
                text,
                detected_language,
                target_language,
                terminology_names or [],
            )

            context.completed_steps.append('translate_text')

            # Step 4: Validate Translation Quality
            context.current_step = 'validate_translation'
            logger.debug(f'Step 4: Validating translation quality for workflow {workflow_id}')

            # Run synchronous method in thread pool
            loop = asyncio.get_event_loop()
            validation_result = await loop.run_in_executor(
                None,
                self.translation_service.validate_translation,
                text,
                translation_result.translated_text,
                detected_language,
                target_language,
            )

            context.completed_steps.append('validate_translation')

            # Check quality threshold
            quality_meets_threshold = True
            if validation_result.quality_score is not None:
                quality_meets_threshold = validation_result.quality_score >= quality_threshold
                if not quality_meets_threshold:
                    logger.warning(
                        f'Translation quality ({validation_result.quality_score}) '
                        f'below threshold ({quality_threshold}) for workflow {workflow_id}'
                    )

            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000

            # Create comprehensive result
            result = SmartTranslationWorkflowResult(
                original_text=text,
                translated_text=translation_result.translated_text,
                detected_language=detected_language,
                target_language=target_language,
                confidence_score=detection_confidence,
                quality_score=validation_result.quality_score,
                applied_terminologies=translation_result.applied_terminologies,
                language_pair_supported=language_pair_supported,
                validation_issues=validation_result.issues,
                suggestions=validation_result.suggestions,
                execution_time_ms=execution_time_ms,
                workflow_steps=context.completed_steps.copy(),
            )

            # Store result
            self._workflow_results[workflow_id] = result

            logger.info(
                f'Smart translation workflow {workflow_id} completed successfully '
                f'in {execution_time_ms:.2f}ms'
            )

            return result

        except (ValidationError, TranslationError) as e:
            # Re-raise validation and translation errors as-is
            context.error_count += 1
            logger.error(
                f'Smart translation workflow {workflow_id} failed at step {context.current_step}: {e}'
            )
            raise
        except Exception as e:
            context.error_count += 1
            logger.error(
                f'Smart translation workflow {workflow_id} failed at step {context.current_step}: {e}'
            )
            raise TranslationError(
                f'Smart translation workflow failed: {str(e)}',
                details={
                    'workflow_id': workflow_id,
                    'failed_step': context.current_step,
                    'completed_steps': context.completed_steps,
                },
            )
        finally:
            # Clean up workflow context
            if workflow_id in self._active_workflows:
                del self._active_workflows[workflow_id]

    async def managed_batch_translation_workflow(
        self,
        input_s3_uri: str,
        output_s3_uri: str,
        data_access_role_arn: str,
        job_name: str,
        source_language: str,
        target_languages: List[str],
        terminology_names: Optional[List[str]] = None,
        content_type: str = 'text/plain',
        monitor_interval: int = 30,
        max_monitoring_duration: int = 3600,
    ) -> BatchTranslationWorkflowResult:
        """Execute managed batch translation workflow with comprehensive monitoring.

        Workflow Steps:
        1. Pre-validate language pairs and terminologies
        2. Start batch translation job
        3. Monitor job progress with automated polling
        4. Collect performance metrics upon completion
        5. Return comprehensive results with monitoring history

        Args:
            input_s3_uri: S3 URI for input documents
            output_s3_uri: S3 URI for output location
            data_access_role_arn: IAM role ARN for S3 access
            job_name: Name for the translation job
            source_language: Source language code
            target_languages: List of target language codes
            terminology_names: Optional list of terminology names
            content_type: Content type of input documents
            monitor_interval: Monitoring interval in seconds
            max_monitoring_duration: Maximum monitoring duration in seconds

        Returns:
            BatchTranslationWorkflowResult with comprehensive job data and monitoring history

        """
        workflow_id = f'batch_translate_{int(time.time() * 1000)}'
        start_time = time.time()

        # Initialize workflow context
        context = WorkflowContext(
            workflow_id=workflow_id,
            workflow_type='batch_translation_monitoring',
            started_at=datetime.now(),
            metadata={
                'job_name': job_name,
                'source_language': source_language,
                'target_languages': target_languages,
                'terminology_names': terminology_names or [],
                'monitor_interval': monitor_interval,
            },
        )

        self._active_workflows[workflow_id] = context

        try:
            logger.info(f'Starting managed batch translation workflow {workflow_id}')

            # Step 1: Pre-validate Language Pairs
            context.current_step = 'validate_language_pairs'
            logger.debug(f'Step 1: Validating language pairs for workflow {workflow_id}')

            # Run synchronous method in thread pool
            loop = asyncio.get_event_loop()
            language_pairs = await loop.run_in_executor(
                None, self.language_operations.list_language_pairs
            )
            validation_results: Dict[str, Any] = {'supported_pairs': [], 'unsupported_pairs': []}

            for target_lang in target_languages:
                pair_supported = any(
                    pair.source_language == source_language and pair.target_language == target_lang
                    for pair in language_pairs
                )

                if pair_supported:
                    validation_results['supported_pairs'].append(
                        f'{source_language}->{target_lang}'
                    )
                else:
                    validation_results['unsupported_pairs'].append(
                        f'{source_language}->{target_lang}'
                    )

            if validation_results['unsupported_pairs']:
                raise ValidationError(
                    f'Unsupported language pairs: {validation_results["unsupported_pairs"]}',
                    details=validation_results,
                )

            context.completed_steps.append('validate_language_pairs')

            # Step 2: Validate Terminologies (if provided)
            if terminology_names:
                context.current_step = 'validate_terminologies'
                logger.debug(f'Step 2: Validating terminologies for workflow {workflow_id}')

                # Type narrowing: terminology_names is now List[str] (not Optional)
                terminology_names_list: List[str] = terminology_names

                # Run synchronous method in thread pool
                loop = asyncio.get_event_loop()
                terminologies_result = await loop.run_in_executor(
                    None, self.terminology_manager.list_terminologies
                )
                available_terminologies = [
                    t.name for t in terminologies_result.get('terminologies', [])
                ]

                missing_terminologies = [
                    name for name in terminology_names_list if name not in available_terminologies
                ]

                if missing_terminologies:
                    raise ValidationError(
                        f'Missing terminologies: {missing_terminologies}',
                        details={
                            'missing': missing_terminologies,
                            'available': available_terminologies,
                        },
                    )

                validation_results['terminologies'] = {
                    'requested': terminology_names_list,
                    'available': available_terminologies,
                    'validated': True,
                }

                context.completed_steps.append('validate_terminologies')

            # Step 3: Start Batch Translation Job
            context.current_step = 'start_batch_job'
            logger.debug(f'Step 3: Starting batch translation job for workflow {workflow_id}')

            # Create configuration objects
            input_config = BatchInputConfig(
                s3_uri=input_s3_uri,
                content_type=content_type,
                data_access_role_arn=data_access_role_arn,
            )

            output_config = BatchOutputConfig(
                s3_uri=output_s3_uri, data_access_role_arn=data_access_role_arn
            )

            job_config = JobConfig(
                job_name=job_name,
                source_language_code=source_language,
                target_language_codes=target_languages,
                terminology_names=terminology_names or [],
            )

            # Run synchronous method in thread pool
            loop = asyncio.get_event_loop()
            job_id = await loop.run_in_executor(
                None,
                self.batch_manager.start_batch_translation,
                input_config,
                output_config,
                job_config,
            )

            context.completed_steps.append('start_batch_job')
            context.metadata['job_id'] = job_id

            # Step 4: Monitor Job Progress Until Completion
            context.current_step = 'monitor_job_progress'
            logger.info(
                f'Step 4: Monitoring job progress for workflow {workflow_id} until completion'
            )

            monitoring_history = []
            job_status = None
            monitoring_start = time.time()

            # Monitor continuously until job reaches final state
            while True:
                current_time = time.time()

                # Get job status
                job_status = await loop.run_in_executor(
                    None, self.batch_manager.get_translation_job, job_id
                )

                # Record monitoring data
                monitoring_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'status': job_status.status,
                    'progress': job_status.progress,
                    'elapsed_time': current_time - monitoring_start,
                }
                monitoring_history.append(monitoring_entry)

                logger.info(
                    f'Job {job_id} status: {job_status.status}, '
                    f'progress: {job_status.progress}%, '
                    f'elapsed: {current_time - monitoring_start:.1f}s'
                )

                # Check if job reached final state
                if job_status.status in ['COMPLETED', 'FAILED', 'STOPPED']:
                    logger.info(f'Job {job_id} reached final state: {job_status.status}')
                    break

                # Check if we've exceeded maximum monitoring duration
                if current_time - monitoring_start > max_monitoring_duration:
                    logger.warning(
                        f'Monitoring duration exceeded {max_monitoring_duration}s for workflow {workflow_id}. '
                        f'Job {job_id} is still {job_status.status}. Stopping monitoring but job continues.'
                    )
                    break

                # Wait before next check
                await asyncio.sleep(monitor_interval)

            context.completed_steps.append('monitor_job_progress')

            # Step 4.5: Analyze Errors if Job Failed
            error_analysis = None
            if job_status and job_status.status == 'FAILED':
                context.current_step = 'analyze_job_errors'
                logger.info(f'Step 4.5: Analyzing job errors for failed job {job_id}')

                error_analysis = await self._analyze_job_errors(job_id, output_s3_uri, loop)

                if error_analysis:
                    logger.error(f'Job {job_id} failed with errors: {error_analysis}')
                    context.completed_steps.append('analyze_job_errors')

            # Step 5: Collect Performance Metrics
            context.current_step = 'collect_metrics'
            logger.debug(f'Step 5: Collecting performance metrics for workflow {workflow_id}')

            performance_metrics = None
            try:
                # Get language metrics for each target language
                metrics_data = {}
                for target_lang in target_languages:
                    language_pair = f'{source_language}-{target_lang}'
                    metrics = await loop.run_in_executor(
                        None, self.language_operations.get_language_metrics, language_pair, '24h'
                    )
                    metrics_data[language_pair] = {
                        'translation_count': metrics.translation_count,
                        'character_count': metrics.character_count,
                        'average_response_time': metrics.average_response_time,
                        'error_rate': metrics.error_rate,
                    }

                performance_metrics = {
                    'language_pairs': metrics_data,
                    'total_monitoring_time': time.time() - monitoring_start,
                    'monitoring_checks': len(monitoring_history),
                    'final_status': job_status.status if job_status else 'UNKNOWN',
                }

            except Exception as e:
                logger.warning(f'Failed to collect performance metrics: {e}')
                performance_metrics = {'error': str(e)}

            context.completed_steps.append('collect_metrics')

            # Calculate total execution time
            total_execution_time = time.time() - start_time

            # Create comprehensive result
            result = BatchTranslationWorkflowResult(
                job_id=job_id,
                job_name=job_name,
                status=job_status.status if job_status else 'UNKNOWN',
                source_language=source_language,
                target_languages=target_languages,
                input_s3_uri=input_s3_uri,
                output_s3_uri=output_s3_uri,
                terminology_names=terminology_names or [],
                pre_validation_results=validation_results,
                monitoring_history=monitoring_history,
                performance_metrics=performance_metrics,
                error_analysis=error_analysis,
                created_at=job_status.created_at if job_status else None,
                completed_at=job_status.completed_at if job_status else None,
                total_execution_time=total_execution_time,
                workflow_steps=context.completed_steps.copy(),
            )

            # Store result
            self._workflow_results[workflow_id] = result

            logger.info(
                f'Managed batch translation workflow {workflow_id} completed '
                f'with status {result.status} in {total_execution_time:.2f}s'
            )

            return result

        except (ValidationError, BatchJobError) as e:
            # Re-raise validation and batch job errors as-is
            context.error_count += 1
            logger.error(
                f'Managed batch translation workflow {workflow_id} failed at step {context.current_step}: {e}'
            )
            raise
        except Exception as e:
            context.error_count += 1
            logger.error(
                f'Managed batch translation workflow {workflow_id} failed at step {context.current_step}: {e}'
            )
            raise BatchJobError(
                f'Managed batch translation workflow failed: {str(e)}',
                details={
                    'workflow_id': workflow_id,
                    'failed_step': context.current_step,
                    'completed_steps': context.completed_steps,
                },
            )
        finally:
            # Clean up workflow context
            if workflow_id in self._active_workflows:
                del self._active_workflows[workflow_id]

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of an active workflow."""
        if workflow_id in self._active_workflows:
            context = self._active_workflows[workflow_id]
            return {
                'workflow_id': workflow_id,
                'workflow_type': context.workflow_type,
                'started_at': context.started_at.isoformat(),
                'current_step': context.current_step,
                'completed_steps': context.completed_steps,
                'error_count': context.error_count,
                'retry_count': context.retry_count,
                'metadata': context.metadata,
            }
        return None

    def list_active_workflows(self) -> List[Dict[str, Any]]:
        """List all currently active workflows."""
        workflows = []
        for workflow_id in self._active_workflows.keys():
            status = self.get_workflow_status(workflow_id)
            if status is not None:
                workflows.append(status)
        return workflows

    def get_workflow_result(self, workflow_id: str) -> Optional[Any]:
        """Get the result of a completed workflow."""
        return self._workflow_results.get(workflow_id)

    def cleanup_old_results(self, max_age_hours: int = 24) -> int:
        """Clean up old workflow results to prevent memory leaks."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleaned_count = 0

        # Note: This is a simplified cleanup. In production, you'd want to store
        # workflow metadata with timestamps for proper cleanup.
        workflow_ids_to_remove = []

        for workflow_id in self._workflow_results.keys():
            # Extract timestamp from workflow_id (simplified approach)
            try:
                timestamp_ms = int(workflow_id.split('_')[-1])
                workflow_time = datetime.fromtimestamp(timestamp_ms / 1000)

                if workflow_time < cutoff_time:
                    workflow_ids_to_remove.append(workflow_id)
                    cleaned_count += 1
            except (ValueError, IndexError):
                # Skip workflows with non-standard IDs
                continue

        for workflow_id in workflow_ids_to_remove:
            del self._workflow_results[workflow_id]

        logger.info(f'Cleaned up {cleaned_count} old workflow results')
        return cleaned_count
