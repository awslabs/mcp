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

"""Tests for error handling in operations."""

import pytest
from awslabs.healthimaging_mcp_server.healthimaging_operations import HealthImagingClient
from botocore.exceptions import ClientError
from unittest.mock import MagicMock, patch


@pytest.fixture
def client():
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


class TestClientErrors:
    """Tests for ClientError handling."""

    @pytest.mark.asyncio
    async def test_get_datastore_details_error(self, client):
        """Test get_datastore_details handles ClientError."""
        client.healthimaging_client.get_datastore.side_effect = ClientError(
            {'Error': {'Code': 'NotFound', 'Message': 'Not found'}}, 'GetDatastore'
        )

        with pytest.raises(ClientError):
            await client.get_datastore_details('a' * 32)

    @pytest.mark.asyncio
    async def test_search_image_sets_error(self, client):
        """Test search_image_sets handles ClientError."""
        client.healthimaging_client.search_image_sets.side_effect = ClientError(
            {'Error': {'Code': 'Error', 'Message': 'Error'}}, 'SearchImageSets'
        )

        with pytest.raises(ClientError):
            await client.search_image_sets('a' * 32)

    @pytest.mark.asyncio
    async def test_get_image_set_error(self, client):
        """Test get_image_set handles ClientError."""
        client.healthimaging_client.get_image_set.side_effect = ClientError(
            {'Error': {'Code': 'Error', 'Message': 'Error'}}, 'GetImageSet'
        )

        with pytest.raises(ClientError):
            await client.get_image_set('a' * 32, 'b' * 32)

    @pytest.mark.asyncio
    async def test_get_image_set_metadata_error(self, client):
        """Test get_image_set_metadata handles ClientError."""
        client.healthimaging_client.get_image_set_metadata.side_effect = ClientError(
            {'Error': {'Code': 'Error', 'Message': 'Error'}}, 'GetImageSetMetadata'
        )

        with pytest.raises(ClientError):
            await client.get_image_set_metadata('a' * 32, 'b' * 32)

    @pytest.mark.asyncio
    async def test_get_image_frame_error(self, client):
        """Test get_image_frame handles ClientError."""
        client.healthimaging_client.get_image_frame.side_effect = ClientError(
            {'Error': {'Code': 'Error', 'Message': 'Error'}}, 'GetImageFrame'
        )

        with pytest.raises(ClientError):
            await client.get_image_frame('a' * 32, 'b' * 32, 'frame123')

    @pytest.mark.asyncio
    async def test_list_image_set_versions_error(self, client):
        """Test list_image_set_versions handles ClientError."""
        client.healthimaging_client.list_image_set_versions.side_effect = ClientError(
            {'Error': {'Code': 'Error', 'Message': 'Error'}}, 'ListImageSetVersions'
        )

        with pytest.raises(ClientError):
            await client.list_image_set_versions('a' * 32, 'b' * 32)

    @pytest.mark.asyncio
    async def test_delete_image_set_error(self, client):
        """Test delete_image_set handles ClientError."""
        client.healthimaging_client.delete_image_set.side_effect = ClientError(
            {'Error': {'Code': 'Error', 'Message': 'Error'}}, 'DeleteImageSet'
        )

        with pytest.raises(ClientError):
            await client.delete_image_set('a' * 32, 'b' * 32)

    @pytest.mark.asyncio
    async def test_delete_patient_studies_error(self, client):
        """Test delete_patient_studies handles ClientError on search."""
        client.healthimaging_client.search_image_sets.side_effect = ClientError(
            {'Error': {'Code': 'Error', 'Message': 'Error'}}, 'SearchImageSets'
        )

        with pytest.raises(ClientError):
            await client.delete_patient_studies('a' * 32, 'P123')

    @pytest.mark.asyncio
    async def test_delete_study_error(self, client):
        """Test delete_study handles ClientError."""
        client.healthimaging_client.search_image_sets.side_effect = ClientError(
            {'Error': {'Code': 'Error', 'Message': 'Error'}}, 'SearchImageSets'
        )

        with pytest.raises(ClientError):
            await client.delete_study('a' * 32, '1.2.3')

    @pytest.mark.asyncio
    async def test_update_image_set_metadata_error(self, client):
        """Test update_image_set_metadata handles ClientError."""
        client.healthimaging_client.update_image_set_metadata.side_effect = ClientError(
            {'Error': {'Code': 'Error', 'Message': 'Error'}}, 'UpdateImageSetMetadata'
        )

        with pytest.raises(ClientError):
            await client.update_image_set_metadata('a' * 32, 'b' * 32, '1', {})

    @pytest.mark.asyncio
    async def test_remove_series_error(self, client):
        """Test remove_series_from_image_set handles ClientError."""
        client.healthimaging_client.get_image_set.side_effect = ClientError(
            {'Error': {'Code': 'Error', 'Message': 'Error'}}, 'GetImageSet'
        )

        with pytest.raises(ClientError):
            await client.remove_series_from_image_set('a' * 32, 'b' * 32, '1.2.3.4')

    @pytest.mark.asyncio
    async def test_search_by_patient_error(self, client):
        """Test search_by_patient_id handles ClientError."""
        client.healthimaging_client.search_image_sets.side_effect = ClientError(
            {'Error': {'Code': 'Error', 'Message': 'Error'}}, 'SearchImageSets'
        )

        with pytest.raises(ClientError):
            await client.search_by_patient_id('a' * 32, 'P123')

    @pytest.mark.asyncio
    async def test_search_by_study_error(self, client):
        """Test search_by_study_uid handles ClientError."""
        client.healthimaging_client.search_image_sets.side_effect = ClientError(
            {'Error': {'Code': 'Error', 'Message': 'Error'}}, 'SearchImageSets'
        )

        with pytest.raises(ClientError):
            await client.search_by_study_uid('a' * 32, '1.2.3')

    @pytest.mark.asyncio
    async def test_search_by_series_error(self, client):
        """Test search_by_series_uid handles ClientError."""
        client.healthimaging_client.search_image_sets.side_effect = ClientError(
            {'Error': {'Code': 'Error', 'Message': 'Error'}}, 'SearchImageSets'
        )

        with pytest.raises(ClientError):
            await client.search_by_series_uid('a' * 32, '1.2.3.4')

    @pytest.mark.asyncio
    async def test_get_patient_studies_error(self, client):
        """Test get_patient_studies handles ClientError."""
        client.healthimaging_client.search_image_sets.side_effect = ClientError(
            {'Error': {'Code': 'Error', 'Message': 'Error'}}, 'SearchImageSets'
        )

        with pytest.raises(ClientError):
            await client.get_patient_studies('a' * 32, 'P123')

    @pytest.mark.asyncio
    async def test_get_patient_series_error(self, client):
        """Test get_patient_series handles ClientError."""
        client.healthimaging_client.search_image_sets.side_effect = ClientError(
            {'Error': {'Code': 'Error', 'Message': 'Error'}}, 'SearchImageSets'
        )

        with pytest.raises(ClientError):
            await client.get_patient_series('a' * 32, 'P123')

    @pytest.mark.asyncio
    async def test_get_study_primary_image_sets_error(self, client):
        """Test get_study_primary_image_sets handles ClientError."""
        client.healthimaging_client.search_image_sets.side_effect = ClientError(
            {'Error': {'Code': 'Error', 'Message': 'Error'}}, 'SearchImageSets'
        )

        with pytest.raises(ClientError):
            await client.get_study_primary_image_sets('a' * 32, '1.2.3')

    @pytest.mark.asyncio
    async def test_bulk_update_patient_metadata_error(self, client):
        """Test bulk_update_patient_metadata handles ClientError."""
        client.healthimaging_client.search_image_sets.side_effect = ClientError(
            {'Error': {'Code': 'Error', 'Message': 'Error'}}, 'SearchImageSets'
        )

        with pytest.raises(ClientError):
            await client.bulk_update_patient_metadata('a' * 32, 'P123', {})

    @pytest.mark.asyncio
    async def test_bulk_delete_by_criteria_error(self, client):
        """Test bulk_delete_by_criteria handles ClientError."""
        client.healthimaging_client.search_image_sets.side_effect = ClientError(
            {'Error': {'Code': 'Error', 'Message': 'Error'}}, 'SearchImageSets'
        )

        with pytest.raises(ClientError):
            await client.bulk_delete_by_criteria('a' * 32, {})
