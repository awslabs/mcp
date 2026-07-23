"""
Unit tests for security groups module.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from botocore.exceptions import ClientError

from awslabs.ec2_mcp_server.modules.security_groups import (
    list_security_groups,
    get_security_group_details,
    create_security_group,
    delete_security_group,
    modify_security_group_rules,
    register_module
)


class TestListSecurityGroups:
    """Tests for list_security_groups function."""

    @patch("awslabs.ec2_mcp_server.modules.security_groups.aws_client")
    @pytest.mark.asyncio
    async def test_list_security_groups_success(self, mock_aws_client, mock_security_group_data):
        """Test successful security groups listing."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_security_groups.return_value = {
            "SecurityGroups": [mock_security_group_data]
        }

        result = await list_security_groups()

        assert result["status"] == "success"
        assert result["count"] == 1
        assert len(result["security_groups"]) == 1
        assert result["security_groups"][0]["group_id"] == "sg-12345678"
        assert result["security_groups"][0]["group_name"] == "test-sg"

    @patch("awslabs.ec2_mcp_server.modules.security_groups.aws_client")
    @pytest.mark.asyncio
    async def test_list_security_groups_with_filters(self, mock_aws_client, mock_security_group_data):
        """Test security groups listing with filters."""
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_security_groups.return_value = {
            "SecurityGroups": [mock_security_group_data]
        }

        group_ids = ["sg-12345678"]
        group_names = ["test-sg"]
        filters = [{"Name": "vpc-id", "Values": ["vpc-12345678"]}]

        result = await list_security_groups(
            group_ids=group_ids,
            group_names=group_names,
            filters=filters
        )

        assert result["status"] == "success"
        
        call_args = mock_client.describe_security_groups.call_args[1]
        assert call_args["GroupIds"] == group_ids
        assert call_args["GroupNames"] == group_names
        assert call_args["Filters"] == filters


class TestGetSecurityGroupDetails:
    """Tests for get_security_group_details function."""

    @patch("awslabs.ec2_mcp_server.modules.security_groups.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.security_groups.validate_security_group_id")
    @pytest.mark.asyncio
    async def test_get_security_group_details_success(self, mock_validate, mock_aws_client, mock_security_group_data):
        """Test successful security group details retrieval."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_security_groups.return_value = {
            "SecurityGroups": [mock_security_group_data]
        }

        result = await get_security_group_details("sg-12345678")

        assert result["status"] == "success"
        assert result["security_group"]["group_id"] == "sg-12345678"
        assert result["security_group"]["group_name"] == "test-sg"
        mock_validate.assert_called_once_with("sg-12345678")

    @patch("awslabs.ec2_mcp_server.modules.security_groups.aws_client")
    @pytest.mark.asyncio
    async def test_list_security_groups_general_exception(self, mock_aws_client):
        """Test list security groups with general exception."""
        mock_aws_client.get_client.side_effect = Exception("General error")

        result = await list_security_groups()

        assert result["status"] == "error"

    @patch("awslabs.ec2_mcp_server.modules.security_groups.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.security_groups.validate_security_group_id")
    @pytest.mark.asyncio
    async def test_get_security_group_details_not_found(self, mock_validate, mock_aws_client):
        """Test security group details when not found."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.describe_security_groups.return_value = {"SecurityGroups": []}

        result = await get_security_group_details("sg-12345678")

        assert result["status"] == "error"
        assert "not found" in result["message"]

    @patch("awslabs.ec2_mcp_server.modules.security_groups.validate_security_group_id")
    @patch("awslabs.ec2_mcp_server.modules.security_groups.aws_client")
    @pytest.mark.asyncio
    async def test_get_security_group_details_general_exception(self, mock_aws_client, mock_validate):
        """Test get security group details with general exception."""
        mock_validate.return_value = True
        mock_aws_client.get_client.side_effect = Exception("General error")

        result = await get_security_group_details("sg-12345678")

        assert result["status"] == "error"


