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


class AgentScriptsManager:
    """Script manager for AWS API MCP."""

    def __init__(self, scripts_dir: Path = Path(__file__).parent / 'registry'):
        """Initialize the manager."""
        self.scripts = {}
        self._scripts_dir = scripts_dir

        if not self._scripts_dir.exists():
            raise RuntimeError(f'Scripts directory {self._scripts_dir} does not exist')

        for file_path in self._scripts_dir.glob('*.script.md'):
            with open(file_path, 'r') as f:
                metadata, script = frontmatter.parse(f.read())
                script_name = file_path.stem.removesuffix('.script')
                description = metadata.get('description')

                if not description:
                    raise RuntimeError(
                        f'Script {file_path.stem} has no "description" metadata in front matter.'
                    )

                self.scripts[script_name] = Script(
                    name=script_name,
                    description=str(description),
                    content=script,
                )

    def get_script(self, script_name: str) -> Script | None:
        """Get a script from file."""
        return self.scripts.get(script_name)

    def pretty_print_scripts(self) -> str:
        """Pretty print all scripts."""
        return '\n'.join(
            [f'* {script.name} : {script.description}\n' for script in self.scripts.values()]
        )


AGENT_SCRIPTS_MANAGER = AgentScriptsManager()
