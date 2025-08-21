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

"""Update Event Source Mapping tool."""

import boto3
import logging
import os
from awslabs.aws_serverless_mcp_server.tools.poller.iamHelper import IAMHelper
from awslabs.aws_serverless_mcp_server.tools.poller.listEventSourceMapping import (
    ListEventSourceMapping,
)
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, Optional


class UpdateEventSourceMapping:
    """Tool for updating an Event Source Mapping (ESM) between an Amazon MSK cluster and an AWS Lambda function."""

    def __init__(self):
        """Initialize the UpdateEventSourceMapping tool."""
        region = os.environ.get('AWS_REGION')
        aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')

        try:
            if aws_access_key and aws_secret_key:
                self.lambda_client = boto3.client(
                    'lambda',
                    region_name=region,
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key,
                )
            else:
                self.lambda_client = boto3.client('lambda', region_name=region)
            self.lambda_client.list_functions(MaxItems=1)
        except NoCredentialsError:
            raise Exception('AWS credentials not found in MCP config')
        except Exception as e:
            raise Exception(f'Failed to initialize with MCP config credentials: {str(e)}')

        self.logger = logging.getLogger(__name__)
        self.list_esm = ListEventSourceMapping()
        self.iam_helper = IAMHelper(region_name=region)

    def update_esm_by_uuid(
        self,
        uuid: str,
        batch_size: Optional[int] = None,
        bisect_batch_on_error: Optional[bool] = None,
        enabled: Optional[bool] = None,
        function_name: Optional[str] = None,
        max_batching_window: Optional[int] = None,
        max_record_age: Optional[int] = None,
        report_batch_item_failures: Optional[bool] = None,
        retry_attempts: Optional[int] = None,
        tumbling_window: Optional[int] = None,
        min_pollers: Optional[int] = None,
        max_pollers: Optional[int] = None,
        check_permissions: bool = True,
    ) -> Dict:
        """Updates an Event Source Mapping by its UUID.

        Args:
            uuid (str): UUID of the Event Source Mapping to update
            batch_size (int, optional): Number of records to retrieve
            bisect_batch_on_error (bool, optional): Split the batch on error
            enabled (bool, optional): Whether the mapping is enabled
            function_name (str, optional): Name or ARN of the Lambda function
            max_batching_window (int, optional): Maximum batching window in seconds
            max_record_age (int, optional): Maximum record age in seconds
            report_batch_item_failures (bool, optional): Report batch item failures
            retry_attempts (int, optional): Number of retry attempts
            tumbling_window (int, optional): Tumbling window in seconds
            min_pollers (int, optional): Minimum number of pollers for provisioned concurrency
            max_pollers (int, optional): Maximum number of pollers for provisioned concurrency
            check_permissions (bool, optional): Whether to check and add IAM permissions

        Returns:
            Dict: Updated Event Source Mapping details
        """
        try:
            if not uuid:
                raise ValueError('Event Source Mapping UUID is required')
            if function_name and check_permissions:
                self.logger.info(f'Checking IAM permissions for function: {function_name}')
                try:
                    self.iam_helper.add_msk_permissions(function_name)
                    self.logger.info(
                        f'Successfully verified/added MSK permissions for function: {function_name}'
                    )
                except Exception as e:
                    self.logger.warning(
                        f'Failed to add MSK permissions: {str(e)}. Continuing with update.'
                    )

            elif check_permissions:
                try:
                    # find the current mapping to find the function name
                    current_mapping = self.lambda_client.get_event_source_mapping(UUID=uuid)
                    current_function = current_mapping.get('FunctionArn', '').split(':')[-1]

                    if current_function:
                        self.logger.info(
                            f'Checking IAM permissions for function: {current_function}'
                        )
                        self.iam_helper.add_msk_permissions(current_function)
                        self.logger.info(
                            f'Successfully verified/added MSK permissions for function: {current_function}'
                        )
                except Exception as e:
                    self.logger.warning(
                        f'Failed to add MSK permissions: {str(e)}. Continuing with update.'
                    )

            update_params = {'UUID': uuid}

            # We will only add parameters that have non-None values
            if batch_size is not None:
                update_params['BatchSize'] = batch_size
            if bisect_batch_on_error is not None:
                update_params['BisectBatchOnError'] = bisect_batch_on_error
            if enabled is not None:
                update_params['Enabled'] = enabled
            if function_name is not None:
                update_params['FunctionName'] = function_name
            if max_batching_window is not None:
                update_params['MaximumBatchingWindowInSeconds'] = max_batching_window
            if max_record_age is not None:
                update_params['MaximumRecordAgeInSeconds'] = max_record_age
            if retry_attempts is not None:
                update_params['MaximumRetryAttempts'] = retry_attempts
            if tumbling_window is not None:
                update_params['TumblingWindowInSeconds'] = tumbling_window

            # Batch item failures reporting
            if report_batch_item_failures is not None and report_batch_item_failures:
                update_params['FunctionResponseTypes'] = ['ReportBatchItemFailures']

            # Provisioned poller config
            if min_pollers is not None or max_pollers is not None:
                poller_config = {}
                if min_pollers is not None:
                    poller_config['MinimumPollers'] = min_pollers
                if max_pollers is not None:
                    poller_config['MaximumPollers'] = max_pollers

                if poller_config:
                    update_params['ProvisionedPollerConfig'] = poller_config

            self.logger.info(f'Updating Event Source Mapping with UUID: {uuid}')
            self.logger.info(f'Update parameters: {update_params}')

            self.lambda_client.update_event_source_mapping(**update_params)
            self.logger.info(f'Successfully updated Event Source Mapping: {uuid}')

            self.logger.info('Retrieving updated mapping details:')
            return self._display_updated_mapping(uuid)

        except ClientError as e:
            error_msg = f'AWS API Error updating Event Source Mapping: {e.response["Error"]["Code"]} - {e.response["Error"]["Message"]}'
            self.logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f'Error updating Event Source Mapping: {str(e)}'
            self.logger.error(error_msg)
            raise Exception(error_msg)

    def update_esm_by_function_and_source(
        self,
        function_name: str,
        event_source_arn: str = None,
        kafka_bootstrap_servers: str = None,
        kafka_topic: Optional[str] = None,
        batch_size: Optional[int] = None,
        bisect_batch_on_error: Optional[bool] = None,
        enabled: Optional[bool] = None,
        max_batching_window: Optional[int] = None,
        max_record_age: Optional[int] = None,
        report_batch_item_failures: Optional[bool] = None,
        retry_attempts: Optional[int] = None,
        tumbling_window: Optional[int] = None,
        min_pollers: Optional[int] = None,
        max_pollers: Optional[int] = None,
        check_permissions: bool = True,
    ) -> Dict:
        """Finds and updates an Event Source Mapping by Lambda function name and MSK cluster ARN.

        Args:
            function_name (str): Name or ARN of the Lambda function
            event_source_arn (str): ARN of the MSK cluster
            kafka_bootstrap_servers (str): Bootstrap servers for SMK
            kafka_topic (str, optional): Kafka topic name to further filter mappings
            batch_size (int, optional): Number of records to retrieve
            bisect_batch_on_error (bool, optional): Split the batch on error
            enabled (bool, optional): Whether the mapping is enabled
            max_batching_window (int, optional): Maximum batching window in seconds
            max_record_age (int, optional): Maximum record age in seconds
            report_batch_item_failures (bool, optional): Report batch item failures
            retry_attempts (int, optional): Number of retry attempts
            tumbling_window (int, optional): Tumbling window in seconds
            min_pollers (int, optional): Minimum number of pollers for provisioned concurrency
            max_pollers (int, optional): Maximum number of pollers for provisioned concurrency
            check_permissions (bool, optional): Whether to check and add IAM permissions

        Returns:
            Dict: Updated Event Source Mapping details
        """
        try:
            if not function_name:
                raise ValueError('Lambda function name is required')
            if not event_source_arn and not kafka_bootstrap_servers:
                raise ValueError('Either event_source_arn or kafka_bootstrap_servers is required')

            if check_permissions and event_source_arn:
                self.logger.info(f'Checking IAM permissions for function: {function_name}')
                try:
                    self.iam_helper.add_msk_permissions(function_name)
                    self.logger.info(
                        f'Successfully verified/added MSK permissions for function: {function_name}'
                    )
                except Exception as e:
                    self.logger.warning(
                        f'Failed to add MSK permissions: {str(e)}. Continuing with update.'
                    )

            if event_source_arn:
                mappings = self.lambda_client.list_event_source_mappings(
                    FunctionName=function_name, EventSourceArn=event_source_arn
                )
            else:
                mappings = self.lambda_client.list_event_source_mappings(
                    FunctionName=function_name
                )

            target_mapping = None
            for mapping in mappings.get('EventSourceMappings', []):
                # For MSK, match by event source ARN
                if event_source_arn and mapping.get('EventSourceArn') == event_source_arn:
                    if kafka_topic:
                        mapping_topics = mapping.get('Topics', [])
                        if kafka_topic not in mapping_topics:
                            continue
                    target_mapping = mapping
                    break
                # For SMK, match by bootstrap servers
                elif kafka_bootstrap_servers and mapping.get('SelfManagedEventSource'):
                    smk_endpoints = mapping.get('SelfManagedEventSource', {}).get('Endpoints', {})
                    smk_servers = smk_endpoints.get('KAFKA_BOOTSTRAP_SERVERS', [])
                    if set(smk_servers) == {s.strip() for s in kafka_bootstrap_servers.split(',')}:
                        if kafka_topic:
                            mapping_topics = mapping.get('Topics', [])
                            if kafka_topic not in mapping_topics:
                                continue
                        target_mapping = mapping
                        break

            if not target_mapping:
                source_identifier = event_source_arn or kafka_bootstrap_servers
                source_type = 'MSK ARN' if event_source_arn else 'SMK bootstrap servers'
                error_msg = f'No matching Event Source Mapping found for function {function_name} and {source_type} {source_identifier}'
                if kafka_topic:
                    error_msg += f' with topic {kafka_topic}'
                self.logger.warning(error_msg)
                return {'Error': error_msg}

            uuid = target_mapping['UUID']
            return self.update_esm_by_uuid(
                uuid=uuid,
                batch_size=batch_size,
                bisect_batch_on_error=bisect_batch_on_error,
                enabled=enabled,
                max_batching_window=max_batching_window,
                max_record_age=max_record_age,
                report_batch_item_failures=report_batch_item_failures,
                retry_attempts=retry_attempts,
                tumbling_window=tumbling_window,
                min_pollers=min_pollers,
                max_pollers=max_pollers,
                check_permissions=False,
            )

        except ClientError as e:
            error_msg = f'AWS API Error updating Event Source Mapping: {e.response["Error"]["Code"]} - {e.response["Error"]["Message"]}'
            self.logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f'Error updating Event Source Mapping: {str(e)}'
            self.logger.error(error_msg)
            raise Exception(error_msg)

    def _display_updated_mapping(self, uuid: str) -> Dict:
        """Helper method to display the updated mapping using the list tool.

        Args:
            uuid (str): UUID of the updated Event Source Mapping

        Returns:
            Dict: Formatted mapping details
        """
        try:
            import time

            time.sleep(1)

            response = self.lambda_client.get_event_source_mapping(UUID=uuid)

            function_arn = response.get('FunctionArn', '')
            function_parts = function_arn.split(':')

            formatted_mapping = {
                'UUID': response.get('UUID'),
                'FunctionName': function_parts[-1] if len(function_parts) > 5 else function_arn,
                'EventSourceArn': response.get('EventSourceArn'),
                'Region': function_parts[3] if len(function_parts) > 3 else 'unknown',
                'State': response.get('State'),
                'Topics': response.get('Topics', []),
                'BatchSize': response.get('BatchSize'),
                'MaximumBatchingWindowInSeconds': response.get('MaximumBatchingWindowInSeconds'),
                'MaximumRetryAttempts': response.get('MaximumRetryAttempts'),
                'MaximumRecordAgeInSeconds': response.get('MaximumRecordAgeInSeconds'),
                'BisectBatchOnError': response.get('BisectBatchOnError'),
                'LastProcessingResult': response.get('LastProcessingResult'),
                'StateTransitionReason': response.get('StateTransitionReason'),
                'LastModified': response.get('LastModified').strftime('%Y-%m-%d %H:%M:%S')
                if response.get('LastModified')
                else None,
            }

            if 'ProvisionedPollerConfig' in response:
                poller_config = response.get('ProvisionedPollerConfig', {})
                formatted_mapping['ProvisionedPollerConfig'] = {
                    'MinimumPollers': poller_config.get('MinimumPollers'),
                    'MaximumPollers': poller_config.get('MaximumPollers'),
                }

            return {'UpdatedEventSourceMapping': formatted_mapping}

        except Exception as e:
            self.logger.warning(f'Error displaying updated mapping: {str(e)}')
            return {
                'Message': 'Event Source Mapping was updated, but there was an error retrieving the updated details.'
            }
