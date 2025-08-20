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

"""IAM Helper tool."""

import boto3
import json
import logging
import os
import getpass
import ssl
from kafka import KafkaProducer
from botocore.exceptions import ClientError
from typing import Dict, List, Optional

class IAMHelper:
    """Helper class to manage IAM permissions for Lambda functions accessing MSK."""
    
    def __init__(self, region_name=None):
        region_name = region_name or os.environ.get('AWS_REGION')
        print(f"DEBUG: Initializing IAMHelper with region {region_name}")
        aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        
        try:
            if aws_access_key and aws_secret_key:
                self.iam_client = boto3.client(
                    'iam',
                    region_name=region_name,
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key
                )
                self.lambda_client = boto3.client(
                    'lambda',
                    region_name=region_name,
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key
                )
            else:
                self.iam_client = boto3.client('iam', region_name=region_name)
                self.lambda_client = boto3.client('lambda', region_name=region_name)
            
            self.lambda_client.list_functions(MaxItems=1)
            self.secrets_client = boto3.client(
                'secretsmanager',
                region_name=region_name,
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key
            ) if aws_access_key and aws_secret_key else boto3.client('secretsmanager', region_name=region_name)
            self.kafka_client = boto3.client(
                'kafka',
                region_name=region_name,
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key
            ) if aws_access_key and aws_secret_key else boto3.client('kafka', region_name=region_name)
            print("DEBUG: IAMHelper initialized successfully")
        except Exception as e:
            print(f"DEBUG: IAMHelper initialization failed: {str(e)}")
            raise
        self.logger = logging.getLogger(__name__)

    def get_lambda_role_arn(self, function_name: str) -> str:
        """Get the execution role ARN for a Lambda function."""
        try:
            response = self.lambda_client.get_function(FunctionName=function_name)
            return response['Configuration']['Role']
        except ClientError as e:
            raise Exception(f"Failed to get Lambda function role: {str(e)}")

    def get_role_name_from_arn(self, role_arn: str) -> str:
        """Extract role name from role ARN."""
        #handle both role ARNs and role names
        if role_arn.startswith('arn:aws:iam:'):
            return role_arn.split('/')[-1]
        return role_arn

    def add_msk_permissions(self, function_name: str, kafka_type: str = "MSK") -> Dict:
        """Add necessary Kafka permissions to Lambda execution role."""
        try:
            #get the functions role
            role_arn = self.get_lambda_role_arn(function_name)
            role_name = self.get_role_name_from_arn(role_arn)
            
            self.logger.info(f"Adding {kafka_type} permissions to role: {role_name}")
            
            # Base Kafka permissions
            statements = [
                {
                    "Effect": "Allow",
                    "Action": [
                        "kafka:DescribeCluster",
                        "kafka:DescribeClusterV2",
                        "kafka:GetBootstrapBrokers",
                        "kafka:ListClusters"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "kafka-cluster:Connect",
                        "kafka-cluster:AlterCluster",
                        "kafka-cluster:DescribeCluster",
                        "kafka-cluster:*Topic*",
                        "kafka-cluster:WriteData",
                        "kafka-cluster:ReadData",
                        "kafka-cluster:AlterGroup",
                        "kafka-cluster:DescribeGroup"
                    ],
                    "Resource": "*"
                }
            ]
            
            # Add SMK-specific permissions
            if kafka_type == "SMK":
                statements.extend([
                    {
                        "Effect": "Allow",
                        "Action": [
                            "ec2:DescribeSecurityGroups",
                            "ec2:DescribeSubnets",
                            "ec2:DescribeVpcs",
                            "ec2:CreateNetworkInterface",
                            "ec2:DescribeNetworkInterfaces",
                            "ec2:DeleteNetworkInterface",
                            "ec2:AttachNetworkInterface",
                            "ec2:DetachNetworkInterface"
                        ],
                        "Resource": "*"
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "secretsmanager:GetSecretValue",
                            "secretsmanager:DescribeSecret"
                        ],
                        "Resource": "*"
                    }
                ])
            
            kafka_policy = {
                "Version": "2012-10-17",
                "Statement": statements
            }
            
            policy_name = f"{kafka_type}-Lambda-Access"
            
            self.iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName=policy_name,
                PolicyDocument=json.dumps(kafka_policy)
            )
            
            self.logger.info(f"Successfully added {kafka_type} permissions to role {role_name}")
            return {"status": "success", "message": f"{kafka_type} permissions added to role {role_name}"}
                
        except ClientError as e:
            error_msg = f"AWS API Error adding MSK permissions: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Error adding MSK permissions: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)

    def get_secret_from_arn(self, secret_arn: str, prompt_if_failed: bool = True) -> Optional[Dict]:
        """Retrieve secret from AWS Secrets Manager with fallback to manual input."""
        try:
            response = self.secrets_client.get_secret_value(SecretArn=secret_arn)
            return json.loads(response['SecretString'])
        except ClientError as e:
            if prompt_if_failed:
                print(f"Cannot access secret: {e.response['Error']['Code']}")
                return self.prompt_for_credentials()
            return None

    def prompt_for_credentials(self) -> Dict:
        """Interactive prompt for missing credentials."""
        print("Please provide credentials:")
        username = input("Username: ")
        password = getpass.getpass("Password: ")
        return {"username": username, "password": password}

    def get_msk_bootstrap_brokers(self, cluster_arn: str) -> Dict:
        """Get MSK bootstrap brokers."""
        try:
            response = self.kafka_client.get_bootstrap_brokers(ClusterArn=cluster_arn)
            return {
                "plaintext": response.get('BootstrapBrokerString', ''),
                "tls": response.get('BootstrapBrokerStringTls', ''),
                "sasl_scram": response.get('BootstrapBrokerStringSaslScram', ''),
                "sasl_iam": response.get('BootstrapBrokerStringSaslIam', '')
            }
        except ClientError as e:
            raise Exception(f"Failed to get bootstrap brokers: {str(e)}")

    def test_kafka_connection(self, bootstrap_servers: str, security_protocol: str = 'PLAINTEXT', 
                            sasl_mechanism: str = None, sasl_secret_arn: str = None, 
                            tls_cert_secret_arn: str = None, prompt_for_missing: bool = True) -> Dict:
        """Test Kafka connection with specified authentication."""
        config = {
            'bootstrap_servers': bootstrap_servers,
            'security_protocol': security_protocol,
            'value_serializer': lambda x: json.dumps(x).encode('utf-8')
        }

        if security_protocol in ['SASL_SSL', 'SASL_PLAINTEXT'] and sasl_mechanism:
            config['sasl_mechanism'] = sasl_mechanism
            if sasl_secret_arn:
                creds = self.get_secret_from_arn(sasl_secret_arn, prompt_for_missing)
                if creds:
                    config['sasl_plain_username'] = creds['username']
                    config['sasl_plain_password'] = creds['password']

        if security_protocol in ['SSL', 'SASL_SSL']:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            config['ssl_context'] = ssl_context
            
            if tls_cert_secret_arn:
                cert_info = self.get_secret_from_arn(tls_cert_secret_arn, prompt_for_missing)
                if cert_info:
                    config['ssl_certfile'] = cert_info.get('certificate')
                    config['ssl_keyfile'] = cert_info.get('private_key')
                    if cert_info.get('private_key_password'):
                        config['ssl_password'] = cert_info['private_key_password']

        try:
            producer = KafkaProducer(**config)
            producer.close()
            return {"status": "success", "message": "Connection successful"}
        except Exception as e:
            return {"status": "error", "message": f"Connection failed: {str(e)}"}