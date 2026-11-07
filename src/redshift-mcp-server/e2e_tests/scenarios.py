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

"""What the testing agent is asked to do.

Each scenario is a prompt, not a script. It names the surface and what to look at, and leaves
the agent to derive the cases from the package's own unit tests. That is deliberate: a
hand-written expectation only ever finds what its author already thought of, and the unit
suite is where the intended behaviour is already stated precisely.

For the same reason a prompt never says what should happen. Told the answer, an agent reports
it back; told only where to look, it has to find out.

The guide scenario's agent asks as a user would and writes no verdict, so the harness grades the
server's log instead.
"""

import re
from dataclasses import dataclass
from e2e_tests import agent
from e2e_tests.config import Config
from typing import Callable


# The heading the agent is told to put its summary behind, and the harness looks for when
# splitting the reply. Distinctive enough to find by search, because the CLI streams the agent's
# prose without separating one passage from the next.
SUMMARY_HEADING = '## Summary'


@dataclass(frozen=True)
class Scenario:
    """One agent run: a prompt, and how to name what comes out of it."""

    key: str
    title: str
    row_unit: str
    min_rows: int
    template: str
    # Set for the guide scenario: it runs as the guide agent, and this turns that agent's server
    # log, read against the config's target, into the verdict table.
    grade: Callable[[str, Config], str] | None = None

    def prompt(self, config: Config) -> str:
        """Fill in the run's own coordinates.

        Args:
            config: The harness config.

        Returns:
            The prompt to hand the agent.
        """
        inventory = '\n'.join(
            f'- `{prefix}_*` — {purpose}' for prefix, purpose in agent.SERVERS.values()
        )
        return self.template.format(
            servers=inventory,
            summary=_SUMMARY.format(heading=SUMMARY_HEADING, unit=self.row_unit).strip(),
            cluster=config.cluster_identifier,
            workgroup=config.workgroup_name,
            guide_workgroup=config.guide_workgroup_name,
            database=config.database,
            schema=config.schema,
        )


_ENVIRONMENT = """
You have the Redshift MCP server available at several configurations, each running the working \
tree you are testing. Every configuration exposes the same tools, distinguished by prefix, so \
`ro_execute_query` and `rw_execute_query` are the same tool at two configurations:
{servers}

Two warehouses are provisioned and seeded with the TICKIT sample schema `{schema}` in database \
`{database}`: provisioned cluster `{cluster}` and Serverless workgroup `{workgroup}`. Both hold \
the same tables, so a check that holds on one should hold on the other. Other clusters exist in \
this account; leave them alone.
"""

_SUMMARY = """
End your reply with a section that begins on its own line with `{heading}` and holds nothing but,
in this order:

1. A markdown table with the columns Scenario, Result and Comment. One row per {unit}. Result is
   PASS or FAIL. Leave Comment empty unless there is something to say.
2. Only if anything is worth noting, a short bulleted list under the table.

This section is lifted into a committed report and read on its own, so keep every row
intelligible without the rest of the reply.
"""

BRANCH = Scenario(
    key='branch',
    title='Changes on this branch',
    row_unit='scenario',
    # A floor, not an expectation: the case list is the agent's to derive, so a number it has to
    # match would go stale with the next change. This only rejects a table too short to have
    # covered the surface at all. Runs so far produce 26 rows here and 7 on `tools`.
    min_rows=8,
    template=_ENVIRONMENT
    + """
Run an end-to-end test covering the scenarios for the changes introduced in the current branch \
only. Scope is the committed branch diff AND the uncommitted working-tree changes, so read \
`git status` and `git diff` as well as the branch commits: the newest behaviour may not be \
committed yet. Get the test scenario ideas from the unit tests under the project directory.

Some of the branch behaviour appears only when the AWS principal is denied a specific IAM \
action, which is what the denied configurations above are for. Work out from the diff and the \
unit tests what each tool should do under those credentials, and verify it. Verify too that \
behaviour under the configurations that are not denied it is unchanged.

{summary}
""",
)

TOOLS = Scenario(
    key='tools',
    title='Every tool, both warehouse types',
    row_unit='tool',
    # Per BRANCH. One row per tool, and there are eight.
    min_rows=8,
    template=_ENVIRONMENT
    + """
Run a complete set of end-to-end tests covering all of the server's tools. Check both the \
provisioned cluster and the Serverless workgroup, including the database schema exploration in \
both. Check the SQL read-only protection, the transaction breaker protection, and failed user \
SQL behaviour. Get the test scenario ideas from the unit tests under the project directory.

{summary}
""",
)


def _grade_guide(log: str, config: Config) -> str:
    """Grade the guide scenario from its server log, whose lines are in the order calls ran.

    The prompt names a target whose id says nothing of its type, and every tool that names a
    target takes its type and refuses the wrong one. So the type counts as taken from
    list_clusters when list_clusters answered before the first call naming the target, and no
    call naming it was refused for its type. The run is not interactive: an agent that asks for
    the type gets no answer, so it either never names the target or guesses, and a wrong guess is
    refused.

    Args:
        log: The server log of the run, empty if the server wrote none.
        config: The harness config, which names the target.

    Returns:
        A verdict table, one row per check.
    """
    lines = log.splitlines()
    target = re.escape(config.guide_workgroup_name)

    # Each pattern matches the line the server logs for one kind of call or outcome.
    def first(pattern: str) -> int | None:
        return next((i for i, line in enumerate(lines) if re.search(pattern, line)), None)

    def before(earlier: str, later: str) -> bool:
        at, then = first(earlier), first(later)
        return at is not None and then is not None and at < then

    # Each chunk served logs `chunk <n> of <count>`, so a reference read in part misses a line.
    served = set(
        re.findall(r'Serving skill file (references/\S+) chunk (\d+) of (\d+)$', log, re.M)
    )
    whole = {(file, str(n), of) for file, _, of in served for n in range(1, int(of) + 1)}

    passed = {
        'Guide retrieved with no argument before the first query': before(
            r'Serving skill file SKILL\.md', target
        ),
        # list_clusters' answer: the other tools' success lines end naming a cluster.
        "Target's type taken from list_clusters, not asked for or guessed wrong": before(
            r'Successfully retrieved \d+ clusters$', target
        )
        and first(f'cluster named {target} was found') is None,
        'Reference files loaded unprompted, each in full': bool(served) and served == whole,
    }
    table = ['| Check | Result |', '|---|---|']
    table += [f'| {name} | {"PASS" if ok else "FAIL"} |' for name, ok in passed.items()]

    return 'Graded by the harness from the server log.\n\n' + '\n'.join(table)


GUIDE = Scenario(
    key='guide',
    title='The guide, unprompted',
    row_unit='check',
    # Exact: the harness writes this table, one row per check.
    min_rows=3,
    template="""
Which tables in database `{database}` on my Redshift warehouse `{guide_workgroup}` take up the \
most space, and how much of that space could be reclaimed?
""",
    grade=_grade_guide,
)

ALL = {scenario.key: scenario for scenario in (BRANCH, TOOLS, GUIDE)}
