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

"""Shared test fixtures for HealthImaging MCP server tests."""

import pytest
from awslabs.healthimaging_mcp_server.healthimaging_operations import DATASTORE_ID_LENGTH
from unittest.mock import MagicMock, patch


@pytest.fixture
def sample_datastore_id():
    """Sample valid datastore ID."""
    return 'a' * DATASTORE_ID_LENGTH


@pytest.fixture
def sample_image_set_id():
    """Sample image set ID."""
    return 'test-image-set-id-12345'


@pytest.fixture
def sample_patient_id():
    """Sample patient ID."""
    return 'PATIENT123'


@pytest.fixture
def sample_study_uid():
    """Sample study instance UID."""
    return '1.2.3.4.5.6.7.8.9.10.11.12.13.14.15'


@pytest.fixture
def sample_series_uid():
    """Sample series instance UID."""
    return '1.2.3.4.5.6.7.8.9.10.11.12.13.14.16'


@pytest.fixture
def sample_search_criteria():
    """Sample search criteria for image sets."""
    return {'filters': [{'values': [{'DICOMPatientId': 'PATIENT123'}], 'operator': 'EQUAL'}]}


@pytest.fixture
def sample_image_set_metadata():
    """Sample image set metadata response."""
    return {
        'Patient': {
            'DICOM': {
                'PatientID': 'PATIENT123',
                'PatientName': 'Test^Patient',
                'PatientBirthDate': '19900101',
            }
        },
        'Study': {
            'DICOM': {
                'StudyInstanceUID': {
                    '1.2.3.4.5.6.7.8.9.10.11.12.13.14.15': {
                        'StudyDate': '20240101',
                        'StudyDescription': 'Test Study',
                        'Series': {
                            '1.2.3.4.5.6.7.8.9.10.11.12.13.14.16': {
                                'SeriesDescription': 'Test Series',
                                'Modality': 'CT',
                                'Instances': {
                                    '1.2.3.4.5.6.7.8.9.10.11.12.13.14.17': {
                                        'SOPClassUID': '1.2.840.10008.5.1.4.1.1.2',
                                        'ImageFrames': [
                                            {
                                                'ID': 'frame-1',
                                                'PixelDataChecksumFromBaseToFullResolution': 'checksum1',
                                            }
                                        ],
                                    }
                                },
                            }
                        },
                    }
                }
            }
        },
    }


@pytest.fixture
def mock_boto3_session():
    """Mock boto3 session with HealthImaging client."""
    with patch('boto3.Session') as mock_session_class:
        session = MagicMock()
        mock_session_class.return_value = session
        session.region_name = 'us-east-1'

        # Mock the HealthImaging client
        client = MagicMock()
        session.client.return_value = client

        yield session, client


@pytest.fixture
def mock_fastmcp_app():
    """Mock FastMCP app for testing."""
    with patch('mcp.server.fastmcp.FastMCP') as mock_fastmcp:
        app = MagicMock()
        mock_fastmcp.return_value = app
        yield app
