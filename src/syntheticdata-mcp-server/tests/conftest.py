"""Test configuration and fixtures."""

import boto3
import os
import pytest
import sys
import tempfile
from .test_constants import TEST_AWS_CONFIG, TEST_AWS_CREDENTIALS
from botocore.client import BaseClient
from moto import mock_aws
from typing import Dict, Generator, List


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for test files.

    Yields:
        Path to temporary directory
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture
def mock_cli_args() -> Generator[List[str], None, None]:
    """Mock command line arguments.

    This fixture saves the original sys.argv and restores it after the test,
    allowing tests to modify sys.argv without affecting other tests.

    Yields:
        List of command line arguments
    """
    original_argv = sys.argv
    sys.argv = ['server.py']  # Default state
    yield sys.argv
    sys.argv = original_argv


@pytest.fixture
def mock_aws_credentials() -> None:
    """Mock AWS credentials for moto using test constants."""
    os.environ.update(TEST_AWS_CREDENTIALS)


@pytest.fixture
def mock_s3(mock_aws_credentials) -> Generator[BaseClient, None, None]:
    """Create a mock S3 client using moto.

    Yields:
        Mocked S3 client
    """
    with mock_aws():
        s3_client = boto3.client('s3', region_name=TEST_AWS_CONFIG['region'])
        # Create test bucket
        s3_client.create_bucket(Bucket=TEST_AWS_CONFIG['test_bucket'])
        yield s3_client


@pytest.fixture
def sample_data() -> Dict:
    """Provide sample data for testing.

    Returns:
        Dictionary containing sample data for different entities
    """
    return {
        'customers': [
            {
                'customer_id': 1,
                'name': 'John Doe',
                'email': 'john@example.com',
                'created_at': '2024-01-01',
            },
            {
                'customer_id': 2,
                'name': 'Jane Smith',
                'email': 'jane@example.com',
                'created_at': '2024-01-02',
            },
        ],
        'orders': [
            {'order_id': 1, 'customer_id': 1, 'amount': 100.00, 'status': 'completed'},
            {'order_id': 2, 'customer_id': 2, 'amount': 200.00, 'status': 'pending'},
            {'order_id': 3, 'customer_id': 1, 'amount': 150.00, 'status': 'processing'},
        ],
    }


@pytest.fixture
def sample_pandas_code() -> str:
    """Provide sample pandas code for testing.

    Returns:
        String containing sample pandas code
    """
    return """
# Create customers DataFrame
customers_df = pd.DataFrame({
    'customer_id': [1, 2, 3],
    'name': ['John Doe', 'Jane Smith', 'Bob Wilson'],
    'email': ['john@example.com', 'jane@example.com', 'bob@example.com'],
    'city': ['New York', 'San Francisco', 'Chicago']
})

# Create orders DataFrame with foreign key relationship
orders_df = pd.DataFrame({
    'order_id': [1, 2, 3, 4],
    'customer_id': [1, 2, 3, 5],  # Note: customer_id 5 doesn't exist
    'amount': [100.00, 200.00, 150.00, 300.00],
    'status': ['completed', 'pending', 'completed', 'processing']
})

# Create addresses DataFrame with functional dependency
addresses_df = pd.DataFrame({
    'address_id': [1, 2, 3, 4],
    'city': ['New York', 'San Francisco', 'New York', 'Chicago'],
    'zip_code': ['10001', '94103', '10001', '60601']  # Note: city -> zip_code dependency
})
"""
