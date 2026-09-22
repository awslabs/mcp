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

"""Offline unit tests for the AgentCore_Deployment injected configuration.

These tests are pure and offline: they exercise the pure configuration functions in
``integration/deploy/agentcore.py`` without touching AWS or the network. They live in
``integration/harness_tests/`` -- separate from the opt-in-gated ``integration/tests/`` suite
and from the offline ``tests/`` suite -- so they are not gated by the Opt_In_Signal and run as
part of the normal offline selection.

They assert the server-facing environment the AgentCore container runs with and the AgentCore
Runtime configuration data: the ``streamable-http`` transport bound to the AgentCore container
port, multi-tenant mode enabled, the ``jwt`` inbound mechanism enabled, and AgentCore as the
sole authenticated ingress. The environment keys are asserted by the server's own configuration
constants imported from :mod:`awslabs.aws_healthomics_mcp_server.consts` (so the test binds to
the actual variable names), while the values are asserted against the literals the requirement
demands (``streamable-http``, ``true``, ``jwt``, ``str(8000)``).

AWS isolation: importing ``integration.deploy.agentcore`` builds no boto3 client (its live-AWS
seams are constructed lazily), and these tests call only the module's pure functions, so no AWS
client is ever constructed and no request leaves the process.

Validates: Requirements AgentCore deployment demonstration.
"""

from awslabs.aws_healthomics_mcp_server import consts
from integration.deploy.agentcore import (
    DEFAULT_CONTAINER_PORT,
    SERVER_PROTOCOL_MCP,
    agentcore_inbound_authorizer,
    agentcore_runtime_config,
    agentcore_server_env,
)


_REGISTRY_URI = 'dynamodb://tbl'


class TestAgentCoreServerEnv:
    """The injected server environment puts the container into the required AgentCore posture.

    Validates: Requirements AgentCore deployment demonstration.
    """

    def test_default_container_port_env_values(self) -> None:
        """Default env selects streamable-http on port 8000, multi-tenant, jwt, and the registry.

        The keys are asserted by the server's own ``consts.*_ENV`` names so the test binds to the
        real variable names, and the values are asserted against the literals the requirement
        demands: ``streamable-http`` transport, ``0.0.0.0`` host, the AgentCore container port
        ``8000``, ``true`` multi-tenant, ``jwt`` inbound auth, and the ``dynamodb://`` registry URI.
        """
        env = agentcore_server_env(registry_uri=_REGISTRY_URI)

        # Transport is streamable-http (Req 2.1).
        assert env[consts.MCP_TRANSPORT_ENV] == 'streamable-http'
        # Host binds all interfaces so AgentCore reaches the container over its NIC.
        assert env[consts.MCP_HOST_ENV] == '0.0.0.0'
        # Port is the AgentCore container port, as a string (Req 2.1). AgentCore routes MCP
        # traffic to the container at the fixed 0.0.0.0:8000/mcp.
        assert env[consts.MCP_PORT_ENV] == '8000'
        assert env[consts.MCP_PORT_ENV] == str(DEFAULT_CONTAINER_PORT)
        # Multi-tenant mode enabled with the jwt inbound mechanism (Req 2.2).
        assert env[consts.MCP_MULTI_TENANT_ENV] == 'true'
        assert env[consts.MCP_INBOUND_AUTH_ENV] == 'jwt'
        # The DynamoDB role registry is selected (Req 5.3).
        assert env[consts.MCP_JWT_ROLE_REGISTRY_ENV] == _REGISTRY_URI

    def test_env_keys_are_the_server_config_variable_names(self) -> None:
        """The env is keyed exactly by the server's configuration variable names.

        Binding the assertion to ``consts.*_ENV`` proves the deployment injects the variables the
        unmodified server actually reads, rather than hard-coded strings.
        """
        env = agentcore_server_env(registry_uri=_REGISTRY_URI)

        assert set(env.keys()) == {
            consts.MCP_TRANSPORT_ENV,
            consts.MCP_HOST_ENV,
            consts.MCP_PORT_ENV,
            consts.MCP_MULTI_TENANT_ENV,
            consts.MCP_INBOUND_AUTH_ENV,
            consts.MCP_JWT_ROLE_REGISTRY_ENV,
        }

    def test_custom_container_port_threads_into_mcp_port(self) -> None:
        """A custom container port is threaded into ``MCP_PORT`` as its string form.

        Only the port value changes; the transport, multi-tenant, inbound-auth, and registry
        values remain the required AgentCore posture.
        """
        env = agentcore_server_env(registry_uri=_REGISTRY_URI, container_port=9000)

        assert env[consts.MCP_PORT_ENV] == '9000'
        # The rest of the posture is unaffected by the custom port.
        assert env[consts.MCP_TRANSPORT_ENV] == 'streamable-http'
        assert env[consts.MCP_MULTI_TENANT_ENV] == 'true'
        assert env[consts.MCP_INBOUND_AUTH_ENV] == 'jwt'


