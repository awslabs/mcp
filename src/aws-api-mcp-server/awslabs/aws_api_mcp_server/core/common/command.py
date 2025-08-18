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

import dataclasses
from .command_metadata import CommandMetadata
from botocore import xform_name
from jmespath.parser import ParsedResult
from typing import Any


@dataclasses.dataclass(frozen=True)
class IRCommand:
    """Intermediate representation of an AWS CLI command."""

    command_metadata: CommandMetadata
    parameters: dict[str, Any]
    region: str
    profile: str | None = None
    client_side_filter: ParsedResult | None = None
    is_awscli_customization: bool = False

    @property
    def operation_python_name(self):
        """Return the Pythonic operation name for the command."""
        return xform_name(self.command_metadata.operation_sdk_name)

    @property
    def operation_name(self):
        """Return the operation name for the command."""
        return self.command_metadata.operation_sdk_name

    @property
    def service_name(self):
        """Return the service name for the command."""
        # The service name is always the existing API (e.g. S3 instead of S3API)
        return self.command_metadata.service_sdk_name

    @property
    def service_full_name(self):
        """Return the full service name for the command."""
        return self.command_metadata.service_full_sdk_name

    @property
    def has_streaming_output(self):
        """Return True if the command has streaming output, False otherwise."""
        return self.command_metadata.has_streaming_output
