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

"""Tests for the server entry point."""
# ruff: noqa: D101

import pytest
from awslabs.aws_transform_mcp_server.server import (
    INSTRUCTIONS,
    _register_handlers,
    create_server,
)
from mcp.server.fastmcp import FastMCP
from unittest.mock import MagicMock, patch


# ── create_server ──────────────────────────────────────────────────────────


class TestCreateServer:
    """Tests for create_server factory."""

    def test_returns_fastmcp_instance(self):
        mcp = create_server()
        assert isinstance(mcp, FastMCP)

    def test_server_name(self):
        mcp = create_server()
        assert mcp.name == 'awslabs.aws-transform-mcp-server'

    def test_instructions_set(self):
        mcp = create_server()
        assert mcp.instructions == INSTRUCTIONS


# ── INSTRUCTIONS ───────────────────────────────────────────────────────────


class TestInstructions:
    """Verify INSTRUCTIONS contains key guidance phrases."""

    @pytest.mark.parametrize(
        'phrase',
        [
            'AWS Transform',
            'HITL',
            'configure',
            'configure_sigv4',
            'get_status',
            'MUST NOT',
            'complete_task',
            'list_resources',
            'get_resource',
            'SigV4',
            'NEVER auto-submit',
        ],
    )
    def test_contains_key_phrase(self, phrase: str):
        assert phrase in INSTRUCTIONS


# ── _register_handlers ─────────────────────────────────────────────────────


_HANDLER_MODULES = {
    'ConfigureHandler': 'awslabs.aws_transform_mcp_server.tools.configure',
    'SigV4ConfigureHandler': 'awslabs.aws_transform_mcp_server.tools.sigv4_configure',
    'WorkspaceHandler': 'awslabs.aws_transform_mcp_server.tools.workspace',
    'JobHandler': 'awslabs.aws_transform_mcp_server.tools.job',
    'HitlHandler': 'awslabs.aws_transform_mcp_server.tools.hitl',
    'ArtifactHandler': 'awslabs.aws_transform_mcp_server.tools.artifact',
    'ChatHandler': 'awslabs.aws_transform_mcp_server.tools.chat',
    'ConnectorHandler': 'awslabs.aws_transform_mcp_server.tools.connector',
    'AgentRegistryHandler': 'awslabs.aws_transform_mcp_server.tools.agent_registry',
    'ListResourcesHandler': 'awslabs.aws_transform_mcp_server.tools.list_resources',
    'GetResourceHandler': 'awslabs.aws_transform_mcp_server.tools.get_resource',
    'CollaboratorHandler': 'awslabs.aws_transform_mcp_server.tools.collaborator',
    'ApproveHitlHandler': 'awslabs.aws_transform_mcp_server.tools.approve_hitl',
    'LoadInstructionsHandler': 'awslabs.aws_transform_mcp_server.tools.load_instructions',
}


class TestRegisterHandlers:
    """Tests for _register_handlers."""

    def test_all_handlers_instantiated(self):
        """Each handler class must be instantiated exactly once with the mcp object."""
        mcp = MagicMock(spec=FastMCP)
        mocks = {}
        patches = []
        for cls_name, module_path in _HANDLER_MODULES.items():
            mock_cls = MagicMock()
            mocks[cls_name] = mock_cls
            p = patch(f'{module_path}.{cls_name}', mock_cls)
            patches.append(p)

        for p in patches:
            p.start()
        try:
            _register_handlers(mcp)
            for _cls_name, mock_cls in mocks.items():
                mock_cls.assert_called_once_with(mcp)
        finally:
            for p in patches:
                p.stop()

    def test_handler_count(self):
        """There should be exactly 14 handler classes registered."""
        assert len(_HANDLER_MODULES) == 14


# ── main ───────────────────────────────────────────────────────────────────


class TestMain:
    """Tests for the main() entry point."""

    @patch('awslabs.aws_transform_mcp_server.server._register_handlers')
    @patch('awslabs.aws_transform_mcp_server.server.create_server')
    @patch('awslabs.aws_transform_mcp_server.server.asyncio.run')
    @patch('awslabs.aws_transform_mcp_server.server.argparse.ArgumentParser')
    def test_main_wiring(self, mock_argparse, mock_asyncio_run, mock_create, mock_register):
        """main() must load config, create server, register handlers, and run."""
        mock_mcp = MagicMock(spec=FastMCP)
        mock_create.return_value = mock_mcp
        mock_parser = MagicMock()
        mock_argparse.return_value = mock_parser

        from awslabs.aws_transform_mcp_server.server import main

        main()

        mock_parser.parse_args.assert_called_once()
        mock_asyncio_run.assert_called_once()
        mock_create.assert_called_once()
        mock_register.assert_called_once_with(mock_mcp)
        mock_mcp.run.assert_called_once()
