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

"""Assessment Manager.

Handles business logic for AWS DMS replication task assessment operations.
"""

from .dms_client import DMSClient
from .response_formatter import ResponseFormatter
from loguru import logger
from typing import Any, Dict, List, Optional


class AssessmentManager:
    """Manager for replication task assessment operations."""

    def __init__(self, client: DMSClient):
        """Initialize assessment manager.

        Args:
            client: DMS client wrapper
        """
        self.client = client
        logger.debug('Initialized AssessmentManager')

    def start_assessment(self, task_arn: str) -> Dict[str, Any]:
        """Start a task assessment (legacy API).

        Args:
            task_arn: Task ARN

        Returns:
            Assessment initiation result
        """
        logger.info('Starting replication task assessment', task_arn=task_arn)

        response = self.client.call_api(
            'start_replication_task_assessment', ReplicationTaskArn=task_arn
        )

        task = response.get('ReplicationTask', {})
        formatted_task = ResponseFormatter.format_task(task)

        return {
            'success': True,
            'data': {'task': formatted_task, 'message': 'Task assessment started'},
            'error': None,
        }

    def start_assessment_run(
        self,
        task_arn: str,
        service_access_role_arn: str,
        result_location_bucket: str,
        result_location_folder: Optional[str] = None,
        result_encryption_mode: Optional[str] = None,
        result_kms_key_arn: Optional[str] = None,
        assessment_run_name: Optional[str] = None,
        include_only: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Start a new assessment run.

        Args:
            task_arn: Task ARN
            service_access_role_arn: IAM role for S3 access
            result_location_bucket: S3 bucket for results
            result_location_folder: S3 folder path
            result_encryption_mode: Encryption mode (sse-s3 or sse-kms)
            result_kms_key_arn: KMS key ARN (if sse-kms)
            assessment_run_name: Assessment run name
            include_only: Assessment types to include
            exclude: Assessment types to exclude

        Returns:
            Assessment run details
        """
        logger.info('Starting replication task assessment run', task_arn=task_arn)

        params: Dict[str, Any] = {
            'ReplicationTaskArn': task_arn,
            'ServiceAccessRoleArn': service_access_role_arn,
            'ResultLocationBucket': result_location_bucket,
        }

        if result_location_folder:
            params['ResultLocationFolder'] = result_location_folder
        if result_encryption_mode:
            params['ResultEncryptionMode'] = result_encryption_mode
        if result_kms_key_arn:
            params['ResultKmsKeyArn'] = result_kms_key_arn
        if assessment_run_name:
            params['AssessmentRunName'] = assessment_run_name
        if include_only:
            params['IncludeOnly'] = include_only
        if exclude:
            params['Exclude'] = exclude

        response = self.client.call_api('start_replication_task_assessment_run', **params)

        assessment_run = response.get('ReplicationTaskAssessmentRun', {})

        return {
            'success': True,
            'data': {
                'assessment_run': assessment_run,
                'message': 'Assessment run started successfully',
            },
            'error': None,
        }

    def cancel_assessment_run(self, assessment_run_arn: str) -> Dict[str, Any]:
        """Cancel a running assessment.

        Args:
            assessment_run_arn: Assessment run ARN

        Returns:
            Cancellation result
        """
        logger.info('Cancelling assessment run', assessment_run_arn=assessment_run_arn)

        response = self.client.call_api(
            'cancel_replication_task_assessment_run',
            ReplicationTaskAssessmentRunArn=assessment_run_arn,
        )

        assessment_run = response.get('ReplicationTaskAssessmentRun', {})

        return {
            'success': True,
            'data': {'assessment_run': assessment_run, 'message': 'Assessment run cancelled'},
            'error': None,
        }

    def delete_assessment_run(self, assessment_run_arn: str) -> Dict[str, Any]:
        """Delete an assessment run.

        Args:
            assessment_run_arn: Assessment run ARN

        Returns:
            Deletion result
        """
        logger.info('Deleting assessment run', assessment_run_arn=assessment_run_arn)

        response = self.client.call_api(
            'delete_replication_task_assessment_run',
            ReplicationTaskAssessmentRunArn=assessment_run_arn,
        )

        assessment_run = response.get('ReplicationTaskAssessmentRun', {})

        return {
            'success': True,
            'data': {
                'assessment_run': assessment_run,
                'message': 'Assessment run deleted successfully',
            },
            'error': None,
        }

    def list_assessment_results(
        self, task_arn: Optional[str] = None, max_results: int = 100, marker: Optional[str] = None
    ) -> Dict[str, Any]:
        """List assessment results (legacy API).

        Args:
            task_arn: Optional task ARN to filter
            max_results: Maximum results per page
            marker: Pagination token

        Returns:
            Assessment results list
        """
        logger.info('Listing assessment results', task_arn=task_arn)

        params: Dict[str, Any] = {'MaxRecords': max_results}

        if task_arn:
            params['ReplicationTaskArn'] = task_arn
        if marker:
            params['Marker'] = marker

        response = self.client.call_api('describe_replication_task_assessment_results', **params)

        results = response.get('ReplicationTaskAssessmentResults', [])

        result = {
            'success': True,
            'data': {'assessment_results': results, 'count': len(results)},
            'error': None,
        }

        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']

        return result

    def list_assessment_runs(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List assessment runs with filtering.

        Args:
            filters: Optional filters for assessment runs
            max_results: Maximum results per page
            marker: Pagination token

        Returns:
            Assessment runs list
        """
        logger.info('Listing assessment runs', filters=filters)

        params: Dict[str, Any] = {'MaxRecords': max_results}

        if filters:
            params['Filters'] = filters
        if marker:
            params['Marker'] = marker

        response = self.client.call_api('describe_replication_task_assessment_runs', **params)

        runs = response.get('ReplicationTaskAssessmentRuns', [])

        result = {
            'success': True,
            'data': {'assessment_runs': runs, 'count': len(runs)},
            'error': None,
        }

        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']

        return result

    def list_individual_assessments(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List individual assessments with filtering.

        Args:
            filters: Optional filters for individual assessments
            max_results: Maximum results per page
            marker: Pagination token

        Returns:
            Individual assessments list
        """
        logger.info('Listing individual assessments', filters=filters)

        params: Dict[str, Any] = {'MaxRecords': max_results}

        if filters:
            params['Filters'] = filters
        if marker:
            params['Marker'] = marker

        response = self.client.call_api(
            'describe_replication_task_individual_assessments', **params
        )

        assessments = response.get('ReplicationTaskIndividualAssessments', [])

        result = {
            'success': True,
            'data': {'individual_assessments': assessments, 'count': len(assessments)},
            'error': None,
        }

        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']

        return result

    def list_applicable_assessments(
        self,
        task_arn: Optional[str] = None,
        migration_type: Optional[str] = None,
        source_engine_name: Optional[str] = None,
        target_engine_name: Optional[str] = None,
        replication_instance_arn: Optional[str] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List applicable individual assessments.

        Args:
            task_arn: Optional task ARN
            migration_type: Migration type
            source_engine_name: Source engine
            target_engine_name: Target engine
            replication_instance_arn: Instance ARN
            max_results: Maximum results per page
            marker: Pagination token

        Returns:
            Applicable assessments list
        """
        logger.info('Listing applicable individual assessments')

        params: Dict[str, Any] = {'MaxRecords': max_results}

        if task_arn:
            params['ReplicationTaskArn'] = task_arn
        if migration_type:
            params['MigrationType'] = migration_type
        if source_engine_name:
            params['SourceEngineName'] = source_engine_name
        if target_engine_name:
            params['TargetEngineName'] = target_engine_name
        if replication_instance_arn:
            params['ReplicationInstanceArn'] = replication_instance_arn
        if marker:
            params['Marker'] = marker

        response = self.client.call_api('describe_applicable_individual_assessments', **params)

        assessments = response.get('IndividualAssessmentNames', [])

        result = {
            'success': True,
            'data': {'applicable_assessments': assessments, 'count': len(assessments)},
            'error': None,
        }

        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']

        return result
