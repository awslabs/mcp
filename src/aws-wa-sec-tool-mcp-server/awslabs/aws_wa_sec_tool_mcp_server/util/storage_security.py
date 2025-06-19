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

"""Utility functions for checking AWS storage services encryption and security."""

from typing import Any, Dict, List

import boto3
import botocore.exceptions
from mcp.server.fastmcp import Context


async def check_storage_encryption(
    region: str,
    services: List[str],
    session: boto3.Session,
    ctx: Context,
    include_unencrypted_only: bool = False,
) -> Dict[str, Any]:
    """Check AWS storage resources for encryption and security best practices.

    Args:
        region: AWS region to check
        services: List of storage services to check
        session: boto3 Session for AWS API calls
        ctx: MCP context for error reporting
        include_unencrypted_only: Whether to include only unencrypted resources in the results

    Returns:
        Dictionary with storage encryption and security status
    """
    results = {
        "region": region,
        "services_checked": services,
        "resources_checked": 0,
        "compliant_resources": 0,
        "non_compliant_resources": 0,
        "compliance_by_service": {},
        "resource_details": [],
        "recommendations": [],
    }

    # Find all storage resources using Resource Explorer
    storage_resources = await find_storage_resources(region, session, services, ctx)

    # Check each service as requested
    if "s3" in services:
        s3_client = session.client("s3", region_name=region)
        s3_results = await check_s3_buckets(region, s3_client, ctx, storage_resources)
        await _update_results(results, s3_results, "s3", include_unencrypted_only)

    # Generate overall recommendations based on findings
    results["recommendations"] = await generate_recommendations(results)

    return results


async def _update_results(
    main_results: Dict[str, Any],
    service_results: Dict[str, Any],
    service_name: str,
    include_unencrypted_only: bool,
) -> None:
    """Update the main results dictionary with service-specific results."""
    # Update resource counts
    main_results["resources_checked"] += service_results.get("resources_checked", 0)
    main_results["compliant_resources"] += service_results.get("compliant_resources", 0)
    main_results["non_compliant_resources"] += service_results.get("non_compliant_resources", 0)

    # Add service-specific compliance info
    main_results["compliance_by_service"][service_name] = {
        "resources_checked": service_results.get("resources_checked", 0),
        "compliant_resources": service_results.get("compliant_resources", 0),
        "non_compliant_resources": service_results.get("non_compliant_resources", 0),
    }

    # Add resource details
    for resource in service_results.get("resource_details", []):
        if not include_unencrypted_only or not resource.get("compliant", True):
            main_results["resource_details"].append(resource)


