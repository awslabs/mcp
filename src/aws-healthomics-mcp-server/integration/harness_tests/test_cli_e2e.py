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

"""Offline unit tests for the deploy CLI, focused on the one-shot ``e2e`` command.

Pure and offline: the CLI is exercised through :func:`integration.deploy.cli.main` with the
provisioning, pytest-runner, and teardown seams monkeypatched, so no AWS client is built and
no pytest subprocess is spawned. The tests assert that ``e2e`` provisions, injects the run
config's ``AHO_ITEST_*`` values into the test run, and tears down when asked.

Validates: Requirements Documentation and reproducibility, Provisioning and teardown lifecycle.
"""

from integration.deploy import agentcore, cli
from integration.deploy.common import ProvisionResult, ProvisionStatus, TeardownResult
from pathlib import Path


def _complete_outcome(tmp_path) -> agentcore.AgentCoreProvisionOutcome:
    """Build a COMPLETE provisioning outcome with a run config carrying fake tokens."""
    run_config = agentcore.AgentCoreRunConfig(
        endpoint='https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/x/invocations',
        bearer_token='tok-a',  # pragma: allowlist secret
        tenant_a_token='tok-a',  # pragma: allowlist secret
        tenant_b_token='tok-b',  # pragma: allowlist secret
        tenant_a_expected_arn='arn:aws:sts::111122223333:assumed-role/a/sub-a',
        tenant_b_expected_arn='arn:aws:sts::111122223333:assumed-role/b/sub-b',
        inventory_path=Path(tmp_path / 'agentcore-inventory.json'),
    )
    result = ProvisionResult(
        status=ProvisionStatus.COMPLETE,
        endpoint=run_config.endpoint,
        failed_stage=None,
        detail=None,
        inventory_path=run_config.inventory_path,
    )
    return agentcore.AgentCoreProvisionOutcome(result=result, run_config=run_config)


class TestParser:
    """The parser exposes the e2e command with its options.

    Validates: Requirements Documentation and reproducibility.
    """

    def test_e2e_command_parses(self) -> None:
        """The e2e subcommand and its --teardown flag parse successfully."""
        args = cli.build_parser().parse_args(
            ['e2e', '--deployment', 'agentcore', '--region', 'us-east-1', '--teardown']
        )
        assert args.command == 'e2e'
        assert args.teardown is True
        # Inbound defaults to jwt.
        assert args.inbound == 'jwt'

    def test_e2e_inbound_explicit_parses_and_threads(self, tmp_path, monkeypatch) -> None:
        """--inbound explicit parses and is passed through to provisioning."""
        args = cli.build_parser().parse_args(
            ['e2e', '--deployment', 'agentcore', '--region', 'us-east-1', '--inbound', 'explicit']
        )
        assert args.inbound == 'explicit'

        captured: dict = {}
        monkeypatch.setattr(
            cli.agentcore,
            'provision_agentcore',
            lambda **kwargs: captured.update(kwargs) or _complete_outcome(tmp_path),
        )
        monkeypatch.setattr(cli, '_run_pytest', lambda env_overrides, tests: 0)

        cli.main(
            ['e2e', '--deployment', 'agentcore', '--region', 'us-east-1', '--inbound', 'explicit']
        )

        assert captured['inbound'] == 'explicit'


class TestE2ERun:
    """``e2e`` provisions, wires the run config into the test run, and optionally tears down.

    Validates: Requirements Provisioning and teardown lifecycle.
    """

    def test_e2e_injects_run_config_env_and_runs_tests(self, tmp_path, monkeypatch) -> None:
        """e2e injects the minted tokens/endpoint and runs the default AgentCore tests."""
        outcome = _complete_outcome(tmp_path)
        monkeypatch.setattr(cli, '_provision_agentcore', lambda args: outcome)

        captured: dict = {}

        def fake_run_pytest(env_overrides, tests):
            captured['env'] = env_overrides
            captured['tests'] = list(tests)
            return 0

        monkeypatch.setattr(cli, '_run_pytest', fake_run_pytest)

        rc = cli.main(['e2e', '--deployment', 'agentcore', '--region', 'us-east-1'])

        assert rc == 0
        # The minted tokens and endpoint were injected into the test environment.
        assert captured['env']['AHO_ITEST_BEARER_TOKEN'] == 'tok-a'  # pragma: allowlist secret
        assert captured['env']['AHO_ITEST_TENANT_B_TOKEN'] == 'tok-b'  # pragma: allowlist secret
        # The default AgentCore tests were selected.
        assert captured['tests'] == list(cli.DEFAULT_AGENTCORE_TESTS)

    def test_e2e_teardown_runs_after_tests(self, tmp_path, monkeypatch) -> None:
        """With --teardown, the inventory is torn down after the tests run."""
        outcome = _complete_outcome(tmp_path)
        monkeypatch.setattr(cli, '_provision_agentcore', lambda args: outcome)
        monkeypatch.setattr(cli, '_run_pytest', lambda env_overrides, tests: 0)

        torn: dict = {}

        def fake_teardown(*, inventory_path):
            torn['path'] = inventory_path
            return TeardownResult(succeeded=True, undeleted=())

        monkeypatch.setattr(agentcore, 'teardown_agentcore', fake_teardown)

        rc = cli.main(['e2e', '--deployment', 'agentcore', '--region', 'us-east-1', '--teardown'])

        assert rc == 0
        assert torn['path'] is not None

    def test_e2e_skips_tests_when_provision_fails(self, tmp_path, monkeypatch) -> None:
        """A failed provision short-circuits: no tests run and the exit code is non-zero."""
        failed = agentcore.AgentCoreProvisionOutcome(
            result=ProvisionResult(
                status=ProvisionStatus.FAILED,
                endpoint=None,
                failed_stage='create-tenant-roles',
                detail='boom',
                inventory_path=Path(tmp_path / 'agentcore-inventory.json'),
            ),
            run_config=None,
        )
        monkeypatch.setattr(cli, '_provision_agentcore', lambda args: failed)

        def fail_if_called(env_overrides, tests):  # pragma: no cover - must not run
            raise AssertionError('tests must not run when provisioning fails')

        monkeypatch.setattr(cli, '_run_pytest', fail_if_called)

        rc = cli.main(['e2e', '--deployment', 'agentcore', '--region', 'us-east-1'])
        assert rc == 1

    def test_e2e_rejects_apigateway(self, monkeypatch) -> None:
        """e2e refuses the apigateway deployment, which cannot mint its own credentials."""
        rc = cli.main(['e2e', '--deployment', 'apigateway', '--region', 'us-east-1'])
        assert rc == 2
