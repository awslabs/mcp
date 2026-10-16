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

import json
import os
import pytest
import threading
import time
from awslabs.redshift_mcp_server import clients
from awslabs.redshift_mcp_server.clients import RedshiftClientManager, client_manager
from awslabs.redshift_mcp_server.consts import CLIENT_RETRIES
from botocore.awsrequest import AWSResponse
from botocore.config import Config
from botocore.exceptions import ClientError, CredentialRetrievalError


@pytest.fixture(autouse=True)
def _no_ambient_aws_environment(monkeypatch, tmp_path):
    """Clear every AWS_* variable, since each client reads the environment when it is built.

    And point botocore at files that do not exist, since building a client reads them too, so the
    developer's own ~/.aws never reaches a test.
    """
    for name in [name for name in os.environ if name.startswith('AWS_')]:
        monkeypatch.delenv(name)
    monkeypatch.setenv('AWS_CONFIG_FILE', str(tmp_path / 'absent-config'))
    monkeypatch.setenv('AWS_SHARED_CREDENTIALS_FILE', str(tmp_path / 'absent-credentials'))


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
        mock_boto3_session.assert_called_once_with(
            botocore_session=mocker.ANY, profile_name=None, region_name=None
        )
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
        mock_boto3_session.assert_called_once_with(
            botocore_session=mocker.ANY, profile_name=None, region_name=None
        )
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
        mock_boto3_session.assert_called_once_with(
            botocore_session=mocker.ANY, profile_name=None, region_name=None
        )
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


class _Body:
    """The raw body botocore reads an answer from."""

    def __init__(self, payload: dict):
        self._content = json.dumps(payload).encode()

    def stream(self, **kwargs):
        yield self._content


class TestKeysRewrittenInTheSharedCredentialsFile:
    """Checked on real clients, which sign every call, answered locally so nothing is sent.

    Botocore read these keys once and signed with them for the life of the process, so keys
    rewritten by `aws configure` or any other tool went unseen until a restart, and every call
    meanwhile failed with ExpiredToken.
    """

    @pytest.fixture(autouse=True)
    def _hermetic_files(self, tmp_path, monkeypatch):
        """A config and credentials file of the test's own, and instance metadata off."""
        self.credentials = tmp_path / 'credentials'
        self.config = tmp_path / 'config'
        self.config.write_text('[default]\nregion = eu-west-1\n')
        self._write_keys('first-key')
        monkeypatch.setenv('AWS_CONFIG_FILE', str(self.config))
        monkeypatch.setenv('AWS_SHARED_CREDENTIALS_FILE', str(self.credentials))
        monkeypatch.setenv('AWS_EC2_METADATA_DISABLED', 'true')

    def _write_keys(self, access_key, profile='default'):
        self.credentials.write_text(
            f'[{profile}]\naws_access_key_id = {access_key}\naws_secret_access_key = secret\n'
        )

    def _client(self, answer=None):
        """A Data API client, retrying as the server's does, whose calls record their key.

        Args:
            answer: The error code to answer every call with; a success when None.
        """
        client = RedshiftClientManager(Config(retries=CLIENT_RETRIES)).redshift_data_client()
        self.signed_with: list[str] = []

        def send(request, **kwargs):
            authorization = request.headers['Authorization'].decode()
            self.signed_with.append(authorization.split('Credential=')[1].split('/')[0])
            if answer is None:
                return AWSResponse(request.url, 200, {}, _Body({}))
            return AWSResponse(request.url, 400, {}, _Body({'__type': answer, 'message': answer}))

        client.meta.events.register('before-send', send)
        return client

    def test_the_same_client_signs_with_the_new_keys_once_the_ttl_passes(self, monkeypatch):
        """Read again under botocore's refresh lock, so the client is never rebuilt."""
        monkeypatch.setattr(clients, 'CREDENTIAL_REFRESH_TTL', 0.2)
        client = self._client()
        client.describe_statement(Id='statement-id')

        self._write_keys('second-key')
        time.sleep(0.3)
        client.describe_statement(Id='statement-id')

        assert self.signed_with == ['first-key', 'second-key']

    def test_the_file_is_not_read_again_within_the_ttl(self):
        """Read once a TTL, not once a call."""
        client = self._client()
        client.describe_statement(Id='statement-id')

        self._write_keys('second-key')
        client.describe_statement(Id='statement-id')

        assert self.signed_with == ['first-key', 'first-key']

    def test_keys_gone_from_the_file_fail_the_call_unsent_until_they_return(self, monkeypatch):
        """Signing with keys the file no longer holds would hide that the operator removed them."""
        monkeypatch.setattr(clients, 'CREDENTIAL_REFRESH_TTL', 0.2)
        client = self._client()
        client.describe_statement(Id='statement-id')

        self.credentials.write_text('[default]\n')
        time.sleep(0.3)
        with pytest.raises(CredentialRetrievalError, match='no longer in the shared credentials'):
            client.describe_statement(Id='statement-id')
        assert self.signed_with == ['first-key']

        self._write_keys('second-key')
        client.describe_statement(Id='statement-id')

        assert self.signed_with == ['first-key', 'second-key']

    def test_a_named_profile_is_read_again_too(self, monkeypatch):
        """The profile read again is the one the session was built for."""
        monkeypatch.setattr(clients, 'CREDENTIAL_REFRESH_TTL', 0.2)
        monkeypatch.setenv('AWS_PROFILE', 'named')
        self.config.write_text('[profile named]\nregion = eu-north-1\n')
        self._write_keys('first-key', profile='named')
        client = self._client()
        client.describe_statement(Id='statement-id')

        self._write_keys('second-key', profile='named')
        time.sleep(0.3)
        client.describe_statement(Id='statement-id')

        assert self.signed_with == ['first-key', 'second-key']

    def test_keys_in_the_environment_still_come_first(self, monkeypatch):
        """With no profile named, botocore's order stands, and the file is never consulted."""
        monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'env-key')
        monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'env-secret')
        client = self._client()
        client.describe_statement(Id='statement-id')

        assert self.signed_with == ['env-key']
        assert client._request_signer._credentials.method == 'env'

    def test_a_profile_without_keys_in_the_file_is_left_to_the_rest_of_the_chain(self):
        """Keys in the config file are found as botocore found them."""
        self.credentials.write_text('[default]\n')
        self.config.write_text(
            '[default]\nregion = eu-west-1\n'
            'aws_access_key_id = config-key\naws_secret_access_key = config-secret\n'
        )
        client = self._client()
        client.describe_statement(Id='statement-id')

        assert self.signed_with == ['config-key']
        assert client._request_signer._credentials.method == 'config-file'

    def test_an_expired_token_is_sent_once_and_never_again(self):
        """Botocore does not retry ExpiredToken, and nothing here does either.

        Which is why the keys have to be read again before the call, and why a submit is never
        sent twice: the first answer is the one the caller gets.
        """
        client = self._client(answer='ExpiredTokenException')

        with pytest.raises(ClientError, match='ExpiredTokenException'):
            client.batch_execute_statement(
                Sqls=['SELECT 1'], Database='dev', ClusterIdentifier='cluster'
            )

        assert self.signed_with == ['first-key']
