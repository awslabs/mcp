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

"""List Event Source Mapping tool."""

import boto3
import logging
import os
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, List, Optional

class ListEventSourceMapping:
    """
    Tool for listing Event Source Mappings (ESM) between Amazon MSK clusters and AWS Lambda functions.
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
            
            #check the credentials, still may change based on what @errona says
            self.lambda_client.list_functions(MaxItems=1)
        except NoCredentialsError:
            raise Exception("AWS credentials not found in MCP config")
        except Exception as e:
            raise Exception(f"Failed to initialize with MCP config credentials: {str(e)}")
        
        self.logger = logging.getLogger(__name__)

    def list_all_esm(self, max_items: Optional[int] = None) -> Dict:
        """
        Lists all Event Source Mappings in the account.
        
        Args:
            max_items (int, optional): Maximum number of items to return
            
        Returns:
            Dict: List of Event Source Mappings
        """
        try:
            params = {}
            if max_items:
                params['MaxItems'] = max_items
                
            self.logger.info("Listing all Event Source Mappings")
            response = self.lambda_client.list_event_source_mappings(**params)
            
            #format the response for better readability
            formatted_mappings = []
            for mapping in response.get('EventSourceMappings', []):
                event_source_arn = mapping.get('EventSourceArn', '')
                self_managed_source = mapping.get('SelfManagedEventSource')
                
                if 'kafka' in event_source_arn.lower() or self_managed_source:
                    formatted_mapping = self._format_mapping(mapping)
                    formatted_mappings.append(formatted_mapping)
                
            return {"EventSourceMappings": formatted_mappings, "Count": len(formatted_mappings)}

        except ClientError as e:
            error_msg = f"AWS API Error listing Event Source Mappings: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Error listing Event Source Mappings: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)

    def list_esm_by_function(self, function_name: str) -> Dict:
        """
        Lists Event Source Mappings for a specific Lambda function.
        
        Args:
            function_name (str): Name or ARN of the Lambda function
            
        Returns:
            Dict: List of Event Source Mappings for the function
        """
        try:
            if not function_name:
                raise ValueError("Lambda function name is required")

            self.logger.info(f"Listing Event Source Mappings for function: {function_name}")
            response = self.lambda_client.list_event_source_mappings(FunctionName=function_name)

            formatted_mappings = []
            for mapping in response.get('EventSourceMappings', []):
                event_source_arn = mapping.get('EventSourceArn', '')
                self_managed_source = mapping.get('SelfManagedEventSource')
                
                if 'kafka' in event_source_arn.lower() or self_managed_source:
                    formatted_mapping = self._format_mapping(mapping)
                    formatted_mappings.append(formatted_mapping)
                
            return {"EventSourceMappings": formatted_mappings, "Count": len(formatted_mappings)}

        except ClientError as e:
            error_msg = f"AWS API Error listing Event Source Mappings: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Error listing Event Source Mappings: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)

    def list_esm_by_source(self, event_source_arn: str) -> Dict:
        """
        Lists Event Source Mappings for a specific event source (MSK cluster).
        
        Args:
            event_source_arn (str): ARN of the MSK cluster
            
        Returns:
            Dict: List of Event Source Mappings for the event source
        """
        try:
            if not event_source_arn:
                raise ValueError("Event source ARN is required")

            self.logger.info(f"Listing Event Source Mappings for source: {event_source_arn}")
            response = self.lambda_client.list_event_source_mappings(EventSourceArn=event_source_arn)

            formatted_mappings = []
            for mapping in response.get('EventSourceMappings', []):
                formatted_mapping = self._format_mapping(mapping)
                formatted_mappings.append(formatted_mapping)
                
            return {"EventSourceMappings": formatted_mappings, "Count": len(formatted_mappings)}

        except ClientError as e:
            error_msg = f"AWS API Error listing Event Source Mappings: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Error listing Event Source Mappings: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
    
    def _format_mapping(self, mapping: Dict) -> Dict:
        """
        Helper method to format a mapping for better readability.
        
        Args:
            mapping (Dict): Raw mapping from AWS API
            
        Returns:
            Dict: Formatted mapping
        """
        try:
            function_arn = mapping.get('FunctionArn', '')
            function_parts = function_arn.split(':')
            
            # Determine if MSK or SMK
            event_source_arn = mapping.get('EventSourceArn')
            self_managed_source = mapping.get('SelfManagedEventSource')
            
            if event_source_arn:
                kafka_type = 'MSK'
                source_info = event_source_arn
            elif self_managed_source:
                kafka_type = 'SMK'
                bootstrap_servers = self_managed_source.get('Endpoints', {}).get('KAFKA_BOOTSTRAP_SERVERS', [])
                source_info = ','.join(bootstrap_servers)
            else:
                kafka_type = 'Unknown'
                source_info = 'N/A'
            
            formatted = {
                'UUID': mapping.get('UUID'),
                'Type': kafka_type,
                'FunctionName': function_parts[-1] if len(function_parts) > 5 else function_arn,
                'Region': function_parts[3] if len(function_parts) > 3 else 'unknown',
                'State': mapping.get('State'),
                'Topics': mapping.get('Topics', []),
                'BatchSize': mapping.get('BatchSize'),
                'MaximumBatchingWindowInSeconds': mapping.get('MaximumBatchingWindowInSeconds'),
                'LastProcessingResult': mapping.get('LastProcessingResult'),
                'LastModified': mapping.get('LastModified').strftime('%Y-%m-%d %H:%M:%S') if mapping.get('LastModified') else None
            }
            
            if kafka_type == 'MSK':
                formatted['EventSourceArn'] = event_source_arn
            elif kafka_type == 'SMK':
                formatted['BootstrapServers'] = source_info
            
            return formatted
        except Exception as e:
            self.logger.warning(f"Error formatting mapping: {str(e)}")
            return mapping
    __all__ = ['ListEventSourceMapping']
