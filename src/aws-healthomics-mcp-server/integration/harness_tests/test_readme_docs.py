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


"""Documentation lint smoke tests for the integration harness README.

These offline tests read ``integration/README.md`` once and assert that it documents
everything a new operator needs to reproduce each deployment without reverse-engineering
the harness: per-deployment provision/run/teardown commands with clearly marked
placeholders, the prerequisites subsections, the Opt_In_Signal enable/disable steps, the
Registry_Record field documentation, and the Tenant_Role cross-account trust guidance.

The assertions are tolerant of minor wording (substring / case-insensitive / regex where
reasonable) but specific enough to catch a missing section. They are pure and offline:
the tests only read a Markdown file, with no AWS access or network activity.

Validates: Requirements Documentation and reproducibility.
"""

import re
from pathlib import Path


# The README lives at integration/README.md. This test file is at
# integration/harness_tests/test_readme_docs.py, so parents[1] is integration/.
README_PATH = Path(__file__).resolve().parents[1] / 'README.md'

# Placeholder convention: values the operator must substitute are written as
# <UPPER_SNAKE> tokens, e.g. <REGION>, <ACCOUNT_ID>, <TENANT_A_ROLE_ARN>.
PLACEHOLDER_RE = re.compile(r'<[A-Z][A-Z0-9_]+>')


def _read_readme() -> str:
    """Read the harness README text once, asserting it exists.

    Validates: Requirements Documentation and reproducibility.
    """
    assert README_PATH.is_file(), f'Expected harness README at {README_PATH}'
    return README_PATH.read_text(encoding='utf-8')


def test_per_deployment_commands_with_marked_placeholders() -> None:
    """Both deployments document provision + teardown commands with marked placeholders.

    Asserts that ``--deployment agentcore`` and ``--deployment apigateway`` each appear
    with ``provision`` and ``teardown`` CLI commands (``python -m integration.deploy.cli``),
    and that the clearly-marked ``<UPPER_SNAKE>`` placeholder convention is present.

    Validates: Requirements Documentation and reproducibility.
    """
    text = _read_readme()
    lowered = text.lower()

    cli = 'python -m integration.deploy.cli'
    assert cli in text, f'README must document the deploy CLI invocation `{cli}`'
    assert f'{cli} provision' in text, 'README must document a `provision` CLI command'
    assert f'{cli} teardown' in text, 'README must document a `teardown` CLI command'

    for deployment in ('agentcore', 'apigateway'):
        flag = f'--deployment {deployment}'
        assert flag in text, f'README must document `{flag}` for the {deployment} deployment'
        # Each deployment must show both a provision and a teardown fenced command block
        # that pairs the CLI verb with its --deployment flag.
        provision_block = re.compile(rf'{re.escape(cli)}\s+provision\b[\s\S]*?{re.escape(flag)}')
        teardown_block = re.compile(rf'{re.escape(cli)}\s+teardown\b[\s\S]*?{re.escape(flag)}')
        assert provision_block.search(text), (
            f'README must show a provision command block for `{flag}`'
        )
        assert teardown_block.search(text), (
            f'README must show a teardown command block for `{flag}`'
        )

    # Both deployments should also document how to run the tests (opt-in + pytest).
    assert 'uv run pytest' in lowered, (
        'README must document running the tests with `uv run pytest`'
    )

    # Clearly marked <UPPER_SNAKE> placeholders must exist, including the canonical ones.
    placeholders = set(PLACEHOLDER_RE.findall(text))
    assert placeholders, 'README must use the <UPPER_SNAKE> placeholder convention'
    for expected in ('<REGION>', '<ACCOUNT_ID>'):
        assert expected in placeholders, f'README must include the `{expected}` placeholder'


