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

"""Test fixtures for the billing-cost-management-mcp-server."""

import asyncio
import os
import pytest
import sys


# Add the parent directory to the Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Set default AWS region if not already set
if 'AWS_REGION' not in os.environ and 'AWS_DEFAULT_REGION' not in os.environ:
    os.environ['AWS_REGION'] = 'us-east-1'  # Default region for tests


TEMP_ENV_VARS = {'AWS_REGION': 'us-east-1'}  # Set default region for testing


@pytest.fixture(scope='session', autouse=True)
def tests_setup_and_teardown():
    """Mock environment and module variables for testing."""
    global TEMP_ENV_VARS
    old_environ = dict(os.environ)
    os.environ.update(TEMP_ENV_VARS)

    yield
    os.environ.clear()
    os.environ.update(old_environ)


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
