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
"""Property-based tests for AWS Location Service Geofencing MCP Server.

This module contains property-based tests using the hypothesis library to verify
universal properties of the geofencing tools across generated inputs.
"""

import pytest
from datetime import datetime, timezone
from hypothesis import given, settings
from hypothesis import strategies as st
from unittest.mock import MagicMock, patch


# Strategy for generating valid collection names
# AWS Location Service collection names must be alphanumeric with hyphens and underscores
collection_name_strategy = st.text(
    min_size=1,
    max_size=50,
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-_'),
).filter(lambda x: x and not x.startswith('-') and not x.startswith('_'))

# Strategy for generating optional descriptions
description_strategy = st.text(min_size=0, max_size=200)


@pytest.fixture
def mock_context():
    """Create a mock MCP context for testing."""
    context = MagicMock()

    async def async_error(*args, **kwargs):
        return None

    context.error = MagicMock(side_effect=async_error)
    return context


class TestProperty8CollectionOperationsReturnRequiredFields:
    """Property 8: Collection Operations Return Required Fields.

    *For any* successful collection operation:
    - create_geofence_collection SHALL return 'collection_name', 'collection_arn', and 'create_time'
    - list_geofence_collections SHALL return 'collections' containing items with 'collection_name', 'collection_arn', and 'create_time'
    - describe_geofence_collection SHALL return 'collection_name', 'collection_arn', 'description', 'create_time', and 'update_time'
    - delete_geofence_collection SHALL return 'success' and 'collection_name'

    **Validates: Requirements 1.1, 1.2, 1.3, 1.4**
    """

    @settings(max_examples=100, deadline=None)
    @given(
        collection_name=collection_name_strategy,
        description=description_strategy,
    )
    @pytest.mark.asyncio
    async def test_property_create_geofence_collection_returns_required_fields(
        self, collection_name: str, description: str
    ):
        """Feature: geofencing-support, Property 8: Collection Operations Return Required Fields.

        Test that create_geofence_collection returns 'collection_name', 'collection_arn', and 'create_time'.

        **Validates: Requirements 1.1**
        """
        from awslabs.aws_location_server.server import create_geofence_collection

        # Create mock context
        mock_context = MagicMock()

        async def async_error(*args, **kwargs):
            return None

        mock_context.error = MagicMock(side_effect=async_error)

        # Set up mock response with valid AWS response structure
        create_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        mock_response = {
            'CollectionName': collection_name,
            'CollectionArn': f'arn:aws:geo:us-east-1:123456789012:geofence-collection/{collection_name}',
            'CreateTime': create_time,
        }

        mock_boto3_client = MagicMock()
        mock_boto3_client.create_geofence_collection.return_value = mock_response

        with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
            mock_geo_client.location_client = mock_boto3_client
            with patch('asyncio.to_thread', return_value=mock_response):
                result = await create_geofence_collection(
                    mock_context,
                    collection_name=collection_name,
                    description=description,
                )

        # Property assertion: successful response must contain required fields
        assert 'error' not in result, f'Unexpected error: {result.get("error")}'
        assert 'collection_name' in result, "Response must contain 'collection_name'"
        assert 'collection_arn' in result, "Response must contain 'collection_arn'"
        assert 'create_time' in result, "Response must contain 'create_time'"

        # Verify field values are not None
        assert result['collection_name'] is not None, "'collection_name' must not be None"
        assert result['collection_arn'] is not None, "'collection_arn' must not be None"
        assert result['create_time'] is not None, "'create_time' must not be None"

        # Verify collection_name matches input
        assert result['collection_name'] == collection_name, (
            'Returned collection_name must match input'
        )

    @settings(max_examples=100, deadline=None)
    @given(
        num_collections=st.integers(min_value=0, max_value=10),
        max_results=st.integers(min_value=1, max_value=100),
    )
    @pytest.mark.asyncio
    async def test_property_list_geofence_collections_returns_required_fields(
        self, num_collections: int, max_results: int
    ):
        """Feature: geofencing-support, Property 8: Collection Operations Return Required Fields.

        Test that list_geofence_collections returns 'collections' containing items with
        'collection_name', 'collection_arn', and 'create_time'.

        **Validates: Requirements 1.2**
        """
        from awslabs.aws_location_server.server import list_geofence_collections

        # Create mock context
        mock_context = MagicMock()

        async def async_error(*args, **kwargs):
            return None

        mock_context.error = MagicMock(side_effect=async_error)

        # Generate mock collection entries
        create_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        entries = []
        for i in range(num_collections):
            entries.append(
                {
                    'CollectionName': f'collection-{i}',
                    'CollectionArn': f'arn:aws:geo:us-east-1:123456789012:geofence-collection/collection-{i}',
                    'CreateTime': create_time,
                }
            )

        mock_response = {'Entries': entries}

        mock_boto3_client = MagicMock()
        mock_boto3_client.list_geofence_collections.return_value = mock_response

        with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
            mock_geo_client.location_client = mock_boto3_client
            with patch('asyncio.to_thread', return_value=mock_response):
                result = await list_geofence_collections(mock_context, max_results=max_results)

        # Property assertion: successful response must contain 'collections' key
        assert 'error' not in result, f'Unexpected error: {result.get("error")}'
        assert 'collections' in result, "Response must contain 'collections'"
        assert isinstance(result['collections'], list), "'collections' must be a list"

        # Property assertion: each collection item must have required fields
        for collection in result['collections']:
            assert 'collection_name' in collection, (
                "Each collection must contain 'collection_name'"
            )
            assert 'collection_arn' in collection, "Each collection must contain 'collection_arn'"
            assert 'create_time' in collection, "Each collection must contain 'create_time'"

            # Verify field values are not None
            assert collection['collection_name'] is not None, "'collection_name' must not be None"
            assert collection['collection_arn'] is not None, "'collection_arn' must not be None"
            assert collection['create_time'] is not None, "'create_time' must not be None"

    @settings(max_examples=100, deadline=None)
    @given(
        collection_name=collection_name_strategy,
        description=description_strategy,
    )
    @pytest.mark.asyncio
    async def test_property_describe_geofence_collection_returns_required_fields(
        self, collection_name: str, description: str
    ):
        """Feature: geofencing-support, Property 8: Collection Operations Return Required Fields.

        Test that describe_geofence_collection returns 'collection_name', 'collection_arn',
        'description', 'create_time', and 'update_time'.

        **Validates: Requirements 1.3**
        """
        from awslabs.aws_location_server.server import describe_geofence_collection

        # Create mock context
        mock_context = MagicMock()

        async def async_error(*args, **kwargs):
            return None

        mock_context.error = MagicMock(side_effect=async_error)

        # Set up mock response with valid AWS response structure
        create_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        update_time = datetime(2024, 1, 20, 14, 45, 0, tzinfo=timezone.utc)
        mock_response = {
            'CollectionName': collection_name,
            'CollectionArn': f'arn:aws:geo:us-east-1:123456789012:geofence-collection/{collection_name}',
            'Description': description,
            'CreateTime': create_time,
            'UpdateTime': update_time,
        }

        mock_boto3_client = MagicMock()
        mock_boto3_client.describe_geofence_collection.return_value = mock_response

        with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
            mock_geo_client.location_client = mock_boto3_client
            with patch('asyncio.to_thread', return_value=mock_response):
                result = await describe_geofence_collection(
                    mock_context,
                    collection_name=collection_name,
                )

        # Property assertion: successful response must contain required fields
        assert 'error' not in result, f'Unexpected error: {result.get("error")}'
        assert 'collection_name' in result, "Response must contain 'collection_name'"
        assert 'collection_arn' in result, "Response must contain 'collection_arn'"
        assert 'description' in result, "Response must contain 'description'"
        assert 'create_time' in result, "Response must contain 'create_time'"
        assert 'update_time' in result, "Response must contain 'update_time'"

        # Verify field values are not None (except description which can be empty string)
        assert result['collection_name'] is not None, "'collection_name' must not be None"
        assert result['collection_arn'] is not None, "'collection_arn' must not be None"
        assert result['description'] is not None, "'description' must not be None"
        assert result['create_time'] is not None, "'create_time' must not be None"
        assert result['update_time'] is not None, "'update_time' must not be None"

        # Verify collection_name matches input
        assert result['collection_name'] == collection_name, (
            'Returned collection_name must match input'
        )

    @settings(max_examples=100, deadline=None)
    @given(
        collection_name=collection_name_strategy,
    )
    @pytest.mark.asyncio
    async def test_property_delete_geofence_collection_returns_required_fields(
        self, collection_name: str
    ):
        """Feature: geofencing-support, Property 8: Collection Operations Return Required Fields.

        Test that delete_geofence_collection returns 'success' and 'collection_name'.

        **Validates: Requirements 1.4**
        """
        from awslabs.aws_location_server.server import delete_geofence_collection

        # Create mock context
        mock_context = MagicMock()

        async def async_error(*args, **kwargs):
            return None

        mock_context.error = MagicMock(side_effect=async_error)

        # Set up mock response (delete returns empty response on success)
        mock_response = {}

        mock_boto3_client = MagicMock()
        mock_boto3_client.delete_geofence_collection.return_value = mock_response

        with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
            mock_geo_client.location_client = mock_boto3_client
            with patch('asyncio.to_thread', return_value=mock_response):
                result = await delete_geofence_collection(
                    mock_context,
                    collection_name=collection_name,
                )

        # Property assertion: successful response must contain required fields
        assert 'error' not in result, f'Unexpected error: {result.get("error")}'
        assert 'success' in result, "Response must contain 'success'"
        assert 'collection_name' in result, "Response must contain 'collection_name'"

        # Verify field values
        assert result['success'] is True, "'success' must be True"
        assert result['collection_name'] is not None, "'collection_name' must not be None"

        # Verify collection_name matches input
        assert result['collection_name'] == collection_name, (
            'Returned collection_name must match input'
        )


