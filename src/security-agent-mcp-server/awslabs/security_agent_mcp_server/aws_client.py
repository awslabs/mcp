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

"""AWS SecurityAgent API client using boto3 SDK."""

import boto3
import json
import re
from typing import Any, Optional


class SecurityAgentClient:
    """Client for AWS SecurityAgent APIs using boto3."""

    def __init__(self, region: str = 'us-east-1'):
        """Initialize SecurityAgent client."""
        self.region = region

    def _get_session(self):
        """Fresh session each call to pick up rotated credentials."""
        return boto3.Session(region_name=self.region)

    def _client(self):
        """Get a fresh securityagent boto3 client."""
        return self._get_session().client('securityagent')

    def call(self, operation: str, params: dict) -> dict:
        """Call any SecurityAgent API operation generically."""
        if not re.match(r'^[A-Za-z]+$', operation):
            raise ValueError(f'Invalid operation name: {operation}')
        client = self._client()
        # Convert PascalCase operation to snake_case method name
        method_name = re.sub(r'(?<!^)(?=[A-Z])', '_', operation).lower()
        method = getattr(client, method_name, None)
        if not method:
            raise ValueError(f'Unknown operation: {operation}')
        return method(**params)

    def get_caller_identity(self) -> dict:
        """Get the current AWS caller identity."""
        return self._get_session().client('sts').get_caller_identity()

    def list_agent_spaces(self) -> list[dict]:
        """List all SecurityAgent agent spaces."""
        result = self._client().list_agent_spaces()
        return result.get('agentSpaceSummaries', [])

    def get_agent_space(self, agent_space_id: str) -> dict:
        """Get details for a specific agent space."""
        result = self._client().batch_get_agent_spaces(agentSpaceIds=[agent_space_id])
        spaces = result.get('agentSpaces', [])
        return spaces[0] if spaces else {}

    def update_agent_space(
        self,
        agent_space_id: str,
        name: str,
        iam_roles: Optional[list[str]] = None,
        s3_buckets: Optional[list[str]] = None,
    ) -> dict:
        """Update an agent space with roles and buckets."""
        kwargs: dict[str, Any] = {'agentSpaceId': agent_space_id, 'name': name}
        aws_resources: dict[str, Any] = {}
        if iam_roles:
            aws_resources['iamRoles'] = iam_roles
        if s3_buckets:
            aws_resources['s3Buckets'] = s3_buckets
        if aws_resources:
            kwargs['awsResources'] = aws_resources
        return self._client().update_agent_space(**kwargs)

    def create_agent_space(
        self, name: str, service_role: Optional[str] = None, s3_bucket: Optional[str] = None
    ) -> dict:
        """Create a new SecurityAgent agent space."""
        kwargs: dict[str, Any] = {'name': name}
        if service_role or s3_bucket:
            kwargs['awsResources'] = {}
            if service_role:
                kwargs['awsResources']['iamRoles'] = [service_role]
            if s3_bucket:
                kwargs['awsResources']['s3Buckets'] = [s3_bucket]
        return self._client().create_agent_space(**kwargs)

    def create_code_review(
        self,
        agent_space_id: str,
        title: str,
        service_role: str,
        s3_url: str,
    ) -> dict:
        """Create a code review resource."""
        return self._client().create_code_review(
            agentSpaceId=agent_space_id,
            title=title,
            serviceRole=service_role,
            assets={'sourceCode': [{'s3Location': s3_url}]},
        )

    def start_code_review_job(self, agent_space_id: str, code_review_id: str) -> dict:
        """Start a code review scan job."""
        return self._client().start_code_review_job(
            agentSpaceId=agent_space_id,
            codeReviewId=code_review_id,
        )

    def batch_get_code_review_jobs(self, agent_space_id: str, job_ids: list[str]) -> dict:
        """Get status of code review jobs."""
        return self._client().batch_get_code_review_jobs(
            agentSpaceId=agent_space_id,
            codeReviewJobIds=job_ids,
        )

    def stop_code_review_job(self, agent_space_id: str, code_review_job_id: str) -> dict:
        """Stop a running code review job."""
        return self._client().stop_code_review_job(
            agentSpaceId=agent_space_id,
            codeReviewJobId=code_review_job_id,
        )

    def list_findings(self, agent_space_id: str, code_review_job_id: str) -> dict:
        """List all findings for a completed scan job, handling pagination."""
        client = self._client()
        all_findings: list[dict] = []
        kwargs: dict[str, Any] = {
            'agentSpaceId': agent_space_id,
            'codeReviewJobId': code_review_job_id,
        }
        while True:
            result = client.list_findings(**kwargs)
            all_findings.extend(result.get('findingsSummaries', []))
            next_token = result.get('nextToken')
            if not next_token:
                break
            kwargs['nextToken'] = next_token
        return {'findingsSummaries': all_findings}

    def batch_get_findings(self, agent_space_id: str, finding_ids: list[str]) -> dict:
        """Get detailed findings by ID."""
        return self._client().batch_get_findings(
            agentSpaceId=agent_space_id,
            findingIds=finding_ids,
        )

    # --- Non-SecurityAgent helpers (S3, IAM, STS) ---

    def create_s3_bucket(self, bucket_name: str) -> str:
        """Create S3 bucket for code uploads with 30-day lifecycle policy."""
        s3 = self._get_session().client('s3')
        create_args: dict[str, Any] = {'Bucket': bucket_name}
        if self.region != 'us-east-1':
            create_args['CreateBucketConfiguration'] = {'LocationConstraint': self.region}
        s3.create_bucket(**create_args)
        s3.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': True,
                'IgnorePublicAcls': True,
                'BlockPublicPolicy': True,
                'RestrictPublicBuckets': True,
            },
        )
        s3.put_bucket_lifecycle_configuration(
            Bucket=bucket_name,
            LifecycleConfiguration={
                'Rules': [
                    {
                        'ID': 'AutoDeleteUploads',
                        'Status': 'Enabled',
                        'Filter': {'Prefix': ''},
                        'Expiration': {'Days': 30},
                    }
                ]
            },
        )
        return bucket_name

    def create_service_role(self, role_name: str, account_id: str, bucket_name: str) -> str:
        """Create IAM service role for Security Agent with S3 + CloudWatch Logs access."""
        iam = self._get_session().client('iam')

        trust_policy = json.dumps(
            {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Effect': 'Allow',
                        'Principal': {'Service': 'securityagent.amazonaws.com'},
                        'Action': 'sts:AssumeRole',
                    }
                ],
            }
        )

        permissions_policy = json.dumps(
            {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Effect': 'Allow',
                        'Action': ['s3:GetObject', 's3:GetObjectVersion', 's3:ListBucket'],
                        'Resource': [
                            f'arn:aws:s3:::security-agent-scans-{account_id}-{self.region}',
                            f'arn:aws:s3:::security-agent-scans-{account_id}-{self.region}/*',
                        ],
                    },
                    {
                        'Effect': 'Allow',
                        'Action': [
                            'logs:CreateLogGroup',
                            'logs:CreateLogStream',
                            'logs:PutLogEvents',
                        ],
                        'Resource': f'arn:aws:logs:*:{account_id}:log-group:/aws/securityagent/*',
                    },
                ],
            }
        )

        try:
            iam.create_role(RoleName=role_name, AssumeRolePolicyDocument=trust_policy)
        except iam.exceptions.EntityAlreadyExistsException:
            iam.update_assume_role_policy(
                RoleName=role_name, PolicyDocument=trust_policy
            )

        iam.put_role_policy(
            RoleName=role_name,
            PolicyName='SecurityAgentCodeReviewAccess',
            PolicyDocument=permissions_policy,
        )

        return f'arn:aws:iam::{account_id}:role/{role_name}'

    def upload_to_s3(self, bucket: str, key: str, file_path: str) -> str:
        """Upload a file to S3."""
        self._get_session().client('s3').upload_file(file_path, bucket, key)
        return f's3://{bucket}/{key}'
