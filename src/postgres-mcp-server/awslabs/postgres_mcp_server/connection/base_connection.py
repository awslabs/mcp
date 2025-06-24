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

"""Abstract base class for database connections."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class DBConnector(ABC):
    """Abstract base class for database connections."""
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to database.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        pass
        
    @abstractmethod
    async def disconnect(self):
        """Disconnect from database."""
        pass
        
    @abstractmethod
    async def execute_query(
        self,
        query: str,
        parameters: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Execute a query against the database.
        
        Args:
            query: SQL query to execute
            parameters: Query parameters
            
        Returns:
            Dict[str, Any]: Query result in standardized format
        """
        pass
        
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if connection is healthy.
        
        Returns:
            bool: True if connection is healthy, False otherwise
        """
        pass
        
    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if connection is active.
        
        Returns:
            bool: True if connection is active, False otherwise
        """
        pass
        
    @property
    @abstractmethod
    def connection_info(self) -> Dict[str, Any]:
        """
        Get connection information.
        
        Returns:
            Dict[str, Any]: Connection information
        """
        pass
        
    @property
    def readonly_query(self) -> bool:
        """
        Get whether this connection is read-only.
        
        Returns:
            bool: True if connection is read-only, False otherwise
        """
        return getattr(self, 'readonly', True)
