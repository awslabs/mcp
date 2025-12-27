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

"""Pytest configuration and fixtures."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock


@pytest.fixture
def mock_healthimaging_client():
    """Mock boto3 HealthImaging client."""
    client = MagicMock()
    return client


@pytest.fixture
def sample_datastore():
    """Sample datastore data for testing."""
    return {
        'datastoreId': 'a' * 32,  # 32-char alphanumeric test ID
        'datastoreName': 'test-datastore',
        'datastoreStatus': 'ACTIVE',
        'createdAt': datetime(2024, 1, 1, 0, 0, 0).timestamp(),
        'updatedAt': datetime(2024, 1, 1, 0, 0, 0).timestamp(),
    }


@pytest.fixture
def sample_image_set():
    """Sample image set data for testing."""
    return {
        'imageSetId': 'b' * 32,  # 32-char alphanumeric test ID
        'versionId': '1',
        'imageSetState': 'ACTIVE',
        'createdAt': datetime(2024, 1, 1, 0, 0, 0).timestamp(),
        'updatedAt': datetime(2024, 1, 1, 0, 0, 0).timestamp(),
    }


@pytest.fixture
def sample_search_criteria():
    """Sample search criteria for testing."""
    return {'filters': [{'values': [{'DICOMPatientId': 'PATIENT123'}], 'operator': 'EQUAL'}]}


@pytest.fixture
def sample_dicom_metadata():
    """Sample DICOM metadata for testing."""
    return {
        'Study': {
            'DICOM': {
                'StudyInstanceUID': '1.2.3.4.5',
                'StudyDate': '20240101',
                'StudyTime': '120000',
                'StudyDescription': 'Test Study',
            },
            'Series': {
                '1.2.3.4.5.1': {
                    'DICOM': {'Modality': 'CT', 'SeriesNumber': '1'},
                    'Instances': {
                        '1.2.3.4.5.1.1': {
                            'DICOM': {'InstanceNumber': '1'},
                            'ImageFrames': [{'ID': 'frame123456', 'FrameSizeInBytes': 1024}],
                        }
                    },
                }
            },
        }
    }
