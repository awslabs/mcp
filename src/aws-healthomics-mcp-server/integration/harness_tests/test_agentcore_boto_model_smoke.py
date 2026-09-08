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

"""Boto-model smoke test for the AgentCore Runtime create/delete requests.

The live AgentCore request shapes cannot be exercised offline against a real account, so this
test validates the exact keyword arguments the harness builds against the **botocore service
model** for ``bedrock-agentcore-control`` -- the same model boto3 would validate against at
call time. This catches parameter-name/shape drift (a wrong or missing member, or a value
outside an enum) without any AWS access or network activity.

The check is offline but *version-dependent*: ``bedrock-agentcore-control`` is a newer service,
so if the installed botocore does not ship its model the model-validation tests skip rather
than fail. The pure-shape assertions still run regardless.

Validates: Requirements AgentCore deployment demonstration.
"""

import pytest
from integration.deploy.agentcore import (
    NETWORK_MODE_PUBLIC,
    SERVER_PROTOCOL_MCP,
    agentcore_inbound_authorizer,
    agentcore_runtime_config,
    agentcore_server_env,
    build_create_agent_runtime_kwargs,
)


_SERVICE = 'bedrock-agentcore-control'
_DISCOVERY_URL = (
    'https://cognito-idp.us-east-1.amazonaws.com/us-east-1_abc/.well-known/openid-configuration'
)
_EXECUTION_ROLE_ARN = 'arn:aws:iam::111122223333:role/aho-mcp-itest-exec'
_IMAGE_URI = '111122223333.dkr.ecr.us-east-1.amazonaws.com/aho-mcp-itest:latest'


def _representative_create_kwargs() -> dict:
    """Build the create-runtime kwargs the harness would send for a complete deployment."""
    server_env = agentcore_server_env(registry_uri='dynamodb://aho-mcp-itest-registry')
    authorizer = agentcore_inbound_authorizer(
        discovery_url=_DISCOVERY_URL, allowed_clients=['client-abc']
    )
    config = agentcore_runtime_config(
        image_uri=_IMAGE_URI,
        server_env=server_env,
        authorizer=authorizer,
        execution_role_arn=_EXECUTION_ROLE_ARN,
    )
    return build_create_agent_runtime_kwargs(runtime_name='aho-mcp-itest', config=config)


def _create_input_shape():
    """Return the CreateAgentRuntime input shape, or skip if the model is unavailable."""
    botocore_session = pytest.importorskip('botocore.session')
    from botocore.exceptions import DataNotFoundError, UnknownServiceError

    session = botocore_session.Session()
    try:
        model = session.get_service_model(_SERVICE)
    except (UnknownServiceError, DataNotFoundError) as exc:  # pragma: no cover - version-dependent
        pytest.skip(f'botocore has no {_SERVICE!r} service model: {exc}')
    return model


class TestCreateAgentRuntimeKwargsPureShape:
    """The builder produces the nested request shape the real API expects.

    Validates: Requirements AgentCore deployment demonstration.
    """

    def test_protocol_and_network_are_nested_not_top_level(self) -> None:
        """The serverProtocol lives under protocolConfiguration, and networkMode is set.

        The API has no top-level ``serverProtocol`` parameter and requires a
        ``networkConfiguration``; asserting the nesting guards against the earlier bug where
        ``serverProtocol`` was passed at the top level.
        """
        kwargs = _representative_create_kwargs()

        assert 'serverProtocol' not in kwargs
        assert kwargs['protocolConfiguration']['serverProtocol'] == SERVER_PROTOCOL_MCP
        assert kwargs['networkConfiguration']['networkMode'] == NETWORK_MODE_PUBLIC

    def test_artifact_role_and_authorizer_wired(self) -> None:
        """The image, execution role, and Cognito JWT authorizer are placed correctly."""
        kwargs = _representative_create_kwargs()

        container = kwargs['agentRuntimeArtifact']['containerConfiguration']
        assert container['containerUri'] == _IMAGE_URI
        assert kwargs['roleArn'] == _EXECUTION_ROLE_ARN
        custom_jwt = kwargs['authorizerConfiguration']['customJWTAuthorizer']
        assert custom_jwt['discoveryUrl'] == _DISCOVERY_URL
        assert custom_jwt['allowedClients'] == ['client-abc']

    def test_tenant_token_header_is_forwarded_to_container(self) -> None:
        """The non-reserved tenant-token header is allow-listed so the token reaches the server.

        AgentCore strips the reserved ``Authorization`` header at its authorizer and does not
        forward it even when allow-listed, so the harness forwards the token in the custom
        ``TENANT_TOKEN_HEADER`` (which the container entrypoint maps back onto Authorization).
        """
        from integration.harness.headers import TENANT_TOKEN_HEADER

        kwargs = _representative_create_kwargs()

        allowlist = kwargs['requestHeaderConfiguration']['requestHeaderAllowlist']
        assert TENANT_TOKEN_HEADER in allowlist


class TestCreateAgentRuntimeAgainstBotoModel:
    """The create kwargs validate cleanly against the botocore service model.

    Validates: Requirements AgentCore deployment demonstration.
    """

    def test_kwargs_pass_botocore_param_validation(self) -> None:
        """The botocore ParamValidator reports no errors for the create-runtime kwargs.

        This validates required members, member names, and types against the same model boto3
        uses, so a drifted or missing parameter fails here instead of at first live call.
        """
        from botocore.validate import ParamValidator

        model = _create_input_shape()
        input_shape = model.operation_model('CreateAgentRuntime').input_shape
        kwargs = _representative_create_kwargs()

        report = ParamValidator().validate(kwargs, input_shape)
        assert not report.has_errors(), report.generate_report()

    def test_required_members_present_in_kwargs(self) -> None:
        """Every member the model marks required is present in the built kwargs."""
        model = _create_input_shape()
        input_shape = model.operation_model('CreateAgentRuntime').input_shape
        kwargs = _representative_create_kwargs()

        assert set(input_shape.required_members) <= set(kwargs), (
            f'missing required members: {set(input_shape.required_members) - set(kwargs)}'
        )

    def test_enum_values_are_valid(self) -> None:
        """The serverProtocol and networkMode values are within the model's enums."""
        model = _create_input_shape()
        input_shape = model.operation_model('CreateAgentRuntime').input_shape

        protocol_enum = (
            input_shape.members['protocolConfiguration']
            .members['serverProtocol']
            .metadata.get('enum', [])
        )
        network_enum = (
            input_shape.members['networkConfiguration']
            .members['networkMode']
            .metadata.get('enum', [])
        )

        assert SERVER_PROTOCOL_MCP in protocol_enum
        assert NETWORK_MODE_PUBLIC in network_enum


class TestDeleteAgentRuntimeAgainstBotoModel:
    """Teardown deletes by runtime id, matching the model's DeleteAgentRuntime input.

    Validates: Requirements Provisioning and teardown lifecycle.
    """

    def test_delete_uses_agent_runtime_id(self) -> None:
        """The delete request keys on ``agentRuntimeId`` (an ARN is not a valid parameter)."""
        from botocore.validate import ParamValidator

        model = _create_input_shape()
        input_shape = model.operation_model('DeleteAgentRuntime').input_shape

        members = set(input_shape.members)
        assert 'agentRuntimeId' in members
        assert 'agentRuntimeArn' not in members

        report = ParamValidator().validate({'agentRuntimeId': 'rt-abc123'}, input_shape)
        assert not report.has_errors(), report.generate_report()
