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
