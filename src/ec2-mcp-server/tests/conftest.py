"""
Pytest configuration for EC2 MCP Server tests.
"""

import os
import tempfile
from datetime import datetime
from typing import Generator
from unittest.mock import MagicMock, AsyncMock

import pytest
from mcp.server.fastmcp import Context


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture
def mock_aws_credentials():
    """Mock AWS credentials for testing."""
    return {
        "aws_access_key_id": "test_access_key",
        "aws_secret_access_key": "test_secret_key",
        "region_name": "us-east-1"
    }


@pytest.fixture
def mock_instance_data():
    """Mock EC2 instance data for testing."""
    return {
        "InstanceId": "i-1234567890abcdef0",
        "InstanceType": "t2.micro",
        "State": {"Name": "running"},
        "ImageId": "ami-12345678",
        "KeyName": "my-key-pair",
        "SubnetId": "subnet-12345678",
        "VpcId": "vpc-12345678",
        "PrivateIpAddress": "10.0.1.100",
        "PublicIpAddress": "54.123.45.67",
        "LaunchTime": datetime(2023, 1, 1, 12, 0, 0),
        "Placement": {"AvailabilityZone": "us-east-1a"},
        "SecurityGroups": [
            {"GroupId": "sg-12345678", "GroupName": "default"}
        ],
        "Tags": [
            {"Key": "Name", "Value": "test-instance"},
            {"Key": "Environment", "Value": "test"}
        ],
        "Architecture": "x86_64",
        "Platform": "linux",
        "Hypervisor": "xen",
        "VirtualizationType": "hvm",
        "Monitoring": {"State": "disabled"},
        "BlockDeviceMappings": [],
        "NetworkInterfaces": []
    }


@pytest.fixture
def mock_security_group_data():
    """Mock EC2 security group data for testing."""
    return {
        "GroupId": "sg-12345678",
        "GroupName": "test-sg",
        "Description": "Test security group",
        "VpcId": "vpc-12345678",
        "OwnerId": "123456789012",
        "IpPermissions": [
            {
                "IpProtocol": "tcp",
                "FromPort": 22,
                "ToPort": 22,
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                "Ipv6Ranges": [],
                "UserIdGroupPairs": []
            }
        ],
        "IpPermissionsEgress": [
            {
                "IpProtocol": "-1",
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                "Ipv6Ranges": [],
                "UserIdGroupPairs": []
            }
        ],
        "Tags": [
            {"Key": "Name", "Value": "test-sg"}
        ]
    }


@pytest.fixture
def mock_key_pair_data():
    """Mock EC2 key pair data for testing."""
    return {
        "KeyName": "test-key-pair",
        "KeyPairId": "key-12345678",
        "KeyFingerprint": "aa:bb:cc:dd:ee:ff:00:11:22:33:44:55:66:77:88:99",
        "KeyType": "rsa",
        "KeyMaterial": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----",
        "Tags": [
            {"Key": "Name", "Value": "test-key-pair"}
        ]
    }


@pytest.fixture
def mock_volume_data():
    """Mock EBS volume data for testing."""
    return {
        "VolumeId": "vol-12345678",
        "VolumeType": "gp3",
        "Size": 20,
        "State": "available",
        "AvailabilityZone": "us-east-1a",
        "Encrypted": False,
        "Iops": 3000,
        "Throughput": 125,
        "Attachments": [],
        "CreateTime": datetime(2023, 1, 1, 12, 0, 0),
        "Tags": [
            {"Key": "Name", "Value": "test-volume"}
        ]
    }


@pytest.fixture
def mock_ami_data():
    """Mock AMI data for testing."""
    return {
        "ImageId": "ami-12345678",
        "Name": "test-ami",
        "Description": "Test AMI",
        "OwnerId": "123456789012",
        "State": "available",
        "Architecture": "x86_64",
        "Platform": "linux",
        "RootDeviceType": "ebs",
        "VirtualizationType": "hvm",
        "CreationDate": datetime(2023, 1, 1, 12, 0, 0),
        "Public": False,
        "Tags": [
            {"Key": "Name", "Value": "test-ami"}
        ]
    }


