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

import frontmatter
from .models import Script
from pathlib import Path
from typing import Optional


class AgentScriptsManager:
    """Script manager for AWS API MCP."""

    _instance: Optional['AgentScriptsManager'] = None

    def __new__(cls) -> 'AgentScriptsManager':
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the manager (only once)."""
        self.scripts = {}
        self._scripts_dir = Path(__file__).parent / 'registry'

        if not self._scripts_dir.exists():
            raise RuntimeError(f'Scripts directory {self._scripts_dir} does not exist')

        for file_path in self._scripts_dir.glob('*.script.md'):
            with open(file_path, 'r') as f:
                metadata, script = frontmatter.parse(f.read())
                script_name = file_path.stem.removesuffix('.script')
                self.scripts[script_name] = Script(
                    name=script_name,
                    description=metadata.get('description'),
                    content=script,
                )

    def get_script(self, script_name: str) -> Optional[Script]:
        """Get a script from file."""
        if script_name not in self.scripts:
            return None

        return self.scripts[script_name]

    def pretty_print_scripts(self) -> str:
        """Pretty print all scripts."""
        return '\n'.join(
            [f'* {script.name} : {script.description}\n' for script in self.scripts.values()]
        )


AGENT_SCRIPTS_MANAGER = AgentScriptsManager()