class TestProperty3PutGeofenceReturnsRequiredFields:
    """Property 3: Put Geofence Returns Required Fields.

    *For any* valid put_geofence call with either circle geometry (valid center coordinates
    and positive radius) or polygon geometry (valid linear ring), the response SHALL contain
    'geofence_id', 'create_time', and 'update_time' fields.

    **Validates: Requirements 2.1, 2.2**
    """

    @settings(max_examples=100, deadline=None)
    @given(
        collection_name=collection_name_strategy,
        geofence_id=collection_name_strategy,
        center_lon=st.floats(min_value=-180, max_value=180, allow_nan=False, allow_infinity=False),
        center_lat=st.floats(min_value=-90, max_value=90, allow_nan=False, allow_infinity=False),
        radius=st.floats(min_value=1, max_value=100000, allow_nan=False, allow_infinity=False),
    )
    @pytest.mark.asyncio
    async def test_property_put_geofence_circle_returns_required_fields(
        self,
        collection_name: str,
        geofence_id: str,
        center_lon: float,
        center_lat: float,
        radius: float,
    ):
        """Feature: geofencing-support, Property 3: Put Geofence Returns Required Fields.

        Test that put_geofence with circle geometry returns 'geofence_id', 'create_time', and 'update_time'.

        **Validates: Requirements 2.1**
        """
        from awslabs.aws_location_server.server import put_geofence

        mock_context = MagicMock()

        async def async_error(*args, **kwargs):
            return None

        mock_context.error = MagicMock(side_effect=async_error)

        create_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        update_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        mock_response = {
            'GeofenceId': geofence_id,
            'CreateTime': create_time,
            'UpdateTime': update_time,
        }

        mock_boto3_client = MagicMock()
        mock_boto3_client.put_geofence.return_value = mock_response

        with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
            mock_geo_client.location_client = mock_boto3_client
            with patch('asyncio.to_thread', return_value=mock_response):
                result = await put_geofence(
                    mock_context,
                    collection_name=collection_name,
                    geofence_id=geofence_id,
                    geometry_type='Circle',
                    circle_center=[center_lon, center_lat],
                    circle_radius=radius,
                )

        assert 'error' not in result, f'Unexpected error: {result.get("error")}'
        assert 'geofence_id' in result, "Response must contain 'geofence_id'"
        assert 'create_time' in result, "Response must contain 'create_time'"
        assert 'update_time' in result, "Response must contain 'update_time'"
        assert result['geofence_id'] == geofence_id, 'Returned geofence_id must match input'


