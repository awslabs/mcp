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

"""Helpers for validating request bodies against the vendored service model."""

from awslabs.aws_transform_mcp_server._service_model import create_session
from botocore import UNSIGNED
from botocore.config import Config as BotoConfig
from botocore.validate import ParamValidator


_CLIENT = create_session().client(
    'elasticgumbyfrontendservice',
    region_name='us-east-1',
    endpoint_url='https://validation-only.invalid',
    config=BotoConfig(signature_version=UNSIGNED),
)
_VALIDATOR = ParamValidator()


def validate_request(operation: str, body: dict) -> None:
    """Validate an operation request body against the vendored C2J model."""
    operation_model = _CLIENT._service_model.operation_model(operation)
    report = _VALIDATOR.validate(body, operation_model.input_shape)
    if report.has_errors():
        raise ValueError(report.generate_report())
