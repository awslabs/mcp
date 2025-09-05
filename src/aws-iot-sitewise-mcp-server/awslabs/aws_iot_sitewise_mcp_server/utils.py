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

import importlib.metadata
import re


LOGIN_REGEX = r'^[a-z]{3,8}$'


def validate_amazon_login(login: str) -> None:
    """Validate that the login string matches the required Amazon login format.

    Args:
        login: The login string to validate

    Raises:
        ValueError: If login doesn't match the required regex pattern
    """
    if not re.match(LOGIN_REGEX, login):
        raise ValueError(f'Invalid login syntax. Must match regex {LOGIN_REGEX}')


def get_package_version() -> str:
    """Get the version of the package, or return a default version if not available."""
    try:
        return importlib.metadata.version('awslabs.aws_iot_sitewise_mcp_server')
    except Exception:
        # Return a default version instead of raising an exception
        # to avoid crashing the server on startup
        return '0.1.0'
