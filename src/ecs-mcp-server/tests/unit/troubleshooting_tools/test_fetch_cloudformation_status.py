"""
Unit tests for the fetch_cloudformation_status function using pytest's native async test support.
"""

import datetime
from unittest import mock

import pytest
from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.api.troubleshooting_tools import fetch_cloudformation_status


@pytest.mark.anyio
@mock.patch("boto3.client")
async def test_stack_exists(mock_boto_client):
    """Test when CloudFormation stack exists."""
    # Mock CloudFormation client
    mock_cf_client = mock.Mock()

    # Mock describe_stacks response
    mock_cf_client.describe_stacks.return_value = {
        "Stacks": [{"StackName": "test-app", "StackStatus": "CREATE_COMPLETE"}]
    }

    # Mock list_stack_resources response
    mock_cf_client.list_stack_resources.return_value = {
        "StackResourceSummaries": [
            {
                "LogicalResourceId": "ECSCluster",
                "PhysicalResourceId": "test-app-cluster",
                "ResourceType": "AWS::ECS::Cluster",
                "ResourceStatus": "CREATE_COMPLETE",
            },
            {
                "LogicalResourceId": "LoadBalancer",
                "PhysicalResourceId": (
                    "arn:aws:elasticloadbalancing:us-west-2:123456789012:"
                    "loadbalancer/app/test-app/1234567890123456"
                ),
                "ResourceType": "AWS::ElasticLoadBalancingV2::LoadBalancer",
                "ResourceStatus": "CREATE_COMPLETE",
            },
        ]
    }

    # Mock describe_stack_events response
    mock_cf_client.describe_stack_events.return_value = {
        "StackEvents": [
            {
                "StackId": (
                    "arn:aws:cloudformation:us-west-2:123456789012:stack/test-app/1234567890123456"
                ),
                "EventId": "1234567890123456",
                "StackName": "test-app",
                "LogicalResourceId": "ECSCluster",
                "PhysicalResourceId": "test-app-cluster",
                "ResourceType": "AWS::ECS::Cluster",
                "Timestamp": datetime.datetime(2025, 5, 13, 12, 0, 0),
                "ResourceStatus": "CREATE_COMPLETE",
            }
        ]
    }

    # Configure boto3.client mock to return our mock client
    mock_boto_client.return_value = mock_cf_client

    # Call the function
    result = await fetch_cloudformation_status("test-app")

    # Verify the result
    assert result["status"] == "success"
    assert result["stack_exists"]
    assert result["stack_status"] == "CREATE_COMPLETE"
    assert len(result["resources"]) == 2
    assert len(result["raw_events"]) == 1


@pytest.mark.anyio
@mock.patch("boto3.client")
async def test_stack_failure(mock_boto_client):
    """Test when CloudFormation stack exists but has failed resources."""
    # Mock CloudFormation client
    mock_cf_client = mock.Mock()

    # Mock describe_stacks response
    mock_cf_client.describe_stacks.return_value = {
        "Stacks": [{"StackName": "test-app", "StackStatus": "CREATE_FAILED"}]
    }

    # Mock list_stack_resources response
    mock_cf_client.list_stack_resources.return_value = {
        "StackResourceSummaries": [
            {
                "LogicalResourceId": "ECSCluster",
                "PhysicalResourceId": "test-app-cluster",
                "ResourceType": "AWS::ECS::Cluster",
                "ResourceStatus": "CREATE_COMPLETE",
            },
            {
                "LogicalResourceId": "ECSService",
                "PhysicalResourceId": "",
                "ResourceType": "AWS::ECS::Service",
                "ResourceStatus": "CREATE_FAILED",
                "ResourceStatusReason": "Resource creation cancelled",
            },
        ]
    }

    # Mock describe_stack_events response
    timestamp = datetime.datetime(2025, 5, 13, 12, 0, 0)
    mock_cf_client.describe_stack_events.return_value = {
        "StackEvents": [
            {
                "StackId": (
                    "arn:aws:cloudformation:us-west-2:123456789012:stack/test-app/1234567890123456"
                ),
                "EventId": "1234567890123456",
                "StackName": "test-app",
                "LogicalResourceId": "ECSService",
                "PhysicalResourceId": "",
                "ResourceType": "AWS::ECS::Service",
                "Timestamp": timestamp,
                "ResourceStatus": "CREATE_FAILED",
                "ResourceStatusReason": "Resource creation cancelled",
            }
        ]
    }

    # Configure boto3.client mock to return our mock client
    mock_boto_client.return_value = mock_cf_client

    # Call the function
    result = await fetch_cloudformation_status("test-app")

    # Verify the result
    assert result["status"] == "success"
    assert result["stack_exists"]
    assert result["stack_status"] == "CREATE_FAILED"
    assert len(result["failure_reasons"]) == 1
    assert result["failure_reasons"][0]["logical_id"] == "ECSService"
    assert "cancelled" in result["failure_reasons"][0]["reason"]


@pytest.mark.anyio
@mock.patch("boto3.client")
async def test_stack_not_found(mock_boto_client):
    """Test when CloudFormation stack does not exist."""
    # Mock CloudFormation client
    mock_cf_client = mock.Mock()

    # Mock describe_stacks with ClientError
    mock_cf_client.describe_stacks.side_effect = ClientError(
        {"Error": {"Code": "ValidationError", "Message": "Stack with id test-app does not exist"}},
        "DescribeStacks",
    )

    # Mock list_stacks for deleted stacks
    mock_cf_client.get_paginator.return_value.paginate.return_value = [
        {
            "StackSummaries": [
                {
                    "StackName": "test-app",
                    "StackStatus": "DELETE_COMPLETE",
                    "DeletionTime": datetime.datetime(2025, 5, 10, 12, 0, 0),
                }
            ]
        }
    ]

    # Configure boto3.client mock to return our mock client
    mock_boto_client.return_value = mock_cf_client

    # Call the function
    result = await fetch_cloudformation_status("test-app")

    # Verify the result
    assert result["status"] == "success"
    assert not result["stack_exists"]
    assert "deleted_stacks" in result
    assert len(result["deleted_stacks"]) == 1
    assert "Found 1 deleted" in result["message"]
