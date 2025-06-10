import os
from typing import Any, Dict

import boto3


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
        client_key = f"{service_name}_{region}"
        if client_key not in self.clients:
            aws_profile = os.environ.get("AWS_PROFILE", "default")
            self.clients[client_key] = boto3.Session(
                profile_name=aws_profile, region_name=region
            ).client(service_name)
        return self.clients[client_key]
