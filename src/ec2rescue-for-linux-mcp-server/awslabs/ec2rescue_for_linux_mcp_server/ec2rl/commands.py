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

"""ec2rl command construction primitives and allowlist validators."""

from __future__ import annotations

import re
from awslabs.ec2rescue_for_linux_mcp_server.ec2rl.registry import EC2RL_MODULES
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from awslabs.ec2rescue_for_linux_mcp_server.ec2rl.module import Ec2rlModule


EC2RL_OUTPUT_BASE_DIR = '/var/tmp/ec2rl'

# Base ec2rl command pattern (without module name and args)
_EC2RL_RUN_PREFIX = 'ec2rl run --only-modules='
_EC2RL_SOFTWARE_CHECK_CMD = 'ec2rl software-check'

# Module-level ec2rl flag required when running a `perfimpact: True` module.
# We hard-code the literal so command construction and allowlist validation
# stay in lock-step; expand to a set if more global flags are introduced.
_PERFIMPACT_FLAG = '--perfimpact=true'

# Allowed characters in argument values: alphanumeric, dot, hyphen, underscore, slash
_ARG_VALUE_RE = re.compile(r'^[A-Za-z0-9._/\-]+$')
# Allowed module names: alphanumeric, hyphen, underscore
_IDENTIFIER_RE = re.compile(r'^[A-Za-z0-9_\-]+$')
# Allowed argument keys: like an identifier but must start alphanumeric, since
# a key is interpolated into `--<key>=` and a leading hyphen would produce
# `---key=`.
_ARG_KEY_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_\-]*$')

# journalctl --since=/--until= args (journal, kernelpanic, hungtasks, etc.).
_TIME_ARG_KEYS = frozenset({'since', 'until'})
# systemd.time charset: default set plus ':' and '+' for single-token forms
# like 13:00:00 and +1h. No space — ec2rl runs `$CMD` unquoted, so a value
# with a space (e.g. "2012-10-30 18:17:16") word-splits and loses the time.
_TIME_ARG_VALUE_RE = re.compile(r'^[A-Za-z0-9:+._/\-]+$')


def validate_arg_value(key: str, value: str) -> bool:
    """True if ``value`` is allowed for argument ``key`` (time args get ':'/'+')."""
    if key in _TIME_ARG_KEYS:
        return bool(_TIME_ARG_VALUE_RE.fullmatch(value))
    return bool(_ARG_VALUE_RE.fullmatch(value))


# ec2rl's output dir timestamp: `strftime('%Y-%m-%dT%H_%M_%S.%f')`, e.g.
# `2026-04-14T02_50_34.749027`. This segment is target-controlled, so pin the
# exact shape rather than accept a loose one.
_TIMESTAMP_RE = (
    r'\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])'
    r'T(?:[01]\d|2[0-3])_[0-5]\d_[0-5]\d\.\d{1,6}'
)
_OUTPUT_DIR_RE = re.compile(rf'^{re.escape(EC2RL_OUTPUT_BASE_DIR)}/{_TIMESTAMP_RE}$')
# `tail -n <N>` line count: 1..9999999, bounded so an absurd count can't be
# smuggled in.
_TAIL_COUNT_RE = r'[1-9][0-9]{0,6}'

# gathered path segment: alnum/_/./- with leading dot allowed (e.g.
# `.placeholder`); the lookahead rejects `.`/`..` so traversal stays blocked.
_GATHERED_SEG = r'(?:/(?!\.\.?(?:/|$))[A-Za-z0-9_.][A-Za-z0-9_.\-]*)+'

# Read-back paths are target-controlled and cat/tail/grep follow symlinks, so
# each read-back command is prefixed with a `[ ! -L <path> ] && ` guard. The
# guard path and the reader path are the same backreferenced token, so the
# guarded path and the read path can't differ.
_NO_SYMLINK_GROUP = 'readpath'


def _no_symlink_guard(path: str) -> str:
    """Return ``[ ! -L <path> ] && `` -- refuse to read a symlinked path."""
    return f'[ ! -L {path} ] && '


def _no_symlink_re(path_pattern: str) -> str:
    """Guard fragment capturing the path for the reader to backreference."""
    return rf'\[ ! -L (?P<{_NO_SYMLINK_GROUP}>{path_pattern}) \] && '


def _read_path_backref() -> str:
    """Backreference to the path captured by :func:`_no_symlink_re`."""
    return rf'(?P={_NO_SYMLINK_GROUP})'


