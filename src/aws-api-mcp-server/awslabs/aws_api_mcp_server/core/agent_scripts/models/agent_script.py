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

"""AgentScript model."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import frontmatter


@dataclass
class AgentScript:
    """Represents an agentic script with its metadata and content."""

    name: str
    content: str
    description: str
    parameters: Dict[str, Any]
    path: Path
    metadata: Dict[str, Any]

    @classmethod
    def load(cls, file_path: Path) -> 'AgentScript':
        """Load script from file."""
        with open(file_path, 'r') as f:
            metadata, content = frontmatter.parse(f.read())

        # Determine script name based on structure
        if file_path.name == 'main.script.md':
            # Modular structure: use parent directory name
            script_name = file_path.parent.name
        else:
            # Legacy flat structure: use filename without .script extension
            script_name = file_path.stem.removesuffix('.script')

        # Get parameters from frontmatter (YAML) - no regex parsing needed!
        parameters = metadata.get('parameters', {})

        return cls(
            name=script_name,
            content=content,
            description=metadata.get('description', f'Script: {script_name}'),
            parameters=parameters,
            path=file_path,
            metadata=metadata,
        )
