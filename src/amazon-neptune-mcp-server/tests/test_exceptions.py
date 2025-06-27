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
"""Tests for the exceptions module."""

from awslabs.amazon_neptune_mcp_server.exceptions import NeptuneException


class TestNeptuneException:
    """Test class for the NeptuneException class."""

    def test_init_with_string(self):
        """Test initialization of NeptuneException with a string message.
        This test verifies that:
        1. The exception can be created with a string message
        2. The message attribute is set to the provided string
        3. The details attribute defaults to "unknown".
        """
        # Arrange & Act
        exception = NeptuneException('Test error message')

        # Assert
        assert exception.message == 'Test error message'
        assert exception.details == 'unknown'

    def test_init_with_dict_complete(self):
        """Test initialization of NeptuneException with a complete dictionary.
        This test verifies that:
        1. The exception can be created with a dictionary containing message and details
        2. The message attribute is set to the value from the dictionary
        3. The details attribute is set to the value from the dictionary.
        """
        # Arrange & Act
        exception_dict = {'message': 'Test error message', 'details': 'Test error details'}
        exception = NeptuneException(exception_dict)

        # Assert
        assert exception.message == 'Test error message'
        assert exception.details == 'Test error details'

    def test_init_with_dict_message_only(self):
        """Test initialization of NeptuneException with a dictionary containing only message.
        This test verifies that:
        1. The exception can be created with a dictionary containing only message
        2. The message attribute is set to the value from the dictionary
        3. The details attribute defaults to "unknown".
        """
        # Arrange & Act
        exception_dict = {'message': 'Test error message'}
        exception = NeptuneException(exception_dict)

        # Assert
        assert exception.message == 'Test error message'
        assert exception.details == 'unknown'

    def test_init_with_dict_details_only(self):
        """Test initialization of NeptuneException with a dictionary containing only details.
        This test verifies that:
        1. The exception can be created with a dictionary containing only details
        2. The message attribute defaults to "unknown"
        3. The details attribute is set to the value from the dictionary.
        """
        # Arrange & Act
        exception_dict = {'details': 'Test error details'}
        exception = NeptuneException(exception_dict)

        # Assert
        assert exception.message == 'unknown'
        assert exception.details == 'Test error details'

    def test_init_with_empty_dict(self):
        """Test initialization of NeptuneException with an empty dictionary.
        This test verifies that:
        1. The exception can be created with an empty dictionary
        2. The message attribute defaults to "unknown"
        3. The details attribute defaults to "unknown".
        """
        # Arrange & Act
        exception = NeptuneException({})

        # Assert
        assert exception.message == 'unknown'
        assert exception.details == 'unknown'

    def test_get_message(self):
        """Test the get_message method.
        This test verifies that:
        1. The get_message method returns the message attribute.
        """
        # Arrange
        exception = NeptuneException('Test error message')

        # Act
        message = exception.get_message()

        # Assert
        assert message == 'Test error message'

    def test_get_details(self):
        """Test the get_details method.
        This test verifies that:
        1. The get_details method returns the details attribute.
        """
        # Arrange
        exception_dict = {'message': 'Test error message', 'details': 'Test error details'}
        exception = NeptuneException(exception_dict)

        # Act
        details = exception.get_details()

        # Assert
        assert details == 'Test error details'

    def test_exception_inheritance(self):
        """Test that NeptuneException inherits from Exception.
        This test verifies that:
        1. NeptuneException is a subclass of Exception
        2. NeptuneException can be caught as an Exception.
        """
        # Arrange & Act
        exception = NeptuneException('Test error message')

        # Assert
        assert isinstance(exception, Exception)

        # Test that it can be caught as an Exception
        try:
            raise NeptuneException('Test error message')
            assert False, 'Exception was not raised'
        except Exception as e:
            assert isinstance(e, NeptuneException)
            assert e.message == 'Test error message'

    def test_exception_in_try_except(self):
        """Test that NeptuneException can be used in a try-except block.
        This test verifies that:
        1. NeptuneException can be raised and caught
        2. The message and details are preserved.
        """
        # Arrange
        exception_dict = {'message': 'Test error message', 'details': 'Test error details'}

        # Act & Assert
        try:
            raise NeptuneException(exception_dict)
            assert False, 'Exception was not raised'
        except NeptuneException as e:
            assert e.message == 'Test error message'
            assert e.details == 'Test error details'

    def test_complex_details(self):
        """Test that NeptuneException can handle complex details.
        This test verifies that:
        1. The details attribute can be a complex object (dict, list, etc.)
        2. The details are preserved as-is.
        """
        # Arrange
        complex_details = {
            'error_code': 500,
            'error_type': 'InternalServerError',
            'nested': {'field1': 'value1', 'field2': 123},
            'items': [1, 2, 3],
        }
        exception_dict = {'message': 'Test error message', 'details': complex_details}

        # Act
        exception = NeptuneException(exception_dict)

        # Assert
        assert exception.message == 'Test error message'
        assert exception.details == complex_details
        assert exception.details['error_code'] == 500
        assert exception.details['nested']['field1'] == 'value1'
        assert exception.details['items'] == [1, 2, 3]
