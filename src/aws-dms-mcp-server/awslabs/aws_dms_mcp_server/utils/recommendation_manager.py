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

"""Recommendation Manager.

Handles business logic for AWS DMS recommendation operations.
"""

from .dms_client import DMSClient
from loguru import logger
from typing import Any, Dict, List, Optional


class RecommendationManager:
    """Manager for DMS recommendation operations."""

    def __init__(self, client: DMSClient):
        """Initialize recommendation manager."""
        self.client = client
        logger.debug('Initialized RecommendationManager')

    def list_recommendations(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List migration recommendations."""
        logger.info('Listing recommendations', filters=filters)

        params: Dict[str, Any] = {'MaxRecords': max_results}
        if filters:
            params['Filters'] = filters
        if marker:
            params['NextToken'] = marker

        response = self.client.call_api('describe_recommendations', **params)

        recommendations = response.get('Recommendations', [])

        result = {
            'success': True,
            'data': {'recommendations': recommendations, 'count': len(recommendations)},
            'error': None,
        }

        if response.get('NextToken'):
            result['data']['next_token'] = response['NextToken']

        logger.info(f'Retrieved {len(recommendations)} recommendations')
        return result

    def list_recommendation_limitations(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List recommendation limitations."""
        logger.info('Listing recommendation limitations', filters=filters)

        params: Dict[str, Any] = {'MaxRecords': max_results}
        if filters:
            params['Filters'] = filters
        if marker:
            params['NextToken'] = marker

        response = self.client.call_api('describe_recommendation_limitations', **params)

        limitations = response.get('Limitations', [])

        result = {
            'success': True,
            'data': {'limitations': limitations, 'count': len(limitations)},
            'error': None,
        }

        if response.get('NextToken'):
            result['data']['next_token'] = response['NextToken']

        return result

    def start_recommendations(self, database_id: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Start generating recommendations for a database."""
        logger.info('Starting recommendations', database_id=database_id)

        self.client.call_api('start_recommendations', DatabaseId=database_id, Settings=settings)

        return {
            'success': True,
            'data': {'message': 'Recommendations generation started', 'database_id': database_id},
            'error': None,
        }

    def batch_start_recommendations(
        self, data: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Batch start recommendations for multiple databases."""
        logger.info('Batch starting recommendations', count=len(data) if data else 0)

        params: Dict[str, Any] = {}
        if data:
            params['Data'] = data

        response = self.client.call_api('batch_start_recommendations', **params)

        error_entries = response.get('ErrorEntries', [])

        return {
            'success': len(error_entries) == 0,
            'data': {
                'error_entries': error_entries,
                'message': f'Batch recommendations started (errors: {len(error_entries)})',
            },
            'error': None,
        }
