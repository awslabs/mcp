#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Pytest configuration and fixtures for AWS Network MCP Server tests."""

import pytest
from unittest.mock import MagicMock, patch
from moto import mock_aws
import boto3
from typing import Any, Dict

from awslabs.aws_network_mcp_server.core.tool_registry import ToolRegistry, FastMCPAdapter
from awslabs.aws_network_mcp_server.core.aws_service_factory import AWSServiceFactory, AWSConfig
from awslabs.aws_network_mcp_server.core.error_handler import ErrorHandler, ErrorContext


@pytest.fixture
def mock_mcp():
    """Create a mock MCP instance for testing."""
    mock = MagicMock()
    mock.name = 'test-mcp-server'
    mock.version = '1.0.0'
    mock.instructions = 'Test instructions'
    mock.tool = MagicMock()
    return mock


@pytest.fixture
def tool_registry(mock_mcp):
    """Create a tool registry for testing."""
    adapter = FastMCPAdapter(mock_mcp)
    return ToolRegistry(adapter=adapter)


@pytest.fixture
def aws_factory():
    """Create an AWS service factory in mock mode."""
    factory = AWSServiceFactory(AWSConfig(region='us-east-1'))
    factory.enable_mock_mode()
    return factory


@pytest.fixture
def error_handler():
    """Create an error handler for testing."""
    return ErrorHandler()


@pytest.fixture
def error_context():
    """Create a sample error context."""
    return ErrorContext(
        tool_name='test_tool',
        service='test_service',
        resource_type='VPC',
        resource_id='vpc-12345678',
        region='us-east-1'
    )


@pytest.fixture
@mock_aws
def aws_resources():
    """Create mock AWS resources for testing."""
    ec2 = boto3.client('ec2', region_name='us-east-1')
    
    # Create VPC
    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc['Vpc']['VpcId']
    
    # Create subnets
    subnet1 = ec2.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24')
    subnet2 = ec2.create_subnet(VpcId=vpc_id, Cidr