class TestProperty5GetGeofenceReturnsCompleteDetails:
    """Property 5: Get Geofence Returns Complete Details.

    *For any* existing geofence in a collection, calling get_geofence SHALL return a dictionary
    containing 'geofence_id', 'geometry', 'status', 'create_time', and 'update_time' fields.

    **Validates: Requirements 2.3**
    """

    @settings(max_examples=100, deadline=None)
    @given(
        collection_name=collection_name_strategy,
        geofence_id=collection_name_strategy,
        status=st.sampled_from(['ACTIVE', 'PENDING', 'FAILED', 'DELETED', 'DELETING']),
    )
    @pytest.mark.asyncio
    async def test_property_get_geofence_returns_complete_details(
        self, collection_name: str, geofence_id: str, status: str
    ):
        """Feature: geofencing-support, Property 5: Get Geofence Returns Complete Details.

        **Validates: Requirements 2.3**
        """
        from awslabs.aws_location_server.server import get_geofence

        mock_context = MagicMock()

        async def async_error(*args, **kwargs):
            return None

        mock_context.error = MagicMock(side_effect=async_error)

        create_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        update_time = datetime(2024, 1, 20, 14, 45, 0, tzinfo=timezone.utc)
        mock_response = {
            'GeofenceId': geofence_id,
            'Geometry': {'Circle': {'Center': [-122.3321, 47.6062], 'Radius': 1000.0}},
            'Status': status,
            'CreateTime': create_time,
            'UpdateTime': update_time,
        }

        mock_boto3_client = MagicMock()
        mock_boto3_client.get_geofence.return_value = mock_response

        with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
            mock_geo_client.location_client = mock_boto3_client
            with patch('asyncio.to_thread', return_value=mock_response):
                result = await get_geofence(
                    mock_context,
                    collection_name=collection_name,
                    geofence_id=geofence_id,
                )

        assert 'error' not in result, f'Unexpected error: {result.get("error")}'
        assert 'geofence_id' in result, "Response must contain 'geofence_id'"
        assert 'geometry' in result, "Response must contain 'geometry'"
        assert 'status' in result, "Response must contain 'status'"
        assert 'create_time' in result, "Response must contain 'create_time'"
        assert 'update_time' in result, "Response must contain 'update_time'"


