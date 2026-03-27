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
"""Configuration for pytest."""

import pytest


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
    config.addinivalue_line(
        'markers', 'requires_uv: mark test as requiring uv package manager'
    )


def pytest_collection_modifyitems(config, items):
    """Skip live tests unless --run-live is specified, and skip requires_uv tests if uv is unavailable."""
    import shutil
    
    uv_available = shutil.which('uv') is not None
    
    if not config.getoption('--run-live'):
        skip_live = pytest.mark.skip(reason='need --run-live option to run')
        for item in items:
            if 'live' in item.keywords:
                item.add_marker(skip_live)
    
    if not uv_available:
        skip_uv = pytest.mark.skip(reason="Requires 'uv' package manager to be installed")
        for item in items:
            if 'requires_uv' in item.keywords:
                item.add_marker(skip_uv)
