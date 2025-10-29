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

"""Script index schema model."""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ScriptIndex:
    """Schema for index.json structure."""

    version: str
    scripts: Dict[str, Dict[str, Any]]
    templates: Dict[str, Dict[str, Any]]
    metadata: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScriptIndex':
        """Load index from dictionary."""
        return cls(
            version=data.get('version', '1.0'),
            scripts=data.get('scripts', {}),
            templates=data.get('templates', {}),
            metadata=data.get('metadata', {}),
        )
