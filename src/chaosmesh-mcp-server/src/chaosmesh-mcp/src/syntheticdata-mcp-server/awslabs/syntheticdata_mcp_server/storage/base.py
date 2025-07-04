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


"""Base classes for data storage targets."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class DataTarget(ABC):
    """Abstract base class for data storage targets."""

    @abstractmethod
    async def load(self, data: Dict[str, List[Dict]], config: Dict[str, Any]) -> Dict:
        """Load data to the target storage.

        Args:
            data: Dictionary mapping table names to lists of records
            config: Target-specific configuration

        Returns:
            Dictionary containing load results
        """
        pass

    @abstractmethod
    async def validate(self, data: Dict[str, List[Dict]], config: Dict[str, Any]) -> bool:
        """Validate data and configuration before loading.

        Args:
            data: Dictionary mapping table names to lists of records
            config: Target-specific configuration

        Returns:
            True if validation passes, False otherwise
        """
        pass
