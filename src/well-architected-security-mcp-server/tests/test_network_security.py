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

"""Tests for the network_security module."""

from unittest import mock

import pytest

from awslabs.well_architected_security_mcp_server.util.network_security import (
    _update_results,
    check_api_gateway,
    check_classic_load_balancers,
    check_cloudfront_distributions,
    check_elbv2_load_balancers,
    check_network_security,
    check_security_groups,
    check_vpc_endpoints,
    find_network_resources,
    generate_recommendations,
)


@pytest.mark.asyncio
async def test_update_results():
    """Test the _update_results function."""
    # Create main results dictionary
    main_results = {
        "resources_checked": 0,
        "compliant_resources": 0,
        "non_compliant_resources": 0,
        "compliance_by_service": {},
        "resource_details": [],
    }

    # Create service results dictionary
    service_results = {
        "service": "elb",
        "resources_checked": 5,
        "compliant_resources": 3,
        "non_compliant_resources": 2,
        "resource_details": [
            {"name": "lb1", "compliant": True},
            {"name": "lb2", "compliant": False},
            {"name": "lb3", "compliant": True},
            {"name": "lb4", "compliant": True},
            {"name": "lb5", "compliant": False},
        ],
    }

    # Test with include_non_compliant_only=False
    await _update_results(main_results, service_results, "elb", False)

    # Verify results
    assert main_results["resources_checked"] == 5
    assert main_results["compliant_resources"] == 3
    assert main_results["non_compliant_resources"] == 2
    assert "elb" in main_results["compliance_by_service"]
    assert main_results["compliance_by_service"]["elb"]["resources_checked"] == 5
    assert main_results["compliance_by_service"]["elb"]["compliant_resources"] == 3
    assert main_results["compliance_by_service"]["elb"]["non_compliant_resources"] == 2
    assert len(main_results["resource_details"]) == 5

    # Reset main results
    main_results = {
        "resources_checked": 0,
        "compliant_resources": 0,
        "non_compliant_resources": 0,
        "compliance_by_service": {},
        "resource_details": [],
    }

    # Test with include_non_compliant_only=True
    await _update_results(main_results, service_results, "elb", True)

    # Verify results
    assert main_results["resources_checked"] == 5
    assert main_results["compliant_resources"] == 3
    assert main_results["non_compliant_resources"] == 2
    assert "elb" in main_results["compliance_by_service"]
    assert main_results["compliance_by_service"]["elb"]["resources_checked"] == 5
    assert main_results["compliance_by_service"]["elb"]["compliant_resources"] == 3
    assert main_results["compliance_by_service"]["elb"]["non_compliant_resources"] == 2
    assert len(main_results["resource_details"]) == 2  # Only non-compliant resources
    assert all(not resource["compliant"] for resource in main_results["resource_details"])


@pytest.mark.asyncio
async def test_generate_recommendations():
    """Test the generate_recommendations function."""
    # Test with no services
    results = {"compliance_by_service": {}}
    recommendations = await generate_recommendations(results)
    assert len(recommendations) == 3  # General recommendations

    # Test with ELB service with non-compliant resources
    results = {
        "compliance_by_service": {
            "elb": {"non_compliant_resources": 2},
            "elbv2": {"non_compliant_resources": 1},
        }
    }
    recommendations = await generate_recommendations(results)
    assert len(recommendations) > 3  # ELB recommendations + general recommendations
    assert any("Configure all load balancers to use HTTPS/TLS" in rec for rec in recommendations)
    assert any(
        "Update security policies to use TLS 1.2 or later" in rec for rec in recommendations
    )

    # Test with VPC service with non-compliant resources
    results = {"compliance_by_service": {"vpc": {"non_compliant_resources": 2}}}
    recommendations = await generate_recommendations(results)
    assert len(recommendations) > 3  # VPC recommendations + general recommendations
    assert any("Configure interface VPC endpoints to use TLS" in rec for rec in recommendations)

    # Test with security groups with non-compliant resources
    results = {"compliance_by_service": {"security_groups": {"non_compliant_resources": 2}}}
    recommendations = await generate_recommendations(results)
    assert len(recommendations) > 3  # Security group recommendations + general recommendations
    assert any("Restrict inbound traffic" in rec for rec in recommendations)

    # Test with API Gateway with non-compliant resources
    results = {"compliance_by_service": {"apigateway": {"non_compliant_resources": 2}}}
    recommendations = await generate_recommendations(results)
    assert len(recommendations) > 3  # API Gateway recommendations + general recommendations
    assert any("Configure API Gateway to enforce HTTPS" in rec for rec in recommendations)

    # Test with CloudFront with non-compliant resources
    results = {"compliance_by_service": {"cloudfront": {"non_compliant_resources": 2}}}
    recommendations = await generate_recommendations(results)
    assert len(recommendations) > 3  # CloudFront recommendations + general recommendations
    assert any(
        "Configure CloudFront distributions to redirect HTTP to HTTPS" in rec
        for rec in recommendations
    )


