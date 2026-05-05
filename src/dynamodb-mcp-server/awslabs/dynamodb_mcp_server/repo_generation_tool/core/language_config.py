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

"""Language-specific configuration system."""

from awslabs.dynamodb_mcp_server.repo_generation_tool.core.file_utils import (
    FileUtils,
)
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SupportFile:
    """Represents a support file to be copied."""

    source: str
    dest: str
    description: str
    category: str


@dataclass
class LinterConfig:
    """Linter configuration for a language."""

    command: list[str]
    check_args: list[str]
    fix_args: list[str]
    format_command: list[str]
    config_file: str


@dataclass
class NamingConventions:
    """Naming conventions for a language."""

    method_naming: str
    crud_patterns: dict[str, str]


@dataclass
class LanguageConfig:
    """Complete language configuration."""

    name: str
    file_extension: str
    naming_conventions: NamingConventions | None
    file_patterns: dict[str, str]
    support_files: list[SupportFile]
    linter: LinterConfig | None


class LanguageConfigLoader:
    """Loads language configurations from JSON files."""

    @staticmethod
    def load(language: str) -> LanguageConfig:
        """Load language configuration from JSON file."""
        languages_dir = Path(__file__).parent.parent / 'languages'
        config_path = languages_dir / language / 'language_config.json'

        # Validate path security with base directory restriction
        try:
            resolved_path = FileUtils.validate_and_resolve_path(
                config_path,
                allow_absolute_paths=True,  # Allow absolute paths for internal config loading
                base_dir=languages_dir,
                file_name='Language configuration',
            )
        except FileNotFoundError:
            raise FileNotFoundError(f'Language configuration not found for: {language}')
        except (ValueError, OSError, RuntimeError) as e:
            raise ValueError(f'Invalid language: {language}') from e

        # Load configuration using shared utility
        data = FileUtils.load_json_file(str(resolved_path), 'Language configuration')

        # Validate required fields
        required_fields = ['name', 'file_extension']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValueError(
                f'Missing required fields in {resolved_path}: {", ".join(missing_fields)}'
            )

        # Convert support_files to SupportFile objects
        support_files = [SupportFile(**sf) for sf in data.get('support_files', [])]

        # Convert naming conventions to NamingConventions object
        naming_data = data.get('naming_conventions', {})
        naming_conventions = NamingConventions(**naming_data) if naming_data else None

        # Convert linter config to LinterConfig object
        linter_data = data.get('linter', {})
        linter = LinterConfig(**linter_data) if linter_data else None

        return LanguageConfig(
            name=data['name'],
            file_extension=data['file_extension'],
            naming_conventions=naming_conventions,
            file_patterns=data.get('file_patterns', {}),
            support_files=support_files,
            linter=linter,
        )

    @staticmethod
    def get_available_languages() -> list[str]:
        """Get list of available languages."""
        languages_dir = Path(__file__).parent.parent / 'languages'
        return [
            lang_dir.name
            for lang_dir in languages_dir.iterdir()
            if lang_dir.is_dir() and (lang_dir / 'language_config.json').exists()
        ]
