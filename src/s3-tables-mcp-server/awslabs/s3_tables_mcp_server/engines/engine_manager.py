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

"""Engine Manager for S3 Tables MCP Server."""

import os
from typing import Dict, Optional

from loguru import logger

from .base_engine import BaseQueryEngine
from .duckdb_engine import DuckDBEngine
from .athena_engine import AthenaEngine
from .emr_engine import EMRServerlessEngine
from ..models import (
    AthenaConfig,
    DuckDBConfig,
    QueryEngine,
    QueryResult,
    SparkConfig,
)


class EngineManager:
    """Manages multiple query engines and selects the best one for each query."""
    
    def __init__(self):
        """Initialize engine manager."""
        self.engines: Dict[QueryEngine, BaseQueryEngine] = {}
        self._initialize_engines()
    
    def _initialize_engines(self):
        """Initialize available engines based on configuration."""
        # Initialize DuckDB (always available)
        try:
            duckdb_config = DuckDBConfig()
            self.engines[QueryEngine.DUCKDB] = DuckDBEngine(duckdb_config)
            logger.info('DuckDB engine initialized')
        except Exception as e:
            logger.warning(f'Failed to initialize DuckDB engine: {str(e)}')
        
        # Initialize Athena if configured
        try:
            athena_config = AthenaConfig()
            self.engines[QueryEngine.ATHENA] = AthenaEngine(athena_config)
            logger.info('Athena engine initialized')
        except Exception as e:
            logger.warning(f'Failed to initialize Athena engine: {str(e)}')
        
        # Initialize EMR Serverless if configured
        if os.getenv('EMR_SERVERLESS_APPLICATION_ID'):
            try:
                spark_config = SparkConfig(application_id=os.getenv('EMR_SERVERLESS_APPLICATION_ID'))
                self.engines[QueryEngine.SPARK] = EMRServerlessEngine(spark_config)
                logger.info('EMR Serverless engine initialized')
            except Exception as e:
                logger.warning(f'Failed to initialize EMR Serverless engine: {str(e)}')
    
    def select_engine(self, sql_query: str, engine_preference: QueryEngine = QueryEngine.AUTO) -> QueryEngine:
        """Select the best engine for the given query."""
        if engine_preference != QueryEngine.AUTO and engine_preference in self.engines:
            return engine_preference
        
        # Simple heuristics for engine selection
        query_upper = sql_query.upper()
        
        # Use DuckDB for simple queries
        if 'JOIN' not in query_upper and 'GROUP BY' not in query_upper and len(sql_query) < 500:
            if QueryEngine.DUCKDB in self.engines:
                return QueryEngine.DUCKDB
        
        # Use Athena for complex analytical queries
        if any(keyword in query_upper for keyword in ['JOIN', 'GROUP BY', 'WINDOW', 'WITH']):
            if QueryEngine.ATHENA in self.engines:
                return QueryEngine.ATHENA
        
        # Default to DuckDB if available, otherwise first available engine
        if QueryEngine.DUCKDB in self.engines:
            return QueryEngine.DUCKDB
        
        return next(iter(self.engines.keys()))
    
    async def execute_query(self, table_arn: str, sql_query: str, engine_preference: QueryEngine = QueryEngine.AUTO, limit: Optional[int] = None) -> QueryResult:
        """Execute query using the selected engine."""
        selected_engine = self.select_engine(sql_query, engine_preference)
        
        if selected_engine not in self.engines:
            return QueryResult(
                status='error',
                message=f'Engine {selected_engine.value} is not available',
                engine_used=selected_engine
            )
        
        engine = self.engines[selected_engine]
        return await engine.execute_query(table_arn, sql_query, limit)
    
    async def test_engines(self) -> Dict[QueryEngine, bool]:
        """Test all available engines."""
        results = {}
        for engine_type, engine in self.engines.items():
            results[engine_type] = await engine.test_connection()
        return results
