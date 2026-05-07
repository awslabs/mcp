#!/usr/bin/env bash
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
#
# Local mirror of .github/workflows/python.yml + .github/workflows/pre-commit.yml
# for src/cloudwatch-applicationsignals-mcp-server. Run before `git push` to
# catch what CI would catch.
#
# Usage:
#   scripts/ci-check.sh              # run everything (fail-fast)
#   scripts/ci-check.sh --only pytest,ruff-check
#   scripts/ci-check.sh --skip precommit,bandit
#   scripts/ci-check.sh --list       # show step names
#   scripts/ci-check.sh --no-fail-fast
#
# Step names (ordered):
#   precommit, bandit, uv-sync, verify-names, pytest, pyright,
#   ruff-format, ruff-check, uv-build, secrets-scanner, semgrep,
#   license-header, codecov-project, codecov-patch

set -u
set -o pipefail

PKG="cloudwatch-applicationsignals-mcp-server"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PKG_DIR="$(cd -- "$SCRIPT_DIR/.." &>/dev/null && pwd)"
REPO_ROOT="$(cd -- "$PKG_DIR/../.." &>/dev/null && pwd)"
# Tool venv for CI-pinned scanners (detect-secrets, semgrep) that are not
# in the package's dev dependency group. Kept outside PKG_DIR so `uv build`
# doesn't try to pack the symlinks inside it into an sdist.
TOOL_VENV="${REPO_ROOT}/.venv-ci-tools-${PKG}"

# Codecov gate targets. Mirrors .github/codecov.yml: project status uses
# threshold: 1.0 (1.0 percentage-point drop tolerated). No patch: block in
# codecov.yml, so codecov defaults patch target to "auto" (== base project
# coverage) — we reproduce that here.
#
# Note: the remote codecov/project check is repo-wide (aggregates XMLs
# across every package). This local gate is package-scoped — it compares
# THIS package's combined line+branch coverage against CODECOV_BASE.
# To refresh the base after meaningful drift on main:
#   git checkout origin/main -- .
#   scripts/ci-check.sh --only pytest
#   scripts/ci-check.sh --only codecov-project  # read reported %, update below
# The metric sums (lines-covered + branches-covered) / (lines-valid +
# branches-valid) — this tracks slightly looser than codecov's per-line
# weighted metric but within ~1pp; a local pass is not a remote guarantee
# but a local fail always predicts a remote fail.
CODECOV_BASE="${CODECOV_BASE:-94.5}"
CODECOV_THRESHOLD="${CODECOV_THRESHOLD:-1.0}"
CODECOV_BASE_BRANCH="${CODECOV_BASE_BRANCH:-origin/main}"

RED=$'\033[0;31m'
GRN=$'\033[0;32m'
YLW=$'\033[0;33m'
BLU=$'\033[0;34m'
RST=$'\033[0m'

ALL_STEPS=(precommit bandit uv-sync verify-names pytest pyright ruff-format ruff-check uv-build secrets-scanner semgrep license-header codecov-project codecov-patch)
ONLY=""
SKIP=""
FAIL_FAST=1

die() { printf '%s[ci-check]%s %s\n' "$RED" "$RST" "$*" >&2; exit 1; }
info() { printf '%s[ci-check]%s %s\n' "$BLU" "$RST" "$*"; }
warn() { printf '%s[ci-check]%s %s\n' "$YLW" "$RST" "$*"; }
ok()   { printf '%s[ci-check]%s %s\n' "$GRN" "$RST" "$*"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --only)  ONLY="$2"; shift 2 ;;
    --skip)  SKIP="$2"; shift 2 ;;
    --list)
      printf 'steps:\n'
      for s in "${ALL_STEPS[@]}"; do printf '  - %s\n' "$s"; done
      exit 0
      ;;
    --no-fail-fast) FAIL_FAST=0; shift ;;
    -h|--help)
      sed -n '16,30p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) die "unknown arg: $1 (try --help)" ;;
  esac
