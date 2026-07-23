"""
Unit tests for instances module.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from botocore.exceptions import ClientError

from awslabs.ec2_mcp_server.modules.instances import (
    list_instances,
    get_instance_details,
    launch_instance,
    terminate_instance,
    start_instance,
    stop_instance,
    reboot_instance,
    get_subnet_info,
    list_subnets,
    register_module
)


class TestListInstances:
    """Tests for list_instances function."""

    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @pytest.mark.asyncio
    async def test_list_instances_success(self, mock_aws_client, mock_instance_data):
        """Test successful instances listing."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_instances.return_value = {
            "Reservations": [
                {"Instances": [mock_instance_data]}
            ]
        }

        result = await list_instances()

        assert result["status"] == "success"
        assert result["count"] == 1
        assert len(result["instances"]) == 1
        assert result["instances"][0]["instance_id"] == "i-1234567890abcdef0"
        assert result["instances"][0]["instance_type"] == "t2.micro"
        assert result["instances"][0]["state"] == "running"

    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @pytest.mark.asyncio
    async def test_list_instances_with_filters(self, mock_aws_client, mock_instance_data):
        """Test instances listing with filters."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_instances.return_value = {
            "Reservations": [
                {"Instances": [mock_instance_data]}
            ]
        }

        filters = [{"Name": "instance-state-name", "Values": ["running"]}]
        instance_ids = ["i-1234567890abcdef0"]

        result = await list_instances(filters=filters, instance_ids=instance_ids)

        assert result["status"] == "success"
        mock_client.describe_instances.assert_called_once_with(
            Filters=filters,
            InstanceIds=instance_ids
        )

    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @pytest.mark.asyncio
    async def test_list_instances_client_error(self, mock_aws_client):
        """Test instances listing with client error."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_instances.side_effect = ClientError(
            error_response={"Error": {"Code": "InvalidInstanceId", "Message": "Invalid instance ID"}},
            operation_name="DescribeInstances"
        )

        result = await list_instances()

        assert result["status"] == "error"
        assert result["error"] == "InvalidInstanceId"

    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @pytest.mark.asyncio
    async def test_list_instances_general_exception(self, mock_aws_client):
        """Test instances listing with general exception."""
        mock_aws_client.get_client.side_effect = Exception("General error")

        result = await list_instances()

        assert result["status"] == "error"


class TestGetInstanceDetails:
    """Tests for get_instance_details function."""

    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.instances.validate_instance_id")
    @pytest.mark.asyncio
    async def test_get_instance_details_success(self, mock_validate, mock_aws_client, mock_instance_data):
        """Test successful instance details retrieval."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_instances.return_value = {
            "Reservations": [
                {"Instances": [mock_instance_data]}
            ]
        }

        result = await get_instance_details("i-1234567890abcdef0")

        assert result["status"] == "success"
        assert result["instance"]["instance_id"] == "i-1234567890abcdef0"
        assert result["instance"]["instance_type"] == "t2.micro"
        mock_validate.assert_called_once_with("i-1234567890abcdef0")

    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.instances.validate_instance_id")
    @pytest.mark.asyncio
    async def test_get_instance_details_not_found(self, mock_validate, mock_aws_client):
        """Test instance details when instance not found."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_instances.return_value = {"Reservations": []}

        result = await get_instance_details("i-1234567890abcdef0")

        assert result["status"] == "error"
        assert "not found" in result["message"]

    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.instances.validate_instance_id")
    @pytest.mark.asyncio
    async def test_get_instance_details_general_exception(self, mock_validate, mock_aws_client):
        """Test instance details with general exception."""
        mock_validate.return_value = True
        mock_aws_client.get_client.side_effect = Exception("General error")

        result = await get_instance_details("i-1234567890abcdef0")

        assert result["status"] == "error"


