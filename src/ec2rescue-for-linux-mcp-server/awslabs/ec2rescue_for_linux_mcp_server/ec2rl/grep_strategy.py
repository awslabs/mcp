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

"""Per-module grep strategies for GREP_KEYS_MODULES dispatch."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GrepStrategy:
    """Base grep strategy — subclass to define per-module behavior."""

    key_pattern: str = r'[A-Za-z0-9_]+'
    key_description: str = 'alphanumeric/underscore identifier'


@dataclass(frozen=True)
class GatheredKvGrep(GrepStrategy):
    """grep -hE '^(K1|K2|...)=' on gathered_out files (e.g. kernelconfig)."""

    pass


@dataclass(frozen=True)
class LogSysctlGrep(GrepStrategy):
    r"""grep -hE '^(K1|K2|...)[ \t]*=' on mod_out/run/<name>.log (e.g. sysctl)."""

    key_pattern: str = r'[A-Za-z0-9_.]+'
    key_description: str = 'sysctl key (alphanumeric, underscore, dots)'


@dataclass(frozen=True)
class LogFixedGrep(GrepStrategy):
    """grep -hF -e K1 -e K2 on mod_out/run/<name>.log (e.g. package lists)."""

    key_pattern: str = r'[A-Za-z0-9_.+\-]+'
    key_description: str = 'package name (alphanumeric, dot, hyphen, plus)'