done

should_run() {
  local name="$1"
  if [[ -n "$ONLY" ]]; then
    [[ ",$ONLY," == *",$name,"* ]] || return 1
  fi
  if [[ -n "$SKIP" ]]; then
    [[ ",$SKIP," == *",$name,"* ]] && return 1
  fi
  return 0
}

declare -a RESULTS
run_step() {
  local name="$1"; shift
  if ! should_run "$name"; then
    info "skip    $name"
    RESULTS+=("SKIP  $name")
    return 0
  fi
  info "start   $name"
  local t0
  t0=$(date +%s)
  if "$@"; then
    local dt=$(( $(date +%s) - t0 ))
    ok "ok      $name (${dt}s)"
    RESULTS+=("OK    $name (${dt}s)")
    return 0
  else
    local rc=$?
    local dt=$(( $(date +%s) - t0 ))
    warn "failed  $name (${dt}s, rc=$rc)"
    RESULTS+=("FAIL  $name (${dt}s, rc=$rc)")
    if [[ $FAIL_FAST -eq 1 ]]; then
      print_summary
      die "aborting on first failure (use --no-fail-fast to continue)"
    fi
    return $rc
  fi
}

print_summary() {
  printf '\n%s=== ci-check summary ===%s\n' "$BLU" "$RST"
  for r in "${RESULTS[@]}"; do printf '  %s\n' "$r"; done
}

require() {
  command -v "$1" >/dev/null 2>&1 || die "missing required tool: $1"
}

# Install a hash-pinned CI requirements file into $TOOL_VENV. Matches the
# GitHub Actions install pattern so tool versions line up exactly with CI.
# Usage: ensure_tool_venv <requirements-filename-in-.github/workflows>
ensure_tool_venv() {
  require uv
  local req_file="$REPO_ROOT/.github/workflows/$1"
  [[ -f "$req_file" ]] || die "missing CI requirements file: $req_file"

  if [[ ! -x "$TOOL_VENV/bin/python" ]]; then
    info "creating tool venv at $TOOL_VENV"
    uv venv --python 3.10 "$TOOL_VENV" >/dev/null
  fi

  # Reinstall only when the requirements file is newer than our sentinel.
  local sentinel="$TOOL_VENV/.installed-$1"
  if [[ ! -f "$sentinel" || "$req_file" -nt "$sentinel" ]]; then
    info "installing $1 into tool venv"
    VIRTUAL_ENV="$TOOL_VENV" uv pip install --require-hashes --requirement "$req_file" >/dev/null
    touch "$sentinel"
  fi
}

# --- step implementations ---

step_precommit() {
  # Mirrors .github/workflows/pre-commit.yml: runs from the directory holding
  # .pre-commit-config.yaml (repo root for this package). Uses the package's
  # dev-group pre-commit; CI pins via pre-commit-requirements.txt but that's
  # a second-order concern for local iteration.
  require uv
  local precommit_bin="$PKG_DIR/.venv/bin/pre-commit"
  if [[ ! -x "$precommit_bin" ]]; then
    die "pre-commit not installed in .venv — run: $0 --only uv-sync"
  fi
  ( cd "$REPO_ROOT" && "$precommit_bin" run --show-diff-on-failure --color=always --all-files )
}

step_bandit() {
  # CI installs from bandit-requirements.txt with --require-hashes; the dev
  # group pins bandit>=1.8.6 so `uv run` is close enough for a dev loop.
  require uv
  ( cd "$PKG_DIR" && uv run --frozen bandit -r \
      --severity-level medium \
      --confidence-level medium \
      -f html \
      -o "bandit-report-${PKG}.html" \
      -c "pyproject.toml" \
      . )
}

step_uv_sync() {
  require uv
  ( cd "$PKG_DIR" && uv sync --frozen --all-extras --dev )
}

