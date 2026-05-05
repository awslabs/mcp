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

"""Common fixtures for well-architected-security-mcp-server tests."""

from unittest import mock

import pytest


@pytest.fixture
def mock_ctx():
    """Mock MCP context for testing."""
    ctx = mock.AsyncMock()
    ctx.error = mock.AsyncMock()
    ctx.warning = mock.AsyncMock()
    return ctx


@pytest.fixture
def mock_boto3_session():
    """Mock boto3 Session for testing."""
    with mock.patch("boto3.Session") as mock_session:
        session = mock.MagicMock()
        mock_session.return_value = session
        yield session


@pytest.fixture
def mock_resource_explorer_client(mock_boto3_session):
    """Mock Resource Explorer client for testing."""
    resource_explorer = mock.MagicMock()
    mock_boto3_session.client.return_value = resource_explorer

    # Set up default responses
    views_response = {
        "Views": [
            {
                "ViewArn": "arn:aws:resource-explorer-2:us-east-1:123456789012:view/default-view",
                "Filters": {"FilterString": ""},
            }
        ]
    }
    resource_explorer.list_views.return_value = views_response

    # Set up paginator for list_resources
    paginator = mock.MagicMock()
    resource_explorer.get_paginator.return_value = paginator

    # Mock empty resources by default
    page_iterator = mock.MagicMock()
    paginator.paginate.return_value = page_iterator
    page_iterator.__iter__.return_value = [{"Resources": []}]

    yield resource_explorer


@pytest.fixture
def mock_s3_client(mock_boto3_session):
    """Mock S3 client for testing."""
    s3_client = mock.MagicMock()
    mock_boto3_session.client.return_value = s3_client

    # Set up default responses
    s3_client.list_buckets.return_value = {
        "Buckets": [{"Name": "test-bucket-1"}, {"Name": "test-bucket-2"}]
    }

    # Mock bucket location
    s3_client.get_bucket_location.return_value = {"LocationConstraint": "us-east-1"}

    # Mock encryption configuration
    s3_client.get_bucket_encryption.return_value = {
        "ServerSideEncryptionConfiguration": {
            "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
        }
    }

    # Mock public access block
    s3_client.get_public_access_block.return_value = {
        "PublicAccessBlockConfiguration": {
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        }
    }

    yield s3_client


@pytest.fixture
def mock_elb_client(mock_boto3_session):
    """Mock ELB client for testing."""
    elb_client = mock.MagicMock()
    mock_boto3_session.client.return_value = elb_client

    # Set up default responses
    elb_client.describe_load_balancers.return_value = {
        "LoadBalancerDescriptions": [
            {
                "LoadBalancerName": "test-lb-1",
                "ListenerDescriptions": [
                    {
                        "Listener": {
                            "Protocol": "HTTPS",
                            "LoadBalancerPort": 443,
                            "InstanceProtocol": "HTTP",
                            "InstancePort": 80,
                        },
                        "PolicyNames": ["ELBSecurityPolicy-2016-08"],
                    }
                ],
            }
        ]
    }

    # Mock policy descriptions
    elb_client.describe_load_balancer_policies.return_value = {
        "PolicyDescriptions": [
            {
                "PolicyName": "ELBSecurityPolicy-2016-08",
                "PolicyAttributeDescriptions": [
                    {"AttributeName": "Protocol-TLSv1.2", "AttributeValue": "true"},
                    {"AttributeName": "Protocol-TLSv1.1", "AttributeValue": "false"},
                ],
            }
        ]
    }

    yield elb_client


@pytest.fixture
def mock_elbv2_client(mock_boto3_session):
    """Mock ELBv2 client for testing."""
    elbv2_client = mock.MagicMock()
    mock_boto3_session.client.return_value = elbv2_client

    # Set up default responses
    elbv2_client.describe_load_balancers.return_value = {
        "LoadBalancers": [
            {
                "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/test-alb/1234567890",
                "LoadBalancerName": "test-alb",
                "Type": "application",
            }
        ]
    }

    # Mock listeners
    elbv2_client.describe_listeners.return_value = {
        "Listeners": [
            {
                "ListenerArn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:listener/app/test-alb/1234567890/abcdef",
                "Protocol": "HTTPS",
                "Port": 443,
                "SslPolicy": "ELBSecurityPolicy-TLS-1-2-2017-01",
            }
        ]
    }

    yield elbv2_client


