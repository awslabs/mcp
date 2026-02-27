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

"""Tests for the deprecated redirect wrapper."""

import warnings
from unittest.mock import patch


def test_import_main():
    """Test that the main function can be imported from the redirect module."""
    from awslabs.cloudwatch_appsignals_mcp_server.server import main

    assert callable(main)


def test_main_emits_deprecation_warning():
    """Test that calling main() emits a DeprecationWarning."""
    with (
        patch('awslabs.cloudwatch_applicationsignals_mcp_server.server.main'),
        warnings.catch_warnings(record=True) as w,
    ):
        warnings.simplefilter('always')
        from awslabs.cloudwatch_appsignals_mcp_server.server import main

        main()

        deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(deprecation_warnings) >= 1
        assert 'deprecated' in str(deprecation_warnings[0].message).lower()
        assert 'cloudwatch-applicationsignals-mcp-server' in str(deprecation_warnings[0].message)


def test_main_delegates_to_new_package():
    """Test that main() delegates to the new package's main()."""
    with (
        patch('awslabs.cloudwatch_applicationsignals_mcp_server.server.main') as mock_new_main,
        warnings.catch_warnings(record=True),
    ):
        warnings.simplefilter('always')
        from awslabs.cloudwatch_appsignals_mcp_server.server import main

        main()

        mock_new_main.assert_called_once()


def test_version():
    """Test that __version__ is set to 0.2.0."""
    from awslabs.cloudwatch_appsignals_mcp_server import __version__

    assert __version__ == '0.2.0'
