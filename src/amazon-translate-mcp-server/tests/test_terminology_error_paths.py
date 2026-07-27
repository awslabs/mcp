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

"""Additional tests for terminology manager error handling paths."""

import pytest
from awslabs.amazon_translate_mcp_server.models import (
    AuthenticationError,
    QuotaExceededError,
    RateLimitError,
    ServiceUnavailableError,
    TerminologyError,
    ValidationError,
)
from awslabs.amazon_translate_mcp_server.terminology_manager import TerminologyManager
from botocore.exceptions import BotoCoreError, ClientError
from unittest.mock import Mock


class TestTerminologyManagerCreateErrors:
    """Test error handling paths for create_terminology."""

    @pytest.fixture
    def mock_aws_client_manager(self):
        """Create a mock AWS client manager."""
        manager = Mock()
        manager.get_translate_client.return_value = Mock()
        return manager

    @pytest.fixture
    def terminology_manager(self, mock_aws_client_manager):
        """Create a TerminologyManager instance with mocked dependencies."""
        return TerminologyManager(mock_aws_client_manager)

    @pytest.fixture
    def sample_terminology_data(self):
        """Create sample terminology data."""
        from awslabs.amazon_translate_mcp_server.models import TerminologyData

        return TerminologyData(
            format='CSV',
            directionality='UNI',
            terminology_data=b'en,es\nhello,hola',
        )

    def test_create_terminology_conflict_exception(
        self, terminology_manager, mock_aws_client_manager, sample_terminology_data
    ):
        """Test create_terminology with ConflictException."""
        mock_client = Mock()
        mock_client.import_terminology.side_effect = ClientError(
            {'Error': {'Code': 'ConflictException', 'Message': 'Terminology already exists'}},
            'ImportTerminology',
        )
        mock_aws_client_manager.get_translate_client.return_value = mock_client

        with pytest.raises(TerminologyError) as exc_info:
            terminology_manager.create_terminology(
                name='test-terminology',
                description='Test terminology',
                terminology_data=sample_terminology_data,
            )
        assert 'already exists' in str(exc_info.value)

    def test_create_terminology_limit_exceeded(
        self, terminology_manager, mock_aws_client_manager, sample_terminology_data
    ):
        """Test create_terminology with LimitExceededException."""
        mock_client = Mock()
        mock_client.import_terminology.side_effect = ClientError(
            {'Error': {'Code': 'LimitExceededException', 'Message': 'Limit exceeded'}},
            'ImportTerminology',
        )
        mock_aws_client_manager.get_translate_client.return_value = mock_client

        with pytest.raises(QuotaExceededError) as exc_info:
            terminology_manager.create_terminology(
                name='test-terminology',
                description='Test terminology',
                terminology_data=sample_terminology_data,
            )
        assert 'limit exceeded' in str(exc_info.value).lower()

    def test_create_terminology_invalid_parameter(
        self, terminology_manager, mock_aws_client_manager, sample_terminology_data
    ):
        """Test create_terminology with InvalidParameterValueException."""
        mock_client = Mock()
        mock_client.import_terminology.side_effect = ClientError(
            {'Error': {'Code': 'InvalidParameterValueException', 'Message': 'Invalid parameter'}},
            'ImportTerminology',
        )
        mock_aws_client_manager.get_translate_client.return_value = mock_client

        with pytest.raises(ValidationError) as exc_info:
            terminology_manager.create_terminology(
                name='test-terminology',
                description='Test terminology',
                terminology_data=sample_terminology_data,
            )
        assert 'Invalid' in str(exc_info.value)

    def test_create_terminology_throttling(
        self, terminology_manager, mock_aws_client_manager, sample_terminology_data
    ):
        """Test create_terminology with ThrottlingException."""
        mock_client = Mock()
        mock_client.import_terminology.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'ImportTerminology',
        )
        mock_aws_client_manager.get_translate_client.return_value = mock_client

        with pytest.raises(RateLimitError) as exc_info:
            terminology_manager.create_terminology(
                name='test-terminology',
                description='Test terminology',
                terminology_data=sample_terminology_data,
            )
        assert 'Rate limit' in str(exc_info.value)

    def test_create_terminology_generic_client_error(
        self, terminology_manager, mock_aws_client_manager, sample_terminology_data
    ):
        """Test create_terminology with generic ClientError."""
        mock_client = Mock()
        mock_client.import_terminology.side_effect = ClientError(
            {'Error': {'Code': 'UnknownError', 'Message': 'Unknown error'}},
            'ImportTerminology',
        )
        mock_aws_client_manager.get_translate_client.return_value = mock_client

        with pytest.raises(TerminologyError) as exc_info:
            terminology_manager.create_terminology(
                name='test-terminology',
                description='Test terminology',
                terminology_data=sample_terminology_data,
            )
        assert 'Failed to create' in str(exc_info.value)

    def test_create_terminology_botocore_error(
        self, terminology_manager, mock_aws_client_manager, sample_terminology_data
    ):
        """Test create_terminology with BotoCoreError."""
        mock_client = Mock()
        mock_client.import_terminology.side_effect = BotoCoreError()
        mock_aws_client_manager.get_translate_client.return_value = mock_client

        with pytest.raises(ServiceUnavailableError):
            terminology_manager.create_terminology(
                name='test-terminology',
                description='Test terminology',
                terminology_data=sample_terminology_data,
            )

    def test_create_terminology_unexpected_error(
        self, terminology_manager, mock_aws_client_manager, sample_terminology_data
    ):
        """Test create_terminology with unexpected error."""
        mock_client = Mock()
        mock_client.import_terminology.side_effect = RuntimeError('Unexpected')
        mock_aws_client_manager.get_translate_client.return_value = mock_client

        with pytest.raises(TerminologyError) as exc_info:
            terminology_manager.create_terminology(
                name='test-terminology',
                description='Test terminology',
                terminology_data=sample_terminology_data,
            )
        assert 'Unexpected error' in str(exc_info.value)


