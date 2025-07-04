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

"""Test fixtures for the cost-analysis-mcp-server."""

import pytest
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = AsyncMock()
    context.info = AsyncMock()
    context.error = AsyncMock()
    context.warning = AsyncMock()
    return context


@pytest.fixture
def sample_pricing_data_web() -> Dict[str, Any]:
    """Sample pricing data from web scraping."""
    return {
        'status': 'success',
        'service_name': 'lambda',
        'data': """
        AWS Lambda Pricing

        AWS Lambda lets you run code without provisioning or managing servers. You pay only for the compute time you consume.

        Pricing Details:
        - $0.20 per 1 million requests
        - $0.0000166667 for every GB-second

        Free Tier:
        - 1 million free requests per month
        - 400,000 GB-seconds of compute time per month

        Factors that affect Lambda pricing:
        - Number of requests
        - Duration of execution
        - Memory allocated
        - Data transfer
        """,
        'message': 'Retrieved pricing for lambda from AWS Pricing url',
    }


@pytest.fixture
def sample_pricing_data_api() -> Dict[str, Any]:
    """Sample pricing data from AWS Price List API."""
    return {
        'status': 'success',
        'service_name': 'AWSLambda',
        'data': [
            {
                'product': {
                    'attributes': {
                        'productFamily': 'Serverless',
                        'description': 'Run code without thinking about servers',
                    },
                },
                'terms': {
                    'OnDemand': {
                        'rate1': {
                            'priceDimensions': {
                                'dim1': {
                                    'unit': 'requests',
                                    'pricePerUnit': {'USD': '0.20'},
                                    'description': 'per 1M requests',
                                },
                            },
                        },
                    },
                },
            },
        ],
        'message': 'Retrieved pricing for AWSLambda in us-west-2 from AWS Pricing API',
    }


@pytest.fixture
def sample_cdk_project(tmp_path: Path) -> str:
    """Create a sample CDK project for testing."""
    project_dir = tmp_path / 'sample-cdk-project'
    project_dir.mkdir()

    # Create Python CDK file
    python_stack = project_dir / 'app.py'
    python_stack.write_text("""
from aws_cdk import (
    aws_lambda as lambda_,
    aws_dynamodb as dynamodb,
    App, Stack
)

class MyStack(Stack):
    def __init__(self, scope, id):
        super().__init__(scope, id)

        # Create DynamoDB table
        table = dynamodb.Table(
            self, 'Table',
            partition_key={'name': 'id', 'type': dynamodb.AttributeType.STRING}
        )

        # Create Lambda function
        lambda_.Function(
            self, 'Function',
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler='index.handler',
            code=lambda_.Code.from_asset('lambda')
        )

app = App()
MyStack(app, 'MyStack')
app.synth()
    """)

    # Create TypeScript CDK file
    ts_dir = project_dir / 'lib'
    ts_dir.mkdir()
    ts_stack = ts_dir / 'stack.ts'
    ts_stack.write_text("""
import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';

export class MyStack extends cdk.Stack {
  constructor(scope: cdk.App, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Create S3 bucket
    const bucket = new s3.Bucket(this, 'MyBucket');

    // Create IAM role
    new iam.Role(this, 'MyRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
    });
  }
}
    """)

    return str(project_dir)


@pytest.fixture
def temp_output_dir() -> Generator[str, None, None]:
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_boto3() -> MagicMock:
    """Mock boto3 for testing AWS API calls."""
    mock = MagicMock()

    # Mock pricing client
    pricing_client = MagicMock()
    pricing_client.get_products.return_value = {
        'PriceList': [
            {
                'product': {
                    'attributes': {
                        'productFamily': 'Serverless',
                        'description': 'Run code without thinking about servers',
                    },
                },
                'terms': {
                    'OnDemand': {
                        'rate1': {
                            'priceDimensions': {
                                'dim1': {
                                    'unit': 'requests',
                                    'pricePerUnit': {'USD': '0.20'},
                                    'description': 'per 1M requests',
                                },
                            },
                        },
                    },
                },
            },
        ],
    }

    # Mock session
    session = MagicMock()
    session.client.return_value = pricing_client
    mock.Session.return_value = session

    return mock
