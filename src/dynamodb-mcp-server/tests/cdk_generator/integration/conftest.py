"""Shared fixtures for CDK generator integration tests."""

import json
import pytest


def pytest_configure(config):
    """Configure pytest for integration tests only."""
    # Keep only failed test directories to save disk space
    # Integration tests can create large node_modules directories
    config.option.tmp_path_retention_count = 1
    config.option.tmp_path_retention_policy = 'failed'


@pytest.fixture
def complex_json_data():
    """Return complex DynamoDB data model with multiple tables, GSIs, and key types.

    Tests non-default values:
    - UserTable: Binary attribute type, GSI with KEYS_ONLY projection, TTL enabled
    - OrderTable: Number sort key, GSI with multi-partition and multi-sort keys, INCLUDE projection
    """
    return {
        'tables': [
            {
                'TableName': 'UserTable',
                'AttributeDefinitions': [
                    {'AttributeName': 'user_id', 'AttributeType': 'B'},
                    {'AttributeName': 'created_at', 'AttributeType': 'N'},
                    {'AttributeName': 'email', 'AttributeType': 'S'},
                ],
                'KeySchema': [
                    {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'created_at', 'KeyType': 'RANGE'},
                ],
                'GlobalSecondaryIndexes': [
                    {
                        'IndexName': 'EmailIndex',
                        'KeySchema': [
                            {'AttributeName': 'email', 'KeyType': 'HASH'},
                        ],
                        'Projection': {'ProjectionType': 'KEYS_ONLY'},
                    }
                ],
                'TimeToLiveSpecification': {
                    'AttributeName': 'ttl',
                    'Enabled': True,
                },
            },
            {
                'TableName': 'OrderTable',
                'AttributeDefinitions': [
                    {'AttributeName': 'customer_id', 'AttributeType': 'S'},
                    {'AttributeName': 'order_id', 'AttributeType': 'N'},
                    {'AttributeName': 'status', 'AttributeType': 'S'},
                    {'AttributeName': 'region', 'AttributeType': 'S'},
                    {'AttributeName': 'created_date', 'AttributeType': 'S'},
                    {'AttributeName': 'priority', 'AttributeType': 'N'},
                ],
                'KeySchema': [
                    {'AttributeName': 'customer_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'order_id', 'KeyType': 'RANGE'},
                ],
                'GlobalSecondaryIndexes': [
                    {
                        'IndexName': 'StatusIndex',
                        'KeySchema': [
                            {'AttributeName': 'status', 'KeyType': 'HASH'},
                            {'AttributeName': 'region', 'KeyType': 'HASH'},
                            {'AttributeName': 'created_date', 'KeyType': 'RANGE'},
                            {'AttributeName': 'priority', 'KeyType': 'RANGE'},
                        ],
                        'Projection': {
                            'ProjectionType': 'INCLUDE',
                            'NonKeyAttributes': ['total_amount', 'customer_name'],
                        },
                    }
                ],
            },
        ]
    }


@pytest.fixture
def complex_json_file(complex_json_data, tmp_path):
    """Create a temporary JSON file with complex data model.

    Pytest's tmp_path automatically handles cleanup after the test.
    """
    json_file = tmp_path / 'dynamodb_data_model.json'
    json_file.write_text(json.dumps(complex_json_data, indent=2))
    return json_file
