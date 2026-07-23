#!/usr/bin/env python3
"""
Unit tests for Pydantic models.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from awslabs.ec2_mcp_server.models import (
    Tag,
    InstanceState,
    InstanceStateModel,
    SecurityGroup,
    Placement,
    Instance,
    IpPermission,
    SecurityGroupDetail,
    KeyPair,
    Volume,
    Snapshot,
    Image,
    Vpc,
    Subnet
)


class TestBasicModels:
    """Test basic model functionality."""
    
    def test_tag_model(self):
        """Test Tag model creation and validation."""
        tag_data = {"key": "Environment", "value": "test"}
        tag = Tag(**tag_data)
        
        assert tag.key == "Environment"
        assert tag.value == "test"
        
        # Test serialization
        assert tag.model_dump() == tag_data
    
    def test_instance_state_model(self):
        """Test InstanceState model."""
        state_data = {"name": "running", "code": 16}
        state = InstanceStateModel(**state_data)
        
        assert state.name == "running"
        assert state.code == 16
    
    def test_security_group_model(self):
        """Test SecurityGroup model."""
        sg_data = {"group_id": "sg-12345678", "group_name": "default"}
        sg = SecurityGroup(**sg_data)
        
        assert sg.group_id == "sg-12345678"
        assert sg.group_name == "default"
    
    def test_placement_model(self):
        """Test Placement model."""
        placement_data = {
            "availability_zone": "us-east-1a",
            "tenancy": "default"
        }
        placement = Placement(**placement_data)
        
        assert placement.availability_zone == "us-east-1a"
        assert placement.tenancy == "default"
        assert placement.affinity is None  # Optional field


class TestInstanceModel:
    """Test Instance model functionality."""
    
    def test_minimal_instance(self):
        """Test Instance creation with minimal required fields."""
        instance_data = {
            "instance_id": "i-1234567890abcdef0",
            "instance_type": "t2.micro",
            "state": {"name": "running", "code": 16},
            "image_id": "ami-123456780abcdef0"
        }
        
        instance = Instance(**instance_data)
        
        assert instance.instance_id == "i-1234567890abcdef0"
        assert instance.instance_type == "t2.micro"
        assert instance.state.name == "running"
        assert instance.image_id == "ami-123456780abcdef0"
        
        # Test that optional fields are None or empty lists
        assert instance.key_name is None
        assert instance.security_groups == []
        assert instance.tags == []
    
    def test_complete_instance(self):
        """Test Instance creation with all fields."""
        instance_data = {
            "instance_id": "i-1234567890abcdef0",
            "instance_type": "t2.micro",
            "state": {"name": "running", "code": 16},
            "image_id": "ami-123456780abcdef0",
            "key_name": "my-key",
            "subnet_id": "subnet-12345678",
            "vpc_id": "vpc-12345678",
            "private_ip_address": "10.0.1.100",
            "public_ip_address": "54.123.45.67",
            "launch_time": datetime(2023, 1, 1, 12, 0, 0),
            "placement": {"availability_zone": "us-east-1a"},
            "security_groups": [
                {"group_id": "sg-12345678", "group_name": "default"}
            ],
            "tags": [
                {"key": "Name", "value": "test-instance"}
            ],
            "architecture": "x86_64",
            "platform": "linux"
        }
        
        instance = Instance(**instance_data)
        
        assert instance.key_name == "my-key"
        assert instance.private_ip_address == "10.0.1.100"
        assert instance.public_ip_address == "54.123.45.67"
        assert instance.placement.availability_zone == "us-east-1a"
        assert len(instance.security_groups) == 1
        assert instance.security_groups[0].group_id == "sg-12345678"
        assert len(instance.tags) == 1
        assert instance.tags[0].key == "Name"
    
    def test_instance_validation_error(self):
        """Test Instance validation with missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            Instance(instance_id="i-123")  # Missing required fields
        
        errors = exc_info.value.errors()
        required_fields = {error['loc'][0] for error in errors}
        assert 'instance_type' in required_fields
        assert 'state' in required_fields
        assert 'image_id' in required_fields


