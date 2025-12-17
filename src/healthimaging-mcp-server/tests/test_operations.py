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

"""Tests for HealthImaging operations."""

import json
import pytest
from awslabs.healthimaging_mcp_server.healthimaging_operations import (
    HealthImagingClient,
    HealthImagingSearchError,
    validate_datastore_id,
)
from botocore.exceptions import ClientError, NoCredentialsError
from unittest.mock import MagicMock, patch


class TestHealthImagingClient:
    """Tests for HealthImagingClient class."""

    @patch('awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session')
    def test_client_initialization(self, mock_session):
        """Test client initializes correctly."""
        mock_session_instance = MagicMock()
        mock_session_instance.client.return_value = MagicMock()
        mock_session_instance.region_name = 'us-east-1'
        mock_session.return_value = mock_session_instance

        client = HealthImagingClient()
        assert client.region == 'us-east-1'

    @patch('awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session')
    def test_client_initialization_with_region(self, mock_session):
        """Test client initializes with specified region."""
        mock_session_instance = MagicMock()
        mock_session_instance.client.return_value = MagicMock()
        mock_session.return_value = mock_session_instance

        client = HealthImagingClient(region_name='us-west-2')
        assert client.region == 'us-west-2'

    @patch('awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session')
    def test_client_initialization_no_credentials(self, mock_session):
        """Test client raises error when no credentials."""
        mock_session.side_effect = NoCredentialsError()

        with pytest.raises(NoCredentialsError):
            HealthImagingClient()


class TestListDatastores:
    """Tests for list_datastores method."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked boto3."""
        with patch(
            'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
        ) as mock_session:
            mock_session_instance = MagicMock()
            mock_hi_client = MagicMock()
            mock_session_instance.client.return_value = mock_hi_client
            mock_session_instance.region_name = 'us-east-1'
            mock_session.return_value = mock_session_instance
            client = HealthImagingClient()
            client.healthimaging_client = mock_hi_client
            return client

    @pytest.mark.asyncio
    async def test_list_datastores_success(self, client):
        """Test listing datastores successfully."""
        client.healthimaging_client.list_datastores.return_value = {
            'datastoreSummaries': [{'datastoreId': 'a' * 32, 'datastoreName': 'test'}]
        }

        result = await client.list_datastores()
        assert 'datastoreSummaries' in result

    @pytest.mark.asyncio
    async def test_list_datastores_with_filter(self, client):
        """Test listing datastores with status filter."""
        client.healthimaging_client.list_datastores.return_value = {'datastoreSummaries': []}

        await client.list_datastores(filter_status='ACTIVE')
        client.healthimaging_client.list_datastores.assert_called_with(
            maxResults=50, datastoreStatus='ACTIVE'
        )

    @pytest.mark.asyncio
    async def test_list_datastores_client_error(self, client):
        """Test listing datastores handles ClientError."""
        client.healthimaging_client.list_datastores.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'ListDatastores'
        )

        with pytest.raises(ClientError):
            await client.list_datastores()


class TestGetDatastoreDetails:
    """Tests for get_datastore_details method."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked boto3."""
        with patch(
            'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
        ) as mock_session:
            mock_session_instance = MagicMock()
            mock_hi_client = MagicMock()
            mock_session_instance.client.return_value = mock_hi_client
            mock_session_instance.region_name = 'us-east-1'
            mock_session.return_value = mock_session_instance
            client = HealthImagingClient()
            client.healthimaging_client = mock_hi_client
            return client

    @pytest.mark.asyncio
    async def test_get_datastore_details_success(self, client):
        """Test getting datastore details successfully."""
        client.healthimaging_client.get_datastore.return_value = {
            'datastoreId': 'a' * 32,
            'datastoreName': 'test',
        }

        result = await client.get_datastore_details('a' * 32)
        assert result['datastoreId'] == 'a' * 32


class TestSearchImageSets:
    """Tests for search_image_sets method."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked boto3."""
        with patch(
            'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
        ) as mock_session:
            mock_session_instance = MagicMock()
            mock_hi_client = MagicMock()
            mock_session_instance.client.return_value = mock_hi_client
            mock_session_instance.region_name = 'us-east-1'
            mock_session.return_value = mock_session_instance
            client = HealthImagingClient()
            client.healthimaging_client = mock_hi_client
            return client

    @pytest.mark.asyncio
    async def test_search_image_sets_success(self, client):
        """Test searching image sets successfully."""
        client.healthimaging_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': []
        }

        result = await client.search_image_sets('a' * 32)
        assert 'imageSetsMetadataSummaries' in result

    @pytest.mark.asyncio
    async def test_search_image_sets_with_criteria(self, client):
        """Test searching image sets with criteria."""
        client.healthimaging_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': []
        }
        criteria = {'filters': [{'values': [{'DICOMPatientId': 'P123'}], 'operator': 'EQUAL'}]}

        result = await client.search_image_sets('a' * 32, search_criteria=criteria)
        assert 'imageSetsMetadataSummaries' in result


