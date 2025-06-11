# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""Base query engine for S3 Tables MCP Server."""

from abc import ABC, abstractmethod
from typing import Dict, Optional

from ..models import EngineConfig, QueryResult


class BaseQueryEngine(ABC):
    """Base class for query engines."""
    
    def __init__(self, config: EngineConfig):
        """Initialize the engine with configuration."""
        self.config = config
        self.engine_type = config.engine_type
    
    @abstractmethod
    async def execute_query(self, table_arn: str, sql_query: str, limit: Optional[int] = None) -> QueryResult:
        """Execute a SQL query against the specified table."""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if the engine is available and properly configured."""
        pass
    
    def parse_table_arn(self, table_arn: str) -> Dict[str, str]:
        """Parse table ARN to extract components."""
        # Expected format: arn:aws:s3tables:region:account:bucket/bucket-name/table/table-name
        # Note: namespace is NOT part of the ARN, it's passed separately to API calls
        parts = table_arn.split(':')
        if len(parts) < 6:
            raise ValueError(f'Invalid table ARN format: {table_arn}')
        
        region = parts[3]
        account_id = parts[4]
        resource_parts = parts[5].split('/')
        
        # Should be exactly 4 parts: bucket/bucket-name/table/table-name
        if len(resource_parts) != 4 or resource_parts[0] != 'bucket' or resource_parts[2] != 'table':
            raise ValueError(f'Invalid table ARN resource format: {table_arn}. Expected: bucket/bucket-name/table/table-name')
        
        bucket_name = resource_parts[1]
        table_name = resource_parts[3]
        
        return {
            'region': region,
            'account_id': account_id,
            'bucket_name': bucket_name,
            'table_name': table_name
        }
