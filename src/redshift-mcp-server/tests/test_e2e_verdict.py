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

Reading a run's verdict, keeping credentials out of a report, and building the server entries a
scenario runs against. A defect in any of them is invisible: the run reports success and the
reports look no different. The rest of the harness reaches AWS and is exercised by running it;
these are pure, so they are pinned here.
"""

import pytest
from e2e_tests import agent
from e2e_tests.run import _failed_scenarios, _redact


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