class TestGetImageSet:
    """Tests for get_image_set method."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked boto3."""
        with patch(
            'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
        ) as mock_session:
            mock_session_instance = MagicMock()
            mock_hi_client = MagicMock()
            mock_session_instance.client.return_value = mock_hi_client
            mock_session_instance.region_name = 'us-east-1'
            mock_session.return_value = mock_session_instance
            client = HealthImagingClient()
            client.healthimaging_client = mock_hi_client
            return client

    @pytest.mark.asyncio
    async def test_get_image_set_success(self, client):
        """Test getting image set successfully."""
        client.healthimaging_client.get_image_set.return_value = {
            'imageSetId': 'b' * 32,
            'versionId': '1',
        }

        result = await client.get_image_set('a' * 32, 'b' * 32)
        assert result['imageSetId'] == 'b' * 32


class TestGetImageSetMetadata:
    """Tests for get_image_set_metadata method."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked boto3."""
        with patch(
            'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
        ) as mock_session:
            mock_session_instance = MagicMock()
            mock_hi_client = MagicMock()
            mock_session_instance.client.return_value = mock_hi_client
            mock_session_instance.region_name = 'us-east-1'
            mock_session.return_value = mock_session_instance
            client = HealthImagingClient()
            client.healthimaging_client = mock_hi_client
            return client

    @pytest.mark.asyncio
    async def test_get_image_set_metadata_success(self, client):
        """Test getting image set metadata successfully."""
        mock_blob = MagicMock()
        mock_blob.read.return_value = b'{"Study": {}}'
        client.healthimaging_client.get_image_set_metadata.return_value = {
            'imageSetMetadataBlob': mock_blob
        }

        result = await client.get_image_set_metadata('a' * 32, 'b' * 32)
        assert result == '{"Study": {}}'

    @pytest.mark.asyncio
    async def test_get_image_set_metadata_with_version(self, client):
        """Test getting image set metadata with version."""
        mock_blob = MagicMock()
        mock_blob.read.return_value = b'{"Study": {}}'
        client.healthimaging_client.get_image_set_metadata.return_value = {
            'imageSetMetadataBlob': mock_blob
        }

        await client.get_image_set_metadata('a' * 32, 'b' * 32, version_id='1')
        client.healthimaging_client.get_image_set_metadata.assert_called_with(
            datastoreId='a' * 32, imageSetId='b' * 32, versionId='1'
        )


class TestGetImageFrame:
    """Tests for get_image_frame method."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked boto3."""
        with patch(
            'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
        ) as mock_session:
            mock_session_instance = MagicMock()
            mock_hi_client = MagicMock()
            mock_session_instance.client.return_value = mock_hi_client
            mock_session_instance.region_name = 'us-east-1'
            mock_session.return_value = mock_session_instance
            client = HealthImagingClient()
            client.healthimaging_client = mock_hi_client
            return client

    @pytest.mark.asyncio
    async def test_get_image_frame_success(self, client):
        """Test getting image frame successfully."""
        client.healthimaging_client.get_image_frame.return_value = {
            'contentType': 'application/octet-stream'
        }

        result = await client.get_image_frame('a' * 32, 'b' * 32, 'frame123')
        assert result['imageFrameId'] == 'frame123'
        assert 'message' in result


class TestListImageSetVersions:
    """Tests for list_image_set_versions method."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked boto3."""
        with patch(
            'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
        ) as mock_session:
            mock_session_instance = MagicMock()
            mock_hi_client = MagicMock()
            mock_session_instance.client.return_value = mock_hi_client
            mock_session_instance.region_name = 'us-east-1'
            mock_session.return_value = mock_session_instance
            client = HealthImagingClient()
            client.healthimaging_client = mock_hi_client
            return client

    @pytest.mark.asyncio
    async def test_list_image_set_versions_success(self, client):
        """Test listing image set versions successfully."""
        client.healthimaging_client.list_image_set_versions.return_value = {
            'imageSetPropertiesList': [{'versionId': '1'}]
        }

        result = await client.list_image_set_versions('a' * 32, 'b' * 32)
        assert 'imageSetPropertiesList' in result


class TestDeleteImageSet:
    """Tests for delete_image_set method."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked boto3."""
        with patch(
            'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
        ) as mock_session:
            mock_session_instance = MagicMock()
            mock_hi_client = MagicMock()
            mock_session_instance.client.return_value = mock_hi_client
            mock_session_instance.region_name = 'us-east-1'
            mock_session.return_value = mock_session_instance
            client = HealthImagingClient()
            client.healthimaging_client = mock_hi_client
            return client

    @pytest.mark.asyncio
    async def test_delete_image_set_success(self, client):
        """Test deleting image set successfully."""
        client.healthimaging_client.delete_image_set.return_value = {
            'imageSetId': 'b' * 32,
            'imageSetState': 'DELETED',
        }

        result = await client.delete_image_set('a' * 32, 'b' * 32)
        assert result['imageSetState'] == 'DELETED'


