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

"""Move CHANGELOG `## Unreleased` entries under the release that shipped them.

The awslabs/mcp release bot bumps the version of every changed package in a
`chore: bump packages for release/...` commit, so the version an entry ships in
is only known after the fact. For each entry under `## Unreleased` this script
finds the commits that wrote its lines (`git blame -w -M`) and the first release
bump commit containing all of them, then moves the entry under a
`## [x.y.z] - YYYY-MM-DD` heading. Entries that have not shipped yet stay put.

Run from a branch that is up to date with `main` (and not a shallow clone), so
the latest release bump commits are in its history:

    python scripts/changelog_release.py          # rewrite CHANGELOG.md
    python scripts/changelog_release.py --check  # exit 1 if entries would move
"""

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent.parent
CHANGELOG = PACKAGE_DIR / 'CHANGELOG.md'
RELEASE_GREP = '^chore: bump packages for release/'
UNRELEASED_RE = re.compile(r'^## \[?Unreleased\]?\s*$', re.IGNORECASE)
VERSION_RE = re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)
UNCOMMITTED = '0' * 40


@dataclass(frozen=True)
class Release:
    """A release bump commit for this package."""

    sha: str
    date: str
    version: str

    @property
    def heading(self) -> str:
        """The CHANGELOG section heading for this release."""
        return f'## [{self.version}] - {self.date}'


@dataclass
class Entry:
    """A top-level bullet, its nested lines, and the `###` subsection it is under."""

    subsection: str | None
    lines: list[str] = field(default_factory=list)
    line_numbers: list[int] = field(default_factory=list)


def git(*args: str) -> str:
    """Run a git command in the package directory and return stdout."""
    return subprocess.run(
        ['git', *args], cwd=PACKAGE_DIR, check=True, capture_output=True, text=True
    ).stdout


def releases() -> list[Release]:
    """Return this package's releases, oldest first."""
    log = git('log', '--format=%H %cs', f'--grep={RELEASE_GREP}', '--', 'pyproject.toml')
    result = []
    for line in reversed(log.splitlines()):
        sha, date = line.split()
        match = VERSION_RE.search(git('show', f'{sha}:./pyproject.toml'))
        if match:
            result.append(Release(sha, date, match.group(1)))
    return result


def blame() -> list[str]:
    """Return the commit sha that last changed each line of CHANGELOG.md (0-indexed)."""
    porcelain = git('blame', '-w', '-M', '--line-porcelain', '--', CHANGELOG.name)
    return re.findall(r'^([0-9a-f]{40}) \d+ \d+', porcelain, re.MULTILINE)


@cache
def is_ancestor(commit: str, release: str) -> bool:
    """Return whether `commit` is contained in `release`."""
    return (
        subprocess.run(
            ['git', 'merge-base', '--is-ancestor', commit, release], cwd=PACKAGE_DIR
        ).returncode
        == 0
    )


def first_release(commit: str, all_releases: list[Release]) -> Release | None:
    """Return the earliest release containing `commit`, or None if unreleased."""
    if commit == UNCOMMITTED:
        return None
    return next((r for r in all_releases if is_ancestor(commit, r.sha)), None)


def section_end(lines: list[str], start: int) -> int:
    """Return the index of the next `## ` heading after `start`, or len(lines)."""
    return next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith('## ')), len(lines)
    )


def parse_entries(lines: list[str], start: int, end: int) -> tuple[list[str], list[Entry]]:
    """Split an Unreleased section body into preamble lines and bullet entries."""
    preamble: list[str] = []
    entries: list[Entry] = []
    subsection = None
    indent = None
    current = None
    for i in range(start, end):
        line = lines[i]
        stripped = line.lstrip()
        if line.startswith('### '):
            subsection, indent, current = line.strip(), None, None
            continue
        line_indent = len(line) - len(stripped)
        if stripped.startswith(('- ', '* ')) and (indent is None or line_indent <= indent):
            indent = line_indent if indent is None else indent
            current = Entry(subsection)
            entries.append(current)
        if current is not None:
            current.lines.append(line)
            current.line_numbers.append(i)
        elif stripped:
            preamble.append(line)
    for entry in entries:
        while entry.lines and not entry.lines[-1].strip():
            entry.lines.pop()
            entry.line_numbers.pop()
        top_indent = len(entry.lines[0]) - len(entry.lines[0].lstrip())
        entry.lines = [line[top_indent:] if line.strip() else '' for line in entry.lines]
    return preamble, entries


def render(entries: list[Entry]) -> list[str]:
    """Render entries, grouped under their `###` subsections in first-seen order."""
    out: list[str] = []
    order = list(dict.fromkeys(entry.subsection for entry in entries))
    for subsection in order:
        if subsection:
            out += [subsection, '']
        for entry in entries:
            if entry.subsection == subsection:
                out += entry.lines
        out.append('')
    return out


def merge_into(lines: list[str], release: Release, entries: list[Entry]) -> list[str]:
    """Insert entries into an existing section for `release`, or a new one after Unreleased."""
    heading_re = re.compile(rf'^## \[?v?{re.escape(release.version)}\]?(\s|$)')
    existing = next((i for i, line in enumerate(lines) if heading_re.match(line)), None)
    if existing is not None:
        end = section_end(lines, existing)
        while end > existing + 1 and not lines[end - 1].strip():
            end -= 1
        return lines[:end] + [''] + render(entries)[:-1] + lines[end:]
    unreleased = next(i for i, line in enumerate(lines) if UNRELEASED_RE.match(line))
    end = section_end(lines, unreleased)
    return lines[:end] + [release.heading, ''] + render(entries) + lines[end:]


def main() -> int:
    """Move released entries out of `## Unreleased`."""
    parser = argparse.ArgumentParser(description=(__doc__ or '').splitlines()[0])
    parser.add_argument('--check', action='store_true', help='exit 1 if any entry would be moved')
    args = parser.parse_args()

    lines = CHANGELOG.read_text().splitlines()
    start = next((i for i, line in enumerate(lines) if UNRELEASED_RE.match(line)), None)
    if start is None:
        print(f'No "## Unreleased" heading in {CHANGELOG}', file=sys.stderr)
        return 1
    end = section_end(lines, start)
    preamble, entries = parse_entries(lines, start + 1, end)

    all_releases = releases()
    shas = blame()
    keep: list[Entry] = []
    moved: dict[Release, list[Entry]] = {}
    for entry in entries:
        found = [first_release(shas[i], all_releases) for i in entry.line_numbers]
        shipped = [release for release in found if release is not None]
        if len(shipped) < len(found):
            keep.append(entry)
            continue
        # An entry ships with its newest line, so a later edit never backdates it.
        release = max(shipped, key=all_releases.index)
        moved.setdefault(release, []).append(entry)
        print(f'{release.version}: {entry.lines[0][:80]}')

    if not moved:
        print('Nothing to move; all Unreleased entries are unreleased.')
        return 0
    if args.check:
        return 1

    body = ([*preamble, ''] if preamble else []) + render(keep)
    lines = lines[: start + 1] + [''] + body + lines[end:]
    for release in sorted(moved, key=all_releases.index):
        lines = merge_into(lines, release, moved[release])
    CHANGELOG.write_text('\n'.join(lines).rstrip('\n') + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
