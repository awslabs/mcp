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

"""AWS HealthImaging MCP Server implementation."""

# Standard library imports
import json
import logging

# Local imports
from .healthimaging_operations import MAX_SEARCH_COUNT, HealthImagingClient, validate_datastore_id
from .models import (
    BulkDeleteByCriteriaRequest,
    BulkUpdatePatientMetadataRequest,
    DatastoreFilter,
    DeleteImageSetRequest,
    DeletePatientStudiesRequest,
    DeleteStudyRequest,
    GetPatientSeriesRequest,
    GetPatientStudiesRequest,
    GetStudyPrimaryImageSetsRequest,
    ImageFrameRequest,
    ImageSetMetadataRequest,
    ImageSetRequest,
    ImageSetVersionsRequest,
    RemoveInstanceRequest,
    RemoveSeriesRequest,
    SearchByPatientRequest,
    SearchBySeriesRequest,
    SearchByStudyRequest,
    SearchImageSetsRequest,
    UpdateImageSetMetadataRequest,
)

# Third-party imports
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime
from mcp.server import Server
from mcp.types import Resource, TextContent, Tool
from pydantic import AnyUrl
from typing import Any, Dict, List, Sequence


logger = logging.getLogger(__name__)


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

    def __init__(self, healthimaging_client: HealthImagingClient):
        """Initialize tool handler with HealthImaging client and set up handlers."""
        self.client = healthimaging_client
        self.handlers = {
            # Original 7 tools
            'list_datastores': self._handle_list_datastores,
            'get_datastore_details': self._handle_get_datastore,
            'search_image_sets': self._handle_search_image_sets,
            'get_image_set': self._handle_get_image_set,
            'get_image_set_metadata': self._handle_get_image_set_metadata,
            'get_image_frame': self._handle_get_image_frame,
            'list_image_set_versions': self._handle_list_image_set_versions,
            # Delete operations (3 tools)
            'delete_image_set': self._handle_delete_image_set,
            'delete_patient_studies': self._handle_delete_patient_studies,
            'delete_study': self._handle_delete_study,
            # Metadata update operations (3 tools)
            'update_image_set_metadata': self._handle_update_image_set_metadata,
            'remove_series_from_image_set': self._handle_remove_series,
            'remove_instance_from_image_set': self._handle_remove_instance,
            # Enhanced search operations (3 tools)
            'search_by_patient_id': self._handle_search_by_patient,
            'search_by_study_uid': self._handle_search_by_study,
            'search_by_series_uid': self._handle_search_by_series,
            # Data analysis operations (3 tools)
            'get_patient_studies': self._handle_get_patient_studies,
            'get_patient_series': self._handle_get_patient_series,
            'get_study_primary_image_sets': self._handle_get_study_primary_image_sets,
            # Bulk operations (2 tools)
            'bulk_update_patient_metadata': self._handle_bulk_update_patient_metadata,
            'bulk_delete_by_criteria': self._handle_bulk_delete_by_criteria,
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

    async def _handle_search_image_sets(self, args: Dict[str, Any]) -> Dict[str, Any]:
        request = SearchImageSetsRequest(**args)
        return await self.client.search_image_sets(
            datastore_id=request.datastore_id,
            search_criteria=request.search_criteria,
            max_results=request.max_results,
        )

    async def _handle_get_image_set(self, args: Dict[str, Any]) -> Dict[str, Any]:
        request = ImageSetRequest(**args)
        return await self.client.get_image_set(
            datastore_id=request.datastore_id,
            image_set_id=request.image_set_id,
        )

    async def _handle_get_image_set_metadata(self, args: Dict[str, Any]) -> str:
        request = ImageSetMetadataRequest(**args)
        return await self.client.get_image_set_metadata(
            datastore_id=request.datastore_id,
            image_set_id=request.image_set_id,
            version_id=request.version_id,
        )

    async def _handle_get_image_frame(self, args: Dict[str, Any]) -> Dict[str, Any]:
        request = ImageFrameRequest(**args)
        return await self.client.get_image_frame(
            datastore_id=request.datastore_id,
            image_set_id=request.image_set_id,
            image_frame_id=request.image_frame_id,
        )

    async def _handle_list_image_set_versions(self, args: Dict[str, Any]) -> Dict[str, Any]:
        request = ImageSetVersionsRequest(**args)
        return await self.client.list_image_set_versions(
            datastore_id=request.datastore_id,
            image_set_id=request.image_set_id,
            max_results=request.max_results,
        )

    # DELETE OPERATION HANDLERS

    async def _handle_delete_image_set(self, args: Dict[str, Any]) -> Dict[str, Any]:
        request = DeleteImageSetRequest(**args)
        return await self.client.delete_image_set(
            datastore_id=request.datastore_id,
            image_set_id=request.image_set_id,
        )

    async def _handle_delete_patient_studies(self, args: Dict[str, Any]) -> Dict[str, Any]:
        request = DeletePatientStudiesRequest(**args)
        return await self.client.delete_patient_studies(
            datastore_id=request.datastore_id,
            patient_id=request.patient_id,
        )

    async def _handle_delete_study(self, args: Dict[str, Any]) -> Dict[str, Any]:
        request = DeleteStudyRequest(**args)
        return await self.client.delete_study(
            datastore_id=request.datastore_id,
            study_instance_uid=request.study_instance_uid,
        )

    # METADATA UPDATE HANDLERS

    async def _handle_update_image_set_metadata(self, args: Dict[str, Any]) -> Dict[str, Any]:
        request = UpdateImageSetMetadataRequest(**args)
        return await self.client.update_image_set_metadata(
            datastore_id=request.datastore_id,
            image_set_id=request.image_set_id,
            version_id=request.version_id,
            updates=request.updates,
        )

    async def _handle_remove_series(self, args: Dict[str, Any]) -> Dict[str, Any]:
        request = RemoveSeriesRequest(**args)
        return await self.client.remove_series_from_image_set(
            datastore_id=request.datastore_id,
            image_set_id=request.image_set_id,
            series_instance_uid=request.series_instance_uid,
        )

    async def _handle_remove_instance(self, args: Dict[str, Any]) -> Dict[str, Any]:
        request = RemoveInstanceRequest(**args)
        return await self.client.remove_instance_from_image_set(
            datastore_id=request.datastore_id,
            image_set_id=request.image_set_id,
            sop_instance_uid=request.sop_instance_uid,
            series_instance_uid=request.series_instance_uid,
        )

    # ENHANCED SEARCH HANDLERS

    async def _handle_search_by_patient(self, args: Dict[str, Any]) -> Dict[str, Any]:
        request = SearchByPatientRequest(**args)
        return await self.client.search_by_patient_id(
            datastore_id=request.datastore_id,
            patient_id=request.patient_id,
            include_primary_only=request.include_primary_only,
        )

    async def _handle_search_by_study(self, args: Dict[str, Any]) -> Dict[str, Any]:
        request = SearchByStudyRequest(**args)
        return await self.client.search_by_study_uid(
            datastore_id=request.datastore_id,
            study_instance_uid=request.study_instance_uid,
            include_primary_only=request.include_primary_only,
        )

    async def _handle_search_by_series(self, args: Dict[str, Any]) -> Dict[str, Any]:
        request = SearchBySeriesRequest(**args)
        return await self.client.search_by_series_uid(
            datastore_id=request.datastore_id,
            series_instance_uid=request.series_instance_uid,
        )

    # DATA ANALYSIS HANDLERS

    async def _handle_get_patient_studies(self, args: Dict[str, Any]) -> Dict[str, Any]:
        request = GetPatientStudiesRequest(**args)
        return await self.client.get_patient_studies(
            datastore_id=request.datastore_id,
            patient_id=request.patient_id,
        )

    async def _handle_get_patient_series(self, args: Dict[str, Any]) -> Dict[str, Any]:
        request = GetPatientSeriesRequest(**args)
        return await self.client.get_patient_series(
            datastore_id=request.datastore_id,
            patient_id=request.patient_id,
        )

    async def _handle_get_study_primary_image_sets(self, args: Dict[str, Any]) -> Dict[str, Any]:
        request = GetStudyPrimaryImageSetsRequest(**args)
        return await self.client.get_study_primary_image_sets(
            datastore_id=request.datastore_id,
            study_instance_uid=request.study_instance_uid,
        )

    # BULK OPERATION HANDLERS

    async def _handle_bulk_update_patient_metadata(self, args: Dict[str, Any]) -> Dict[str, Any]:
        request = BulkUpdatePatientMetadataRequest(**args)
        return await self.client.bulk_update_patient_metadata(
            datastore_id=request.datastore_id,
            patient_id=request.patient_id,
            new_metadata=request.new_metadata,
        )

    async def _handle_bulk_delete_by_criteria(self, args: Dict[str, Any]) -> Dict[str, Any]:
        request = BulkDeleteByCriteriaRequest(**args)
        return await self.client.bulk_delete_by_criteria(
            datastore_id=request.datastore_id,
            search_criteria=request.search_criteria,
        )


def create_healthimaging_server() -> Server:
    """Create and configure the HealthImaging MCP server."""
    server = Server('healthimaging-mcp-server')
    healthimaging_client = HealthImagingClient()
    tool_handler = ToolHandler(healthimaging_client)

    @server.list_tools()
    async def handle_list_tools() -> List[Tool]:
        """List available HealthImaging tools."""
        return [
            # Datastore Management (foundational operations)
            Tool(
                name='list_datastores',
                description='List all HealthImaging datastores in the account',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'status': {
                            'type': 'string',
                            'description': 'Filter datastores by status (CREATING, ACTIVE, DELETING, DELETED)',
                            'enum': ['CREATING', 'ACTIVE', 'DELETING', 'DELETED'],
                        }
                    },
                },
            ),
            Tool(
                name='get_datastore_details',
                description='Get detailed information about a specific HealthImaging datastore',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthImaging datastore ID',
                        }
                    },
                    'required': ['datastore_id'],
                },
            ),
            # Image Set Operations (core functionality)
            Tool(
                name='search_image_sets',
                description='Search for image sets in a HealthImaging datastore with advanced search capabilities. Returns up to 100 results per call.',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthImaging datastore ID',
                        },
                        'search_criteria': {
                            'type': 'object',
                            'description': 'DICOM search criteria (optional)',
                            'additionalProperties': True,
                        },
                        'max_results': {
                            'type': 'integer',
                            'description': 'Maximum number of results to return (1-100, default: 50)',
                            'minimum': 1,
                            'maximum': 100,
                            'default': 50,
                        },
                    },
                    'required': ['datastore_id'],
                },
            ),
            Tool(
                name='get_image_set',
                description='Get metadata for a specific image set',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthImaging datastore ID',
                        },
                        'image_set_id': {
                            'type': 'string',
                            'description': 'Image set ID',
                        },
                    },
                    'required': ['datastore_id', 'image_set_id'],
                },
            ),
            Tool(
                name='get_image_set_metadata',
                description='Get detailed DICOM metadata for an image set',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthImaging datastore ID',
                        },
                        'image_set_id': {
                            'type': 'string',
                            'description': 'Image set ID',
                        },
                        'version_id': {
                            'type': 'string',
                            'description': 'Version ID (optional, defaults to latest)',
                        },
                    },
                    'required': ['datastore_id', 'image_set_id'],
                },
            ),
            Tool(
                name='get_image_frame',
                description='Get information about a specific image frame',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthImaging datastore ID',
                        },
                        'image_set_id': {
                            'type': 'string',
                            'description': 'Image set ID',
                        },
                        'image_frame_id': {
                            'type': 'string',
                            'description': 'Image frame ID',
                        },
                    },
                    'required': ['datastore_id', 'image_set_id', 'image_frame_id'],
                },
            ),
            Tool(
                name='list_image_set_versions',
                description='List all versions of an image set',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthImaging datastore ID',
                        },
                        'image_set_id': {
                            'type': 'string',
                            'description': 'Image set ID',
                        },
                        'max_results': {
                            'type': 'integer',
                            'description': 'Maximum number of results to return (1-100, default: 50)',
                            'minimum': 1,
                            'maximum': 100,
                            'default': 50,
                        },
                    },
                    'required': ['datastore_id', 'image_set_id'],
                },
            ),
            # DELETE OPERATIONS (Critical for data lifecycle management)
            Tool(
                name='delete_image_set',
                description='Delete an image set (IRREVERSIBLE operation)',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthImaging datastore ID',
                        },
                        'image_set_id': {
                            'type': 'string',
                            'description': 'Image set ID to delete',
                        },
                    },
                    'required': ['datastore_id', 'image_set_id'],
                },
            ),
            Tool(
                name='delete_patient_studies',
                description='Delete all studies for a specific patient (IRREVERSIBLE operation)',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthImaging datastore ID',
                        },
                        'patient_id': {
                            'type': 'string',
                            'description': 'DICOM Patient ID',
                        },
                    },
                    'required': ['datastore_id', 'patient_id'],
                },
            ),
            Tool(
                name='delete_study',
                description='Delete all image sets for a specific study (IRREVERSIBLE operation)',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthImaging datastore ID',
                        },
                        'study_instance_uid': {
                            'type': 'string',
                            'description': 'DICOM Study Instance UID',
                        },
                    },
                    'required': ['datastore_id', 'study_instance_uid'],
                },
            ),
            # METADATA UPDATE OPERATIONS (Critical for data corrections)
            Tool(
                name='update_image_set_metadata',
                description='Update DICOM metadata for an image set',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthImaging datastore ID',
                        },
                        'image_set_id': {
                            'type': 'string',
                            'description': 'Image set ID',
                        },
                        'version_id': {
                            'type': 'string',
                            'description': 'Current version ID of the image set',
                        },
                        'updates': {
                            'type': 'object',
                            'description': 'DICOM metadata updates',
                            'additionalProperties': True,
                        },
                    },
                    'required': ['datastore_id', 'image_set_id', 'version_id', 'updates'],
                },
            ),
            Tool(
                name='remove_series_from_image_set',
                description='Remove a specific series from an image set',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthImaging datastore ID',
                        },
                        'image_set_id': {
                            'type': 'string',
                            'description': 'Image set ID',
                        },
                        'series_instance_uid': {
                            'type': 'string',
                            'description': 'DICOM Series Instance UID to remove',
                        },
                    },
                    'required': ['datastore_id', 'image_set_id', 'series_instance_uid'],
                },
            ),
            Tool(
                name='remove_instance_from_image_set',
                description='Remove a specific instance from an image set',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthImaging datastore ID',
                        },
                        'image_set_id': {
                            'type': 'string',
                            'description': 'Image set ID',
                        },
                        'sop_instance_uid': {
                            'type': 'string',
                            'description': 'DICOM SOP Instance UID to remove',
                        },
                        'series_instance_uid': {
                            'type': 'string',
                            'description': 'DICOM Series Instance UID (optional, will be auto-detected if not provided)',
                        },
                    },
                    'required': ['datastore_id', 'image_set_id', 'sop_instance_uid'],
                },
            ),
            # ENHANCED SEARCH OPERATIONS (Improved clinical workflows)
            Tool(
                name='search_by_patient_id',
                description='Enhanced search for all data related to a patient with study/series analysis',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthImaging datastore ID',
                        },
                        'patient_id': {
                            'type': 'string',
                            'description': 'DICOM Patient ID',
                        },
                        'include_primary_only': {
                            'type': 'boolean',
                            'description': 'Include only primary image sets (default: false)',
                            'default': False,
                        },
                    },
                    'required': ['datastore_id', 'patient_id'],
                },
            ),
            Tool(
                name='search_by_study_uid',
                description='Enhanced search for all image sets in a specific study',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthImaging datastore ID',
                        },
                        'study_instance_uid': {
                            'type': 'string',
                            'description': 'DICOM Study Instance UID',
                        },
                        'include_primary_only': {
                            'type': 'boolean',
                            'description': 'Include only primary image sets (default: false)',
                            'default': False,
                        },
                    },
                    'required': ['datastore_id', 'study_instance_uid'],
                },
            ),
            Tool(
                name='search_by_series_uid',
                description='Enhanced search for image sets containing a specific series',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthImaging datastore ID',
                        },
                        'series_instance_uid': {
                            'type': 'string',
                            'description': 'DICOM Series Instance UID',
                        },
                    },
                    'required': ['datastore_id', 'series_instance_uid'],
                },
            ),
            # DATA ANALYSIS OPERATIONS (Clinical insights)
            Tool(
                name='get_patient_studies',
                description='Get all studies for a patient with comprehensive study-level DICOM metadata',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthImaging datastore ID',
                        },
                        'patient_id': {
                            'type': 'string',
                            'description': 'DICOM Patient ID',
                        },
                    },
                    'required': ['datastore_id', 'patient_id'],
                },
            ),
            Tool(
                name='get_patient_series',
                description='Get all series UIDs for a patient for series-level analysis',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthImaging datastore ID',
                        },
                        'patient_id': {
                            'type': 'string',
                            'description': 'DICOM Patient ID',
                        },
                    },
                    'required': ['datastore_id', 'patient_id'],
                },
            ),
            Tool(
                name='get_study_primary_image_sets',
                description='Get primary image sets for a study (avoids duplicates)',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthImaging datastore ID',
                        },
                        'study_instance_uid': {
                            'type': 'string',
                            'description': 'DICOM Study Instance UID',
                        },
                    },
                    'required': ['datastore_id', 'study_instance_uid'],
                },
            ),
            # BULK OPERATIONS (Efficiency for large datasets)
            Tool(
                name='bulk_update_patient_metadata',
                description='Update patient metadata across all studies for a patient (e.g., name corrections)',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthImaging datastore ID',
                        },
                        'patient_id': {
                            'type': 'string',
                            'description': 'DICOM Patient ID',
                        },
                        'new_metadata': {
                            'type': 'object',
                            'description': 'New patient metadata to apply',
                            'additionalProperties': True,
                        },
                    },
                    'required': ['datastore_id', 'patient_id', 'new_metadata'],
                },
            ),
            Tool(
                name='bulk_delete_by_criteria',
                description='Delete multiple image sets matching search criteria (IRREVERSIBLE operation)',
                inputSchema={
                    'type': 'object',
                    'properties': {
                        'datastore_id': {
                            'type': 'string',
                            'description': 'HealthImaging datastore ID',
                        },
                        'search_criteria': {
                            'type': 'object',
                            'description': 'DICOM search criteria for bulk deletion',
                            'additionalProperties': True,
                        },
                    },
                    'required': ['datastore_id', 'search_criteria'],
                },
            ),
        ]

    @server.list_resources()
    async def handle_list_resources() -> List[Resource]:
        """List available HealthImaging datastores as discoverable resources."""
        try:
            response = await healthimaging_client.list_datastores()
            resources = []

            for datastore in response.get('datastoreSummaries', []):
                status_emoji = '✅' if datastore['datastoreStatus'] == 'ACTIVE' else '⏳'
                created_date = datetime.fromtimestamp(datastore['createdAt']).strftime('%Y-%m-%d')

                resources.append(
                    Resource(
                        uri=AnyUrl(f'healthimaging://datastore/{datastore["datastoreId"]}'),
                        name=f'{status_emoji} {datastore.get("datastoreName", "Unnamed")} ({datastore["datastoreStatus"]})',
                        description=f'HealthImaging datastore\n'
                        f'Created: {created_date}\n'
                        f'ID: {datastore["datastoreId"]}',
                        mimeType='application/json',
                    )
                )

            return resources
        except Exception as e:
            logger.error(f'Error listing datastore resources: {e}')
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> str:
        """Read detailed datastore information."""
        uri_str = str(uri)
        if not uri_str.startswith('healthimaging://datastore/'):
            raise ValueError(f'Unknown resource URI: {uri_str}')

        datastore_id = uri_str.split('/')[-1]
        details = await healthimaging_client.get_datastore_details(datastore_id)

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