class TestAgentCoreRuntimeConfig:
    """The AgentCore Runtime config pins MCP, embeds the env, and documents sole ingress.

    Validates: Requirements AgentCore deployment demonstration.
    """

    def test_runtime_config_shape_and_embedded_env(self) -> None:
        """The runtime config uses ``server_protocol='MCP'`` and embeds the injected env.

        The config pins the MCP server protocol (Req 2.3), carries the image reference and the
        container port it routes to (Req 2.1), and embeds the injected server environment (Req 2.2).
        """
        server_env = agentcore_server_env(registry_uri=_REGISTRY_URI)
        config = agentcore_runtime_config(
            image_uri='123.dkr.ecr.us-east-1.amazonaws.com/aho-mcp-itest:latest',
            server_env=server_env,
        )

        # MCP protocol is pinned (Req 2.3).
        assert config['server_protocol'] == 'MCP'
        assert config['server_protocol'] == SERVER_PROTOCOL_MCP
        # The container image and routed port are recorded (Req 2.1).
        assert config['container']['image_uri'] == (
            '123.dkr.ecr.us-east-1.amazonaws.com/aho-mcp-itest:latest'
        )
        assert config['container']['port'] == DEFAULT_CONTAINER_PORT
        # The injected server environment is embedded verbatim (Req 2.2).
        assert config['environment'] == dict(server_env)
        assert config['environment'][consts.MCP_TRANSPORT_ENV] == 'streamable-http'

    def test_runtime_config_documents_agentcore_as_sole_ingress(self) -> None:
        """The runtime config attaches the inbound authorizer and marks AgentCore-only ingress.

        The inbound-authorizer descriptor documents AgentCore as the sole authenticated ingress
        (Req 2.3, 2.4): it terminates authentication and declares sole ingress, and the config
        restricts network ingress to AgentCore Runtime.
        """
        config = agentcore_runtime_config(
            image_uri='123.dkr.ecr.us-east-1.amazonaws.com/aho-mcp-itest:latest',
            server_env=agentcore_server_env(registry_uri=_REGISTRY_URI),
        )

        authorizer = config['inbound_authorizer']
        assert authorizer['type'] == 'jwt'
        assert authorizer['terminates_authentication'] is True
        assert authorizer['sole_ingress'] is True
        # Network ingress is restricted to AgentCore Runtime (Req 2.4).
        assert config['network_ingress'] == 'agentcore-runtime-only'

    def test_runtime_config_records_custom_container_port(self) -> None:
        """A custom container port is recorded on the runtime config's container descriptor."""
        config = agentcore_runtime_config(
            image_uri='img:latest',
            server_env=agentcore_server_env(registry_uri=_REGISTRY_URI, container_port=9000),
            container_port=9000,
        )

        assert config['container']['port'] == 9000


class TestAgentCoreInboundAuthorizer:
    """The inbound-authorizer descriptor has the expected sole-ingress shape.

    Validates: Requirements AgentCore deployment demonstration.
    """

    def test_inbound_authorizer_shape(self) -> None:
        """The authorizer is a jwt authorizer that terminates auth and is the sole ingress.

        This is the pure descriptor the runtime config attaches by default, documenting that
        AgentCore verifies the caller's token before any request reaches the server (Req 2.3, 2.4).
        """
        authorizer = agentcore_inbound_authorizer()

        assert authorizer == {
            'type': 'jwt',
            'terminates_authentication': True,
            'sole_ingress': True,
        }
