#!/usr/bin/env python3
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

"""Check that every server's `uv.lock` agrees with the `mcp` bound in its `pyproject.toml`.

Why this exists: `uv run pytest` resolves from `uv.lock`, not from `pyproject.toml`. A lock
that predates a cap change keeps installing the *old* SDK, so the suite passes against v1
while the manifest claims v2 -- a false PASS that looks like a successful migration. During
the fleet rollout this masked three servers (`aws-api`, `billing-cost-management`,
`dynamodb`) whose locks were still on mcp 1.x.

Run before trusting a green test run:

    python3 scripts/verify-mcp-v2-locks.py          # report
    python3 scripts/verify-mcp-v2-locks.py --strict  # exit 1 on any mismatch

Note that a mismatch is not always a stale lock: it can also mean the resolution is
genuinely unsatisfiable, e.g. a transitive dep pinning `mcp<2.0`. `uv lock` fails loudly in
that case, but only if you actually re-lock -- hence this check.
"""

import argparse
import re
import sys
import tomllib
from pathlib import Path
from typing import List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parent.parent

# `uv.lock` is TOML, but the files run to several thousand lines and we only need one field.
# A targeted regex over the `[[package]]` block for `mcp` is far cheaper than a full parse.
LOCK_MCP_RE = re.compile(r'^name = "mcp"\nversion = "([^"]+)"', re.MULTILINE)

# Matches the requirement string for the `mcp` distribution, with or without extras, in a
# PEP 508 dependency entry. Anchored on the name so `mcp-proxy-for-aws` and the "mcp"
# keyword in `keywords = [...]` do not match.
DEP_MCP_RE = re.compile(r'^mcp(\[[^\]]*\])?\s*(?P<spec>[<>=!~,\s\d.*]*)$')


def mcp_requirement(pyproject: Path) -> Optional[str]:
    """Return the `mcp` requirement string from a pyproject's dependency tables.

    Reads `project.dependencies` plus every `project.optional-dependencies` group. Returns
    None when the server does not depend on the SDK directly -- several servers reach it only
    through `fastmcp` or `mcp-proxy-for-aws`, and those are not this check's business.
    """
    data = tomllib.loads(pyproject.read_text())
    project = data.get('project', {})
    groups: List[str] = list(project.get('dependencies', []))
    for extra in project.get('optional-dependencies', {}).values():
        groups.extend(extra)
    for raw in groups:
        # Strip environment markers (`; python_version < "3.11"`) before matching.
        if DEP_MCP_RE.match(raw.split(';')[0].strip()):
            return raw.strip()
    return None


def locked_mcp_version(lock: Path) -> Optional[str]:
    """Return the `mcp` version pinned in a uv.lock, or None if absent from the graph."""
    if not lock.exists():
        return None
    match = LOCK_MCP_RE.search(lock.read_text())
    return match.group(1) if match else None


def audit() -> Tuple[List[Tuple[str, str, str]], List[Tuple[str, str, str]]]:
    """Classify every server as consistent or mismatched.

    Returns (mismatches, skipped). A mismatch is a server declaring `>=2.0.0` whose lock
    resolves to something outside 2.x -- including "not in the lock at all", which happens
    when the dependency was added to the manifest but never locked.
    """
    mismatches, skipped = [], []
    for pyproject in sorted((REPO_ROOT / 'src').glob('*/pyproject.toml')):
        server = pyproject.parent.name
        requirement = mcp_requirement(pyproject)
        if requirement is None:
            continue
        locked = locked_mcp_version(pyproject.parent / 'uv.lock')
        if '>=2.0.0' not in requirement:
            skipped.append((server, requirement, locked or 'not locked'))
        elif locked is None or not locked.startswith('2.'):
            mismatches.append((server, requirement, locked or 'not locked'))
    return mismatches, skipped


def main() -> int:
    """Report lock/manifest disagreements; optionally fail the build on any."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--strict', action='store_true', help='exit non-zero when any server mismatches'
    )
    args = parser.parse_args()

    mismatches, skipped = audit()

    if skipped:
        print(f'{len(skipped)} server(s) do not declare mcp>=2.0.0 (not checked):')
        for server, requirement, locked in skipped:
            print(f'  {server:<45} {requirement:<24} lock={locked}')
        print()

    if not mismatches:
        print('OK: every server declaring mcp>=2.0.0 has a 2.x lock.')
        return 0

    print(f'MISMATCH: {len(mismatches)} server(s) declare mcp>=2.0.0 but do not lock 2.x.')
    print('Test runs for these resolve the OLD SDK -- a green suite proves nothing.')
    for server, requirement, locked in mismatches:
        print(f'  {server:<45} {requirement:<24} lock={locked}')
    print('\nRe-lock with:  cd src/<server> && uv lock')
    print('If `uv lock` fails, the resolution is genuinely blocked (check for a')
    print('transitive dep pinning mcp<2.0) -- not a stale lock.')
    return 1 if args.strict else 0


if __name__ == '__main__':
    sys.exit(main())
