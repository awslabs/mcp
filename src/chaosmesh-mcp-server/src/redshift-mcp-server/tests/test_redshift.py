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

"""Tests for the redshift module."""

import pytest
from awslabs.redshift_mcp_server.redshift import (
    RedshiftClientManager,
    protect_sql,
    quote_literal_string,
)
from botocore.config import Config


class TestRedshiftClientManagerRedshiftClient:
    """Tests for RedshiftClientManager redshift_client() method."""

    def test_redshift_client_creation_default_credentials(self, mocker):
        """Test Redshift client creation with default credentials."""
        mock_client = mocker.Mock()
        mock_boto3_client = mocker.patch('boto3.client', return_value=mock_client)

        config = Config()
        manager = RedshiftClientManager(config, 'us-east-1')
        client = manager.redshift_client()

        assert client == mock_client

        # Verify boto3.client was called with correct parameters
        mock_boto3_client.assert_called_once_with(
            'redshift', config=config, region_name='us-east-1'
        )

    def test_redshift_client_creation_with_profile(self, mocker):
        """Test Redshift client creation with AWS profile."""
        mock_session = mocker.Mock()
        mock_client = mocker.Mock()
        mock_session.client.return_value = mock_client
        mock_session_class = mocker.patch('boto3.Session', return_value=mock_session)

        config = Config()
        manager = RedshiftClientManager(config, 'us-west-2', 'test-profile')
        client = manager.redshift_client()

        assert client == mock_client

        # Verify session was created with profile and client was created
        mock_session_class.assert_called_once_with(profile_name='test-profile')
        mock_session.client.assert_called_once_with('redshift', config=config)

    def test_redshift_client_creation_error_default_credentials(self, mocker):
        """Test error handling when client creation fails with default credentials."""
        mocker.patch('boto3.client', side_effect=Exception('Credentials error'))

        config = Config()
        manager = RedshiftClientManager(config, 'us-east-1')

        with pytest.raises(Exception, match='Credentials error'):
            manager.redshift_client()

    def test_redshift_client_creation_error_with_profile(self, mocker):
        """Test error handling when session creation fails with profile."""
        mocker.patch('boto3.Session', side_effect=Exception('Profile not found'))

        config = Config()
        manager = RedshiftClientManager(config, 'us-east-1', 'non-existent-profile')

        with pytest.raises(Exception, match='Profile not found'):
            manager.redshift_client()


class TestRedshiftClientManagerServerlessClient:
    """Tests for RedshiftClientManager redshift_serverless_client() method."""

    def test_redshift_serverless_client_creation_default_credentials(self, mocker):
        """Test Redshift Serverless client creation with default credentials."""
        mock_client = mocker.Mock()
        mock_boto3_client = mocker.patch('boto3.client', return_value=mock_client)

        config = Config()
        manager = RedshiftClientManager(config, 'us-east-1')
        client = manager.redshift_serverless_client()

        assert client == mock_client

        # Verify boto3.client was called with correct parameters
        mock_boto3_client.assert_called_once_with(
            'redshift-serverless', config=config, region_name='us-east-1'
        )

    def test_redshift_serverless_client_creation_with_profile(self, mocker):
        """Test Redshift Serverless client creation with AWS profile."""
        mock_session = mocker.Mock()
        mock_client = mocker.Mock()
        mock_session.client.return_value = mock_client
        mock_session_class = mocker.patch('boto3.Session', return_value=mock_session)

        config = Config()
        manager = RedshiftClientManager(config, 'us-west-2', 'test-profile')
        client = manager.redshift_serverless_client()

        assert client == mock_client

        # Verify session was created with profile and client was created
        mock_session_class.assert_called_once_with(profile_name='test-profile')
        mock_session.client.assert_called_once_with('redshift-serverless', config=config)

    def test_redshift_serverless_client_creation_error_default_credentials(self, mocker):
        """Test error handling when serverless client creation fails with default credentials."""
        mocker.patch('boto3.client', side_effect=Exception('Credentials error'))

        config = Config()
        manager = RedshiftClientManager(config, 'us-east-1')

        with pytest.raises(Exception, match='Credentials error'):
            manager.redshift_serverless_client()

    def test_redshift_serverless_client_creation_error_with_profile(self, mocker):
        """Test error handling when session creation fails with profile."""
        mocker.patch('boto3.Session', side_effect=Exception('Profile not found'))

        config = Config()
        manager = RedshiftClientManager(config, 'us-east-1', 'non-existent-profile')

        with pytest.raises(Exception, match='Profile not found'):
            manager.redshift_serverless_client()


