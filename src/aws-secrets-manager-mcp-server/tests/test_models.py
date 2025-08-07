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

"""Tests for Pydantic models."""

import json
import pytest
from pydantic import ValidationError

from awslabs.aws_secrets_manager_mcp_server.models import (
    CreateSecretRequest,
    RandomPasswordConfig,
    SecretValue,
    Tag,
    UpdateSecretRequest,
)


class TestTag:
    """Test Tag model validation."""
    
    def test_valid_tag(self):
        """Test valid tag creation."""
        tag = Tag(key='Environment', value='production')
        assert tag.key == 'Environment'
        assert tag.value == 'production'
    
    def test_invalid_tag_key(self):
        """Test invalid tag key validation."""
        with pytest.raises(ValidationError):
            Tag(key='', value='production')  # Empty key
        
        with pytest.raises(ValidationError):
            Tag(key='invalid@#$%', value='production')  # Invalid characters


class TestSecretValue:
    """Test SecretValue model validation."""
    
    def test_valid_secret_string(self):
        """Test valid secret string."""
        secret = SecretValue(secret_string='my-secret-value')
        assert secret.secret_string == 'my-secret-value'
        assert secret.secret_binary is None
    
    def test_valid_secret_binary(self):
        """Test valid secret binary."""
        secret = SecretValue(secret_binary=b'binary-data')
        assert secret.secret_binary == b'binary-data'
        assert secret.secret_string is None
    
    def test_both_values_provided(self):
        """Test validation error when both values are provided."""
        with pytest.raises(ValidationError):
            SecretValue(secret_string='string', secret_binary=b'binary')
    
    def test_no_values_provided(self):
        """Test validation error when no values are provided."""
        with pytest.raises(ValidationError):
            SecretValue()
    
    def test_secret_size_validation(self):
        """Test secret size validation."""
        # Create a large secret that exceeds the limit
        large_secret = 'x' * 70000  # Exceeds 64KB limit
        
        with pytest.raises(ValidationError):
            SecretValue(secret_string=large_secret)


class TestCreateSecretRequest:
    """Test CreateSecretRequest model validation."""
    
    def test_valid_request_string_value(self):
        """Test valid request with string value."""
        request = CreateSecretRequest(
            name='test-secret',
            secret_value='my-secret-value'
        )
        assert request.name == 'test-secret'
        assert request.secret_value == 'my-secret-value'
    
    def test_valid_request_dict_value(self):
        """Test valid request with dictionary value."""
        secret_data = {'username': 'admin', 'password': 'secret123'}
        request = CreateSecretRequest(
            name='test-secret',
            secret_value=secret_data
        )
        assert request.name == 'test-secret'
        assert request.secret_value == secret_data
    
    def test_invalid_secret_name(self):
        """Test invalid secret name validation."""
        with pytest.raises(ValidationError):
            CreateSecretRequest(
                name='invalid name with spaces',  # Spaces not allowed
                secret_value='value'
            )
    
    def test_secret_name_length(self):
        """Test secret name length validation."""
        # Test maximum length
        long_name = 'a' * 513  # Exceeds 512 character limit
        with pytest.raises(ValidationError):
            CreateSecretRequest(
                name=long_name,
                secret_value='value'
            )
    
    def test_description_length(self):
        """Test description length validation."""
        long_description = 'a' * 2049  # Exceeds 2048 character limit
        with pytest.raises(ValidationError):
            CreateSecretRequest(
                name='test-secret',
                secret_value='value',
                description=long_description
            )
    
    def test_large_secret_value(self):
        """Test large secret value validation."""
        large_value = 'x' * 70000  # Exceeds 64KB limit
        with pytest.raises(ValidationError):
            CreateSecretRequest(
                name='test-secret',
                secret_value=large_value
            )
    
    def test_large_dict_secret_value(self):
        """Test large dictionary secret value validation."""
        large_dict = {'key': 'x' * 70000}  # JSON will exceed 64KB limit
        with pytest.raises(ValidationError):
            CreateSecretRequest(
                name='test-secret',
                secret_value=large_dict
            )


class TestUpdateSecretRequest:
    """Test UpdateSecretRequest model validation."""
    
    def test_valid_update_request(self):
        """Test valid update request."""
        request = UpdateSecretRequest(
            secret_id='test-secret',
            secret_value='new-value'
        )
        assert request.secret_id == 'test-secret'
        assert request.secret_value == 'new-value'
    
    def test_update_with_none_values(self):
        """Test update request with None values."""
        request = UpdateSecretRequest(
            secret_id='test-secret',
            secret_value=None,
            description=None
        )
        assert request.secret_id == 'test-secret'
        assert request.secret_value is None
        assert request.description is None


class TestRandomPasswordConfig:
    """Test RandomPasswordConfig model validation."""
    
    def test_valid_config(self):
        """Test valid password configuration."""
        config = RandomPasswordConfig(
            password_length=16,
            exclude_numbers=False,
            exclude_punctuation=True
        )
        assert config.password_length == 16
        assert config.exclude_numbers is False
        assert config.exclude_punctuation is True
    
    def test_password_length_validation(self):
        """Test password length validation."""
        # Test minimum length
        with pytest.raises(ValidationError):
            RandomPasswordConfig(password_length=3)  # Below minimum of 4
        
        # Test maximum length
        with pytest.raises(ValidationError):
            RandomPasswordConfig(password_length=5000)  # Above maximum of 4096
    
    def test_default_values(self):
        """Test default configuration values."""
        config = RandomPasswordConfig()
        assert config.password_length == 32
        assert config.exclude_numbers is False
        assert config.exclude_punctuation is False
        assert config.exclude_uppercase is False
        assert config.exclude_lowercase is False
        assert config.include_space is False
        assert config.require_each_included_type is True
