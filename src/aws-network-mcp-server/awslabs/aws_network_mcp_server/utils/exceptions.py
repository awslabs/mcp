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

"""Centralized error handling utilities for standardized error messages."""


class NetworkResourceError(Exception):
    """Base exception for AWS network resource access errors.
    
    Provides standardized error message format:
    "{resource_type} with id {resource_id} could not be accessed. Error: {error_msg}"
    
    This ensures consistent error messages across all tools and prevents
    credential leakage in error responses.
    """
    
    def __init__(self, resource_type: str, resource_id: str, error_msg: str):
        """Initialize with resource details and error message.
        
        Args:
            resource_type: Type of AWS resource (VPC, Transit Gateway, etc.)
            resource_id: Resource identifier (e.g., vpc-12345678)
            error_msg: Error message from AWS or validation failure
        """
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.error_msg = error_msg
        super().__init__(
            f'{resource_type} with id {resource_id} could not be accessed. '
            f'Error: {error_msg}'
        )


class ResourceNotFoundError(NetworkResourceError):
    """Specific exception for resources that don't exist."""
    
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            resource_type,
            resource_id,
            f'{resource_type} with id {resource_id} could not be found.'
        )


class ValidationError(Exception):
    """Exception for invalid input parameters."""