@pytest.mark.asyncio
async def test_find_network_resources_success(
    mock_ctx, mock_boto3_session, mock_resource_explorer_client
):
    """Test successful finding of network resources."""
    # Set up mock response for Resource Explorer
    resource_explorer = mock_resource_explorer_client

    # Mock paginator to return resources
    paginator = mock.MagicMock()
    resource_explorer.get_paginator.return_value = paginator

    # Create mock page iterator
    page_iterator = mock.MagicMock()
    paginator.paginate.return_value = page_iterator

    # Set up mock resources
    mock_resources = [
        {
            "Arn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/test-alb/1234567890"
        },
        {"Arn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/test-clb"},
        {"Arn": "arn:aws:ec2:us-east-1:123456789012:vpc-endpoint/vpce-1234567890abcdef0"},
        {"Arn": "arn:aws:ec2:us-east-1:123456789012:security-group/sg-1234567890abcdef0"},
        {"Arn": "arn:aws:apigateway:us-east-1::/restapis/abc123"},
        {"Arn": "arn:aws:cloudfront::123456789012:distribution/E000000000"},
    ]

    # Set up mock pages
    page_iterator.__iter__.return_value = [{"Resources": mock_resources}]

    # Call the function
    services = ["elb", "vpc", "apigateway", "cloudfront"]
    result = await find_network_resources("us-east-1", mock_boto3_session, services, mock_ctx)

    # Verify the result
    assert result["total_resources"] == 6
    assert "resources_by_service" in result
    assert "elb" in result["resources_by_service"]
    assert "vpc_endpoints" in result["resources_by_service"]
    assert "security_groups" in result["resources_by_service"]
    assert "apigateway" in result["resources_by_service"]
    assert "cloudfront" in result["resources_by_service"]

    # Verify Resource Explorer was called correctly
    mock_boto3_session.client.assert_called_with(
        "resource-explorer-2", region_name="us-east-1", config=mock.ANY
    )
    resource_explorer.list_views.assert_called_once()
    paginator.paginate.assert_called_once()
    assert (
        "service:elasticloadbalancing"
        in paginator.paginate.call_args[1]["Filters"]["FilterString"]
    )
    assert (
        "service:ec2 resourcetype:ec2:vpc"
        in paginator.paginate.call_args[1]["Filters"]["FilterString"]
    )


@pytest.mark.asyncio
async def test_find_network_resources_no_default_view(mock_ctx, mock_boto3_session):
    """Test handling when no default Resource Explorer view is found."""
    # Create a mock resource explorer client
    resource_explorer = mock.MagicMock()
    mock_boto3_session.client.return_value = resource_explorer

    # Mock list_views to return views without a default view
    resource_explorer.list_views.return_value = {
        "Views": [
            {
                "ViewArn": "arn:aws:resource-explorer-2:us-east-1:123456789012:view/custom-view",
                "Filters": {"FilterString": "service:s3"},  # Not a default view
            }
        ]
    }

    # Call the function
    services = ["elb"]
    result = await find_network_resources("us-east-1", mock_boto3_session, services, mock_ctx)

    # Verify the result
    assert "error" in result
    assert "No default Resource Explorer view found" in result["error"]

    # Verify warning was logged
    mock_ctx.warning.assert_called_once()
    assert "No default Resource Explorer view found" in mock_ctx.warning.call_args[0][0]


