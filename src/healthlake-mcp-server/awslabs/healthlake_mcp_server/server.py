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
import logging

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
from mcp.server import Server
from mcp.types import Resource, TextContent, Tool
from typing import Any, Dict, List, Sequence


logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""

    def default(self, obj):
        """Convert datetime objects to ISO format strings."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


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

    def __init__(self, healthlake_client: HealthLakeClient):
        """Initialize tool handler with HealthLake client and set up handlers."""
        self.client = healthlake_client
        self.handlers = {
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

    async def handle_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Dispatch tool call to appropriate handler."""
        if name not in self.handlers:
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
        request = UpdateResourceRequest(**args)

        return await self.client.update_resource(
            datastore_id=request.datastore_id,
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            resource_data=request.resource_data,
        )

    async def _handle_delete(self, args: Dict[str, Any]) -> Dict[str, Any]:
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
        request = ImportJobConfig(**args)

        return await self.client.start_import_job(
            datastore_id=request.datastore_id,
            input_data_config=request.input_data_config,
            job_output_data_config=args['job_output_data_config'],
            data_access_role_arn=request.data_access_role_arn,
            job_name=request.job_name,
        )

    async def _handle_export_job(self, args: Dict[str, Any]) -> Dict[str, Any]:
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


def create_healthlake_server() -> Server:
    """Create and configure the HealthLake MCP server."""
    server = Server('healthlake-mcp-server')
    healthlake_client = HealthLakeClient()
    tool_handler = ToolHandler(healthlake_client)

    @server.list_tools()
    async def handle_list_tools() -> List[Tool]:
        """List available HealthLake tools."""
        return [
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

    @server.list_resources()
    async def handle_list_resources() -> List[Resource]:
        """List available HealthLake datastores as discoverable resources."""
        try:
            response = await healthlake_client.list_datastores()
            resources = []

            for datastore in response.get('DatastorePropertiesList', []):
                status_emoji = '✅' if datastore['DatastoreStatus'] == 'ACTIVE' else '⏳'
                created_date = datetime.fromtimestamp(datastore['CreatedAt']).strftime('%Y-%m-%d')

                resources.append(
                    Resource(
                        uri=f'healthlake://datastore/{datastore["DatastoreId"]}',
                        name=f'{status_emoji} {datastore.get("DatastoreName", "Unnamed")} ({datastore["DatastoreStatus"]})',
                        description=f'FHIR {datastore["DatastoreTypeVersion"]} datastore\n'
                        f'Created: {created_date}\n'
                        f'Endpoint: {datastore["DatastoreEndpoint"]}\n'
                        f'ID: {datastore["DatastoreId"]}',
                        mimeType='application/json',
                    )
                )

            return resources
        except Exception as e:
            logger.error(f'Error listing datastore resources: {e}')
            return []

    @server.read_resource()
    async def handle_read_resource(uri: str) -> str:
        """Read detailed datastore information."""
        if not uri.startswith('healthlake://datastore/'):
            raise ValueError(f'Unknown resource URI: {uri}')

        datastore_id = uri.split('/')[-1]
        details = await healthlake_client.get_datastore_details(datastore_id)

        return json.dumps(details, indent=2, cls=DateTimeEncoder)

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Handle tool calls using dispatch pattern."""
        try:
            return await tool_handler.handle_tool(name, arguments)

        except (InputValidationError, ValueError) as e:
            logger.warning(f'Validation error in {name}: {e}')
            return create_error_response(str(e), 'validation_error')

        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f'AWS error in {name}: {error_code}')

            if error_code == 'ResourceNotFoundException':
                return create_error_response('Resource not found', 'not_found')
            elif error_code == 'ValidationException':
                return create_error_response(
                    f'Invalid parameters: {e.response["Error"]["Message"]}', 'validation_error'
                )
            else:
                return create_error_response('AWS service error', 'service_error')

        except NoCredentialsError:
            logger.error(f'Credentials error in {name}')
            return create_error_response('AWS credentials not configured', 'auth_error')

        except Exception as e:
            logger.error(f'Unexpected error in {name}: {e}', exc_info=True)
            return create_error_response('Internal server error', 'server_error')

    return server
