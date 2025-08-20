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

"""ESM Testing tool."""

#!/usr/bin/env python3
import os
from typing import Optional
from boto3 import client as boto3_client
from kafka import KafkaProducer, KafkaConsumer
from kafka.structs import TopicPartition
from aws_msk_iam_sasl_signer import MSKAuthTokenProvider
from kafka.sasl.oauth import AbstractTokenProvider
from src.tools.iamHelper import IAMHelper
from src.tools.listEventSourceMapping import ListEventSourceMapping
import json
import time

class MSKOAuthTokenProvider(AbstractTokenProvider):
    def __init__(self, region=None):
        self.region = region or os.environ.get('AWS_REGION')
    
    def token(self):
        token, _ = MSKAuthTokenProvider.generate_auth_token(self.region)
        return token

class ESMTesting:
    def __init__(self, region=None):
        self.region = region or os.environ.get('AWS_REGION')
        self.lambda_client = boto3_client('lambda', region_name=region)
        self.iam_helper = IAMHelper(region_name=region)
        self.list_esm = ListEventSourceMapping()
        self.bootstrap_servers = None
        self.kafka_topic = None

    def _get_config_from_secret(self, secret_arn: str) -> Optional[dict]:
        """get full config from secret arn"""
        try:
            secret = self.iam_helper.get_secret_from_arn(secret_arn, prompt_if_failed=False)
            return secret
        except Exception as e:
            print(f"❌ Could not get config from secret: {e}")
        return None

    def _get_config_from_esm(self, esm_uuid: str) -> dict:
        """get config from esm and msk cluster"""
        config = {}
        try:
            response = self.lambda_client.get_event_source_mapping(UUID=esm_uuid)
            event_source_arn = response.get('EventSourceArn')
            topics = response.get('Topics', [])
            
            if event_source_arn:
                brokers = self.iam_helper.get_msk_bootstrap_brokers(event_source_arn)
                config['iam'] = {
                    'bootstrap_servers': brokers.get('sasl_iam', '').replace('sasl_iam://', ''),
                    'security_protocol': 'SASL_SSL',
                    'sasl_mechanism': 'AWS_MSK_IAM'
                }
                config['cluster_arn'] = event_source_arn
            
            if topics:
                config['topic'] = topics[0]
                
        except Exception as e:
            print(f"❌ Could not get config from ESM: {e}")
        return config

    def _prompt_for_manual_config(self) -> dict:
        """prompt user for manual config if auto detection fails"""
        print("❌ Could not automatically detect configuration.")
        print("Note: This will only be stored for this session.")
        
        bootstrap_servers = input("Enter MSK bootstrap servers (comma-separated): ").strip()
        topic = input("Enter Kafka topic name: ").strip()
        
        return {
            'iam': {
                'bootstrap_servers': bootstrap_servers,
                'security_protocol': 'SASL_SSL',
                'sasl_mechanism': 'AWS_MSK_IAM'
            },
            'topic': topic
        }

    def _setup_connection_params(self, esm_uuid: str, secret_arn: Optional[str] = None, bootstrap_servers: Optional[str] = None, kafka_topic: Optional[str] = None):
        """setup connection parameters for testing"""
        config = None
        
        # try secret first if provided
        if secret_arn:
            config = self._get_config_from_secret(secret_arn)
        
        # fallback to esm discovery
        if not config:
            config = self._get_config_from_esm(esm_uuid)
        
        # manual overrides or prompts
        if not config or not config.get('iam', {}).get('bootstrap_servers'):
            if bootstrap_servers:
                config = config or {}
                config['iam'] = {
                    'bootstrap_servers': bootstrap_servers,
                    'security_protocol': 'SASL_SSL', 
                    'sasl_mechanism': 'AWS_MSK_IAM'
                }
            else:
                config = self._prompt_for_manual_config()
        
        if not config.get('topic'):
            if kafka_topic:
                config['topic'] = kafka_topic
            else:
                print("Note: Topic name will only be stored for this session.")
                config['topic'] = input("Enter Kafka topic name: ").strip()
        
        # set instance variables
        self.bootstrap_servers = config['iam']['bootstrap_servers']
        self.kafka_topic = config['topic']
        self.auth_config = config

    def get_esm_config_output(self, esm_uuid):
        """get esm configuration details as output list"""
        try:
            response = self.lambda_client.get_event_source_mapping(UUID=esm_uuid)
            return [
                "\nESM Configuration:",
                f"  UUID: {response['UUID']}",
                f"  State: {response['State']}",
                f"  Batch Size: {response.get('BatchSize', 'N/A')}",
                f"  Max Batching Window: {response.get('MaximumBatchingWindowInSeconds', 'N/A')}s",
                f"  Starting Position: {response.get('StartingPosition', 'N/A')}",
                f"  Topics: {response.get('Topics', 'N/A')}",
                f"  Function Name: {response.get('FunctionName', 'N/A')}",
                f"  Event Source ARN: {response.get('EventSourceArn', 'N/A')}"
            ]
        except Exception as e:
            return [f"❌ Failed to get ESM config: {e}"]

    def get_consumer_offset(self, consumer_group_id):
        """get current consumer group offset"""
        try:
            token_provider = MSKOAuthTokenProvider(self.region)
            consumer = KafkaConsumer(
                bootstrap_servers=self.bootstrap_servers,
                security_protocol='SASL_SSL',
                sasl_mechanism='OAUTHBEARER',
                sasl_oauth_token_provider=token_provider,
                group_id=consumer_group_id
            )
            
            try:
                partitions = consumer.partitions_for_topic(self.kafka_topic)
                if not partitions:
                    print("❌ No partitions found for topic")
                    return 0
                
                print(f"Found {len(partitions)} partitions: {partitions}")
                
                total_offset = 0
                for partition in partitions:
                    tp = TopicPartition(self.kafka_topic, partition)
                    committed = consumer.committed(tp)
                    print(f"  Partition {partition}: offset {committed}")
                    total_offset += committed if committed else 0
                
                return total_offset
            finally:
                consumer.close()
        except Exception as e:
            print(f"❌ Error getting consumer offset: {e}")
            return 0

    def send_messages(self, message_count, test_type="end_to_end"):
        """send test messages"""
        print(f"Sending {message_count} messages...")
        
        try:
            token_provider = MSKOAuthTokenProvider(self.region)
            producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                security_protocol='SASL_SSL',
                sasl_mechanism='OAUTHBEARER',
                sasl_oauth_token_provider=token_provider,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            
            try:
                for i in range(message_count):
                    message = {'id': f'test-{i+1}', 'timestamp': time.time(), 'data': f'{test_type} test message {i+1}'}
                    future = producer.send(self.kafka_topic, message)
                    future.get(timeout=10)  # wait for delivery confirmation
                    print(f"  ✅ Message {i+1} sent")
                producer.flush()
            finally:
                producer.close()
        except Exception as e:
            print(f"❌ Error sending messages: {e}")
            raise

    def run_load_test_with_config(self, esm_uuid, message_count, test_name, secret_arn=None, bootstrap_servers=None, kafka_topic=None):
        """generic load test with esm config display"""
        try:
            # setup connection parameters
            self._setup_connection_params(esm_uuid, secret_arn, bootstrap_servers, kafka_topic)
            
            output = []
            output.append(f"=== {test_name} ===")
            output.append(f"Consumer Group ID: {esm_uuid}")
            output.append(f"Bootstrap Servers: {self.bootstrap_servers}")
            output.append(f"Topic: {self.kafka_topic}")

            config_output = self.get_esm_config_output(esm_uuid)
            output.extend(config_output)
            
            output.append("\nGetting initial offset...")
            offset_init = self.get_consumer_offset(esm_uuid)
            output.append(f"Initial total offset: {offset_init}")
            
            self.send_messages(message_count, test_name.lower().replace(" ", "_"))
            
            output.append("\nWaiting 90 seconds...")
            time.sleep(90)
            
            output.append("\nGetting final offset...")
            offset_fin = self.get_consumer_offset(esm_uuid)
            output.append(f"Final total offset: {offset_fin}")
            
            messages_processed = offset_fin - offset_init
            output.append(f"\n=== RESULTS ===")
            output.append(f"Messages processed: {messages_processed}")
            output.append(f"Initial offset: {offset_init}")
            output.append(f"Final offset: {offset_fin}")
            
            if messages_processed == message_count:
                output.append(f"✅ {test_name} PASSED - ESM worked properly")
                result = True
            else:
                output.append(f"❌ {test_name} FAILED")
                result = False
            
            full_output = "\n".join(output)
            # Log completion without sensitive data
            print(f"Test execution completed: {test_name}")
            return result, full_output
            
        except Exception as e:
            error_msg = f"❌ {test_name} failed with error: {e}"
            print(error_msg)
            return False, error_msg

    def run_end_to_end_test(self, esm_uuid, secret_arn=None, bootstrap_servers=None, kafka_topic=None):
        return self.run_load_test_with_config(esm_uuid, 5, "End-to-End Test", secret_arn, bootstrap_servers, kafka_topic)

    def run_small_load_test(self, esm_uuid, secret_arn=None, bootstrap_servers=None, kafka_topic=None):
        return self.run_load_test_with_config(esm_uuid, 35, "Small Load Test", secret_arn, bootstrap_servers, kafka_topic)

    def run_medium_load_test(self, esm_uuid, secret_arn=None, bootstrap_servers=None, kafka_topic=None):
        return self.run_load_test_with_config(esm_uuid, 75, "Medium Load Test", secret_arn, bootstrap_servers, kafka_topic)

    def run_large_load_test(self, esm_uuid, secret_arn=None, bootstrap_servers=None, kafka_topic=None):
        return self.run_load_test_with_config(esm_uuid, 150, "Large Load Test", secret_arn, bootstrap_servers, kafka_topic)

    def validate_existing_traffic(self, bootstrap_servers, kafka_topic, esm_uuid, wait_seconds=90):
        """Validate existing traffic processing for SMK/MSK clusters"""
        try:
            self.bootstrap_servers = bootstrap_servers
            self.kafka_topic = kafka_topic
            
            print(f"Validating existing traffic for ESM {esm_uuid}")
            print(f"Bootstrap servers: {bootstrap_servers}")
            print(f"Topic: {kafka_topic}")
            
            initial_offset = self.get_consumer_offset(esm_uuid)
            print(f"Initial offset: {initial_offset}")
            
            print(f"Waiting {wait_seconds} seconds for existing message processing...")
            time.sleep(wait_seconds)
            
            final_offset = self.get_consumer_offset(esm_uuid)
            print(f"Final offset: {final_offset}")
            
            messages_processed = final_offset - initial_offset
            print(f"Messages processed during validation: {messages_processed}")
            
            return messages_processed > 0
            
        except Exception as e:
            print(f"Error during traffic validation: {e}")
            return False