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

"""Unit tests for the API Gateway deployment's injected configuration.

These tests are pure and offline: they exercise the deterministic, I/O-free functions
``apigateway_server_env`` and ``apigateway_config`` in ``integration/deploy/apigateway.py``
without touching AWS or the network. They live in ``integration/harness_tests/`` — separate
from the opt-in-gated ``integration/tests/`` suite and from the offline ``tests/`` suite — so
they are not gated by the Opt_In_Signal and run as part of the normal offline selection.

They assert the server-facing environment the harness injects into the loopback-bound server
for the API Gateway deployment, keyed by the server's *own* environment-variable-name
constants (from :mod:`awslabs.aws_healthomics_mcp_server.consts`) so the harness never invents
new server configuration: the server runs the ``streamable-http`` transport bound to the
loopback address ``127.0.0.1`` with multi-tenant mode and the ``jwt`` inbound mechanism
enabled, reading its per-tenant role mappings from the DynamoDB registry URI. They also assert
the inspectable API Gateway topology: a regional REST API whose sole reachable ingress requires
a custom authorizer and whose integration is a private (VPC-link) proxy to the loopback-bound
server.

AWS isolation: this module never constructs a real AWS client. Dummy AWS environment values
are set before the server package is imported so the import stays offline regardless of the
machine's ambient AWS configuration, mirroring ``test_entrypoint.py``.

Validates: Requirements API Gateway deployment demonstration.
"""

import os


# Establish a deterministic, offline AWS environment BEFORE importing anything that pulls in
# the server package. The autouse ``mock_environment`` fixture in ``tests/conftest.py`` does
# not apply under ``integration/``, so this module is self-sufficient for AWS isolation.
# Values are only set when absent so an explicit ambient configuration is not clobbered.
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('AWS_REGION', 'us-east-1')
os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')  # pragma: allowlist secret
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')  # pragma: allowlist secret
os.environ.setdefault('AWS_SESSION_TOKEN', 'testing')  # pragma: allowlist secret

from awslabs.aws_healthomics_mcp_server import consts  # noqa: E402
from integration.deploy.apigateway import (  # noqa: E402
    apigateway_config,
    apigateway_server_env,
)


class TestApiGatewayServerEnv:
    """``apigateway_server_env`` injects the loopback + multi-tenant JWT configuration.

    Validates: Requirements API Gateway deployment demonstration.
    """

    def test_injects_expected_env_by_server_constant_keys(self) -> None:
        """The injected env uses the server's own ``*_ENV`` keys and the required values.

        The core assertions of the requirement are the loopback host, multi-tenant mode, and
        the ``jwt`` inbound mechanism; the transport and registry URI complete the mapping.
        Keys are asserted via ``consts.*_ENV`` so the harness stays bound to the server's
        actual environment-variable names.
        """
        env = apigateway_server_env(registry_uri='dynamodb://tbl')

        assert env[consts.MCP_HOST_ENV] == '127.0.0.1'
        assert env[consts.MCP_MULTI_TENANT_ENV] == 'true'
        assert env[consts.MCP_INBOUND_AUTH_ENV] == 'jwt'
        assert env[consts.MCP_TRANSPORT_ENV] == 'streamable-http'
        assert env[consts.MCP_JWT_ROLE_REGISTRY_ENV] == 'dynamodb://tbl'

    def test_env_is_exactly_the_five_server_keys(self) -> None:
        """No extra keys are injected: the mapping is exactly the five server env vars."""
        env = apigateway_server_env(registry_uri='dynamodb://tbl')

        assert set(env.keys()) == {
            consts.MCP_TRANSPORT_ENV,
            consts.MCP_HOST_ENV,
            consts.MCP_MULTI_TENANT_ENV,
            consts.MCP_INBOUND_AUTH_ENV,
            consts.MCP_JWT_ROLE_REGISTRY_ENV,
        }

    def test_host_is_the_server_loopback_constant(self) -> None:
        """The injected host is the server's loopback default, not a hard-coded literal.

        Binding to ``consts.DEFAULT_HTTP_HOST`` (``127.0.0.1``) keeps the server off any
        non-loopback interface so API Gateway remains the sole network-reachable ingress.
        """
        env = apigateway_server_env(registry_uri='dynamodb://tbl')

        assert env[consts.MCP_HOST_ENV] == consts.DEFAULT_HTTP_HOST

    def test_registry_uri_is_passed_through_verbatim(self) -> None:
        """The registry URI argument is threaded through unchanged into the env."""
        env = apigateway_server_env(registry_uri='dynamodb://aho-mcp-itest-registry')

        assert env[consts.MCP_JWT_ROLE_REGISTRY_ENV] == 'dynamodb://aho-mcp-itest-registry'


class TestApiGatewayConfig:
    """``apigateway_config`` describes a private, authorizer-guarded, sole-ingress API.

    Validates: Requirements API Gateway deployment demonstration.
    """

    def test_config_captures_sole_ingress_topology(self) -> None:
        """The config records sole ingress via a private, authorizer-required integration.

        A private (``VPC_LINK``) integration and a required custom authorizer together keep
        API Gateway the only reachable entry point to the loopback-bound server.
        """
        config = apigateway_config(api_name='x')

        assert config['sole_ingress'] is True
        assert config['integration']['connection_type'] == 'VPC_LINK'
        assert config['method']['authorization'] == 'CUSTOM'
        assert config['server']['host'] == '127.0.0.1'
        assert config['endpoint_type'] == 'REGIONAL'

    def test_config_defaults_and_structure(self) -> None:
        """The nested config carries the expected defaults for a regional REST API."""
        config = apigateway_config(api_name='x')

        assert config['api_name'] == 'x'
        assert config['stage_name'] == 'itest'
        assert config['server']['host'] == consts.DEFAULT_HTTP_HOST
        assert config['server']['port'] == consts.DEFAULT_HTTP_PORT
        assert config['server']['path'] == consts.DEFAULT_HTTP_PATH
        assert config['authorizer']['type'] == 'TOKEN'
        assert config['authorizer']['identity_source'] == 'method.request.header.Authorization'
        assert config['integration']['type'] == 'HTTP_PROXY'
        assert config['integration']['target_path'] == consts.DEFAULT_HTTP_PATH

    def test_config_honors_overridden_arguments(self) -> None:
        """Caller-supplied overrides flow into the returned config."""
        config = apigateway_config(
            api_name='custom-api',
            server_host='127.0.0.1',
            server_port=9000,
            server_path='/rpc',
            authorizer_name='my-authorizer',
            stage_name='prod',
        )

        assert config['api_name'] == 'custom-api'
        assert config['server']['port'] == 9000
        assert config['server']['path'] == '/rpc'
        assert config['authorizer']['name'] == 'my-authorizer'
        assert config['stage_name'] == 'prod'
        # The private, authorizer-guarded, sole-ingress invariants hold under overrides.
        assert config['sole_ingress'] is True
        assert config['integration']['connection_type'] == 'VPC_LINK'
        assert config['method']['authorization'] == 'CUSTOM'
