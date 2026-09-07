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

"""Abstract database connection interface for postgres MCP Server."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class AbstractDBConnection(ABC):
    """Abstract base class for database connections."""

    def __init__(self, readonly: bool):
        """Initialize the database connection.

        Args:
            readonly: Whether the connection should be read-only
        """
        self._readonly = readonly
        # Diagnostic only: whether the connected role is over-privileged
        # (superuser, a member of rds_superuser, or carrying BYPASSRLS), as
        # determined by the post-connect privilege probe in
        # server.validate_connection.
        #   None  -> not determined (privilege_check=off, or the probe could
        #            not be performed / has not run for this connection)
        #   True  -> connected role is over-privileged
        #   False -> connected role is confirmed not over-privileged
        # This is for observability (surfaced in connection-map diagnostics)
        # and must never be used to make a security decision — that logic
        # lives in server.validate_connection.
        self._effective_is_over_privileged: Optional[bool] = None

    @property
    def readonly_query(self) -> bool:
        """Get whether this connection is read-only.

        Returns:
            bool: True if the connection is read-only, False otherwise
        """
        return self._readonly

    @property
    def effective_is_over_privileged(self) -> Optional[bool]:
        """Diagnostic flag: is the connected role over-privileged?

        Over-privileged means superuser, rds_superuser member, or BYPASSRLS.

        Returns:
            Optional[bool]: True/False once the privilege probe has run,
            or None if it was not determined (e.g. privilege_check=off).
        """
        return self._effective_is_over_privileged

    @effective_is_over_privileged.setter
    def effective_is_over_privileged(self, value: Optional[bool]) -> None:
        """Record the privilege-probe result (diagnostic use only)."""
        self._effective_is_over_privileged = value

    @abstractmethod
    async def execute_query(
        self, sql: str, parameters: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Execute a SQL query.

        Args:
            sql: The SQL query to execute
            parameters: Optional parameters for the query

        Returns:
            Dict containing query results with column metadata and records
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the database connection."""
        pass

    @abstractmethod
    async def check_connection_health(self) -> bool:
        """Check if the database connection is healthy.

        Returns:
            bool: True if the connection is healthy, False otherwise
        """
        pass