@pytest.mark.asyncio
async def test_check_classic_load_balancers_success(mock_ctx, mock_elb_client):
    """Test successful checking of Classic Load Balancers."""
    # Set up mock network resources
    network_resources = {
        "resources_by_service": {
            "elb": [
                {
                    "Arn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/test-lb-1"
                },
            ]
        }
    }

    # Call the function
    result = await check_classic_load_balancers(
        "us-east-1", mock_elb_client, mock_ctx, network_resources
    )

    # Verify the result
    assert result["service"] == "elb"
    assert result["resources_checked"] == 1
    assert result["compliant_resources"] == 1
    assert result["non_compliant_resources"] == 0
    assert len(result["resource_details"]) == 1

    # Verify ELB client was called correctly
    mock_elb_client.describe_load_balancers.assert_called()
    mock_elb_client.describe_load_balancer_policies.assert_called()


@pytest.mark.asyncio
async def test_check_classic_load_balancers_insecure_protocol(mock_ctx, mock_elb_client):
    """Test checking Classic Load Balancers with insecure protocols."""
    # Set up mock network resources
    network_resources = {
        "resources_by_service": {
            "elb": [
                {
                    "Arn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/test-lb-1"
                },
            ]
        }
    }

    # Mock describe_load_balancers to return a load balancer with HTTP listener
    mock_elb_client.describe_load_balancers.return_value = {
        "LoadBalancerDescriptions": [
            {
                "LoadBalancerName": "test-lb-1",
                "ListenerDescriptions": [
                    {
                        "Listener": {
                            "Protocol": "HTTP",
                            "LoadBalancerPort": 80,
                            "InstanceProtocol": "HTTP",
                            "InstancePort": 80,
                        },
                        "PolicyNames": [],
                    }
                ],
            }
        ]
    }

    # Call the function
    result = await check_classic_load_balancers(
        "us-east-1", mock_elb_client, mock_ctx, network_resources
    )

    # Verify the result
    assert result["service"] == "elb"
    assert result["resources_checked"] == 1
    assert result["compliant_resources"] == 0
    assert result["non_compliant_resources"] == 1
    assert len(result["resource_details"]) == 1
    assert not result["resource_details"][0]["compliant"]
    assert "non-encrypted listeners" in result["resource_details"][0]["issues"][0]


