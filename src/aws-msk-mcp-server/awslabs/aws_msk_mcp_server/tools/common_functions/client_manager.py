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

import boto3
import os
from typing import Any, Dict


class AWSClientManager:
    """Manages AWS service clients across different regions."""

    def __init__(self):
        """Initialize the AWS client manager."""
        self.clients: Dict[str, Any] = {}

    def get_client(self, region: str, service_name: str) -> Any:
        """Get or create a service client for the specified service and region.

        Args:
            region: AWS region name
            service_name: The AWS service name (e.g., 'kafka', 'cloudwatch')

        Returns:
            boto3 client for the specified service and region
        """
        client_key = f'{service_name}_{region}'
        if client_key not in self.clients:
            aws_profile = os.environ.get('AWS_PROFILE', 'default')
            self.clients[client_key] = boto3.Session(
                profile_name=aws_profile, region_name=region
            ).client(service_name)
        return self.clients[client_key]
