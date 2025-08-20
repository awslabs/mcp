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

"""Role Creator tool."""

import boto3
import json
import logging
import os
from botocore.exceptions import ClientError
from typing import Dict

class RoleCreator:
    """Helper class to create IAM roles with MSK permissions for Lambda functions."""
    
    def __init__(self, region_name=None):
        region_name = region_name or os.environ.get('AWS_REGION')
        aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
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
        
        self.logger = logging.getLogger(__name__)

    def create_msk_lambda_role(self, role_name: str = None) -> Dict:
        """Create a new IAM role with MSK and Lambda permissions."""
        if not role_name:
            import time
            role_name = f"MSK-Lambda-Role-{int(time.time())}"
        
        try:
            # trust policy for Lambda
            trust_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "lambda.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            }
            
            # create the role
            role_response = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="IAM role for Lambda function to access MSK cluster"
            )
            
            #  basic Lambda execution policy
            self.iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
            )
            
            # MSK permissions policy with VPC permissions
            msk_policy = {
                "Version": "2012-10-17",
                "Statement": [
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
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "ec2:DescribeSecurityGroups",
                            "ec2:DescribeSubnets",
                            "ec2:DescribeVpcs",
                            "ec2:CreateNetworkInterface",
                            "ec2:DescribeNetworkInterfaces",
                            "ec2:DeleteNetworkInterface"
                        ],
                        "Resource": "*"
                    }
                ]
            }
            
            # add MSK policy to role
            self.iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName="MSK-Access-Policy",
                PolicyDocument=json.dumps(msk_policy)
            )
            
            role_arn = role_response['Role']['Arn']
            self.logger.info(f"Created IAM role {role_name} with ARN {role_arn}")
            
            return {
                "status": "success",
                "role_name": role_name,
                "role_arn": role_arn,
                "message": f"Created IAM role {role_name} with MSK permissions"
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityAlreadyExists':
                # Role already exists, return its ARN
                role_response = self.iam_client.get_role(RoleName=role_name)
                return {
                    "status": "success",
                    "role_name": role_name,
                    "role_arn": role_response['Role']['Arn'],
                    "message": f"Role {role_name} already exists"
                }
            else:
                raise Exception(f"Failed to create IAM role: {str(e)}")

    def update_lambda_role(self, function_name: str, role_arn: str) -> Dict:
        """Update a Lambda function to use a specific IAM role."""
        try:
            self.lambda_client.update_function_configuration(
                FunctionName=function_name,
                Role=role_arn
            )
            
            self.logger.info(f"Updated Lambda function {function_name} to use role {role_arn}")
            return {
                "status": "success",
                "message": f"Updated Lambda function {function_name} to use new role"
            }
            
        except ClientError as e:
            raise Exception(f"Failed to update Lambda function role: {str(e)}")