class TestUpdateImageSetMetadata:
    """Tests for update_image_set_metadata method."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked boto3."""
        with patch(
            'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
        ) as mock_session:
            mock_session_instance = MagicMock()
            mock_hi_client = MagicMock()
            mock_session_instance.client.return_value = mock_hi_client
            mock_session_instance.region_name = 'us-east-1'
            mock_session.return_value = mock_session_instance
            client = HealthImagingClient()
            client.healthimaging_client = mock_hi_client
            return client

    @pytest.mark.asyncio
    async def test_update_image_set_metadata_success(self, client):
        """Test updating image set metadata successfully."""
        client.healthimaging_client.update_image_set_metadata.return_value = {
            'imageSetId': 'b' * 32,
            'latestVersionId': '2',
        }

        result = await client.update_image_set_metadata(
            'a' * 32, 'b' * 32, '1', {'DICOMUpdates': {}}
        )
        assert result['latestVersionId'] == '2'


# Extended tests merged from test_operations_extended.py


@pytest.fixture
def client_fixture():
    """Create a client with mocked boto3 for extended tests."""
    with patch(
        'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
    ) as mock_session:
        mock_session_instance = MagicMock()
        mock_hi_client = MagicMock()
        mock_session_instance.client.return_value = mock_hi_client
        mock_session_instance.region_name = 'us-east-1'
        mock_session.return_value = mock_session_instance
        client = HealthImagingClient()
        client.healthimaging_client = mock_hi_client
        yield client


class TestDeletePatientStudies:
    """Tests for delete_patient_studies method."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked boto3."""
        with patch(
            'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
        ) as mock_session:
            mock_session_instance = MagicMock()
            mock_hi_client = MagicMock()
            mock_session_instance.client.return_value = mock_hi_client
            mock_session_instance.region_name = 'us-east-1'
            mock_session.return_value = mock_session_instance
            client = HealthImagingClient()
            client.healthimaging_client = mock_hi_client
            return client

    @pytest.mark.asyncio
    async def test_delete_patient_studies_success(self, client):
        """Test deleting patient studies successfully."""
        client.healthimaging_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [{'imageSetId': 'img1'}, {'imageSetId': 'img2'}]
        }
        client.healthimaging_client.delete_image_set.return_value = {'imageSetState': 'DELETED'}

        result = await client.delete_patient_studies('a' * 32, 'P123')
        assert result['totalDeleted'] == 2

    @pytest.mark.asyncio
    async def test_delete_patient_studies_partial_failure(self, client):
        """Test deleting patient studies with partial failure."""
        client.healthimaging_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [{'imageSetId': 'img1'}, {'imageSetId': 'img2'}]
        }
        client.healthimaging_client.delete_image_set.side_effect = [
            {'imageSetState': 'DELETED'},
            ClientError({'Error': {'Code': 'Error', 'Message': 'Failed'}}, 'DeleteImageSet'),
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

    @pytest.fixture
    def client(self):
        """Create a client with mocked boto3."""
        with patch(
            'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
        ) as mock_session:
            mock_session_instance = MagicMock()
            mock_hi_client = MagicMock()
            mock_session_instance.client.return_value = mock_hi_client
            mock_session_instance.region_name = 'us-east-1'
            mock_session.return_value = mock_session_instance
            client = HealthImagingClient()
            client.healthimaging_client = mock_hi_client
            return client

    @pytest.mark.asyncio
    async def test_delete_study_success(self, client):
        """Test deleting study successfully."""
        client.healthimaging_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [{'imageSetId': 'img1'}]
        }
        client.healthimaging_client.delete_image_set.return_value = {'imageSetState': 'DELETED'}

        result = await client.delete_study('a' * 32, '1.2.3')
        assert result['totalDeleted'] == 1


class TestRemoveSeriesFromImageSet:
    """Tests for remove_series_from_image_set method."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked boto3."""
        with patch(
            'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
        ) as mock_session:
            mock_session_instance = MagicMock()
            mock_hi_client = MagicMock()
            mock_session_instance.client.return_value = mock_hi_client
            mock_session_instance.region_name = 'us-east-1'
            mock_session.return_value = mock_session_instance
            client = HealthImagingClient()
            client.healthimaging_client = mock_hi_client
            return client

    @pytest.mark.asyncio
    async def test_remove_series_success(self, client):
        """Test removing series successfully."""
        client.healthimaging_client.get_image_set.return_value = {'versionId': '1'}
        client.healthimaging_client.update_image_set_metadata.return_value = {
            'latestVersionId': '2'
        }

        result = await client.remove_series_from_image_set('a' * 32, 'b' * 32, '1.2.3.4')
        assert result['latestVersionId'] == '2'


class TestRemoveInstanceFromImageSet:
    """Tests for remove_instance_from_image_set method."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked boto3."""
        with patch(
            'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
        ) as mock_session:
            mock_session_instance = MagicMock()
            mock_hi_client = MagicMock()
            mock_session_instance.client.return_value = mock_hi_client
            mock_session_instance.region_name = 'us-east-1'
            mock_session.return_value = mock_session_instance
            client = HealthImagingClient()
            client.healthimaging_client = mock_hi_client
            return client

    @pytest.mark.asyncio
    async def test_remove_instance_with_series_uid(self, client):
        """Test removing instance with series UID provided."""
        client.healthimaging_client.get_image_set.return_value = {'versionId': '1'}
        client.healthimaging_client.update_image_set_metadata.return_value = {
            'latestVersionId': '2'
        }

        result = await client.remove_instance_from_image_set(
            'a' * 32, 'b' * 32, '1.2.3.4.5', series_instance_uid='1.2.3.4'
        )
        assert result['latestVersionId'] == '2'