class TestLaunchInstance:
    """Tests for launch_instance function."""

    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.instances.validate_ami_id")
    @patch("awslabs.ec2_mcp_server.modules.vpc_management.find_suitable_subnet")
    @pytest.mark.asyncio
    async def test_launch_instance_success(self, mock_find_subnet, mock_validate, mock_aws_client, mock_instance_data):
        """Test successful instance launch."""
        mock_validate.return_value = True
        mock_find_subnet.return_value = {
            "status": "success",
            "subnet": {"subnet_id": "subnet-12345678"},
            "vpc_id": "vpc-12345678"
        }
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.run_instances.return_value = {
            "Instances": [mock_instance_data]
        }

        result = await launch_instance(
            ami_id="ami-12345678",
            instance_type="t2.micro",
            key_name="my-key",
            security_group_ids=["sg-12345678"],
            tags={"Name": "test-instance"}
        )

        assert result["status"] == "success"
        assert "Successfully launched" in result["message"]
        assert len(result["instances"]) == 1
        assert result["instances"][0]["instance_id"] == "i-1234567890abcdef0"

        # Verify the API call parameters
        call_args = mock_client.run_instances.call_args[1]
        assert call_args["ImageId"] == "ami-12345678"
        assert call_args["InstanceType"] == "t2.micro"
        assert call_args["KeyName"] == "my-key"
        assert call_args["SecurityGroupIds"] == ["sg-12345678"]
        assert "TagSpecifications" in call_args

    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.instances.validate_ami_id")
    @patch("awslabs.ec2_mcp_server.modules.vpc_management.find_suitable_subnet")
    @pytest.mark.asyncio
    async def test_launch_instance_minimal_params(self, mock_find_subnet, mock_validate, mock_aws_client, mock_instance_data):
        """Test instance launch with minimal parameters."""
        mock_validate.return_value = True
        mock_find_subnet.return_value = {
            "status": "success",
            "subnet": {"subnet_id": "subnet-12345678"},
            "vpc_id": "vpc-12345678"
        }
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.run_instances.return_value = {
            "Instances": [mock_instance_data]
        }

        result = await launch_instance(ami_id="ami-12345678")

        assert result["status"] == "success"
        
        # Verify minimal parameters
        call_args = mock_client.run_instances.call_args[1]
        assert call_args["ImageId"] == "ami-12345678"
        assert call_args["InstanceType"] == "t2.micro"  # Default
        assert call_args["MinCount"] == 1  # Default
        assert call_args["MaxCount"] == 1  # Default

    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.instances.validate_ami_id")
    @pytest.mark.asyncio
    async def test_launch_instance_with_public_ip(self, mock_validate, mock_aws_client, mock_instance_data):
        """Test instance launch with public IP configuration."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.run_instances.return_value = {
            "Instances": [mock_instance_data]
        }

        result = await launch_instance(
            ami_id="ami-12345678",
            subnet_id="subnet-12345678",
            associate_public_ip=True,
            security_group_ids=["sg-12345678"]
        )

        assert result["status"] == "success"
        
        # Verify NetworkInterfaces configuration for public IP
        call_args = mock_client.run_instances.call_args[1]
        assert "NetworkInterfaces" in call_args
        assert call_args["NetworkInterfaces"][0]["AssociatePublicIpAddress"] is True
        assert call_args["NetworkInterfaces"][0]["SubnetId"] == "subnet-12345678"
        assert "SubnetId" not in call_args  # Should be removed when using NetworkInterfaces
        assert "SecurityGroupIds" not in call_args  # Should be removed when using NetworkInterfaces

    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.instances.validate_ami_id")
    @patch("awslabs.ec2_mcp_server.modules.vpc_management.find_suitable_subnet")
    @pytest.mark.asyncio
    async def test_launch_instance_with_user_data(self, mock_find_subnet, mock_validate, mock_aws_client, mock_instance_data):
        """Test instance launch with user data script."""
        import base64
        
        mock_validate.return_value = True
        mock_find_subnet.return_value = {
            "status": "success",
            "subnet": {"subnet_id": "subnet-12345678"},
            "vpc_id": "vpc-12345678"
        }
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.run_instances.return_value = {
            "Instances": [mock_instance_data]
        }

        user_script = "#!/bin/bash\necho 'Hello World' > /tmp/hello.txt"
        result = await launch_instance(
            ami_id="ami-12345678",
            user_data=user_script
        )

        assert result["status"] == "success"
        
        # Verify user data is base64 encoded
        call_args = mock_client.run_instances.call_args[1]
        assert "UserData" in call_args
        decoded_data = base64.b64decode(call_args["UserData"]).decode('utf-8')
        assert decoded_data == user_script

    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.instances.validate_ami_id")
    @patch("awslabs.ec2_mcp_server.modules.vpc_management.find_suitable_subnet")
    @pytest.mark.asyncio
    async def test_launch_instance_with_monitoring_and_termination_protection(self, mock_find_subnet, mock_validate, mock_aws_client, mock_instance_data):
        """Test instance launch with monitoring and termination protection."""
        mock_validate.return_value = True
        mock_find_subnet.return_value = {
            "status": "success",
            "subnet": {"subnet_id": "subnet-12345678"},
            "vpc_id": "vpc-12345678"
        }
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.run_instances.return_value = {
            "Instances": [mock_instance_data]
        }

        result = await launch_instance(
            ami_id="ami-12345678",
            monitoring_enabled=True,
            disable_api_termination=True
        )

        assert result["status"] == "success"
        
        # Verify monitoring and termination protection
        call_args = mock_client.run_instances.call_args[1]
        assert call_args["Monitoring"]["Enabled"] is True
        assert call_args["DisableApiTermination"] is True


class TestGetSubnetInfo:
    """Tests for get_subnet_info function."""

    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @pytest.mark.asyncio
    async def test_get_subnet_info_public_subnet(self, mock_aws_client):
        """Test getting info for a public subnet."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        
        # Mock subnet response
        mock_client.describe_subnets.return_value = {
            "Subnets": [{
                "SubnetId": "subnet-12345678",
                "VpcId": "vpc-12345678",
                "AvailabilityZone": "us-east-1a",
                "CidrBlock": "10.0.1.0/24",
                "AvailableIpAddressCount": 250,
                "MapPublicIpOnLaunch": True,
                "State": "available",
                "Tags": [{"Key": "Name", "Value": "Public Subnet"}]
            }]
        }
        
        # Mock route table response with IGW route
        mock_client.describe_route_tables.return_value = {
            "RouteTables": [{
                "Routes": [
                    {"GatewayId": "igw-12345678", "DestinationCidrBlock": "0.0.0.0/0"}
                ]
            }]
        }

        result = await get_subnet_info("subnet-12345678")

        assert result["status"] == "success"
        assert result["subnet"]["is_public"] is True
        assert result["subnet"]["auto_assign_public_ip"] is True

    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @pytest.mark.asyncio
    async def test_get_subnet_info_private_subnet(self, mock_aws_client):
        """Test getting info for a private subnet."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        
        # Mock subnet response
        mock_client.describe_subnets.return_value = {
            "Subnets": [{
                "SubnetId": "subnet-87654321",
                "VpcId": "vpc-12345678",
                "AvailabilityZone": "us-east-1b",
                "CidrBlock": "10.0.2.0/24",
                "AvailableIpAddressCount": 250,
                "MapPublicIpOnLaunch": False,
                "State": "available",
                "Tags": [{"Key": "Name", "Value": "Private Subnet"}]
            }]
        }
        
        # Mock route table response without IGW route
        mock_client.describe_route_tables.return_value = {
            "RouteTables": [{
                "Routes": [
                    {"GatewayId": "local", "DestinationCidrBlock": "10.0.0.0/16"}
                ]
            }]
        }

        result = await get_subnet_info("subnet-87654321")

        assert result["status"] == "success"
        assert result["subnet"]["is_public"] is False
        assert result["subnet"]["auto_assign_public_ip"] is False


class TestListSubnets:
    """Tests for list_subnets function."""

    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.instances.get_subnet_info")
    @pytest.mark.asyncio
    async def test_list_subnets_success(self, mock_get_subnet_info, mock_aws_client):
        """Test successful subnets listing."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        
        mock_client.describe_subnets.return_value = {
            "Subnets": [
                {"SubnetId": "subnet-12345678"},
                {"SubnetId": "subnet-87654321"}
            ]
        }
        
        mock_get_subnet_info.side_effect = [
            {"status": "success", "subnet": {"subnet_id": "subnet-12345678", "is_public": True}},
            {"status": "success", "subnet": {"subnet_id": "subnet-87654321", "is_public": False}}
        ]

        result = await list_subnets()

        assert result["status"] == "success"
        assert result["count"] == 2
        assert len(result["subnets"]) == 2


