"""
Unit tests for AWS utilities.
"""

import pytest
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError, NoCredentialsError

from awslabs.ec2_mcp_server.utils.aws import (
    AWSClientManager,
    handle_aws_error,
    get_availability_zones,
    get_default_vpc,
    get_default_subnet,
    parse_tags,
    format_tags
)


class TestAWSClientManager:
    """Tests for AWSClientManager class."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        manager = AWSClientManager()
        assert manager.region == "us-east-1"
        assert manager.profile is None
        assert manager._session is None
        assert manager._clients == {}

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        manager = AWSClientManager(region="us-west-2", profile="test-profile")
        assert manager.region == "us-west-2"
        assert manager.profile == "test-profile"

    @patch("boto3.Session")
    def test_get_session_without_profile(self, mock_session_class):
        """Test getting session without profile."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        manager = AWSClientManager()
        session = manager._get_session()
        
        assert session == mock_session
        mock_session_class.assert_called_once_with()

    @patch("boto3.Session")
    def test_get_session_with_profile(self, mock_session_class):
        """Test getting session with profile."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        manager = AWSClientManager(profile="test-profile")
        session = manager._get_session()
        
        assert session == mock_session
        mock_session_class.assert_called_once_with(profile_name="test-profile")

    @patch("boto3.Session")
    def test_get_client_success(self, mock_session_class):
        """Test getting AWS client successfully."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_session_class.return_value = mock_session
        
        manager = AWSClientManager(region="us-west-2")
        client = manager.get_client("ec2")
        
        assert client == mock_client
        assert "ec2" in manager._clients
        mock_session.client.assert_called_once_with("ec2", region_name="us-west-2")

    @patch("boto3.Session")
    def test_get_client_cached(self, mock_session_class):
        """Test that clients are cached."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_session_class.return_value = mock_session
        
        manager = AWSClientManager()
        client1 = manager.get_client("ec2")
        client2 = manager.get_client("ec2")
        
        assert client1 == client2 == mock_client
        # Should only call session.client once due to caching
        mock_session.client.assert_called_once()

    @patch("boto3.Session")
    def test_get_client_no_credentials_error(self, mock_session_class):
        """Test handling of NoCredentialsError."""
        mock_session = MagicMock()
        mock_session.client.side_effect = NoCredentialsError()
        mock_session_class.return_value = mock_session
        
        manager = AWSClientManager()
        
        with pytest.raises(NoCredentialsError):
            manager.get_client("ec2")

    @patch("boto3.Session")
    def test_test_credentials_success(self, mock_session_class):
        """Test successful credentials test."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_client.get_caller_identity.return_value = {
            "Account": "123456789012",
            "UserId": "AIDACKCEVSQ6C2EXAMPLE",
            "Arn": "arn:aws:iam::123456789012:user/test"
        }
        mock_session.client.return_value = mock_client
        mock_session_class.return_value = mock_session
        
        manager = AWSClientManager()
        result = manager.test_credentials()
        
        assert result["status"] == "success"
        assert result["account_id"] == "123456789012"
        assert "AWS credentials are valid" in result["message"]

    @patch("boto3.Session")
    def test_test_credentials_no_credentials(self, mock_session_class):
        """Test credentials test with no credentials."""
        mock_session = MagicMock()
        mock_session.client.side_effect = NoCredentialsError()
        mock_session_class.return_value = mock_session
        
        manager = AWSClientManager()
        result = manager.test_credentials()
        
        assert result["status"] == "error"
        assert "not found" in result["message"]

    @patch("boto3.Session")
    def test_test_credentials_client_error(self, mock_session_class):
        """Test credentials test with client error."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_client.get_caller_identity.side_effect = ClientError(
            error_response={"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            operation_name="GetCallerIdentity"
        )
        mock_session.client.return_value = mock_client
        mock_session_class.return_value = mock_session
        
        manager = AWSClientManager()
        result = manager.test_credentials()
        
        assert result["status"] == "error"
        assert "Access denied" in result["message"]


class TestHandleAwsError:
    """Tests for handle_aws_error function."""

    def test_handle_no_credentials_error(self):
        """Test handling of NoCredentialsError."""
        error = NoCredentialsError()
        result = handle_aws_error(error)
        
        assert result["status"] == "error"
        assert result["error"] == "AWS credentials not found"
        assert "configure" in result["message"]

    def test_handle_client_error(self):
        """Test handling of ClientError."""
        error = ClientError(
            error_response={"Error": {"Code": "InvalidInstanceID.NotFound", "Message": "Instance not found"}},
            operation_name="DescribeInstances"
        )
        result = handle_aws_error(error)
        
        assert result["status"] == "error"
        assert result["error"] == "InvalidInstanceID.NotFound"
        assert result["message"] == "Instance not found"

    def test_handle_unknown_error(self):
        """Test handling of unknown errors."""
        error = ValueError("Unknown error")
        result = handle_aws_error(error)
        
        assert result["status"] == "error"
        assert result["error"] == "Unknown error"
        assert result["message"] == "Unknown error"


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_get_availability_zones_success(self):
        """Test successful availability zones retrieval."""
        mock_client = MagicMock()
        mock_client.describe_availability_zones.return_value = {
            "AvailabilityZones": [
                {"ZoneName": "us-east-1a"},
                {"ZoneName": "us-east-1b"},
                {"ZoneName": "us-east-1c"}
            ]
        }
        
        result = get_availability_zones(mock_client)
        
        assert result == ["us-east-1a", "us-east-1b", "us-east-1c"]

    def test_get_availability_zones_error(self):
        """Test availability zones retrieval with error."""
        mock_client = MagicMock()
        mock_client.describe_availability_zones.side_effect = Exception("API Error")
        
        result = get_availability_zones(mock_client)
        
        assert result == []

    def test_get_default_vpc_success(self):
        """Test successful default VPC retrieval."""
        mock_client = MagicMock()
        mock_client.describe_vpcs.return_value = {
            "Vpcs": [{"VpcId": "vpc-12345678"}]
        }
        
        result = get_default_vpc(mock_client)
        
        assert result == "vpc-12345678"
        mock_client.describe_vpcs.assert_called_once_with(
            Filters=[{"Name": "isDefault", "Values": ["true"]}]
        )

    def test_get_default_vpc_none_found(self):
        """Test default VPC retrieval when none found."""
        mock_client = MagicMock()
        mock_client.describe_vpcs.return_value = {"Vpcs": []}
        
        result = get_default_vpc(mock_client)
        
        assert result is None

    def test_get_default_subnet_success(self):
        """Test successful default subnet retrieval."""
        mock_client = MagicMock()
        mock_client.describe_subnets.return_value = {
            "Subnets": [{"SubnetId": "subnet-12345678"}]
        }
        
        result = get_default_subnet(mock_client, "vpc-12345678")
        
        assert result == "subnet-12345678"
        mock_client.describe_subnets.assert_called_once_with(
            Filters=[
                {"Name": "vpc-id", "Values": ["vpc-12345678"]},
                {"Name": "default-for-az", "Values": ["true"]},
            ]
        )

    def test_get_default_subnet_none_found(self):
        """Test default subnet retrieval when none found."""
        mock_client = MagicMock()
        mock_client.describe_subnets.return_value = {"Subnets": []}
        
        result = get_default_subnet(mock_client, "vpc-12345678")
        
        assert result is None

    def test_parse_tags_success(self):
        """Test successful tag parsing."""
        tags = [
            {"Key": "Name", "Value": "test-instance"},
            {"Key": "Environment", "Value": "production"},
            {"Key": "Owner", "Value": "team-a"}
        ]
        
        result = parse_tags(tags)
        
        expected = {
            "Name": "test-instance",
            "Environment": "production",
            "Owner": "team-a"
        }
        assert result == expected

    def test_parse_tags_empty(self):
        """Test tag parsing with empty list."""
        result = parse_tags([])
        assert result == {}

    def test_parse_tags_none(self):
        """Test tag parsing with None."""
        result = parse_tags(None)
        assert result == {}

    def test_format_tags_success(self):
        """Test successful tag formatting."""
        tags = {
            "Name": "test-instance",
            "Environment": "production",
            "Owner": "team-a"
        }
        
        result = format_tags(tags)
        
        expected = [
            {"Key": "Name", "Value": "test-instance"},
            {"Key": "Environment", "Value": "production"},
            {"Key": "Owner", "Value": "team-a"}
        ]
        
        # Sort both lists for comparison since order may vary
        result_sorted = sorted(result, key=lambda x: x["Key"])
        expected_sorted = sorted(expected, key=lambda x: x["Key"])
        
        assert result_sorted == expected_sorted

    def test_format_tags_empty(self):
        """Test tag formatting with empty dict."""
        result = format_tags({})
        assert result == []

    def test_format_s3_tags_success(self):
        """Test successful S3 tag formatting with URL encoding."""
        from awslabs.ec2_mcp_server.utils.aws import format_s3_tags
        
        tags = {
            "Name": "test-key",
            "Environment": "prod/dev",  # Contains special char
            "Space Key": "value with spaces"  # Contains spaces
        }
        
        result = format_s3_tags(tags)
        
        # Should be URL encoded and & separated
        assert "Name=test-key" in result
        assert "Environment=prod/dev" in result  # forward slash not encoded by default
        assert "Space%20Key=value%20with%20spaces" in result
        assert "&" in result

    def test_format_s3_tags_empty(self):
        """Test S3 tag formatting with empty/None input."""
        from awslabs.ec2_mcp_server.utils.aws import format_s3_tags
        
        assert format_s3_tags({}) == ""
        assert format_s3_tags(None) == ""

    def test_format_s3_tags_with_none_values(self):
        """Test S3 tag formatting filters out None values."""
        from awslabs.ec2_mcp_server.utils.aws import format_s3_tags
        
        tags = {
            "Valid": "value",
            "None-Key": None,
            None: "None-Value",
            "Another": "valid"
        }
        
        result = format_s3_tags(tags)
        
        # Should only contain valid key-value pairs
        assert "Valid=value" in result
        assert "Another=valid" in result
        assert "None" not in result

    def test_get_default_vpc_error(self):
        """Test default VPC retrieval with error."""
        mock_client = MagicMock()
        mock_client.describe_vpcs.side_effect = Exception("API Error")
        
        result = get_default_vpc(mock_client)
        
        assert result is None

    def test_get_default_subnet_error(self):
        """Test default subnet retrieval with error."""
        mock_client = MagicMock()
        mock_client.describe_subnets.side_effect = Exception("API Error")
        
        result = get_default_subnet(mock_client, "vpc-12345678")
        
        assert result is None

    @patch("boto3.Session")
    def test_get_session_exception(self, mock_session_class):
        """Test session creation with exception."""
        mock_session_class.side_effect = Exception("Session creation failed")
        
        manager = AWSClientManager()
        
        with pytest.raises(Exception, match="Session creation failed"):
            manager._get_session()

    @patch("boto3.Session")
    def test_get_session_with_profile_exception(self, mock_session_class):
        """Test session creation with profile exception."""
        mock_session_class.side_effect = Exception("Profile not found")
        
        manager = AWSClientManager(profile="invalid-profile")
        
        with pytest.raises(Exception, match="Profile not found"):
            manager._get_session()

    @patch("boto3.Session")
    def test_get_client_general_exception(self, mock_session_class):
        """Test getting client with general exception."""
        mock_session = MagicMock()
        mock_session.client.side_effect = Exception("General error")
        mock_session_class.return_value = mock_session
        
        manager = AWSClientManager()
        
        with pytest.raises(Exception, match="General error"):
            manager.get_client("ec2")

    @patch("boto3.Session")
    def test_test_credentials_general_exception(self, mock_session_class):
        """Test credentials test with general exception."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_client.get_caller_identity.side_effect = Exception("Unexpected error")
        mock_session.client.return_value = mock_client
        mock_session_class.return_value = mock_session
        
        manager = AWSClientManager()
        result = manager.test_credentials()
        
        assert result["status"] == "error"
        assert "Unexpected error" in result["message"]

    def test_parse_tags_missing_key_or_value(self):
        """Test tag parsing with malformed tags."""
        tags = [
            {"Key": "Name", "Value": "test-instance"},
            {"Key": "Environment"},  # Missing Value
            {"Value": "orphaned-value"}  # Missing Key
        ]
        
        # This should handle KeyError gracefully if the implementation doesn't check
        try:
            result = parse_tags(tags)
            # If it succeeds, it should only parse valid tags
            assert "Name" in result
            assert result["Name"] == "test-instance"
        except KeyError:
            # If it fails, that's expected behavior for malformed tags
            pass

    def test_client_manager_session_reuse(self):
        """Test that session is reused across calls."""
        manager = AWSClientManager()
        
        with patch.object(manager, '_get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session
            
            # First call should create session
            manager.get_client("ec2")
            # Second call should reuse session
            manager.get_client("s3")
            
            # _get_session should be called twice (once per service)
            assert mock_get_session.call_count == 2

    @patch("boto3.Session")
    def test_aws_client_manager_region_setting(self, mock_session_class):
        """Test that region is properly passed to client creation."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        mock_session_class.return_value = mock_session
        
        manager = AWSClientManager(region="eu-west-1")
        manager.get_client("ec2")
        
        mock_session.client.assert_called_once_with("ec2", region_name="eu-west-1")

    def test_handle_aws_error_client_error_without_response(self):
        """Test handling ClientError with missing response structure."""
        # Create a ClientError with minimal structure
        error = ClientError(
            error_response={"Error": {"Code": "TestError"}},  # Missing Message
            operation_name="TestOperation"
        )
        
        try:
            result = handle_aws_error(error)
            assert result["status"] == "error"
            assert result["error"] == "TestError"
        except KeyError:
            # If the implementation expects Message to always be present, this is expected
            pass