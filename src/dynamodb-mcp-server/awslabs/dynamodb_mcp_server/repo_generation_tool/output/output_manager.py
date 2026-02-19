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

"""Output management for generated code files."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class GeneratedFile:
    """Represents a single generated file."""

    path: str  # Relative path: "entities.py" or "models/UserProfile.java"
    description: str  # Human description: "5 entities" or "UserProfile entity"
    category: str  # File category: "entities", "repositories", "config", "examples"
    content: str = ''  # Complete file content (for new approach)
    count: int = 0  # Optional count for summary


@dataclass
class GenerationResult:
    """Contains all generated code and metadata."""

    generated_files: list[GeneratedFile]  # List of all files created
    access_pattern_mapping: dict[str, Any]
    generator_type: str


class OutputManager:
    """Manages all output operations for generated code."""

    def __init__(self, output_dir: str, language: str = 'python'):
        """Initialize the output manager with target directory and language."""
        self.output_path = Path(output_dir)
        self.language = language
        self.output_path.mkdir(parents=True, exist_ok=True)

    def write_generated_files(self, generation_result: GenerationResult) -> None:
        """Write all generated files in one coordinated operation."""
        # Write files from manifest
        for file in generation_result.generated_files:
            if file.content:  # Files with content - write directly
                self._write_file(file.path, file.content)
            else:  # Files without content - copy from source
                self._copy_support_file(file.path)

        # Always write the access pattern mapping
        self._write_mapping_file(
            generation_result.access_pattern_mapping, generation_result.generator_type
        )

        self._print_summary(generation_result)

    def _write_mapping_file(
        self, access_pattern_mapping: dict[str, Any], generator_type: str
    ) -> None:
        """Write access_pattern_mapping.json."""
        mapping_file = self.output_path / 'access_pattern_mapping.json'
        with open(mapping_file, 'w') as f:
            json.dump(
                {
                    'metadata': {
                        'generated_at': {'timestamp': 'auto-generated'},
                        'total_patterns': len(access_pattern_mapping),
                        'generator_type': generator_type,
                    },
                    'access_pattern_mapping': access_pattern_mapping,
                },
                f,
                indent=2,
            )
            f.write('\n')  # Add trailing newline for pre-commit compatibility

    def _write_file(self, file_path: str, content: str) -> None:
        """Write a single file with content - language agnostic."""
        output_file = self.output_path / file_path

        # Create parent directories if they don't exist (for nested paths like "models/UserProfile.java")
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            f.write(content)
            if not content.endswith('\n'):
                f.write('\n')  # Add final newline

    def _copy_support_file(self, dest_filename: str) -> None:
        """Copy a single support file from language-specific directory."""
        # Get the generator directory (parent of parent of this file)
        generator_dir = Path(__file__).parent.parent
        language_dir = generator_dir / 'languages' / self.language

        # Copy the file
        source_file = language_dir / dest_filename
        dest_file = self.output_path / dest_filename

        if source_file.exists():
            # Create parent directories if they don't exist (for nested paths)
            dest_file.parent.mkdir(parents=True, exist_ok=True)

            with open(source_file) as src, open(dest_file, 'w') as dst:
                dst.write(src.read())
        else:
            print(f'Warning: Support file not found: {source_file}')

    def _print_summary(self, generation_result: GenerationResult) -> None:
        """Print generation summary with flexible file listing."""
        print(f'Generated code in {self.output_path}')

        # Group files by category for organized output
        by_category = {}
        for file in generation_result.generated_files:
            if file.category not in by_category:
                by_category[file.category] = []
            by_category[file.category].append(file)

        # Print organized summary in logical order
        for category in ['entities', 'repositories', 'services', 'config', 'examples']:
            if category in by_category:
                files = by_category[category]
                if len(files) == 1 and files[0].count > 0:
                    # Single file with count: "- entities.py: 5 entities"
                    print(f'- {files[0].path}: {files[0].description}')
                else:
                    # Multiple files or no count: list each file
                    for file in files:
                        print(f'- {file.path}: {file.description}')

        # Always show access pattern mapping
        print(
            f'- access_pattern_mapping.json: {len(generation_result.access_pattern_mapping)} access patterns'
        )
