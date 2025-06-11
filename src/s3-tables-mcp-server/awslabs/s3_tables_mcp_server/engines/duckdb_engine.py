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

"""DuckDB query engine for S3 Tables MCP Server."""

import re
import time
from typing import Optional

import boto3
from loguru import logger

from .base_engine import BaseQueryEngine
from ..models import DuckDBConfig, QueryEngine, QueryResult


class DuckDBEngine(BaseQueryEngine):
    """DuckDB query engine for fast local queries with native S3 Tables support."""
    
    def __init__(self, config: DuckDBConfig):
        """Initialize DuckDB engine."""
        super().__init__(config)
        self.config: DuckDBConfig = config
        self._connection = None
        self._s3_tables_attached = {}  # Track attached S3 Tables databases
    
    async def _get_connection(self):
        """Get or create DuckDB connection."""
        if self._connection is None:
            try:
                import duckdb
                
                # Create connection with configuration
                self._connection = duckdb.connect()
                
                # Configure DuckDB
                self._connection.execute(f"SET memory_limit='{self.config.memory_limit}'")
                self._connection.execute(f"SET threads={self.config.threads}")
                
                # Set home directory to avoid "Can't find the home directory" error
                import os
                home_dir = os.path.expanduser("~")
                self._connection.execute(f"SET home_directory='{home_dir}'")
                # https://github.com/duckdb/duckdb/issues/12837
                self._connection.execute(f"SET secret_directory='{home_dir}/duckdb/secrets'")
                self._connection.execute(f"SET extension_directory='{home_dir}/duckdb/extensions'")
                
                # Install and load AWS extension for S3 Tables support
                self._connection.execute("INSTALL aws")
                self._connection.execute("INSTALL httpfs")
                self._connection.execute("INSTALL iceberg")
                self._connection.execute("LOAD aws")
                self._connection.execute("LOAD httpfs")
                self._connection.execute("LOAD iceberg")
                
                # Configure S3 credentials using boto3 session (default approach)
                try:
                    session = boto3.Session()
                    credentials = session.get_credentials()
                    
                    if credentials:
                        self._connection.execute(f"""
                            CREATE SECRET (
                                TYPE s3,
                                KEY_ID '{credentials.access_key}',
                                SECRET '{credentials.secret_key}'
                                {f", SESSION_TOKEN '{credentials.token}'" if credentials.token else ""}
                            );
                        """)
                        logger.info('DuckDB S3 credentials configured from boto3 session (default)')
                    else:
                        logger.error('No AWS credentials available from boto3 session')
                        raise RuntimeError('No AWS credentials available from boto3 session')
                except Exception as e:
                    logger.warning(f'Failed to create DuckDB S3 secret with boto3 session: {e}')
                    
                    # Fallback to credential_chain approach
                    try:
                        self._connection.execute("""
                            CREATE SECRET (
                                TYPE s3,
                                PROVIDER credential_chain
                            );
                        """)
                        logger.info('DuckDB S3 secret created using credential_chain (fallback)')
                    except Exception as e2:
                        logger.error(f'Failed to create DuckDB S3 secret with credential_chain: {e2}')
                        raise RuntimeError('Unable to configure AWS credentials for DuckDB S3 Tables access')
                
                logger.info('DuckDB connection initialized successfully')
                
            except ImportError:
                raise RuntimeError('DuckDB is not installed. Please install with: pip install duckdb')
            except Exception as e:
                logger.error(f'Failed to initialize DuckDB: {str(e)}')
                raise
        
        return self._connection
    
    async def _attach_s3_tables_database(self, table_bucket_arn: str, db_name: str):
        """Attach S3 Tables database to DuckDB if not already attached."""
        conn = await self._get_connection()
        
        if table_bucket_arn not in self._s3_tables_attached:
            try:
                # Attach the S3 Tables bucket as a database
                # This follows the official DuckDB S3 Tables documentation pattern
                attach_sql = f"""
                    ATTACH '{table_bucket_arn}'
                    AS {db_name} (
                        TYPE iceberg,
                        ENDPOINT_TYPE s3_tables
                    );
                """
                conn.execute(attach_sql)
                self._s3_tables_attached[table_bucket_arn] = db_name
                logger.info(f'Attached S3 Tables database: {table_bucket_arn} as {db_name}')
            except Exception as e:
                logger.error(f'Failed to attach S3 Tables database: {e}')
                raise
    
    async def execute_query(self, table_arn: str, sql_query: str, limit: Optional[int] = None) -> QueryResult:
        """Execute query using DuckDB with native S3 Tables support."""
        start_time = time.time()
        
        try:
            conn = await self._get_connection()
            table_info = self.parse_table_arn(table_arn)
            
            # Get table information first to obtain namespace and actual table name
            s3tables_client = boto3.client('s3tables', region_name=table_info['region'])
            
            # Construct table bucket ARN for listing tables
            table_bucket_arn = f"arn:aws:s3tables:{table_info['region']}:{table_info['account_id']}:bucket/{table_info['bucket_name']}"
            
            # List tables to find the one matching our table ARN
            # The table ARN might contain a UUID, but we need the actual table name for AWS APIs
            tables_response = s3tables_client.list_tables(tableBucketARN=table_bucket_arn)
            
            target_table = None
            table_identifier = table_info['table_name']  # This could be UUID or actual name
            
            for table in tables_response.get('tables', []):
                # First try matching by table ARN (this handles UUID case)
                if table_arn == table.get('tableARN'):
                    target_table = table
                    break
                # Fallback: match by table name (this handles direct name case)
                elif table['name'] == table_identifier:
                    target_table = table
                    break
            
            if not target_table:
                # If still not found, log available tables for debugging
                available_tables = [(t.get('name', 'unknown'), t.get('tableARN', 'unknown')) for t in tables_response.get('tables', [])]
                logger.error(f"Table with ARN {table_arn} not found in bucket {table_info['bucket_name']}. Available tables: {available_tables}")
                raise ValueError(f"Table with ARN {table_arn} not found in bucket {table_info['bucket_name']}")
            
            namespace_list = target_table['namespace']
            namespace = namespace_list[0] if namespace_list else 'default'
            actual_table_name = target_table['name']
            
            logger.info(f'Retrieved table info - namespace: {namespace}, name: {actual_table_name}')
            
            # KEY FIX: Use table bucket ARN for attachment, not individual table ARN
            # This is the critical learning - attach to the bucket, then reference tables by name
            # Create a unique database name for this S3 Tables bucket
            db_name = f"s3tables_{table_info['bucket_name'].replace('-', '_')}"
            
            # Attach S3 Tables database using the table bucket ARN (not individual table ARN)
            await self._attach_s3_tables_database(table_bucket_arn, db_name)
            
            # Build the fully qualified table reference using attached database
            # Format: db_name.namespace.table_name
            s3_tables_ref = f"{db_name}.{namespace}.{actual_table_name}"
            
            # Process the SQL query to use the attached database reference
            modified_query = sql_query
            
            # Replace "FROM table" with our S3 Tables reference
            modified_query = re.sub(r'\bFROM\s+table\b', f'FROM {s3_tables_ref}', modified_query, flags=re.IGNORECASE)
            
            # Replace "FROM <actual_table_name>" with our S3 Tables reference  
            modified_query = re.sub(
                rf'\bFROM\s+{re.escape(actual_table_name)}\b', 
                f'FROM {s3_tables_ref}', 
                modified_query, 
                flags=re.IGNORECASE
            )
            
            # If query doesn't have FROM clause, add it (for simple SELECT queries)
            if 'FROM' not in modified_query.upper():
                if modified_query.strip().upper().startswith('SELECT'):
                    modified_query += f' FROM {s3_tables_ref}'
                else:
                    # Default to SELECT * if not a SELECT query
                    modified_query = f'SELECT * FROM {s3_tables_ref}'
            
            # Apply limit if specified and not already present
            if limit and 'LIMIT' not in modified_query.upper():
                modified_query += f' LIMIT {limit}'
            
            logger.info(f'Executing DuckDB query: {modified_query}')
            
            # Execute the query
            result = conn.execute(modified_query).fetchall()
            columns = [desc[0] for desc in conn.description]
            
            # Convert results to list of dictionaries
            data = [dict(zip(columns, row)) for row in result]
            
            execution_time = (time.time() - start_time) * 1000
            
            return QueryResult(
                status='success',
                rows_returned=len(data),
                execution_time_ms=execution_time,
                engine_used=QueryEngine.DUCKDB,
                data=data,
                result_schema={'columns': columns}
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.exception(e)
            logger.error(f'DuckDB query failed: {str(e)}', stack_info=True, exc_info=True)
            
            return QueryResult(
                status='error',
                message=f'DuckDB execution failed: {str(e)}',
                execution_time_ms=execution_time,
                engine_used=QueryEngine.DUCKDB
            )
    
    async def test_connection(self) -> bool:
        """Test DuckDB connection."""
        try:
            conn = await self._get_connection()
            conn.execute("SELECT 1").fetchone()
            return True
        except Exception as e:
            logger.error(f'DuckDB connection test failed: {str(e)}')
            return False