class TestTerminateInstance:
    """Tests for terminate_instance function."""

    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.instances.validate_instance_id")
    @pytest.mark.asyncio
    async def test_terminate_instance_success(self, mock_validate, mock_aws_client):
        """Test successful instance termination."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.terminate_instances.return_value = {
            "TerminatingInstances": [
                {
                    "InstanceId": "i-1234567890abcdef0",
                    "CurrentState": {"Name": "shutting-down"},
                    "PreviousState": {"Name": "running"}
                }
            ]
        }

        result = await terminate_instance("i-1234567890abcdef0")

        assert result["status"] == "success"
        assert "Successfully initiated termination" in result["message"]
        assert len(result["terminating_instances"]) == 1
        assert result["terminating_instances"][0]["instance_id"] == "i-1234567890abcdef0"
        assert result["terminating_instances"][0]["current_state"] == "shutting-down"

        mock_client.terminate_instances.assert_called_once_with(
            InstanceIds=["i-1234567890abcdef0"]
        )

    @patch("awslabs.ec2_mcp_server.modules.instances.validate_instance_id")
    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @pytest.mark.asyncio
    async def test_terminate_instance_general_exception(self, mock_aws_client, mock_validate):
        """Test terminate instance with general exception."""
        mock_validate.return_value = True
        mock_aws_client.get_client.side_effect = Exception("General error")

        result = await terminate_instance("i-1234567890abcdef0")

        assert result["status"] == "error"


class TestStartInstance:
    """Tests for start_instance function."""

    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.instances.validate_instance_id")
    @pytest.mark.asyncio
    async def test_start_instance_success(self, mock_validate, mock_aws_client):
        """Test successful instance start."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.start_instances.return_value = {
            "StartingInstances": [
                {
                    "InstanceId": "i-1234567890abcdef0",
                    "CurrentState": {"Name": "pending"},
                    "PreviousState": {"Name": "stopped"}
                }
            ]
        }

        result = await start_instance("i-1234567890abcdef0")

        assert result["status"] == "success"
        assert "Successfully started" in result["message"]
        assert len(result["starting_instances"]) == 1
        assert result["starting_instances"][0]["current_state"] == "pending"

        mock_client.start_instances.assert_called_once_with(
            InstanceIds=["i-1234567890abcdef0"]
        )

    @patch("awslabs.ec2_mcp_server.modules.instances.validate_instance_id")
    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @pytest.mark.asyncio
    async def test_start_instance_general_exception(self, mock_aws_client, mock_validate):
        """Test start instance with general exception."""
        mock_validate.return_value = True
        mock_aws_client.get_client.side_effect = Exception("General error")

        result = await start_instance("i-1234567890abcdef0")

        assert result["status"] == "error"


