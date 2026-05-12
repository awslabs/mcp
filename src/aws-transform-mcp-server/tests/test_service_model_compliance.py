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

"""Regression tests: validate FES request bodies against the C2J service model.

Uses botocore's ParamValidator against the vendored service-2.json to catch
parameter mismatches that mocked tests would miss.
"""
# ruff: noqa: D101, D102, D103

import pytest
from awslabs.aws_transform_mcp_server._service_model import create_session
from botocore import UNSIGNED
from botocore.config import Config as BotoConfig
from botocore.validate import ParamValidator


_client = create_session().client(
    'elasticgumbyfrontendservice',
    region_name='us-east-1',
    endpoint_url='https://validation-only.invalid',
    config=BotoConfig(signature_version=UNSIGNED),
)
_validator = ParamValidator()


def _validate(operation: str, body: dict) -> None:
    op_model = _client._service_model.operation_model(operation)
    report = _validator.validate(body, op_model.input_shape)
    if report.has_errors():
        raise ValueError(report.generate_report())


class TestRegressions:
    def test_file_metadata_rejects_fileName(self):
        """Bug fix: fileMetadata.fileName does not exist in the service model."""
        with pytest.raises(ValueError, match='fileName'):
            _validate(
                'CreateArtifactUploadUrl',
                {
                    'workspaceId': 'w',
                    'contentDigest': {'Sha256': 'abc'},
                    'artifactReference': {
                        'artifactType': {'categoryType': 'CUSTOMER_INPUT', 'fileType': 'JSON'}
                    },
                    'fileMetadata': {'fileName': 'bad.json', 'path': 'bad.json'},
                },
            )

    def test_list_plan_updates_requires_timestamp_and_plan_version(self):
        """Bug fix: ListPlanUpdates requires timestamp and planVersion."""
        with pytest.raises(ValueError, match='timestamp'):
            _validate('ListPlanUpdates', {'workspaceId': 'w', 'jobId': 'j'})