def test_prerequisites_subsections_present() -> None:
    """The Prerequisites section lists IAM actions, tools/versions, account config, env vars.

    Asserts the ``## Prerequisites`` heading and its four subsections are present, plus at
    least one IAM action string, a tool with a version, and the opt-in env var.

    Validates: Requirements Documentation and reproducibility.
    """
    text = _read_readme()
    lowered = text.lower()

    assert '## prerequisites' in lowered, 'README must include a `## Prerequisites` section'
    for subsection in (
        '### iam actions',
        '### tools and minimum versions',
        '### account configuration',
        '### environment variables',
    ):
        assert subsection in lowered, f'Prerequisites must include a `{subsection}` subsection'

    # At least one IAM action string with a scoped resource meaning.
    iam_actions = ('sts:assumerole', 'dynamodb:createtable')
    assert any(action in lowered for action in iam_actions), (
        f'Prerequisites must list at least one IAM action (e.g. one of {iam_actions})'
    )

    # At least one required tool documented with a version requirement nearby.
    tools = ('python', 'uv', 'docker')
    assert any(tool in lowered for tool in tools), (
        f'Prerequisites must list required tools (e.g. one of {tools})'
    )
    # A minimum-version convention (e.g. `3.10+`, `0.4+`, `24+`) should appear.
    assert re.search(r'\d+(?:\.\d+)*\+', text), (
        'Prerequisites must document minimum tool versions (e.g. `3.10+`)'
    )

    assert 'RUN_REMOTE_INTEGRATION_TESTS' in text, (
        'Prerequisites must document the `RUN_REMOTE_INTEGRATION_TESTS` environment variable'
    )


def test_opt_in_signal_enable_and_disable_steps() -> None:
    """The Opt-In Signal section names the variable and gives enable + disable steps.

    Asserts an opt-in section names ``RUN_REMOTE_INTEGRATION_TESTS`` and documents both the
    ``export`` (enable) and ``unset`` (disable) steps.

    Validates: Requirements Documentation and reproducibility.
    """
    text = _read_readme()
    lowered = text.lower()

    assert 'opt-in signal' in lowered or 'opt_in_signal' in lowered, (
        'README must include an Opt-In Signal section'
    )
    assert 'RUN_REMOTE_INTEGRATION_TESTS' in text, (
        'Opt-In Signal section must name the `RUN_REMOTE_INTEGRATION_TESTS` variable'
    )
    assert 'export RUN_REMOTE_INTEGRATION_TESTS' in text, (
        'Opt-In Signal section must document the enable step '
        '(`export RUN_REMOTE_INTEGRATION_TESTS=...`)'
    )
    assert 'unset RUN_REMOTE_INTEGRATION_TESTS' in text, (
        'Opt-In Signal section must document the disable step '
        '(`unset RUN_REMOTE_INTEGRATION_TESTS`)'
    )


def test_registry_record_fields_documented() -> None:
    """The Registry_Record section documents each field by name.

    Asserts the ``## Registry_Record`` section names ``identity``, ``role_arn``,
    ``external_id``, ``account_id``, and ``enabled``.

    Validates: Requirements Documentation and reproducibility.
    """
    text = _read_readme()
    lowered = text.lower()

    assert '## registry_record' in lowered, 'README must include a `## Registry_Record` section'
    for field in ('identity', 'role_arn', 'external_id', 'account_id', 'enabled'):
        assert field in lowered, f'Registry_Record section must document the `{field}` field'


def test_tenant_role_trust_policy_guidance() -> None:
    """The Tenant_Role trust section names the action, external id, principal, and JSON policy.

    Asserts the trust section names ``sts:AssumeRole`` and ``sts:ExternalId``, references a
    trusted ``Principal``, and includes a JSON trust-policy block.

    Validates: Requirements Documentation and reproducibility.
    """
    text = _read_readme()
    lowered = text.lower()

    assert 'tenant_role trust' in lowered or 'trust relationship' in lowered, (
        'README must include a Tenant_Role trust relationship section'
    )
    assert 'sts:assumerole' in lowered, 'Trust section must name the `sts:AssumeRole` action'
    assert 'sts:externalid' in lowered, 'Trust section must name the `sts:ExternalId` condition'
    assert 'principal' in lowered, 'Trust section must reference a trusted `Principal`'

    # A JSON trust-policy block should be present: check for the key policy tokens.
    assert '"Action"' in text and '"sts:AssumeRole"' in text, (
        'Trust section must include a JSON trust-policy block naming the assume-role action'
    )
    assert '"Principal"' in text, 'JSON trust-policy block must declare a `Principal`'