class TestSearchByPatientId:
    """Tests for search_by_patient_id method."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked boto3."""
        with patch(
            'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
        ) as mock_session:
            mock_session_instance = MagicMock()
            mock_hi_client = MagicMock()
            mock_session_instance.client.return_value = mock_hi_client
            mock_session_instance.region_name = 'us-east-1'
            mock_session.return_value = mock_session_instance
            client = HealthImagingClient()
            client.healthimaging_client = mock_hi_client
            return client

    @pytest.mark.asyncio
    async def test_search_by_patient_success(self, client):
        """Test searching by patient ID successfully."""
        client.healthimaging_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {
                    'imageSetId': 'img1',
                    'DICOMTags': {
                        'DICOMStudyInstanceUID': '1.2.3',
                        'DICOMSeriesInstanceUID': '1.2.3.4',
                    },
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
                {'imageSetId': 'img2', 'isPrimary': False, 'DICOMTags': {}},
            ]
        }

        result = await client.search_by_patient_id('a' * 32, 'P123', include_primary_only=True)
        assert len(result['imageSetsMetadataSummaries']) == 1


class TestSearchByStudyUid:
    """Tests for search_by_study_uid method."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked boto3."""
        with patch(
            'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
        ) as mock_session:
            mock_session_instance = MagicMock()
            mock_hi_client = MagicMock()
            mock_session_instance.client.return_value = mock_hi_client
            mock_session_instance.region_name = 'us-east-1'
            mock_session.return_value = mock_session_instance
            client = HealthImagingClient()
            client.healthimaging_client = mock_hi_client
            return client

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

    @pytest.fixture
    def client(self):
        """Create a client with mocked boto3."""
        with patch(
            'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
        ) as mock_session:
            mock_session_instance = MagicMock()
            mock_hi_client = MagicMock()
            mock_session_instance.client.return_value = mock_hi_client
            mock_session_instance.region_name = 'us-east-1'
            mock_session.return_value = mock_session_instance
            client = HealthImagingClient()
            client.healthimaging_client = mock_hi_client
            return client

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

    @pytest.fixture
    def client(self):
        """Create a client with mocked boto3."""
        with patch(
            'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
        ) as mock_session:
            mock_session_instance = MagicMock()
            mock_hi_client = MagicMock()
            mock_session_instance.client.return_value = mock_hi_client
            mock_session_instance.region_name = 'us-east-1'
            mock_session.return_value = mock_session_instance
            client = HealthImagingClient()
            client.healthimaging_client = mock_hi_client
            return client

    @pytest.mark.asyncio
    async def test_get_patient_studies_success(self, client):
        """Test getting patient studies successfully."""
        client.healthimaging_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {
                    'imageSetId': 'img1',
                    'isPrimary': True,
                    'DICOMTags': {'DICOMStudyInstanceUID': '1.2.3'},
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

    @pytest.fixture
    def client(self):
        """Create a client with mocked boto3."""
        with patch(
            'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
        ) as mock_session:
            mock_session_instance = MagicMock()
            mock_hi_client = MagicMock()
            mock_session_instance.client.return_value = mock_hi_client
            mock_session_instance.region_name = 'us-east-1'
            mock_session.return_value = mock_session_instance
            client = HealthImagingClient()
            client.healthimaging_client = mock_hi_client
            return client

    @pytest.mark.asyncio
    async def test_get_patient_series_success(self, client):
        """Test getting patient series successfully."""
        client.healthimaging_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {'imageSetId': 'img1', 'DICOMTags': {'DICOMSeriesInstanceUID': '1.2.3.4'}}
            ]
        }

        result = await client.get_patient_series('a' * 32, 'P123')
        assert 'seriesUIDs' in result


