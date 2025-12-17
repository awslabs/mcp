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
from unittest.mock import MagicMock, patch, AsyncMock
from botocore.exceptions import ClientError, NoCredentialsError

from awslabs.healthimaging_mcp_server.healthimaging_operations import (
    HealthImagingClient,
    HealthImagingSearchError,
    validate_datastore_id,
)


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
        with patch('awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session') as mock_session:
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
        client.healthimaging_client.list_datastores.return_value = {
            'datastoreSummaries': []
        }

        result = await client.list_datastores(filter_status='ACTIVE')
        client.healthimaging_client.list_datastores.assert_called_with(
            maxResults=50, datastoreStatus='ACTIVE'
        )

    @pytest.mark.asyncio
    async def test_list_datastores_client_error(self, client):
        """Test listing datastores handles ClientError."""
        client.healthimaging_client.list_datastores.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            'ListDatastores'
        )

        with pytest.raises(ClientError):
            await client.list_datastores()


class TestGetDatastoreDetails:
    """Tests for get_datastore_details method."""

    @pytest.fixture
    def client(self):
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

    @pytest.mark.asyncio
    async def test_get_datastore_details_success(self, client):
        """Test getting datastore details successfully."""
        client.healthimaging_client.get_datastore.return_value = {
            'datastoreId': 'a' * 32,
            'datastoreName': 'test'
        }

        result = await client.get_datastore_details('a' * 32)
        assert result['datastoreId'] == 'a' * 32


class TestSearchImageSets:
    """Tests for search_image_sets method."""

    @pytest.fixture
    def client(self):
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
        with patch('awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session') as mock_session:
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
            'versionId': '1'
        }

        result = await client.get_image_set('a' * 32, 'b' * 32)
        assert result['imageSetId'] == 'b' * 32


class TestGetImageSetMetadata:
    """Tests for get_image_set_metadata method."""

    @pytest.fixture
    def client(self):
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

        result = await client.get_image_set_metadata('a' * 32, 'b' * 32, version_id='1')
        client.healthimaging_client.get_image_set_metadata.assert_called_with(
            datastoreId='a' * 32, imageSetId='b' * 32, versionId='1'
        )


class TestGetImageFrame:
    """Tests for get_image_frame method."""

    @pytest.fixture
    def client(self):
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
        with patch('awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session') as mock_session:
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
        with patch('awslabs.healthimaging_mcp_server.healthimaging_operations.boto3.Session') as mock_session:
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
            'imageSetState': 'DELETED'
        }

        result = await client.delete_image_set('a' * 32, 'b' * 32)
        assert result['imageSetState'] == 'DELETED'


class TestUpdateImageSetMetadata:
    """Tests for update_image_set_metadata method."""

    @pytest.fixture
    def client(self):
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

    @pytest.mark.asyncio
    async def test_update_image_set_metadata_success(self, client):
        """Test updating image set metadata successfully."""
        client.healthimaging_client.update_image_set_metadata.return_value = {
            'imageSetId': 'b' * 32,
            'latestVersionId': '2'
        }

        result = await client.update_image_set_metadata(
            'a' * 32, 'b' * 32, '1', {'DICOMUpdates': {}}
        )
        assert result['latestVersionId'] == '2'