class TestProperty6ListGeofencesReturnsAllRequiredFields:
    """Property 6: List Geofences Returns All Required Fields.

    *For any* collection containing geofences, calling list_geofences SHALL return a dictionary
    with a 'geofences' key containing a list where each item has 'geofence_id', 'geometry',
    'status', and 'create_time' fields.

    **Validates: Requirements 2.4**
    """

    @settings(max_examples=100, deadline=None)
    @given(
        collection_name=collection_name_strategy,
        num_geofences=st.integers(min_value=0, max_value=10),
        max_results=st.integers(min_value=1, max_value=100),
    )
    @pytest.mark.asyncio
    async def test_property_list_geofences_returns_all_required_fields(
        self, collection_name: str, num_geofences: int, max_results: int
    ):
        """Feature: geofencing-support, Property 6: List Geofences Returns All Required Fields.

        **Validates: Requirements 2.4**
        """
        from awslabs.aws_location_server.server import list_geofences

        mock_context = MagicMock()

        async def async_error(*args, **kwargs):
            return None

        mock_context.error = MagicMock(side_effect=async_error)

        create_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        entries = []
        for i in range(num_geofences):
            entries.append(
                {
                    'GeofenceId': f'geofence-{i}',
                    'Geometry': {'Circle': {'Center': [-122.3321, 47.6062], 'Radius': 1000.0}},
                    'Status': 'ACTIVE',
                    'CreateTime': create_time,
                }
            )

        mock_response = {'Entries': entries}

        mock_boto3_client = MagicMock()
        mock_boto3_client.list_geofences.return_value = mock_response

        with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
            mock_geo_client.location_client = mock_boto3_client
            with patch('asyncio.to_thread', return_value=mock_response):
                result = await list_geofences(
                    mock_context,
                    collection_name=collection_name,
                    max_results=max_results,
                )

        assert 'error' not in result, f'Unexpected error: {result.get("error")}'
        assert 'geofences' in result, "Response must contain 'geofences'"
        assert isinstance(result['geofences'], list), "'geofences' must be a list"

        for geofence in result['geofences']:
            assert 'geofence_id' in geofence, "Each geofence must contain 'geofence_id'"
            assert 'geometry' in geofence, "Each geofence must contain 'geometry'"
            assert 'status' in geofence, "Each geofence must contain 'status'"
            assert 'create_time' in geofence, "Each geofence must contain 'create_time'"


