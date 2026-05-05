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

from awslabs.aws_api_mcp_server.core.common.command import IRCommand
from awslabs.aws_api_mcp_server.core.common.command_metadata import CommandMetadata


def test_operation_cli_name():
    """Test the operation_cli_name property."""
    metadata = CommandMetadata(
        service_sdk_name='ec2',
        service_full_sdk_name='Amazon Elastic Compute Cloud',
        operation_sdk_name='DescribeNetworkInterfaces',
        has_streaming_output=False,
    )
    command = IRCommand(command_metadata=metadata, parameters={}, region='us-east-1')
    assert command.operation_cli_name == 'describe-network-interfaces'


def test_operation_cli_name_ec2():
    """Test operation_cli_name with operations that have multiple underscores."""
    metadata = CommandMetadata(
        service_sdk_name='ec2',
        service_full_sdk_name='Amazon Elastic Compute Cloud',
        operation_sdk_name='DescribeNetworkInterfaces',
        has_streaming_output=False,
    )
    command = IRCommand(command_metadata=metadata, parameters={}, region='us-east-1')
    assert command.operation_cli_name == 'describe-network-interfaces'


def test_operation_cli_name_with_s3():
    """Test operation_cli_name with operations that have no underscores."""
    metadata = CommandMetadata(
        service_sdk_name='s3',
        service_full_sdk_name='Amazon Simple Storage Service',
        operation_sdk_name='ListBuckets',
        has_streaming_output=False,
    )
    command = IRCommand(command_metadata=metadata, parameters={}, region='us-east-1')
    assert command.operation_cli_name == 'list-buckets'
