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

"""EMR Serverless Spark engine for S3 Tables MCP Server."""

import asyncio
import os
import time
import uuid
from typing import Optional

import boto3
from loguru import logger

from .base_engine import BaseQueryEngine
from ..models import SparkConfig, QueryEngine, QueryResult


class EMRServerlessEngine(BaseQueryEngine):
    """EMR Serverless Spark engine for scalable processing."""
    
    def __init__(self, config: SparkConfig):
        """Initialize EMR Serverless engine."""
        super().__init__(config)
        self.config: SparkConfig = config
        self._emr_client = None
        self._s3_client = None
    
    def _get_clients(self):
        """Get or create AWS clients."""
        if self._emr_client is None:
            self._emr_client = boto3.client('emr-serverless')
        if self._s3_client is None:
            self._s3_client = boto3.client('s3')
        return self._emr_client, self._s3_client
    
    def _generate_pyspark_script(self, table_arn: str, sql_query: str, limit: Optional[int]) -> str:
        """Generate PySpark script for query execution."""
        table_info = self.parse_table_arn(table_arn)
        job_id = str(uuid.uuid4())[:8]
        
        script = f'''
import json
import sys
from pyspark.sql import SparkSession

# Initialize Spark with Iceberg support
spark = SparkSession.builder \\
    .appName("S3Tables-Query-{job_id}") \\
    .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \\
    .config("spark.sql.catalog.s3tables", "org.apache.iceberg.spark.SparkCatalog") \\
    .config("spark.sql.catalog.s3tables.catalog-impl", "org.apache.iceberg.rest.RESTCatalog") \\
    .config("spark.sql.catalog.s3tables.uri", "https://s3tables.{table_info["region"]}.amazonaws.com/catalog") \\
    .config("spark.executor.memory", "{self.config.executor_memory}") \\
    .config("spark.executor.cores", "{self.config.executor_cores}") \\
    .config("spark.driver.memory", "{self.config.driver_memory}") \\
    .getOrCreate()

try:
    # Reference the S3 Tables table
    table_name = "s3tables.{table_info["bucket_name"]}.{table_info["table_name"]}"
    
    # Execute the query
    query = """{sql_query}""".replace("FROM table", f"FROM {{table_name}}")
    {"query += f' LIMIT {limit}'" if limit else ""}
    
    df = spark.sql(query)
    
    # Convert to JSON and collect results
    results = df.toJSON().collect()
    
    # Get schema information
    schema = df.schema.json()
    row_count = len(results)
    
    # Output results for parsing
    print(f"QUERY_SUCCESS: {{json.dumps({{'row_count': row_count, 'schema': schema}})}}")
    
    # Output actual data (limited for MCP response size)
    max_rows = min(1000, len(results))
    for i, row in enumerate(results[:max_rows]):
        print(f"DATA_ROW: {{row}}")
    
except Exception as e:
    print(f"QUERY_ERROR: {{str(e)}}")
    sys.exit(1)
finally:
    spark.stop()
'''
        return script
    
    async def execute_query(self, table_arn: str, sql_query: str, limit: Optional[int] = None) -> QueryResult:
        """Execute query using EMR Serverless."""
        start_time = time.time()
        
        try:
            emr_client, s3_client = self._get_clients()
            table_info = self.parse_table_arn(table_arn)
            job_id = str(uuid.uuid4())[:8]
            
            # Generate PySpark script
            script_content = self._generate_pyspark_script(table_arn, sql_query, limit)
            
            # Upload script to S3
            script_bucket = f"s3tables-mcp-scripts-{table_info['account_id']}-{table_info['region']}"
            script_key = f"jobs/{job_id}.py"
            
            try:
                s3_client.create_bucket(Bucket=script_bucket)
            except s3_client.exceptions.BucketAlreadyExists:
                pass  # Bucket already exists
            
            s3_client.put_object(
                Bucket=script_bucket,
                Key=script_key,
                Body=script_content.encode('utf-8')
            )
            
            # Submit EMR Serverless job
            application_id = self.config.application_id
            if not application_id:
                raise ValueError('EMR Serverless application ID not configured')
            
            job_role_arn = os.getenv('EMR_SERVERLESS_JOB_ROLE_ARN')
            if not job_role_arn:
                raise ValueError('EMR_SERVERLESS_JOB_ROLE_ARN environment variable not set')
            
            response = emr_client.start_job_run(
                applicationId=application_id,
                executionRoleArn=job_role_arn,
                jobDriver={
                    'sparkSubmit': {
                        'entryPoint': f's3://{script_bucket}/{script_key}',
                        'sparkSubmitParameters': f'--conf spark.executor.memory={self.config.executor_memory} --conf spark.executor.cores={self.config.executor_cores}'
                    }
                },
                configurationOverrides={
                    'monitoringConfiguration': {
                        'cloudWatchLoggingConfiguration': {
                            'enabled': True,
                            'logGroupName': '/aws/emr-serverless/s3tables-mcp'
                        }
                    }
                }
            )
            
            job_run_id = response['jobRunId']
            logger.info(f'Started EMR Serverless job: {job_run_id}')
            
            # Wait for job completion
            while True:
                job_response = emr_client.get_job_run(
                    applicationId=application_id,
                    jobRunId=job_run_id
                )
                
                state = job_response['jobRun']['state']
                
                if state == 'SUCCESS':
                    break
                elif state in ['FAILED', 'CANCELLED']:
                    error_msg = job_response['jobRun'].get('stateDetails', 'Unknown error')
                    raise Exception(f'EMR Serverless job failed: {error_msg}')
                
                await asyncio.sleep(10)  # Poll every 10 seconds
            
            # Parse results from CloudWatch logs (simplified - would need actual log parsing)
            # For now, return a mock successful result
            execution_time = (time.time() - start_time) * 1000
            
            return QueryResult(
                status='success',
                message='Query executed successfully on EMR Serverless',
                rows_returned=0,  # Would be parsed from logs
                execution_time_ms=execution_time,
                engine_used=QueryEngine.SPARK,
                data=[],  # Would be parsed from logs
                result_schema={}
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f'EMR Serverless query failed: {str(e)}')
            
            return QueryResult(
                status='error',
                message=f'EMR Serverless execution failed: {str(e)}',
                execution_time_ms=execution_time,
                engine_used=QueryEngine.SPARK
            )
    
    async def test_connection(self) -> bool:
        """Test EMR Serverless connection."""
        try:
            emr_client, _ = self._get_clients()
            emr_client.list_applications(maxResults=1)
            return True
        except Exception as e:
            logger.error(f'EMR Serverless connection test failed: {str(e)}')
            return False