class TestCreateSecurityGroup:
    """Tests for create_security_group function."""

    @patch("awslabs.ec2_mcp_server.modules.security_groups.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.security_groups.validate_vpc_id")
    @pytest.mark.asyncio
    async def test_create_security_group_success(self, mock_validate, mock_aws_client):
        """Test successful security group creation."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.create_security_group.return_value = {
            "GroupId": "sg-12345678"
        }

        result = await create_security_group(
            group_name="test-sg",
            description="Test security group",
            vpc_id="vpc-12345678",
            tags={"Environment": "test"}
        )

        assert result["status"] == "success"
        assert "Successfully created security group" in result["message"]
        assert result["group_id"] == "sg-12345678"
        assert result["group_name"] == "test-sg"
        assert result["vpc_id"] == "vpc-12345678"

        # Verify API calls
        mock_client.create_security_group.assert_called_once_with(
            GroupName="test-sg",
            Description="Test security group",
            VpcId="vpc-12345678"
        )
        mock_client.create_tags.assert_called_once()

    @patch("awslabs.ec2_mcp_server.modules.security_groups.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.security_groups.validate_vpc_id")
    @pytest.mark.asyncio
    async def test_create_security_group_without_tags(self, mock_validate, mock_aws_client):
        """Test security group creation without tags."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client
        mock_client.create_security_group.return_value = {
            "GroupId": "sg-12345678"
        }

        result = await create_security_group(
            group_name="test-sg",
            description="Test security group", 
            vpc_id="vpc-12345678"
        )

        assert result["status"] == "success"
        
        # Verify that create_tags was not called
        mock_client.create_tags.assert_not_called()

    @patch("awslabs.ec2_mcp_server.modules.security_groups.validate_vpc_id")
    @patch("awslabs.ec2_mcp_server.modules.security_groups.aws_client")
    @pytest.mark.asyncio
    async def test_create_security_group_general_exception(self, mock_aws_client, mock_validate):
        """Test create security group with general exception."""
        mock_validate.return_value = True
        mock_aws_client.get_client.side_effect = Exception("General error")

        result = await create_security_group(
            group_name="test-sg",
            description="Test security group",
            vpc_id="vpc-12345678"
        )

        assert result["status"] == "error"


