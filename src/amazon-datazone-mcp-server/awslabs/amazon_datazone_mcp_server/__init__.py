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

"""AWS DataZone MCP Server."""

import os
from pathlib import Path

# Read version from VERSION file
_version_file = Path(__file__).parent.parent.parent / 'VERSION'
if _version_file.exists():
    try:
        __version__ = _version_file.read_text().strip()
    except FileNotFoundError:  # pragma: no cover
        __version__ = 'unknown'
else:
    __version__ = 'unknown'

__all__ = ['__version__']