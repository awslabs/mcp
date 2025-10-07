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

"""Tests for dms_exceptions module."""

import pytest
from awslabs.aws_dms_mcp_server.exceptions.dms_exceptions import (
    AWS_ERROR_MAP,
    DMSAccessDeniedException,
    DMSConnectionTestException,
    DMSInvalidParameterException,
    DMSMCPException,
    DMSReadOnlyModeException,
    DMSResourceInUseException,
    DMSResourceNotFoundException,
    DMSValidationException,
)
from datetime import datetime


class TestDMSMCPException:
    """Test base DMSMCPException class."""

    def test_basic_exception(self):
        """Test creating basic exception."""
        exc = DMSMCPException('Test error')
        assert exc.message == 'Test error'
        assert exc.details == {}
        assert exc.suggested_action is None
        assert isinstance(exc.timestamp, datetime)
        assert str(exc) == 'Test error'

    def test_exception_with_details(self):
        """Test exception with details."""
        details = {'resource_id': '123', 'status': 'failed'}
        exc = DMSMCPException('Error with details', details=details)
        assert exc.message == 'Error with details'
        assert exc.details == details

    def test_exception_with_suggested_action(self):
        """Test exception with suggested action."""
        exc = DMSMCPException(
            'Configuration error', suggested_action='Check your configuration file'
        )
        assert exc.message == 'Configuration error'
        assert exc.suggested_action == 'Check your configuration file'

    def test_to_dict_basic(self):
        """Test to_dict method with basic exception."""
        exc = DMSMCPException('Test error')
        error_dict = exc.to_dict()

        assert error_dict['error'] is True
        assert error_dict['error_type'] == 'DMSMCPException'
        assert error_dict['message'] == 'Test error'
        assert 'timestamp' in error_dict
        assert error_dict['timestamp'].endswith('Z')

    def test_to_dict_with_details(self):
        """Test to_dict method with details."""
        details = {'key': 'value'}
        exc = DMSMCPException('Test error', details=details)
        error_dict = exc.to_dict()

        assert error_dict['details'] == details

    def test_to_dict_with_suggested_action(self):
        """Test to_dict method with suggested action."""
        exc = DMSMCPException('Test error', suggested_action='Do this')
        error_dict = exc.to_dict()

        assert 'details' in error_dict
        assert error_dict['details']['suggested_action'] == 'Do this'

    def test_to_dict_with_both_details_and_action(self):
        """Test to_dict with both details and suggested action."""
        details = {'resource': 'test'}
        exc = DMSMCPException('Test error', details=details, suggested_action='Fix it')
        error_dict = exc.to_dict()

        assert error_dict['details']['resource'] == 'test'
        assert error_dict['details']['suggested_action'] == 'Fix it'


class TestSpecificExceptions:
    """Test specific exception classes."""

    def test_resource_not_found_exception(self):
        """Test DMSResourceNotFoundException."""
        exc = DMSResourceNotFoundException('Resource not found')
        assert isinstance(exc, DMSMCPException)
        assert exc.message == 'Resource not found'
        error_dict = exc.to_dict()
        assert error_dict['error_type'] == 'DMSResourceNotFoundException'

    def test_invalid_parameter_exception(self):
        """Test DMSInvalidParameterException."""
        exc = DMSInvalidParameterException('Invalid parameter')
        assert isinstance(exc, DMSMCPException)
        assert exc.message == 'Invalid parameter'
        error_dict = exc.to_dict()
        assert error_dict['error_type'] == 'DMSInvalidParameterException'

    def test_access_denied_exception(self):
        """Test DMSAccessDeniedException."""
        exc = DMSAccessDeniedException('Access denied')
        assert isinstance(exc, DMSMCPException)
        assert exc.message == 'Access denied'
        error_dict = exc.to_dict()
        assert error_dict['error_type'] == 'DMSAccessDeniedException'

    def test_resource_in_use_exception(self):
        """Test DMSResourceInUseException."""
        exc = DMSResourceInUseException('Resource in use')
        assert isinstance(exc, DMSMCPException)
        assert exc.message == 'Resource in use'
        error_dict = exc.to_dict()
        assert error_dict['error_type'] == 'DMSResourceInUseException'

    def test_connection_test_exception(self):
        """Test DMSConnectionTestException."""
        exc = DMSConnectionTestException('Connection test failed')
        assert isinstance(exc, DMSMCPException)
        assert exc.message == 'Connection test failed'
        error_dict = exc.to_dict()
        assert error_dict['error_type'] == 'DMSConnectionTestException'

    def test_validation_exception(self):
        """Test DMSValidationException."""
        exc = DMSValidationException('Validation failed')
        assert isinstance(exc, DMSMCPException)
        assert exc.message == 'Validation failed'
        error_dict = exc.to_dict()
        assert error_dict['error_type'] == 'DMSValidationException'


