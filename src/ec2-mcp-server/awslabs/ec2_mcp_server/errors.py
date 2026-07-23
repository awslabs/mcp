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
"""
Error handling for EC2 MCP Server.
"""

from typing import Any, Union

from botocore.exceptions import ClientError
from loguru import logger


class Ec2McpError(Exception):
    """Base exception for EC2 MCP Server errors."""
    pass


class Ec2ClientError(Ec2McpError):
    """Client-side errors from AWS EC2 API."""
    pass


class Ec2PermissionError(Ec2McpError):
    """Permission-related errors."""
    pass


class Ec2ResourceNotFoundError(Ec2McpError):
    """Resource not found errors."""
    pass


class Ec2ValidationError(Ec2McpError):
    """Input validation errors."""
    pass


class Ec2LimitExceededError(Ec2McpError):
    """AWS service limit exceeded errors."""
    pass


def handle_ec2_error(error: Exception) -> Ec2McpError:
    """
    Handle EC2-specific errors and return standardized responses.
    
    Args:
        error: The original exception
        
    Returns:
        Standardized EC2 MCP error
    """
    if isinstance(error, ClientError):
        error_code = error.response.get('Error', {}).get('Code', 'Unknown')
        error_message = error.response.get('Error', {}).get('Message', str(error))
        
        logger.error(f"AWS ClientError: {error_code} - {error_message}")
        
        # Map AWS error codes to our custom exceptions
        if error_code in ['UnauthorizedOperation', 'AccessDenied', 'Forbidden']:
            return Ec2PermissionError(f"Permission denied: {error_message}")
        
        elif error_code in [
            'InvalidInstanceID.NotFound',
            'InvalidGroupId.NotFound', 
            'InvalidKeyPair.NotFound',
            'InvalidVolumeID.NotFound',
            'InvalidSnapshotID.NotFound',
            'InvalidAMIID.NotFound'
        ]:
            return Ec2ResourceNotFoundError(f"Resource not found: {error_message}")
        
        elif error_code in [
            'InvalidParameterValue',
            'InvalidParameter',
            'MissingParameter',
            'ValidationError'
        ]:
            return Ec2ValidationError(f"Invalid input: {error_message}")
        
        elif error_code in [
            'InstanceLimitExceeded',
            'VolumeIOPSLimitExceeded',
            'RequestLimitExceeded'
        ]:
            return Ec2LimitExceededError(f"AWS service limit exceeded: {error_message}")
        
        else:
            return Ec2ClientError(f"AWS API error ({error_code}): {error_message}")
    
    elif isinstance(error, Ec2McpError):
        # Already one of our custom errors
        return error
    
    else:
        # Generic error
        logger.error(f"Unexpected error: {type(error).__name__}: {str(error)}")
        return Ec2McpError(f"Unexpected error: {str(error)}")


def safe_execute(func: callable, *args, **kwargs) -> Any:
    """
    Safely execute a function and handle EC2 errors.
    
    Args:
        func: Function to execute
        *args: Function positional arguments
        **kwargs: Function keyword arguments
        
    Returns:
        Function result
        
    Raises:
        Ec2McpError: Standardized error on failure
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        raise handle_ec2_error(e)