class TestStopInstance:
    """Tests for stop_instance function."""

    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.instances.validate_instance_id")
    @pytest.mark.asyncio
    async def test_stop_instance_success(self, mock_validate, mock_aws_client):
        """Test successful instance stop."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.stop_instances.return_value = {
            "StoppingInstances": [
                {
                    "InstanceId": "i-1234567890abcdef0",
                    "CurrentState": {"Name": "stopping"},
                    "PreviousState": {"Name": "running"}
                }
            ]
        }

        result = await stop_instance("i-1234567890abcdef0", force=True)

        assert result["status"] == "success"
        assert "Successfully stopped" in result["message"]
        assert len(result["stopping_instances"]) == 1
        assert result["stopping_instances"][0]["current_state"] == "stopping"

        mock_client.stop_instances.assert_called_once_with(
            InstanceIds=["i-1234567890abcdef0"],
            Force=True
        )

    @patch("awslabs.ec2_mcp_server.modules.instances.validate_instance_id")
    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @pytest.mark.asyncio
    async def test_stop_instance_general_exception(self, mock_aws_client, mock_validate):
        """Test stop instance with general exception."""
        mock_validate.return_value = True
        mock_aws_client.get_client.side_effect = Exception("General error")

        result = await stop_instance("i-1234567890abcdef0")

        assert result["status"] == "error"


class TestRebootInstance:
    """Tests for reboot_instance function."""

    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.instances.validate_instance_id")
    @pytest.mark.asyncio
    async def test_reboot_instance_success(self, mock_validate, mock_aws_client):
        """Test successful instance reboot."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client

        result = await reboot_instance("i-1234567890abcdef0")

        assert result["status"] == "success"
        assert "Successfully initiated reboot" in result["message"]
        assert result["instance_id"] == "i-1234567890abcdef0"

        mock_client.reboot_instances.assert_called_once_with(
            InstanceIds=["i-1234567890abcdef0"]
        )

    @patch("awslabs.ec2_mcp_server.modules.instances.validate_instance_id")
    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @pytest.mark.asyncio
    async def test_reboot_instance_general_exception(self, mock_aws_client, mock_validate):
        """Test reboot instance with general exception."""
        mock_validate.return_value = True
        mock_aws_client.get_client.side_effect = Exception("General error")

        result = await reboot_instance("i-1234567890abcdef0")

        assert result["status"] == "error"


