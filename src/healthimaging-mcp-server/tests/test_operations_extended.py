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

"""Extended tests for HealthImaging operations."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from botocore.exceptions import ClientError

from awslabs.healthimaging_mcp_server.healthimaging_operations import HealthImagingClient


@pytest.fixture
def client():
    """Create a client with mocked boto3."""
    with patch('awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session') as mock_session:
        mock_session_instance = MagicMock()
        mock_hi_client = MagicMock()
        mock_session_instance.client.return_value = mock_hi_client
        mock_session_instance.region_name = 'us-east-1'
        mock_session.return_value = mock_session_instance
        client = HealthImagingClient()
        client.healthimaging_client = mock_hi_client
        return client


class TestDeletePatientStudies:
    """Tests for delete_patient_studies method."""

    @pytest.mark.asyncio
    async def test_delete_patient_studies_success(self, client):
        """Test deleting patient studies successfully."""
        client.healthimaging_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {'imageSetId': 'img1'},
                {'imageSetId': 'img2'}
            ]
        }
        client.healthimaging_client.delete_image_set.return_value = {
            'imageSetState': 'DELETED'
        }

        result = await client.delete_patient_studies('a' * 32, 'P123')

        assert result['totalDeleted'] == 2

    @pytest.mark.asyncio
    async def test_delete_patient_studies_partial_failure(self, client):
        """Test deleting patient studies with partial failure."""
        client.healthimaging_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {'imageSetId': 'img1'},
                {'imageSetId': 'img2'}
            ]
        }
        client.healthimaging_client.delete_image_set.side_effect = [
            {'imageSetState': 'DELETED'},
            ClientError({'Error': {'Code': 'Error', 'Message': 'Failed'}}, 'DeleteImageSet')
        ]

        result = await client.delete_patient_studies('a' * 32, 'P123')

        assert result['totalDeleted'] == 1

    @pytest.mark.asyncio
    async def test_delete_patient_studies_no_results(self, client):
        """Test deleting patient studies with no results."""
        client.healthimaging_client.search_image_sets.return_value = {}

        result = await client.delete_patient_studies('a' * 32, 'P123')

        assert result['totalDeleted'] == 0


class TestDeleteStudy:
    """Tests for delete_study method."""

    @pytest.mark.asyncio
    async def test_delete_study_success(self, client):
        """Test deleting study successfully."""
        client.healthimaging_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [{'imageSetId': 'img1'}]
        }
        client.healthimaging_client.delete_image_set.return_value = {
            'imageSetState': 'DELETED'
        }

        result = await client.delete_study('a' * 32, '1.2.3')

        assert result['totalDeleted'] == 1


class TestRemoveSeriesFromImageSet:
    """Tests for remove_series_from_image_set method."""

    @pytest.mark.asyncio
    async def test_remove_series_success(self, client):
        """Test removing series successfully."""
        client.healthimaging_client.get_image_set.return_value = {
            'versionId': '1'
        }
        client.healthimaging_client.update_image_set_metadata.return_value = {
            'latestVersionId': '2'
        }

        result = await client.remove_series_from_image_set('a' * 32, 'b' * 32, '1.2.3.4')

        assert result['latestVersionId'] == '2'


class TestRemoveInstanceFromImageSet:
    """Tests for remove_instance_from_image_set method."""

    @pytest.mark.asyncio
    async def test_remove_instance_with_series_uid(self, client):
        """Test removing instance with series UID provided."""
        client.healthimaging_client.get_image_set.return_value = {
            'versionId': '1'
        }
        client.healthimaging_client.update_image_set_metadata.return_value = {
            'latestVersionId': '2'
        }

        result = await client.remove_instance_from_image_set(
            'a' * 32, 'b' * 32, '1.2.3.4.5', series_instance_uid='1.2.3.4'
        )

        assert result['latestVersionId'] == '2'


class TestSearchByPatientId:
    """Tests for search_by_patient_id method."""

    @pytest.mark.asyncio
    async def test_search_by_patient_success(self, client):
        """Test searching by patient ID successfully."""
        client.healthimaging_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {
                    'imageSetId': 'img1',
                    'DICOMTags': {
                        'DICOMStudyInstanceUID': '1.2.3',
                        'DICOMSeriesInstanceUID': '1.2.3.4'
                    }
                }
            ]
        }

        result = await client.search_by_patient_id('a' * 32, 'P123')

        assert 'uniqueStudyUIDs' in result
        assert 'uniqueSeriesUIDs' in result

    @pytest.mark.asyncio
    async def test_search_by_patient_primary_only(self, client):
        """Test searching by patient ID with primary only filter."""
        client.healthimaging_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {'imageSetId': 'img1', 'isPrimary': True, 'DICOMTags': {}},
                {'imageSetId': 'img2', 'isPrimary': False, 'DICOMTags': {}}
            ]
        }

        result = await client.search_by_patient_id('a' * 32, 'P123', include_primary_only=True)

        assert len(result['imageSetsMetadataSummaries']) == 1


class TestSearchByStudyUid:
    """Tests for search_by_study_uid method."""

    @pytest.mark.asyncio
    async def test_search_by_study_success(self, client):
        """Test searching by study UID successfully."""
        client.healthimaging_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': []
        }

        result = await client.search_by_study_uid('a' * 32, '1.2.3')

        assert result['studyInstanceUID'] == '1.2.3'


class TestSearchBySeriesUid:
    """Tests for search_by_series_uid method."""

    @pytest.mark.asyncio
    async def test_search_by_series_success(self, client):
        """Test searching by series UID successfully."""
        client.healthimaging_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': []
        }

        result = await client.search_by_series_uid('a' * 32, '1.2.3.4')

        assert result['seriesInstanceUID'] == '1.2.3.4'


class TestGetPatientStudies:
    """Tests for get_patient_studies method."""

    @pytest.mark.asyncio
    async def test_get_patient_studies_success(self, client):
        """Test getting patient studies successfully."""
        client.healthimaging_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {
                    'imageSetId': 'img1',
                    'isPrimary': True,
                    'DICOMTags': {'DICOMStudyInstanceUID': '1.2.3'}
                }
            ]
        }
        mock_blob = MagicMock()
        mock_blob.read.return_value = b'{"Patient": {}, "Study": {}}'
        client.healthimaging_client.get_image_set_metadata.return_value = {
            'imageSetMetadataBlob': mock_blob
        }

        result = await client.get_patient_studies('a' * 32, 'P123')

        assert 'studies' in result


class TestGetPatientSeries:
    """Tests for get_patient_series method."""

    @pytest.mark.asyncio
    async def test_get_patient_series_success(self, client):
        """Test getting patient series successfully."""
        client.healthimaging_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {
                    'imageSetId': 'img1',
                    'DICOMTags': {'DICOMSeriesInstanceUID': '1.2.3.4'}
                }
            ]
        }

        result = await client.get_patient_series('a' * 32, 'P123')

        assert 'seriesUIDs' in result


class TestGetStudyPrimaryImageSets:
    """Tests for get_study_primary_image_sets method."""

    @pytest.mark.asyncio
    async def test_get_study_primary_image_sets_success(self, client):
        """Test getting study primary image sets successfully."""
        client.healthimaging_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {'imageSetId': 'img1', 'isPrimary': True, 'DICOMTags': {}}
            ]
        }

        result = await client.get_study_primary_image_sets('a' * 32, '1.2.3')

        assert 'imageSetsMetadataSummaries' in result


class TestBulkUpdatePatientMetadata:
    """Tests for bulk_update_patient_metadata method."""

    @pytest.mark.asyncio
    async def test_bulk_update_success(self, client):
        """Test bulk updating patient metadata successfully."""
        client.healthimaging_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {'imageSetId': 'img1', 'DICOMTags': {}}
            ]
        }
        client.healthimaging_client.get_image_set.return_value = {'versionId': '1'}
        client.healthimaging_client.update_image_set_metadata.return_value = {
            'latestVersionId': '2'
        }

        result = await client.bulk_update_patient_metadata(
            'a' * 32, 'P123', {'PatientName': 'Test'}
        )

        assert result['totalUpdated'] == 1


class TestBulkDeleteByCriteria:
    """Tests for bulk_delete_by_criteria method."""

    @pytest.mark.asyncio
    async def test_bulk_delete_success(self, client):
        """Test bulk deleting by criteria successfully."""
        client.healthimaging_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [{'imageSetId': 'img1'}]
        }
        client.healthimaging_client.delete_image_set.return_value = {
            'imageSetState': 'DELETED'
        }

        result = await client.bulk_delete_by_criteria('a' * 32, {'filters': []})

        assert result['totalDeleted'] == 1
