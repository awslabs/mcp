"""
Mock ECS client for testing.
"""

import datetime
from typing import Any, Dict, List, Tuple

from botocore.exceptions import ClientError


class MockEcsClient:
    """Mock implementation of EcsClient for testing."""

    def __init__(self, mock_config=None):
        """
        Initialize with mock configuration.

        Parameters
        ----------
        mock_config : dict, optional
            Configuration for mock responses with keys:
            - cluster_not_found: bool - If True, simulate cluster not found
            - raise_client_error: bool - If True, simulate client error
            - raise_general_error: bool - If True, simulate general error
            - stopped_tasks: List[Dict] - Tasks to return from get_stopped_tasks
            - running_tasks_count: int - Count to return from get_running_tasks_count
        """
        self.mock_config = mock_config or {}

    async def check_cluster_exists(self, cluster_name: str) -> Tuple[bool, Dict[str, Any]]:
        """Mock implementation of check_cluster_exists."""
        if self.mock_config.get("raise_general_error", False):
            raise Exception("Unexpected general error")

        if self.mock_config.get("raise_client_error", False):
            raise ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "DescribeClusters"
            )

        if self.mock_config.get("cluster_not_found", False):
            return False, {}

        return True, {"clusterName": cluster_name, "status": "ACTIVE"}

    async def get_stopped_tasks(
        self, cluster_name: str, start_time: datetime.datetime
    ) -> List[Dict[str, Any]]:
        """Mock implementation of get_stopped_tasks."""
        if self.mock_config.get("raise_general_error", False):
            raise Exception("Unexpected general error")

        # Return specific list of tasks if provided
        if "stopped_tasks" in self.mock_config:
            return self.mock_config["stopped_tasks"]

        # Default empty response
        return []

    async def get_running_tasks_count(self, cluster_name: str) -> int:
        """Mock implementation of get_running_tasks_count."""
        if self.mock_config.get("raise_general_error", False):
            raise Exception("Unexpected general error")

        # Return specific count if provided
        return self.mock_config.get("running_tasks_count", 0)
