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

"""Fleet Advisor Manager.

Handles business logic for AWS DMS Fleet Advisor operations.
"""

from .dms_client import DMSClient
from loguru import logger
from typing import Any, Dict, List, Optional


class FleetAdvisorManager:
    """Manager for Fleet Advisor database discovery operations."""

    def __init__(self, client: DMSClient):
        """Initialize Fleet Advisor manager."""
        self.client = client
        logger.debug('Initialized FleetAdvisorManager')

    def create_collector(
        self, name: str, description: str, service_access_role_arn: str, s3_bucket_name: str
    ) -> Dict[str, Any]:
        """Create Fleet Advisor collector."""
        response = self.client.call_api(
            'create_fleet_advisor_collector',
            CollectorName=name,
            Description=description,
            ServiceAccessRoleArn=service_access_role_arn,
            S3BucketName=s3_bucket_name,
        )
        return {
            'success': True,
            'data': {
                'collector': response.get('Collector', {}),
                'message': 'Fleet Advisor collector created',
            },
            'error': None,
        }

    def delete_collector(self, ref: str) -> Dict[str, Any]:
        """Delete Fleet Advisor collector."""
        self.client.call_api('delete_fleet_advisor_collector', CollectorReferencedId=ref)
        return {
            'success': True,
            'data': {'message': 'Fleet Advisor collector deleted'},
            'error': None,
        }

    def list_collectors(
        self,
        filters: Optional[List[Dict]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List Fleet Advisor collectors."""
        params: Dict[str, Any] = {'MaxRecords': max_results}
        if filters:
            params['Filters'] = filters
        if marker:
            params['NextToken'] = marker
        response = self.client.call_api('describe_fleet_advisor_collectors', **params)
        collectors = response.get('Collectors', [])
        result = {
            'success': True,
            'data': {'collectors': collectors, 'count': len(collectors)},
            'error': None,
        }
        if response.get('NextToken'):
            result['data']['next_token'] = response['NextToken']
        return result

    def delete_databases(self, database_ids: List[str]) -> Dict[str, Any]:
        """Delete Fleet Advisor databases."""
        response = self.client.call_api('delete_fleet_advisor_databases', DatabaseIds=database_ids)
        return {
            'success': True,
            'data': {
                'database_ids': response.get('DatabaseIds', []),
                'message': 'Fleet Advisor databases deleted',
            },
            'error': None,
        }

    def list_databases(
        self,
        filters: Optional[List[Dict]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List Fleet Advisor databases."""
        params: Dict[str, Any] = {'MaxRecords': max_results}
        if filters:
            params['Filters'] = filters
        if marker:
            params['NextToken'] = marker
        response = self.client.call_api('describe_fleet_advisor_databases', **params)
        databases = response.get('Databases', [])
        result = {
            'success': True,
            'data': {'databases': databases, 'count': len(databases)},
            'error': None,
        }
        if response.get('NextToken'):
            result['data']['next_token'] = response['NextToken']
        return result

    def describe_lsa_analysis(
        self, max_results: int = 100, marker: Optional[str] = None
    ) -> Dict[str, Any]:
        """Describe Fleet Advisor LSA analysis."""
        params: Dict[str, Any] = {'MaxRecords': max_results}
        if marker:
            params['NextToken'] = marker
        response = self.client.call_api('describe_fleet_advisor_lsa_analysis', **params)
        analysis = response.get('Analysis', [])
        result = {
            'success': True,
            'data': {'lsa_analysis': analysis, 'count': len(analysis)},
            'error': None,
        }
        if response.get('NextToken'):
            result['data']['next_token'] = response['NextToken']
        return result

    def run_lsa_analysis(self) -> Dict[str, Any]:
        """Run Fleet Advisor LSA analysis."""
        response = self.client.call_api('run_fleet_advisor_lsa_analysis')
        return {
            'success': True,
            'data': {
                'lsa_analysis_run': response.get('LSAAnalysisRun', {}),
                'message': 'Fleet Advisor LSA analysis started',
            },
            'error': None,
        }

    def describe_schema_object_summary(
        self,
        filters: Optional[List[Dict]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Describe Fleet Advisor schema object summary."""
        params: Dict[str, Any] = {'MaxRecords': max_results}
        if filters:
            params['Filters'] = filters
        if marker:
            params['NextToken'] = marker
        response = self.client.call_api('describe_fleet_advisor_schema_object_summary', **params)
        objects = response.get('FleetAdvisorSchemaObjects', [])
        result = {
            'success': True,
            'data': {'schema_objects': objects, 'count': len(objects)},
            'error': None,
        }
        if response.get('NextToken'):
            result['data']['next_token'] = response['NextToken']
        return result

    def list_schemas(
        self,
        filters: Optional[List[Dict]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List Fleet Advisor schemas."""
        params: Dict[str, Any] = {'MaxRecords': max_results}
        if filters:
            params['Filters'] = filters
        if marker:
            params['NextToken'] = marker
        response = self.client.call_api('describe_fleet_advisor_schemas', **params)
        schemas = response.get('FleetAdvisorSchemas', [])
        result = {
            'success': True,
            'data': {'schemas': schemas, 'count': len(schemas)},
            'error': None,
        }
        if response.get('NextToken'):
            result['data']['next_token'] = response['NextToken']
        return result
