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
"""MCP Server for AWS Pricing Calculator automation."""

import sys
from typing import Any, Optional

from loguru import logger
from mcp.server.fastmcp import Context, FastMCP

from awslabs.aws_calculator_mcp_server.calculator import AWSCalculatorAutomation
from awslabs.aws_calculator_mcp_server.service_fields import SERVICE_FIELDS


logger.remove()
logger.add(sys.stderr, level="INFO")

mcp = FastMCP(
    "awslabs.aws-calculator-mcp-server",
    instructions="Automates AWS Pricing Calculator (calculator.aws) using Playwright to generate shareable estimate links with accurate pricing for all 159 AWS services.",
)

_calculator: Optional[AWSCalculatorAutomation] = None


def _get_calculator() -> AWSCalculatorAutomation:
    global _calculator
    if _calculator is None:
        _calculator = AWSCalculatorAutomation(headless=True)
    return _calculator


def _save_result_json(result: dict, output_file: str):
    """Save estimate result to a JSON file."""
    import json
    from datetime import datetime, timezone
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **result,
    }
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)


@mcp.tool()
async def create_estimate(
    ctx: Context,
    services: list[dict[str, Any]],
    output_file: str = "",
) -> dict[str, Any]:
    """Create an AWS Pricing Calculator estimate and return a shareable link.

    This tool automates calculator.aws via browser to add services with exact
    configurations and generate a public shareable link.

    Args:
        services: List of service configurations. Each service dict should have:
            - service_name (str): Exact name as in calculator (use list_service_fields to discover)
            - region (str): Region display name (default: "South America (Sao Paulo)")
            - config (dict): Field configurations using the EXACT field labels from
              the calculator UI. Use the field names from list_service_fields.

    All 159 AWS services are supported. Use list_service_fields() for full details.

    Common services by category:

    COMPUTE: Amazon EC2, AWS Fargate, AWS Lambda, AWS App Runner, Amazon EKS
    DATABASES: Amazon RDS for PostgreSQL/MySQL/Oracle/SQL Server/MariaDB/Db2,
               Aurora PostgreSQL/MySQL, DynamoDB, ElastiCache, MemoryDB,
               DocumentDB, Neptune, Redshift, Amazon Keyspaces
    STORAGE: Amazon Simple Storage Service (S3), Elastic Block Store (EBS),
             Elastic File System (EFS), FSx (Lustre/ONTAP/OpenZFS/Windows),
             Elastic Container Registry, AWS Backup
    NETWORKING: Elastic Load Balancing, Amazon Virtual Private Cloud (VPC),
               Amazon CloudFront, Amazon Route 53, Amazon API Gateway,
               AWS Direct Connect, AWS Network Firewall
    MESSAGING: Amazon Simple Queue Service (SQS), Amazon Simple Notification Service (SNS),
               Amazon EventBridge, Amazon Kinesis Data Streams, Amazon MQ,
               Amazon Managed Streaming for Apache Kafka (MSK)
    ANALYTICS: Amazon Athena, Amazon EMR, Amazon OpenSearch Service,
               AWS Glue, Amazon Redshift, Amazon Kinesis Data Streams
    ML/AI: Amazon Bedrock, Amazon SageMaker, Amazon Rekognition,
            Amazon Textract, Amazon Comprehend, Amazon Polly, Amazon Translate
    SECURITY: AWS Web Application Firewall (WAF), AWS Shield, AWS Secrets Manager,
              AWS Key Management Service, Amazon Cognito, Amazon GuardDuty, Amazon Inspector
    DEVOPS: AWS CodeBuild, AWS CodePipeline, AWS Step Functions,
            AWS CloudTrail, Amazon CloudWatch, AWS Systems Manager

    Special config key prefixes:
        "_autosuggest:<placeholder>": Use autosuggest input (e.g., instance type)
        "_radio": Click a radio button by its label text
        "_change:<current_text>": Change a dropdown by its current displayed value
        "<field>_unit": Set the Unit dropdown for a field

    Returns:
        Dict with estimate_url, monthly_cost, and service results.

    Example:
        services=[
            {"service_name": "Amazon EC2", "config": {"Number of instances": "2"}},
            {"service_name": "Amazon Simple Storage Service (S3)", "config": {"S3 Standard storage": "500"}},
            {"service_name": "AWS Lambda", "config": {"Number of requests": "1000000", "Duration of each request (in ms)": "200"}},
            {"service_name": "Amazon DynamoDB", "config": {"Average item size (all attributes)": "1", "Baseline write rate": "100", "Baseline read rate": "100"}}
        ]
    """
    await ctx.info(f"Creating estimate with {len(services)} service(s)...")

    calculator = _get_calculator()
    try:
        result = await calculator.create_estimate(services)
        await ctx.info(f"Estimate created: {result.get('estimate_url', 'N/A')}")
        if output_file:
            _save_result_json(result, output_file)
            await ctx.info(f"Result saved: {output_file}")
        return result
    except Exception as e:
        logger.error(f"Failed: {e}")
        return {"error": str(e)}
    finally:
        await calculator.close()


@mcp.tool()
async def update_estimate(
    ctx: Context,
    estimate_url: str,
    add_services: list[dict[str, Any]] = None,
    remove_services: list[str] = None,
    output_file: str = "",
) -> dict[str, Any]:
    """Update an existing AWS Calculator estimate by adding or removing services.

    Loads the estimate from its shareable URL, applies changes, and returns
    a new shareable link with the updated configuration.

    Args:
        estimate_url: Existing calculator.aws estimate URL
            (e.g., "https://calculator.aws/#/estimate?id=abc123")
        add_services: Optional list of services to add (same format as create_estimate)
        remove_services: Optional list of service names to remove from the estimate
        output_file: Optional path to save the result as JSON. Empty string disables.

    Returns:
        Dict with new estimate_url, monthly_cost, and service details.

    Example:
        update_estimate(
            estimate_url="https://calculator.aws/#/estimate?id=abc123",
            add_services=[{"service_name": "AWS Data Transfer", "config": {"Enter Amount": "800"}}],
            remove_services=["AWS Shield"],
            output_file="/tmp/estimate-result.json"
        )
    """
    await ctx.info(f"Updating estimate: {estimate_url}")

    calculator = _get_calculator()
    try:
        result = await calculator.update_estimate(
            estimate_url=estimate_url,
            add_services=add_services or [],
            remove_services=remove_services or [],
        )
        await ctx.info(f"Estimate updated: {result.get('estimate_url', 'N/A')}")
        if output_file:
            _save_result_json(result, output_file)
            await ctx.info(f"Result saved: {output_file}")
        return result
    except Exception as e:
        logger.error(f"Failed to update: {e}")
        return {"error": str(e)}
    finally:
        await calculator.close()


@mcp.tool()
async def list_service_fields(
    ctx: Context,
    service_name: str = "",
) -> dict[str, Any]:
    """List available calculator services and their configurable fields.

    Args:
        service_name: Optional - filter to a specific service name.
                     Leave empty to list all available services.

    Returns:
        Dict of service names mapped to their field descriptions and config keys.
    """
    if service_name:
        for name, info in SERVICE_FIELDS.items():
            if service_name.lower() in name.lower():
                return {name: info}
        return {"error": f"Service '{service_name}' not found. Available: {list(SERVICE_FIELDS.keys())}"}

    return {name: info["description"] for name, info in SERVICE_FIELDS.items()}


def main():
    """Run the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
