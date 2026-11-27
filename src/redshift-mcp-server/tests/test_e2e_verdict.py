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


"""Tests for what the end-to-end harness decides without talking to AWS.

Reading a run's verdict, keeping credentials out of a report, building the server entries a
scenario runs against, and reading the config. A defect in any of them is invisible: the run
reports success and the reports look no different. The rest of the harness reaches AWS and is
exercised by running it; these are pure, so they are pinned here.
"""

import pytest
import re
from e2e_tests import agent, run, scenarios
from e2e_tests.config import EXAMPLE_PATH, ConfigError, load
from e2e_tests.run import _failed_scenarios, _redact
from unittest.mock import Mock


def _table(*rows: tuple[str, str]) -> str:
    """Build a summary section carrying the verdict table the agent is asked to end with."""
    lines = ['## Summary', '', '| Scenario | Result |', '| --- | --- |']
    lines += [f'| {name} | {result} |' for name, result in rows]
    return '\n'.join(lines)


class TestNoVerdictIsNotAPass:
    """Every one of these returns None, which the caller counts as a failed run."""

    def test_no_summary_at_all(self):
        """The agent ended without one, so nothing graded the run."""
        assert _failed_scenarios(None, min_rows=1) is None

    def test_a_summary_with_no_table(self):
        """Prose is not a verdict, however confident it reads."""
        assert _failed_scenarios('## Summary\n\nEverything worked.', min_rows=1) is None

    def test_a_table_shorter_than_the_floor(self):
        """A table too short to have covered the surface graded nothing.

        One row saying PASS is the cheapest way for a run to look green, and the floor is what
        stops it counting.
        """
        assert _failed_scenarios(_table(('only one', 'PASS')), min_rows=6) is None

    @pytest.mark.parametrize('result', ['ERROR', 'SKIP', 'UNKNOWN', 'N/A', 'PASS (partial)', ''])
    def test_a_result_that_is_neither_pass_nor_fail(self, result):
        """That case was not graded, and counting it as a pass is how a run reports success.

        Matched by substring instead, 'PASS (partial)' read as a pass and the rest read as
        anything-but-FAIL, which is also a pass.
        """
        table = _table(('one', 'PASS'), ('two', result), ('three', 'PASS'))

        assert _failed_scenarios(table, min_rows=1) is None


class TestAVerdictIsRead:
    """A table that graded the run answers which rows failed."""

    def test_every_row_passed(self):
        """An empty list, not None: the run was graded and nothing failed."""
        table = _table(('one', 'PASS'), ('two', 'PASS'))

        assert _failed_scenarios(table, min_rows=2) == []

    def test_the_failed_rows_are_named(self):
        """The caller prints them, so the operator knows what to look at."""
        table = _table(('one', 'PASS'), ('two', 'FAIL'), ('three', 'FAIL'))

        assert _failed_scenarios(table, min_rows=3) == ['two', 'three']

    def test_a_lowercase_verdict_is_read(self):
        """The agent writes the table, and its casing is not something to fail a run over."""
        table = _table(('one', 'pass'), ('two', 'fail'))

        assert _failed_scenarios(table, min_rows=2) == ['two']

    def test_an_unnamed_row_is_still_reported(self):
        """Losing the failure because its name cell was empty would be worse than a placeholder."""
        table = _table(('', 'FAIL'))

        assert _failed_scenarios(table, min_rows=1) == ['(unnamed)']

    def test_the_header_and_its_rule_are_not_rows(self):
        """Counted as rows, they would satisfy the floor on their own."""
        assert _failed_scenarios(_table(('one', 'PASS')), min_rows=2) is None


class TestCredentialsDoNotReachAReport:
    """The agent can read its own config, and the report it produces is committed."""

    def test_each_value_is_replaced_everywhere_it_appears(self):
        """One shell command is enough to echo the config, so the transcript is scrubbed.

        The values here are deliberately not credential-shaped: what is under test is the
        replacement, and a realistic-looking fixture only trips the repo's secret scanner.
        """
        transcript = 'cat the agent config\nfirst-value and second-value\nfirst-value again\n'

        redacted = _redact(transcript, {'first-value', 'second-value'})

        assert 'first-value' not in redacted
        assert 'second-value' not in redacted
        assert redacted.count('[redacted]') == 3

    def test_a_value_containing_another_is_fully_replaced(self):
        """Replaced shortest-first, the longer value would keep a readable tail.

        Session tokens are long and can carry a shorter value inside them, so the order matters.
        """
        redacted = _redact('carried=outer-inner-tail', {'inner', 'outer-inner-tail'})

        assert redacted == 'carried=[redacted]'

    def test_nothing_to_redact_leaves_the_transcript_alone(self):
        """A run with no assumed-role configuration collects no values."""
        assert _redact('nothing secret here', set()) == 'nothing secret here'


