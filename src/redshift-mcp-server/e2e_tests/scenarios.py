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
"""

from dataclasses import dataclass
from e2e_tests import agent
from e2e_tests.config import Config


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
    template: str

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
    template=_ENVIRONMENT
    + """
Run a complete set of end-to-end tests covering all of the server's tools. Check both the \
provisioned cluster and the Serverless workgroup, including the database schema exploration in \
both. Check the SQL read-only protection, the transaction breaker protection, and failed user \
SQL behaviour. Get the test scenario ideas from the unit tests under the project directory.

{summary}
""",
)

ALL = {scenario.key: scenario for scenario in (BRANCH, TOOLS)}
