#!/usr/bin/env python3
"""
Unit tests for error handling module.
"""

import pytest
from botocore.exceptions import ClientError

from awslabs.ec2_mcp_server.errors import (
    Ec2McpError,
    Ec2ClientError,
    Ec2PermissionError,
    Ec2ResourceNotFoundError,
    Ec2ValidationError,
    Ec2LimitExceededError,
    handle_ec2_error,
    safe_execute
)


class TestErrorHandling:
    """Test suite for error handling functionality."""
    
    def test_handle_permission_error(self):
        """Test handling of permission-related errors."""
        client_error = ClientError(
            error_response={
                'Error': {
                    'Code': 'UnauthorizedOperation',
                    'Message': 'You are not authorized to perform this operation'
                }
            },
            operation_name='DescribeInstances'
        )
        
        result = handle_ec2_error(client_error)
        
        assert isinstance(result, Ec2PermissionError)
        assert "Permission denied" in str(result)
        assert "You are not authorized" in str(result)
    
    def test_handle_resource_not_found_error(self):
        """Test handling of resource not found errors."""
        client_error = ClientError(
            error_response={
                'Error': {
                    'Code': 'InvalidInstanceID.NotFound',
                    'Message': 'The instance ID i-123456 does not exist'
                }
            },
            operation_name='DescribeInstances'
        )
        
        result = handle_ec2_error(client_error)
        
        assert isinstance(result, Ec2ResourceNotFoundError)
        assert "Resource not found" in str(result)
        assert "does not exist" in str(result)
    
    def test_handle_validation_error(self):
        """Test handling of validation errors."""
        client_error = ClientError(
            error_response={
                'Error': {
                    'Code': 'InvalidParameterValue',
                    'Message': 'Invalid instance type: t2.invalid'
                }
            },
            operation_name='RunInstances'
        )
        
        result = handle_ec2_error(client_error)
        
        assert isinstance(result, Ec2ValidationError)
        assert "Invalid input" in str(result)
        assert "Invalid instance type" in str(result)
    
    def test_handle_limit_exceeded_error(self):
        """Test handling of limit exceeded errors."""
        client_error = ClientError(
            error_response={
                'Error': {
                    'Code': 'InstanceLimitExceeded',
                    'Message': 'You have exceeded your instance limit'
                }
            },
            operation_name='RunInstances'
        )
        
        result = handle_ec2_error(client_error)
        
        assert isinstance(result, Ec2LimitExceededError)
        assert "AWS service limit exceeded" in str(result)
        assert "exceeded your instance limit" in str(result)
    
    def test_handle_unknown_client_error(self):
        """Test handling of unknown AWS client errors."""
        client_error = ClientError(
            error_response={
                'Error': {
                    'Code': 'UnknownError',
                    'Message': 'Something went wrong'
                }
            },
            operation_name='SomeOperation'
        )
        
        result = handle_ec2_error(client_error)
        
        assert isinstance(result, Ec2ClientError)
        assert "AWS API error (UnknownError)" in str(result)
        assert "Something went wrong" in str(result)
    
    def test_handle_existing_ec2_error(self):
        """Test that existing EC2 MCP errors are passed through."""
        original_error = Ec2ValidationError("Original validation error")
        
        result = handle_ec2_error(original_error)
        
        assert result is original_error
        assert isinstance(result, Ec2ValidationError)
    
    def test_handle_generic_error(self):
        """Test handling of generic Python exceptions."""
        generic_error = ValueError("Invalid value provided")
        
        result = handle_ec2_error(generic_error)
        
        assert isinstance(result, Ec2McpError)
        assert "Unexpected error" in str(result)
        assert "Invalid value provided" in str(result)
    
    def test_safe_execute_success(self):
        """Test safe_execute with successful function."""
        def success_func(x, y):
            return x + y
        
        result = safe_execute(success_func, 2, 3)
        assert result == 5
    
    def test_safe_execute_with_client_error(self):
        """Test safe_execute with AWS client error."""
        def failing_func():
            raise ClientError(
                error_response={
                    'Error': {
                        'Code': 'InvalidInstanceID.NotFound',
                        'Message': 'Instance not found'
                    }
                },
                operation_name='DescribeInstances'
            )
        
        with pytest.raises(Ec2ResourceNotFoundError):
            safe_execute(failing_func)
    
    def test_safe_execute_with_generic_error(self):
        """Test safe_execute with generic error."""
        def failing_func():
            raise RuntimeError("Something bad happened")
        
        with pytest.raises(Ec2McpError) as exc_info:
            safe_execute(failing_func)
        
        assert "Unexpected error" in str(exc_info.value)
        assert "Something bad happened" in str(exc_info.value)


class TestSpecificErrorTypes:
    """Test specific error type behaviors."""
    
    def test_ec2_permission_error_inheritance(self):
        """Test that Ec2PermissionError inherits from Ec2McpError."""
        error = Ec2PermissionError("Permission denied")
        assert isinstance(error, Ec2McpError)
        assert isinstance(error, Exception)
    
    def test_ec2_resource_not_found_error_inheritance(self):
        """Test that Ec2ResourceNotFoundError inherits from Ec2McpError."""
        error = Ec2ResourceNotFoundError("Resource not found")
        assert isinstance(error, Ec2McpError)
        assert isinstance(error, Exception)
    
    def test_error_string_representation(self):
        """Test string representation of custom errors."""
        error = Ec2ValidationError("Invalid parameter value")
        assert str(error) == "Invalid parameter value"
    
    def test_multiple_error_codes_mapping(self):
        """Test that multiple error codes map to the same exception type."""
        access_denied = ClientError(
            error_response={'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            operation_name='Test'
        )
        
        forbidden = ClientError(
            error_response={'Error': {'Code': 'Forbidden', 'Message': 'Forbidden'}},
            operation_name='Test'
        )
        
        result1 = handle_ec2_error(access_denied)
        result2 = handle_ec2_error(forbidden)
        
        assert isinstance(result1, Ec2PermissionError)
        assert isinstance(result2, Ec2PermissionError)