class TestGetStudyPrimaryImageSets:
    """Tests for get_study_primary_image_sets method."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked boto3."""
        with patch(
            'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
        ) as mock_session:
            mock_session_instance = MagicMock()
            mock_hi_client = MagicMock()
            mock_session_instance.client.return_value = mock_hi_client
            mock_session_instance.region_name = 'us-east-1'
            mock_session.return_value = mock_session_instance
            client = HealthImagingClient()
            client.healthimaging_client = mock_hi_client
            return client

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

    @pytest.fixture
    def client(self):
        """Create a client with mocked boto3."""
        with patch(
            'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
        ) as mock_session:
            mock_session_instance = MagicMock()
            mock_hi_client = MagicMock()
            mock_session_instance.client.return_value = mock_hi_client
            mock_session_instance.region_name = 'us-east-1'
            mock_session.return_value = mock_session_instance
            client = HealthImagingClient()
            client.healthimaging_client = mock_hi_client
            return client

    @pytest.mark.asyncio
    async def test_bulk_update_success(self, client):
        """Test bulk updating patient metadata successfully."""
        client.healthimaging_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [{'imageSetId': 'img1', 'DICOMTags': {}}]
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

    @pytest.fixture
    def client(self):
        """Create a client with mocked boto3."""
        with patch(
            'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
        ) as mock_session:
            mock_session_instance = MagicMock()
            mock_hi_client = MagicMock()
            mock_session_instance.client.return_value = mock_hi_client
            mock_session_instance.region_name = 'us-east-1'
            mock_session.return_value = mock_session_instance
            client = HealthImagingClient()
            client.healthimaging_client = mock_hi_client
            return client

    @pytest.mark.asyncio
    async def test_bulk_delete_success(self, client):
        """Test bulk deleting by criteria successfully."""
        client.healthimaging_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [{'imageSetId': 'img1'}]
        }
        client.healthimaging_client.delete_image_set.return_value = {'imageSetState': 'DELETED'}

        result = await client.bulk_delete_by_criteria('a' * 32, {'filters': []})
        assert result['totalDeleted'] == 1


class TestDeleteStudyPartialFailure:
    """Tests for delete_study with partial failures."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked boto3."""
        with patch(
            'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
        ) as mock_session:
            mock_session_instance = MagicMock()
            mock_hi_client = MagicMock()
            mock_session_instance.client.return_value = mock_hi_client
            mock_session_instance.region_name = 'us-east-1'
            mock_session.return_value = mock_session_instance
            client = HealthImagingClient()
            client.healthimaging_client = mock_hi_client
            return client

    @pytest.mark.asyncio
    async def test_delete_study_partial_failure(self, client):
        """Test deleting study with partial failure."""
        client.healthimaging_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [{'imageSetId': 'img1'}, {'imageSetId': 'img2'}]
        }
        client.healthimaging_client.delete_image_set.side_effect = [
            {'imageSetState': 'DELETED'},
            ClientError({'Error': {'Code': 'Error', 'Message': 'Failed'}}, 'DeleteImageSet'),
        ]

        result = await client.delete_study('a' * 32, '1.2.3')
        assert result['totalDeleted'] == 1

    @pytest.mark.asyncio
    async def test_delete_study_no_results(self, client):
        """Test deleting study with no results."""
        client.healthimaging_client.search_image_sets.return_value = {}

        result = await client.delete_study('a' * 32, '1.2.3')
        assert result['totalDeleted'] == 0


class TestRemoveInstanceWithoutSeriesUid:
    """Tests for remove_instance_from_image_set without series UID."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked boto3."""
        with patch(
            'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
        ) as mock_session:
            mock_session_instance = MagicMock()
            mock_hi_client = MagicMock()
            mock_session_instance.client.return_value = mock_hi_client
            mock_session_instance.region_name = 'us-east-1'
            mock_session.return_value = mock_session_instance
            client = HealthImagingClient()
            client.healthimaging_client = mock_hi_client
            return client

    @pytest.mark.asyncio
    async def test_remove_instance_not_found(self, client):
        """Test removing instance when series not found raises error."""
        client.healthimaging_client.get_image_set.return_value = {'versionId': '1'}
        mock_blob = MagicMock()
        mock_blob.read.return_value = b'{"Study": {"DICOM": {"StudyInstanceUID": {}}}}'
        client.healthimaging_client.get_image_set_metadata.return_value = {
            'imageSetMetadataBlob': mock_blob
        }

        with pytest.raises(ValueError, match='Could not find series'):
            await client.remove_instance_from_image_set('a' * 32, 'b' * 32, '1.2.3.4.5')


class TestBulkUpdatePartialFailure:
    """Tests for bulk_update_patient_metadata with partial failures."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked boto3."""
        with patch(
            'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
        ) as mock_session:
            mock_session_instance = MagicMock()
            mock_hi_client = MagicMock()
            mock_session_instance.client.return_value = mock_hi_client
            mock_session_instance.region_name = 'us-east-1'
            mock_session.return_value = mock_session_instance
            client = HealthImagingClient()
            client.healthimaging_client = mock_hi_client
            return client

    @pytest.mark.asyncio
    async def test_bulk_update_partial_failure(self, client):
        """Test bulk update with partial failure."""
        client.healthimaging_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {'imageSetId': 'img1', 'DICOMTags': {}},
                {'imageSetId': 'img2', 'DICOMTags': {}},
            ]
        }
        client.healthimaging_client.get_image_set.return_value = {'versionId': '1'}
        client.healthimaging_client.update_image_set_metadata.side_effect = [
            {'latestVersionId': '2'},
            ClientError(
                {'Error': {'Code': 'Error', 'Message': 'Failed'}}, 'UpdateImageSetMetadata'
            ),
        ]

        result = await client.bulk_update_patient_metadata(
            'a' * 32, 'P123', {'PatientName': 'Test'}
        )
        assert result['totalUpdated'] == 1

    @pytest.mark.asyncio
    async def test_bulk_update_no_results(self, client):
        """Test bulk update with no results."""
        client.healthimaging_client.search_image_sets.return_value = {}

        result = await client.bulk_update_patient_metadata(
            'a' * 32, 'P123', {'PatientName': 'Test'}
        )
        assert result['totalUpdated'] == 0