class TestProperty7BatchDeleteReturnsDeletedIDsAndErrors:
    """Property 7: Batch Delete Returns Deleted IDs and Errors.

    *For any* batch_delete_geofences call with a list of geofence IDs, the response SHALL
    contain 'deleted' (list of successfully deleted IDs) and 'errors' (list of error objects
    for failed deletions) keys.

    **Validates: Requirements 2.5**
    """

    @settings(max_examples=100, deadline=None)
    @given(
        collection_name=collection_name_strategy,
        num_geofences=st.integers(min_value=1, max_value=10),
        num_errors=st.integers(min_value=0, max_value=5),
    )
    @pytest.mark.asyncio
    async def test_property_batch_delete_returns_deleted_ids_and_errors(
        self, collection_name: str, num_geofences: int, num_errors: int
    ):
        """Feature: geofencing-support, Property 7: Batch Delete Returns Deleted IDs and Errors.

        **Validates: Requirements 2.5**
        """
        from awslabs.aws_location_server.server import batch_delete_geofences

        mock_context = MagicMock()

        async def async_error(*args, **kwargs):
            return None

        mock_context.error = MagicMock(side_effect=async_error)

        geofence_ids = [f'geofence-{i}' for i in range(num_geofences)]

        # Simulate some errors (up to num_errors, but not more than num_geofences)
        actual_errors = min(num_errors, num_geofences)
        errors = []
        for i in range(actual_errors):
            errors.append(
                {
                    'GeofenceId': geofence_ids[i],
                    'Error': {
                        'Code': 'ResourceNotFoundException',
                        'Message': 'Geofence not found',
                    },
                }
            )

        mock_response = {'Errors': errors}

        mock_boto3_client = MagicMock()
        mock_boto3_client.batch_delete_geofence.return_value = mock_response

        with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
            mock_geo_client.location_client = mock_boto3_client
            with patch('asyncio.to_thread', return_value=mock_response):
                result = await batch_delete_geofences(
                    mock_context,
                    collection_name=collection_name,
                    geofence_ids=geofence_ids,
                )

        assert 'error' not in result, f'Unexpected error: {result.get("error")}'
        assert 'deleted' in result, "Response must contain 'deleted'"
        assert 'errors' in result, "Response must contain 'errors'"
        assert isinstance(result['deleted'], list), "'deleted' must be a list"
        assert isinstance(result['errors'], list), "'errors' must be a list"


class TestProperty10GeometryResponseFormat:
    """Property 10: Geometry Response Format.

    *For any* geofence response containing geometry, the geometry SHALL be a dictionary
    with exactly one key ('Circle', 'Polygon', or 'MultiPolygon') containing the appropriate
    coordinate structure.

    **Validates: Requirements 5.3**
    """

    @settings(max_examples=100, deadline=None)
    @given(
        geometry_type=st.sampled_from(['Circle', 'Polygon', 'MultiPolygon']),
    )
    @pytest.mark.asyncio
    async def test_property_geometry_response_format(self, geometry_type: str):
        """Feature: geofencing-support, Property 10: Geometry Response Format.

        **Validates: Requirements 5.3**
        """
        from awslabs.aws_location_server.server import get_geofence

        mock_context = MagicMock()

        async def async_error(*args, **kwargs):
            return None

        mock_context.error = MagicMock(side_effect=async_error)

        # Build geometry based on type
        if geometry_type == 'Circle':
            geometry = {'Circle': {'Center': [-122.3321, 47.6062], 'Radius': 1000.0}}
        elif geometry_type == 'Polygon':
            geometry = {
                'Polygon': [
                    [
                        [-122.3321, 47.6062],
                        [-122.3421, 47.6062],
                        [-122.3421, 47.6162],
                        [-122.3321, 47.6062],
                    ]
                ]
            }
        else:  # MultiPolygon
            geometry = {
                'MultiPolygon': [
                    [
                        [
                            [-122.3321, 47.6062],
                            [-122.3421, 47.6062],
                            [-122.3421, 47.6162],
                            [-122.3321, 47.6062],
                        ]
                    ]
                ]
            }

        create_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        update_time = datetime(2024, 1, 20, 14, 45, 0, tzinfo=timezone.utc)
        mock_response = {
            'GeofenceId': 'test-geofence',
            'Geometry': geometry,
            'Status': 'ACTIVE',
            'CreateTime': create_time,
            'UpdateTime': update_time,
        }

        mock_boto3_client = MagicMock()
        mock_boto3_client.get_geofence.return_value = mock_response

        with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
            mock_geo_client.location_client = mock_boto3_client
            with patch('asyncio.to_thread', return_value=mock_response):
                result = await get_geofence(
                    mock_context,
                    collection_name='test-collection',
                    geofence_id='test-geofence',
                )

        assert 'error' not in result, f'Unexpected error: {result.get("error")}'
        assert 'geometry' in result, "Response must contain 'geometry'"

        # Verify geometry has exactly one key
        geometry_keys = list(result['geometry'].keys())
        assert len(geometry_keys) == 1, 'Geometry must have exactly one key'
        assert geometry_keys[0] in ('Circle', 'Polygon', 'MultiPolygon'), (
            f"Geometry key must be 'Circle', 'Polygon', or 'MultiPolygon', got '{geometry_keys[0]}'"
        )


