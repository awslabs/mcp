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

"""Test configuration and fixtures for Amazon SageMaker MCP Server tests."""

import os
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def clean_environment():
    """Clean environment variables before and after each test."""
    # Environment variables that might affect tests
    env_vars = [
        'ALLOW_WRITE',
        'ALLOW_SENSITIVE_DATA_ACCESS',
        'AWS_PROFILE',
        'AWS_REGION',
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY',
        'AWS_SESSION_TOKEN',
        'SAGEMAKER_EXECUTION_ROLE',
        'FASTMCP_LOG_LEVEL'
    ]
    
    # Store original values
    original_values = {}
    for var in env_vars:
        original_values[var] = os.environ.get(var)
    
    yield
    
    # Restore original values
    for var, value in original_values.items():
        if value is not None:
            os.environ[var] = value
        elif var in os.environ:
            del os.environ[var]


@pytest.fixture
def mock_sagemaker_client():
    """Create a mock SageMaker client."""
    client = MagicMock()
    
    # Mock common responses
    client.list_notebook_instances.return_value = {
        'NotebookInstances': [
            {
                'NotebookInstanceName': 'test-instance',
                'NotebookInstanceStatus': 'InService',
                'CreationTime': '2023-01-01T00:00:00Z'
            }
        ]
    }
    
    client.describe_notebook_instance.return_value = {
        'NotebookInstanceName': 'test-instance',
        'NotebookInstanceStatus': 'InService',
        'InstanceType': 'ml.t3.medium'
    }
    
    client.list_endpoints.return_value = {
        'Endpoints': [
            {
                'EndpointName': 'test-endpoint',
                'EndpointStatus': 'InService',
                'CreationTime': '2023-01-01T00:00:00Z'
            }
        ]
    }
    
    client.describe_endpoint.return_value = {
        'EndpointName': 'test-endpoint',
        'EndpointStatus': 'InService',
        'EndpointConfigName': 'test-config'
    }
    
    client.list_domains.return_value = {
        'Domains': [
            {
                'DomainId': 'd-123456789',
                'DomainName': 'test-domain',
                'Status': 'InService'
            }
        ]
    }
    
    client.describe_domain.return_value = {
        'DomainId': 'd-123456789',
        'DomainName': 'test-domain',
        'Status': 'InService'
    }
    
    return client


@pytest.fixture
def mock_sagemaker_runtime_client():
    """Create a mock SageMaker Runtime client."""
    client = MagicMock()
    
    # Mock response body
    mock_body = MagicMock()
    mock_body.read.return_value = b'{"prediction": "success"}'
    
    client.invoke_endpoint.return_value = {
        'Body': mock_body,
        'ContentType': 'application/json',
        'InvokedProductionVariant': 'variant-1'
    }
    
    return client


@pytest.fixture
def mock_sts_client():
    """Create a mock STS client."""
    client = MagicMock()
    client.get_caller_identity.return_value = {
        'Account': '123456789012',
        'Arn': 'arn:aws:iam::123456789012:user/test-user',
        'UserId': 'AIDACKCEVSQ6C2EXAMPLE'
    }
    return client


@pytest.fixture
def enable_write_access():
    """Enable write access for tests that need it."""
    os.environ['ALLOW_WRITE'] = 'true'
    yield
    if 'ALLOW_WRITE' in os.environ:
        del os.environ['ALLOW_WRITE']


@pytest.fixture
def enable_sensitive_data_access():
    """Enable sensitive data access for tests that need it."""
    os.environ['ALLOW_SENSITIVE_DATA_ACCESS'] = 'true'
    yield
    if 'ALLOW_SENSITIVE_DATA_ACCESS' in os.environ:
        del os.environ['ALLOW_SENSITIVE_DATA_ACCESS']


@pytest.fixture
def aws_credentials():
    """Set up AWS credentials for testing."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'test-key'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'test-secret'
    os.environ['AWS_REGION'] = 'us-east-1'
    yield
    # Cleanup is handled by clean_environment fixture


@pytest.fixture
def aws_profile():
    """Set up AWS profile for testing."""
    os.environ['AWS_PROFILE'] = 'test-profile'
    os.environ['AWS_REGION'] = 'us-west-2'
    yield
    # Cleanup is handled by clean_environment fixture
