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

"""Create Event Source Mapping tool."""

import boto3
import logging
import os
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, field

@dataclass
class MetricsConfig:
    metrics: List[str] = field(default_factory=list)

@dataclass
class ProvisionedPollerConfig:
    maximum_pollers: Optional[int] = None
    minimum_pollers: Optional[int] = None

class CreateEventSourceMapping:
    """
    Tool for creating an Event Source Mapping (ESM) between an Amazon MSK cluster or Self-Managed Kafka and an AWS Lambda function.
    This implementation is inspired by the AWS CDK EventSourceMapping construct but uses boto3 for direct API calls.
    """

    def __init__(self):
        # this just reads from the config file
        region = os.environ.get('AWS_REGION')
        aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        
        try:
            if aws_access_key and aws_secret_key:
                self.lambda_client = boto3.client(
                    'lambda',
                    region_name=region,
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key
                )
            else:
                self.lambda_client = boto3.client('lambda', region_name=region)
            
            # testing the credentials
            self.lambda_client.list_functions(MaxItems=1)
        except NoCredentialsError:
            raise Exception("AWS credentials not found in MCP config")
        except Exception as e:
            raise Exception(f"Failed to initialize with MCP config credentials: {str(e)}")
        
        self.logger = logging.getLogger(__name__)

    def create_esm(self,
        target: str,
        event_source_arn: str,
        kafka_topic: str,
        batch_size: Optional[int] = None,
        bisect_batch_on_error: Optional[bool] = None,
        enabled: Optional[bool] = None,
        kafka_bootstrap_servers: Optional[List[str]] = None,
        kafka_consumer_group_id: Optional[str] = None,
        max_batching_window: Optional[int] = None,
        max_record_age: Optional[int] = None,
        report_batch_item_failures: Optional[bool] = None,
        retry_attempts: Optional[int] = None,
        starting_position: Optional[str] = None,
        starting_position_timestamp: Optional[int] = None,
        tumbling_window: Optional[int] = None,
        min_pollers: Optional[int] = 1,
        max_pollers: Optional[int] = 2
    ) -> Dict:
        """
        Creates an Event Source Mapping for an MSK cluster to a Lambda function.
        
        Args:
            target (str): Name or ARN of the Lambda function
            event_source_arn (str): ARN of the event source (MSK cluster)
            kafka_topic (str): Kafka topic name
            batch_size (int, optional): Number of records to retrieve (default: 100)
            bisect_batch_on_error (bool, optional): Split the batch on error
            enabled (bool, optional): Whether the mapping is enabled
            kafka_bootstrap_servers (List[str], optional): Kafka bootstrap servers
            kafka_consumer_group_id (str, optional): Kafka consumer group ID
            max_batching_window (int, optional): Maximum batching window in seconds
            max_record_age (int, optional): Maximum record age in seconds
            min_pollers (int, optional): Minimum number of pollers for provisioned concurrency
            max_pollers (int, optional): Maximum number of pollers for provisioned concurrency
            report_batch_item_failures (bool, optional): Report batch item failures
            retry_attempts (int, optional): Number of retry attempts
            starting_position (str, optional): Starting position (LATEST, TRIM_HORIZON, AT_TIMESTAMP)
            starting_position_timestamp (int, optional): Starting position timestamp
            tumbling_window (int, optional): Tumbling window in seconds
            
        Returns:
            Dict: Created Event Source Mapping details
        """
        try:
            # validate required parameters with better error handling
            if not target or not isinstance(target, str) or target.strip() == '':
                raise ValueError(f"Invalid target parameter: '{target}' - Lambda function name is required and must be a non-empty string")
            if not event_source_arn or not isinstance(event_source_arn, str) or event_source_arn.strip() == '':
                raise ValueError(f"Invalid event_source_arn parameter: '{event_source_arn}' - Event source ARN is required and must be a non-empty string")
            if not kafka_topic or not isinstance(kafka_topic, str) or kafka_topic.strip() == '':
                raise ValueError(f"Invalid kafka_topic parameter: '{kafka_topic}' - Kafka topic name is required and must be a non-empty string")
            
            # Debug logging
            print(f"DEBUG: Creating ESM with target='{target}', event_source_arn='{event_source_arn}', kafka_topic='{kafka_topic}'")

            # Ensure parameters are properly formatted
            target = target.strip()
            event_source_arn = event_source_arn.strip()
            kafka_topic = kafka_topic.strip()
            
            create_params = {
                'FunctionName': target,
                'EventSourceArn': event_source_arn,
                'Topics': [kafka_topic],
                'Enabled': enabled if enabled is not None else True,
            }
            
            print(f"DEBUG: create_params before API call: {create_params}")

            # optional parameters only if they have values
            optional_params = {
                'BatchSize': batch_size,
                'BisectBatchOnError': bisect_batch_on_error,
                'MaximumBatchingWindowInSeconds': max_batching_window,
                'MaximumRecordAgeInSeconds': max_record_age,
                'StartingPosition': starting_position,
                'StartingPositionTimestamp': starting_position_timestamp,
                'TumblingWindowInSeconds': tumbling_window,
                'MaximumRetryAttempts': retry_attempts,
            }

            # only add parameters that have non-None values
            for key, value in optional_params.items():
                if value is not None:
                    create_params[key] = value

            # consumer group ID for self-managed Kafka
            if kafka_consumer_group_id:
                create_params['SelfManagedKafkaEventSourceConfig'] = {
                    'ConsumerGroupId': kafka_consumer_group_id
                }


            if report_batch_item_failures:
                create_params['FunctionResponseTypes'] = ['ReportBatchItemFailures']

            # this gave errors often so here we do provisioned poller config with the provided values or defaults
            create_params['ProvisionedPollerConfig'] = {
                'MinimumPollers': min_pollers,
                'MaximumPollers': max_pollers
            }

            self.logger.info(f"Creating Event Source Mapping with params: {create_params}")
            print(f"DEBUG: About to call create_event_source_mapping with params: {create_params}")
            response = self.lambda_client.create_event_source_mapping(**create_params)
            print(f"DEBUG: Successfully created ESM with UUID: {response.get('UUID', 'Unknown')}")
            
            self.logger.info(f"Successfully created MSK Event Source Mapping: {response['UUID']}")
            return response

        except ClientError as e:
            error_msg = f"AWS API Error creating Event Source Mapping: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Error creating Event Source Mapping: {str(e)}"
            print(f"DEBUG: Exception occurred: {error_msg}")
            print(f"DEBUG: Exception type: {type(e).__name__}")
            self.logger.error(error_msg)
            raise Exception(error_msg)

    def create_smk_esm(self,
        target: str,
        kafka_bootstrap_servers: List[str],
        kafka_topic: str,
        source_access_configurations: Optional[List[Dict]] = None,
        batch_size: Optional[int] = None,
        enabled: Optional[bool] = None,
        kafka_consumer_group_id: Optional[str] = None,
        max_batching_window: Optional[int] = None,
        max_concurrency: Optional[int] = None,
        report_batch_item_failures: Optional[bool] = None,
        retry_attempts: Optional[int] = None,
        starting_position: Optional[str] = None,
        starting_position_timestamp: Optional[int] = None,
        min_pollers: Optional[int] = 1,
        max_pollers: Optional[int] = 2
    ) -> Dict:
        """
        Creates an Event Source Mapping for a Self-Managed Kafka cluster to a Lambda function.
        Note: SMK supports most MSK parameters except TumblingWindow, MaximumRecordAge, BisectBatchOnError.
        """
        try:
            if not target or not isinstance(target, str) or target.strip() == '':
                raise ValueError(f"Invalid target parameter: '{target}' - Lambda function name is required")
            if not kafka_bootstrap_servers or not isinstance(kafka_bootstrap_servers, list):
                raise ValueError(f"Invalid kafka_bootstrap_servers parameter - Bootstrap servers list is required")
            if not kafka_topic or not isinstance(kafka_topic, str) or kafka_topic.strip() == '':
                raise ValueError(f"Invalid kafka_topic parameter: '{kafka_topic}' - Kafka topic name is required")
            
            for server in kafka_bootstrap_servers:
                if not isinstance(server, str) or ':' not in server:
                    raise ValueError(f"Invalid bootstrap server format: '{server}' - Expected format: 'host:port'")
            
            print(f"DEBUG: Creating SMK ESM with target='{target}', bootstrap_servers='{kafka_bootstrap_servers}', kafka_topic='{kafka_topic}'")

            target = target.strip()
            kafka_topic = kafka_topic.strip()
            
            create_params = {
                'FunctionName': target,
                'Topics': [kafka_topic],
                'Enabled': enabled if enabled is not None else True,
                'SelfManagedEventSource': {
                    'Endpoints': {
                        'KAFKA_BOOTSTRAP_SERVERS': kafka_bootstrap_servers
                    }
                }
            }

            # SMK optional parameters
            smk_optional_params = {
                'BatchSize': batch_size,
                'MaximumBatchingWindowInSeconds': max_batching_window,
                'StartingPosition': starting_position,
                'StartingPositionTimestamp': starting_position_timestamp,
                'MaximumRetryAttempts': retry_attempts,
            }

            for key, value in smk_optional_params.items():
                if value is not None:
                    create_params[key] = value

            if kafka_consumer_group_id:
                create_params['SelfManagedKafkaEventSourceConfig'] = {
                    'ConsumerGroupId': kafka_consumer_group_id
                }

            if source_access_configurations:
                create_params['SourceAccessConfigurations'] = source_access_configurations

            if report_batch_item_failures:
                create_params['FunctionResponseTypes'] = ['ReportBatchItemFailures']

            # MaxConcurrency goes in ScalingConfig for SMK
            if max_concurrency is not None:
                create_params['ScalingConfig'] = {
                    'MaximumConcurrency': max_concurrency
                }

            # ProvisionedPollerConfig is supported for both MSK and SMK
            if min_pollers is not None or max_pollers is not None:
                create_params['ProvisionedPollerConfig'] = {
                    'MinimumPollers': min_pollers or 1,
                    'MaximumPollers': max_pollers or 2
                }

            # Note: TumblingWindow, MaximumRecordAge, BisectBatchOnError are NOT supported for SMK

            self.logger.info(f"Creating SMK Event Source Mapping with params: {create_params}")
            response = self.lambda_client.create_event_source_mapping(**create_params)
            print(f"DEBUG: Successfully created SMK ESM with UUID: {response.get('UUID', 'Unknown')}")
            
            self.logger.info(f"Successfully created SMK Event Source Mapping: {response['UUID']}")
            return response

        except ClientError as e:
            error_msg = f"AWS API Error creating SMK Event Source Mapping: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Error creating SMK Event Source Mapping: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)