class TestProperty9PositionEvaluationProducesEventsForBoundaryCrossings:
    """Property 9: Position Evaluation Produces Events for Boundary Crossings.

    *For any* device position that crosses a geofence boundary (from outside to inside
    or inside to outside), batch_evaluate_geofences SHALL return results containing
    the device_id, geofence_id, and event_type ('ENTER' or 'EXIT').

    **Validates: Requirements 3.1, 3.2**
    """

    @settings(max_examples=100, deadline=None)
    @given(
        collection_name=collection_name_strategy,
        num_devices=st.integers(min_value=1, max_value=5),
        lon=st.floats(min_value=-180, max_value=180, allow_nan=False, allow_infinity=False),
        lat=st.floats(min_value=-90, max_value=90, allow_nan=False, allow_infinity=False),
    )
    @pytest.mark.asyncio
    async def test_property_batch_evaluate_returns_results_structure(
        self, collection_name: str, num_devices: int, lon: float, lat: float
    ):
        """Feature: geofencing-support, Property 9: Position Evaluation Produces Events for Boundary Crossings.

        Test that batch_evaluate_geofences returns a 'results' key with proper structure.

        **Validates: Requirements 3.1, 3.2**
        """
        from awslabs.aws_location_server.server import batch_evaluate_geofences

        mock_context = MagicMock()

        async def async_error(*args, **kwargs):
            return None

        mock_context.error = MagicMock(side_effect=async_error)

        # Generate device position updates
        device_position_updates = []
        for i in range(num_devices):
            device_position_updates.append(
                {
                    'device_id': f'device-{i}',
                    'position': [lon, lat],
                    'sample_time': '2024-01-15T10:30:00Z',
                }
            )

        # Mock response with no errors (successful evaluation)
        mock_response = {'Errors': []}

        mock_boto3_client = MagicMock()
        mock_boto3_client.batch_evaluate_geofences.return_value = mock_response

        with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
            mock_geo_client.location_client = mock_boto3_client
            with patch('asyncio.to_thread', return_value=mock_response):
                result = await batch_evaluate_geofences(
                    mock_context,
                    collection_name=collection_name,
                    device_position_updates=device_position_updates,
                )

        # Property assertion: successful response must contain 'results' key
        assert 'error' not in result, f'Unexpected error: {result.get("error")}'
        assert 'results' in result, "Response must contain 'results'"
        assert isinstance(result['results'], list), "'results' must be a list"


