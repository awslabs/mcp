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

import pytest


def pytest_addoption(parser):
    """Add command-line options to pytest."""
    parser.addoption(
        '--run-live',
        action='store_true',
        default=False,
        help='Run tests that make live API calls to AWS services',
    )
    parser.addoption(
        '--run-github',
        action='store_true',
        default=False,
        help='Run tests that make API calls to GitHub',
    )


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line('markers', 'live: mark test as making live AWS API calls')
    config.addinivalue_line('markers', 'github: mark test as making GitHub API calls')


def pytest_collection_modifyitems(config, items):
    """Skip live and GitHub tests unless explicit options are provided."""
    if not config.getoption('--run-live'):
        skip_live = pytest.mark.skip(reason='need --run-live option to run')
        for item in items:
            if 'live' in item.keywords:
                item.add_marker(skip_live)

    if not config.getoption('--run-github'):
        skip_github = pytest.mark.skip(reason='need --run-github option to run')
        for item in items:
            if 'github' in item.keywords:
                item.add_marker(skip_github)
