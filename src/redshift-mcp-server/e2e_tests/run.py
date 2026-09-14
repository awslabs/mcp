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

"""The harness's entry point.

    python -m e2e_tests.run status
    python -m e2e_tests.run up
    python -m e2e_tests.run test [branch|tools|all]
    python -m e2e_tests.run pause
    python -m e2e_tests.run down

`test` does the whole thing: brings the warehouses up, generates the agent config, runs each
scenario, writes a report per scenario, then applies the configured teardown. The other
commands are the same steps on their own, for when a run is being set up or cleaned up by hand.
"""

import argparse
import boto3
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from e2e_tests import agent, deploy, scenarios, tickit
from e2e_tests.config import HARNESS_ROOT, PACKAGE_ROOT, REPORTS_DIR, Config, ConfigError, load
from pathlib import Path


# kiro-cli draws progress as it goes, and none of it belongs in a committed report.
_ANSI = re.compile(r'\x1b\[[0-9;?]*[a-zA-Z]|\x1b\][^\x07]*\x07|[\r\x0b\x0c]')


def _session(config: Config):
    """Return a boto3 session for the configured profile and region.

    Args:
        config: The harness config.

    Returns:
        A boto3 Session.
    """
    return boto3.Session(profile_name=config.profile, region_name=config.region)


def _text(partial: str | bytes | None) -> str:
    """Return whatever a killed subprocess had already written, as text.

    A timeout gives back what was buffered, and it arrives as bytes even from a subprocess
    opened in text mode.

    Args:
        partial: Buffered output, or None if there was none.

    Returns:
        The output as text, replacing anything that will not decode.
    """
    if partial is None:
        return ''
    return partial.decode(errors='replace') if isinstance(partial, bytes) else partial


def _git(*args: str) -> str:
    """Read one fact about the working tree.

    Args:
        *args: Arguments to git.

    Returns:
        Its trimmed output, or the empty string if git fails.
    """
    result = subprocess.run(
        ['git', *args], cwd=PACKAGE_ROOT, capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else ''


def _revision() -> str:
    """Describe the code under test precisely enough to find it again.

    Returns:
        Branch and short commit, marked dirty when the tree carries uncommitted changes.
    """
    branch = _git('rev-parse', '--abbrev-ref', 'HEAD') or 'unknown'
    commit = _git('rev-parse', '--short', 'HEAD') or 'unknown'
    dirty = ', uncommitted changes' if _git('status', '--porcelain') else ''
    return f'`{branch}` at `{commit}`{dirty}'


def _invoke(config: Config, prompt: str) -> tuple[int, str, float]:
    """Run one scenario through the agent and collect everything it said.

    Invoked from the harness directory, because that is where kiro-cli looks for the agent the
    harness generated.

    Args:
        config: The harness config.
        prompt: The scenario prompt.

    Returns:
        Exit status, the transcript with control sequences stripped, and elapsed seconds.
    """
    # The model is named in the agent config, not here: passing both makes kiro-cli refuse the
    # flag ("failed to set model ... Method not found") and fall back to its default, which
    # would leave the report naming a model that never ran.
    command = [
        config.agent_command,
        'chat',
        '--agent',
        config.agent_name,
        '--no-interactive',
        '--trust-tools',
        agent.trust_argument(),
        prompt,
    ]

    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            cwd=HARNESS_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=config.timeout_seconds,
        )
        status, output = result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired as e:
        status = 124
        output = (
            f'{_text(e.stdout)}{_text(e.stderr)}\n\n'
            f'harness: no answer within {config.timeout_seconds}s, killed'
        )

    return status, _ANSI.sub('', output), time.monotonic() - started


def _as_paragraphs(text: str) -> str:
    """Separate lines so that markdown keeps them apart.

    The transcript arrives as consecutive lines, most of them one tool call each. Rendered as
    markdown those run together into a single paragraph, so each becomes its own.

    Args:
        text: Lines to separate.

    Returns:
        The same lines, one paragraph each.
    """
    return '\n\n'.join(line for line in text.splitlines() if line.strip())


def _split_summary(transcript: str) -> tuple[str | None, str]:
    """Separate the agent's summary from the rest of what it said.

    Found by searching rather than by matching a whole line, because the CLI streams one passage
    of prose straight into the next and the heading can arrive with text still on its left. Tool
    activity after the summary, which is usually cleanup, stays with the transcript.

    Args:
        transcript: What the agent said, control sequences already stripped.

    Returns:
        The summary, or None when the agent produced none, and the transcript without it.
    """
    cut = transcript.rfind(scenarios.SUMMARY_HEADING)
    if cut == -1:
        return None, _as_paragraphs(transcript)

    summary: list[str] = []
    trailing: list[str] = []

    for line in transcript[cut + len(scenarios.SUMMARY_HEADING) :].splitlines():
        if trailing or line.startswith('[tool]'):
            trailing.append(line)
        else:
            summary.append(line)

    return (
        '\n'.join(summary).strip(),
        _as_paragraphs('\n'.join([transcript[:cut], *trailing])),
    )