step_verify_names() {
  require python3
  require uv
  ( cd "$REPO_ROOT" \
      && python3 scripts/verify_package_name.py "src/${PKG}" \
      && uv run --script scripts/verify_awslabs_init.py "src/${PKG}" \
      && ( python3 scripts/verify_tool_names.py "src/${PKG}" || true ) )
}

step_pytest() {
  require uv
  ( cd "$PKG_DIR" && uv run --frozen pytest \
      --cov --cov-branch \
      --cov-report=term-missing \
      --cov-report=xml:"${PKG}-coverage.xml" \
      --junitxml="${PKG}-junit.xml" \
      -o junit-family=legacy )
}

step_pyright() {
  require uv
  ( cd "$PKG_DIR" && uv run --frozen pyright )
}

step_ruff_format() {
  # CI runs `ruff format .` (not --check); this writes changes. Mirror that
  # here so local behavior matches. The follow-up `git diff --quiet` surfaces
  # drift the way CI's implicit "no modifications" invariant does.
  require uv
  ( cd "$PKG_DIR" \
      && uv run --frozen ruff format . \
      && ( git -C "$REPO_ROOT" diff --quiet -- "src/${PKG}" \
           || { warn "ruff format produced changes — stage & review"; git -C "$REPO_ROOT" -P diff --stat -- "src/${PKG}"; return 1; } ) )
}

step_ruff_check() {
  require uv
  ( cd "$PKG_DIR" && uv run --frozen ruff check . )
}

step_uv_build() {
  require uv
  ( cd "$PKG_DIR" && uv build )
}

step_secrets_scanner() {
  # Mirrors .github/workflows/scanners.yml — detect-secrets scan against the
  # repo-level .secrets.baseline, then jq assertion that no result is
  # flagged true/unknown.
  require jq
  ensure_tool_venv detect-secrets-requirements.txt
  ( cd "$REPO_ROOT" \
      && "$TOOL_VENV/bin/detect-secrets" scan --baseline .secrets.baseline \
      && jq '[.results|to_entries|.[].value[]|{ "filename": .filename, "is_secret": .is_secret } | if .is_secret == null or .is_secret == true then .filename else empty end]|unique|if length>0 then error("potential secrets in: \(.)") else empty end' \
         .secrets.baseline >/dev/null )
}

step_semgrep() {
  # Mirrors .github/workflows/semgrep.yml. `--no-error --dryrun` matches CI so
  # findings produce a SARIF artifact but don't fail the build. SARIF is
  # written into PKG_DIR/build/ (gitignored) rather than repo root so it
  # doesn't clutter `git status`.
  ensure_tool_venv semgrep-requirements.txt
  mkdir -p "$PKG_DIR/build"
  ( cd "$REPO_ROOT" \
      && "$TOOL_VENV/bin/semgrep" scan \
           --config auto \
           --sarif-output "$PKG_DIR/build/semgrep.sarif.json" \
           --no-error --dryrun )
}

