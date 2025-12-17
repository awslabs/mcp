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

"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from awslabs.healthimaging_mcp_server.models import (
    DatastoreFilter,
    SearchImageSetsRequest,
    ImageSetRequest,
    ImageSetMetadataRequest,
    ImageFrameRequest,
    ImageSetVersionsRequest,
    DeleteImageSetRequest,
    DeletePatientStudiesRequest,
    DeleteStudyRequest,
    UpdateImageSetMetadataRequest,
    RemoveSeriesRequest,
    RemoveInstanceRequest,
    SearchByPatientRequest,
    SearchByStudyRequest,
    SearchBySeriesRequest,
    GetPatientStudiesRequest,
    GetPatientSeriesRequest,
    GetStudyPrimaryImageSetsRequest,
    BulkUpdatePatientMetadataRequest,
    BulkDeleteByCriteriaRequest,
)


class TestDatastoreFilter:
    """Tests for DatastoreFilter model."""

    def test_valid_status(self):
        """Test valid status values."""
        for status in ['CREATING', 'ACTIVE', 'DELETING', 'DELETED']:
            model = DatastoreFilter(status=status)
            assert model.status == status

    def test_none_status(self):
        """Test None status is valid."""
        model = DatastoreFilter()
        assert model.status is None


class TestSearchImageSetsRequest:
    """Tests for SearchImageSetsRequest model."""

    def test_valid_request(self):
        """Test valid request."""
        model = SearchImageSetsRequest(datastore_id='a' * 32)
        assert model.datastore_id == 'a' * 32
        assert model.max_results == 50

    def test_with_search_criteria(self):
        """Test with search criteria."""
        criteria = {'filters': []}
        model = SearchImageSetsRequest(datastore_id='a' * 32, search_criteria=criteria)
        assert model.search_criteria == criteria

    def test_invalid_datastore_id_length(self):
        """Test invalid datastore ID length."""
        with pytest.raises(ValidationError):
            SearchImageSetsRequest(datastore_id='short')

    def test_invalid_datastore_id_non_alphanumeric(self):
        """Test invalid datastore ID with special characters."""
        with pytest.raises(ValidationError):
            SearchImageSetsRequest(datastore_id='a' * 31 + '!')

    def test_max_results_bounds(self):
        """Test max_results bounds."""
        model = SearchImageSetsRequest(datastore_id='a' * 32, max_results=100)
        assert model.max_results == 100

        with pytest.raises(ValidationError):
            SearchImageSetsRequest(datastore_id='a' * 32, max_results=101)

        with pytest.raises(ValidationError):
            SearchImageSetsRequest(datastore_id='a' * 32, max_results=0)


class TestImageSetRequest:
    """Tests for ImageSetRequest model."""

    def test_valid_request(self):
        """Test valid request."""
        model = ImageSetRequest(datastore_id='a' * 32, image_set_id='b' * 32)
        assert model.datastore_id == 'a' * 32
        assert model.image_set_id == 'b' * 32


class TestImageSetMetadataRequest:
    """Tests for ImageSetMetadataRequest model."""

    def test_valid_request(self):
        """Test valid request."""
        model = ImageSetMetadataRequest(datastore_id='a' * 32, image_set_id='b' * 32)
        assert model.version_id is None

    def test_with_version(self):
        """Test with version ID."""
        model = ImageSetMetadataRequest(
            datastore_id='a' * 32, image_set_id='b' * 32, version_id='1'
        )
        assert model.version_id == '1'


class TestImageFrameRequest:
    """Tests for ImageFrameRequest model."""

    def test_valid_request(self):
        """Test valid request."""
        model = ImageFrameRequest(
            datastore_id='a' * 32, image_set_id='b' * 32, image_frame_id='frame123'
        )
        assert model.image_frame_id == 'frame123'


class TestImageSetVersionsRequest:
    """Tests for ImageSetVersionsRequest model."""

    def test_valid_request(self):
        """Test valid request."""
        model = ImageSetVersionsRequest(datastore_id='a' * 32, image_set_id='b' * 32)
        assert model.max_results == 50


class TestDeleteImageSetRequest:
    """Tests for DeleteImageSetRequest model."""

    def test_valid_request(self):
        """Test valid request."""
        model = DeleteImageSetRequest(datastore_id='a' * 32, image_set_id='b' * 32)
        assert model.image_set_id == 'b' * 32


class TestDeletePatientStudiesRequest:
    """Tests for DeletePatientStudiesRequest model."""

    def test_valid_request(self):
        """Test valid request."""
        model = DeletePatientStudiesRequest(datastore_id='a' * 32, patient_id='P123')
        assert model.patient_id == 'P123'