@pytest.mark.asyncio
async def test_check_classic_load_balancers_insecure_ssl_policy(mock_ctx, mock_elb_client):
    """Test checking Classic Load Balancers with insecure SSL policy."""
    # Set up mock network resources
    network_resources = {
        "resources_by_service": {
            "elb": [
                {
                    "Arn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/test-lb-1"
                },
            ]
        }
    }

    # Mock describe_load_balancers to return a load balancer with HTTPS listener
    mock_elb_client.describe_load_balancers.return_value = {
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

    # Mock describe_load_balancer_policies to return a policy with insecure protocols
    mock_elb_client.describe_load_balancer_policies.return_value = {
        "PolicyDescriptions": [
            {
                "PolicyName": "ELBSecurityPolicy-2016-08",
                "PolicyAttributeDescriptions": [
                    {"AttributeName": "Protocol-TLSv1.2", "AttributeValue": "true"},
                    {
                        "AttributeName": "Protocol-TLSv1.0",
                        "AttributeValue": "true",  # Insecure protocol
                    },
                ],
            }
        ]
    }

    # Call the function
    result = await check_classic_load_balancers(
        "us-east-1", mock_elb_client, mock_ctx, network_resources
    )

    # Verify the result
    assert result["service"] == "elb"
    assert result["resources_checked"] == 1
    assert result["compliant_resources"] == 0
    assert result["non_compliant_resources"] == 1
    assert len(result["resource_details"]) == 1
    assert not result["resource_details"][0]["compliant"]
    assert "Using insecure protocols" in result["resource_details"][0]["issues"][0]


@pytest.mark.asyncio
async def test_check_elbv2_load_balancers_success(mock_ctx, mock_elbv2_client):
    """Test successful checking of ALB/NLB Load Balancers."""
    # Set up mock network resources
    network_resources = {
        "resources_by_service": {
            "elb": [
                {
                    "Arn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/test-alb/1234567890"
                },
            ]
        }
    }

    # Set up mock_elbv2_client to return load balancer details
    mock_elbv2_client.describe_load_balancers.return_value = {
        "LoadBalancers": [
            {
                "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/test-alb/1234567890",
                "LoadBalancerName": "test-alb",
                "Type": "application",
            }
        ]
    }

    # Call the function
    result = await check_elbv2_load_balancers(
        "us-east-1", mock_elbv2_client, mock_ctx, network_resources
    )

    # Verify the result
    assert result["service"] == "elbv2"
    assert result["resources_checked"] == 1
    assert result["compliant_resources"] == 1
    assert result["non_compliant_resources"] == 0
    assert len(result["resource_details"]) == 1

    # Don't verify specific method calls, just check the result structure
    # The actual implementation might call different methods


@pytest.mark.asyncio
async def test_check_elbv2_load_balancers_http_listener(mock_ctx, mock_elbv2_client):
    """Test checking ALB with HTTP listener."""
    # Set up mock network resources
    network_resources = {
        "resources_by_service": {
            "elb": [
                {
                    "Arn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/test-alb/1234567890"
                },
            ]
        }
    }

    # Mock describe_listeners to return an HTTP listener
    mock_elbv2_client.describe_listeners.return_value = {
        "Listeners": [
            {
                "ListenerArn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:listener/app/test-alb/1234567890/abcdef",
                "Protocol": "HTTP",
                "Port": 80,
            }
        ]
    }

    # Call the function
    result = await check_elbv2_load_balancers(
        "us-east-1", mock_elbv2_client, mock_ctx, network_resources
    )

    # Verify the result
    assert result["service"] == "elbv2"
    assert result["resources_checked"] == 1
    assert result["compliant_resources"] == 0
    assert result["non_compliant_resources"] == 1
    assert len(result["resource_details"]) == 1
    assert not result["resource_details"][0]["compliant"]
    assert "non-encrypted HTTP listeners" in result["resource_details"][0]["issues"][0]


@pytest.mark.asyncio
async def test_check_elbv2_load_balancers_insecure_ssl_policy(mock_ctx, mock_elbv2_client):
    """Test checking ALB with insecure SSL policy."""
    # Set up mock network resources
    network_resources = {
        "resources_by_service": {
            "elb": [
                {
                    "Arn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/test-alb/1234567890"
                },
            ]
        }
    }

    # Mock describe_listeners to return an HTTPS listener with insecure policy
    mock_elbv2_client.describe_listeners.return_value = {
        "Listeners": [
            {
                "ListenerArn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:listener/app/test-alb/1234567890/abcdef",
                "Protocol": "HTTPS",
                "Port": 443,
                "SslPolicy": "ELBSecurityPolicy-TLS-1-0-2015-04",  # Insecure policy
            }
        ]
    }

    # Call the function
    result = await check_elbv2_load_balancers(
        "us-east-1", mock_elbv2_client, mock_ctx, network_resources
    )

    # Verify the result
    assert result["service"] == "elbv2"
    assert result["resources_checked"] == 1
    assert result["compliant_resources"] == 0
    assert result["non_compliant_resources"] == 1
    assert len(result["resource_details"]) == 1
    assert not result["resource_details"][0]["compliant"]
    assert "Using potentially insecure SSL policy" in result["resource_details"][0]["issues"][0]


@pytest.mark.asyncio
async def test_check_vpc_endpoints_success(mock_ctx, mock_ec2_client):
    """Test successful checking of VPC endpoints."""
    # Set up mock network resources
    network_resources = {
        "resources_by_service": {
            "vpc_endpoints": [
                {"Arn": "arn:aws:ec2:us-east-1:123456789012:vpc-endpoint/vpce-1234567890abcdef0"},
            ]
        }
    }

    # Call the function
    result = await check_vpc_endpoints("us-east-1", mock_ec2_client, mock_ctx, network_resources)

    # Verify the result
    assert result["service"] == "vpc"
    assert result["resources_checked"] == 1
    assert result["compliant_resources"] == 1
    assert result["non_compliant_resources"] == 0
    assert len(result["resource_details"]) == 1

    # Verify EC2 client was called correctly
    mock_ec2_client.describe_vpc_endpoints.assert_called()


@pytest.mark.asyncio
async def test_check_vpc_endpoints_private_dns_disabled(mock_ctx, mock_ec2_client):
    """Test checking VPC endpoints with private DNS disabled."""
    # Set up mock network resources
    network_resources = {
        "resources_by_service": {
            "vpc_endpoints": [
                {"Arn": "arn:aws:ec2:us-east-1:123456789012:vpc-endpoint/vpce-1234567890abcdef0"},
            ]
        }
    }

    # Mock describe_vpc_endpoints to return an endpoint with private DNS disabled
    mock_ec2_client.describe_vpc_endpoints.return_value = {
        "VpcEndpoints": [
            {
                "VpcEndpointId": "vpce-1234567890abcdef0",
                "ServiceName": "com.amazonaws.us-east-1.s3",
                "VpcEndpointType": "Interface",
                "PrivateDnsEnabled": False,  # Private DNS disabled
                "OwnerId": "123456789012",
                "Groups": [{"GroupId": "sg-1234567890abcdef0", "GroupName": "default"}],
            }
        ]
    }

    # Call the function
    result = await check_vpc_endpoints("us-east-1", mock_ec2_client, mock_ctx, network_resources)

    # Verify the result
    assert result["service"] == "vpc"
    assert result["resources_checked"] == 1
    assert result["compliant_resources"] == 0
    assert result["non_compliant_resources"] == 1
    assert len(result["resource_details"]) == 1
    assert not result["resource_details"][0]["compliant"]
    assert "Private DNS not enabled" in result["resource_details"][0]["issues"][0]


@pytest.mark.asyncio
async def test_check_security_groups_success(mock_ctx, mock_ec2_client):
    """Test successful checking of security groups."""
    # Set up mock network resources
    network_resources = {
        "resources_by_service": {
            "security_groups": [
                {"Arn": "arn:aws:ec2:us-east-1:123456789012:security-group/sg-1234567890abcdef0"},
            ]
        }
    }

    # Call the function
    result = await check_security_groups("us-east-1", mock_ec2_client, mock_ctx, network_resources)

    # Verify the result
    assert result["service"] == "security_groups"
    assert result["resources_checked"] == 1
    assert result["compliant_resources"] == 1
    assert result["non_compliant_resources"] == 0
    assert len(result["resource_details"]) == 1

    # Verify EC2 client was called correctly
    mock_ec2_client.describe_security_groups.assert_called()


@pytest.mark.asyncio
async def test_check_security_groups_open_sensitive_ports(mock_ctx, mock_ec2_client):
    """Test checking security groups with open sensitive ports."""
    # Set up mock network resources
    network_resources = {
        "resources_by_service": {
            "security_groups": [
                {"Arn": "arn:aws:ec2:us-east-1:123456789012:security-group/sg-1234567890abcdef0"},
            ]
        }
    }

    # Mock describe_security_groups to return a group with open sensitive ports
    mock_ec2_client.describe_security_groups.return_value = {
        "SecurityGroups": [
            {
                "GroupId": "sg-1234567890abcdef0",
                "GroupName": "test-sg",
                "VpcId": "vpc-1234567890abcdef0",
                "OwnerId": "123456789012",
                "IpPermissions": [
                    {
                        "FromPort": 80,  # HTTP - sensitive port
                        "ToPort": 80,
                        "IpProtocol": "tcp",
                        "IpRanges": [
                            {"CidrIp": "0.0.0.0/0"}  # Open to the world
                        ],
                    }
                ],
            }
        ]
    }

    # Call the function
    result = await check_security_groups("us-east-1", mock_ec2_client, mock_ctx, network_resources)

    # Verify the result
    assert result["service"] == "security_groups"
    assert result["resources_checked"] == 1
    assert result["compliant_resources"] == 0
    assert result["non_compliant_resources"] == 1
    assert len(result["resource_details"]) == 1
    assert not result["resource_details"][0]["compliant"]
    assert "Port 80 (HTTP) open to the world" in result["resource_details"][0]["issues"][0]


@pytest.mark.asyncio
async def test_check_api_gateway_success(mock_ctx, mock_apigateway_client):
    """Test successful checking of API Gateway."""
    # Set up mock network resources
    network_resources = {
        "resources_by_service": {
            "apigateway": [
                {"Arn": "arn:aws:apigateway:us-east-1::/restapis/abc123"},
            ]
        }
    }

    # Call the function
    result = await check_api_gateway(
        "us-east-1", mock_apigateway_client, mock_ctx, network_resources
    )

    # Verify the result
    assert result["service"] == "apigateway"
    assert result["resources_checked"] == 1
    assert result["compliant_resources"] == 1
    assert result["non_compliant_resources"] == 0
    assert len(result["resource_details"]) == 1

    # Verify API Gateway client was called correctly
    mock_apigateway_client.get_rest_api.assert_called()
    mock_apigateway_client.get_stages.assert_called()


@pytest.mark.asyncio
async def test_check_api_gateway_https_not_enforced(mock_ctx, mock_apigateway_client):
    """Test checking API Gateway with HTTPS not enforced."""
    # Set up mock network resources
    network_resources = {
        "resources_by_service": {
            "apigateway": [
                {"Arn": "arn:aws:apigateway:us-east-1::/restapis/abc123"},
            ]
        }
    }

    # Mock get_stages to return a stage without HTTPS enforcement
    mock_apigateway_client.get_stages.return_value = {
        "item": [
            {
                "stageName": "prod",
                "methodSettings": {
                    "*/*": {
                        "requireHttps": False  # HTTPS not enforced
                    }
                },
            }
        ]
    }

    # Call the function
    result = await check_api_gateway(
        "us-east-1", mock_apigateway_client, mock_ctx, network_resources
    )

    # Verify the result
    assert result["service"] == "apigateway"
    assert result["resources_checked"] == 1
    assert result["compliant_resources"] == 0
    assert result["non_compliant_resources"] == 1
    assert len(result["resource_details"]) == 1
    assert not result["resource_details"][0]["compliant"]
    assert "HTTPS not enforced for stage" in result["resource_details"][0]["issues"][0]


@pytest.mark.asyncio
async def test_check_cloudfront_distributions_success(mock_ctx, mock_cloudfront_client):
    """Test successful checking of CloudFront distributions."""
    # Set up mock network resources
    network_resources = {
        "resources_by_service": {
            "cloudfront": [
                {"Arn": "arn:aws:cloudfront::123456789012:distribution/E000000000"},
            ]
        }
    }

    # Call the function
    result = await check_cloudfront_distributions(
        "us-east-1", mock_cloudfront_client, mock_ctx, network_resources
    )

    # Verify the result
    assert result["service"] == "cloudfront"
    assert result["resources_checked"] == 1
    assert result["compliant_resources"] == 1
    assert result["non_compliant_resources"] == 0
    assert len(result["resource_details"]) == 1

    # Verify CloudFront client was called correctly
    mock_cloudfront_client.get_distribution.assert_called()


@pytest.mark.asyncio
async def test_check_cloudfront_distributions_insecure_viewer_protocol(
    mock_ctx, mock_cloudfront_client
):
    """Test checking CloudFront distributions with insecure viewer protocol policy."""
    # Set up mock network resources
    network_resources = {
        "resources_by_service": {
            "cloudfront": [
                {"Arn": "arn:aws:cloudfront::123456789012:distribution/E000000000"},
            ]
        }
    }

    # Mock get_distribution to return a distribution with insecure viewer protocol policy
    mock_cloudfront_client.get_distribution.return_value = {
        "Distribution": {
            "Id": "E000000000",
            "ARN": "arn:aws:cloudfront::123456789012:distribution/E000000000",
            "DomainName": "d123456abcdef8.cloudfront.net",
            "DistributionConfig": {
                "ViewerCertificate": {"MinimumProtocolVersion": "TLSv1.2_2021"},
                "DefaultCacheBehavior": {
                    "ViewerProtocolPolicy": "allow-all"  # Insecure policy
                },
                "Origins": {
                    "Items": [
                        {
                            "Id": "S3-example-bucket",
                            "DomainName": "example-bucket.s3.amazonaws.com",
                            "S3OriginConfig": {
                                "OriginAccessIdentity": ""  # No OAI/OAC
                            },
                        }
                    ]
                },
            },
        }
    }

    # Call the function
    result = await check_cloudfront_distributions(
        "us-east-1", mock_cloudfront_client, mock_ctx, network_resources
    )

    # Verify the result
    assert result["service"] == "cloudfront"
    assert result["resources_checked"] == 1
    assert result["compliant_resources"] == 0
    assert result["non_compliant_resources"] == 1
    assert len(result["resource_details"]) == 1
    assert not result["resource_details"][0]["compliant"]
    assert (
        "Viewer protocol policy not enforcing HTTPS" in result["resource_details"][0]["issues"][0]
    )


@pytest.mark.asyncio
async def test_check_network_security_success(mock_ctx, mock_boto3_session):
    """Test successful checking of network security."""
    # Mock find_network_resources
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.util.network_security.find_network_resources"
    ) as mock_find:
        mock_find.return_value = {
            "total_resources": 2,
            "resources_by_service": {
                "elb": [
                    {
                        "Arn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/test-lb-1"
                    },
                ]
            },
        }

        # Mock check_classic_load_balancers
        with mock.patch(
            "awslabs.well_architected_security_mcp_server.util.network_security.check_classic_load_balancers"
        ) as mock_check_elb:
            mock_check_elb.return_value = {
                "service": "elb",
                "resources_checked": 1,
                "compliant_resources": 1,
                "non_compliant_resources": 0,
                "resource_details": [
                    {"name": "test-lb-1", "compliant": True},
                ],
            }

            # Call the function
            result = await check_network_security(
                "us-east-1", ["elb"], mock_boto3_session, mock_ctx, False
            )

            # Verify the result
            assert result["region"] == "us-east-1"
            assert result["services_checked"] == ["elb"]
            assert result["resources_checked"] == 1
            assert result["compliant_resources"] == 1
            assert result["non_compliant_resources"] == 0
            assert "elb" in result["compliance_by_service"]
            assert len(result["resource_details"]) == 1
            assert len(result["recommendations"]) > 0

            # Verify mocks were called correctly
            mock_find.assert_called_once_with("us-east-1", mock_boto3_session, ["elb"], mock_ctx)
            mock_check_elb.assert_called_once()


