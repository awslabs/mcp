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
"""Pytest fixtures for AWS Trusted Advisor MCP Server tests."""

import pytest
from typing import Any, Dict, List


@pytest.fixture
def check_summary_data() -> Dict[str, Any]:
    """Return a sample Trusted Advisor check summary."""
    return {
        'arn': 'arn:aws:trustedadvisor:::check/abc123',
        'id': 'abc123',
        'name': 'Amazon S3 Bucket Permissions',
        'description': 'Checks the permissions on your Amazon S3 buckets.',
        'pillar': 'security',
        'awsService': 'Amazon S3',
        'source': 'ta_check',
    }


@pytest.fixture
def check_summaries_data() -> List[Dict[str, Any]]:
    """Return a list of sample Trusted Advisor check summaries."""
    return [
        {
            'arn': 'arn:aws:trustedadvisor:::check/abc123',
            'id': 'abc123',
            'name': 'Amazon S3 Bucket Permissions',
            'description': 'Checks the permissions on your Amazon S3 buckets.',
            'pillar': 'security',
            'awsService': 'Amazon S3',
            'source': 'ta_check',
        },
        {
            'arn': 'arn:aws:trustedadvisor:::check/def456',
            'id': 'def456',
            'name': 'Low Utilization Amazon EC2 Instances',
            'description': 'Checks for EC2 instances with low utilization.',
            'pillar': 'cost_optimizing',
            'awsService': 'Amazon EC2',
            'source': 'ta_check',
        },
        {
            'arn': 'arn:aws:trustedadvisor:::check/ghi789',
            'id': 'ghi789',
            'name': 'Security Groups - Unrestricted Access',
            'description': 'Checks for security groups with unrestricted access.',
            'pillar': 'security',
            'awsService': 'Amazon EC2',
            'source': 'ta_check',
        },
    ]


@pytest.fixture
def recommendation_summary_data() -> Dict[str, Any]:
    """Return a sample recommendation summary."""
    return {
        'arn': 'arn:aws:trustedadvisor::123456789012:recommendation/rec-001',
        'name': 'Low Utilization Amazon EC2 Instances',
        'status': 'warning',
        'pillar': 'cost_optimizing',
        'awsService': 'Amazon EC2',
        'source': 'ta_check',
        'resourcesAggregates': {
            'okCount': 5,
            'warningCount': 3,
            'errorCount': 0,
        },
        'pillarSpecificAggregates': {
            'costOptimizing': {
                'estimatedMonthlySavings': 150.50,
                'estimatedMonthlySavingsCurrency': 'USD',
            },
        },
        'lastUpdatedAt': '2024-01-15T10:30:00Z',
    }


@pytest.fixture
def recommendation_summaries_data() -> List[Dict[str, Any]]:
    """Return a list of sample recommendation summaries."""
    return [
        {
            'arn': 'arn:aws:trustedadvisor::123456789012:recommendation/rec-001',
            'name': 'Low Utilization Amazon EC2 Instances',
            'status': 'warning',
            'pillar': 'cost_optimizing',
            'awsService': 'Amazon EC2',
            'source': 'ta_check',
            'resourcesAggregates': {
                'okCount': 5,
                'warningCount': 3,
                'errorCount': 0,
            },
            'pillarSpecificAggregates': {
                'costOptimizing': {
                    'estimatedMonthlySavings': 150.50,
                    'estimatedMonthlySavingsCurrency': 'USD',
                },
            },
            'lastUpdatedAt': '2024-01-15T10:30:00Z',
        },
        {
            'arn': 'arn:aws:trustedadvisor::123456789012:recommendation/rec-002',
            'name': 'Idle Load Balancers',
            'status': 'warning',
            'pillar': 'cost_optimizing',
            'awsService': 'Elastic Load Balancing',
            'source': 'ta_check',
            'resourcesAggregates': {
                'okCount': 2,
                'warningCount': 1,
                'errorCount': 0,
            },
            'pillarSpecificAggregates': {
                'costOptimizing': {
                    'estimatedMonthlySavings': 25.00,
                    'estimatedMonthlySavingsCurrency': 'USD',
                },
            },
            'lastUpdatedAt': '2024-01-14T08:00:00Z',
        },
    ]


@pytest.fixture
def recommendation_detail_data() -> Dict[str, Any]:
    """Return detailed recommendation data."""
    return {
        'arn': 'arn:aws:trustedadvisor::123456789012:recommendation/rec-001',
        'name': 'Low Utilization Amazon EC2 Instances',
        'description': (
            'Checks the Amazon Elastic Compute Cloud (Amazon EC2) instances that were '
            'running at any time during the last 14 days and alerts you if the daily CPU '
            'utilization or daily network I/O was 10% or less on 4 or more days.'
        ),
        'status': 'warning',
        'pillar': 'cost_optimizing',
        'awsService': 'Amazon EC2',
        'source': 'ta_check',
        'resourcesAggregates': {
            'okCount': 5,
            'warningCount': 3,
            'errorCount': 0,
        },
        'pillarSpecificAggregates': {
            'costOptimizing': {
                'estimatedMonthlySavings': 150.50,
                'estimatedMonthlySavingsCurrency': 'USD',
            },
        },
        'lifecycleStage': 'pending_response',
        'lastUpdatedAt': '2024-01-15T10:30:00Z',
        'createdAt': '2024-01-01T00:00:00Z',
    }


