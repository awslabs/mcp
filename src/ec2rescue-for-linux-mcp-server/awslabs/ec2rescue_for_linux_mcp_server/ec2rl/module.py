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

"""Runtime representation of one ec2rl YAML module."""

from __future__ import annotations

import re
from awslabs.ec2rescue_for_linux_mcp_server.ec2rl.commands import (
    _ARG_KEY_RE,
    _EC2RL_RUN_PREFIX,
    _EC2RL_SOFTWARE_CHECK_CMD,
    _GATHERED_GREP_CMD_RE,
    _GATHERED_LIST_CMD_RE,
    _GATHERED_NOCOMMENT_CMD_RE,
    _GATHERED_READ_CMD_RE,
    _GATHERED_TAIL_CMD_RE,
    _IDENTIFIER_RE,
    _LOG_FIXED_GREP_CMD_RE,
    _LOG_SYSCTL_GREP_CMD_RE,
    _MOD_OUT_TAIL_RE,
    _OUTPUT_DIR_RE,
    _PERFIMPACT_FLAG,
    _no_symlink_guard,
    validate_arg_value,
)
from awslabs.ec2rescue_for_linux_mcp_server.ec2rl.registry import GATHEREDDIR_FILES


# Bounds size and control characters only. Text within the allowed charset can
# still read as an instruction; that is handled where it is used, in
# execution._render_helptext_block.
_MAX_HELPTEXT_LEN = 500


def _sanitize_helptext(helptext: str) -> str:
    """Replace control characters in helptext with spaces and cap its length."""
    # Dropping a newline would join the words either side of it ("output.For").
    cleaned = ''.join(c if c == ' ' or c.isprintable() else ' ' for c in helptext)
    return ' '.join(cleaned.split())[:_MAX_HELPTEXT_LEN]


def _validate_arg_keys(module_name: str, keys: list[str] | None) -> list[str]:
    """Return the arg-key list, rejecting any key that is not a plain identifier.

    Argument keys are interpolated into ``--<key>=<value>`` on the command
    line, so a key with shell metacharacters or a leading hyphen would break
    out of the intended flag.
    """
    result = list(keys) if keys else []
    for key in result:
        if not isinstance(key, str) or not _ARG_KEY_RE.fullmatch(key):
            raise ValueError(f'Invalid argument key for module {module_name!r}: {key!r}')
    return result