def _report(
    config: Config,
    scenario: scenarios.Scenario,
    prompt: str,
    status: int,
    transcript: str,
    seconds: float,
    seeded_rows: int,
) -> Path:
    """Write the run down, in the form it will be read in a pull request.

    The summary leads, because that is what a reader came for. The prompt follows, so a
    surprising row can be weighed against what was actually asked. The transcript is last, for
    whoever is checking one particular claim.

    Args:
        config: The harness config.
        scenario: The scenario that ran.
        prompt: The prompt it was given.
        status: The agent's exit status.
        transcript: What the agent said, control sequences already stripped.
        seconds: How long it took.
        seeded_rows: Rows in the sample schema, so a reader can tell the data was really there.

    Returns:
        Path to the written report.
    """
    now = datetime.now(timezone.utc)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f'{scenario.key}-{now:%Y%m%d-%H%M}.md'

    facts = {
        'Scenario': f'`{scenario.key}`',
        'Code under test': _revision(),
        'Agent': f'`{config.agent_command}`, model `{config.model}`',
        'Exit status': f'`{status}`' + ('' if status == 0 else ' — the agent did not finish'),
        'Duration': f'{seconds / 60:.1f} min',
        'Region': f'`{config.region}`',
        'Provisioned': (
            f'`{config.cluster_identifier}`, {config.node_type} x{config.number_of_nodes}'
        ),
        'Serverless': f'`{config.workgroup_name}`, {config.base_capacity} RPU',
        'Sample data': f'`{config.schema}` in `{config.database}`, {seeded_rows:,} rows each',
    }

    summary, remainder = _split_summary(transcript)
    if summary is None:
        summary = (
            'The agent ended without one, so nothing here has been summarised. Read the '
            'transcript before citing this run.'
        )

    path.write_text(
        f'# End-to-end test: {scenario.title}\n\n'
        f'{now:%Y-%m-%d %H:%M} UTC\n\n'
        + '\n'.join(f'- **{key}**: {value}' for key, value in facts.items())
        + '\n\n'
        f'## Summary\n\n{summary}\n\n'
        '## Prompt\n\n'
        "Written by the harness, not by hand. The agent derives the cases from the package's "
        'unit tests, and is told where to look rather than what to expect.\n\n'
        f'{prompt.strip()}\n\n'
        '## Transcript\n\n'
        f'{remainder.strip()}\n'
    )

    return path


def test(config: Config, keys: list[str], keep_up: bool) -> int:
    """Provision, run the named scenarios, report, and tear down.

    Args:
        config: The harness config.
        keys: Scenario keys to run, in order.
        keep_up: Skip teardown, leaving the warehouses running for the next run.

    Returns:
        A process exit status: zero only when every scenario finished cleanly.
    """
    session = _session(config)
    deploy.up(session, config)

    agent_path = agent.write(config, session.client('sts'))
    print(f'agent      {agent_path}')

    seeded_rows = sum(tickit.EXPECTED_ROWS.values())
    failures = 0

    for key in keys:
        scenario = scenarios.ALL[key]
        prompt = scenario.prompt(config)
        print(f'scenario   {key} running, up to {config.timeout_seconds / 60:.0f} min')

        status, transcript, seconds = _invoke(config, prompt)
        path = _report(config, scenario, prompt, status, transcript, seconds, seeded_rows)
        print(f'scenario   {key} exit {status} in {seconds / 60:.1f} min -> {path}')

        if status != 0:
            failures += 1

    if keep_up:
        print('lifecycle  left running, --keep-up was given')
    else:
        deploy.teardown(session, config)

    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    """Run one command.

    Args:
        argv: Arguments, defaulting to the process's own.

    Returns:
        A process exit status.
    """
    parser = argparse.ArgumentParser(prog='python -m e2e_tests.run', description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)

    for name, help_text in (
        ('status', 'report what exists, changing nothing'),
        ('up', 'create, resume, seed and grant'),
        ('pause', 'stop compute billing on the provisioned cluster'),
        ('down', 'delete everything the harness owns'),
    ):
        sub.add_parser(name, help=help_text)

    run = sub.add_parser('test', help='provision, run scenarios, write reports, tear down')
    run.add_argument(
        'scenario',
        nargs='?',
        default='all',
        choices=(*scenarios.ALL, 'all'),
        help='which scenario to run (default: all)',
    )
    run.add_argument(
        '--keep-up',
        action='store_true',
        help='skip teardown, so the next run does not pay to resume',
    )

    args = parser.parse_args(argv)

    try:
        config = load()
    except ConfigError as e:
        print(f'error: {e}', file=sys.stderr)
        return 2

    if args.command == 'test':
        keys = list(scenarios.ALL) if args.scenario == 'all' else [args.scenario]
        return test(config, keys, args.keep_up)

    session = _session(config)
    {'status': deploy.status, 'up': deploy.up, 'pause': deploy.pause, 'down': deploy.down}[
        args.command
    ](session, config)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
