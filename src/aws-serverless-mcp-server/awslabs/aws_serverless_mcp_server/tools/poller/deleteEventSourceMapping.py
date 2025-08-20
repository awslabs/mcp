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

"""Delete Event Source Mapping tool."""

import boto3
import logging
import os
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, Optional

class DeleteEventSourceMapping:
    """
    Tool for deleting an Event Source Mapping (ESM) between an Amazon MSK cluster and an AWS Lambda function.
    """

    def __init__(self):
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

            self.lambda_client.list_functions(MaxItems=1)
        except NoCredentialsError:
            raise Exception("AWS credentials not found in MCP config")
        except Exception as e:
            raise Exception(f"Failed to initialize with MCP config credentials: {str(e)}")
        
        self.logger = logging.getLogger(__name__)

    def delete_esm_by_uuid(self, uuid: str) -> Dict:
        """
        Deletes an Event Source Mapping by its UUID.
        
        Args:
            uuid (str): UUID of the Event Source Mapping to delete
            
        Returns:
            Dict: Deleted Event Source Mapping details
        """
        try:
            if not uuid:
                raise ValueError("Event Source Mapping UUID is required")

            self.logger.info(f"Deleting Event Source Mapping with UUID: {uuid}")
            response = self.lambda_client.delete_event_source_mapping(UUID=uuid)
            
            self.logger.info(f"Successfully deleted Event Source Mapping: {uuid}")
            return response

        except ClientError as e:
            error_msg = f"AWS API Error deleting Event Source Mapping: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Error deleting Event Source Mapping: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)

    def delete_esm_by_function_and_source(self, 
                                         function_name: str, 
                                         event_source_arn: str = None,
                                         kafka_bootstrap_servers: str = None,
                                         kafka_topic: Optional[str] = None) -> Dict:
        """
        Finds and deletes the Event Source Mapping for a Lambda function and MSK cluster ARN.
        
        Args:
            function_name (str): Name or ARN of the Lambda function
            event_source_arn (str): ARN of the MSK cluster
            kafka_topic (str, optional): Kafka topic name to further filter the mapping
            
        Returns:
            Dict: Information about the deleted mapping
        """
        try:
            if not function_name:
                raise ValueError("Lambda function name is required")
            if not event_source_arn and not kafka_bootstrap_servers:
                raise ValueError("Either event_source_arn or kafka_bootstrap_servers is required")

            mappings = self.lambda_client.list_event_source_mappings(
                FunctionName=function_name
            )
            
            target_mapping = None
            deleted_count = 0
            
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
                    if set(smk_servers) == set([s.strip() for s in kafka_bootstrap_servers.split(',')]):
                        if kafka_topic:
                            mapping_topics = mapping.get('Topics', [])
                            if kafka_topic not in mapping_topics:
                                continue
                        target_mapping = mapping
                        break
            
            if not target_mapping:
                source_identifier = event_source_arn or kafka_bootstrap_servers
                source_type = "MSK ARN" if event_source_arn else "SMK bootstrap servers"
                self.logger.warning(f"No matching Event Source Mapping found for function {function_name} and {source_type} {source_identifier}")
                return {"DeletedMapping": None, "Message": "No matching mapping found", "Count": 0}

            uuid = target_mapping['UUID']
            self.logger.info(f"Deleting Event Source Mapping with UUID: {uuid}")
            response = self.lambda_client.delete_event_source_mapping(UUID=uuid)
            self.logger.info(f"Successfully deleted Event Source Mapping: {uuid}")
                
            return {"DeletedMapping": response, "Count": 1}

        except ClientError as e:
            error_msg = f"AWS API Error deleting Event Source Mapping: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Error deleting Event Source Mapping: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)