class TestBulkDeletePartialFailure:
    """Tests for bulk_delete_by_criteria with partial failures."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked boto3."""
        with patch(
            'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
        ) as mock_session:
            mock_session_instance = MagicMock()
            mock_hi_client = MagicMock()
            mock_session_instance.client.return_value = mock_hi_client
            mock_session_instance.region_name = 'us-east-1'
            mock_session.return_value = mock_session_instance
            client = HealthImagingClient()
            client.healthimaging_client = mock_hi_client
            return client

    @pytest.mark.asyncio
    async def test_bulk_delete_partial_failure(self, client):
        """Test bulk delete with partial failure."""
        client.healthimaging_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [{'imageSetId': 'img1'}, {'imageSetId': 'img2'}]
        }
        client.healthimaging_client.delete_image_set.side_effect = [
            {'imageSetState': 'DELETED'},
            ClientError({'Error': {'Code': 'Error', 'Message': 'Failed'}}, 'DeleteImageSet'),
        ]

        result = await client.bulk_delete_by_criteria('a' * 32, {'filters': []})
        assert result['totalDeleted'] == 1

    @pytest.mark.asyncio
    async def test_bulk_delete_no_results(self, client):
        """Test bulk delete with no results."""
        client.healthimaging_client.search_image_sets.return_value = {}

        result = await client.bulk_delete_by_criteria('a' * 32, {'filters': []})
        assert result['totalDeleted'] == 0


class TestGetPatientStudiesMetadataError:
    """Tests for get_patient_studies with metadata errors."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked boto3."""
        with patch(
            'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
        ) as mock_session:
            mock_session_instance = MagicMock()
            mock_hi_client = MagicMock()
            mock_session_instance.client.return_value = mock_hi_client
            mock_session_instance.region_name = 'us-east-1'
            mock_session.return_value = mock_session_instance
            client = HealthImagingClient()
            client.healthimaging_client = mock_hi_client
            return client

    @pytest.mark.asyncio
    async def test_get_patient_studies_metadata_error(self, client):
        """Test getting patient studies handles metadata errors gracefully."""
        client.healthimaging_client.search_image_sets.return_value = {
            'imageSetsMetadataSummaries': [
                {
                    'imageSetId': 'img1',
                    'isPrimary': True,
                    'DICOMTags': {'DICOMStudyInstanceUID': '1.2.3'},
                }
            ]
        }
        client.healthimaging_client.get_image_set_metadata.side_effect = Exception(
            'Metadata error'
        )

        result = await client.get_patient_studies('a' * 32, 'P123')
        assert 'studies' in result
        assert result['totalStudies'] == 0


class TestRemoveInstanceFindSeriesFromMetadata:
    """Tests for remove_instance_from_image_set finding series from metadata."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked boto3."""
        with patch(
            'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
        ) as mock_session:
            mock_session_instance = MagicMock()
            mock_hi_client = MagicMock()
            mock_session_instance.client.return_value = mock_hi_client
            mock_session_instance.region_name = 'us-east-1'
            mock_session.return_value = mock_session_instance
            client = HealthImagingClient()
            client.healthimaging_client = mock_hi_client
            return client

    @pytest.mark.asyncio
    async def test_remove_instance_finds_series_from_metadata(self, client):
        """Test removing instance finds series UID from metadata when not provided."""
        client.healthimaging_client.get_image_set.return_value = {'versionId': '1'}

        # Create metadata with nested structure that contains the SOP instance
        metadata = {
            'Study': {
                'DICOM': {
                    'StudyInstanceUID': {
                        '1.2.3': {'Series': {'1.2.3.4': {'Instances': {'1.2.3.4.5': {}}}}}
                    }
                }
            }
        }
        mock_blob = MagicMock()
        mock_blob.read.return_value = json.dumps(metadata).encode()
        client.healthimaging_client.get_image_set_metadata.return_value = {
            'imageSetMetadataBlob': mock_blob
        }
        client.healthimaging_client.update_image_set_metadata.return_value = {
            'latestVersionId': '2'
        }

        result = await client.remove_instance_from_image_set('a' * 32, 'b' * 32, '1.2.3.4.5')
        assert result['latestVersionId'] == '2'

    @pytest.mark.asyncio
    async def test_remove_instance_series_not_found_in_metadata(self, client):
        """Test removing instance raises error when series not found in metadata."""
        client.healthimaging_client.get_image_set.return_value = {'versionId': '1'}

        # Create metadata without the SOP instance
        metadata = {
            'Study': {
                'DICOM': {
                    'StudyInstanceUID': {
                        '1.2.3': {'Series': {'1.2.3.4': {'Instances': {'different_sop': {}}}}}
                    }
                }
            }
        }
        mock_blob = MagicMock()
        mock_blob.read.return_value = json.dumps(metadata).encode()
        client.healthimaging_client.get_image_set_metadata.return_value = {
            'imageSetMetadataBlob': mock_blob
        }

        with pytest.raises(ValueError, match='Could not find series'):
            await client.remove_instance_from_image_set('a' * 32, 'b' * 32, '1.2.3.4.5')

    @pytest.mark.asyncio
    async def test_remove_instance_empty_metadata(self, client):
        """Test removing instance with empty metadata structure."""
        client.healthimaging_client.get_image_set.return_value = {'versionId': '1'}

        metadata = {'Study': {}}
        mock_blob = MagicMock()
        mock_blob.read.return_value = json.dumps(metadata).encode()
        client.healthimaging_client.get_image_set_metadata.return_value = {
            'imageSetMetadataBlob': mock_blob
        }

        with pytest.raises(ValueError, match='Could not find series'):
            await client.remove_instance_from_image_set('a' * 32, 'b' * 32, '1.2.3.4.5')


