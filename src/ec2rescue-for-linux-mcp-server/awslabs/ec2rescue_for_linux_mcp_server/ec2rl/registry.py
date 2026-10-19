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

"""Curated registries for ec2rl modules: discovered modules, log-read overrides, and gathered file maps."""

from __future__ import annotations

from awslabs.ec2rescue_for_linux_mcp_server.ec2rl.grep_strategy import (
    GatheredKvGrep,
    GrepStrategy,
    LogFixedGrep,
    LogSysctlGrep,
)
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from awslabs.ec2rescue_for_linux_mcp_server.ec2rl.module import Ec2rlModule


# Python modules whose run() returns False (any reason: issue detected
# or internal exception). ec2rl exits non-zero in both cases, but the
# log file still has the useful detail; server reads it and sets
# `detected_issue: true`. Audit a new Python module's run() return paths
# before adding it here; bash modules trap errors and exit 0 so they
# don't belong.
READ_LOG_ON_NONZERO_EXIT_MODULES: frozenset[str] = frozenset(
    {
        'arpcache',
        'arpignore',
        'asymmetricroute',
        'conntrackfull',
        'consoleoverload',
        'duplicatefslabels',
        'duplicatefsuuid',
        'duplicatepartuuid',
        'enadiag',
        'fstabfailures',
        'hungtasks',
        'ixgbevfversion',
        'kernelbug',
        'kerneldereference',
        'kernelpanic',
        'kpti',
        'oomkiller',
        'openssh',
        'rebuildinitrd',
        'retpoline',
        'selinuxpermissive',
        'softlockup',
        'tcprecycle',
        'udevpersistentnet',
        'xennetrocket',
        'xennetsgmtu',
    }
)


# Modules that write output via $EC2RL_GATHEREDDIR/<name>/ rather than
# mod_out/run/<name>.log. Values are file paths relative to
# <output_dir>/gathered_out/<module>/.
#
# Each value has one of these meanings:
#
# * ``()`` (empty tuple) — server returns a `find` listing of available
#   files under `available_files`; the user/AI is expected to re-invoke
#   the tool with `gathered_files=[...]` to read specific files. Use this
#   when filenames are distro/runtime dependent (atophistory, kernelconfig,
#   udev, etc.) or when the file set is too varied to curate.
#
# * ``('a', 'b/c')`` (specific paths) — server cats exactly these files,
#   in order. Missing files are reported in `missing_files`.
#
# * ``('*',)`` (the read-all sentinel) — server runs `find ... -type f`
#   first to discover every file under the module's gathered_out
#   directory, then cats them all (e.g. cron, sysctlconf where the file
#   set is small but the names aren't statically known).
#
# A module that is intentionally absent from this dict (atophistory, gcore,
# nvidiabugreport, perf, sarhistory, sosreport, supportconfig, tcpdump)
# falls through to the default `mod_out/run/<name>.log` flow — used for
# modules whose gathered_out artifact is binary (atop history, core dump,
# perf.data, .tar.xz archive, .pcap, sysstat binary, etc.) and can't be
# cat'd safely into a JSON response. Only the module's run-log (its stdout
# notification) is returned.
GATHEREDDIR_FILES: dict[str, tuple[str, ...]] = {
    'aptlog': ('history.log', 'dpkg.log'),
    'cloudinitlog': ('cloud-init.log', 'cloud-init-output.log'),
    'collectlhistory': (),
    'cron': ('*',),
    'dhclientleases': (),
    'dmesgfiles': ('dmesg',),
    'environment': ('environment',),
    'fstab': ('fstab',),
    'hosts': ('hosts',),
    'httpdlogs': (),
    'inittab': ('inittab',),
    'kerberosconfig': ('krb5.conf',),
    'kernelconfig': (),
    'libtirpcnetconfig': ('netconfig',),
    'ltrace': ('ltrace.out',),
    'lvmarchive': (),
    'lvmconf': ('lvm.conf',),
    'messages': (),
    'mysqldlog': (),
    'nginxlogs': (),
    'nsswitch': ('nsswitch.conf',),
    'ntpconf': ('ntp.conf',),
    'profile': ('profile',),
    'resolvconf': ('resolv.conf',),
    'strace': ('strace.out',),
    'sysctlconf': ('*',),  # /etc/sysctl.conf + /etc/sysctl.d/*
    'systemsmanager': (),
    'udev': (),
    'workspacelogs': (),
    'yumlog': ('yum.log',),
    'zypperlog': (),
}


