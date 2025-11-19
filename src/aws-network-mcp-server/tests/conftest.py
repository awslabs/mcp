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

import pytest
from unittest.mock import patch


@pytest.fixture
def mock_aws_credentials():
    """Mock AWS credentials for testing."""
    with patch.dict(
        'os.environ',
        {
            'AWS_ACCESS_KEY_ID': 'testing',  # pragma: allowlist secret
            'AWS_SECRET_ACCESS_KEY': 'testing',  # pragma: allowlist secret
            'AWS_SECURITY_TOKEN': 'testing',  # pragma: allowlist secret
            'AWS_SESSION_TOKEN': 'testing',  # pragma: allowlist secret
            'AWS_DEFAULT_REGION': 'us-east-1',
        },
    ):
        yield