step_license_header() {
  # Lightweight local mirror of .github/workflows/check-license-header.yml —
  # that workflow runs viperproject/check-license-header (JS), which we can't
  # invoke cleanly. Instead: parse the JSON config, resolve each rule's
  # license-header file, and walk the covered paths asserting the file
  # starts with that header. Rules with a null `license` key cover
  # excluded file types and are skipped.
  require python3
  python3 - "$REPO_ROOT" <<'PY'
import json
import os
import pathlib
import sys

repo = pathlib.Path(sys.argv[1])
cfg_path = repo / '.github/workflows/check-license-header.json'
cfg = json.loads(cfg_path.read_text())

import re

def _glob_to_regex(pattern: str) -> re.Pattern:
    # Translate a Node-style glob into a regex. Key differences from
    # fnmatch: "**" matches any run of path segments (including zero),
    # "*" matches within a single segment, and path separators are
    # respected. This avoids pathlib.PurePath.match's quirk where
    # a trailing "**" won't match an empty tail.
    out = []
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if pattern[i:i+3] == '**/':
            out.append('(?:.*/)?')
            i += 3
        elif pattern[i:i+3] == '/**':
            out.append('(?:/.*)?')
            i += 3
        elif c == '*':
            out.append('[^/]*')
            i += 1
        elif c == '?':
            out.append('[^/]')
            i += 1
        elif c in '.+()|^$[]{}\\':
            out.append(re.escape(c))
            i += 1
        else:
            out.append(c)
            i += 1
    return re.compile('^' + ''.join(out) + '$')

_REGEX_CACHE: dict[str, re.Pattern] = {}

def matches(rel: str, patterns) -> bool:
    for p in patterns:
        rx = _REGEX_CACHE.get(p)
        if rx is None:
            rx = _glob_to_regex(p)
            _REGEX_CACHE[p] = rx
        if rx.match(rel):
            return True
    return False

# Dependency/build dirs we never descend into even if the user's config
# forgets to list them. The CI JS action skips these by default.
PRUNE = {'.venv', 'node_modules', '.git', 'dist', 'build', '__pycache__', '.pytest_cache', '.ruff_cache', 'site-packages'}
# Prefixes of directory names to skip at any depth (e.g. our own tool venv
# at repo root: `.venv-ci-tools-<pkg>`, plus any other `.venv-*` variants).
PRUNE_PREFIXES = ('.venv-',)

def walk_files(root: pathlib.Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames
            if d not in PRUNE and not d.startswith(PRUNE_PREFIXES)
        ]
        for fn in filenames:
            yield pathlib.Path(dirpath) / fn

failures = []
checked = 0
for rule in cfg:
    license_path = rule.get('license')
    if not license_path:
        continue
    header = (repo / license_path).read_text()
    includes = rule.get('include') or ['**/*']
    excludes = rule.get('exclude') or []

    for path in walk_files(repo):
        rel = str(path.relative_to(repo))
        if not matches(rel, includes):
            continue
        if matches(rel, excludes):
            continue
        try:
            head = path.read_text(encoding='utf-8', errors='replace')[: len(header) + 1024]
        except Exception:
            continue
        checked += 1
        if header.strip() not in head:
            failures.append(rel)

if failures:
    print(f'checked {checked} file(s); missing/outdated header in {len(failures)}:', file=sys.stderr)
    for f in failures[:20]:
        print(f'  {f}', file=sys.stderr)
    if len(failures) > 20:
        print(f'  ... and {len(failures) - 20} more', file=sys.stderr)
    sys.exit(1)
print(f'license headers OK ({checked} files checked)')
PY
}

step_codecov_project() {
  # Local mirror of the codecov/project gate. Reads the cobertura XML that
  # step_pytest produced and compares overall line coverage against
  # CODECOV_BASE with CODECOV_THRESHOLD percentage-point tolerance. Mirrors
  # .github/codecov.yml `coverage.status.project.default.threshold: 1.0`.
  require python3
  local xml="$PKG_DIR/${PKG}-coverage.xml"
  [[ -f "$xml" ]] || die "missing coverage xml at $xml — run step pytest first"

  python3 - "$xml" "$CODECOV_BASE" "$CODECOV_THRESHOLD" <<'PY'
import sys
import xml.etree.ElementTree as ET

xml_path, base_s, threshold_s = sys.argv[1], sys.argv[2], sys.argv[3]
base = float(base_s)
threshold = float(threshold_s)
tree = ET.parse(xml_path)
root = tree.getroot()

# Use line-rate + branch-rate weighted by respective totals to approximate
# codecov's combined line+branch metric, matching the pre-push signal with
# what codecov/project actually enforces.
lv = int(root.attrib.get('lines-valid', '0'))
lc = int(root.attrib.get('lines-covered', '0'))
bv = int(root.attrib.get('branches-valid', '0'))
bc = int(root.attrib.get('branches-covered', '0'))

total = lv + bv
covered = lc + bc
pct = 100.0 * covered / total if total else 0.0
floor = base - threshold

print(f'project coverage: {pct:.2f}%  (lines {lc}/{lv}, branches {bc}/{bv})')
print(f'base:             {base:.2f}%')
print(f'threshold:        {threshold:.2f}pp  => floor {floor:.2f}%')

if pct + 1e-9 < floor:
    print(f'FAIL: project coverage {pct:.2f}% below floor {floor:.2f}%', file=sys.stderr)
    sys.exit(1)
print('OK: project coverage within threshold')
PY
}

