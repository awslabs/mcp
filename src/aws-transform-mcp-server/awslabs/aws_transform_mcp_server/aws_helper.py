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
from botocore.config import Config
from typing import Any, Dict, Optional


USER_AGENT = f'md/awslabs#mcp#aws-transform-mcp-server#{__version__}'


class AwsHelper:
    """Singleton helper for creating and caching boto3 clients."""

    _client_cache: Dict[str, Any] = {}

    @classmethod
    def create_boto3_client(cls, service_name: str, region_name: Optional[str] = None) -> Any:
        """Create or retrieve a cached boto3 client.

        Args:
            service_name: AWS service name (e.g., 'sso-oidc', 'sts').
            region_name: AWS region. Falls back to AWS_REGION env var.

        Returns:
            A boto3 client for the requested service.
        """
        cache_key = f'{service_name}:{region_name or "default"}'
        if cache_key in cls._client_cache:
            return cls._client_cache[cache_key]

        config = Config(user_agent_extra=USER_AGENT)
        region = region_name or os.environ.get('AWS_REGION')
        profile = os.environ.get('AWS_PROFILE')

        try:
            if profile:
                session = boto3.Session(profile_name=profile, region_name=region)
                client = session.client(service_name, config=config)  # type: ignore[call-overload]
            elif region:
                client = boto3.client(service_name, region_name=region, config=config)  # type: ignore[call-overload]
            else:
                client = boto3.client(service_name, config=config)  # type: ignore[call-overload]
        except Exception as e:
            raise Exception(f'Failed to create boto3 client for {service_name}: {str(e)}') from e

        cls._client_cache[cache_key] = client
        return client

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the client cache."""
        cls._client_cache.clear()