class TestClientErrorHandling:
    """Tests for ClientError handling in various operations."""

    @pytest.fixture
    def client(self):
        """Create a client with mocked boto3."""
        with patch(
            'awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session'
        ) as mock_session:
            mock_session_instance = MagicMock()
            mock_hi_client = MagicMock()
            mock_session_instance.client.return_value = mock_hi_client
            mock_session_instance.region_name = 'us-east-1'
            mock_session.return_value = mock_session_instance
            client = HealthImagingClient()
            client.healthimaging_client = mock_hi_client
            return client

    @pytest.mark.asyncio
    async def test_get_datastore_details_client_error(self, client):
        """Test get_datastore_details handles ClientError."""
        client.healthimaging_client.get_datastore.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}},
            'GetDatastore',
        )

        with pytest.raises(ClientError):
            await client.get_datastore_details('a' * 32)

    @pytest.mark.asyncio
    async def test_search_image_sets_client_error(self, client):
        """Test search_image_sets handles ClientError."""
        client.healthimaging_client.search_image_sets.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid'}}, 'SearchImageSets'
        )

        with pytest.raises(ClientError):
            await client.search_image_sets('a' * 32)

    @pytest.mark.asyncio
    async def test_get_image_set_client_error(self, client):
        """Test get_image_set handles ClientError."""
        client.healthimaging_client.get_image_set.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}}, 'GetImageSet'
        )

        with pytest.raises(ClientError):
            await client.get_image_set('a' * 32, 'b' * 32)

    @pytest.mark.asyncio
    async def test_get_image_set_metadata_client_error(self, client):
        """Test get_image_set_metadata handles ClientError."""
        client.healthimaging_client.get_image_set_metadata.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}},
            'GetImageSetMetadata',
        )

        with pytest.raises(ClientError):
            await client.get_image_set_metadata('a' * 32, 'b' * 32)

    @pytest.mark.asyncio
    async def test_get_image_frame_client_error(self, client):
        """Test get_image_frame handles ClientError."""
        client.healthimaging_client.get_image_frame.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}},
            'GetImageFrame',
        )

        with pytest.raises(ClientError):
            await client.get_image_frame('a' * 32, 'b' * 32, 'frame1')

    @pytest.mark.asyncio
    async def test_list_image_set_versions_client_error(self, client):
        """Test list_image_set_versions handles ClientError."""
        client.healthimaging_client.list_image_set_versions.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}},
            'ListImageSetVersions',
        )

        with pytest.raises(ClientError):
            await client.list_image_set_versions('a' * 32, 'b' * 32)

    @pytest.mark.asyncio
    async def test_delete_image_set_client_error(self, client):
        """Test delete_image_set handles ClientError."""
        client.healthimaging_client.delete_image_set.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}},
            'DeleteImageSet',
        )

        with pytest.raises(ClientError):
            await client.delete_image_set('a' * 32, 'b' * 32)

    @pytest.mark.asyncio
    async def test_delete_patient_studies_client_error(self, client):
        """Test delete_patient_studies handles ClientError on search."""
        client.healthimaging_client.search_image_sets.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'SearchImageSets'
        )

        with pytest.raises(ClientError):
            await client.delete_patient_studies('a' * 32, 'P123')

    @pytest.mark.asyncio
    async def test_delete_study_client_error(self, client):
        """Test delete_study handles ClientError on search."""
        client.healthimaging_client.search_image_sets.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'SearchImageSets'
        )

        with pytest.raises(ClientError):
            await client.delete_study('a' * 32, '1.2.3')

    @pytest.mark.asyncio
    async def test_update_image_set_metadata_client_error(self, client):
        """Test update_image_set_metadata handles ClientError."""
        client.healthimaging_client.update_image_set_metadata.side_effect = ClientError(
            {'Error': {'Code': 'ConflictException', 'Message': 'Conflict'}},
            'UpdateImageSetMetadata',
        )

        with pytest.raises(ClientError):
            await client.update_image_set_metadata('a' * 32, 'b' * 32, '1', {})

    @pytest.mark.asyncio
    async def test_remove_series_client_error(self, client):
        """Test remove_series_from_image_set handles ClientError."""
        client.healthimaging_client.get_image_set.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}}, 'GetImageSet'
        )

        with pytest.raises(ClientError):
            await client.remove_series_from_image_set('a' * 32, 'b' * 32, '1.2.3.4')

    @pytest.mark.asyncio
    async def test_remove_instance_client_error(self, client):
        """Test remove_instance_from_image_set handles ClientError."""
        client.healthimaging_client.get_image_set.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}}, 'GetImageSet'
        )

        with pytest.raises(ClientError):
            await client.remove_instance_from_image_set('a' * 32, 'b' * 32, '1.2.3.4.5', '1.2.3.4')

    @pytest.mark.asyncio
    async def test_search_by_patient_client_error(self, client):
        """Test search_by_patient_id handles ClientError."""
        client.healthimaging_client.search_image_sets.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'SearchImageSets'
        )

        with pytest.raises(ClientError):
            await client.search_by_patient_id('a' * 32, 'P123')

    @pytest.mark.asyncio
    async def test_search_by_study_client_error(self, client):
        """Test search_by_study_uid handles ClientError."""
        client.healthimaging_client.search_image_sets.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'SearchImageSets'
        )

        with pytest.raises(ClientError):
            await client.search_by_study_uid('a' * 32, '1.2.3')

    @pytest.mark.asyncio
    async def test_search_by_series_client_error(self, client):
        """Test search_by_series_uid handles ClientError."""
        client.healthimaging_client.search_image_sets.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'SearchImageSets'
        )

        with pytest.raises(ClientError):
            await client.search_by_series_uid('a' * 32, '1.2.3.4')

    @pytest.mark.asyncio
    async def test_get_patient_studies_client_error(self, client):
        """Test get_patient_studies handles ClientError."""
        client.healthimaging_client.search_image_sets.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'SearchImageSets'
        )

        with pytest.raises(ClientError):
            await client.get_patient_studies('a' * 32, 'P123')

    @pytest.mark.asyncio
    async def test_get_patient_series_client_error(self, client):
        """Test get_patient_series handles ClientError."""
        client.healthimaging_client.search_image_sets.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'SearchImageSets'
        )

        with pytest.raises(ClientError):
            await client.get_patient_series('a' * 32, 'P123')

    @pytest.mark.asyncio
    async def test_get_study_primary_image_sets_client_error(self, client):
        """Test get_study_primary_image_sets handles ClientError."""
        client.healthimaging_client.search_image_sets.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'SearchImageSets'
        )

        with pytest.raises(ClientError):
            await client.get_study_primary_image_sets('a' * 32, '1.2.3')

    @pytest.mark.asyncio
    async def test_bulk_update_patient_metadata_client_error(self, client):
        """Test bulk_update_patient_metadata handles ClientError on search."""
        client.healthimaging_client.search_image_sets.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'SearchImageSets'
        )

        with pytest.raises(ClientError):
            await client.bulk_update_patient_metadata('a' * 32, 'P123', {})

    @pytest.mark.asyncio
    async def test_bulk_delete_by_criteria_client_error(self, client):
        """Test bulk_delete_by_criteria handles ClientError on search."""
        client.healthimaging_client.search_image_sets.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'SearchImageSets'
        )

        with pytest.raises(ClientError):
            await client.bulk_delete_by_criteria('a' * 32, {})


