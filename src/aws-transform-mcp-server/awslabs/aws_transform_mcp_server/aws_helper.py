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

"""AWS client helper with caching and user agent configuration."""

import boto3
import os
from awslabs.aws_transform_mcp_server import __version__
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.config import Config
from botocore.credentials import ReadOnlyCredentials
from typing import Any, Dict, Optional


USER_AGENT = f'md/awslabs#mcp#aws-transform-mcp-server#{__version__}'


class AwsHelper:
    """Helper for boto3 session, region, and client management."""

    _client_cache: Dict[str, Any] = {}

    @staticmethod
    def create_session() -> boto3.Session:
        """Create a boto3 Session using AWS_PROFILE if set."""
        profile = (os.environ.get('AWS_PROFILE') or '').strip() or None
        return boto3.Session(profile_name=profile)

    @staticmethod
    def resolve_region(session: Optional[boto3.Session] = None) -> str:
        """Resolve AWS region: AWS_REGION env → session profile region → us-east-1."""
        return (
            os.environ.get('AWS_REGION')
            or (session.region_name if session else None)
            or 'us-east-1'
        )

    @classmethod
    def create_boto3_client(cls, service_name: str, region_name: Optional[str] = None) -> Any:
        """Create or retrieve a cached boto3 client.

        Args:
            service_name: AWS service name (e.g., 'sso-oidc', 'sts').
            region_name: AWS region override. If not provided, uses
                         resolve_region() (AWS_REGION env → profile region → us-east-1).

        Returns:
            A boto3 client for the requested service.
        """
        cache_key = f'{service_name}:{region_name or "default"}'
        if cache_key in cls._client_cache:
            return cls._client_cache[cache_key]

        session = cls.create_session()
        region = region_name or cls.resolve_region(session)
        config = Config(user_agent_extra=USER_AGENT)

        try:
            client = session.client(service_name, region_name=region, config=config)  # type: ignore[call-overload]
        except Exception as e:
            raise Exception(f'Failed to create boto3 client for {service_name}: {str(e)}') from e

        cls._client_cache[cache_key] = client
        return client

    @staticmethod
    def sign_request(
        endpoint: str,
        headers: Dict[str, str],
        body_bytes: bytes,
        credentials: ReadOnlyCredentials,
        service: str,
        region: str,
    ) -> Dict[str, str]:
        """Sign an HTTP request using SigV4 and return the signed headers."""
        aws_request = AWSRequest(method='POST', url=endpoint, data=body_bytes, headers=headers)
        SigV4Auth(credentials, service, region).add_auth(aws_request)
        return dict(aws_request.headers)

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the client cache."""
        cls._client_cache.clear()
