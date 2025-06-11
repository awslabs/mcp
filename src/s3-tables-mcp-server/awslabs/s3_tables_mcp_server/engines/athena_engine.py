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

"""Amazon Athena query engine for S3 Tables MCP Server."""

import asyncio
import os
import time
import uuid
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from loguru import logger

from .base_engine import BaseQueryEngine
from ..models import AthenaConfig, QueryEngine, QueryResult
from ..analytics_integration import get_analytics_manager


class AthenaEngine(BaseQueryEngine):
    """Amazon Athena query engine for serverless SQL."""
    
    def __init__(self, config: AthenaConfig):
        """Initialize Athena engine."""
        super().__init__(config)
        self.config: AthenaConfig = config
        self._client = None
        self._s3_client = None
        self._analytics_manager = None
        self._result_location_configured = False
    
    def _get_client(self):
        """Get or create Athena client."""
        if self._client is None:
            region = os.getenv('AWS_REGION', 'us-west-2')
            self._client = boto3.client('athena', region_name=region)
        return self._client
    
    def _get_s3_client(self):
        """Get or create S3 client."""
        if self._s3_client is None:
            region = os.getenv('AWS_REGION', 'us-west-2')
            self._s3_client = boto3.client('s3', region_name=region)
        return self._s3_client
    
    def _get_analytics_manager(self):
        """Get or create analytics integration manager."""
        if self._analytics_manager is None:
            region = os.getenv('AWS_REGION', 'us-west-2')
            self._analytics_manager = get_analytics_manager(region)
        return self._analytics_manager
    
    async def _ensure_result_location(self, account_id: str, region: str) -> str:
        """Ensure Athena query result location is configured and accessible."""
        if self._result_location_configured and self.config.result_location:
            return self.config.result_location
        
        try:
            # Default result bucket name
            result_bucket_name = f"aws-athena-query-results-{account_id}-{region}"
            result_location = f"s3://{result_bucket_name}/"
            
            # Check if the bucket exists, create if not
            s3_client = self._get_s3_client()
            
            try:
                s3_client.head_bucket(Bucket=result_bucket_name)
                logger.info(f"✅ Athena result bucket {result_bucket_name} already exists")
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == '404':
                    # Bucket doesn't exist, create it
                    logger.info(f"🔧 Creating Athena result bucket: {result_bucket_name}")
                    
                    # Create bucket with appropriate region configuration
                    create_params = {'Bucket': result_bucket_name}
                    if region != 'us-east-1':
                        create_params['CreateBucketConfiguration'] = {'LocationConstraint': region}
                    
                    s3_client.create_bucket(**create_params)
                    
                    # Enable versioning for better management
                    s3_client.put_bucket_versioning(
                        Bucket=result_bucket_name,
                        VersioningConfiguration={'Status': 'Enabled'}
                    )
                    
                    # Set lifecycle policy to clean up old query results
                    lifecycle_config = {
                        'Rules': [
                            {
                                'ID': 'DeleteOldQueryResults',
                                'Status': 'Enabled',
                                'Filter': {'Prefix': ''},
                                'Expiration': {'Days': 30},
                                'NoncurrentVersionExpiration': {'NoncurrentDays': 7}
                            }
                        ]
                    }
                    
                    try:
                        s3_client.put_bucket_lifecycle_configuration(
                            Bucket=result_bucket_name,
                            LifecycleConfiguration=lifecycle_config
                        )
                        logger.info(f"✅ Applied lifecycle policy to {result_bucket_name}")
                    except Exception as lc_error:
                        logger.warning(f"⚠️  Could not apply lifecycle policy: {str(lc_error)}")
                    
                    logger.info(f"✅ Created Athena result bucket: {result_bucket_name}")
                else:
                    logger.warning(f"⚠️  Cannot access result bucket {result_bucket_name}: {str(e)}")
            
            # Configure workgroup to use this result location
            await self._configure_workgroup_result_location(result_location)
            
            self._result_location_configured = True
            self.config.result_location = result_location
            
            return result_location
            
        except Exception as e:
            logger.error(f"Failed to ensure Athena result location: {str(e)}")
            # Return a default location even if we can't create the bucket
            return f"s3://aws-athena-query-results-{account_id}-{region}/"
    
    async def _configure_workgroup_result_location(self, result_location: str):
        """Configure the Athena workgroup with the result location."""
        try:
            client = self._get_client()
            workgroup_name = self.config.workgroup
            
            # Get current workgroup configuration
            try:
                response = client.get_work_group(WorkGroup=workgroup_name)
                workgroup_config = response.get('WorkGroup', {}).get('Configuration', {})
                result_config = workgroup_config.get('ResultConfiguration', {})
                
                current_location = result_config.get('OutputLocation')
                
                if current_location == result_location:
                    logger.info(f"✅ Workgroup {workgroup_name} already configured with correct result location")
                    return
                
                # Update workgroup configuration
                update_params = {
                    'WorkGroup': workgroup_name,
                    'ConfigurationUpdates': {
                        'ResultConfigurationUpdates': {
                            'OutputLocation': result_location
                        }
                    }
                }
                
                client.update_work_group(**update_params)
                logger.info(f"✅ Updated workgroup {workgroup_name} with result location: {result_location}")
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'InvalidRequestException':
                    logger.warning(f"⚠️  Workgroup {workgroup_name} may not exist, will use query-level result configuration")
                else:
                    logger.warning(f"⚠️  Could not configure workgroup {workgroup_name}: {str(e)}")
                    
        except Exception as e:
            logger.warning(f"⚠️  Failed to configure workgroup result location: {str(e)}")
    
    async def _ensure_analytics_integration(self, table_bucket_arn: str) -> bool:
        """Ensure analytics integration is configured for the table bucket."""
        try:
            analytics_manager = self._get_analytics_manager()
            status = await analytics_manager.ensure_analytics_integration(table_bucket_arn)
            
            if not status.glue_catalog_configured:
                logger.warning(f"Glue catalog not properly configured for {table_bucket_arn}")
                return False
            
            if not status.athena_workgroup_configured:
                logger.warning(f"Athena workgroup not properly configured for {table_bucket_arn}")
                return False
            
            if status.error_message:
                logger.error(f"Analytics integration error for {table_bucket_arn}: {status.error_message}")
                return False
            
            logger.info(f"Analytics integration verified for {table_bucket_arn}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to ensure analytics integration for {table_bucket_arn}: {str(e)}")
            return False
    
    async def execute_query(self, table_arn: str, sql_query: str, limit: Optional[int] = None) -> QueryResult:
        """Execute query using Athena with official AWS S3 Tables integration patterns."""
        start_time = time.time()
        
        try:
            client = self._get_client()
            table_info = self.parse_table_arn(table_arn)
            
            # Construct table bucket ARN from table ARN
            table_bucket_arn = f"arn:aws:s3tables:{table_info['region']}:{table_info['account_id']}:bucket/{table_info['bucket_name']}"
            
            # Ensure result location is configured FIRST (this fixes the main issue)
            logger.info(f"🔧 Ensuring Athena result location is configured...")
            result_location = await self._ensure_result_location(table_info['account_id'], table_info['region'])
            logger.info(f"✅ Using Athena result location: {result_location}")
            
            # Ensure analytics integration is configured
            logger.info(f"Ensuring analytics integration for table bucket: {table_bucket_arn}")
            integration_success = await self._ensure_analytics_integration(table_bucket_arn)
            
            if not integration_success:
                logger.warning(f"Analytics integration may not be fully configured for {table_bucket_arn}, but proceeding with query")
            
            # Get table information directly using the table ARN
            s3tables_client = boto3.client('s3tables', region_name=table_info['region'])
            
            # Find table details by listing tables since get_table requires namespace and name
            # We only have the table ARN which contains the table ID, not namespace/name
            tables_response = s3tables_client.list_tables(tableBucketARN=table_bucket_arn)
            
            target_table = None
            table_id = table_info['table_name']  # This is actually the table ID from ARN
            
            for table in tables_response.get('tables', []):
                # Extract table ID from table ARN for comparison
                table_id_from_arn = table['tableARN'].split('/')[-1]
                if table_id_from_arn == table_id:
                    target_table = table
                    break
            
            if not target_table:
                raise ValueError(f"Table with ID {table_id} not found in bucket {table_info['bucket_name']}")
            
            actual_table_name = target_table['name']
            
            # FIX: Handle namespace properly - it could be a string or list
            namespace_raw = target_table['namespace']
            if isinstance(namespace_raw, list):
                namespace = namespace_raw[0] if namespace_raw else 'default'
            else:
                namespace = namespace_raw if namespace_raw else 'default'
            
            logger.info(f"Found table via listing - namespace: {namespace}, name: {actual_table_name}")
            
            # Now get detailed table information using the correct parameters
            try:
                table_response = s3tables_client.get_table(
                    tableBucketARN=table_bucket_arn,
                    namespace=namespace,
                    name=actual_table_name
                )
                logger.info(f"Retrieved detailed table info for {namespace}.{actual_table_name}")
            except Exception as e:
                logger.warning(f"Failed to get detailed table info: {str(e)}, proceeding with basic info")
            
            # OFFICIAL AWS S3 TABLES + ATHENA INTEGRATION PATTERN
            # From AWS docs: --query-execution-context '{"Catalog": "s3tablescatalog/bucket-name", "Database":"namespace"}'
            bucket_name = table_info['bucket_name']
            
            # Official AWS format: s3tablescatalog/bucket-name (with forward slash)
            catalog_name = f"s3tablescatalog/{bucket_name}"
            
            # Official AWS table reference format from the documentation
            # Example: "s3tablescatalog/amzn-s3-demo-bucket".test_namespace.daily_sales
            athena_table_name = f'"{catalog_name}".{namespace}.{actual_table_name}'
            
            logger.info(f"Using official AWS S3 Tables catalog reference: {athena_table_name}")
            logger.info(f"Catalog context: {catalog_name}")
            logger.info(f"Database context: {namespace}")
            
            # Replace table reference in query
            modified_query = sql_query.replace('FROM table', f'FROM {athena_table_name}')
            
            # Add limit only if not already present in the query
            if limit and 'LIMIT' not in modified_query.upper():
                modified_query += f' LIMIT {limit}'
            
            logger.info(f"Executing Athena query: {modified_query}")
            
            # Start query execution
            execution_id = str(uuid.uuid4())
            
            # FINAL FIX: Use BOTH Catalog AND Database in QueryExecutionContext (from AWS docs!)
            # Example from AWS docs: '{"Catalog": "s3tablescatalog/amzn-s3-demo-bucket", "Database":"test_namespace"}'
            query_params = {
                'QueryString': modified_query,
                'QueryExecutionContext': {
                    'Catalog': catalog_name,    # s3tablescatalog/bucket-name
                    'Database': namespace       # The namespace as database (from AWS docs!)
                },
                'ResultConfiguration': {
                    'OutputLocation': result_location
                },
                'WorkGroup': self.config.workgroup,
                'ClientRequestToken': execution_id
            }
            
            logger.info(f"Query execution context: Catalog={catalog_name}, Database={namespace}")
            
            response = client.start_query_execution(**query_params)
            
            query_execution_id = response['QueryExecutionId']
            logger.info(f"Athena query started with execution ID: {query_execution_id}")
            
            # Wait for query completion
            while True:
                result = client.get_query_execution(QueryExecutionId=query_execution_id)
                status = result['QueryExecution']['Status']['State']
                
                if status in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                    break
                
                await asyncio.sleep(1)
            
            if status != 'SUCCEEDED':
                # Get detailed error information
                query_status = result['QueryExecution']['Status']
                error_msg = query_status.get('StateChangeReason', 'Unknown error')
                athena_error = query_status.get('AthenaError', {})
                
                # Build comprehensive error message
                error_parts = [f'Athena query failed with status: {status}']
                
                if error_msg and error_msg != 'Unknown error':
                    error_parts.append(f'Reason: {error_msg}')
                
                if athena_error:
                    if 'ErrorCategory' in athena_error:
                        error_parts.append(f'Category: {athena_error["ErrorCategory"]}')
                    if 'ErrorType' in athena_error:
                        error_parts.append(f'Type: {athena_error["ErrorType"]}')
                    if 'Retryable' in athena_error:
                        error_parts.append(f'Retryable: {athena_error["Retryable"]}')
                
                # Log the full query execution result for debugging
                logger.error(f"Full Athena query execution result: {result}")
                
                error_details = '. '.join(error_parts)
                
                # Add specific suggestions based on error patterns (updated with correct formats)
                error_lower = error_msg.lower()
                if 'catalog' in error_lower and 'does not exist' in error_lower:
                    error_details += f'\n\n🔧 SETUP REQUIRED: S3 Tables bucket is not registered with Glue Data Catalog.\n'
                    error_details += f'📖 Ensure analytics integration is enabled for bucket: {table_bucket_arn}\n'
                    error_details += f'⚡ Lake Formation permissions required (AWS CLI format):\n'
                    error_details += f'   aws lakeformation grant-permissions \\\n'
                    error_details += f'   --cli-input-json \'{{"Principal": {{"DataLakePrincipalIdentifier": "USER_ARN"}}, "Resource": {{"Catalog": {{"Id": "{table_info["account_id"]}:{catalog_name}"}}}}, "Permissions": ["ALL"]}}\''
                elif 'database' in error_lower and 'does not exist' in error_lower:
                    error_details += f'. SUGGESTION: Database "{namespace}" does not exist in catalog "{catalog_name}". You may need to create it first with: CREATE DATABASE `{namespace}`'
                elif 'does not exist' in error_lower or 'table not found' in error_lower:
                    error_details += f'. SUGGESTION: Table exists in S3 Tables but not visible in Glue catalog "{catalog_name}". Enable analytics integration.'
                elif 'access denied' in error_lower or 'permission' in error_lower:
                    error_details += f'. SUGGESTION: Grant Lake Formation permissions on catalog "{catalog_name}" and database "{namespace}".'
                elif 'workgroup' in error_lower:
                    error_details += '. SUGGESTION: Check Athena workgroup configuration and result location.'
                elif 'syntax' in error_lower or 'parse' in error_lower:
                    error_details += f'. SUGGESTION: Check SQL syntax. Query was: {modified_query}'
                elif 'query result location' in error_lower or 'output location' in error_lower:
                    error_details += f'. RESULT LOCATION: Auto-configured to {result_location}. Check S3 bucket permissions.'
                
                raise Exception(error_details)
            
            # Get query results
            results = client.get_query_results(QueryExecutionId=query_execution_id)
            
            # Parse results
            rows = results['ResultSet']['Rows']
            if not rows:
                data = []
                columns = []
            else:
                # First row contains column names
                columns = [col['VarCharValue'] for col in rows[0]['Data']]
                
                # Convert remaining rows to dictionaries
                data = []
                for row in rows[1:]:
                    row_data = {}
                    for i, col in enumerate(columns):
                        value = row['Data'][i].get('VarCharValue', '')
                        row_data[col] = value
                    data.append(row_data)
            
            execution_time = (time.time() - start_time) * 1000
            
            logger.info(f"Athena query completed successfully. Returned {len(data)} rows in {execution_time:.2f}ms")
            
            return QueryResult(
                status='success',
                rows_returned=len(data),
                execution_time_ms=execution_time,
                engine_used=QueryEngine.ATHENA,
                data=data,
                result_schema={'columns': columns}
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f'Athena query failed: {str(e)}')
            
            return QueryResult(
                status='error',
                message=f'Athena execution failed: {str(e)}',
                execution_time_ms=execution_time,
                engine_used=QueryEngine.ATHENA
            )
    
    async def test_connection(self) -> bool:
        """Test Athena connection."""
        try:
            client = self._get_client()
            client.list_work_groups(MaxResults=1)
            return True
        except Exception as e:
            logger.error(f'Athena connection test failed: {str(e)}')
            return False
