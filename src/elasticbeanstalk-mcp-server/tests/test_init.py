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

"""Tests for the elasticbeanstalk MCP Server package initialization."""

import re
from awslabs.elasticbeanstalk_mcp_server import __version__


def test_version_format():
    """Test that the version string follows semantic versioning format."""
    # Semantic versioning pattern: MAJOR.MINOR.PATCH
    semver_pattern = r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'

    # For initial development, version 0.0.0 is also acceptable
    if __version__ != '0.0.0':
        assert re.match(semver_pattern, __version__) is not None, (
            f"Version '{__version__}' does not follow semantic versioning"
        )