step_codecov_patch() {
  # Local mirror of the codecov/patch gate. Computes coverage of lines
  # changed vs $CODECOV_BASE_BRANCH (origin/main by default) and compares
  # against CODECOV_BASE with CODECOV_THRESHOLD tolerance, matching
  # codecov's default patch target of "auto" (== project target) when
  # no patch: block is present in .github/codecov.yml.
  require python3
  require git
  local xml="$PKG_DIR/${PKG}-coverage.xml"
  [[ -f "$xml" ]] || die "missing coverage xml at $xml — run step pytest first"

  # Ensure the base ref is reachable for git diff. If not fetched, surface
  # a clear error rather than a confusing empty diff.
  if ! git -C "$REPO_ROOT" rev-parse --verify -q "$CODECOV_BASE_BRANCH" >/dev/null; then
    die "base ref '$CODECOV_BASE_BRANCH' not found — run: git fetch origin main"
  fi

  # Capture the unified=0 diff of the package dir. u=0 removes all context
  # so only true changed lines land in the python parser below.
  local diff_tmp rc
  diff_tmp="$(mktemp -t codecov-patch-diff.XXXXXX)"
  git -C "$REPO_ROOT" diff --unified=0 "$CODECOV_BASE_BRANCH"...HEAD -- "src/$PKG" > "$diff_tmp"

  python3 - "$xml" "$diff_tmp" "src/$PKG" "$CODECOV_BASE" "$CODECOV_THRESHOLD" <<'PY'
import os
import re
import sys
import xml.etree.ElementTree as ET

xml_path, diff_path, pkg_rel, base_s, threshold_s = sys.argv[1:6]
base = float(base_s)
threshold = float(threshold_s)

# --- 1. Parse diff: collect {file_relpath: set(changed_line_numbers)} ---
file_re = re.compile(r'^\+\+\+ b/(.+)$')
hunk_re = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@')
changed: dict[str, set[int]] = {}
current_file = None
current_newline = 0
remaining = 0
with open(diff_path) as f:
    for line in f:
        m = file_re.match(line)
        if m:
            current_file = m.group(1)
            if current_file != '/dev/null' and current_file not in changed:
                changed[current_file] = set()
            continue
        m = hunk_re.match(line)
        if m:
            current_newline = int(m.group(1))
            remaining = int(m.group(2)) if m.group(2) is not None else 1
            continue
        if remaining > 0 and line.startswith('+') and not line.startswith('+++'):
            if current_file and current_file != '/dev/null':
                changed[current_file].add(current_newline)
            current_newline += 1
            remaining -= 1
        elif remaining > 0 and not line.startswith('-') and not line.startswith('\\'):
            # context line under u=0 shouldn't happen; ignore defensively
            current_newline += 1
            remaining -= 1

# Restrict to .py under pkg_rel/awslabs/; tests aren't measured in
# coverage.run.source. Strip the full "src/<pkg>/awslabs/" prefix since
# pyproject.toml has source = ["awslabs"] which stores coverage paths
# relative to awslabs/ (so the XML keys look like
# "cloudwatch_applicationsignals_mcp_server/rum_tools.py").
PKG_SRC_PREFIX = f'{pkg_rel}/awslabs/'
patch_files = {
    f[len(PKG_SRC_PREFIX):]: lines for f, lines in changed.items()
    if f.startswith(PKG_SRC_PREFIX) and f.endswith('.py') and lines
}

if not patch_files:
    print('no patch lines under coverage source — nothing to gate')
    sys.exit(0)

# --- 2. Parse coverage xml into per-file {line: (covered_units, total_units)}
#        where a plain line is (hit, 1) and a branch line is
#        (covered_conditions, total_conditions). Mirrors how codecov weights
#        partial branches when computing patch coverage.
tree = ET.parse(xml_path)
root = tree.getroot()

# condition-coverage looks like "50% (1/2)"; pull the "(x/y)" pair out.
_COND_RE = re.compile(r'\((\d+)/(\d+)\)')

cov_lines: dict[str, dict[int, tuple[int, int]]] = {}
for cls in root.iter('class'):
    fn = cls.attrib.get('filename', '')
    per: dict[int, tuple[int, int]] = {}
    for ln in cls.iter('line'):
        try:
            num = int(ln.attrib['number'])
            hits = int(ln.attrib.get('hits', '0'))
        except (KeyError, ValueError):
            continue
        if ln.attrib.get('branch') == 'true':
            m = _COND_RE.search(ln.attrib.get('condition-coverage', ''))
            if m:
                per[num] = (int(m.group(1)), int(m.group(2)))
                continue
        per[num] = (1 if hits > 0 else 0, 1)
    cov_lines[fn] = per

# --- 3. Intersect and compute ---
total = 0
covered = 0
per_file_report = []
for f, lines in sorted(patch_files.items()):
    hits_map = cov_lines.get(f)
    if hits_map is None:
        # File may not be in coverage source (e.g. __init__.py excluded
        # from ruff.lint but still compiled — or a new file not yet
        # picked up by coverage.run.source).
        continue
    exec_lines = [ln for ln in lines if ln in hits_map]
    if not exec_lines:
        continue
    f_total = sum(hits_map[ln][1] for ln in exec_lines)
    f_covered = sum(hits_map[ln][0] for ln in exec_lines)
    total += f_total
    covered += f_covered
    per_file_report.append((f, f_covered, f_total))

if total == 0:
    print('no executable patch lines under coverage — nothing to gate')
    sys.exit(0)

pct = 100.0 * covered / total
floor = base - threshold

for f, c, t in per_file_report:
    file_pct = 100.0 * c / t
    print(f'  {f}: {file_pct:6.2f}%  ({c}/{t})')

print(f'patch coverage:   {pct:.2f}%  (lines {covered}/{total})')
print(f'base:             {base:.2f}%')
print(f'threshold:        {threshold:.2f}pp  => floor {floor:.2f}%')

if pct + 1e-9 < floor:
    print(f'FAIL: patch coverage {pct:.2f}% below floor {floor:.2f}%', file=sys.stderr)
    sys.exit(1)
print('OK: patch coverage within threshold')
PY
  rc=$?
  rm -f "$diff_tmp"
  return $rc
}

main() {
  info "package : $PKG"
  info "pkg_dir : $PKG_DIR"
  info "repo    : $REPO_ROOT"
  [[ -n "$ONLY" ]] && info "only    : $ONLY"
  [[ -n "$SKIP" ]] && info "skip    : $SKIP"
  info "fail-fast=$FAIL_FAST"
  echo

  run_step precommit       step_precommit
  run_step bandit          step_bandit
  run_step uv-sync         step_uv_sync
  run_step verify-names    step_verify_names
  run_step pytest          step_pytest
  run_step pyright         step_pyright
  run_step ruff-format     step_ruff_format
  run_step ruff-check      step_ruff_check
  run_step uv-build        step_uv_build
  run_step secrets-scanner step_secrets_scanner
  run_step semgrep         step_semgrep
  run_step license-header  step_license_header
  run_step codecov-project step_codecov_project
  run_step codecov-patch   step_codecov_patch

  print_summary

  # nonzero exit if any step recorded FAIL (only reachable with --no-fail-fast)
  for r in "${RESULTS[@]}"; do
    [[ "$r" == FAIL* ]] && exit 1
  done
}

main "$@"
