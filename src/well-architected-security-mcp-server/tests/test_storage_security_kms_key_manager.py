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

"""Tests for telling AWS managed and customer managed KMS keys apart."""

from unittest import mock

import botocore.exceptions
import pytest

from awslabs.well_architected_security_mcp_server.util.storage_security import (
    _is_customer_managed_key,
    check_ebs_volumes,
    check_efs_filesystems,
    check_rds_instances,
    check_storage_encryption,
)

AWS_MANAGED_KEY = "arn:aws:kms:us-east-1:123456789012:key/11111111-1111-1111-1111-111111111111"
CUSTOMER_KEY = "arn:aws:kms:us-east-1:123456789012:key/22222222-2222-2222-2222-222222222222"
CMK_REMEDIATION = "Consider using a customer-managed KMS key instead of AWS managed key"


def _kms_client():
    """Return a mock KMS client that knows one AWS managed and one customer managed key."""
    managers = {AWS_MANAGED_KEY: "AWS", CUSTOMER_KEY: "CUSTOMER"}
    kms_client = mock.MagicMock()
    kms_client.describe_key.side_effect = lambda KeyId: {
        "KeyMetadata": {"KeyId": KeyId, "KeyManager": managers[KeyId]}
    }
    return kms_client


def test_is_customer_managed_key():
    """KeyManager from DescribeKey decides, and each key is described once."""
    kms_client = _kms_client()
    cache = {}

    assert _is_customer_managed_key(kms_client, AWS_MANAGED_KEY, cache) is False
    assert _is_customer_managed_key(kms_client, CUSTOMER_KEY, cache) is True
    assert _is_customer_managed_key(kms_client, AWS_MANAGED_KEY, cache) is False
    assert kms_client.describe_key.call_count == 2


def test_is_customer_managed_key_unknown():
    """Without a client, or when DescribeKey fails, the key manager is unknown."""
    assert _is_customer_managed_key(None, CUSTOMER_KEY, {}) is None

    kms_client = mock.MagicMock()
    kms_client.describe_key.side_effect = botocore.exceptions.ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "denied"}}, "DescribeKey"
    )
    assert _is_customer_managed_key(kms_client, CUSTOMER_KEY, {}) is None


@pytest.mark.asyncio
async def test_check_ebs_volumes_detects_aws_managed_key(mock_ctx):
    """An EBS volume encrypted with the aws/ebs key is not reported as using a CMK."""
    storage_resources = {
        "resources_by_service": {
            "ebs": [
                {"Arn": "arn:aws:ec2:us-east-1:123456789012:volume/vol-aws"},
                {"Arn": "arn:aws:ec2:us-east-1:123456789012:volume/vol-cmk"},
            ]
        }
    }
    ec2_client = mock.MagicMock()
    ec2_client.describe_volumes.return_value = {
        "Volumes": [
            {"VolumeId": "vol-aws", "Encrypted": True, "KmsKeyId": AWS_MANAGED_KEY},
            {"VolumeId": "vol-cmk", "Encrypted": True, "KmsKeyId": CUSTOMER_KEY},
        ]
    }

    result = await check_ebs_volumes(
        "us-east-1", ec2_client, mock_ctx, storage_resources, kms_client=_kms_client()
    )

    aws_volume, cmk_volume = result["resource_details"]
    assert aws_volume["checks"]["using_cmk"] is False
    assert CMK_REMEDIATION in aws_volume["remediation"]
    assert cmk_volume["checks"]["using_cmk"] is True
    assert cmk_volume["remediation"] == []


@pytest.mark.asyncio
async def test_check_rds_instances_detects_aws_managed_key(mock_ctx):
    """An RDS instance encrypted with the aws/rds key is not reported as using a CMK."""
    storage_resources = {
        "resources_by_service": {"rds": [{"Arn": "arn:aws:rds:us-east-1:123456789012:db:db-1"}]}
    }
    rds_client = mock.MagicMock()
    rds_client.describe_db_instances.return_value = {
        "DBInstances": [
            {
                "DBInstanceIdentifier": "db-1",
                "StorageEncrypted": True,
                "KmsKeyId": AWS_MANAGED_KEY,
                "PubliclyAccessible": False,
            }
        ]
    }

    result = await check_rds_instances(
        "us-east-1", rds_client, mock_ctx, storage_resources, kms_client=_kms_client()
    )

    instance = result["resource_details"][0]
    assert instance["checks"]["using_cmk"] is False
    assert CMK_REMEDIATION in instance["remediation"]


@pytest.mark.asyncio
async def test_check_efs_filesystems_detects_aws_managed_key(mock_ctx):
    """An EFS file system encrypted with the aws/elasticfilesystem key is not a CMK."""
    storage_resources = {
        "resources_by_service": {
            "elasticfilesystem": [
                {"Arn": "arn:aws:elasticfilesystem:us-east-1:123456789012:file-system/fs-1"}
            ]
        }
    }
    efs_client = mock.MagicMock()
    efs_client.describe_file_systems.return_value = {
        "FileSystems": [{"FileSystemId": "fs-1", "Encrypted": True, "KmsKeyId": AWS_MANAGED_KEY}]
    }

    result = await check_efs_filesystems(
        "us-east-1", efs_client, mock_ctx, storage_resources, kms_client=_kms_client()
    )

    fs = result["resource_details"][0]
    assert fs["checks"]["using_cmk"] is False
    assert CMK_REMEDIATION in fs["remediation"]


@pytest.mark.asyncio
async def test_check_storage_encryption_passes_kms_client(mock_ctx, mock_boto3_session):
    """check_storage_encryption creates a KMS client and hands it to the EBS check."""
    kms_client = mock.MagicMock()
    mock_boto3_session.client.side_effect = lambda service, **kwargs: (
        kms_client if service == "kms" else mock.MagicMock()
    )
    module = "awslabs.well_architected_security_mcp_server.util.storage_security"

    with (
        mock.patch(f"{module}.find_storage_resources", new=mock.AsyncMock(return_value={})),
        mock.patch(
            f"{module}.check_ebs_volumes",
            new=mock.AsyncMock(return_value={"service": "ebs", "resource_details": []}),
        ) as check_ebs,
    ):
        await check_storage_encryption("us-east-1", ["ebs"], mock_boto3_session, mock_ctx)

    assert check_ebs.call_args.kwargs["kms_client"] is kms_client