@pytest.fixture
def mock_ec2_client(mock_boto3_session):
    """Mock EC2 client for testing."""
    ec2_client = mock.MagicMock()
    mock_boto3_session.client.return_value = ec2_client

    # Set up default responses for VPC endpoints
    ec2_client.describe_vpc_endpoints.return_value = {
        "VpcEndpoints": [
            {
                "VpcEndpointId": "vpce-1234567890abcdef0",
                "ServiceName": "com.amazonaws.us-east-1.s3",
                "VpcEndpointType": "Interface",
                "PrivateDnsEnabled": True,
                "OwnerId": "123456789012",
                "Groups": [{"GroupId": "sg-1234567890abcdef0", "GroupName": "default"}],
            }
        ]
    }

    # Set up default responses for security groups
    ec2_client.describe_security_groups.return_value = {
        "SecurityGroups": [
            {
                "GroupId": "sg-1234567890abcdef0",
                "GroupName": "default",
                "VpcId": "vpc-1234567890abcdef0",
                "OwnerId": "123456789012",
                "IpPermissions": [
                    {
                        "FromPort": 443,
                        "ToPort": 443,
                        "IpProtocol": "tcp",
                        "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                    }
                ],
            }
        ]
    }

    yield ec2_client


@pytest.fixture
def mock_apigateway_client(mock_boto3_session):
    """Mock API Gateway client for testing."""
    apigateway_client = mock.MagicMock()
    mock_boto3_session.client.return_value = apigateway_client

    # Set up default responses
    apigateway_client.get_rest_apis.return_value = {
        "items": [{"id": "abc123", "name": "test-api"}]
    }

    # Mock API details
    apigateway_client.get_rest_api.return_value = {"id": "abc123", "name": "test-api"}

    # Mock stages
    apigateway_client.get_stages.return_value = {
        "item": [{"stageName": "prod", "methodSettings": {"*/*": {"requireHttps": True}}}]
    }

    # Mock domain names
    apigateway_client.get_domain_names.return_value = {
        "items": [{"domainName": "api.example.com", "securityPolicy": "TLS_1_2"}]
    }

    # Mock mappings
    apigateway_client.get_base_path_mappings.return_value = {
        "items": [{"restApiId": "abc123", "stage": "prod"}]
    }

    yield apigateway_client


@pytest.fixture
def mock_cloudfront_client(mock_boto3_session):
    """Mock CloudFront client for testing."""
    cloudfront_client = mock.MagicMock()
    mock_boto3_session.client.return_value = cloudfront_client

    # Set up default responses
    cloudfront_client.list_distributions.return_value = {
        "DistributionList": {
            "Items": [
                {
                    "Id": "E000000000",
                    "ARN": "arn:aws:cloudfront::123456789012:distribution/E000000000",
                }
            ]
        }
    }

    # Mock distribution details
    cloudfront_client.get_distribution.return_value = {
        "Distribution": {
            "Id": "E000000000",
            "ARN": "arn:aws:cloudfront::123456789012:distribution/E000000000",
            "DomainName": "d123456abcdef8.cloudfront.net",
            "DistributionConfig": {
                "ViewerCertificate": {"MinimumProtocolVersion": "TLSv1.2_2021"},
                "DefaultCacheBehavior": {"ViewerProtocolPolicy": "redirect-to-https"},
                "Origins": {
                    "Items": [
                        {
                            "Id": "S3-example-bucket",
                            "DomainName": "example-bucket.s3.amazonaws.com",
                            "S3OriginConfig": {
                                "OriginAccessIdentity": "origin-access-identity/cloudfront/E000000000"
                            },
                        }
                    ]
                },
            },
        }
    }

    yield cloudfront_client


@pytest.fixture
def mock_guardduty_client(mock_boto3_session):
    """Mock GuardDuty client for testing."""
    guardduty_client = mock.MagicMock()
    mock_boto3_session.client.return_value = guardduty_client

    # Set up default responses
    guardduty_client.list_detectors.return_value = {
        "DetectorIds": ["12345678901234567890123456789012"]
    }

    # Mock detector details
    guardduty_client.get_detector.return_value = {
        "Status": "ENABLED",
        "FindingPublishingFrequency": "SIX_HOURS",
        "DataSources": {
            "S3Logs": {"Status": "ENABLED"},
            "Kubernetes": {"Status": "ENABLED"},
            "Malware": {"Status": "ENABLED"},
        },
    }

    # Mock findings
    guardduty_client.list_findings.return_value = {
        "FindingIds": ["12345678901234567890123456789012"]
    }

    guardduty_client.get_findings.return_value = {
        "Findings": [
            {
                "Id": "12345678901234567890123456789012",
                "Type": "UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration",
                "Severity": 8.0,
                "CreatedAt": "2023-01-01T00:00:00Z",
                "UpdatedAt": "2023-01-01T01:00:00Z",
                "Resource": {"ResourceType": "AccessKey"},
            }
        ]
    }

    yield guardduty_client


@pytest.fixture
def mock_securityhub_client(mock_boto3_session):
    """Mock Security Hub client for testing."""
    securityhub_client = mock.MagicMock()
    mock_boto3_session.client.return_value = securityhub_client

    # Set up default responses
    securityhub_client.describe_hub.return_value = {
        "HubArn": "arn:aws:securityhub:us-east-1:123456789012:hub/default"
    }

    # Mock standards
    securityhub_client.get_enabled_standards.return_value = {
        "StandardsSubscriptions": [
            {
                "StandardsArn": "arn:aws:securityhub:::ruleset/cis-aws-foundations-benchmark/v/1.2.0",
                "StandardsSubscriptionArn": "arn:aws:securityhub:us-east-1:123456789012:subscription/cis-aws-foundations-benchmark/v/1.2.0",
                "StandardsStatus": "READY",
                "EnabledAt": "2023-01-01T00:00:00Z",
            }
        ]
    }

    # Mock findings
    securityhub_client.get_findings.return_value = {
        "Findings": [
            {
                "Id": "arn:aws:securityhub:us-east-1:123456789012:finding/12345678-1234-1234-1234-123456789012",
                "ProductArn": "arn:aws:securityhub:us-east-1::product/aws/securityhub",
                "ProductName": "Security Hub",
                "CompanyName": "AWS",
                "Region": "us-east-1",
                "GeneratorId": "arn:aws:securityhub:::ruleset/cis-aws-foundations-benchmark/v/1.2.0/rule/1.1",
                "AwsAccountId": "123456789012",
                "Types": [
                    "Software and Configuration Checks/Industry and Regulatory Standards/CIS AWS Foundations Benchmark"
                ],
                "CreatedAt": "2023-01-01T00:00:00Z",
                "UpdatedAt": "2023-01-01T01:00:00Z",
                "Severity": {"Label": "HIGH", "Normalized": 70},
                "Title": "1.1 Avoid the use of the root account",
                "Description": "The root account has unrestricted access to all resources in the AWS account.",
                "Resources": [{"Type": "AwsAccount", "Id": "AWS::::Account:123456789012"}],
                "Compliance": {"Status": "FAILED"},
                "RecordState": "ACTIVE",
                "WorkflowState": "NEW",
            }
        ]
    }

    yield securityhub_client


@pytest.fixture
def mock_inspector_client(mock_boto3_session):
    """Mock Inspector client for testing."""
    inspector_client = mock.MagicMock()
    mock_boto3_session.client.return_value = inspector_client

    # Set up default responses
    inspector_client.get_status.return_value = {
        "status": {"ec2Status": "ENABLED", "ecrStatus": "ENABLED", "lambdaStatus": "DISABLED"}
    }

    # Mock account status
    inspector_client.batch_get_account_status.return_value = {
        "accounts": [
            {
                "accountId": "123456789012",
                "resourceStatus": {
                    "ec2": {"status": "ENABLED"},
                    "ecr": {"status": "ENABLED"},
                    "lambda": {"status": "DISABLED"},
                },
            }
        ]
    }

    # Mock findings
    inspector_client.list_findings.return_value = {
        "findings": [
            {
                "findingArn": "arn:aws:inspector2:us-east-1:123456789012:finding/12345678-1234-1234-1234-123456789012",
                "awsAccountId": "123456789012",
                "severity": "HIGH",
                "type": "PACKAGE_VULNERABILITY",
                "title": "CVE-2023-12345 - openssl",
                "description": "A vulnerability in OpenSSL could allow an attacker to...",
                "status": "ACTIVE",
                "resourceType": "AWS_EC2_INSTANCE",
                "createdAt": "2023-01-01T00:00:00Z",
                "updatedAt": "2023-01-01T01:00:00Z",
            }
        ]
    }

    yield inspector_client


@pytest.fixture
def mock_accessanalyzer_client(mock_boto3_session):
    """Mock Access Analyzer client for testing."""
    analyzer_client = mock.MagicMock()
    mock_boto3_session.client.return_value = analyzer_client

    # Set up default responses
    analyzer_client.list_analyzers.return_value = {
        "analyzers": [
            {
                "arn": "arn:aws:access-analyzer:us-east-1:123456789012:analyzer/account-analyzer",
                "name": "account-analyzer",
                "type": "ACCOUNT",
                "status": "ACTIVE",
                "createdAt": "2023-01-01T00:00:00Z",
            }
        ]
    }

    # Mock findings
    analyzer_client.list_findings.return_value = {
        "findings": ["12345678-1234-1234-1234-123456789012"]
    }

    analyzer_client.get_finding.return_value = {
        "id": "12345678-1234-1234-1234-123456789012",
        "principal": {"AWS": "123456789012"},
        "action": ["s3:GetObject", "s3:ListBucket"],
        "resource": "arn:aws:s3:::example-bucket",
        "resourceType": "AWS::S3::Bucket",
        "isPublic": True,
        "status": "ACTIVE",
        "createdAt": "2023-01-01T00:00:00Z",
        "updatedAt": "2023-01-01T01:00:00Z",
    }

    yield analyzer_client


@pytest.fixture
def mock_macie_client(mock_boto3_session):
    """Mock Macie client for testing."""
    macie_client = mock.MagicMock()
    mock_boto3_session.client.return_value = macie_client

    # Set up default responses
    macie_client.get_macie_session.return_value = {
        "status": "ENABLED",
        "createdAt": "2023-01-01T00:00:00Z",
        "serviceRole": "arn:aws:iam::123456789012:role/aws-service-role/macie.amazonaws.com/AWSServiceRoleForAmazonMacie",
        "findingPublishingFrequency": "FIFTEEN_MINUTES",
    }

    # Mock findings
    macie_client.list_findings.return_value = {
        "findingIds": ["12345678-1234-1234-1234-123456789012"]
    }

    macie_client.get_findings.return_value = {
        "findings": [
            {
                "id": "12345678-1234-1234-1234-123456789012",
                "type": "SensitiveData:S3Object/Personal",
                "severity": {"score": 8},
                "createdAt": "2023-01-01T00:00:00Z",
                "updatedAt": "2023-01-01T01:00:00Z",
                "resourcesAffected": {
                    "s3Bucket": {"name": "example-bucket", "arn": "arn:aws:s3:::example-bucket"},
                    "s3Object": {
                        "key": "sensitive-data.csv",
                        "path": "example-bucket/sensitive-data.csv",
                    },
                },
            }
        ]
    }

    yield macie_client


@pytest.fixture
def mock_support_client(mock_boto3_session):
    """Mock Support client for testing."""
    support_client = mock.MagicMock()
    mock_boto3_session.client.return_value = support_client

    # Set up default responses
    support_client.describe_trusted_advisor_checks.return_value = {
        "checks": [
            {
                "id": "Pfx0RwqBli",
                "name": "Amazon S3 Bucket Permissions",
                "description": "Checks for S3 buckets that have open access permissions.",
                "category": "security",
                "metadata": ["Bucket Name", "Region", "Access Level"],
            },
            {
                "id": "7DAFEmoDos",
                "name": "IAM Use",
                "description": "Checks for your use of AWS Identity and Access Management (IAM).",
                "category": "security",
                "metadata": ["Parameter", "Value"],
            },
        ]
    }

    # Mock check results
    support_client.describe_trusted_advisor_check_result.return_value = {
        "result": {
            "checkId": "Pfx0RwqBli",
            "timestamp": "2023-01-01T00:00:00Z",
            "status": "warning",
            "resourcesSummary": {
                "resourcesProcessed": 10,
                "resourcesFlagged": 2,
                "resourcesSuppressed": 0,
            },
            "flaggedResources": [
                {
                    "status": "warning",
                    "region": "us-east-1",
                    "resourceId": "example-bucket",
                    "metadata": ["example-bucket", "us-east-1", "Public Read"],
                }
            ],
        }
    }

    yield support_client