class TestValidateDatastoreId:
    """Tests for validate_datastore_id function."""

    def test_valid_datastore_id(self):
        """Test valid datastore ID."""
        result = validate_datastore_id('a' * 32)
        assert result == 'a' * 32

    def test_invalid_datastore_id_too_short(self):
        """Test invalid datastore ID that is too short."""
        with pytest.raises(ValueError, match='must be 32 characters'):
            validate_datastore_id('short')

    def test_invalid_datastore_id_too_long(self):
        """Test invalid datastore ID that is too long."""
        with pytest.raises(ValueError, match='must be 32 characters'):
            validate_datastore_id('a' * 33)

    def test_invalid_datastore_id_empty(self):
        """Test invalid empty datastore ID."""
        with pytest.raises(ValueError, match='must be 32 characters'):
            validate_datastore_id('')


class TestHealthImagingSearchError:
    """Tests for HealthImagingSearchError exception."""

    def test_search_error_with_params(self):
        """Test HealthImagingSearchError with invalid params."""
        error = HealthImagingSearchError('Test error', ['param1', 'param2'])
        assert str(error) == 'Test error'
        assert error.invalid_params == ['param1', 'param2']

    def test_search_error_without_params(self):
        """Test HealthImagingSearchError without invalid params."""
        error = HealthImagingSearchError('Test error')
        assert str(error) == 'Test error'
        assert error.invalid_params == []


class TestClientDefaultRegion:
    """Tests for client region handling."""

    @patch('awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session')
    def test_client_default_region_fallback(self, mock_session):
        """Test client falls back to us-east-1 when no region specified."""
        mock_session_instance = MagicMock()
        mock_session_instance.client.return_value = MagicMock()
        mock_session_instance.region_name = None
        mock_session.return_value = mock_session_instance

        client = HealthImagingClient()
        assert client.region == 'us-east-1'
