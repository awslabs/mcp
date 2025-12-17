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

"""Tests for additional tool handlers."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from awslabs.healthimaging_mcp_server.healthimaging_operations import HealthImagingClient
from awslabs.healthimaging_mcp_server.server import ToolHandler


@pytest.fixture
def mock_client():
    """Create a mock HealthImaging client."""
    return MagicMock(spec=HealthImagingClient)


@pytest.fixture
def handler(mock_client):
    """Create a tool handler with mock client."""
    return ToolHandler(mock_client)


class TestDeleteHandlers:
    """Tests for delete operation handlers."""

    @pytest.mark.asyncio
    async def test_handle_delete_image_set(self, handler, mock_client):
        """Test delete image set handler."""
        mock_client.delete_image_set = AsyncMock(return_value={'imageSetState': 'DELETED'})

        result = await handler.handle_tool('delete_image_set', {
            'datastore_id': 'a' * 32,
            'image_set_id': 'b' * 32
        })

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data['imageSetState'] == 'DELETED'

    @pytest.mark.asyncio
    async def test_handle_delete_patient_studies(self, handler, mock_client):
        """Test delete patient studies handler."""
        mock_client.delete_patient_studies = AsyncMock(return_value={
            'patientId': 'P123',
            'totalDeleted': 2
        })

        result = await handler.handle_tool('delete_patient_studies', {
            'datastore_id': 'a' * 32,
            'patient_id': 'P123'
        })

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data['totalDeleted'] == 2

    @pytest.mark.asyncio
    async def test_handle_delete_study(self, handler, mock_client):
        """Test delete study handler."""
        mock_client.delete_study = AsyncMock(return_value={
            'studyInstanceUID': '1.2.3',
            'totalDeleted': 1
        })

        result = await handler.handle_tool('delete_study', {
            'datastore_id': 'a' * 32,
            'study_instance_uid': '1.2.3'
        })

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data['totalDeleted'] == 1


class TestMetadataUpdateHandlers:
    """Tests for metadata update handlers."""

    @pytest.mark.asyncio
    async def test_handle_update_image_set_metadata(self, handler, mock_client):
        """Test update image set metadata handler."""
        mock_client.update_image_set_metadata = AsyncMock(return_value={
            'latestVersionId': '2'
        })

        result = await handler.handle_tool('update_image_set_metadata', {
            'datastore_id': 'a' * 32,
            'image_set_id': 'b' * 32,
            'version_id': '1',
            'updates': {'DICOMUpdates': {}}
        })

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data['latestVersionId'] == '2'

    @pytest.mark.asyncio
    async def test_handle_remove_series(self, handler, mock_client):
        """Test remove series handler."""
        mock_client.remove_series_from_image_set = AsyncMock(return_value={
            'latestVersionId': '2'
        })

        result = await handler.handle_tool('remove_series_from_image_set', {
            'datastore_id': 'a' * 32,
            'image_set_id': 'b' * 32,
            'series_instance_uid': '1.2.3.4'
        })

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_remove_instance(self, handler, mock_client):
        """Test remove instance handler."""
        mock_client.remove_instance_from_image_set = AsyncMock(return_value={
            'latestVersionId': '2'
        })

        result = await handler.handle_tool('remove_instance_from_image_set', {
            'datastore_id': 'a' * 32,
            'image_set_id': 'b' * 32,
            'sop_instance_uid': '1.2.3.4.5'
        })

        assert len(result) == 1


class TestSearchHandlers:
    """Tests for enhanced search handlers."""

    @pytest.mark.asyncio
    async def test_handle_search_by_patient(self, handler, mock_client):
        """Test search by patient handler."""
        mock_client.search_by_patient_id = AsyncMock(return_value={
            'patientId': 'P123',
            'imageSetsMetadataSummaries': []
        })

        result = await handler.handle_tool('search_by_patient_id', {
            'datastore_id': 'a' * 32,
            'patient_id': 'P123'
        })

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_search_by_study(self, handler, mock_client):
        """Test search by study handler."""
        mock_client.search_by_study_uid = AsyncMock(return_value={
            'studyInstanceUID': '1.2.3',
            'imageSetsMetadataSummaries': []
        })

        result = await handler.handle_tool('search_by_study_uid', {
            'datastore_id': 'a' * 32,
            'study_instance_uid': '1.2.3'
        })

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_search_by_series(self, handler, mock_client):
        """Test search by series handler."""
        mock_client.search_by_series_uid = AsyncMock(return_value={
            'seriesInstanceUID': '1.2.3.4',
            'imageSetsMetadataSummaries': []
        })

        result = await handler.handle_tool('search_by_series_uid', {
            'datastore_id': 'a' * 32,
            'series_instance_uid': '1.2.3.4'
        })

        assert len(result) == 1


class TestDataAnalysisHandlers:
    """Tests for data analysis handlers."""

    @pytest.mark.asyncio
    async def test_handle_get_patient_studies(self, handler, mock_client):
        """Test get patient studies handler."""
        mock_client.get_patient_studies = AsyncMock(return_value={
            'patientId': 'P123',
            'studies': [],
            'totalStudies': 0
        })

        result = await handler.handle_tool('get_patient_studies', {
            'datastore_id': 'a' * 32,
            'patient_id': 'P123'
        })

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_get_patient_series(self, handler, mock_client):
        """Test get patient series handler."""
        mock_client.get_patient_series = AsyncMock(return_value={
            'patientId': 'P123',
            'seriesUIDs': [],
            'totalSeries': 0
        })

        result = await handler.handle_tool('get_patient_series', {
            'datastore_id': 'a' * 32,
            'patient_id': 'P123'
        })

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_get_study_primary_image_sets(self, handler, mock_client):
        """Test get study primary image sets handler."""
        mock_client.get_study_primary_image_sets = AsyncMock(return_value={
            'imageSetsMetadataSummaries': []
        })

        result = await handler.handle_tool('get_study_primary_image_sets', {
            'datastore_id': 'a' * 32,
            'study_instance_uid': '1.2.3'
        })

        assert len(result) == 1


class TestBulkOperationHandlers:
    """Tests for bulk operation handlers."""

    @pytest.mark.asyncio
    async def test_handle_bulk_update_patient_metadata(self, handler, mock_client):
        """Test bulk update patient metadata handler."""
        mock_client.bulk_update_patient_metadata = AsyncMock(return_value={
            'patientId': 'P123',
            'totalUpdated': 3
        })

        result = await handler.handle_tool('bulk_update_patient_metadata', {
            'datastore_id': 'a' * 32,
            'patient_id': 'P123',
            'new_metadata': {'PatientName': 'Test'}
        })

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_bulk_delete_by_criteria(self, handler, mock_client):
        """Test bulk delete by criteria handler."""
        mock_client.bulk_delete_by_criteria = AsyncMock(return_value={
            'totalDeleted': 5
        })

        result = await handler.handle_tool('bulk_delete_by_criteria', {
            'datastore_id': 'a' * 32,
            'search_criteria': {'filters': []}
        })

        assert len(result) == 1


class TestImageFrameAndVersionHandlers:
    """Tests for image frame and version handlers."""

    @pytest.mark.asyncio
    async def test_handle_get_image_frame(self, handler, mock_client):
        """Test get image frame handler."""
        mock_client.get_image_frame = AsyncMock(return_value={
            'imageFrameId': 'frame123',
            'message': 'Frame data available'
        })

        result = await handler.handle_tool('get_image_frame', {
            'datastore_id': 'a' * 32,
            'image_set_id': 'b' * 32,
            'image_frame_id': 'frame123'
        })

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_list_image_set_versions(self, handler, mock_client):
        """Test list image set versions handler."""
        mock_client.list_image_set_versions = AsyncMock(return_value={
            'imageSetPropertiesList': [{'versionId': '1'}]
        })

        result = await handler.handle_tool('list_image_set_versions', {
            'datastore_id': 'a' * 32,
            'image_set_id': 'b' * 32
        })

        assert len(result) == 1
