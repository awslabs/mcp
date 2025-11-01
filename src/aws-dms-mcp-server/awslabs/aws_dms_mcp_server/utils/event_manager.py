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

"""Event Manager.

Handles business logic for AWS DMS event subscription and monitoring operations.
"""

from .dms_client import DMSClient
from loguru import logger
from typing import Any, Dict, List, Optional


class EventManager:
    """Manager for DMS event subscription and monitoring operations."""

    def __init__(self, client: DMSClient):
        """Initialize event manager.

        Args:
            client: DMS client wrapper
        """
        self.client = client
        logger.debug('Initialized EventManager')

    def create_event_subscription(
        self,
        subscription_name: str,
        sns_topic_arn: str,
        source_type: Optional[str] = None,
        event_categories: Optional[List[str]] = None,
        source_ids: Optional[List[str]] = None,
        enabled: bool = True,
        tags: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Create an event subscription for DMS notifications.

        Args:
            subscription_name: Unique subscription name
            sns_topic_arn: SNS topic ARN for notifications
            source_type: Event source type (replication-instance, replication-task, etc.)
            event_categories: List of event categories to subscribe to
            source_ids: List of source identifiers to monitor
            enabled: Enable subscription immediately
            tags: Resource tags

        Returns:
            Created event subscription details
        """
        logger.info('Creating event subscription', name=subscription_name)

        params: Dict[str, Any] = {
            'SubscriptionName': subscription_name,
            'SnsTopicArn': sns_topic_arn,
            'Enabled': enabled,
        }

        if source_type:
            params['SourceType'] = source_type
        if event_categories:
            params['EventCategories'] = event_categories
        if source_ids:
            params['SourceIds'] = source_ids
        if tags:
            params['Tags'] = tags

        response = self.client.call_api('create_event_subscription', **params)

        subscription = response.get('EventSubscription', {})

        return {
            'success': True,
            'data': {
                'event_subscription': subscription,
                'message': 'Event subscription created successfully',
            },
            'error': None,
        }

    def modify_event_subscription(
        self,
        subscription_name: str,
        sns_topic_arn: Optional[str] = None,
        source_type: Optional[str] = None,
        event_categories: Optional[List[str]] = None,
        enabled: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Modify an event subscription.

        Args:
            subscription_name: Subscription name
            sns_topic_arn: New SNS topic ARN
            source_type: New source type
            event_categories: New event categories
            enabled: Enable or disable subscription

        Returns:
            Modified event subscription details
        """
        logger.info('Modifying event subscription', name=subscription_name)

        params: Dict[str, Any] = {'SubscriptionName': subscription_name}

        if sns_topic_arn:
            params['SnsTopicArn'] = sns_topic_arn
        if source_type:
            params['SourceType'] = source_type
        if event_categories:
            params['EventCategories'] = event_categories
        if enabled is not None:
            params['Enabled'] = enabled

        response = self.client.call_api('modify_event_subscription', **params)

        subscription = response.get('EventSubscription', {})

        return {
            'success': True,
            'data': {
                'event_subscription': subscription,
                'message': 'Event subscription modified successfully',
            },
            'error': None,
        }

    def delete_event_subscription(self, subscription_name: str) -> Dict[str, Any]:
        """Delete an event subscription.

        Args:
            subscription_name: Subscription name to delete

        Returns:
            Deleted event subscription details
        """
        logger.info('Deleting event subscription', name=subscription_name)

        response = self.client.call_api(
            'delete_event_subscription', SubscriptionName=subscription_name
        )

        subscription = response.get('EventSubscription', {})

        return {
            'success': True,
            'data': {
                'event_subscription': subscription,
                'message': 'Event subscription deleted successfully',
            },
            'error': None,
        }

    def list_event_subscriptions(
        self,
        subscription_name: Optional[str] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List event subscriptions with optional filtering.

        Args:
            subscription_name: Optional subscription name to filter
            filters: Optional filters
            max_results: Maximum results per page
            marker: Pagination token

        Returns:
            List of event subscriptions
        """
        logger.info('Listing event subscriptions')

        params: Dict[str, Any] = {'MaxRecords': max_results}

        if subscription_name:
            params['SubscriptionName'] = subscription_name
        if filters:
            params['Filters'] = filters
        if marker:
            params['Marker'] = marker

        response = self.client.call_api('describe_event_subscriptions', **params)

        subscriptions = response.get('EventSubscriptionsList', [])

        result = {
            'success': True,
            'data': {'event_subscriptions': subscriptions, 'count': len(subscriptions)},
            'error': None,
        }

        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']

        logger.info(f'Retrieved {len(subscriptions)} event subscriptions')
        return result

    def list_events(
        self,
        source_identifier: Optional[str] = None,
        source_type: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        duration: Optional[int] = None,
        event_categories: Optional[List[str]] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List DMS events with optional filtering.

        Args:
            source_identifier: Source identifier to filter events
            source_type: Source type (replication-instance, replication-task, etc.)
            start_time: Start time for events
            end_time: End time for events
            duration: Duration in minutes from now
            event_categories: Event categories to filter
            filters: Optional filters
            max_results: Maximum results per page
            marker: Pagination token

        Returns:
            List of events
        """
        logger.info('Listing events')

        params: Dict[str, Any] = {'MaxRecords': max_results}

        if source_identifier:
            params['SourceIdentifier'] = source_identifier
        if source_type:
            params['SourceType'] = source_type
        if start_time:
            params['StartTime'] = start_time
        if end_time:
            params['EndTime'] = end_time
        if duration:
            params['Duration'] = duration
        if event_categories:
            params['EventCategories'] = event_categories
        if filters:
            params['Filters'] = filters
        if marker:
            params['Marker'] = marker

        response = self.client.call_api('describe_events', **params)

        events = response.get('Events', [])

        result = {'success': True, 'data': {'events': events, 'count': len(events)}, 'error': None}

        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']

        logger.info(f'Retrieved {len(events)} events')
        return result

    def list_event_categories(
        self, source_type: Optional[str] = None, filters: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """List event categories for a source type.

        Args:
            source_type: Source type to get categories for
            filters: Optional filters

        Returns:
            List of event categories
        """
        logger.info('Listing event categories', source_type=source_type)

        params: Dict[str, Any] = {}

        if source_type:
            params['SourceType'] = source_type
        if filters:
            params['Filters'] = filters

        response = self.client.call_api('describe_event_categories', **params)

        event_category_groups = response.get('EventCategoryGroupList', [])

        result = {
            'success': True,
            'data': {
                'event_category_groups': event_category_groups,
                'count': len(event_category_groups),
            },
            'error': None,
        }

        logger.info(f'Retrieved {len(event_category_groups)} event category groups')
        return result

    def update_subscriptions_to_event_bridge(self, force_move: bool = False) -> Dict[str, Any]:
        """Update DMS event subscriptions to use EventBridge.

        Args:
            force_move: Force move even if some subscriptions fail

        Returns:
            Update operation result
        """
        logger.info('Updating subscriptions to EventBridge', force_move=force_move)

        params: Dict[str, Any] = {}
        if force_move:
            params['ForceMove'] = force_move

        response = self.client.call_api('update_subscriptions_to_event_bridge', **params)

        result = response.get('Result', '')

        return {
            'success': True,
            'data': {
                'result': result,
                'message': 'Successfully updated subscriptions to EventBridge',
            },
            'error': None,
        }
