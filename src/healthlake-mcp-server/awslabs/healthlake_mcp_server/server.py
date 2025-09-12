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

"""AWS HealthLake MCP Server implementation."""

# Standard library imports
import json

# Local imports
from .fhir_operations import MAX_SEARCH_COUNT, HealthLakeClient, validate_datastore_id
from .models import (
    CreateResourceRequest,
    DatastoreFilter,
    ExportJobConfig,
    ImportJobConfig,
    JobFilter,
    UpdateResourceRequest,
)

# Third-party imports
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime
from loguru import logger
from mcp.server import Server
from mcp.types import Resource, TextContent, Tool
from pydantic import AnyUrl
from typing import Any, Dict, List, Sequence


# Tool categories for read-only mode
READ_ONLY_TOOLS = {
    'list_datastores',
    'get_datastore_details',
    'read_fhir_resource',
    'search_fhir_resources',
    'patient_everything',
    'list_fhir_jobs',
}

WRITE_TOOLS = {
    'create_fhir_resource',
    'update_fhir_resource',
    'delete_fhir_resource',
    'start_fhir_import_job',
    'start_fhir_export_job',
}


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""

    def default(self, o):
        """Convert datetime objects to ISO format strings."""
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


class InputValidationError(Exception):
    """Custom validation error for input parameters."""

    pass


def validate_count(count: int) -> int:
    """Validate and normalize count parameter."""
    if count < 1 or count > MAX_SEARCH_COUNT:
        raise InputValidationError(f'Count must be between 1 and {MAX_SEARCH_COUNT}')
    return count


def create_error_response(message: str, error_type: str = 'error') -> List[TextContent]:
    """Create standardized error response."""
    return [
        TextContent(
            type='text',
            text=json.dumps({'error': True, 'type': error_type, 'message': message}, indent=2),
        )
    ]


def create_success_response(data: Any) -> List[TextContent]:
    """Create standardized success response."""
    return [TextContent(type='text', text=json.dumps(data, indent=2, cls=DateTimeEncoder))]


