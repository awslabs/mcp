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
#   license-header

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

RED=$'\033[0;31m'
GRN=$'\033[0;32m'
YLW=$'\033[0;33m'
BLU=$'\033[0;34m'
RST=$'\033[0m'

ALL_STEPS=(precommit bandit uv-sync verify-names pytest pyright ruff-format ruff-check uv-build secrets-scanner semgrep license-header)
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

  print_summary

  # nonzero exit if any step recorded FAIL (only reachable with --no-fail-fast)
  for r in "${RESULTS[@]}"; do
    [[ "$r" == FAIL* ]] && exit 1
  done
}

main "$@"
