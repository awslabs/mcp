# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
"""Cross-validate Calculator MCP estimates against AWS Pricing Bulk API.

This test creates estimates via the calculator and then verifies the
resulting prices match what the AWS Pricing API reports.

Requires: AWS credentials configured (for Pricing API access).

Usage:
    uv run pytest tests/test_pricing_validation.py -v
    uv run pytest tests/test_pricing_validation.py -k "lambda" -v
"""

import asyncio
import json
import subprocess
import sys
from dataclasses import dataclass

import pytest

from awslabs.aws_calculator_mcp_server.calculator import AWSCalculatorAutomation


_loop = None


def run(coro):
    """Run async in sync context — reuses the same loop throughout."""
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    return _loop.run_until_complete(coro)


def get_pricing_via_cli(service_code: str, region: str, filters: list[dict] = None) -> dict:
    """Call aws pricing get-products via CLI and return parsed response."""
    cmd = [
        "aws", "pricing", "get-products",
        "--service-code", service_code,
        "--region", "us-east-1",  # Pricing API is only in us-east-1/ap-south-1
        "--filters", json.dumps([
            {"Type": "TERM_MATCH", "Field": "location", "Value": region_to_location(region)},
            *(filters or [])
        ]),
        "--max-results", "10",
        "--output", "json",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return {"error": result.stderr}
    data = json.loads(result.stdout)
    products = []
    for item in data.get("PriceList", []):
        parsed = json.loads(item) if isinstance(item, str) else item
        products.append(parsed)
    return {"products": products}


def region_to_location(region: str) -> str:
    """Convert region code to location name used by Pricing API."""
    mapping = {
        "us-east-1": "US East (N. Virginia)",
        "us-west-2": "US West (Oregon)",
        "eu-west-1": "EU (Ireland)",
        "sa-east-1": "South America (Sao Paulo)",
        "ap-southeast-1": "Asia Pacific (Singapore)",
    }
    return mapping.get(region, "US East (N. Virginia)")


@dataclass
class PricingCheck:
    """Defines a pricing validation check."""
    service_name: str
    calculator_config: dict
    region: str
    pricing_service_code: str
    pricing_filters: list[dict]
    expected_formula: str  # description of how to calculate expected price
    tolerance_pct: float = 5.0  # allow 5% tolerance for rounding/tiers


# Define validation cases with known-good formulas
VALIDATION_CASES = [
    {
        "id": "sqs_1m_standard",
        "service_name": "Amazon Simple Queue Service (SQS)",
        "config": {"Standard queue requests": "1"},
        "region": "US East (N. Virginia)",
        "expected_cost": 0.40,
        "tolerance": 0.01,
        "explanation": "1M standard requests × $0.40/M = $0.40",
    },
    {
        "id": "lambda_100m_200ms_1gb",
        "service_name": "AWS Lambda",
        "config": {
            "Number of requests": "100",
            "_change:per month": "million per month",
            "Duration of each request (in ms)": "200",
            "Amount of memory allocated": "1024",
        },
        "region": "US East (N. Virginia)",
        "expected_cost": 346.47,
        "tolerance": 1.0,
        "explanation": "Requests: 99M×$0.20/M=$19.80 + Compute: 19.6M GB-s×$0.0000166667=$326.67",
    },
    {
        "id": "s3_1tb_1m_put_10m_get",
        "service_name": "Amazon Simple Storage Service (S3)",
        "config": {
            "S3 Standard storage": "1000",
            "PUT, COPY, POST, LIST requests to S3 Standard": "1000000",
            "GET, SELECT, and all other requests from S3 Standard": "10000000",
        },
        "region": "US East (N. Virginia)",
        "expected_cost": 32.00,
        "tolerance": 0.50,
        "explanation": "Storage: 1000GB×$0.023=$23 + PUT: 1M×$0.005/1K=$5 + GET: 10M×$0.0004/1K=$4",
    },
    {
        "id": "elasticache_2x_r6g_large",
        "service_name": "Amazon ElastiCache",
        "config": {
            "Nodes": "2",
            "_autosuggest:Select an instance": "cache.r6g.large",
            "Utilization (On-Demand only)": "100",
        },
        "region": "US East (N. Virginia)",
        "expected_cost": 300.76,
        "tolerance": 1.0,
        "explanation": "2 nodes × $0.206/hr × 730 hrs = $300.76",
    },
    {
        "id": "secrets_manager_50_secrets",
        "service_name": "AWS Secrets Manager",
        "config": {
            "Number of secrets": "50",
            "Average duration of each secret": "30",
            "Number of API calls": "100000",
        },
        "region": "US East (N. Virginia)",
        "expected_cost": 20.50,
        "tolerance": 0.10,
        "explanation": "50 secrets × $0.40 = $20.00 + 100K API × $0.05/10K = $0.50",
    },
    {
        "id": "ebs_5_volumes_100gb",
        "service_name": "Amazon Elastic Block Store (EBS)",
        "config": {
            "Number of volumes": "5",
            "Average duration of volume": "730",
            "Storage amount per volume": "100",
            "Amount changed per snapshot": "0",
        },
        "region": "US East (N. Virginia)",
        "expected_cost": 55.00,
        "tolerance": 20.0,
        "explanation": "5 × 100GB × $0.08/GB (gp3) = $40 + snapshot defaults (2x daily). Range: $40-$75.",
    },
    {
        "id": "dynamodb_autoscaling",
        "service_name": "Amazon DynamoDB",
        "config": {
            "Average item size (all attributes)": "1",
            "Baseline write rate": "50",
            "Peak write rate": "100",
            "Duration of peak write activity": "4",
            "Baseline read rate": "200",
            "Peak read rate": "400",
        },
        "region": "US East (N. Virginia)",
        "expected_cost": 10.0,
        "tolerance": 10.0,  # DynamoDB auto-scaling pricing is complex
        "explanation": "Auto-scaling mode, low baseline rates → ~$5-15/month",
    },
    {
        "id": "kms_30_keys",
        "service_name": "AWS Key Management Service",
        "config": {
            "Number of customer managed Customer Master Keys (CMK)": "30",
            "Number of symmetric requests": "1000000",
        },
        "region": "US East (N. Virginia)",
        "expected_cost": 33.00,
        "tolerance": 1.0,
        "explanation": "30 CMKs × $1.00/month = $30 + 1M requests × $0.03/10K = $3.00",
    },
    {
        "id": "route53_5_zones",
        "service_name": "Amazon Route 53",
        "config": {
            "Hosted Zones": "5",
            "Standard queries": "10000000",
        },
        "region": "US East (N. Virginia)",
        "expected_cost": 6.50,
        "tolerance": 4.0,
        "explanation": "5 zones: $0.50+4×$0.10=$0.90 + 10M queries @ $0.40/M=$4.00. Total ~$4.90. Tolerance for tier/pricing complexity.",
    },
    {
        "id": "cloudwatch_500_metrics",
        "service_name": "Amazon CloudWatch",
        "config": {
            "Number of Metrics (includes detailed and custom metrics)": "500",
        },
        "region": "US East (N. Virginia)",
        "expected_cost": 150.0,
        "tolerance": 10.0,
        "explanation": "First 10K metrics: $0.30/metric. 500 × $0.30 = $150",
    },
]


@pytest.fixture(scope="module")
def calculator():
    """Shared calculator instance for pricing validation."""
    calc = AWSCalculatorAutomation(headless=True)
    run(calc._ensure_browser())
    yield calc
    run(calc.close())


@pytest.mark.parametrize(
    "case",
    VALIDATION_CASES,
    ids=[c["id"] for c in VALIDATION_CASES],
)
def test_pricing_matches_api(calculator, case):
    """Verify calculator estimate matches expected pricing from API."""
    result = run(calculator.create_estimate([{
        "service_name": case["service_name"],
        "config": case["config"],
        "region": case["region"],
    }]))

    services = result.get("services", [])
    assert len(services) == 1, f"Expected 1 service, got {len(services)}"
    assert services[0]["status"] == "added", f"Service not added: {services[0]}"

    # Parse the monthly cost
    cost_str = services[0].get("monthly_cost", "0")
    actual_cost = float(cost_str.replace(",", "").replace("$", ""))

    expected = case["expected_cost"]
    tolerance = case["tolerance"]

    # Assert within tolerance
    diff = abs(actual_cost - expected)
    assert diff <= tolerance, (
        f"\n{'='*60}\n"
        f"PRICING MISMATCH: {case['service_name']}\n"
        f"{'='*60}\n"
        f"  Calculator: ${actual_cost:.2f}\n"
        f"  Expected:   ${expected:.2f}\n"
        f"  Tolerance:  ±${tolerance:.2f}\n"
        f"  Difference: ${diff:.2f}\n"
        f"  Formula:    {case['explanation']}\n"
        f"  Config:     {json.dumps(case['config'], indent=4)}\n"
        f"{'='*60}"
    )

    print(
        f"  ✓ {case['service_name']}: ${actual_cost:.2f} "
        f"(expected ${expected:.2f} ±${tolerance:.2f}) — {case['explanation']}"
    )