_MOD_OUT_LOG_PATH = (
    rf'{re.escape(EC2RL_OUTPUT_BASE_DIR)}/{_TIMESTAMP_RE}'
    r'/mod_out/run/[A-Za-z0-9_\-]+\.log'
)
_GATHERED_FILE_PATH = (
    rf'{re.escape(EC2RL_OUTPUT_BASE_DIR)}/{_TIMESTAMP_RE}'
    r'/gathered_out/[A-Za-z0-9_\-]+'
    rf'{_GATHERED_SEG}'
)

# `cat <mod_out log>` — non-gathered modules.
_MOD_OUT_LOG_RE = re.compile(rf'^{_no_symlink_re(_MOD_OUT_LOG_PATH)}cat {_read_path_backref()}$')
# `tail -n <N> <mod_out log>` — append-only logs (e.g. dmesg).
_MOD_OUT_TAIL_RE = re.compile(
    rf'^{_no_symlink_re(_MOD_OUT_LOG_PATH)}tail -n {_TAIL_COUNT_RE} '
    rf'{_read_path_backref()}$'
)
# `cat <gathered file>`.
_GATHERED_READ_CMD_RE = re.compile(
    rf'^{_no_symlink_re(_GATHERED_FILE_PATH)}cat {_read_path_backref()}$'
)
# `tail -n <N> <gathered file>` — append-only gathered logs (e.g. messages).
_GATHERED_TAIL_CMD_RE = re.compile(
    rf'^{_no_symlink_re(_GATHERED_FILE_PATH)}tail -n {_TAIL_COUNT_RE} '
    rf'{_read_path_backref()}$'
)
# `find <gathered_out>/<module> -type f ! -type l` — list gathered files.
# `! -type l` drops symlinks so a planted one is never listed then read back.
_GATHERED_LIST_CMD_RE = re.compile(
    rf'^find {re.escape(EC2RL_OUTPUT_BASE_DIR)}/{_TIMESTAMP_RE}'
    r'/gathered_out/[A-Za-z0-9_\-]+ -type f ! -type l$'
)
# `grep -hE '^(KEY1|...)=' <gathered file>` — return only caller-supplied keys
# (e.g. kernelconfig CONFIG_* settings). Keys are bare identifiers.
_GATHERED_GREP_CMD_RE = re.compile(
    rf"^{_no_symlink_re(_GATHERED_FILE_PATH)}grep -hE '\^\("
    r'[A-Za-z0-9_]+(?:\|[A-Za-z0-9_]+)*'
    r"\)=' "
    rf'{_read_path_backref()}$'
)
# `grep -vE '^[[:space:]]*#' <gathered file>` — strip comment lines from
# comment-heavy config files (e.g. sysctlconf, nsswitch).
_GATHERED_NOCOMMENT_CMD_RE = re.compile(
    rf"^{_no_symlink_re(_GATHERED_FILE_PATH)}grep -vE '\^\[\[:space:\]\]\*#' "
    rf'{_read_path_backref()}$'
)
# `grep -hE '^(K1|...)[ \t]*=' <mod_out log>` — sysctl-style keys with dots.
_LOG_SYSCTL_GREP_CMD_RE = re.compile(
    rf"^{_no_symlink_re(_MOD_OUT_LOG_PATH)}grep -hE '\^\("
    r'[A-Za-z0-9_.]+(?:\|[A-Za-z0-9_.]+)*'
    r"\)\[ \\t\]\*=' "
    rf'{_read_path_backref()}$'
)
# `grep -hF -e K1 -e K2 ... <mod_out log> || true` — fixed-string grep on
# collect-class logs (e.g. dpkgpackages). `|| true` runs after the reader.
_LOG_FIXED_GREP_CMD_RE = re.compile(
    rf'^{_no_symlink_re(_MOD_OUT_LOG_PATH)}grep -hF'
    r'(?: -e [A-Za-z0-9_.+\-]+)+'
    r' '
    rf'{_read_path_backref()} \|\| true$'
)