class TestLocalPathsDoNotReachAReport:
    """A report names the package root and the home directory by label."""

    def test_each_path_is_replaced_as_given_and_resolved(self, mocker, monkeypatch, tmp_path):
        """Home can be a symlink, so output carries each path through it and resolved.

        Here home as given is part of its resolved form, and home is part of the package root,
        so the order of replacement matters.
        """
        real = tmp_path / 'ana.real'
        real.mkdir()
        home = tmp_path / 'ana'
        home.symlink_to(real)
        monkeypatch.setenv('HOME', str(home))
        mocker.patch('e2e_tests.run.PACKAGE_ROOT', real / 'pkg')
        text = f'{real}/pkg/a {home}/pkg/b {real}/c {home}/d first-value e\n'

        redacted = _redact(text, {'first-value'})

        assert redacted == '[package root]/a [package root]/b ~/c ~/d [redacted] e\n'


class TestDeniedServersDoNotInheritAProfile:
    """The denied configurations are the only way a run reaches the no_batch fallback."""

    def _server(self, **kwargs):
        """Build one server entry the way `render` does."""
        return agent._server('/usr/bin/uv', 'srv', {'AWS_ACCESS_KEY_ID': 'k'}, **kwargs)

    def test_denied_servers_run_without_a_profile(self):
        """Omitting AWS_PROFILE from `env` does not remove it from the child.

        An MCP server inherits this process's environment, so an omitted one leaves the harness's
        profile in place and a profile beats explicit keys: the denied configurations then run as
        the harness's own identity, through the batch path every fallback scenario means to avoid.
        """
        entry = self._server(without_profile=True)

        assert entry['command'].endswith('/env')
        assert entry['args'][:2] == ['-u', 'AWS_PROFILE']
        assert 'AWS_PROFILE' not in entry['env']

    def test_the_other_servers_keep_the_inherited_profile(self):
        """They authenticate as the operator, which is what a user of the server does."""
        entry = self._server()

        assert entry['command'].endswith('uv')
        assert '-u' not in entry['args']

    def test_both_shapes_run_the_same_server(self):
        """Wrapping the command must not change which code is under test."""
        wrapped = self._server(without_profile=True)
        plain = self._server()

        assert wrapped['args'][-len(plain['args']) :] == plain['args']
        assert wrapped['args'][2] == plain['command']


# The guide scenario's target, and the lines the server logs for each call or outcome it grades.
_TARGET = 'e2e-target'
_GUIDE = 'Serving skill file SKILL.md chunk 1 of 1'
_LIST = 'Discovering Redshift clusters and serverless workgroups'
_LISTED = 'Successfully retrieved 6 clusters'
_REFERENCE = 'Serving skill file references/redshift-sql-metadata.md chunk 1 of 1'
_TABLES = f'Discovering tables in schema public in database dev on cluster {_TARGET}'
_QUERY = f'Executing query on cluster {_TARGET} in database dev (access mode: read-only)'
_WRONG_TYPE = (
    f'Error in execute_query_tool: No provisioned cluster named {_TARGET} was found. Found '
    'instead: a serverless one.'
)

_GUIDE_ROW = 'Guide retrieved with no argument before the first query'
_TYPE_ROW = "Target's type taken from list_clusters, not asked for or guessed wrong"
_REFERENCE_ROW = 'Reference files loaded unprompted, each in full'