class TestDeleteSecurityGroup:
    """Tests for delete_security_group function."""

    @patch("awslabs.ec2_mcp_server.modules.security_groups.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.security_groups.validate_security_group_id")
    @pytest.mark.asyncio
    async def test_delete_security_group_success(self, mock_validate, mock_aws_client):
        """Test successful security group deletion."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client

        result = await delete_security_group("sg-12345678")

        assert result["status"] == "success"
        assert "Successfully deleted security group" in result["message"]
        assert result["group_id"] == "sg-12345678"

        mock_client.delete_security_group.assert_called_once_with(GroupId="sg-12345678")

    @patch("awslabs.ec2_mcp_server.modules.security_groups.validate_security_group_id")
    @patch("awslabs.ec2_mcp_server.modules.security_groups.aws_client")
    @pytest.mark.asyncio
    async def test_delete_security_group_general_exception(self, mock_aws_client, mock_validate):
        """Test delete security group with general exception."""
        mock_validate.return_value = True
        mock_aws_client.get_client.side_effect = Exception("General error")

        result = await delete_security_group("sg-12345678")

        assert result["status"] == "error"


class TestModifySecurityGroupRules:
    """Tests for modify_security_group_rules function."""

    @patch("awslabs.ec2_mcp_server.modules.security_groups.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.security_groups.validate_security_group_id")
    @pytest.mark.asyncio
    async def test_modify_security_group_rules_add_inbound(self, mock_validate, mock_aws_client):
        """Test adding inbound security group rule."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client

        result = await modify_security_group_rules(
            group_id="sg-12345678",
            action="add",
            rule_type="inbound",
            ip_protocol="tcp",
            from_port=80,
            to_port=80,
            cidr_blocks=["0.0.0.0/0"]
        )

        assert result["status"] == "success"
        assert "Successfully added inbound rule" in result["message"]
        assert result["group_id"] == "sg-12345678"
        assert result["action"] == "add"
        assert result["rule_type"] == "inbound"

        # Verify API call
        call_args = mock_client.authorize_security_group_ingress.call_args[1]
        assert call_args["GroupId"] == "sg-12345678"
        assert len(call_args["IpPermissions"]) == 1
        assert call_args["IpPermissions"][0]["IpProtocol"] == "tcp"
        assert call_args["IpPermissions"][0]["FromPort"] == 80
        assert call_args["IpPermissions"][0]["ToPort"] == 80

    @patch("awslabs.ec2_mcp_server.modules.security_groups.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.security_groups.validate_security_group_id")
    @pytest.mark.asyncio
    async def test_modify_security_group_rules_remove_outbound(self, mock_validate, mock_aws_client):
        """Test removing outbound security group rule."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client

        result = await modify_security_group_rules(
            group_id="sg-12345678",
            action="remove",
            rule_type="outbound",
            ip_protocol="tcp",
            from_port=443,
            to_port=443,
            cidr_blocks=["0.0.0.0/0"]
        )

        assert result["status"] == "success"
        assert "Successfully removed outbound rule" in result["message"]

        # Verify API call
        call_args = mock_client.revoke_security_group_egress.call_args[1]
        assert call_args["GroupId"] == "sg-12345678"

    @patch("awslabs.ec2_mcp_server.modules.security_groups.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.security_groups.validate_security_group_id")
    @pytest.mark.asyncio
    async def test_modify_security_group_rules_with_source_sg(self, mock_validate, mock_aws_client):
        """Test modifying security group rule with source security group."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client

        result = await modify_security_group_rules(
            group_id="sg-12345678",
            action="add",
            rule_type="inbound",
            ip_protocol="tcp",
            from_port=3306,
            to_port=3306,
            source_security_group_id="sg-87654321"
        )

        assert result["status"] == "success"

        # Verify API call includes source security group
        call_args = mock_client.authorize_security_group_ingress.call_args[1]
        ip_permission = call_args["IpPermissions"][0]
        assert ip_permission["UserIdGroupPairs"] == [{"GroupId": "sg-87654321"}]

    @pytest.mark.asyncio
    async def test_modify_security_group_rules_invalid_action(self):
        """Test modifying security group rule with invalid action."""
        result = await modify_security_group_rules(
            group_id="sg-12345678",
            action="invalid",
            rule_type="inbound",
            ip_protocol="tcp"
        )

        assert result["status"] == "error"
        assert "Action must be either 'add' or 'remove'" in result["message"]

    @pytest.mark.asyncio
    async def test_modify_security_group_rules_invalid_rule_type(self):
        """Test modifying security group rule with invalid rule type."""
        result = await modify_security_group_rules(
            group_id="sg-12345678",
            action="add",
            rule_type="invalid",
            ip_protocol="tcp"
        )

        assert result["status"] == "error"
        assert "Rule type must be either 'inbound' or 'outbound'" in result["message"]

    @patch("awslabs.ec2_mcp_server.modules.security_groups.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.security_groups.validate_security_group_id")
    @pytest.mark.asyncio
    async def test_modify_security_group_rules_add_outbound(self, mock_validate, mock_aws_client):
        """Test adding outbound security group rule."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client

        result = await modify_security_group_rules(
            group_id="sg-12345678",
            action="add",
            rule_type="outbound",
            ip_protocol="tcp",
            from_port=443,
            to_port=443,
            cidr_blocks=["0.0.0.0/0"]
        )

        assert result["status"] == "success"
        assert "Successfully added outbound rule" in result["message"]

        # Verify API call
        call_args = mock_client.authorize_security_group_egress.call_args[1]
        assert call_args["GroupId"] == "sg-12345678"

    @patch("awslabs.ec2_mcp_server.modules.security_groups.aws_client")
    @patch("awslabs.ec2_mcp_server.modules.security_groups.validate_security_group_id")
    @pytest.mark.asyncio
    async def test_modify_security_group_rules_remove_inbound(self, mock_validate, mock_aws_client):
        """Test removing inbound security group rule."""
        mock_validate.return_value = True
        mock_client = MagicMock()
        mock_aws_client.get_client.return_value = mock_client

        result = await modify_security_group_rules(
            group_id="sg-12345678",
            action="remove",
            rule_type="inbound",
            ip_protocol="tcp",
            from_port=80,
            to_port=80,
            cidr_blocks=["0.0.0.0/0"]
        )

        assert result["status"] == "success"
        assert "Successfully removed inbound rule" in result["message"]

        # Verify API call
        call_args = mock_client.revoke_security_group_ingress.call_args[1]
        assert call_args["GroupId"] == "sg-12345678"

    @patch("awslabs.ec2_mcp_server.modules.security_groups.validate_security_group_id")
    @patch("awslabs.ec2_mcp_server.modules.security_groups.aws_client")
    @pytest.mark.asyncio
    async def test_modify_security_group_rules_general_exception(self, mock_aws_client, mock_validate):
        """Test modify security group rules with general exception."""
        mock_validate.return_value = True
        mock_aws_client.get_client.side_effect = Exception("General error")

        result = await modify_security_group_rules(
            group_id="sg-12345678",
            action="add",
            rule_type="inbound",
            ip_protocol="tcp"
        )

        assert result["status"] == "error"


class TestRegisterModule:
    """Tests for register_module function."""

    def test_register_module(self):
        """Test module registration with FastMCP."""
        mock_mcp = MagicMock()

        register_module(mock_mcp)

        # Verify that all expected tools are registered
        expected_tools = [
            "list_security_groups",
            "get_security_group_details",
            "create_security_group",
            "delete_security_group",
            "modify_security_group_rules"
        ]

        # Check that mcp.tool was called for each expected tool
        assert mock_mcp.tool.call_count == len(expected_tools)
        
        # Verify specific tool registrations
        tool_calls = [call[0][0] for call in mock_mcp.tool.call_args_list]
        for expected_tool in expected_tools:
            assert expected_tool in tool_calls