class ToolHandler:
    """Handles tool dispatch and execution."""

    def __init__(self, healthlake_client: HealthLakeClient, read_only: bool = False):
        """Initialize tool handler with HealthLake client and read-only mode support."""
        self.client = healthlake_client
        self.read_only = read_only

        # Define all possible handlers
        all_handlers = {
            'list_datastores': self._handle_list_datastores,
            'get_datastore_details': self._handle_get_datastore,
            'create_fhir_resource': self._handle_create,
            'read_fhir_resource': self._handle_read,
            'update_fhir_resource': self._handle_update,
            'delete_fhir_resource': self._handle_delete,
            'search_fhir_resources': self._handle_search,
            'patient_everything': self._handle_patient_everything,
            'start_fhir_import_job': self._handle_import_job,
            'start_fhir_export_job': self._handle_export_job,
            'list_fhir_jobs': self._handle_list_jobs,
        }

        # Filter handlers based on read-only mode
        if read_only:
            self.handlers = {k: v for k, v in all_handlers.items() if k in READ_ONLY_TOOLS}
        else:
            self.handlers = all_handlers

    async def handle_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Dispatch tool call to appropriate handler with read-only safety check."""
        if name not in self.handlers:
            if self.read_only and name in WRITE_TOOLS:
                raise ValueError(f'Tool {name} not available in read-only mode')
            else:
                raise ValueError(f'Unknown tool: {name}')

        handler = self.handlers[name]
        result = await handler(arguments)
        return create_success_response(result)

    async def _handle_list_datastores(self, args: Dict[str, Any]) -> Dict[str, Any]:
        filter_obj = DatastoreFilter(**args)
        return await self.client.list_datastores(filter_status=filter_obj.status)

    async def _handle_get_datastore(self, args: Dict[str, Any]) -> Dict[str, Any]:
        datastore_id = validate_datastore_id(args['datastore_id'])

        return await self.client.get_datastore_details(datastore_id=datastore_id)

    async def _handle_create(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if self.read_only:
            raise ValueError('Create operation not allowed in read-only mode')

        request = CreateResourceRequest(**args)

        return await self.client.create_resource(
            datastore_id=request.datastore_id,
            resource_type=request.resource_type,
            resource_data=request.resource_data,
        )

    async def _handle_read(self, args: Dict[str, Any]) -> Dict[str, Any]:
        datastore_id = validate_datastore_id(args['datastore_id'])

        return await self.client.read_resource(
            datastore_id=datastore_id,
            resource_type=args['resource_type'],
            resource_id=args['resource_id'],
        )

    async def _handle_update(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if self.read_only:
            raise ValueError('Update operation not allowed in read-only mode')

        request = UpdateResourceRequest(**args)

        return await self.client.update_resource(
            datastore_id=request.datastore_id,
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            resource_data=request.resource_data,
        )

    async def _handle_delete(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if self.read_only:
            raise ValueError('Delete operation not allowed in read-only mode')

        datastore_id = validate_datastore_id(args['datastore_id'])

        return await self.client.delete_resource(
            datastore_id=datastore_id,
            resource_type=args['resource_type'],
            resource_id=args['resource_id'],
        )

    async def _handle_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        datastore_id = validate_datastore_id(args['datastore_id'])

        count = args.get('count', 100)
        if count < 1 or count > MAX_SEARCH_COUNT:
            raise ValueError(f'Count must be between 1 and {MAX_SEARCH_COUNT}')

        return await self.client.search_resources(
            datastore_id=datastore_id,
            resource_type=args['resource_type'],
            search_params=args.get('search_params', {}),
            include_params=args.get('include_params'),
            revinclude_params=args.get('revinclude_params'),
            chained_params=args.get('chained_params'),
            count=count,
            next_token=args.get('next_token'),
        )

    async def _handle_patient_everything(self, args: Dict[str, Any]) -> Dict[str, Any]:
        datastore_id = validate_datastore_id(args['datastore_id'])

        count = args.get('count', 100)
        if count < 1 or count > MAX_SEARCH_COUNT:
            raise ValueError(f'Count must be between 1 and {MAX_SEARCH_COUNT}')

        return await self.client.patient_everything(
            datastore_id=datastore_id,
            patient_id=args['patient_id'],
            start=args.get('start'),
            end=args.get('end'),
            count=count,
            next_token=args.get('next_token'),
        )

    async def _handle_import_job(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if self.read_only:
            raise ValueError('Import job operation not allowed in read-only mode')

        request = ImportJobConfig(**args)

        return await self.client.start_import_job(
            datastore_id=request.datastore_id,
            input_data_config=request.input_data_config,
            job_output_data_config=args['job_output_data_config'],
            data_access_role_arn=request.data_access_role_arn,
            job_name=request.job_name,
        )

    async def _handle_export_job(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if self.read_only:
            raise ValueError('Export job operation not allowed in read-only mode')

        request = ExportJobConfig(**args)

        return await self.client.start_export_job(
            datastore_id=request.datastore_id,
            output_data_config=request.output_data_config,
            data_access_role_arn=request.data_access_role_arn,
            job_name=request.job_name,
        )

    async def _handle_list_jobs(self, args: Dict[str, Any]) -> Dict[str, Any]:
        datastore_id = validate_datastore_id(args['datastore_id'])

        filter_obj = JobFilter(job_status=args.get('job_status'), job_type=args.get('job_type'))

        return await self.client.list_jobs(
            datastore_id=datastore_id,
            job_status=filter_obj.job_status,
            job_type=filter_obj.job_type,
        )


def create_healthlake_server(read_only: bool = False) -> Server:
    """Create and configure the HealthLake MCP server."""
    server = Server('healthlake-mcp-server')
    healthlake_client = HealthLakeClient()
    tool_handler = ToolHandler(healthlake_client, read_only=read_only)

    @server.list_tools()
    async def handle_list_tools() -> List[Tool]:
        """List available HealthLake tools based on mode."""
        # Define all tools
        all_tools = [
            # Datastore Management (foundational operations)
            Tool(
                name='list_datastores',
                description='List all HealthLake datastores in the account',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'filter': {
                            'type': 'string',
                            'description': 'Filter datastores by status (CREATING, ACTIVE, DELETING, DELETED)',
                            'enum': ['CREATING', 'ACTIVE', 'DELETING', 'DELETED'],
                        }
                    },
                },
            ),
            Tool(
                name='get_datastore_details',
                description='Get detailed information about a specific HealthLake datastore',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthLake datastore ID',
                        }
                    },
                    'required': ['datastore_id'],
                },
            ),
            # CRUD Operations (core functionality)
            Tool(
                name='create_fhir_resource',
                description='Create a new FHIR resource in HealthLake',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthLake datastore ID',
                        },
                        'resource_type': {'type': 'string', 'description': 'FHIR resource type'},
                        'resource_data': {
                            'type': 'object',
                            'description': 'FHIR resource data as JSON object',
                        },
                    },
                    'required': ['datastore_id', 'resource_type', 'resource_data'],
                },
            ),
            Tool(
                name='read_fhir_resource',
                description='Get a specific FHIR resource by ID',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthLake datastore ID',
                        },
                        'resource_type': {'type': 'string', 'description': 'FHIR resource type'},
                        'resource_id': {'type': 'string', 'description': 'FHIR resource ID'},
                    },
                    'required': ['datastore_id', 'resource_type', 'resource_id'],
                },
            ),
            Tool(
                name='update_fhir_resource',
                description='Update an existing FHIR resource in HealthLake',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthLake datastore ID',
                        },
                        'resource_type': {'type': 'string', 'description': 'FHIR resource type'},
                        'resource_id': {'type': 'string', 'description': 'FHIR resource ID'},
                        'resource_data': {
                            'type': 'object',
                            'description': 'Updated FHIR resource data as JSON object',
                        },
                    },
                    'required': ['datastore_id', 'resource_type', 'resource_id', 'resource_data'],
                },
            ),
            Tool(
                name='delete_fhir_resource',
                description='Delete a FHIR resource from HealthLake',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthLake datastore ID',
                        },
                        'resource_type': {'type': 'string', 'description': 'FHIR resource type'},
                        'resource_id': {'type': 'string', 'description': 'FHIR resource ID'},
                    },
                    'required': ['datastore_id', 'resource_type', 'resource_id'],
                },
            ),
            # Advanced Search Operations
            Tool(
                name='search_fhir_resources',
                description='Search for FHIR resources in HealthLake datastore with advanced search capabilities. Returns up to 100 results per call. If pagination.has_next is true, call this tool again with the next_token to get more results.',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthLake datastore ID',
                        },
                        'resource_type': {
                            'type': 'string',
                            'description': 'FHIR resource type (e.g., Patient, Observation, Condition)',
                        },
                        'search_params': {
                            'type': 'object',
                            'description': "Basic FHIR search parameters. Supports modifiers (e.g., 'name:contains'), prefixes (e.g., 'birthdate': 'ge1990-01-01'), and simple chaining (e.g., 'subject:Patient')",
                            'additionalProperties': True,
                        },
                        'chained_params': {
                            'type': 'object',
                            'description': "Advanced chained search parameters. Key format: 'param.chain' or 'param:TargetType.chain' (e.g., {'subject.name': 'Smith', 'general-practitioner:Practitioner.name': 'Johnson'})",
                            'additionalProperties': {'type': 'string'},
                        },
                        'include_params': {
                            'type': 'array',
                            'description': "Include related resources in the response. Format: 'ResourceType:parameter' or 'ResourceType:parameter:target-type' (e.g., ['Patient:general-practitioner', 'Observation:subject:Patient'])",
                            'items': {'type': 'string'},
                        },
                        'revinclude_params': {
                            'type': 'array',
                            'description': "Include resources that reference the found resources. Format: 'ResourceType:parameter' (e.g., ['Observation:subject', 'Condition:subject'])",
                            'items': {'type': 'string'},
                        },
                        'count': {
                            'type': 'integer',
                            'description': 'Maximum number of results to return (1-100, default: 100)',
                            'minimum': 1,
                            'maximum': 100,
                            'default': 100,
                        },
                        'next_token': {
                            'type': 'string',
                            'description': "Pagination token for retrieving the next page of results. Use the complete URL from a previous response's pagination.next_token field. When provided, other search parameters are ignored.",
                        },
                    },
                    'required': ['datastore_id', 'resource_type'],
                },
            ),
            Tool(
                name='patient_everything',
                description='Retrieve all resources related to a specific patient using the FHIR $patient-everything operation',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthLake datastore ID',
                        },
                        'patient_id': {'type': 'string', 'description': 'Patient resource ID'},
                        'start': {
                            'type': 'string',
                            'description': 'Start date for filtering resources (YYYY-MM-DD format)',
                        },
                        'end': {
                            'type': 'string',
                            'description': 'End date for filtering resources (YYYY-MM-DD format)',
                        },
                        'count': {
                            'type': 'integer',
                            'description': 'Maximum number of results to return (1-100, default: 100)',
                            'minimum': 1,
                            'maximum': 100,
                            'default': 100,
                        },
                        'next_token': {
                            'type': 'string',
                            'description': "Pagination token for retrieving the next page of results. Use the complete URL from a previous response's pagination.next_token field.",
                        },
                    },
                    'required': ['datastore_id', 'patient_id'],
                },
            ),
            # Job Management Operations
            Tool(
                name='start_fhir_import_job',
                description='Start a FHIR import job to load data into HealthLake',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthLake datastore ID',
                        },
                        'input_data_config': {
                            'type': 'object',
                            'description': 'Input data configuration',
                            'properties': {
                                's3_uri': {
                                    'type': 'string',
                                    'description': 'S3 URI containing FHIR data',
                                }
                            },
                            'required': ['s3_uri'],
                        },
                        'job_output_data_config': {
                            'type': 'object',
                            'description': 'Output data configuration (required for import jobs)',
                            'properties': {
                                's3_configuration': {
                                    'type': 'object',
                                    'properties': {
                                        's3_uri': {
                                            'type': 'string',
                                            'description': 'S3 URI for job output/logs',
                                        },
                                        'kms_key_id': {
                                            'type': 'string',
                                            'description': 'KMS key ID for encryption (optional)',
                                        },
                                    },
                                    'required': ['s3_uri'],
                                }
                            },
                            'required': ['s3_configuration'],
                        },
                        'data_access_role_arn': {
                            'type': 'string',
                            'description': 'IAM role ARN for data access',
                        },
                        'job_name': {'type': 'string', 'description': 'Name for the import job'},
                    },
                    'required': [
                        'datastore_id',
                        'input_data_config',
                        'job_output_data_config',
                        'data_access_role_arn',
                    ],
                },
            ),
            Tool(
                name='start_fhir_export_job',
                description='Start a FHIR export job to export data from HealthLake',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthLake datastore ID',
                        },
                        'output_data_config': {
                            'type': 'object',
                            'description': 'Output data configuration',
                            'properties': {
                                's3_configuration': {
                                    'type': 'object',
                                    'properties': {
                                        's3_uri': {
                                            'type': 'string',
                                            'description': 'S3 URI for export destination',
                                        },
                                        'kms_key_id': {
                                            'type': 'string',
                                            'description': 'KMS key ID for encryption',
                                        },
                                    },
                                    'required': ['s3_uri'],
                                }
                            },
                            'required': ['s3_configuration'],
                        },
                        'data_access_role_arn': {
                            'type': 'string',
                            'description': 'IAM role ARN for data access',
                        },
                        'job_name': {'type': 'string', 'description': 'Name for the export job'},
                    },
                    'required': ['datastore_id', 'output_data_config', 'data_access_role_arn'],
                },
            ),
            Tool(
                name='list_fhir_jobs',
                description='List FHIR import/export jobs',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthLake datastore ID',
                        },
                        'job_status': {
                            'type': 'string',
                            'description': 'Filter jobs by status',
                            'enum': [
                                'SUBMITTED',
                                'IN_PROGRESS',
                                'COMPLETED',
                                'FAILED',
                                'STOP_REQUESTED',
                                'STOPPED',
                            ],
                        },
                        'job_type': {
                            'type': 'string',
                            'description': 'Type of job to list',
                            'enum': ['IMPORT', 'EXPORT'],
                        },
                    },
                    'required': ['datastore_id'],
                },
            ),
        ]

        # Filter tools based on read-only mode
        if read_only:
            return [tool for tool in all_tools if tool.name in READ_ONLY_TOOLS]
        else:
            return all_tools

    @server.list_resources()
    async def handle_list_resources() -> List[Resource]:
        """List available HealthLake datastores as discoverable resources."""
        try:
            response = await healthlake_client.list_datastores()
            return [
                Resource(
                    uri=AnyUrl(f'healthlake://datastore/{ds["DatastoreId"]}'),
                    name=f'{"✅" if ds["DatastoreStatus"] == "ACTIVE" else "⏳"} {ds.get("DatastoreName", "Unnamed")} ({ds["DatastoreStatus"]})',
                    description=f'FHIR {ds["DatastoreTypeVersion"]} datastore\nCreated: {ds["CreatedAt"].strftime("%Y-%m-%d")}\nEndpoint: {ds["DatastoreEndpoint"]}\nID: {ds["DatastoreId"]}',
                    mimeType='application/json',
                )
                for ds in response.get('DatastorePropertiesList', [])
            ]
        except Exception as e:
            logger.error(f'Error listing datastore resources: {e}')
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> str:
        """Read detailed datastore information."""
        uri_str = str(uri)
        if not uri_str.startswith('healthlake://datastore/'):
            raise ValueError(f'Unknown resource URI: {uri_str}')
        datastore_id = uri_str.split('/')[-1]
        return json.dumps(
            await healthlake_client.get_datastore_details(datastore_id),
            indent=2,
            cls=DateTimeEncoder,
        )

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Handle tool calls using dispatch pattern."""
        try:
            return await tool_handler.handle_tool(name, arguments)
        except (InputValidationError, ValueError) as e:
            if 'read-only mode' in str(e):
                logger.warning(f'Read-only mode violation attempt: {name}')
                return create_error_response(
                    f'Operation {name} not available in read-only mode. '
                    'Remove --readonly flag to enable write operations.',
                    'read_only_violation',
                )
            else:
                logger.warning(f'Validation error in {name}: {e}')
                return create_error_response(str(e), 'validation_error')
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f'AWS error in {name}: {error_code}')
            errors = {
                'ResourceNotFoundException': ('Resource not found', 'not_found'),
                'ValidationException': (
                    f'Invalid parameters: {e.response["Error"]["Message"]}',
                    'validation_error',
                ),
            }
            msg, typ = errors.get(error_code, ('AWS service error', 'service_error'))
            return create_error_response(msg, typ)
        except NoCredentialsError:
            logger.error(f'Credentials error in {name}')
            return create_error_response('AWS credentials not configured', 'auth_error')
        except Exception:
            logger.exception('Unexpected error in tool call', tool=name)
            return create_error_response('Internal server error', 'server_error')

    return server
