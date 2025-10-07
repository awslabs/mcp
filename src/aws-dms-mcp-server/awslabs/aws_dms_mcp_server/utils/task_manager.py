"""
Task Manager.

Handles business logic for AWS DMS replication task operations.
"""

from typing import Any, Dict, List, Optional, Tuple
import json

from loguru import logger

from .dms_client import DMSClient
from .response_formatter import ResponseFormatter
from ..exceptions import DMSInvalidParameterException, DMSValidationException


class TaskManager:
    """Manager for replication task operations."""

    def __init__(self, client: DMSClient):
        """
        Initialize task manager.

        Args:
            client: DMS client wrapper
        """
        self.client = client
        logger.debug('Initialized TaskManager')

    def list_tasks(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 100,
        marker: Optional[str] = None,
        without_settings: bool = False,
    ) -> Dict[str, Any]:
        """
        List replication tasks with optional filtering.

        Args:
            filters: Optional filters for task selection
            max_results: Maximum results per page
            marker: Pagination token
            without_settings: Exclude task settings from response

        Returns:
            Dictionary with tasks list
        """
        logger.info('Listing replication tasks', filters=filters)

        # Build API parameters
        params = {'MaxRecords': max_results, 'WithoutSettings': without_settings}

        if filters:
            params['Filters'] = filters

        if marker:
            params['Marker'] = marker

        # Call API
        response = self.client.call_api('describe_replication_tasks', **params)

        # Format tasks
        tasks = response.get('ReplicationTasks', [])
        formatted_tasks = [ResponseFormatter.format_task(task) for task in tasks]

        result = {
            'success': True,
            'data': {'tasks': formatted_tasks, 'count': len(formatted_tasks)},
            'error': None,
        }

        # Add pagination info
        if response.get('Marker'):
            result['data']['next_marker'] = response['Marker']

        logger.info(f'Retrieved {len(formatted_tasks)} replication tasks')
        return result

    def create_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new replication task.

        Args:
            params: Task creation parameters

        Returns:
            Created task details
        """
        identifier = params.get('ReplicationTaskIdentifier', 'unknown')
        logger.info('Creating replication task', identifier=identifier)

        # Validate required parameters
        required_params = [
            'ReplicationTaskIdentifier',
            'SourceEndpointArn',
            'TargetEndpointArn',
            'ReplicationInstanceArn',
            'MigrationType',
            'TableMappings',
        ]
        for param in required_params:
            if param not in params:
                raise DMSInvalidParameterException(
                    message=f'Missing required parameter: {param}',
                    details={'missing_param': param},
                )

        # Validate table mappings JSON
        table_mappings = params.get('TableMappings')
        is_valid, error_msg = self.validate_table_mappings(table_mappings)
        if not is_valid:
            raise DMSValidationException(
                message=f'Invalid table mappings: {error_msg}',
                details={'validation_error': error_msg},
            )

        # Validate migration type
        migration_type = params.get('MigrationType')
        valid_types = ['full-load', 'cdc', 'full-load-and-cdc']
        if migration_type not in valid_types:
            raise DMSInvalidParameterException(
                message=f'Invalid migration type: {migration_type}',
                details={'valid_types': valid_types},
            )

        # Call API
        response = self.client.call_api('create_replication_task', **params)

        # Format response
        task = response.get('ReplicationTask', {})
        formatted_task = ResponseFormatter.format_task(task)

        result = {
            'success': True,
            'data': {'task': formatted_task, 'message': 'Replication task created successfully'},
            'error': None,
        }

        logger.info(f'Created replication task: {formatted_task.get("identifier")}')
        return result

    def start_task(
        self, task_arn: str, start_type: str, cdc_start_position: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start a replication task.

        Args:
            task_arn: Task ARN
            start_type: Start type (start-replication, resume-processing, reload-target)
            cdc_start_position: CDC start position (for resume operations)

        Returns:
            Task status after start
        """
        logger.info('Starting replication task', task_arn=task_arn, start_type=start_type)

        # Validate start_type
        valid_start_types = ['start-replication', 'resume-processing', 'reload-target']
        if start_type not in valid_start_types:
            raise DMSInvalidParameterException(
                message=f'Invalid start type: {start_type}',
                details={'valid_types': valid_start_types},
            )

        # Build API parameters
        params = {'ReplicationTaskArn': task_arn, 'StartReplicationTaskType': start_type}

        if cdc_start_position:
            params['CdcStartPosition'] = cdc_start_position

        # Call API
        response = self.client.call_api('start_replication_task', **params)

        # Format response
        task = response.get('ReplicationTask', {})
        formatted_task = ResponseFormatter.format_task(task)

        result = {
            'success': True,
            'data': {
                'task': formatted_task,
                'message': f'Replication task started with type: {start_type}',
            },
            'error': None,
        }

        logger.info(f'Started replication task: {task_arn}')
        return result

    def stop_task(self, task_arn: str) -> Dict[str, Any]:
        """
        Stop a running replication task.

        Args:
            task_arn: Task ARN

        Returns:
            Task status after stop
        """
        logger.info('Stopping replication task', task_arn=task_arn)

        # Call API
        response = self.client.call_api('stop_replication_task', ReplicationTaskArn=task_arn)

        # Format response
        task = response.get('ReplicationTask', {})
        formatted_task = ResponseFormatter.format_task(task)

        result = {
            'success': True,
            'data': {'task': formatted_task, 'message': 'Replication task stop initiated'},
            'error': None,
        }

        logger.info(f'Stopped replication task: {task_arn}')
        return result

    def validate_table_mappings(self, mappings: str) -> Tuple[bool, str]:
        """
        Validate table mappings JSON structure.

        Args:
            mappings: Table mappings JSON string

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Parse JSON
            mapping_obj = json.loads(mappings)
        except json.JSONDecodeError as e:
            return False, f'Invalid JSON: {str(e)}'

        # Check for required top-level key
        if 'rules' not in mapping_obj:
            return False, "Missing required key: 'rules'"

        rules = mapping_obj['rules']
        if not isinstance(rules, list):
            return False, "'rules' must be an array"

        if len(rules) == 0:
            return False, 'At least one rule is required'

        # Validate each rule
        valid_rule_types = ['selection', 'transformation', 'table-settings']
        valid_object_locators = ['schema-name', 'table-name', 'column-name']

        for idx, rule in enumerate(rules):
            if not isinstance(rule, dict):
                return False, f'Rule {idx} must be an object'

            # Check rule-type
            rule_type = rule.get('rule-type')
            if not rule_type:
                return False, f"Rule {idx} missing 'rule-type'"

            if rule_type not in valid_rule_types:
                return False, f'Rule {idx} has invalid rule-type: {rule_type}'

            # For selection rules, validate required fields
            if rule_type == 'selection':
                if 'rule-id' not in rule:
                    return False, f"Selection rule {idx} missing 'rule-id'"

                if 'rule-action' not in rule:
                    return False, f"Selection rule {idx} missing 'rule-action'"

                valid_actions = ['include', 'exclude', 'explicit']
                if rule.get('rule-action') not in valid_actions:
                    return False, f'Selection rule {idx} has invalid rule-action'

                if 'object-locator' not in rule:
                    return False, f"Selection rule {idx} missing 'object-locator'"

        return True, ''


# TODO: Add task modification support
# TODO: Add task deletion support
# TODO: Add task status monitoring with polling