class TestRedshiftClientManagerDataClient:
    """Tests for RedshiftClientManager redshift_data_client() method."""

    def test_redshift_data_client_creation_default_credentials(self, mocker):
        """Test Redshift Data API client creation with default credentials."""
        mock_client = mocker.Mock()
        mock_boto3_client = mocker.patch('boto3.client', return_value=mock_client)

        config = Config()
        manager = RedshiftClientManager(config, 'us-east-1')
        client = manager.redshift_data_client()

        assert client == mock_client

        # Verify boto3.client was called with correct parameters
        mock_boto3_client.assert_called_once_with(
            'redshift-data', config=config, region_name='us-east-1'
        )

    def test_redshift_data_client_creation_with_profile(self, mocker):
        """Test Redshift Data API client creation with AWS profile."""
        mock_session = mocker.Mock()
        mock_client = mocker.Mock()
        mock_session.client.return_value = mock_client
        mock_session_class = mocker.patch('boto3.Session', return_value=mock_session)

        config = Config()
        manager = RedshiftClientManager(config, 'us-west-2', 'test-profile')
        client = manager.redshift_data_client()

        assert client == mock_client

        # Verify session was created with profile and client was created
        mock_session_class.assert_called_once_with(profile_name='test-profile')
        mock_session.client.assert_called_once_with('redshift-data', config=config)

    def test_redshift_data_client_creation_error_default_credentials(self, mocker):
        """Test error handling when data client creation fails with default credentials."""
        mocker.patch('boto3.client', side_effect=Exception('Credentials error'))

        config = Config()
        manager = RedshiftClientManager(config, 'us-east-1')

        with pytest.raises(Exception, match='Credentials error'):
            manager.redshift_data_client()

    def test_redshift_data_client_creation_error_with_profile(self, mocker):
        """Test error handling when session creation fails with profile."""
        mocker.patch('boto3.Session', side_effect=Exception('Profile not found'))

        config = Config()
        manager = RedshiftClientManager(config, 'us-east-1', 'non-existent-profile')

        with pytest.raises(Exception, match='Profile not found'):
            manager.redshift_data_client()


class TestQuoteLiteralString:
    """Tests for the quote_literal_string function."""

    def test_quote_literal_string_none_value(self):
        """Test quoting None value returns NULL."""
        result = quote_literal_string(None)
        assert result == 'NULL'

    def test_quote_literal_string_simple_string(self):
        """Test quoting a simple string."""
        result = quote_literal_string('hello')
        assert result == "'hello'"

    def test_quote_literal_string_empty_string(self):
        """Test quoting an empty string."""
        result = quote_literal_string('')
        assert result == "''"

    def test_quote_literal_string_with_single_quote(self):
        """Test quoting a string containing single quotes."""
        result = quote_literal_string("it's")
        assert result == "'it\\'s'"

    def test_quote_literal_string_with_double_quote(self):
        """Test quoting a string containing double quotes."""
        result = quote_literal_string('say "hello"')
        assert result == '\'say "hello"\''

    def test_quote_literal_string_numeric_string(self):
        """Test quoting a numeric string."""
        result = quote_literal_string('123')
        assert result == "'123'"

    def test_quote_literal_string_with_newline(self):
        """Test quoting a string with newline characters."""
        result = quote_literal_string('line1\nline2')
        assert result == "'line1\\nline2'"

    def test_quote_literal_string_with_special_characters(self):
        """Test quoting a string with various special characters."""
        result = quote_literal_string('test\t\r\n\\')
        assert result == "'test\\t\\r\\n\\\\'"


class TestProtectSQL:
    """Tests for the protect_sql function."""

    def test_protect_sql_allow_read_write(self):
        """Test protecting with read-write allowed."""
        result = protect_sql(sql='DROP TABLE public.test', allow_read_write=True)
        assert result == ['BEGIN READ WRITE;', 'DROP TABLE public.test', 'END;']

    def test_protect_sql_read_only(self):
        """Test protecting with read-only mode."""
        result = protect_sql(sql='SELECT * FROM test', allow_read_write=False)
        assert result == ['BEGIN READ ONLY;', 'SELECT * FROM test', 'END;']

    def test_protect_sql_read_only_transaction_breaker_error(self):
        """Test protecting with transaction breaker error."""
        for sql in (
            'END; SELECT 1',
            '  COMMIT\t\r\n; SELECT 1',
            ';;;abort -- slc \n; SELECT 1',
            'ABORT work; SELECT 1',
            '/* mlc */ COMMIT work;;   ; SELECT 1',
            'commit   TRANSACTION/* mlc /* /* mlc */ mlc */ */; SELECT 1',
            'rollback  ; -- slc \n SELECT 1',
            'ROLLBACK TRANSACTION;/* mlc /* /* mlc */ mlc */ */SELECT 1',
            ';; \t\r\n; rollback -- slc\n  /* mlc -- mlc \n */  work;-- slc \n SELECT 1',
        ):
            with pytest.raises(
                Exception,
                match='SQL contains suspicious pattern, execution rejected',
            ):
                protect_sql(sql=sql, allow_read_write=False)