def validate_log_read_command(command: str) -> bool:
    """True if ``command`` is an allowed read of an ec2rl output location.

    Accepts:

    * Legacy ``cat <output_dir>/mod_out/run/<name>.log`` form.
    * ``tail -n <N> <output_dir>/mod_out/run/<name>.log`` for append-only logs.
    * ``cat <output_dir>/gathered_out/<module>/<rel>`` for gathered modules.
    * ``tail -n <N> <output_dir>/gathered_out/<module>/<rel>`` for append-only
      gathered logs (e.g. messages, yumlog).
    * ``find <output_dir>/gathered_out/<module> -type f`` for listing
      gathered files when the caller wants to discover paths.
    * ``grep -hE '^(KEY1|KEY2|...)=' <gathered file>`` for extracting only
      caller-supplied keys (e.g. kernelconfig CONFIG_* settings).
    * ``grep -vE '^[[:space:]]*#' <gathered file>`` for stripping comment
      lines from config files (e.g. sysctlconf, nsswitch).
    * ``grep -hF -e K1 -e K2 ... <mod_out log> || true`` for fixed-string
      grep on collect-class logs (e.g. dpkgpackages, rpmpackages).
    """
    return bool(
        _MOD_OUT_LOG_RE.fullmatch(command)
        or _MOD_OUT_TAIL_RE.fullmatch(command)
        or _GATHERED_READ_CMD_RE.fullmatch(command)
        or _GATHERED_TAIL_CMD_RE.fullmatch(command)
        or _GATHERED_LIST_CMD_RE.fullmatch(command)
        or _GATHERED_GREP_CMD_RE.fullmatch(command)
        or _LOG_SYSCTL_GREP_CMD_RE.fullmatch(command)
        or _GATHERED_NOCOMMENT_CMD_RE.fullmatch(command)
        or _LOG_FIXED_GREP_CMD_RE.fullmatch(command)
    )


# Matches: ec2rl software-check | grep -i '<package>' || true
# where <package> is a single identifier (alnum/_/-).
_SOFTWARE_CHECK_CMD_RE = re.compile(
    rf'^{re.escape(_EC2RL_SOFTWARE_CHECK_CMD)}'
    r" \| grep -i '(?P<pkg>[A-Za-z0-9_\-]+)' \|\| true$"
)
# Matches: which <binary>
# where <binary> is a known software binary name (alnum/_/./- starting with alnum/_).
# The caller uses SSM exit code (0 = found, non-zero = not found) rather than
# parsing stdout, which varies across OSes and can include login shell noise.
_WHICH_BINARY_CHECK_CMD_RE = re.compile(r'^which (?P<binary>[A-Za-z0-9_][A-Za-z0-9_.\-]*)$')


def _validate_software_check_command(
    command: str,
    registry: dict[str, 'Ec2rlModule'],
) -> bool:
    """True if ``command`` is a grep-filtered software-check for a known package."""
    match = _SOFTWARE_CHECK_CMD_RE.fullmatch(command)
    if not match:
        return False
    pkg = match.group('pkg')
    return any(module.package == pkg for module in registry.values())


def _validate_which_binary_command(
    command: str,
    registry: dict[str, 'Ec2rlModule'],
) -> bool:
    """True if ``command`` is a ``which <binary>`` check for a known module's software."""
    match = _WHICH_BINARY_CHECK_CMD_RE.fullmatch(command)
    if not match:
        return False
    binary = match.group('binary')
    return any(module.software == binary for module in registry.values())


def validate_command(
    command: str,
    modules: dict[str, 'Ec2rlModule'] | None = None,
) -> bool:
    """True if ``command`` is an allowed ec2rl run/software-check/log-read form.

    ``modules`` defaults to :data:`EC2RL_MODULES`.
    """
    if not command:
        return False
    if validate_log_read_command(command):
        return True

    registry = modules if modules is not None else EC2RL_MODULES

    if _validate_software_check_command(command, registry):
        return True

    if _validate_which_binary_command(command, registry):
        return True

    if not command.startswith(_EC2RL_RUN_PREFIX):
        return False

    remainder = command[len(_EC2RL_RUN_PREFIX) :]
    tokens = remainder.split(' ')
    if not tokens:
        return False

    module_name = tokens[0]
    module = registry.get(module_name)
    if module is None:
        return False

    # Validate remaining tokens as --key=value pairs with allowed keys/values.
    # The literal `--perfimpact=true` flag is also accepted (only on
    # perfimpact-flagged modules) — it's a module-level ec2rl flag, not a
    # per-argument key. Reject the flag when the module isn't perfimpact so
    # tampering can't sneak it onto arbitrary modules.
    allowed_keys = set(module.required_args) | set(module.optional_args)
    for token in tokens[1:]:
        if token == _PERFIMPACT_FLAG:
            if not module.perfimpact:
                return False
            continue
        if not token.startswith('--'):
            return False
        kv = token[2:]
        if '=' not in kv:
            return False
        key, _, value = kv.partition('=')
        if not _ARG_KEY_RE.fullmatch(key):
            return False
        if key not in allowed_keys:
            return False
        if not validate_arg_value(key, value):
            return False
    return True