@pytest.fixture
def recommendation_resources_data() -> List[Dict[str, Any]]:
    """Return a list of recommendation resource summaries."""
    return [
        {
            'arn': 'arn:aws:ec2:us-east-1:123456789012:instance/i-0123456789abcdef0',
            'awsResourceId': 'i-0123456789abcdef0',
            'regionCode': 'us-east-1',
            'status': 'warning',
            'metadata': {
                'Instance Type': 't2.large',
                'Estimated Monthly Savings': '$50.00',
                'CPU Utilization (14-Day Avg)': '2.5%',
            },
            'lastUpdatedAt': '2024-01-15T10:30:00Z',
            'recommendationArn': 'arn:aws:trustedadvisor::123456789012:recommendation/rec-001',
        },
        {
            'arn': 'arn:aws:ec2:us-west-2:123456789012:instance/i-0abcdef1234567890',
            'awsResourceId': 'i-0abcdef1234567890',
            'regionCode': 'us-west-2',
            'status': 'warning',
            'metadata': {
                'Instance Type': 'm5.xlarge',
                'Estimated Monthly Savings': '$75.00',
                'CPU Utilization (14-Day Avg)': '4.1%',
            },
            'lastUpdatedAt': '2024-01-15T10:30:00Z',
            'recommendationArn': 'arn:aws:trustedadvisor::123456789012:recommendation/rec-001',
        },
    ]


@pytest.fixture
def security_recommendations_data() -> List[Dict[str, Any]]:
    """Return sample security recommendations."""
    return [
        {
            'arn': 'arn:aws:trustedadvisor::123456789012:recommendation/sec-001',
            'name': 'Security Groups - Unrestricted Access',
            'status': 'error',
            'pillar': 'security',
            'awsService': 'Amazon EC2',
            'resourcesAggregates': {
                'okCount': 10,
                'warningCount': 0,
                'errorCount': 2,
            },
            'lastUpdatedAt': '2024-01-15T10:30:00Z',
        },
        {
            'arn': 'arn:aws:trustedadvisor::123456789012:recommendation/sec-002',
            'name': 'MFA on Root Account',
            'status': 'ok',
            'pillar': 'security',
            'awsService': 'IAM',
            'resourcesAggregates': {
                'okCount': 1,
                'warningCount': 0,
                'errorCount': 0,
            },
            'lastUpdatedAt': '2024-01-15T10:30:00Z',
        },
        {
            'arn': 'arn:aws:trustedadvisor::123456789012:recommendation/sec-003',
            'name': 'S3 Bucket Permissions',
            'status': 'warning',
            'pillar': 'security',
            'awsService': 'Amazon S3',
            'resourcesAggregates': {
                'okCount': 8,
                'warningCount': 1,
                'errorCount': 0,
            },
            'lastUpdatedAt': '2024-01-14T08:00:00Z',
        },
    ]


@pytest.fixture
def service_limits_recommendations_data() -> List[Dict[str, Any]]:
    """Return sample service limits recommendations."""
    return [
        {
            'arn': 'arn:aws:trustedadvisor::123456789012:recommendation/sl-001',
            'name': 'VPC Elastic IP Address Limit',
            'status': 'warning',
            'pillar': 'service_limits',
            'awsService': 'Amazon VPC',
            'resourcesAggregates': {
                'okCount': 3,
                'warningCount': 1,
                'errorCount': 0,
            },
            'lastUpdatedAt': '2024-01-15T10:30:00Z',
        },
        {
            'arn': 'arn:aws:trustedadvisor::123456789012:recommendation/sl-002',
            'name': 'EC2 On-Demand Instances Limit',
            'status': 'error',
            'pillar': 'service_limits',
            'awsService': 'Amazon EC2',
            'resourcesAggregates': {
                'okCount': 5,
                'warningCount': 0,
                'errorCount': 1,
            },
            'lastUpdatedAt': '2024-01-15T10:30:00Z',
        },
    ]


@pytest.fixture
def organization_recommendations_data() -> List[Dict[str, Any]]:
    """Return sample organization recommendation summaries."""
    return [
        {
            'arn': 'arn:aws:trustedadvisor:::organization-recommendation/org-rec-001',
            'name': 'Low Utilization Amazon EC2 Instances',
            'status': 'warning',
            'pillar': 'cost_optimizing',
            'awsService': 'Amazon EC2',
            'resourcesAggregates': {
                'okCount': 50,
                'warningCount': 15,
                'errorCount': 0,
            },
            'pillarSpecificAggregates': {
                'costOptimizing': {
                    'estimatedMonthlySavings': 1500.00,
                    'estimatedMonthlySavingsCurrency': 'USD',
                },
            },
            'lifecycleStage': 'pending_response',
            'lastUpdatedAt': '2024-01-15T10:30:00Z',
        },
        {
            'arn': 'arn:aws:trustedadvisor:::organization-recommendation/org-rec-002',
            'name': 'Security Groups - Unrestricted Access',
            'status': 'error',
            'pillar': 'security',
            'awsService': 'Amazon EC2',
            'resourcesAggregates': {
                'okCount': 100,
                'warningCount': 5,
                'errorCount': 8,
            },
            'lastUpdatedAt': '2024-01-15T10:30:00Z',
        },
    ]
