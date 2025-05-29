# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Configuration for pytest."""

import os
import pytest
from unittest.mock import MagicMock


def pytest_addoption(parser):
    """Add command-line options to pytest."""
    parser.addoption(
        '--run-live',
        action='store_true',
        default=False,
        help='Run tests that make live API calls',
    )


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line('markers', 'live: mark test as making live API calls')


def pytest_collection_modifyitems(config, items):
    """Skip live tests unless --run-live is specified."""
    if not config.getoption('--run-live'):
        skip_live = pytest.mark.skip(reason='need --run-live option to run')
        for item in items:
            if 'live' in item.keywords:
                item.add_marker(skip_live)


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    return MagicMock()


@pytest.fixture
def mock_schemas_client():
    """Create a mock boto3 schemas client."""
    return MagicMock()


@pytest.fixture
def mock_env():
    """Create a mock environment with test AWS credentials."""
    original_env = dict(os.environ)
    test_env = {'AWS_PROFILE': 'test-profile', 'AWS_REGION': 'us-west-2'}
    os.environ.update(test_env)
    yield test_env
    os.environ.clear()
    os.environ.update(original_env)