class Ec2rlModule:
    """An ec2rl diagnostic module loaded from a ``mod.d/`` YAML file."""

    # Binary names: alnum, hyphen, underscore, dot (must start with alnum/_).
    _SOFTWARE_BINARY_RE = re.compile(r'^[A-Za-z0-9_][A-Za-z0-9_.\-]*$')

    def __init__(
        self,
        name: str,
        log_subpath: str,
        *,
        title: str = '',
        helptext: str = '',
        required_args: list[str] | None = None,
        optional_args: list[str] | None = None,
        remediation: bool = False,
        constraint_class: str = '',
        domain: str = '',
        package: str = '',
        software: str = '',
        perfimpact: bool = False,
    ):
        """Initialize from YAML fields; raises ValueError on unsafe fields."""
        if not _IDENTIFIER_RE.fullmatch(name):
            raise ValueError(f'Invalid module name: {name!r}')
        self.name = name
        self.log_subpath = log_subpath
        self.title = title
        self.helptext = _sanitize_helptext(helptext)
        self.required_args = _validate_arg_keys(name, required_args)
        self.optional_args = _validate_arg_keys(name, optional_args)
        self.remediation = remediation
        self.constraint_class = constraint_class
        self.domain = domain
        self.perfimpact = perfimpact

        if package and not _IDENTIFIER_RE.fullmatch(package):
            raise ValueError(f'Invalid package name for module {name!r}: {package!r}')
        self.package = package

        if software and not self._SOFTWARE_BINARY_RE.fullmatch(software):
            raise ValueError(f'Invalid software binary for module {name!r}: {software!r}')
        self.software = software

    @property
    def run_command(self) -> str:
        """Base ec2rl command; use :meth:`build_run_command` for args."""
        return f'{_EC2RL_RUN_PREFIX}{self.name}'

    def build_run_command(
        self,
        args: dict[str, str] | None = None,
        extra_flags: list[str] | None = None,
    ) -> str:
        """Return ``ec2rl run --only-modules=<name> [--k=v ...] [extra_flags]``.

        ``extra_flags`` is reserved for module-level ec2rl flags that aren't
        per-argument key=value pairs (currently only ``--perfimpact=true``).
        Each flag is matched against an explicit allowlist; unknown flags
        raise ValueError so we can't smuggle arbitrary tokens into the SSM
        command line.

        Raises ValueError on missing required args, unknown keys, unsafe
        chars in keys/values, or disallowed extra_flags.
        """
        args = args or {}

        for key in self.required_args:
            if key not in args or args[key] in (None, ''):
                raise ValueError(f'Missing required argument {key!r} for module {self.name!r}')

        allowed_keys = set(self.required_args) | set(self.optional_args)
        for key in args:
            if key not in allowed_keys:
                raise ValueError(f'Unknown argument {key!r} for module {self.name!r}')

        parts = [f'{_EC2RL_RUN_PREFIX}{self.name}']
        # Preserve YAML declaration order: required first, then optional
        for key in list(self.required_args) + list(self.optional_args):
            if key not in args:
                continue
            value = args[key]
            if value is None or value == '':
                continue
            if not _IDENTIFIER_RE.fullmatch(key):
                raise ValueError(f'Invalid argument key: {key!r}')
            if not isinstance(value, str) or not validate_arg_value(key, value):
                raise ValueError(f'Invalid value for argument {key!r}: {value!r}')
            parts.append(f'--{key}={value}')

        for flag in extra_flags or ():
            if flag != _PERFIMPACT_FLAG:
                raise ValueError(f'Disallowed extra ec2rl flag: {flag!r}')
            parts.append(flag)

        return ' '.join(parts)

    def software_check_command(self) -> str:
        """Return ``ec2rl software-check | grep -i <package> || true``.

        Grep-filters on the instance so the SSM response stays small.
        ``|| true`` forces exit 0 when grep finds no match (presence of
        output is the signal, not exit code). Raises ValueError if this
        module has no declared package.
        """
        if not self.package:
            raise ValueError(f'software_check_command called on package-less module {self.name!r}')
        return f"{_EC2RL_SOFTWARE_CHECK_CMD} | grep -i '{self.package}' || true"

    def is_package_missing(self, stdout: str) -> bool:
        """True if the grep-filtered software-check stdout mentions our package.

        ``ec2rl software-check`` reports *missing* software, so any match
        after grep filtering means the package is not installed.
        """
        if not self.package:
            return False
        return self.package.lower() in stdout.lower()

    def software_binary_check_command(self) -> str:
        """Return ``which <binary>`` for PATH-based availability check.

        The caller determines presence from the SSM exit code (0 = found,
        1 = not found) rather than parsing stdout. Raises ValueError if no
        software binary set.
        """
        if not self.software:
            raise ValueError(
                f'software_binary_check_command called on module without '
                f'software binary: {self.name!r}'
            )
        return f'which {self.software}'

    def log_read_command(self, output_dir: str, tail_lines: int | None = None) -> str:
        """Return ``cat <output_dir>/<log_subpath>``, or ``tail -n N`` of it.

        When ``tail_lines`` is a positive int, only the last N lines are read
        (append-only logs like ``dmesg``); otherwise the whole file is cat-ed.
        The generated command is re-validated against its allowlist.
        """
        if not _OUTPUT_DIR_RE.fullmatch(output_dir):
            raise ValueError(f'Invalid ec2rl output directory: {output_dir}')
        path = f'{output_dir}/{self.log_subpath}'
        if tail_lines is None:
            return f'{_no_symlink_guard(path)}cat {path}'
        if not isinstance(tail_lines, int) or tail_lines < 1:
            raise ValueError(f'Invalid tail line count: {tail_lines!r}')
        cmd = f'{_no_symlink_guard(path)}tail -n {tail_lines} {path}'
        if not _MOD_OUT_TAIL_RE.fullmatch(cmd):
            raise ValueError(f'Invalid log tail command for module {self.name!r}')
        return cmd

    def gathered_read_commands(
        self,
        output_dir: str,
        files: list[str] | None = None,
        tail_lines: int | None = None,
    ) -> list[tuple[str, str]]:
        """Return [(relative_path, read_command), ...] for this module's gathered files.

        Args:
            output_dir: ec2rl run output directory (e.g.
                ``/var/tmp/ec2rl/2026-...``).
            files: When provided, use these relative paths instead of the
                curated :data:`GATHEREDDIR_FILES` entry. Useful when the
                caller (AI) discovered file names via :meth:`gathered_list_command`.
            tail_lines: When a positive int, read only the last N lines of each
                file via ``tail -n N`` (append-only logs like ``messages``,
                ``yumlog``); otherwise each file is cat-ed in full.

        Returns empty list when neither ``files`` nor :data:`GATHEREDDIR_FILES`
        contains paths. Validates ``output_dir`` against :data:`_OUTPUT_DIR_RE`
        and re-checks each generated command against its allowlist.

        Raises:
            ValueError: If ``output_dir`` is malformed, ``tail_lines`` is not a
                positive int, or any relative path produces a command that
                fails allowlist validation (e.g. contains ``..``).
        """
        if not _OUTPUT_DIR_RE.fullmatch(output_dir):
            raise ValueError(f'Invalid ec2rl output directory: {output_dir}')
        if tail_lines is not None and (not isinstance(tail_lines, int) or tail_lines < 1):
            raise ValueError(f'Invalid tail line count: {tail_lines!r}')
        rels = files if files is not None else list(GATHEREDDIR_FILES.get(self.name, ()))
        cmds: list[tuple[str, str]] = []
        for rel in rels:
            path = f'{output_dir}/gathered_out/{self.name}/{rel}'
            if tail_lines is None:
                cmd, pattern = f'{_no_symlink_guard(path)}cat {path}', _GATHERED_READ_CMD_RE
            else:
                cmd = f'{_no_symlink_guard(path)}tail -n {tail_lines} {path}'
                pattern = _GATHERED_TAIL_CMD_RE
            if not pattern.fullmatch(cmd):
                raise ValueError(f'Invalid gathered file path for module {self.name!r}: {rel!r}')
            cmds.append((rel, cmd))
        return cmds

    def is_valid_gathered_relpath(self, output_dir: str, rel_path: str) -> bool:
        """True if ``rel_path`` produces an allowlisted gathered ``cat`` command."""
        path = f'{output_dir}/gathered_out/{self.name}/{rel_path}'
        cmd = f'{_no_symlink_guard(path)}cat {path}'
        return bool(_GATHERED_READ_CMD_RE.fullmatch(cmd))

    def gathered_list_command(self, output_dir: str) -> str:
        """Return ``find <output_dir>/gathered_out/<name> -type f ! -type l``.

        Lists gathered files when the caller hasn't curated
        :data:`GATHEREDDIR_FILES` or supplied ``files``. ``! -type l`` excludes
        symlinks; the listing is untrusted, so each returned path is re-checked
        by :meth:`is_valid_gathered_relpath` before any read.
        """
        if not _OUTPUT_DIR_RE.fullmatch(output_dir):
            raise ValueError(f'Invalid ec2rl output directory: {output_dir}')
        cmd = f'find {output_dir}/gathered_out/{self.name} -type f ! -type l'
        if not _GATHERED_LIST_CMD_RE.fullmatch(cmd):
            raise ValueError(f'Invalid gathered list command: {cmd!r}')
        return cmd

    def gathered_grep_command(
        self,
        output_dir: str,
        rel_path: str,
        keys: list[str],
    ) -> str:
        """Return ``grep -hE '^(K1|K2|...)=' <gathered file>`` for one file.

        Each key must be an identifier (alnum/underscore). The keys list is
        deduplicated while preserving order, and at least one key is required.

        Useful when the gathered file is large and only specific configuration
        keys are interesting (e.g. kernel config CONFIG_* settings, sysctl).
        """
        if not _OUTPUT_DIR_RE.fullmatch(output_dir):
            raise ValueError(f'Invalid ec2rl output directory: {output_dir}')
        if not keys:
            raise ValueError('At least one key is required for gathered_grep_command')
        seen: set[str] = set()
        unique_keys: list[str] = []
        for key in keys:
            if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_]+', key):
                raise ValueError(f'Invalid grep key: {key!r}')
            if key not in seen:
                seen.add(key)
                unique_keys.append(key)
        pattern = '|'.join(unique_keys)
        path = f'{output_dir}/gathered_out/{self.name}/{rel_path}'
        cmd = f"{_no_symlink_guard(path)}grep -hE '^({pattern})=' {path}"
        if not _GATHERED_GREP_CMD_RE.fullmatch(cmd):
            raise ValueError(
                f'Invalid gathered grep command for module {self.name!r}: rel_path={rel_path!r}'
            )
        return cmd

    def log_sysctl_grep_command(self, output_dir: str, keys: list[str]) -> str:
        r"""Return ``grep -hE '^(K1|K2|...)[ \t]*=' <mod_out log>``.

        Used for collect-class modules whose log output is in ``key = value``
        format with dots in keys (e.g. ``sysctl -a`` output). The pattern
        allows optional whitespace before ``=``.
        """
        if not _OUTPUT_DIR_RE.fullmatch(output_dir):
            raise ValueError(f'Invalid ec2rl output directory: {output_dir}')
        if not keys:
            raise ValueError('At least one key is required for log_sysctl_grep_command')
        seen: set[str] = set()
        unique_keys: list[str] = []
        for key in keys:
            if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_.]+', key):
                raise ValueError(f'Invalid grep key: {key!r}')
            if key not in seen:
                seen.add(key)
                unique_keys.append(key)
        pattern = '|'.join(unique_keys)
        path = f'{output_dir}/mod_out/run/{self.name}.log'
        cmd = f"{_no_symlink_guard(path)}grep -hE '^({pattern})[ \\t]*=' {path}"
        if not _LOG_SYSCTL_GREP_CMD_RE.fullmatch(cmd):
            raise ValueError(f'Invalid log sysctl grep command for module {self.name!r}')
        return cmd

    def log_grep_command(self, output_dir: str, keys: list[str]) -> str:
        """Return ``grep -hF -e K1 -e K2 ... <mod_out log> || true``.

        Fixed-string grep on collect-class module logs. Each key is matched
        as a literal substring (no regex interpretation). The ``|| true``
        suffix ensures grep returning no matches (exit 1) does not cause SSM
        to report failure.
        """
        if not _OUTPUT_DIR_RE.fullmatch(output_dir):
            raise ValueError(f'Invalid ec2rl output directory: {output_dir}')
        if not keys:
            raise ValueError('At least one key is required for log_grep_command')
        seen: set[str] = set()
        unique_keys: list[str] = []
        for key in keys:
            if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_.+\-]+', key):
                raise ValueError(f'Invalid grep key: {key!r}')
            if key not in seen:
                seen.add(key)
                unique_keys.append(key)
        args = ' '.join(f'-e {k}' for k in unique_keys)
        path = f'{output_dir}/mod_out/run/{self.name}.log'
        cmd = f'{_no_symlink_guard(path)}grep -hF {args} {path} || true'
        if not _LOG_FIXED_GREP_CMD_RE.fullmatch(cmd):
            raise ValueError(f'Invalid log grep command for module {self.name!r}')
        return cmd

    def gathered_nocomment_command(self, output_dir: str, rel_path: str) -> str:
        """Return ``grep -vE '^[[:space:]]*#' <gathered file>`` to strip comments.

        Used for config files dominated by comments (e.g. ``/etc/sysctl.conf``,
        ``/etc/nsswitch.conf``). Empty lines are preserved; only comment lines
        — including those with leading whitespace — are removed.
        """
        if not _OUTPUT_DIR_RE.fullmatch(output_dir):
            raise ValueError(f'Invalid ec2rl output directory: {output_dir}')
        path = f'{output_dir}/gathered_out/{self.name}/{rel_path}'
        cmd = f"{_no_symlink_guard(path)}grep -vE '^[[:space:]]*#' {path}"
        if not _GATHERED_NOCOMMENT_CMD_RE.fullmatch(cmd):
            raise ValueError(
                f'Invalid gathered nocomment command for module {self.name!r}: '
                f'rel_path={rel_path!r}'
            )
        return cmd

    @staticmethod
    def parse_output_dir(stdout: str) -> str | None:
        """Extract the output dir path after 'output logs are located in'."""
        lines = stdout.splitlines()
        for i, line in enumerate(lines):
            if 'output logs are located in' in line.lower():
                for j in range(i + 1, len(lines)):
                    stripped = lines[j].strip()
                    if stripped:
                        if _OUTPUT_DIR_RE.fullmatch(stripped):
                            return stripped
                        break
        return None

    def __repr__(self) -> str:
        """Short repr with module name and remediation flag."""
        return f'Ec2rlModule(name={self.name!r}, remediation={self.remediation})'