class TestProperty1ErrorResponseFormatConsistency:
    """Property 1: Error Response Format Consistency.

    *For any* geofencing tool call that results in an error (AWS service error, invalid geometry,
    invalid coordinates, ClientError, or general exception), the response SHALL be a dictionary
    containing an 'error' key with a non-empty string describing the error.

    **Validates: Requirements 1.5, 2.7, 3.4, 5.2, 6.2, 6.3**
    """

    @settings(max_examples=100, deadline=None)
    @given(
        error_message=st.text(min_size=1, max_size=100),
    )
    @pytest.mark.asyncio
    async def test_property_client_error_returns_error_dict(self, error_message: str):
        """Feature: geofencing-support, Property 1: Error Response Format Consistency.

        Test that ClientError returns a dictionary with 'error' key.

        **Validates: Requirements 1.5, 5.2, 6.2**
        """
        from awslabs.aws_location_server.server import create_geofence_collection
        from botocore.exceptions import ClientError

        mock_context = MagicMock()

        async def async_error(*args, **kwargs):
            return None

        mock_context.error = MagicMock(side_effect=async_error)

        mock_boto3_client = MagicMock()

        with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
            mock_geo_client.location_client = mock_boto3_client
            with patch(
                'asyncio.to_thread',
                side_effect=ClientError(
                    {'Error': {'Code': 'TestError', 'Message': error_message}},
                    'create_geofence_collection',
                ),
            ):
                result = await create_geofence_collection(
                    mock_context,
                    collection_name='test-collection',
                )

        # Property assertion: error response must be a dict with 'error' key
        assert isinstance(result, dict), 'Error response must be a dictionary'
        assert 'error' in result, "Error response must contain 'error' key"
        assert isinstance(result['error'], str), "'error' value must be a string"
        assert len(result['error']) > 0, "'error' value must be non-empty"

    @settings(max_examples=100, deadline=None)
    @given(
        error_message=st.text(min_size=1, max_size=100),
    )
    @pytest.mark.asyncio
    async def test_property_general_exception_returns_error_dict(self, error_message: str):
        """Feature: geofencing-support, Property 1: Error Response Format Consistency.

        Test that general exceptions return a dictionary with 'error' key.

        **Validates: Requirements 1.5, 5.2, 6.3**
        """
        from awslabs.aws_location_server.server import list_geofence_collections

        mock_context = MagicMock()

        async def async_error(*args, **kwargs):
            return None

        mock_context.error = MagicMock(side_effect=async_error)

        mock_boto3_client = MagicMock()

        with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
            mock_geo_client.location_client = mock_boto3_client
            with patch('asyncio.to_thread', side_effect=Exception(error_message)):
                result = await list_geofence_collections(mock_context, max_results=10)

        # Property assertion: error response must be a dict with 'error' key
        assert isinstance(result, dict), 'Error response must be a dictionary'
        assert 'error' in result, "Error response must contain 'error' key"
        assert isinstance(result['error'], str), "'error' value must be a string"
        assert len(result['error']) > 0, "'error' value must be non-empty"

    @settings(max_examples=100, deadline=None)
    @given(
        geometry_type=st.sampled_from(['InvalidType', 'Unknown', 'BadGeometry', '']),
    )
    @pytest.mark.asyncio
    async def test_property_invalid_geometry_returns_error_dict(self, geometry_type: str):
        """Feature: geofencing-support, Property 1: Error Response Format Consistency.

        Test that invalid geometry returns a dictionary with 'error' key.

        **Validates: Requirements 2.7, 5.2**
        """
        from awslabs.aws_location_server.server import put_geofence

        mock_context = MagicMock()

        async def async_error(*args, **kwargs):
            return None

        mock_context.error = MagicMock(side_effect=async_error)

        mock_boto3_client = MagicMock()

        with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
            mock_geo_client.location_client = mock_boto3_client
            result = await put_geofence(
                mock_context,
                collection_name='test-collection',
                geofence_id='test-geofence',
                geometry_type=geometry_type,
            )

        # Property assertion: error response must be a dict with 'error' key
        assert isinstance(result, dict), 'Error response must be a dictionary'
        assert 'error' in result, "Error response must contain 'error' key"
        assert isinstance(result['error'], str), "'error' value must be a string"
        assert len(result['error']) > 0, "'error' value must be non-empty"


class TestProperty2UninitializedClientErrorHandling:
    """Property 2: Uninitialized Client Error Handling.

    *For any* geofencing tool called when the GeoFencingClient's location_client is None,
    the tool SHALL return a dictionary with an 'error' key containing a message indicating
    the client is not initialized.

    **Validates: Requirements 4.5**
    """

    @settings(max_examples=10, deadline=None)
    @given(
        collection_name=collection_name_strategy,
    )
    @pytest.mark.asyncio
    async def test_property_uninitialized_client_create_collection(self, collection_name: str):
        """Feature: geofencing-support, Property 2: Uninitialized Client Error Handling.

        **Validates: Requirements 4.5**
        """
        from awslabs.aws_location_server.server import create_geofence_collection

        mock_context = MagicMock()

        async def async_error(*args, **kwargs):
            return None

        mock_context.error = MagicMock(side_effect=async_error)

        with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
            mock_geo_client.location_client = None
            result = await create_geofence_collection(
                mock_context, collection_name=collection_name
            )

        assert isinstance(result, dict), 'Response must be a dictionary'
        assert 'error' in result, "Response must contain 'error' key"
        assert 'not initialized' in result['error'].lower(), (
            'Error must indicate client not initialized'
        )

    @settings(max_examples=10, deadline=None)
    @given(
        collection_name=collection_name_strategy,
        geofence_id=collection_name_strategy,
    )
    @pytest.mark.asyncio
    async def test_property_uninitialized_client_put_geofence(
        self, collection_name: str, geofence_id: str
    ):
        """Feature: geofencing-support, Property 2: Uninitialized Client Error Handling.

        **Validates: Requirements 4.5**
        """
        from awslabs.aws_location_server.server import put_geofence

        mock_context = MagicMock()

        async def async_error(*args, **kwargs):
            return None

        mock_context.error = MagicMock(side_effect=async_error)

        with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
            mock_geo_client.location_client = None
            result = await put_geofence(
                mock_context,
                collection_name=collection_name,
                geofence_id=geofence_id,
                geometry_type='Circle',
                circle_center=[-122.3321, 47.6062],
                circle_radius=1000.0,
            )

        assert isinstance(result, dict), 'Response must be a dictionary'
        assert 'error' in result, "Response must contain 'error' key"
        assert 'not initialized' in result['error'].lower(), (
            'Error must indicate client not initialized'
        )