class TestDeleteStudyRequest:
    """Tests for DeleteStudyRequest model."""

    def test_valid_request(self):
        """Test valid request."""
        model = DeleteStudyRequest(datastore_id='a' * 32, study_instance_uid='1.2.3')
        assert model.study_instance_uid == '1.2.3'


class TestUpdateImageSetMetadataRequest:
    """Tests for UpdateImageSetMetadataRequest model."""

    def test_valid_request(self):
        """Test valid request."""
        model = UpdateImageSetMetadataRequest(
            datastore_id='a' * 32,
            image_set_id='b' * 32,
            version_id='1',
            updates={'DICOMUpdates': {}}
        )
        assert model.updates == {'DICOMUpdates': {}}


class TestRemoveSeriesRequest:
    """Tests for RemoveSeriesRequest model."""

    def test_valid_request(self):
        """Test valid request."""
        model = RemoveSeriesRequest(
            datastore_id='a' * 32, image_set_id='b' * 32, series_instance_uid='1.2.3.4'
        )
        assert model.series_instance_uid == '1.2.3.4'


class TestRemoveInstanceRequest:
    """Tests for RemoveInstanceRequest model."""

    def test_valid_request(self):
        """Test valid request."""
        model = RemoveInstanceRequest(
            datastore_id='a' * 32, image_set_id='b' * 32, sop_instance_uid='1.2.3.4.5'
        )
        assert model.sop_instance_uid == '1.2.3.4.5'
        assert model.series_instance_uid is None

    def test_with_series_uid(self):
        """Test with series UID."""
        model = RemoveInstanceRequest(
            datastore_id='a' * 32,
            image_set_id='b' * 32,
            sop_instance_uid='1.2.3.4.5',
            series_instance_uid='1.2.3.4'
        )
        assert model.series_instance_uid == '1.2.3.4'


class TestSearchByPatientRequest:
    """Tests for SearchByPatientRequest model."""

    def test_valid_request(self):
        """Test valid request."""
        model = SearchByPatientRequest(datastore_id='a' * 32, patient_id='P123')
        assert model.include_primary_only is False

    def test_with_primary_only(self):
        """Test with include_primary_only."""
        model = SearchByPatientRequest(
            datastore_id='a' * 32, patient_id='P123', include_primary_only=True
        )
        assert model.include_primary_only is True


class TestSearchByStudyRequest:
    """Tests for SearchByStudyRequest model."""

    def test_valid_request(self):
        """Test valid request."""
        model = SearchByStudyRequest(datastore_id='a' * 32, study_instance_uid='1.2.3')
        assert model.include_primary_only is False


class TestSearchBySeriesRequest:
    """Tests for SearchBySeriesRequest model."""

    def test_valid_request(self):
        """Test valid request."""
        model = SearchBySeriesRequest(datastore_id='a' * 32, series_instance_uid='1.2.3.4')
        assert model.series_instance_uid == '1.2.3.4'


class TestGetPatientStudiesRequest:
    """Tests for GetPatientStudiesRequest model."""

    def test_valid_request(self):
        """Test valid request."""
        model = GetPatientStudiesRequest(datastore_id='a' * 32, patient_id='P123')
        assert model.patient_id == 'P123'


class TestGetPatientSeriesRequest:
    """Tests for GetPatientSeriesRequest model."""

    def test_valid_request(self):
        """Test valid request."""
        model = GetPatientSeriesRequest(datastore_id='a' * 32, patient_id='P123')
        assert model.patient_id == 'P123'


class TestGetStudyPrimaryImageSetsRequest:
    """Tests for GetStudyPrimaryImageSetsRequest model."""

    def test_valid_request(self):
        """Test valid request."""
        model = GetStudyPrimaryImageSetsRequest(
            datastore_id='a' * 32, study_instance_uid='1.2.3'
        )
        assert model.study_instance_uid == '1.2.3'


class TestBulkUpdatePatientMetadataRequest:
    """Tests for BulkUpdatePatientMetadataRequest model."""

    def test_valid_request(self):
        """Test valid request."""
        model = BulkUpdatePatientMetadataRequest(
            datastore_id='a' * 32, patient_id='P123', new_metadata={'PatientName': 'Test'}
        )
        assert model.new_metadata == {'PatientName': 'Test'}


class TestBulkDeleteByCriteriaRequest:
    """Tests for BulkDeleteByCriteriaRequest model."""

    def test_valid_request(self):
        """Test valid request."""
        model = BulkDeleteByCriteriaRequest(
            datastore_id='a' * 32, search_criteria={'filters': []}
        )
        assert model.search_criteria == {'filters': []}