@pytest.fixture
def mock_vpc_data():
    """Mock VPC data for testing."""
    return {
        "VpcId": "vpc-12345678",
        "CidrBlock": "10.0.0.0/16",
        "State": "available",
        "IsDefault": False,
        "InstanceTenancy": "default",
        "DhcpOptionsId": "dopt-12345678",
        "Tags": [
            {"Key": "Name", "Value": "test-vpc"}
        ]
    }


@pytest.fixture
def mock_subnet_data():
    """Mock subnet data for testing."""
    return {
        "SubnetId": "subnet-12345678",
        "VpcId": "vpc-12345678",
        "CidrBlock": "10.0.1.0/24",
        "AvailabilityZone": "us-east-1a",
        "State": "available",
        "AvailableIpAddressCount": 250,
        "MapPublicIpOnLaunch": False,
        "DefaultForAz": False,
        "Tags": [
            {"Key": "Name", "Value": "test-subnet"}
        ]
    }


@pytest.fixture
def mock_snapshot_data():
    """Mock EBS snapshot data for testing."""
    return {
        "SnapshotId": "snap-12345678",
        "VolumeId": "vol-12345678",
        "State": "completed",
        "Progress": "100%",
        "StartTime": datetime(2023, 1, 1, 12, 0, 0),
        "Description": "Test snapshot",
        "OwnerId": "123456789012",
        "VolumeSize": 20,
        "Encrypted": False,
        "Tags": [
            {"Key": "Name", "Value": "test-snapshot"}
        ]
    }


@pytest.fixture
def mock_ec2_client():
    """Create a mock boto3 EC2 client."""
    mock_client = MagicMock()
    
    # Mock describe_instances
    mock_client.describe_instances.return_value = {
        "Reservations": [
            {
                "Instances": [
                    {
                        "InstanceId": "i-1234567890abcdef0",
                        "InstanceType": "t2.micro",
                        "State": {"Name": "running", "Code": 16},
                        "ImageId": "ami-12345678",
                        "KeyName": "my-key-pair",
                        "SubnetId": "subnet-12345678",
                        "VpcId": "vpc-12345678",
                        "PrivateIpAddress": "10.0.1.100",
                        "PublicIpAddress": "54.123.45.67",
                        "LaunchTime": datetime(2023, 1, 1, 12, 0, 0),
                        "Placement": {"AvailabilityZone": "us-east-1a"},
                        "SecurityGroups": [
                            {"GroupId": "sg-12345678", "GroupName": "default"}
                        ],
                        "Tags": [
                            {"Key": "Name", "Value": "test-instance"},
                            {"Key": "Environment", "Value": "test"}
                        ]
                    }
                ]
            }
        ]
    }
    
    # Mock describe_security_groups
    mock_client.describe_security_groups.return_value = {
        "SecurityGroups": [
            {
                "GroupId": "sg-12345678",
                "GroupName": "test-sg",
                "Description": "Test security group",
                "VpcId": "vpc-12345678",
                "OwnerId": "123456789012",
                "IpPermissions": [],
                "IpPermissionsEgress": [],
                "Tags": [{"Key": "Name", "Value": "test-sg"}]
            }
        ]
    }
    
    # Mock run_instances
    mock_client.run_instances.return_value = {
        "Instances": [
            {
                "InstanceId": "i-1234567890abcdef0",
                "State": {"Name": "pending", "Code": 0}
            }
        ]
    }
    
    # Mock other common operations
    mock_client.create_security_group.return_value = {"GroupId": "sg-12345678"}
    mock_client.create_key_pair.return_value = {
        "KeyName": "test-key",
        "KeyPairId": "key-12345678",
        "KeyMaterial": "-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----"
    }
    mock_client.create_volume.return_value = {"VolumeId": "vol-12345678"}
    mock_client.create_snapshot.return_value = {"SnapshotId": "snap-12345678"}
    
    return mock_client


@pytest.fixture
def mock_context():
    """Create a mock MCP context for testing."""
    context = AsyncMock(spec=Context)
    context.session = AsyncMock()
    return context


@pytest.fixture(autouse=True)
def mock_environment(monkeypatch):
    """Mock environment variables for testing."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test_access_key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret_key")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_REGION", "us-east-1")


@pytest.fixture
def mock_boto3_client(mock_ec2_client):
    """Mock boto3.client() to return the mock EC2 client."""
    with pytest.MonkeyPatch.context() as m:
        import boto3
        m.setattr(boto3, "client", lambda service, **kwargs: mock_ec2_client)
        yield mock_ec2_client