class TestSecurityGroupDetailModel:
    """Test SecurityGroupDetail model functionality."""
    
    def test_security_group_detail(self):
        """Test SecurityGroupDetail creation."""
        sg_data = {
            "group_id": "sg-12345678456789",
            "group_name": "test-sg",
            "description": "Test security group",
            "owner_id": "123456789012",
            "ip_permissions": [
                {
                    "ip_protocol": "tcp",
                    "from_port": 22,
                    "to_port": 22,
                    "ip_ranges": [{"CidrIp": "0.0.0.0/0"}],
                    "ipv6_ranges": [],
                    "user_id_group_pairs": []
                }
            ],
            "ip_permissions_egress": [],
            "tags": []
        }
        
        sg = SecurityGroupDetail(**sg_data)
        
        assert sg.group_id == "sg-12345678456789"
        assert sg.group_name == "test-sg"
        assert sg.description == "Test security group"
        assert len(sg.ip_permissions) == 1
        assert sg.ip_permissions[0].ip_protocol == "tcp"
        assert sg.ip_permissions[0].from_port == 22
    
    def test_ip_permission_model(self):
        """Test IpPermission model."""
        ip_perm_data = {
            "ip_protocol": "tcp",
            "from_port": 80,
            "to_port": 80,
            "ip_ranges": [{"CidrIp": "10.0.0.0/8"}],
            "ipv6_ranges": [],
            "user_id_group_pairs": []
        }
        
        ip_perm = IpPermission(**ip_perm_data)
        
        assert ip_perm.ip_protocol == "tcp"
        assert ip_perm.from_port == 80
        assert ip_perm.to_port == 80
        assert len(ip_perm.ip_ranges) == 1
        assert ip_perm.ip_ranges[0]["CidrIp"] == "10.0.0.0/8"


class TestVolumeAndSnapshotModels:
    """Test Volume and Snapshot models."""
    
    def test_volume_model(self):
        """Test Volume model creation."""
        volume_data = {
            "volume_id": "vol-1234567890abcdef0",
            "volume_type": "gp3",
            "size": 20,
            "state": "available",
            "availability_zone": "us-east-1a",
            "encrypted": False,
            "iops": 3000,
            "throughput": 125,
            "attachments": [],
            "create_time": datetime(2023, 1, 1, 12, 0, 0),
            "tags": []
        }
        
        volume = Volume(**volume_data)
        
        assert volume.volume_id == "vol-1234567890abcdef0"
        assert volume.volume_type == "gp3"
        assert volume.size == 20
        assert volume.iops == 3000
        assert volume.throughput == 125
    
    def test_snapshot_model(self):
        """Test Snapshot model creation."""
        snapshot_data = {
            "snapshot_id": "snap-1234567890abcdef0",
            "volume_id": "vol-1234567890abcdef0",
            "state": "completed",
            "progress": "100%",
            "start_time": datetime(2023, 1, 1, 12, 0, 0),
            "description": "Test snapshot",
            "owner_id": "123456789012",
            "volume_size": 20,
            "encrypted": False,
            "tags": []
        }
        
        snapshot = Snapshot(**snapshot_data)
        
        assert snapshot.snapshot_id == "snap-1234567890abcdef0"
        assert snapshot.volume_id == "vol-1234567890abcdef0"
        assert snapshot.state == "completed"
        assert snapshot.progress == "100%"
        assert snapshot.volume_size == 20


class TestKeyPairModel:
    """Test KeyPair model functionality."""
    
    def test_key_pair_minimal(self):
        """Test KeyPair with minimal data."""
        key_data = {"key_name": "test-key"}
        key_pair = KeyPair(**key_data)
        
        assert key_pair.key_name == "test-key"
        assert key_pair.key_pair_id is None
        assert key_pair.key_material is None
    
    def test_key_pair_complete(self):
        """Test KeyPair with complete data."""
        key_data = {
            "key_name": "test-key",
            "key_pair_id": "key-1234567890abcdef0",
            "key_fingerprint": "aa:bb:cc:dd:ee:ff",
            "key_type": "rsa",
            "key_material": "-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----",
            "tags": [{"key": "Environment", "value": "test"}]
        }
        
        key_pair = KeyPair(**key_data)
        
        assert key_pair.key_name == "test-key"
        assert key_pair.key_pair_id == "key-1234567890abcdef0"
        assert key_pair.key_fingerprint == "aa:bb:cc:dd:ee:ff"
        assert key_pair.key_type == "rsa"
        assert "BEGIN RSA PRIVATE KEY" in key_pair.key_material
        assert len(key_pair.tags) == 1