class TestTerminologyManagerGetErrors:
    """Test error handling paths for get_terminology."""

    @pytest.fixture
    def mock_aws_client_manager(self):
        """Create a mock AWS client manager."""
        manager = Mock()
        manager.get_translate_client.return_value = Mock()
        return manager

    @pytest.fixture
    def terminology_manager(self, mock_aws_client_manager):
        """Create a TerminologyManager instance with mocked dependencies."""
        return TerminologyManager(mock_aws_client_manager)

    def test_get_terminology_access_denied(self, terminology_manager, mock_aws_client_manager):
        """Test get_terminology with AccessDeniedException."""
        mock_client = Mock()
        mock_client.get_terminology.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}},
            'GetTerminology',
        )
        mock_aws_client_manager.get_translate_client.return_value = mock_client

        with pytest.raises(AuthenticationError) as exc_info:
            terminology_manager.get_terminology('test-terminology')
        assert 'Access denied' in str(exc_info.value)

    def test_get_terminology_throttling(self, terminology_manager, mock_aws_client_manager):
        """Test get_terminology with ThrottlingException."""
        mock_client = Mock()
        mock_client.get_terminology.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'GetTerminology',
        )
        mock_aws_client_manager.get_translate_client.return_value = mock_client

        with pytest.raises(RateLimitError) as exc_info:
            terminology_manager.get_terminology('test-terminology')
        assert 'Rate limit' in str(exc_info.value)

    def test_get_terminology_generic_error(self, terminology_manager, mock_aws_client_manager):
        """Test get_terminology with generic ClientError."""
        mock_client = Mock()
        mock_client.get_terminology.side_effect = ClientError(
            {'Error': {'Code': 'UnknownError', 'Message': 'Unknown error'}},
            'GetTerminology',
        )
        mock_aws_client_manager.get_translate_client.return_value = mock_client

        with pytest.raises(TerminologyError) as exc_info:
            terminology_manager.get_terminology('test-terminology')
        assert 'Failed to get' in str(exc_info.value)

    def test_get_terminology_botocore_error(self, terminology_manager, mock_aws_client_manager):
        """Test get_terminology with BotoCoreError."""
        mock_client = Mock()
        mock_client.get_terminology.side_effect = BotoCoreError()
        mock_aws_client_manager.get_translate_client.return_value = mock_client

        with pytest.raises(ServiceUnavailableError):
            terminology_manager.get_terminology('test-terminology')

    def test_get_terminology_unexpected_error(self, terminology_manager, mock_aws_client_manager):
        """Test get_terminology with unexpected error."""
        mock_client = Mock()
        mock_client.get_terminology.side_effect = RuntimeError('Unexpected')
        mock_aws_client_manager.get_translate_client.return_value = mock_client

        with pytest.raises(TerminologyError) as exc_info:
            terminology_manager.get_terminology('test-terminology')
        assert 'Unexpected error' in str(exc_info.value)