class TestTheGuideScenarioIsGradedFromTheServerLog:
    """Its agent asks as a user would, so the verdict is the server's record, not the agent's."""

    def _failed(self, *lines: str) -> list[str] | None:
        """Grade a log of these lines and read the verdict as the harness does."""
        grade = scenarios.GUIDE.grade
        assert grade is not None
        config = Mock(guide_workgroup_name=_TARGET)
        return _failed_scenarios(grade('\n'.join(lines), config), scenarios.GUIDE.min_rows)

    def test_every_check_passes_in_the_order_the_guide_asks_for(self):
        """Guide first, then list_clusters and a reference, then the target."""
        assert self._failed(_GUIDE, _LIST, _REFERENCE, _LISTED, _QUERY) == []

    def test_a_guide_retrieved_after_the_first_query_fails(self):
        """Read after the agent acted, it steered nothing."""
        assert self._failed(_LIST, _LISTED, _QUERY, _GUIDE, _REFERENCE) == [_GUIDE_ROW]
        assert self._failed(_LIST, _LISTED, _TABLES, _GUIDE, _REFERENCE, _QUERY) == [_GUIDE_ROW]

    def test_no_call_naming_the_target_fails_both_ordering_checks(self):
        """An agent that stopped to ask the user for the type never named the target."""
        assert self._failed(_GUIDE, _LIST, _LISTED, _REFERENCE) == [_GUIDE_ROW, _TYPE_ROW]

    def test_no_reference_served_fails(self):
        """A refused path logs nothing, so only a served reference counts."""
        assert self._failed(_GUIDE, _LIST, _LISTED, _QUERY) == [_REFERENCE_ROW]

    def test_a_reference_served_in_part_fails(self):
        """Each chunk served is logged, so a chunk the agent never asked for shows."""
        first = 'Serving skill file references/redshift-storage-utilization.md chunk 1 of 2'
        last = first.replace('chunk 1', 'chunk 2')

        assert self._failed(_GUIDE, _LIST, first, _LISTED, _QUERY) == [_REFERENCE_ROW]
        assert self._failed(_GUIDE, _LIST, last, first, _LISTED, _QUERY) == []

    def test_a_target_named_before_list_clusters_answered_fails(self):
        """Called alongside list_clusters, the call took its type from somewhere else."""
        assert self._failed(_GUIDE, _REFERENCE, _LIST, _QUERY, _LISTED) == [_TYPE_ROW]

    def test_any_tool_naming_the_target_first_counts_not_only_a_query(self):
        """Every tool that names the target takes its type, so the first of them had to know it."""
        assert self._failed(_GUIDE, _REFERENCE, _TABLES, _LIST, _LISTED, _QUERY) == [_TYPE_ROW]

    def test_a_type_refused_for_the_target_fails_though_retried(self):
        """The server refuses the wrong type; the agent guessed even with the answer in hand."""
        log = (_GUIDE, _LIST, _LISTED, _REFERENCE, _QUERY, _WRONG_TYPE, _QUERY)

        assert self._failed(*log) == [_TYPE_ROW]

    def test_the_prompt_names_the_target_and_no_type(self, mocker):
        """The type has to come from somewhere other than the prompt."""
        config = mocker.Mock(database='dev', guide_workgroup_name=_TARGET)

        prompt = scenarios.GUIDE.prompt(config).lower()

        assert f'warehouse `{_TARGET}`' in prompt
        assert not re.search('serverless|provisioned|workgroup|cluster', prompt), prompt

    def test_its_agent_reaches_the_guide_only_through_the_read_only_server(self, mocker):
        """No builtins to read the package with, and no other server."""
        mocker.patch('e2e_tests.agent.require_executable', return_value='/usr/bin/uv')
        config = mocker.Mock(agent_name='e2e', profile='p', region='r', model='m')

        rendered = agent.render_guide(config)

        assert rendered['tools'] == rendered['allowedTools'] == [f'@{agent.READ_ONLY}']
        assert list(rendered['mcpServers']) == [agent.READ_ONLY]
        assert rendered['includeMcpJson'] is False
        assert rendered['mcpServers'][agent.READ_ONLY]['env']['LOG_FILE'] == str(agent.GUIDE_LOG)

    def test_a_guide_skill_installed_for_every_agent_refuses_the_run(self, mocker, tmp_path):
        """The skill would hand the agent the guide, and the run would grade nothing."""
        mocker.patch('e2e_tests.agent.GLOBAL_SKILL', tmp_path)
        for step in ('run._session', 'deploy.check_ownership', 'deploy.up'):
            mocker.patch(f'e2e_tests.{step}')
        mocker.patch('e2e_tests.agent.write', return_value=(tmp_path, set()))
        invoke = mocker.patch('e2e_tests.run._invoke')

        assert run.test(mocker.Mock(), ['guide'], keep_up=True) == 1
        invoke.assert_not_called()


class TestTheGuideTargetComesFromTheConfig:
    """Like every configured name, it has no default that could reach the wrong account."""

    def test_a_config_without_it_is_refused(self, mocker, tmp_path):
        """The example carries it; a config without it fails to load."""
        path = tmp_path / 'config.toml'
        mocker.patch('e2e_tests.config.CONFIG_PATH', path)
        filled = EXAMPLE_PATH.read_text().replace('<AWS_PROFILE>', 'p').replace('<REGION>', 'r')

        path.write_text(filled)
        assert load().guide_workgroup_name == 'mcp-e2e-harbor'

        path.write_text(filled.replace('guide_workgroup_name = "mcp-e2e-harbor"\n', ''))
        with pytest.raises(ConfigError, match=r'missing \[serverless\]\.guide_workgroup_name'):
            load()
