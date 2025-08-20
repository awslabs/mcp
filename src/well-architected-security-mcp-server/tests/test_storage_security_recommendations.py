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

"""Tests for storage_security recommendations to improve coverage."""

import pytest

from awslabs.well_architected_security_mcp_server.util.storage_security import (
    generate_recommendations,
)


@pytest.mark.asyncio
async def test_generate_recommendations_with_s3_non_compliant():
    """Test recommendations generation with S3 non-compliant resources."""
    results = {"compliance_by_service": {"s3": {"non_compliant_resources": 2}}}

    recommendations = await generate_recommendations(results)

    # Should include S3-specific recommendations plus general ones
    assert len(recommendations) >= 4
    assert any("Enable default encryption" in rec for rec in recommendations)
    assert any("block public access" in rec for rec in recommendations)
    assert any("customer-managed KMS keys" in rec for rec in recommendations)


@pytest.mark.asyncio
async def test_generate_recommendations_with_ebs_non_compliant():
    """Test recommendations generation with EBS non-compliant resources."""
    results = {"compliance_by_service": {"ebs": {"non_compliant_resources": 1}}}

    recommendations = await generate_recommendations(results)

    # Should include EBS-specific recommendations plus general ones
    assert len(recommendations) >= 4
    assert any("Enable default EBS encryption" in rec for rec in recommendations)
    assert any("encrypted snapshots" in rec for rec in recommendations)


@pytest.mark.asyncio
async def test_generate_recommendations_with_rds_non_compliant():
    """Test recommendations generation with RDS non-compliant resources."""
    results = {"compliance_by_service": {"rds": {"non_compliant_resources": 1}}}

    recommendations = await generate_recommendations(results)

    # Should include RDS-specific recommendations plus general ones
    assert len(recommendations) >= 5
    assert any("Enable encryption for all RDS instances" in rec for rec in recommendations)
    assert any("Configure SSL/TLS for database connections" in rec for rec in recommendations)
    assert any("Enable default RDS encryption" in rec for rec in recommendations)


@pytest.mark.asyncio
async def test_generate_recommendations_with_dynamodb_non_compliant():
    """Test recommendations generation with DynamoDB non-compliant resources."""
    results = {"compliance_by_service": {"dynamodb": {"non_compliant_resources": 1}}}

    recommendations = await generate_recommendations(results)

    # Should include DynamoDB-specific recommendations plus general ones
    assert len(recommendations) >= 3
    assert any("customer-managed KMS keys for DynamoDB tables" in rec for rec in recommendations)


@pytest.mark.asyncio
async def test_generate_recommendations_with_efs_non_compliant():
    """Test recommendations generation with EFS non-compliant resources."""
    results = {"compliance_by_service": {"efs": {"non_compliant_resources": 1}}}

    recommendations = await generate_recommendations(results)

    # Should include EFS-specific recommendations plus general ones
    assert len(recommendations) >= 4
    assert any("Create new encrypted EFS filesystems" in rec for rec in recommendations)
    assert any(
        "Enable encryption by default for new EFS filesystems" in rec for rec in recommendations
    )


@pytest.mark.asyncio
async def test_generate_recommendations_with_elasticache_non_compliant():
    """Test recommendations generation with ElastiCache non-compliant resources."""
    results = {"compliance_by_service": {"elasticache": {"non_compliant_resources": 1}}}

    recommendations = await generate_recommendations(results)

    # Should include ElastiCache-specific recommendations plus general ones
    assert len(recommendations) >= 5
    assert any("Use Redis instead of Memcached" in rec for rec in recommendations)
    assert any(
        "Enable at-rest and in-transit encryption for Redis clusters" in rec
        for rec in recommendations
    )
    assert any("Enable AUTH tokens for Redis clusters" in rec for rec in recommendations)


@pytest.mark.asyncio
async def test_generate_recommendations_with_multiple_services():
    """Test recommendations generation with multiple services having non-compliant resources."""
    results = {
        "compliance_by_service": {
            "s3": {"non_compliant_resources": 2},
            "ebs": {"non_compliant_resources": 1},
            "rds": {"non_compliant_resources": 1},
            "dynamodb": {"non_compliant_resources": 1},
            "efs": {"non_compliant_resources": 1},
            "elasticache": {"non_compliant_resources": 1},
        }
    }

    recommendations = await generate_recommendations(results)

    # Should include recommendations from all services plus general ones
    assert len(recommendations) >= 10

    # Check for service-specific recommendations
    assert any("Enable default encryption" in rec for rec in recommendations)  # S3
    assert any("Enable default EBS encryption" in rec for rec in recommendations)  # EBS
    assert any("Enable encryption for all RDS instances" in rec for rec in recommendations)  # RDS
    assert any(
        "customer-managed KMS keys for DynamoDB tables" in rec for rec in recommendations
    )  # DynamoDB
    assert any("Create new encrypted EFS filesystems" in rec for rec in recommendations)  # EFS
    assert any("Use Redis instead of Memcached" in rec for rec in recommendations)  # ElastiCache


@pytest.mark.asyncio
async def test_generate_recommendations_with_all_compliant():
    """Test recommendations generation when all resources are compliant."""
    results = {
        "compliance_by_service": {
            "s3": {"non_compliant_resources": 0},
            "ebs": {"non_compliant_resources": 0},
            "rds": {"non_compliant_resources": 0},
        }
    }

    recommendations = await generate_recommendations(results)

    # Should only include general recommendations
    assert len(recommendations) == 2
    assert any(
        "customer-managed KMS keys instead of AWS managed keys" in rec for rec in recommendations
    )
    assert any("key rotation policy" in rec for rec in recommendations)


@pytest.mark.asyncio
async def test_generate_recommendations_empty_results():
    """Test recommendations generation with empty results."""
    results = {"compliance_by_service": {}}

    recommendations = await generate_recommendations(results)

    # Should only include general recommendations
    assert len(recommendations) == 2
    assert any(
        "customer-managed KMS keys instead of AWS managed keys" in rec for rec in recommendations
    )
    assert any("key rotation policy" in rec for rec in recommendations)
