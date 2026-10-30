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


"""Tests for the AWS clients."""

import os
import pytest
import threading
from awslabs.redshift_mcp_server.clients import RedshiftClientManager, client_manager
from botocore.config import Config


@pytest.fixture(autouse=True)
def _no_ambient_aws_environment(monkeypatch):
    """Clear every AWS_* variable, since each client reads the environment when it is built."""
    for name in [name for name in os.environ if name.startswith('AWS_')]:
        monkeypatch.delenv(name)


def test_two_clients_built_at_once_both_survive_the_scrub(monkeypatch, mocker):
    """Clients are built on worker threads, so two first uses can scrub at once.

    The delete is held at a barrier, so both threads have listed the empty variable before either
    removes it. Serialized, the second finds nothing to remove; unserialized, its delete raised
    KeyError out of client construction and the tool call failed with nothing to act on.
    """
    monkeypatch.setenv('AWS_PROFILE', '')
    mocker.patch('boto3.Session')

    # Serialized, the first delete waits out the timeout alone, so it is kept short.
    held = threading.Barrier(2, timeout=0.5)
    original = os._Environ.__delitem__

    def held_delete(self, key):
        try:
            held.wait()
        except threading.BrokenBarrierError:
            pass
        original(self, key)

    monkeypatch.setattr(os._Environ, '__delitem__', held_delete)

    manager = RedshiftClientManager(Config())
    start = threading.Barrier(2)
    errors: list[BaseException] = []

    def build():
        start.wait()
        try:
            manager._client('redshift-data')
        except Exception as e:  # noqa: BLE001 - collected for the assertion
            errors.append(e)

    threads = [threading.Thread(target=build) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(10)

    assert errors == []


class TestRedshiftClientManagerRedshiftClient:
    """Tests for RedshiftClientManager redshift_client() method."""

    def test_redshift_client_creation_default_credentials(self, mocker):
        """Test Redshift client creation with default credentials."""
        mock_client = mocker.Mock()
        mock_boto3_session = mocker.patch('boto3.Session')
        mock_boto3_session.return_value.client.return_value = mock_client

        config = Config()
        manager = RedshiftClientManager(config)
        client = manager.redshift_client()

        assert client == mock_client

        # Verify boto3.Session was called with correct parameters
        mock_boto3_session.assert_called_once_with(profile_name=None, region_name=None)
        mock_boto3_session.return_value.client.assert_called_once_with('redshift', config=config)

    def test_redshift_client_creation_error(self, mocker):
        """Test Redshift client creation error handling."""
        mock_boto3_session = mocker.patch('boto3.Session')
        mock_boto3_session.return_value.client.side_effect = Exception('AWS credentials error')

        config = Config()
        manager = RedshiftClientManager(config)

        with pytest.raises(Exception, match='AWS credentials error'):
            manager.redshift_client()

    def test_client_caching(self, mocker):
        """Test that clients are cached after first creation."""
        mock_client = mocker.Mock()
        mock_boto3_session = mocker.patch('boto3.Session')
        mock_boto3_session.return_value.client.return_value = mock_client

        config = Config()
        manager = RedshiftClientManager(config)

        # First call should create client
        client1 = manager.redshift_client()
        # Second call should return cached client
        client2 = manager.redshift_client()

        assert client1 == client2 == mock_client
        # Session should only be called once
        mock_boto3_session.assert_called_once()


class TestRedshiftClientManagerServerlessClient:
    """Tests for RedshiftClientManager redshift_serverless_client() method."""

    def test_redshift_serverless_client_creation_default_credentials(self, mocker):
        """Test Redshift Serverless client creation with default credentials."""
        mock_client = mocker.Mock()
        mock_boto3_session = mocker.patch('boto3.Session')
        mock_boto3_session.return_value.client.return_value = mock_client

        config = Config()
        manager = RedshiftClientManager(config)
        client = manager.redshift_serverless_client()

        assert client == mock_client

        # Verify boto3.Session was called with correct parameters
        mock_boto3_session.assert_called_once_with(profile_name=None, region_name=None)
        mock_boto3_session.return_value.client.assert_called_once_with(
            'redshift-serverless', config=config
        )

    def test_redshift_serverless_client_creation_error(self, mocker):
        """Test Redshift Serverless client creation error handling."""
        mock_boto3_session = mocker.patch('boto3.Session')
        mock_boto3_session.return_value.client.side_effect = Exception('Serverless client error')

        config = Config()
        manager = RedshiftClientManager(config)

        with pytest.raises(Exception, match='Serverless client error'):
            manager.redshift_serverless_client()

    def test_redshift_serverless_client_caching(self, mocker):
        """Test that redshift serverless client is cached after first creation."""
        mock_client = mocker.Mock()
        mock_boto3_session = mocker.patch('boto3.Session')
        mock_boto3_session.return_value.client.return_value = mock_client

        config = Config()
        manager = RedshiftClientManager(config)

        # First call should create client
        client1 = manager.redshift_serverless_client()
        # Second call should return cached client
        client2 = manager.redshift_serverless_client()

        assert client1 == client2 == mock_client
        # Session should only be called once
        mock_boto3_session.assert_called_once()


class TestRedshiftClientManagerDataClient:
    """Tests for RedshiftClientManager redshift_data_client() method."""

    def test_redshift_data_client_creation_default_credentials(self, mocker):
        """Test Redshift Data API client creation with default credentials."""
        mock_client = mocker.Mock()
        mock_boto3_session = mocker.patch('boto3.Session')
        mock_boto3_session.return_value.client.return_value = mock_client

        config = Config()
        manager = RedshiftClientManager(config)
        client = manager.redshift_data_client()

        assert client == mock_client

        # Verify boto3.Session was called with correct parameters
        mock_boto3_session.assert_called_once_with(profile_name=None, region_name=None)
        mock_boto3_session.return_value.client.assert_called_once_with(
            'redshift-data', config=config
        )

    def test_redshift_data_client_creation_error(self, mocker):
        """Test Redshift Data client creation error handling."""
        mock_boto3_session = mocker.patch('boto3.Session')
        mock_boto3_session.return_value.client.side_effect = Exception('Data client error')

        config = Config()
        manager = RedshiftClientManager(config)

        with pytest.raises(Exception, match='Data client error'):
            manager.redshift_data_client()

    def test_redshift_data_client_caching(self, mocker):
        """Test that redshift data client is cached after first creation."""
        mock_client = mocker.Mock()
        mock_boto3_session = mocker.patch('boto3.Session')
        mock_boto3_session.return_value.client.return_value = mock_client

        config = Config()
        manager = RedshiftClientManager(config)

        # First call should create client
        client1 = manager.redshift_data_client()
        # Second call should return cached client
        client2 = manager.redshift_data_client()

        assert client1 == client2 == mock_client
        # Session should only be called once
        mock_boto3_session.assert_called_once()


class TestTheServersClientsReadTheEnvironment:
    """Checked on the server's own manager, building real clients.

    Botocore reads most AWS_* variables itself, so only a real client shows what it made of
    them. Asserting on values handed to botocore passed while every client still failed: None
    passed for an empty variable left botocore to read the same empty value from the environment.
    """

    @pytest.fixture(autouse=True)
    def _hermetic_config(self, tmp_path, monkeypatch):
        """Point botocore at a config of the test's own, and build the server's client afresh."""
        config = tmp_path / 'config'
        config.write_text(
            '[default]\nregion = eu-west-1\n'
            '[profile named]\nregion = eu-north-1\n'
            '[profile other]\nregion = ap-south-1\n'
        )
        # Keys for every profile, and instance metadata off, so no build reaches the network: on
        # an EC2 host a client left without keys fetched the host's own role credentials.
        credentials = tmp_path / 'credentials'
        credentials.write_text(
            '[default]\naws_access_key_id = default-key\naws_secret_access_key = default-secret\n'
            '[named]\naws_access_key_id = named-key\naws_secret_access_key = named-secret\n'
            '[other]\naws_access_key_id = other-key\naws_secret_access_key = other-secret\n'
        )
        monkeypatch.setenv('AWS_CONFIG_FILE', str(config))
        monkeypatch.setenv('AWS_SHARED_CREDENTIALS_FILE', str(credentials))
        monkeypatch.setenv('AWS_EC2_METADATA_DISABLED', 'true')
        monkeypatch.setattr(client_manager, '_redshift_data_client', None)

    def test_aws_profile_takes_precedence_over_aws_default_profile(self, monkeypatch):
        """Botocore, left to find the profile itself, reads AWS_DEFAULT_PROFILE first.

        So a shell carrying both ran every tool in the other profile's account and region.
        """
        monkeypatch.setenv('AWS_PROFILE', 'named')
        monkeypatch.setenv('AWS_DEFAULT_PROFILE', 'other')

        assert client_manager.redshift_data_client().meta.region_name == 'eu-north-1'

    def test_aws_profile_takes_precedence_over_keys_in_the_environment(self, monkeypatch):
        """Only a profile passed in disables botocore's environment credentials.

        Left to botocore, keys exported in the shell - by aws-vault, awsume, a CI job - signed
        every call as a principal the operator never named.
        """
        monkeypatch.setenv('AWS_PROFILE', 'named')
        monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'env-key')
        monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'env-secret')

        client = client_manager.redshift_data_client()

        assert client._request_signer._credentials.access_key == 'named-key'

    @pytest.mark.parametrize(
        'name',
        [
            'AWS_PROFILE',
            'AWS_DEFAULT_PROFILE',
            'AWS_REGION',
            'AWS_DEFAULT_REGION',
            'AWS_CA_BUNDLE',
        ],
    )
    def test_an_empty_variable_reads_as_unset(self, monkeypatch, name):
        """Each of these, left empty, failed every client and with it every tool.

        A profile named `''` (`The config profile () could not be found`), the endpoint
        `https://redshift-data..amazonaws.com`, or an invalid CA bundle. An empty value is what an
        MCP config template leaves behind.
        """
        monkeypatch.setenv(name, '')

        assert client_manager.redshift_data_client().meta.region_name == 'eu-west-1'

    def test_aws_region_takes_precedence(self, monkeypatch):
        """Over AWS_DEFAULT_REGION and the profile, as the README documents.

        Botocore reads only AWS_DEFAULT_REGION, so left to it, AWS_REGION would be ignored.
        """
        monkeypatch.setenv('AWS_REGION', 'us-west-2')
        monkeypatch.setenv('AWS_DEFAULT_REGION', 'eu-central-1')

        assert client_manager.redshift_data_client().meta.region_name == 'us-west-2'

    def test_aws_default_region_takes_precedence_over_the_profile(self, monkeypatch):
        """The second of the three, which botocore applies itself."""
        monkeypatch.setenv('AWS_DEFAULT_REGION', 'eu-central-1')

        assert client_manager.redshift_data_client().meta.region_name == 'eu-central-1'