class TestProperty11TimestampFormatCompliance:
    """Property 11: Timestamp Format Compliance.

    *For any* response containing timestamp fields (create_time, update_time, sample_time),
    the timestamp SHALL be a valid ISO 8601 format string.

    **Validates: Requirements 5.4**
    """

    @settings(max_examples=100, deadline=None)
    @given(
        year=st.integers(min_value=2020, max_value=2030),
        month=st.integers(min_value=1, max_value=12),
        day=st.integers(min_value=1, max_value=28),
        hour=st.integers(min_value=0, max_value=23),
        minute=st.integers(min_value=0, max_value=59),
    )
    @pytest.mark.asyncio
    async def test_property_timestamp_format_compliance(
        self, year: int, month: int, day: int, hour: int, minute: int
    ):
        """Feature: geofencing-support, Property 11: Timestamp Format Compliance.

        **Validates: Requirements 5.4**
        """
        import re
        from awslabs.aws_location_server.server import describe_geofence_collection

        mock_context = MagicMock()

        async def async_error(*args, **kwargs):
            return None

        mock_context.error = MagicMock(side_effect=async_error)

        # Create datetime with the generated values
        create_time = datetime(year, month, day, hour, minute, 0, tzinfo=timezone.utc)
        update_time = datetime(year, month, day, hour, minute, 30, tzinfo=timezone.utc)

        mock_response = {
            'CollectionName': 'test-collection',
            'CollectionArn': 'arn:aws:geo:us-east-1:123456789012:geofence-collection/test-collection',
            'Description': 'Test description',
            'CreateTime': create_time,
            'UpdateTime': update_time,
        }

        mock_boto3_client = MagicMock()
        mock_boto3_client.describe_geofence_collection.return_value = mock_response

        with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
            mock_geo_client.location_client = mock_boto3_client
            with patch('asyncio.to_thread', return_value=mock_response):
                result = await describe_geofence_collection(
                    mock_context,
                    collection_name='test-collection',
                )

        assert 'error' not in result, f'Unexpected error: {result.get("error")}'

        # ISO 8601 pattern (simplified - matches common formats)
        iso8601_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'

        if 'create_time' in result and result['create_time']:
            assert re.match(iso8601_pattern, result['create_time']), (
                f"create_time '{result['create_time']}' is not ISO 8601 format"
            )

        if 'update_time' in result and result['update_time']:
            assert re.match(iso8601_pattern, result['update_time']), (
                f"update_time '{result['update_time']}' is not ISO 8601 format"
            )


class TestProperty12SuccessfulResponsesAreDictionaries:
    """Property 12: Successful Responses Are Dictionaries.

    *For any* successful geofencing tool call, the response SHALL be a dictionary
    (not a list, string, or other type).

    **Validates: Requirements 5.1**
    """

    @settings(max_examples=100, deadline=None)
    @given(
        collection_name=collection_name_strategy,
    )
    @pytest.mark.asyncio
    async def test_property_successful_responses_are_dicts(self, collection_name: str):
        """Feature: geofencing-support, Property 12: Successful Responses Are Dictionaries.

        **Validates: Requirements 5.1**
        """
        from awslabs.aws_location_server.server import create_geofence_collection

        mock_context = MagicMock()

        async def async_error(*args, **kwargs):
            return None

        mock_context.error = MagicMock(side_effect=async_error)

        create_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        mock_response = {
            'CollectionName': collection_name,
            'CollectionArn': f'arn:aws:geo:us-east-1:123456789012:geofence-collection/{collection_name}',
            'CreateTime': create_time,
        }

        mock_boto3_client = MagicMock()
        mock_boto3_client.create_geofence_collection.return_value = mock_response

        with patch('awslabs.aws_location_server.server.geo_fencing_client') as mock_geo_client:
            mock_geo_client.location_client = mock_boto3_client
            with patch('asyncio.to_thread', return_value=mock_response):
                result = await create_geofence_collection(
                    mock_context,
                    collection_name=collection_name,
                )

        # Property assertion: successful response must be a dictionary
        assert isinstance(result, dict), f'Response must be a dictionary, got {type(result)}'