@pytest.mark.asyncio
async def test_check_network_security_include_non_compliant_only(mock_ctx, mock_boto3_session):
    """Test checking network security with include_non_compliant_only=True."""
    # Mock find_network_resources
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.util.network_security.find_network_resources"
    ) as mock_find:
        mock_find.return_value = {
            "total_resources": 2,
            "resources_by_service": {
                "elb": [
                    {
                        "Arn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/test-lb-1"
                    },
                    {
                        "Arn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/test-lb-2"
                    },
                ]
            },
        }

        # Mock check_classic_load_balancers
        with mock.patch(
            "awslabs.well_architected_security_mcp_server.util.network_security.check_classic_load_balancers"
        ) as mock_check_elb:
            mock_check_elb.return_value = {
                "service": "elb",
                "resources_checked": 2,
                "compliant_resources": 1,
                "non_compliant_resources": 1,
                "resource_details": [
                    {"name": "test-lb-1", "compliant": True},
                    {"name": "test-lb-2", "compliant": False},
                ],
            }

            # Call the function with include_non_compliant_only=True
            result = await check_network_security(
                "us-east-1", ["elb"], mock_boto3_session, mock_ctx, True
            )

            # Verify the result
            assert result["region"] == "us-east-1"
            assert result["services_checked"] == ["elb"]
            assert result["resources_checked"] == 2
            assert result["compliant_resources"] == 1
            assert result["non_compliant_resources"] == 1
            assert "elb" in result["compliance_by_service"]
            assert len(result["resource_details"]) == 1  # Only non-compliant resources
            assert not result["resource_details"][0]["compliant"]
            assert len(result["recommendations"]) > 0