class TestTerminologyManagerDeleteErrors:
    """Test error handling paths for delete_terminology."""

    @pytest.fixture
    def mock_aws_client_manager(self):
        """Create a mock AWS client manager."""
        manager = Mock()
        manager.get_translate_client.return_value = Mock()
        return manager

    @pytest.fixture
    def terminology_manager(self, mock_aws_client_manager):
        """Create a TerminologyManager instance with mocked dependencies."""
        return TerminologyManager(mock_aws_client_manager)

    def test_delete_terminology_access_denied(self, terminology_manager, mock_aws_client_manager):
        """Test delete_terminology with AccessDeniedException."""
        mock_client = Mock()
        mock_client.delete_terminology.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}},
            'DeleteTerminology',
        )
        mock_aws_client_manager.get_translate_client.return_value = mock_client

        with pytest.raises(AuthenticationError) as exc_info:
            terminology_manager.delete_terminology('test-terminology')
        assert 'Access denied' in str(exc_info.value)

    def test_delete_terminology_throttling(self, terminology_manager, mock_aws_client_manager):
        """Test delete_terminology with ThrottlingException."""
        mock_client = Mock()
        mock_client.delete_terminology.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'DeleteTerminology',
        )
        mock_aws_client_manager.get_translate_client.return_value = mock_client

        with pytest.raises(RateLimitError) as exc_info:
            terminology_manager.delete_terminology('test-terminology')
        assert 'Rate limit' in str(exc_info.value)

    def test_delete_terminology_generic_error(self, terminology_manager, mock_aws_client_manager):
        """Test delete_terminology with generic ClientError."""
        mock_client = Mock()
        mock_client.delete_terminology.side_effect = ClientError(
            {'Error': {'Code': 'UnknownError', 'Message': 'Unknown error'}},
            'DeleteTerminology',
        )
        mock_aws_client_manager.get_translate_client.return_value = mock_client

        with pytest.raises(TerminologyError) as exc_info:
            terminology_manager.delete_terminology('test-terminology')
        assert 'Failed to delete' in str(exc_info.value)

    def test_delete_terminology_botocore_error(self, terminology_manager, mock_aws_client_manager):
        """Test delete_terminology with BotoCoreError."""
        mock_client = Mock()
        mock_client.delete_terminology.side_effect = BotoCoreError()
        mock_aws_client_manager.get_translate_client.return_value = mock_client

        with pytest.raises(ServiceUnavailableError):
            terminology_manager.delete_terminology('test-terminology')

    def test_delete_terminology_unexpected_error(
        self, terminology_manager, mock_aws_client_manager
    ):
        """Test delete_terminology with unexpected error."""
        mock_client = Mock()
        mock_client.delete_terminology.side_effect = RuntimeError('Unexpected')
        mock_aws_client_manager.get_translate_client.return_value = mock_client

        with pytest.raises(TerminologyError) as exc_info:
            terminology_manager.delete_terminology('test-terminology')
        assert 'Unexpected error' in str(exc_info.value)
