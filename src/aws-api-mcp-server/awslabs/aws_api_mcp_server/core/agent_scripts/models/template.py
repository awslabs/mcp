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

"""Template model."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass
class Template:
    """Represents a configuration template."""

    name: str
    content: Dict[str, Any]
    path: Path
    description: str

    @classmethod
    def load(cls, file_path: Path) -> 'Template':
        """Load template from file."""
        with open(file_path, 'r') as f:
            template_content = json.load(f)

        template_name = file_path.stem
        description = template_content.get('_description', f'Template: {template_name}')

        # Remove metadata fields
        clean_content = {k: v for k, v in template_content.items() if not k.startswith('_')}

        return cls(
            name=template_name,
            content=clean_content,
            path=file_path,
            description=description,
        )

    def substitute_parameters(self, parameters: Dict[str, str]) -> str:
        """Return JSON string with parameters substituted."""
        # Convert template to JSON string
        template_json = json.dumps(self.content, indent=2)

        # Simple string replacement
        for param_name, param_value in parameters.items():
            placeholder = f'{{{param_name}}}'
            template_json = template_json.replace(placeholder, param_value)

        return template_json
