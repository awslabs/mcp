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

"""Context management for Amazon RDS Control Plane MCP Server."""

from mypy_boto3_rds.type_defs import PaginatorConfigTypeDef


class Context:
    """Context class for RDS Control Plane MCP Server."""

    _readonly = True
    _max_items = 100

    @classmethod
    def initialize(cls, readonly: bool = True, max_items: int = 100):
        """Initialize the context.

        Args:
            readonly (bool): Whether to run in readonly mode. Defaults to True.
            max_items (int): Maximum number of items returned from API responses. Defaults to 100.
        """
        cls._readonly = readonly
        cls._max_items = max_items

    @classmethod
    def readonly_mode(cls) -> bool:
        """Check if the server is running in readonly mode.

        Returns:
            True if readonly mode is enabled, False otherwise
        """
        return cls._readonly

    @classmethod
    def max_items(cls) -> int:
        """Get the maximum number of items returned from API responses.

        Returns:
            The maximum number of items returned from API responses
        """
        return cls._max_items

    @classmethod
    def get_pagination_config(cls) -> PaginatorConfigTypeDef:
        """Get the pagination config needed for API responses.

        Returns:
            The pagination config needed for API responses
        """
        return {
            'MaxItems': cls._max_items,
            'PageSize': 20,
        }