class TestReadOnlyModeException:
    """Test DMSReadOnlyModeException."""

    def test_read_only_mode_exception(self):
        """Test read-only mode exception creation."""
        exc = DMSReadOnlyModeException('create_replication_instance')
        assert isinstance(exc, DMSMCPException)
        assert "Operation 'create_replication_instance' not allowed" in exc.message
        assert exc.suggested_action == 'Disable read-only mode by setting DMS_READ_ONLY_MODE=false'

    def test_read_only_mode_exception_different_operation(self):
        """Test read-only mode exception with different operation."""
        exc = DMSReadOnlyModeException('delete_endpoint')
        assert "Operation 'delete_endpoint' not allowed" in exc.message

    def test_read_only_mode_exception_to_dict(self):
        """Test read-only mode exception to_dict."""
        exc = DMSReadOnlyModeException('test_operation')
        error_dict = exc.to_dict()

        assert error_dict['error'] is True
        assert error_dict['error_type'] == 'DMSReadOnlyModeException'
        assert 'test_operation' in error_dict['message']
        assert 'details' in error_dict
        assert 'suggested_action' in error_dict['details']


class TestAWSErrorMap:
    """Test AWS error code mapping."""

    def test_error_map_exists(self):
        """Test that AWS_ERROR_MAP is defined."""
        assert AWS_ERROR_MAP is not None
        assert isinstance(AWS_ERROR_MAP, dict)

    def test_error_map_mappings(self):
        """Test specific error code mappings."""
        assert AWS_ERROR_MAP['ResourceNotFoundFault'] == DMSResourceNotFoundException
        assert AWS_ERROR_MAP['InvalidParameterValueException'] == DMSInvalidParameterException
        assert (
            AWS_ERROR_MAP['InvalidParameterCombinationException'] == DMSInvalidParameterException
        )
        assert AWS_ERROR_MAP['AccessDeniedFault'] == DMSAccessDeniedException
        assert AWS_ERROR_MAP['AccessDeniedException'] == DMSAccessDeniedException
        assert AWS_ERROR_MAP['ResourceAlreadyExistsFault'] == DMSResourceInUseException
        assert AWS_ERROR_MAP['InvalidResourceStateFault'] == DMSResourceInUseException
        assert AWS_ERROR_MAP['TestConnectionFault'] == DMSConnectionTestException

    def test_error_map_coverage(self):
        """Test that error map has expected entries."""
        expected_codes = [
            'ResourceNotFoundFault',
            'InvalidParameterValueException',
            'InvalidParameterCombinationException',
            'AccessDeniedFault',
            'AccessDeniedException',
            'ResourceAlreadyExistsFault',
            'InvalidResourceStateFault',
            'TestConnectionFault',
        ]
        for code in expected_codes:
            assert code in AWS_ERROR_MAP


class TestExceptionInheritance:
    """Test exception inheritance hierarchy."""

    def test_all_exceptions_inherit_from_base(self):
        """Test that all custom exceptions inherit from DMSMCPException."""
        exceptions = [
            DMSResourceNotFoundException,
            DMSInvalidParameterException,
            DMSAccessDeniedException,
            DMSResourceInUseException,
            DMSConnectionTestException,
            DMSReadOnlyModeException,
            DMSValidationException,
        ]

        for exc_class in exceptions:
            exc = exc_class('test')
            assert isinstance(exc, DMSMCPException)
            assert isinstance(exc, Exception)

    def test_exception_can_be_caught_as_base(self):
        """Test that specific exceptions can be caught as base exception."""
        try:
            raise DMSResourceNotFoundException('Not found')
        except DMSMCPException as e:
            assert e.message == 'Not found'
        except Exception:
            pytest.fail('Should have been caught as DMSMCPException')

    def test_exception_can_be_caught_specifically(self):
        """Test that specific exceptions can be caught by their type."""
        try:
            raise DMSAccessDeniedException('Access denied')
        except DMSAccessDeniedException as e:
            assert e.message == 'Access denied'
        except Exception:
            pytest.fail('Should have been caught as DMSAccessDeniedException')
