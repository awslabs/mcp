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

"""Tools must not write to stdout, which carries the stdio JSON-RPC stream (issue #4991)."""

import pytest

from awslabs.well_architected_security_mcp_server.server import (
    check_network_security_tool,
    check_security_services,
    check_storage_encryption_tool,
)


@pytest.mark.asyncio
async def test_check_security_services_writes_nothing_to_stdout(
    capsys, mock_ctx, mock_boto3_session
):
    """CheckSecurityServices runs the real service checks against mocked boto clients."""
    await check_security_services(
        mock_ctx,
        region="us-east-1",
        services=[
            "guardduty",
            "inspector",
            "accessanalyzer",
            "securityhub",
            "trustedadvisor",
            "macie",
        ],
        account_id=None,
        aws_profile=None,
        store_in_context=False,
        debug=True,
    )

    captured = capsys.readouterr()
    assert captured.out == ""


@pytest.mark.asyncio
async def test_storage_and_network_checks_write_nothing_to_stdout(
    capsys, mock_ctx, mock_boto3_session
):
    """CheckStorageEncryption and CheckNetworkSecurity log to stderr only."""
    await check_storage_encryption_tool(
        mock_ctx,
        region="us-east-1",
        services=["s3", "ebs", "rds", "dynamodb", "efs", "elasticache"],
        aws_profile=None,
        include_unencrypted_only=False,
        store_in_context=False,
    )
    await check_network_security_tool(
        mock_ctx,
        region="us-east-1",
        services=["elb", "vpc", "apigateway", "cloudfront"],
        aws_profile=None,
        include_non_compliant_only=False,
        store_in_context=False,
    )

    captured = capsys.readouterr()
    assert captured.out == ""