class TestRegisterModule:
    """Tests for register_module function."""

    def test_register_module(self):
        """Test module registration with FastMCP."""
        mock_mcp = MagicMock()

        register_module(mock_mcp)

        # Verify that all expected tools are registered
        expected_tools = [
            "list_instances",
            "get_instance_details", 
            "launch_instance",
            "terminate_instance",
            "start_instance",
            "stop_instance",
            "reboot_instance",
            "get_subnet_info"
        ]

        # Check that mcp.tool was called for each expected tool
        assert mock_mcp.tool.call_count == len(expected_tools)
        
        # Verify specific tool registrations
        tool_calls = [call[0][0] for call in mock_mcp.tool.call_args_list]
        for expected_tool in expected_tools:
            assert expected_tool in tool_calls


class TestAdditionalInstanceCases:
    """Additional tests to improve coverage."""

    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @pytest.mark.asyncio
    async def test_list_instances_empty_reservations(self, mock_aws_client):
        """Test listing instances with empty reservations."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_instances.return_value = {"Reservations": []}

        result = await list_instances()

        assert result["status"] == "success"
        assert result["count"] == 0
        assert result["instances"] == []

    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @pytest.mark.asyncio
    async def test_list_instances_partial_data(self, mock_aws_client):
        """Test listing instances with minimal required data."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        
        # Instance with minimal required data
        from datetime import datetime
        minimal_instance = {
            "InstanceId": "i-minimal123",
            "InstanceType": "t2.nano", 
            "State": {"Name": "pending"},
            "ImageId": "ami-minimal",  # Required field
            "LaunchTime": datetime(2023, 1, 1, 12, 0, 0),
            "Placement": {"AvailabilityZone": "us-east-1a"},
            "SecurityGroups": [],
            "Tags": []
        }
        
        mock_client.describe_instances.return_value = {
            "Reservations": [{"Instances": [minimal_instance]}]
        }

        result = await list_instances()

        assert result["status"] == "success"
        assert result["count"] == 1
        assert result["instances"][0]["instance_id"] == "i-minimal123"
        assert result["instances"][0]["state"] == "pending"

    @patch("awslabs.ec2_mcp_server.modules.instances.validate_instance_id")
    @pytest.mark.asyncio
    async def test_get_instance_details_invalid_id_format(self, mock_validate):
        """Test get instance details with invalid ID format."""
        mock_validate.side_effect = Exception("Invalid instance ID format")

        result = await get_instance_details("invalid-instance-id")

        assert result["status"] == "error"
        mock_validate.assert_called_once_with("invalid-instance-id")

    @patch("awslabs.ec2_mcp_server.modules.instances.validate_ami_id")
    @pytest.mark.asyncio
    async def test_launch_instance_invalid_ami_id(self, mock_validate):
        """Test launch instance with invalid AMI ID format."""
        mock_validate.side_effect = Exception("Invalid AMI ID format")

        result = await launch_instance(ami_id="invalid-ami-id")

        assert result["status"] == "error"
        mock_validate.assert_called_once_with("invalid-ami-id")

    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.instances.validate_ami_id")
    @patch("awslabs.ec2_mcp_server.modules.vpc_management.find_suitable_subnet")
    @pytest.mark.asyncio
    async def test_launch_instance_subnet_find_error(self, mock_find_subnet, mock_validate, mock_aws_client):
        """Test launch instance when subnet finding fails."""
        mock_validate.return_value = True
        mock_find_subnet.return_value = {
            "status": "error",
            "message": "No suitable subnet found"
        }

        result = await launch_instance(ami_id="ami-12345678")

        assert result["status"] == "error"
        assert "No suitable subnet found" in result["message"]

    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.instances.validate_ami_id")
    @patch("awslabs.ec2_mcp_server.modules.vpc_management.find_suitable_subnet")
    @pytest.mark.asyncio
    async def test_launch_instance_run_instances_error(self, mock_find_subnet, mock_validate, mock_aws_client):
        """Test launch instance when run_instances fails."""
        mock_validate.return_value = True
        mock_find_subnet.return_value = {
            "status": "success",
            "subnet": {"subnet_id": "subnet-12345678"},
            "vpc_id": "vpc-12345678"
        }
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.run_instances.side_effect = ClientError(
            error_response={"Error": {"Code": "InsufficientInstanceCapacity", "Message": "No capacity"}},
            operation_name="RunInstances"
        )

        result = await launch_instance(ami_id="ami-12345678")

        assert result["status"] == "error"
        assert result["error"] == "InsufficientInstanceCapacity"

    @patch("awslabs.ec2_mcp_server.modules.instances.validate_instance_id")
    @pytest.mark.asyncio
    async def test_terminate_instance_invalid_id(self, mock_validate):
        """Test terminate instance with invalid ID format."""
        mock_validate.side_effect = Exception("Invalid instance ID format")

        result = await terminate_instance("invalid-id")

        assert result["status"] == "error"
        mock_validate.assert_called_once_with("invalid-id")

    @patch("awslabs.ec2_mcp_server.modules.instances.validate_instance_id")
    @pytest.mark.asyncio
    async def test_start_instance_invalid_id(self, mock_validate):
        """Test start instance with invalid ID format."""
        mock_validate.side_effect = Exception("Invalid instance ID format")

        result = await start_instance("invalid-id")

        assert result["status"] == "error"
        mock_validate.assert_called_once_with("invalid-id")

    @patch("awslabs.ec2_mcp_server.modules.instances.validate_instance_id")
    @pytest.mark.asyncio
    async def test_stop_instance_invalid_id(self, mock_validate):
        """Test stop instance with invalid ID format."""
        mock_validate.side_effect = Exception("Invalid instance ID format")

        result = await stop_instance("invalid-id")

        assert result["status"] == "error"
        mock_validate.assert_called_once_with("invalid-id")

    @patch("awslabs.ec2_mcp_server.modules.instances.validate_instance_id")
    @pytest.mark.asyncio
    async def test_reboot_instance_invalid_id(self, mock_validate):
        """Test reboot instance with invalid ID format."""
        mock_validate.side_effect = Exception("Invalid instance ID format")

        result = await reboot_instance("invalid-id")

        assert result["status"] == "error"
        mock_validate.assert_called_once_with("invalid-id")

    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @pytest.mark.asyncio
    async def test_get_subnet_info_client_error(self, mock_aws_client):
        """Test get subnet info with client error."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_subnets.side_effect = ClientError(
            error_response={"Error": {"Code": "InvalidSubnetID.NotFound", "Message": "Subnet not found"}},
            operation_name="DescribeSubnets"
        )

        result = await get_subnet_info("subnet-invalid")

        assert result["status"] == "error"
        assert result["error"] == "InvalidSubnetID.NotFound"

    @patch("awslabs.ec2_mcp_server.modules.instances.aws_client")
    @pytest.mark.asyncio
    async def test_list_subnets_client_error(self, mock_aws_client):
        """Test list subnets with client error."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_subnets.side_effect = ClientError(
            error_response={"Error": {"Code": "UnauthorizedOperation", "Message": "Not authorized"}},
            operation_name="DescribeSubnets"
        )

        result = await list_subnets()

        assert result["status"] == "error"
        assert result["error"] == "UnauthorizedOperation"