#!/usr/bin/env python3
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
"""Pydantic models for EC2 MCP Server.

This module defines all data models used for EC2 resource representation
and validation with comprehensive type hints and field validation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class InstanceState(str, Enum):
    """EC2 instance state enumeration.
    
    Attributes:
        PENDING: Instance is being launched.
        RUNNING: Instance is running and available.
        SHUTTING_DOWN: Instance is being shut down.
        TERMINATED: Instance has been terminated.
        STOPPING: Instance is being stopped.
        STOPPED: Instance is stopped.
        REBOOTING: Instance is being rebooted.
    """
    
    PENDING = 'pending'
    RUNNING = 'running'
    SHUTTING_DOWN = 'shutting-down'
    TERMINATED = 'terminated'
    STOPPING = 'stopping'
    STOPPED = 'stopped'
    REBOOTING = 'rebooting'


class VolumeState(str, Enum):
    """EBS volume state enumeration.
    
    Attributes:
        CREATING: Volume is being created.
        AVAILABLE: Volume is available for attachment.
        IN_USE: Volume is attached to an instance.
        DELETING: Volume is being deleted.
        DELETED: Volume has been deleted.
        ERROR: Volume is in error state.
    """
    
    CREATING = 'creating'
    AVAILABLE = 'available'
    IN_USE = 'in-use'
    DELETING = 'deleting'
    DELETED = 'deleted'
    ERROR = 'error'


class Tag(BaseModel):
    """AWS resource tag.
    
    Attributes:
        key: The tag key (1-128 characters).
        value: The tag value (0-255 characters).
    """
    
    key: str = Field(..., description='Tag key', min_length=1, max_length=128)
    value: str = Field(..., description='Tag value', max_length=255)

    @field_validator('key')
    @classmethod
    def validate_key(cls, v: str) -> str:
        """Validate tag key format."""
        if not v.strip():
            raise ValueError('Tag key cannot be empty or whitespace only')
        return v.strip()


class InstanceStateModel(BaseModel):
    """EC2 instance state model.
    
    Attributes:
        name: State name as enumerated value.
        code: Numeric state code.
    """
    
    name: InstanceState = Field(..., description='Instance state name')
    code: int = Field(..., description='Instance state code', ge=0, le=255)


class SecurityGroup(BaseModel):
    """Security group reference.
    
    Attributes:
        group_id: Security group ID (sg-xxxxxxxx format).
        group_name: Security group name.
    """
    
    group_id: str = Field(..., description='Security group ID', pattern=r'^sg-[a-f0-9]{8,17}$')
    group_name: str = Field(..., description='Security group name', min_length=1, max_length=255)


class Placement(BaseModel):
    """Instance placement information.
    
    Attributes:
        availability_zone: Availability zone name.
        affinity: Affinity setting for Dedicated Hosts.
        group_name: Name of the placement group.
        host_id: ID of the Dedicated Host.
        tenancy: Tenancy of the instance.
    """
    
    availability_zone: str = Field(..., description='Availability zone')
    affinity: Optional[str] = Field(None, description='Affinity setting')
    group_name: Optional[str] = Field(None, description='Placement group name')
    host_id: Optional[str] = Field(None, description='Dedicated Host ID')
    tenancy: Optional[str] = Field(None, description='Instance tenancy')


class Instance(BaseModel):
    """EC2 instance model.
    
    Represents an Amazon EC2 instance with comprehensive metadata.
    
    Attributes:
        instance_id: Unique instance identifier (i-xxxxxxxx format).
        instance_type: Instance type (e.g., t3.micro, m5.large).
        state: Current instance state.
        image_id: AMI ID used to launch the instance.
        key_name: Name of the key pair for SSH access.
        subnet_id: Subnet ID where instance is launched.
        vpc_id: VPC ID containing the instance.
        private_ip_address: Private IP address within VPC.
        public_ip_address: Public IP address if assigned.
        launch_time: Instance launch timestamp.
        placement: Instance placement information.
        security_groups: List of attached security groups.
        tags: Resource tags.
        architecture: Instance architecture (x86_64, arm64).
        platform: Operating system platform.
    """
    
    instance_id: str = Field(
        ..., 
        description='Instance ID',
        pattern=r'^i-[a-f0-9]{8,17}$'
    )
    instance_type: str = Field(
        ..., 
        description='Instance type',
        min_length=1,
        max_length=20
    )
    state: InstanceStateModel = Field(..., description='Instance state')
    image_id: str = Field(
        ..., 
        description='AMI ID',
        pattern=r'^ami-[a-f0-9]{8,17}$'
    )
    key_name: Optional[str] = Field(None, description='Key pair name')
    subnet_id: Optional[str] = Field(
        None, 
        description='Subnet ID',
        pattern=r'^subnet-[a-f0-9]{8,17}$'
    )
    vpc_id: Optional[str] = Field(
        None, 
        description='VPC ID',
        pattern=r'^vpc-[a-f0-9]{8,17}$'
    )
    private_ip_address: Optional[str] = Field(None, description='Private IP address')
    public_ip_address: Optional[str] = Field(None, description='Public IP address')
    launch_time: Optional[datetime] = Field(None, description='Launch timestamp')
    placement: Optional[Placement] = Field(None, description='Placement information')
    security_groups: List[SecurityGroup] = Field(
        default_factory=list, 
        description='Attached security groups'
    )
    tags: List[Tag] = Field(default_factory=list, description='Resource tags')
    architecture: Optional[str] = Field(None, description='Instance architecture')
    platform: Optional[str] = Field(None, description='OS platform')

    model_config = {'populate_by_name': True}


class IpPermission(BaseModel):
    """Security group IP permission.
    
    Attributes:
        ip_protocol: IP protocol (tcp, udp, icmp, or -1 for all).
        from_port: Start of port range (1-65535).
        to_port: End of port range (1-65535).
        ip_ranges: List of IPv4 CIDR blocks.
        ipv6_ranges: List of IPv6 CIDR blocks.
        user_id_group_pairs: Referenced security groups.
    """
    
    ip_protocol: str = Field(..., description='IP protocol')
    from_port: Optional[int] = Field(None, description='Start port', ge=1, le=65535)
    to_port: Optional[int] = Field(None, description='End port', ge=1, le=65535)
    ip_ranges: List[Dict[str, str]] = Field(
        default_factory=list, 
        description='IPv4 CIDR blocks'
    )
    ipv6_ranges: List[Dict[str, str]] = Field(
        default_factory=list, 
        description='IPv6 CIDR blocks'
    )
    user_id_group_pairs: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description='Referenced security groups'
    )


class SecurityGroupDetail(BaseModel):
    """Detailed security group model.
    
    Represents a VPC security group with all rules and metadata.
    
    Attributes:
        group_id: Security group ID (sg-xxxxxxxx format).
        group_name: Security group name.
        description: Security group description.
        vpc_id: VPC ID containing this security group.
        owner_id: AWS account ID of the owner.
        ip_permissions: Inbound rules.
        ip_permissions_egress: Outbound rules.
        tags: Resource tags.
    """
    
    group_id: str = Field(
        ..., 
        description='Security group ID',
        pattern=r'^sg-[a-f0-9]{8,17}$'
    )
    group_name: str = Field(
        ..., 
        description='Security group name',
        min_length=1,
        max_length=255
    )
    description: str = Field(..., description='Security group description')
    vpc_id: Optional[str] = Field(
        None, 
        description='VPC ID',
        pattern=r'^vpc-[a-f0-9]{8,17}$'
    )
    owner_id: str = Field(..., description='AWS account ID', pattern=r'^\d{12}$')
    ip_permissions: List[IpPermission] = Field(
        default_factory=list, 
        description='Inbound rules'
    )
    ip_permissions_egress: List[IpPermission] = Field(
        default_factory=list, 
        description='Outbound rules'
    )
    tags: List[Tag] = Field(default_factory=list, description='Resource tags')

    model_config = {'populate_by_name': True}


class KeyPair(BaseModel):
    """EC2 key pair model.
    
    Represents an SSH key pair for EC2 instance access.
    
    Attributes:
        key_name: Key pair name.
        key_pair_id: Unique key pair identifier.
        key_fingerprint: Public key fingerprint.
        key_type: Key type (rsa, ed25519).
        key_material: Private key material (only for newly created keys).
        tags: Resource tags.
    """
    
    key_name: str = Field(
        ..., 
        description='Key pair name',
        min_length=1,
        max_length=255
    )
    key_pair_id: Optional[str] = Field(None, description='Key pair ID')
    key_fingerprint: Optional[str] = Field(None, description='Public key fingerprint')
    key_type: Optional[str] = Field(None, description='Key type')
    key_material: Optional[str] = Field(None, description='Private key material')
    tags: List[Tag] = Field(default_factory=list, description='Resource tags')

    model_config = {'populate_by_name': True}


class VolumeAttachment(BaseModel):
    """EBS volume attachment.
    
    Attributes:
        device: Device name (e.g., /dev/sdf, /dev/xvdf).
        instance_id: Instance ID the volume is attached to.
        state: Attachment state (attaching, attached, detaching, detached).
        attach_time: Attachment timestamp.
        delete_on_termination: Whether to delete volume on instance termination.
    """
    
    device: str = Field(..., description='Device name')
    instance_id: str = Field(
        ..., 
        description='Instance ID',
        pattern=r'^i-[a-f0-9]{8,17}$'
    )
    state: str = Field(..., description='Attachment state')
    attach_time: Optional[datetime] = Field(None, description='Attachment time')
    delete_on_termination: bool = Field(False, description='Delete on termination')


class Volume(BaseModel):
    """EBS volume model.
    
    Represents an Amazon EBS volume with all metadata.
    
    Attributes:
        volume_id: Volume ID (vol-xxxxxxxx format).
        volume_type: Volume type (gp2, gp3, io1, io2, sc1, st1).
        size: Volume size in GiB.
        state: Volume state.
        availability_zone: Availability zone.
        encrypted: Whether volume is encrypted.
        iops: Provisioned IOPS (for io1/io2 volumes).
        throughput: Provisioned throughput (for gp3 volumes).
        attachments: List of volume attachments.
        create_time: Volume creation timestamp.
        tags: Resource tags.
    """
    
    volume_id: str = Field(
        ..., 
        description='Volume ID',
        pattern=r'^vol-[a-f0-9]{8,17}$'
    )
    volume_type: str = Field(..., description='Volume type')
    size: int = Field(..., description='Size in GiB', ge=1, le=65536)
    state: VolumeState = Field(..., description='Volume state')
    availability_zone: str = Field(..., description='Availability zone')
    encrypted: bool = Field(False, description='Encryption status')
    iops: Optional[int] = Field(None, description='Provisioned IOPS', ge=100, le=64000)
    throughput: Optional[int] = Field(None, description='Throughput MiB/s', ge=125, le=1000)
    attachments: List[VolumeAttachment] = Field(
        default_factory=list, 
        description='Volume attachments'
    )
    create_time: Optional[datetime] = Field(None, description='Creation time')
    tags: List[Tag] = Field(default_factory=list, description='Resource tags')

    model_config = {'populate_by_name': True}


class Snapshot(BaseModel):
    """EBS snapshot model.
    
    Represents an Amazon EBS snapshot with metadata.
    
    Attributes:
        snapshot_id: Snapshot ID (snap-xxxxxxxx format).
        volume_id: Source volume ID.
        state: Snapshot state (pending, completed, error).
        progress: Completion progress percentage.
        start_time: Snapshot start timestamp.
        description: Snapshot description.
        owner_id: AWS account ID of snapshot owner.
        volume_size: Size of source volume in GiB.
        encrypted: Whether snapshot is encrypted.
        tags: Resource tags.
    """
    
    snapshot_id: str = Field(
        ..., 
        description='Snapshot ID',
        pattern=r'^snap-[a-f0-9]{8,17}$'
    )
    volume_id: Optional[str] = Field(
        None, 
        description='Source volume ID',
        pattern=r'^vol-[a-f0-9]{8,17}$'
    )
    state: str = Field(..., description='Snapshot state')
    progress: Optional[str] = Field(None, description='Progress percentage')
    start_time: Optional[datetime] = Field(None, description='Start time')
    description: Optional[str] = Field(None, description='Description')
    owner_id: str = Field(..., description='Owner account ID', pattern=r'^\d{12}$')
    volume_size: int = Field(..., description='Volume size GiB', ge=1)
    encrypted: bool = Field(False, description='Encryption status')
    tags: List[Tag] = Field(default_factory=list, description='Resource tags')

    model_config = {'populate_by_name': True}


class Image(BaseModel):
    """Amazon Machine Image (AMI) model.
    
    Represents an AMI with comprehensive metadata.
    
    Attributes:
        image_id: AMI ID (ami-xxxxxxxx format).
        name: AMI name.
        description: AMI description.
        owner_id: AWS account ID of AMI owner.
        state: AMI state (pending, available, invalid, deregistered).
        architecture: Architecture (x86_64, arm64).
        platform: Platform (windows or empty for Linux).
        root_device_type: Root device type (ebs, instance-store).
        virtualization_type: Virtualization type (hvm, paravirtual).
        creation_date: AMI creation timestamp.
        public: Whether AMI is public.
        tags: Resource tags.
    """
    
    image_id: str = Field(
        ..., 
        description='AMI ID',
        pattern=r'^ami-[a-f0-9]{8,17}$'
    )
    name: Optional[str] = Field(None, description='AMI name')
    description: Optional[str] = Field(None, description='AMI description')
    owner_id: str = Field(..., description='Owner account ID', pattern=r'^\d{12}$')
    state: str = Field(..., description='AMI state')
    architecture: Optional[str] = Field(None, description='Architecture')
    platform: Optional[str] = Field(None, description='Platform')
    root_device_type: Optional[str] = Field(None, description='Root device type')
    virtualization_type: Optional[str] = Field(None, description='Virtualization type')
    creation_date: Optional[datetime] = Field(None, description='Creation date')
    public: bool = Field(False, description='Public AMI')
    tags: List[Tag] = Field(default_factory=list, description='Resource tags')

    model_config = {'populate_by_name': True}


class Vpc(BaseModel):
    """Virtual Private Cloud (VPC) model.
    
    Represents an Amazon VPC with metadata.
    
    Attributes:
        vpc_id: VPC ID (vpc-xxxxxxxx format).
        cidr_block: Primary CIDR block.
        state: VPC state (pending, available).
        is_default: Whether this is the default VPC.
        instance_tenancy: Instance tenancy (default, dedicated, host).
        dhcp_options_id: DHCP options set ID.
        tags: Resource tags.
    """
    
    vpc_id: str = Field(
        ..., 
        description='VPC ID',
        pattern=r'^vpc-[a-f0-9]{8,17}$'
    )
    cidr_block: str = Field(..., description='CIDR block')
    state: str = Field(..., description='VPC state')
    is_default: bool = Field(False, description='Default VPC')
    instance_tenancy: str = Field(..., description='Instance tenancy')
    dhcp_options_id: Optional[str] = Field(None, description='DHCP options ID')
    tags: List[Tag] = Field(default_factory=list, description='Resource tags')

    model_config = {'populate_by_name': True}


class Subnet(BaseModel):
    """VPC subnet model.
    
    Represents a VPC subnet with metadata.
    
    Attributes:
        subnet_id: Subnet ID (subnet-xxxxxxxx format).
        vpc_id: Parent VPC ID.
        cidr_block: Subnet CIDR block.
        availability_zone: Availability zone.
        state: Subnet state (pending, available).
        available_ip_address_count: Available IP addresses.
        map_public_ip_on_launch: Auto-assign public IP.
        default_for_az: Default subnet for AZ.
        tags: Resource tags.
    """
    
    subnet_id: str = Field(
        ..., 
        description='Subnet ID',
        pattern=r'^subnet-[a-f0-9]{8,17}$'
    )
    vpc_id: str = Field(
        ..., 
        description='VPC ID',
        pattern=r'^vpc-[a-f0-9]{8,17}$'
    )
    cidr_block: str = Field(..., description='CIDR block')
    availability_zone: str = Field(..., description='Availability zone')
    state: str = Field(..., description='Subnet state')
    available_ip_address_count: int = Field(..., description='Available IPs', ge=0)
    map_public_ip_on_launch: bool = Field(False, description='Auto-assign public IP')
    default_for_az: bool = Field(False, description='Default for AZ')
    tags: List[Tag] = Field(default_factory=list, description='Resource tags')

    model_config = {'populate_by_name': True}