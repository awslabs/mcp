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

"""Unit tests for the harness deployment entrypoint.

These tests are pure and offline: they exercise ``integration/deploy/image/entrypoint.py``
without touching AWS or the network. They live in ``integration/harness_tests/`` — separate
from the opt-in-gated ``integration/tests/`` suite and from the offline ``tests/`` suite — so
they are not gated by the Opt_In_Signal and run as part of the normal offline selection.

They cover two guarantees of the identity-revealing tool the harness attaches to the
*unmodified* server ``mcp`` instance:

- Importing the entrypoint registers a single read-only ``WhoAmI`` tool on the already
  constructed ``mcp`` instance, and the server package source itself never mentions the tool
  (the tool is harness-owned, not a server-package change).
- Invoking ``WhoAmI`` returns only the caller's STS ``arn``/``account``/``user_id`` and no
  Credential_Material, with the STS client fully mocked so no real AWS call is made.

AWS isolation: this module never constructs a real AWS client. Dummy AWS environment values
are set before the server package is imported so the import stays offline regardless of the
machine's ambient AWS configuration, and the ``get_aws_session`` seam in the entrypoint is
mocked for the invocation test so ``sts:get_caller_identity`` never leaves the process.

Validates: Requirements Cross-tenant isolation verification.
"""

import os


# Establish a deterministic, offline AWS environment BEFORE importing the server package.
# The autouse ``mock_environment`` fixture in ``tests/conftest.py`` does not apply under
# ``integration/``, so this module is self-sufficient for AWS isolation. Values are only set
# when absent so an explicit ambient configuration is not clobbered.
os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
os.environ.setdefault('AWS_REGION', 'us-east-1')
os.environ.setdefault('AWS_ACCESS_KEY_ID', 'testing')  # pragma: allowlist secret
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'testing')  # pragma: allowlist secret
os.environ.setdefault('AWS_SESSION_TOKEN', 'testing')  # pragma: allowlist secret

import inspect  # noqa: E402
from awslabs.aws_healthomics_mcp_server import server as server_module  # noqa: E402
from awslabs.aws_healthomics_mcp_server.server import mcp  # noqa: E402
from integration.deploy.image import entrypoint  # noqa: E402
from unittest.mock import MagicMock, patch  # noqa: E402


# Fake STS identity the mocked client returns. It intentionally carries secret-looking
# fields alongside the identity fields so the test can prove the tool surfaces neither the
# secret access key nor the session token — only arn/account/user_id.
_FAKE_ARN = 'arn:aws:sts::111111111111:assumed-role/Tenant_A_Role/session'
_FAKE_ACCOUNT = '111111111111'
_FAKE_USER_ID = 'AROAEXAMPLE:session'
_FAKE_SECRET_ACCESS_KEY = 'FAKE-SECRET-ACCESS-KEY-value'  # pragma: allowlist secret
_FAKE_SESSION_TOKEN = 'FAKE-SESSION-TOKEN-value'  # pragma: allowlist secret


class TestWhoAmIRegistration:
    """The entrypoint registers ``WhoAmI`` on the imported ``mcp`` instance.

    Validates: Requirements Cross-tenant isolation verification.
    """

    async def test_who_am_i_tool_is_registered_on_mcp(self) -> None:
        """Importing the entrypoint attaches a tool named ``WhoAmI`` to ``mcp``.

        The public async ``FastMCP.list_tools`` accessor is used to enumerate the
        registered tools, and exactly one tool named ``WhoAmI`` must be present.
        """
        tools = await mcp.list_tools()
        names = [tool.name for tool in tools]

        assert 'WhoAmI' in names
        assert names.count('WhoAmI') == 1

    def test_who_am_i_attached_without_modifying_server_source(self) -> None:
        """The tool is harness-owned: the server package source never mentions it.

        The entrypoint attaches ``WhoAmI`` to the already constructed ``mcp`` instance at
        import time, so the tool is present at runtime while the server package's own source
        contains no reference to it.
        """
        server_source = inspect.getsource(server_module)

        assert 'WhoAmI' not in server_source
        # The harness entrypoint is where the tool is defined.
        assert 'WhoAmI' in inspect.getsource(entrypoint)


class TestWhoAmIReturnsNoCredentialMaterial:
    """``WhoAmI`` returns only identity fields and no Credential_Material.

    Validates: Requirements Cross-tenant isolation verification.
    """

    async def test_returns_only_identity_fields(self) -> None:
        """The result keys are exactly ``arn``/``account``/``user_id``.

        The STS client is fully mocked via the ``get_aws_session`` seam so no real AWS call
        is made. The mocked ``get_caller_identity`` returns identity fields plus secret-looking
        fields; the tool must surface only the three identity fields.
        """
        fake_session = MagicMock()
        fake_session.client.return_value.get_caller_identity.return_value = {
            'Arn': _FAKE_ARN,
            'Account': _FAKE_ACCOUNT,
            'UserId': _FAKE_USER_ID,
            'SecretAccessKey': _FAKE_SECRET_ACCESS_KEY,
            'SessionToken': _FAKE_SESSION_TOKEN,
        }

        with patch.object(
            entrypoint, 'get_aws_session', return_value=fake_session
        ) as mock_get_session:
            result = await entrypoint.who_am_i(MagicMock())

        # The seam was used and the STS client was requested — no real session was built.
        mock_get_session.assert_called_once_with()
        fake_session.client.assert_called_once_with('sts')

        assert set(result.keys()) == {'arn', 'account', 'user_id'}
        assert result == {
            'arn': _FAKE_ARN,
            'account': _FAKE_ACCOUNT,
            'user_id': _FAKE_USER_ID,
        }

    async def test_result_contains_no_credential_material(self) -> None:
        """No injected secret value appears anywhere in the returned mapping.

        The mocked identity injects a fake secret access key and session token. Neither may
        appear as a key or as a substring of any value in the tool's result, proving the tool
        returns no Credential_Material.
        """
        fake_session = MagicMock()
        fake_session.client.return_value.get_caller_identity.return_value = {
            'Arn': _FAKE_ARN,
            'Account': _FAKE_ACCOUNT,
            'UserId': _FAKE_USER_ID,
            'SecretAccessKey': _FAKE_SECRET_ACCESS_KEY,
            'SessionToken': _FAKE_SESSION_TOKEN,
        }

        with patch.object(entrypoint, 'get_aws_session', return_value=fake_session):
            result = await entrypoint.who_am_i(MagicMock())

        secrets = (_FAKE_SECRET_ACCESS_KEY, _FAKE_SESSION_TOKEN)
        for secret in secrets:
            assert secret not in result.keys()
            for value in result.values():
                assert secret not in str(value)


class TestImportDoesNotStartServer:
    """Importing the entrypoint must not start the server.

    Validates: Requirements Cross-tenant isolation verification.
    """

    def test_main_guarded_by_dunder_main(self) -> None:
        """``main()`` runs only under ``__main__``, so import does not serve.

        The import performed at module load did not start a server (this test module is
        running), and ``main`` is the unmodified server entrypoint guarded by the standard
        ``if __name__ == '__main__'`` block.
        """
        assert entrypoint.main is server_module.main
        source = inspect.getsource(entrypoint)
        assert "if __name__ == '__main__':" in source
