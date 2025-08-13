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

"""Test configuration and fixtures."""

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_boto_client():
    """Mock boto3 client fixture."""
    return MagicMock()


@pytest.fixture
def mock_pipeline_response():
    """Mock pipeline response fixture."""
    return {
        'pipeline': {
            'name': 'test-pipeline',
            'roleArn': 'arn:aws:iam::123456789012:role/service-role/AWSCodePipelineServiceRole',
            'stages': []
        },
        'metadata': {
            'pipelineArn': 'arn:aws:codepipeline:us-east-1:123456789012:test-pipeline'
        }
    }