def is_gathered_module(name: str) -> bool:
    """True if the module writes to $EC2RL_GATHEREDDIR rather than mod_out/run."""
    return name in GATHEREDDIR_FILES


# Curated set of commonly-used modules registered by default to keep
# context consumption low (32 tools vs 209). Use ``--all`` to register
# every module, or ``--modules=name1,name2`` to add specific extras.
DEFAULT_MODULES: frozenset[str] = frozenset(
    {
        # System basics
        'cpuinfo',
        'meminfo',
        'kernelversion',
        'osrelease',
        'lsblk',
        'mounts',
        'ps',
        # Network
        'ifconfig',
        'iproute',
        'netstatanp',
        'ethtool',
        'resolvconf',
        'dig',
        # Logs
        'journal',
        'dmesg',
        'messages',
        'cloudinitlog',
        # Kernel / boot issues
        'kernelpanic',
        'hungtasks',
        'oomkiller',
        'softlockup',
        'fstabfailures',
        'kernelcmdline',
        'lsmod',
        # Performance
        'iostat',
        'vmstat',
        'top',
        'sysctl',
        # Packages / config
        'dpkgpackages',
        'rpmpackages',
        'kernelconfig',
        'fstab',
    }
)


# Modules that require caller-supplied grep keys. Maps module name →
# GrepStrategy instance that controls command construction, key validation,
# and target file location.
GREP_KEYS_MODULES: dict[str, GrepStrategy] = {
    'kernelconfig': GatheredKvGrep(),
    'sysctl': LogSysctlGrep(),
    'dpkgpackages': LogFixedGrep(),
    'rpmpackages': LogFixedGrep(),
}

# Modules whose gathered files are dominated by comments (e.g. config files)
# — strip lines matching ``^[[:space:]]*#`` before returning. Empty lines
# are preserved.
STRIP_COMMENTS_MODULES: set[str] = {
    'hosts',
    'inittab',
    'lvmconf',
    'nsswitch',
    'ntpconf',
    'sysctlconf',
}

# Modules whose output is typically very large and may consume significant
# context. The elicitation gate warns the user before proceeding. The value
# is the warning message shown to the user; mention alternatives when they
# exist.
LARGE_OUTPUT_MODULES: dict[str, str] = {
    'messages': (
        "Module 'messages' gathers all /var/log/messages* or /var/log/syslog* "
        'files, which can be very large and consume significant context. '
        "Consider using 'journal' module instead with --since= and --until= "
        "to limit the time range (e.g. since='1 hour ago'). "
        'Confirm to proceed with fetching all messages anyway.'
    ),
    'dmesg': (
        "Module 'dmesg' collects the entire kernel ring buffer, which can be "
        "large. Consider using 'journal' module with --since= and --until= "
        'to retrieve kernel messages for a specific time range '
        "(e.g. since='1 hour ago'). "
        'Confirm to proceed with fetching the full dmesg output anyway.'
    ),
}


# Append-only log modules: return only the last N lines by default (newest
# entries) to avoid flooding the context. Maps module name → default line
# count; callers override via the tool's ``tail_lines`` (0 = full output).
# `journal` is intentionally excluded — it already bounds output via its own
# --since/--until args.
TAIL_MODULES: dict[str, int] = {
    'messages': 100,
    'dmesg': 100,
    'yumlog': 100,
    'aptlog': 100,
    'cloudinitlog': 100,
    'httpdlogs': 100,
    'nginxlogs': 100,
    'mysqldlog': 100,
    'systemsmanager': 100,
    'workspacelogs': 100,
    'zypperlog': 100,
}


# --- Default module registry (empty until populated by main()) ---
EC2RL_MODULES: dict[str, Ec2rlModule] = {}