class TestNetworkingModels:
    """Test VPC and Subnet models."""
    
    def test_vpc_model(self):
        """Test VPC model creation."""
        vpc_data = {
            "vpc_id": "vpc-12345678456789",
            "cidr_block": "10.0.0.0/16",
            "state": "available",
            "is_default": False,
            "instance_tenancy": "default",
            "dhcp_options_id": "dopt-12345678",
            "tags": []
        }
        
        vpc = Vpc(**vpc_data)
        
        assert vpc.vpc_id == "vpc-12345678456789"
        assert vpc.cidr_block == "10.0.0.0/16"
        assert vpc.state == "available"
        assert vpc.is_default is False
        assert vpc.instance_tenancy == "default"
    
    def test_subnet_model(self):
        """Test Subnet model creation."""
        subnet_data = {
            "subnet_id": "subnet-12345678456789",
            "vpc_id": "vpc-12345678456789",
            "cidr_block": "10.0.1.0/24",
            "availability_zone": "us-east-1a",
            "state": "available",
            "available_ip_address_count": 250,
            "map_public_ip_on_launch": False,
            "default_for_az": False,
            "tags": []
        }
        
        subnet = Subnet(**subnet_data)
        
        assert subnet.subnet_id == "subnet-12345678456789"
        assert subnet.vpc_id == "vpc-12345678456789"
        assert subnet.cidr_block == "10.0.1.0/24"
        assert subnet.availability_zone == "us-east-1a"
        assert subnet.available_ip_address_count == 250


class TestImageModel:
    """Test Image (AMI) model functionality."""
    
    def test_image_model(self):
        """Test Image model creation."""
        image_data = {
            "image_id": "ami-123456780abcdef0",
            "name": "test-ami",
            "description": "Test AMI description",
            "owner_id": "123456789012",
            "state": "available",
            "architecture": "x86_64",
            "platform": "linux",
            "root_device_type": "ebs",
            "virtualization_type": "hvm",
            "creation_date": datetime(2023, 1, 1, 12, 0, 0),
            "public": False,
            "tags": []
        }
        
        image = Image(**image_data)
        
        assert image.image_id == "ami-123456780abcdef0"
        assert image.name == "test-ami"
        assert image.owner_id == "123456789012"
        assert image.state == "available"
        assert image.architecture == "x86_64"
        assert image.public is False


class TestModelSerialization:
    """Test model serialization with aliases."""
    
    def test_instance_serialization_with_aliases(self):
        """Test that models serialize correctly with AWS field names."""
        instance_data = {
            "instance_id": "i-1234567890abcdef0",
            "instance_type": "t2.micro",
            "state": {"name": "running", "code": 16},
            "image_id": "ami-123456780abcdef0"
        }
        
        instance = Instance(**instance_data)
        serialized = instance.model_dump()
        
        # Should use Python field names
        assert "instance_id" in serialized
        assert "instance_type" in serialized
        assert "state" in serialized
        assert "image_id" in serialized
    
    def test_model_round_trip(self):
        """Test that models can be serialized and deserialized."""
        original_data = {
            "group_id": "sg-12345678456789",
            "group_name": "test-sg",
            "description": "Test security group",
            "owner_id": "123456789012",
            "ip_permissions": [],
            "ip_permissions_egress": [],
            "tags": [{"key": "Name", "value": "test"}]
        }
        
        # Create model from data
        sg = SecurityGroupDetail(**original_data)
        
        # Serialize back to dict
        serialized = sg.model_dump()
        
        # Create new model from serialized data
        sg2 = SecurityGroupDetail(**serialized)
        
        # Should be equivalent
        assert sg.group_id == sg2.group_id
        assert sg.group_name == sg2.group_name
        assert sg.description == sg2.description
        assert len(sg.tags) == len(sg2.tags)