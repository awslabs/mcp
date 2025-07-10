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

"""CrawlerHandler for Data Processing MCP Server."""

from awslabs.aws_dataprocessing_mcp_server.models.glue_models import (
    BatchGetCrawlersResponse,
    CreateClassifierResponse,
    CreateCrawlerResponse,
    DeleteClassifierResponse,
    DeleteCrawlerResponse,
    GetClassifierResponse,
    GetClassifiersResponse,
    GetCrawlerMetricsResponse,
    GetCrawlerResponse,
    GetCrawlersResponse,
    ListCrawlersResponse,
    StartCrawlerResponse,
    StartCrawlerScheduleResponse,
    StopCrawlerResponse,
    StopCrawlerScheduleResponse,
    UpdateClassifierResponse,
    UpdateCrawlerResponse,
    UpdateCrawlerScheduleResponse,
)
from awslabs.aws_dataprocessing_mcp_server.utils.aws_helper import AwsHelper
from awslabs.aws_dataprocessing_mcp_server.utils.logging_helper import (
    LogLevel,
    log_with_request_id,
)
from botocore.exceptions import ClientError
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from pydantic import Field
from typing import Any, Dict, List, Optional, Union


class CrawlerHandler:
    """Handler for Amazon Glue Crawler operations."""

    def __init__(self, mcp, allow_write: bool = False, allow_sensitive_data_access: bool = False):
        """Initialize the Glue Crawler handler.

        Args:
            mcp: The MCP server instance
            allow_write: Whether to enable write access (default: False)
            allow_sensitive_data_access: Whether to allow access to sensitive data (default: False)
        """
        self.mcp = mcp
        self.allow_write = allow_write
        self.allow_sensitive_data_access = allow_sensitive_data_access
        self.glue_client = AwsHelper.create_boto3_client('glue')

        # Register tools
        self.mcp.tool(name='manage_aws_glue_crawlers')(self.manage_aws_glue_crawlers)
        self.mcp.tool(name='manage_aws_glue_classifiers')(self.manage_aws_glue_classifiers)
        self.mcp.tool(name='manage_aws_glue_crawler_management')(
            self.manage_aws_glue_crawler_management
        )

    async def manage_aws_glue_crawlers(
        self,
        ctx: Context,
        operation: str = Field(
            ...,
            description='Operation to perform: create-crawler, delete-crawler, get-crawler, get-crawlers, start-crawler, stop-crawler, batch-get-crawlers, list-crawlers, update-crawler. Choose "get-crawler", "get-crawlers", "batch-get-crawlers", or "list-crawlers" for read-only operations when write access is disabled.',
        ),
        crawler_name: Optional[str] = Field(
            None,
            description='Name of the crawler (required for all operations except get-crawlers, batch-get-crawlers, and list-crawlers).',
        ),
        crawler_definition: Optional[Dict[str, Any]] = Field(
            None,
            description='Crawler definition for create-crawler and update-crawler operations.',
        ),
        crawler_names: Optional[List[str]] = Field(
            None,
            description='List of crawler names for batch-get-crawlers operation.',
        ),
        max_results: Optional[int] = Field(
            None,
            description='Maximum number of results to return for get-crawlers and list-crawlers operations.',
        ),
        next_token: Optional[str] = Field(
            None,
            description='Pagination token for get-crawlers and list-crawlers operations.',
        ),
        tags: Optional[Dict[str, str]] = Field(
            None,
            description='Tags to filter crawlers by for list-crawlers operation.',
        ),
    ) -> Union[
        CreateCrawlerResponse,
        DeleteCrawlerResponse,
        GetCrawlerResponse,
        GetCrawlersResponse,
        StartCrawlerResponse,
        StopCrawlerResponse,
        BatchGetCrawlersResponse,
        ListCrawlersResponse,
        UpdateCrawlerResponse,
    ]:
        """Manage AWS Glue crawlers to discover and catalog data sources.

        This tool provides comprehensive operations for AWS Glue crawlers, which automatically discover and catalog
        data from various sources like S3, JDBC databases, DynamoDB, and more. Crawlers examine your data sources,
        determine schemas, and register metadata in the AWS Glue Data Catalog.

        ## Requirements
        - The server must be run with the `--allow-write` flag for create, delete, start, stop, and update operations
        - Appropriate AWS permissions for Glue crawler operations

        ## Operations
        - **create-crawler**: Create a new crawler with specified targets, role, and configuration
        - **delete-crawler**: Remove an existing crawler from AWS Glue
        - **get-crawler**: Retrieve detailed information about a specific crawler
        - **get-crawlers**: List all crawlers with pagination
        - **batch-get-crawlers**: Retrieve multiple specific crawlers in a single call
        - **list-crawlers**: List all crawlers with tag-based filtering
        - **start-crawler**: Initiate a crawler run immediately
        - **stop-crawler**: Halt a currently running crawler
        - **update-crawler**: Modify an existing crawler's configuration

        ## Example
        ```python
        # Create a new S3 crawler
        {
            'operation': 'create-crawler',
            'crawler_name': 'my-s3-data-crawler',
            'crawler_definition': {
                'Role': 'arn:aws:iam::123456789012:role/GlueServiceRole',
                'Targets': {'S3Targets': [{'Path': 's3://my-bucket/data/'}]},
                'DatabaseName': 'my_catalog_db',
                'Description': 'Crawler for S3 data files',
                'Schedule': 'cron(0 0 * * ? *)',
                'TablePrefix': 'raw_',
            },
        }
        ```

        Args:
            ctx: MCP context
            operation: Operation to perform
            crawler_name: Name of the crawler
            crawler_definition: Crawler definition for create-crawler and update-crawler operations
            crawler_names: List of crawler names for batch-get-crawlers operation
            max_results: Maximum number of results to return for get-crawlers and list-crawlers operations
            next_token: Pagination token for get-crawlers and list-crawlers operations
            tags: Tags to filter crawlers by for list-crawlers operation

        Returns:
            Union of response types specific to the operation performed
        """
        try:
            if not self.allow_write and operation not in [
                'get-crawler',
                'get-crawlers',
                'batch-get-crawlers',
                'list-crawlers',
            ]:
                error_message = f'Operation {operation} is not allowed without write access'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)

                if operation == 'create-crawler':
                    return CreateCrawlerResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        crawler_name='',
                        operation='create-crawler',
                    )
                elif operation == 'delete-crawler':
                    return DeleteCrawlerResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        crawler_name='',
                        operation='delete-crawler',
                    )
                elif operation == 'start-crawler':
                    return StartCrawlerResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        crawler_name='',
                        operation='start-crawler',
                    )
                elif operation == 'stop-crawler':
                    return StopCrawlerResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        crawler_name='',
                        operation='top-crawler',
                    )
                elif operation == 'update-crawler':
                    return UpdateCrawlerResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        crawler_name='',
                        operation='update-crawler',
                    )
                else:
                    return GetCrawlerResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        crawler_name='',
                        operation='get-crawler',
                    )

            if operation == 'create-crawler':
                if crawler_name is None or crawler_definition is None:
                    raise ValueError(
                        'crawler_name and crawler_definition are required for create-crawler operation'
                    )

                # Create the crawler with required and optional parameters
                create_params = {'Name': crawler_name}

                # Add required parameters
                if 'Role' in crawler_definition:
                    create_params['Role'] = crawler_definition.pop('Role')
                else:
                    raise ValueError('Role is required for create-crawler operation')

                if 'Targets' in crawler_definition:
                    create_params['Targets'] = crawler_definition.pop('Targets')
                else:
                    raise ValueError('Targets is required for create-crawler operation')

                # Add MCP management tags
                resource_tags = AwsHelper.prepare_resource_tags('GlueCrawler')
                if 'Tags' in crawler_definition:
                    crawler_definition['Tags'].update(resource_tags)
                else:
                    crawler_definition['Tags'] = resource_tags

                # Add optional parameters
                for param in [
                    'DatabaseName',
                    'Description',
                    'Schedule',
                    'Classifiers',
                    'TablePrefix',
                    'SchemaChangePolicy',
                    'RecrawlPolicy',
                    'LineageConfiguration',
                    'LakeFormationConfiguration',
                    'Configuration',
                    'CrawlerSecurityConfiguration',
                    'Tags',
                ]:
                    if param in crawler_definition:
                        create_params[param] = crawler_definition.pop(param)

                # Add any remaining parameters
                create_params.update(crawler_definition)

                # Create the crawler
                self.glue_client.create_crawler(**create_params)

                return CreateCrawlerResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully created Glue crawler {crawler_name} with MCP management tags',
                        )
                    ],
                    crawler_name=crawler_name,
                    operation='create-crawler',
                )

            elif operation == 'delete-crawler':
                if crawler_name is None:
                    raise ValueError('crawler_name is required for delete-crawler operation')

                # Verify that the crawler is managed by MCP before deleting
                # Construct the ARN for the crawler
                region = AwsHelper.get_aws_region() or 'us-east-1'
                account_id = AwsHelper.get_aws_account_id()
                crawler_arn = f'arn:aws:glue:{region}:{account_id}:crawler/{crawler_name}'

                # Get crawler parameters
                try:
                    response = self.glue_client.get_crawler(Name=crawler_name)
                    crawler = response.get('Crawler', {})
                    parameters = crawler.get('Parameters', {})
                except ClientError:
                    parameters = {}

                # Check if the crawler is managed by MCP
                if not AwsHelper.is_resource_mcp_managed(
                    self.glue_client, crawler_arn, parameters
                ):
                    error_message = f'Cannot delete crawler {crawler_name} - it is not managed by the MCP server (missing required tags)'
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return DeleteCrawlerResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        crawler_name=crawler_name,
                        operation='delete-crawler',
                    )

                # Delete the crawler with required parameters
                self.glue_client.delete_crawler(Name=crawler_name)

                return DeleteCrawlerResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully deleted MCP-managed Glue crawler {crawler_name}',
                        )
                    ],
                    crawler_name=crawler_name,
                    operation='delete-crawler',
                )

            elif operation == 'get-crawler':
                if crawler_name is None:
                    raise ValueError('crawler_name is required for get-crawler operation')

                # Get the crawler with required parameters
                response = self.glue_client.get_crawler(Name=crawler_name)

                return GetCrawlerResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully retrieved crawler {crawler_name}',
                        )
                    ],
                    crawler_name=crawler_name,
                    crawler_details=response.get('Crawler', {}),
                    operation='get-crawler',
                )

            elif operation == 'get-crawlers':
                # Prepare parameters for get_crawlers (all optional)
                params: Dict[str, Any] = {}
                if max_results is not None:
                    params['MaxResults'] = max_results
                if next_token is not None:
                    params['NextToken'] = next_token

                # Get crawlers
                response = self.glue_client.get_crawlers(**params)

                crawlers = response.get('Crawlers', [])
                return GetCrawlersResponse(
                    isError=False,
                    content=[TextContent(type='text', text='Successfully retrieved crawlers')],
                    crawlers=crawlers,
                    count=len(crawlers),
                    next_token=response.get('NextToken'),
                    operation='get-crawlers',
                )

            elif operation == 'start-crawler':
                if crawler_name is None:
                    raise ValueError('crawler_name is required for start-crawler operation')

                # Start crawler with required parameters
                self.glue_client.start_crawler(Name=crawler_name)

                return StartCrawlerResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully started crawler {crawler_name}',
                        )
                    ],
                    crawler_name=crawler_name,
                    operation='start-crawler',
                )

            elif operation == 'stop-crawler':
                if crawler_name is None:
                    raise ValueError('crawler_name is required for stop-crawler operation')

                # Stop crawler with required parameters
                self.glue_client.stop_crawler(Name=crawler_name)

                return StopCrawlerResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully stopped crawler {crawler_name}',
                        )
                    ],
                    crawler_name=crawler_name,
                    operation='stop-crawler',
                )

            elif operation == 'batch-get-crawlers':
                if crawler_names is None or not crawler_names:
                    raise ValueError('crawler_names is required for batch-get-crawlers operation')

                # Batch get crawlers with required parameters
                response = self.glue_client.batch_get_crawlers(CrawlerNames=crawler_names)

                crawlers = response.get('Crawlers', [])
                crawlers_not_found = response.get('CrawlersNotFound', [])
                return BatchGetCrawlersResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully retrieved {len(crawlers)} crawlers',
                        )
                    ],
                    crawlers=crawlers,
                    crawlers_not_found=crawlers_not_found,
                    operation='batch-get-crawlers',
                )

            elif operation == 'list-crawlers':
                # Prepare parameters for list_crawlers (all optional)
                params: Dict[str, Any] = {}
                if max_results is not None:
                    params['MaxResults'] = max_results
                if next_token is not None:
                    params['NextToken'] = next_token
                if tags is not None:
                    params['Tags'] = tags

                # List crawlers
                response = self.glue_client.list_crawlers(**params)

                crawlers = response.get('CrawlerNames', [])
                return ListCrawlersResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text='Successfully listed crawlers',
                        )
                    ],
                    crawlers=crawlers,
                    count=len(crawlers),
                    next_token=response.get('NextToken'),
                    operation='list-crawlers',
                )

            elif operation == 'update-crawler':
                if crawler_name is None or crawler_definition is None:
                    raise ValueError(
                        'crawler_name and crawler_definition are required for update-crawler operation'
                    )

                # Update the crawler with required and optional parameters
                update_params = {'Name': crawler_name}

                # Add optional parameters
                for param in [
                    'Role',
                    'DatabaseName',
                    'Description',
                    'Targets',
                    'Schedule',
                    'Classifiers',
                    'TablePrefix',
                    'SchemaChangePolicy',
                    'RecrawlPolicy',
                    'LineageConfiguration',
                    'LakeFormationConfiguration',
                    'Configuration',
                    'CrawlerSecurityConfiguration',
                ]:
                    if param in crawler_definition:
                        update_params[param] = crawler_definition.pop(param)

                # Add any remaining parameters
                update_params.update(crawler_definition)

                # Update the crawler
                self.glue_client.update_crawler(**update_params)

                return UpdateCrawlerResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully updated crawler {crawler_name}',
                        )
                    ],
                    crawler_name=crawler_name,
                    operation='update-crawler',
                )

            else:
                error_message = f'Invalid operation: {operation}. Must be one of: create-crawler, delete-crawler, get-crawler, get-crawlers, start-crawler, stop-crawler, batch-get-crawlers, list-crawlers, update-crawler'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return GetCrawlerResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    crawler_name=crawler_name or '',
                    crawler_details={},
                    operation='get-crawler',
                )

        except ValueError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f'Parameter validation error: {str(e)}')
            raise
        except Exception as e:
            error_message = f'Error in manage_aws_glue_crawlers: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return GetCrawlerResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                crawler_name=crawler_name or '',
                crawler_details={},
                operation='get-crawler',
            )

    async def manage_aws_glue_classifiers(
        self,
        ctx: Context,
        operation: str = Field(
            ...,
            description='Operation to perform: create-classifier, delete-classifier, get-classifier, get-classifiers, update-classifier. Choose "get-classifier" or "get-classifiers" for read-only operations when write access is disabled.',
        ),
        classifier_name: Optional[str] = Field(
            None,
            description='Name of the classifier (required for delete-classifier and get-classifier operations).',
        ),
        classifier_definition: Optional[Dict[str, Any]] = Field(
            None,
            description='Classifier definition for create-classifier and update-classifier operations. Must include one of GrokClassifier, XMLClassifier, JsonClassifier, or CsvClassifier.',
        ),
        max_results: Optional[int] = Field(
            None,
            description='Maximum number of results to return for get-classifiers operation.',
        ),
        next_token: Optional[str] = Field(
            None,
            description='Pagination token for get-classifiers operation.',
        ),
    ) -> Union[
        CreateClassifierResponse,
        DeleteClassifierResponse,
        GetClassifierResponse,
        GetClassifiersResponse,
        UpdateClassifierResponse,
    ]:
        r"""Manage AWS Glue classifiers to determine data formats and schemas.

        This tool provides operations for AWS Glue classifiers, which help determine the schema of your data.
        Classifiers analyze data samples to infer formats and structures, enabling accurate schema creation
        when crawlers process your data sources.

        ## Requirements
        - The server must be run with the `--allow-write` flag for create, delete, and update operations
        - Appropriate AWS permissions for Glue classifier operations

        ## Operations
        - **create-classifier**: Create a new custom classifier (CSV, JSON, XML, or GROK)
        - **delete-classifier**: Remove an existing classifier
        - **get-classifier**: Retrieve detailed information about a specific classifier
        - **get-classifiers**: List all available classifiers
        - **update-classifier**: Modify an existing classifier's configuration

        ## Example
        ```python
        # Create a CSV classifier
        {
            'operation': 'create-classifier',
            'classifier_definition': {
                'CsvClassifier': {
                    'Name': 'my-csv-classifier',
                    'Delimiter': ',',
                    'QuoteSymbol': '"',
                    'ContainsHeader': 'PRESENT',
                    'Header': ['id', 'name', 'date', 'value'],
                    'AllowSingleColumn': false,
                }
            },
        }
        ```

        Args:
            ctx: MCP context
            operation: Operation to perform
            classifier_name: Name of the classifier
            classifier_definition: Classifier definition for create-classifier and update-classifier operations
            max_results: Maximum number of results to return for get-classifiers operation
            next_token: Pagination token for get-classifiers operation

        Returns:
            Union of response types specific to the operation performed
        """
        try:
            if not self.allow_write and operation not in [
                'get-classifier',
                'get-classifiers',
            ]:
                error_message = f'Operation {operation} is not allowed without write access'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)

                if operation == 'create-classifier':
                    return CreateClassifierResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        classifier_name='',
                        operation='create-classifier',
                    )
                elif operation == 'delete-classifier':
                    return DeleteClassifierResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        classifier_name='',
                        operation='delete-classifier',
                    )
                elif operation == 'update-classifier':
                    return UpdateClassifierResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        classifier_name='',
                        operation='update-classifier',
                    )
                else:
                    return GetClassifierResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        classifier_name='',
                        operation='get-classifier',
                    )

            if operation == 'create-classifier':
                if classifier_definition is None:
                    raise ValueError(
                        'classifier_definition is required for create-classifier operation'
                    )

                # Create the classifier with required parameters
                # Classifier definition must include one of: GrokClassifier, XMLClassifier, JsonClassifier, or CsvClassifier
                if not any(
                    key in classifier_definition
                    for key in [
                        'GrokClassifier',
                        'XMLClassifier',
                        'JsonClassifier',
                        'CsvClassifier',
                    ]
                ):
                    raise ValueError(
                        'classifier_definition must include one of: GrokClassifier, XMLClassifier, JsonClassifier, or CsvClassifier'
                    )

                response = self.glue_client.create_classifier(**classifier_definition)

                # Extract classifier name from definition based on classifier type
                extracted_name = ''
                if 'GrokClassifier' in classifier_definition:
                    extracted_name = classifier_definition['GrokClassifier']['Name']
                elif 'XMLClassifier' in classifier_definition:
                    extracted_name = classifier_definition['XMLClassifier']['Name']
                elif 'JsonClassifier' in classifier_definition:
                    extracted_name = classifier_definition['JsonClassifier']['Name']
                elif 'CsvClassifier' in classifier_definition:
                    extracted_name = classifier_definition['CsvClassifier']['Name']

                return CreateClassifierResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully created classifier {extracted_name}',
                        )
                    ],
                    classifier_name=extracted_name,
                    operation='create-classifier',
                )

            elif operation == 'delete-classifier':
                if classifier_name is None:
                    raise ValueError('classifier_name is required for delete-classifier operation')

                # Delete the classifier with required parameters
                self.glue_client.delete_classifier(Name=classifier_name)

                return DeleteClassifierResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully deleted classifier {classifier_name}',
                        )
                    ],
                    classifier_name=classifier_name,
                    operation='delete-classifier',
                )

            elif operation == 'get-classifier':
                if classifier_name is None:
                    raise ValueError('classifier_name is required for get-classifier operation')

                # Get the classifier with required parameters
                response = self.glue_client.get_classifier(Name=classifier_name)

                return GetClassifierResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully retrieved classifier {classifier_name}',
                        )
                    ],
                    classifier_name=classifier_name,
                    classifier_details=response.get('Classifier', {}),
                    operation='get-classifier',
                )

            elif operation == 'get-classifiers':
                # Prepare parameters for get_classifiers (all optional)
                params: Dict[str, Any] = {}
                if max_results is not None:
                    params['MaxResults'] = max_results
                if next_token is not None:
                    params['NextToken'] = next_token

                # Get classifiers
                response = self.glue_client.get_classifiers(**params)

                classifiers = response.get('Classifiers', [])
                return GetClassifiersResponse(
                    isError=False,
                    content=[TextContent(type='text', text='Successfully retrieved classifiers')],
                    classifiers=classifiers,
                    count=len(classifiers),
                    next_token=response.get('NextToken'),
                    operation='get-classifiers',
                )

            elif operation == 'update-classifier':
                if classifier_definition is None:
                    raise ValueError(
                        'classifier_definition is required for update-classifier operation'
                    )

                # Update the classifier with required parameters
                # Classifier definition must include one of: GrokClassifier, XMLClassifier, JsonClassifier, or CsvClassifier
                if not any(
                    key in classifier_definition
                    for key in [
                        'GrokClassifier',
                        'XMLClassifier',
                        'JsonClassifier',
                        'CsvClassifier',
                    ]
                ):
                    raise ValueError(
                        'classifier_definition must include one of: GrokClassifier, XMLClassifier, JsonClassifier, or CsvClassifier'
                    )

                self.glue_client.update_classifier(**classifier_definition)

                # Extract classifier name from definition based on classifier type
                extracted_name = ''
                if 'GrokClassifier' in classifier_definition:
                    extracted_name = classifier_definition['GrokClassifier']['Name']
                elif 'XMLClassifier' in classifier_definition:
                    extracted_name = classifier_definition['XMLClassifier']['Name']
                elif 'JsonClassifier' in classifier_definition:
                    extracted_name = classifier_definition['JsonClassifier']['Name']
                elif 'CsvClassifier' in classifier_definition:
                    extracted_name = classifier_definition['CsvClassifier']['Name']

                return UpdateClassifierResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully updated classifier {extracted_name}',
                        )
                    ],
                    classifier_name=extracted_name,
                    operation='update-classifier',
                )

            else:
                error_message = f'Invalid operation: {operation}. Must be one of: create-classifier, delete-classifier, get-classifier, get-classifiers, update-classifier'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return GetClassifierResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    classifier_name=classifier_name or '',
                    classifier_details={},
                    operation='get-classifier',
                )

        except ValueError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f'Parameter validation error: {str(e)}')
            raise
        except Exception as e:
            error_message = f'Error in manage_aws_glue_classifiers: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return GetClassifierResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                classifier_name=classifier_name or '',
                classifier_details={},
                operation='get',
            )

    async def manage_aws_glue_crawler_management(
        self,
        ctx: Context,
        operation: str = Field(
            ...,
            description='Operation to perform: get-crawler-metrics, start-crawler-schedule, stop-crawler-schedule, update-crawler-schedule. Choose "get-crawler-metrics" for read-only operations when write access is disabled.',
        ),
        crawler_name: Optional[str] = Field(
            None,
            description='Name of the crawler (required for start-crawler-schedule, stop-crawler-schedule, and update-crawler-schedule operations).',
        ),
        crawler_name_list: Optional[List[str]] = Field(
            None,
            description='List of crawler names for get-crawler-metrics operation (optional).',
        ),
        max_results: Optional[int] = Field(
            None,
            description='Maximum number of results to return for get-crawler-metrics operation (optional).',
        ),
        schedule: Optional[str] = Field(
            None,
            description='Cron expression for the crawler schedule (required for update-crawler-schedule operation).',
        ),
    ) -> Union[
        GetCrawlerMetricsResponse,
        StartCrawlerScheduleResponse,
        StopCrawlerScheduleResponse,
        UpdateCrawlerScheduleResponse,
    ]:
        """Manage AWS Glue crawler schedules and monitor performance metrics.

        This tool provides operations for controlling crawler schedules and retrieving performance metrics.
        Use it to automate crawler runs on a schedule and monitor crawler efficiency and status.

        ## Requirements
        - The server must be run with the `--allow-write` flag for schedule management operations
        - Appropriate AWS permissions for Glue crawler operations

        ## Operations
        - **get-crawler-metrics**: Retrieve performance statistics about crawlers
        - **start-crawler-schedule**: Activate a crawler's schedule
        - **stop-crawler-schedule**: Deactivate a crawler's schedule
        - **update-crawler-schedule**: Modify a crawler's schedule with a new cron expression

        ## Example
        ```python
        # Update a crawler's schedule to run daily at 2:30 AM UTC
        {
            'operation': 'update-crawler-schedule',
            'crawler_name': 'my-s3-data-crawler',
            'schedule': 'cron(30 2 * * ? *)',
        }

        # Get metrics for specific crawlers
        {
            'operation': 'get-crawler-metrics',
            'crawler_name_list': ['my-s3-data-crawler', 'my-jdbc-crawler'],
        }
        ```

        Args:
            ctx: MCP context
            operation: Operation to perform
            crawler_name: Name of the crawler for schedule operations
            crawler_name_list: List of crawler names for get-crawler-metrics operation
            max_results: Maximum number of results to return for get-crawler-metrics operation
            schedule: Cron expression for the crawler schedule (required for update-crawler-schedule operation)

        Returns:
            Union of response types specific to the operation performed
        """
        try:
            if not self.allow_write and operation not in ['get-crawler-metrics']:
                error_message = f'Operation {operation} is not allowed without write access'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)

                if operation == 'start-crawler-schedule':
                    return StartCrawlerScheduleResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        crawler_name='',
                        operation='start-crawler-schedule',
                    )
                elif operation == 'stop-crawler-schedule':
                    return StopCrawlerScheduleResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        crawler_name='',
                        operation='stop-crawler-schedule',
                    )
                elif operation == 'update-crawler-schedule':
                    return UpdateCrawlerScheduleResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        crawler_name='',
                        operation='update-crawler-schedule',
                    )
                else:
                    return GetCrawlerMetricsResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        crawler_name='',
                        operation='get-crawler-metrics',
                    )

            if operation == 'get-crawler-metrics':
                # Prepare parameters for get_crawler_metrics (all optional)
                params: Dict[str, Any] = {}
                if crawler_name_list is not None:
                    params['CrawlerNameList'] = crawler_name_list
                if max_results is not None:
                    params['MaxResults'] = max_results

                # Get crawler metrics
                response = self.glue_client.get_crawler_metrics(**params)

                crawler_metrics = response.get('CrawlerMetricsList', [])
                return GetCrawlerMetricsResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text='Successfully retrieved crawler metrics',
                        )
                    ],
                    crawler_metrics=crawler_metrics,
                    count=len(crawler_metrics),
                    next_token=response.get('NextToken'),
                    operation='get-crawler-metrics',
                )

            elif operation == 'start-crawler-schedule':
                if crawler_name is None:
                    raise ValueError(
                        'crawler_name is required for start-crawler-schedule operation'
                    )

                # Start crawler schedule with required parameters
                self.glue_client.start_crawler_schedule(CrawlerName=crawler_name)

                return StartCrawlerScheduleResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully started schedule for crawler {crawler_name}',
                        )
                    ],
                    crawler_name=crawler_name,
                    operation='start-crawler-schedule',
                )

            elif operation == 'stop-crawler-schedule':
                if crawler_name is None:
                    raise ValueError(
                        'crawler_name is required for stop-crawler-schedule operation'
                    )

                # Stop crawler schedule with required parameters
                self.glue_client.stop_crawler_schedule(CrawlerName=crawler_name)

                return StopCrawlerScheduleResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully stopped schedule for crawler {crawler_name}',
                        )
                    ],
                    crawler_name=crawler_name,
                    operation='stop-crawler-schedule',
                )

            elif operation == 'update-crawler-schedule':
                if crawler_name is None or schedule is None:
                    raise ValueError(
                        'crawler_name and schedule are required for update-crawler-schedule operation'
                    )

                # Update crawler schedule with required parameters
                self.glue_client.update_crawler_schedule(
                    CrawlerName=crawler_name, Schedule=schedule
                )

                return UpdateCrawlerScheduleResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully updated schedule for crawler {crawler_name}',
                        )
                    ],
                    crawler_name=crawler_name,
                    operation='update-crawler-schedule',
                )

            else:
                error_message = f'Invalid operation: {operation}. Must be one of: get-crawler-metrics, start-crawler-schedule, stop-crawler-schedule, update-crawler-schedule'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return GetCrawlerMetricsResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    crawler_metrics=[],
                    count=0,
                    next_token=None,
                    operation='get-crawler-metrics',
                )

        except ValueError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f'Parameter validation error: {str(e)}')
            raise
        except Exception as e:
            error_message = f'Error in manage_aws_glue_crawler_management: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return GetCrawlerMetricsResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                crawler_metrics=[],
                count=0,
                next_token=None,
                operation='get-crawler-metrics',
            )