async def generate_recommendations(results: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on the scan results."""
    recommendations = []

    # Check S3 recommendations
    if "s3" in results.get("compliance_by_service", {}):
        s3_results = results["compliance_by_service"]["s3"]
        if s3_results.get("non_compliant_resources", 0) > 0:
            recommendations.append("Enable default encryption for all S3 buckets")
            recommendations.append("Enable block public access settings at the account level")

    # General recommendations
    recommendations.append(
        "Use customer-managed KMS keys instead of AWS managed keys for sensitive data"
    )
    recommendations.append("Implement a key rotation policy for all customer-managed KMS keys")

    return recommendations


async def find_storage_resources(
    region: str, session: boto3.Session, services: List[str], ctx: Context
) -> Dict[str, Any]:
    """Find storage resources using Resource Explorer."""
    try:
        print(
            f"[DEBUG:StorageSecurity] Finding storage resources in {region} using Resource Explorer"
        )

        # Initialize resource explorer client
        resource_explorer = session.client("resource-explorer-2", region_name=region)

        # Try to get the default view for Resource Explorer
        print("[DEBUG:StorageSecurity] Listing Resource Explorer views...")
        views = resource_explorer.list_views()
        print(f"[DEBUG:StorageSecurity] Found {len(views.get('Views', []))} views")

        default_view = None
        # Find the default view
        for view in views.get("Views", []):
            print(f"[DEBUG:StorageSecurity] View: {view.get('ViewArn')}")
            if view.get("Filters", {}).get("FilterString", "") == "":
                default_view = view.get("ViewArn")
                print(f"[DEBUG:StorageSecurity] Found default view: {default_view}")
                break

        if not default_view:
            print("[DEBUG:StorageSecurity] No default view found. Cannot use Resource Explorer.")
            await ctx.warning(
                "No default Resource Explorer view found. Will fall back to direct service API calls."
            )
            return {"error": "No default Resource Explorer view found"}

        # Build filter strings for each service
        service_filters = []

        if "s3" in services:
            service_filters.append("service:s3")
        if "ebs" in services:
            service_filters.append("service:ec2 resourcetype:ec2:volume")
        if "rds" in services:
            service_filters.append("service:rds")
        if "dynamodb" in services:
            service_filters.append("service:dynamodb")
        if "efs" in services:
            service_filters.append("service:elasticfilesystem")
        if "elasticache" in services:
            service_filters.append("service:elasticache")

        # Combine with OR
        filter_string = " OR ".join(service_filters)
        print(f"[DEBUG:StorageSecurity] Using filter string: {filter_string}")

        # Get resources
        resources = []
        paginator = resource_explorer.get_paginator("list_resources")
        page_iterator = paginator.paginate(
            Filters={"FilterString": filter_string}, MaxResults=100, ViewArn=default_view
        )

        for page in page_iterator:
            resources.extend(page.get("Resources", []))

        print(f"[DEBUG:StorageSecurity] Found {len(resources)} total storage resources")

        # Organize by service
        resources_by_service = {}

        for resource in resources:
            arn = resource.get("Arn", "")
            if ":" in arn:
                service = arn.split(":")[2]

                # Map EC2 volumes to 'ebs'
                if service == "ec2" and "volume" in arn:
                    service = "ebs"

                if service not in resources_by_service:
                    resources_by_service[service] = []

                resources_by_service[service].append(resource)

        # Print summary
        for service, svc_resources in resources_by_service.items():
            print(f"[DEBUG:StorageSecurity] {service}: {len(svc_resources)} resources")

        return {
            "total_resources": len(resources),
            "resources_by_service": resources_by_service,
            "resources": resources,
        }

    except botocore.exceptions.BotoCoreError as e:
        print(f"[DEBUG:StorageSecurity] Error finding storage resources: {e}")
        await ctx.error(f"Error finding storage resources: {e}")
        return {"error": str(e), "resources_by_service": {}}


async def check_s3_buckets(
    region: str, s3_client: Any, ctx: Context, storage_resources: Dict[str, Any]
) -> Dict[str, Any]:
    """Check S3 buckets for encryption and security best practices."""
    print(f"[DEBUG:StorageSecurity] Checking S3 buckets in {region}")

    results = {
        "service": "s3",
        "resources_checked": 0,
        "compliant_resources": 0,
        "non_compliant_resources": 0,
        "resource_details": [],
    }

    try:
        # Get bucket list - either from Resource Explorer or directly
        buckets = []

        if "error" not in storage_resources and "s3" in storage_resources.get(
            "resources_by_service", {}
        ):
            # Use Resource Explorer results
            s3_resources = storage_resources["resources_by_service"]["s3"]
            for resource in s3_resources:
                arn = resource.get("Arn", "")
                if ":bucket/" in arn or ":bucket:" in arn:
                    bucket_name = arn.split(":")[-1]
                    buckets.append(bucket_name)
        else:
            # Fall back to direct API call
            response = s3_client.list_buckets()
            for bucket in response["Buckets"]:
                # Check if bucket is in the specified region
                try:
                    location = s3_client.get_bucket_location(Bucket=bucket["Name"])
                    bucket_region = location.get("LocationConstraint")
                    # us-east-1 returns None for the location constraint
                    if bucket_region is None:
                        bucket_region = "us-east-1"

                    if bucket_region == region:
                        buckets.append(bucket["Name"])
                except Exception as e:
                    print(
                        f"[DEBUG:StorageSecurity] Error getting location for bucket {bucket['Name']}: {e}"
                    )
                    await ctx.warning(f"Error getting location for bucket {bucket['Name']}: {e}")

        print(f"[DEBUG:StorageSecurity] Found {len(buckets)} S3 buckets in region {region}")
        results["resources_checked"] = len(buckets)

        # Check each bucket
        for bucket_name in buckets:
            bucket_result = {
                "name": bucket_name,
                "arn": f"arn:aws:s3:::{bucket_name}",
                "type": "s3",
                "compliant": True,
                "issues": [],
                "checks": {},
            }

            # Check default encryption
            try:
                encryption = s3_client.get_bucket_encryption(Bucket=bucket_name)
                encryption_rules = encryption.get("ServerSideEncryptionConfiguration", {}).get(
                    "Rules", []
                )

                if encryption_rules:
                    encryption_type = (
                        encryption_rules[0]
                        .get("ApplyServerSideEncryptionByDefault", {})
                        .get("SSEAlgorithm")
                    )
                    bucket_result["checks"]["default_encryption"] = {
                        "enabled": True,
                        "type": encryption_type,
                    }

                    # Check if using CMK
                    kms_key = (
                        encryption_rules[0]
                        .get("ApplyServerSideEncryptionByDefault", {})
                        .get("KMSMasterKeyID")
                    )
                    bucket_result["checks"]["using_cmk"] = kms_key is not None

                    # Check if using bucket key
                    bucket_key_enabled = encryption_rules[0].get("BucketKeyEnabled", False)
                    bucket_result["checks"]["bucket_key_enabled"] = bucket_key_enabled
                else:
                    bucket_result["compliant"] = False
                    bucket_result["issues"].append("Default encryption not enabled")
                    bucket_result["checks"]["default_encryption"] = {"enabled": False}
                    bucket_result["checks"]["using_cmk"] = False
            except Exception:
                # No encryption configuration found
                bucket_result["compliant"] = False
                bucket_result["issues"].append("Default encryption not enabled")
                bucket_result["checks"]["default_encryption"] = {"enabled": False}
                bucket_result["checks"]["using_cmk"] = False

            # Check public access block
            try:
                public_access = s3_client.get_public_access_block(Bucket=bucket_name)
                block_public_access = all(
                    [
                        public_access["PublicAccessBlockConfiguration"]["BlockPublicAcls"],
                        public_access["PublicAccessBlockConfiguration"]["IgnorePublicAcls"],
                        public_access["PublicAccessBlockConfiguration"]["BlockPublicPolicy"],
                        public_access["PublicAccessBlockConfiguration"]["RestrictPublicBuckets"],
                    ]
                )

                bucket_result["checks"]["block_public_access"] = {
                    "enabled": block_public_access,
                    "configuration": public_access["PublicAccessBlockConfiguration"],
                }

                if not block_public_access:
                    bucket_result["compliant"] = False
                    bucket_result["issues"].append("Public access not fully blocked")
            except Exception as e:
                print(
                    f"[DEBUG:StorageSecurity] Error checking public access block for {bucket_name}: {e}"
                )
                bucket_result["checks"]["block_public_access"] = {
                    "enabled": False,
                    "error": str(e),
                }
                bucket_result["compliant"] = False
                bucket_result["issues"].append("Public access block status unknown")

            # Generate remediation steps
            bucket_result["remediation"] = []

            if not bucket_result["checks"].get("default_encryption", {}).get("enabled", False):
                bucket_result["remediation"].append(
                    "Enable default encryption using SSE-KMS or SSE-S3"
                )

            if not bucket_result["checks"].get("block_public_access", {}).get("enabled", False):
                bucket_result["remediation"].append(
                    "Enable block public access settings for this bucket"
                )

            # Update counts
            if bucket_result["compliant"]:
                results["compliant_resources"] += 1
            else:
                results["non_compliant_resources"] += 1

            results["resource_details"].append(bucket_result)

        return results

    except botocore.exceptions.BotoCoreError as e:
        print(f"[DEBUG:StorageSecurity] Error checking S3 buckets: {e}")
        await ctx.error(f"Error checking S3 buckets: {e}")
        return {
            "service": "s3",
            "error": str(e),
            "resources_checked": 0,
            "compliant_resources": 0,
            "non_compliant_resources": 0,
            "resource_details": [],
        }
