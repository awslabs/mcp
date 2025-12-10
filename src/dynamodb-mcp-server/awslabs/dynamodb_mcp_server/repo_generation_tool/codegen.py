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

#!/usr/bin/env python3
"""Main script to generate entities and repositories from schema.

This module provides the generate() function which validates schemas and generates
code, returning a GenerationResult object. The result can be formatted for CLI
output or programmatic consumption (e.g., MCP tools).
"""

import argparse
import logging
import os
import subprocess
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.language_config import (
    LanguageConfigLoader,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_definitions import (
    ValidationResult,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_validator import (
    SchemaValidator,
    validate_schema_file,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.generators import create_generator
from dataclasses import dataclass
from pathlib import Path


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Constants
SUPPORTED_LANGUAGES = ['python']
ALLOWED_LINTER_COMMANDS = {'ruff', 'uv'}  # Allowlist for subprocess security


@dataclass
class GenerationResult:
    """Result of schema validation and code generation operation."""

    success: bool
    validation_passed: bool
    validation_result: ValidationResult
    validate_only: bool = False
    output_dir: Path | None = None
    linting_passed: bool | None = None
    error_message: str | None = None

    # Public methods

    def format_for_cli(self, args) -> str:
        """Format result for CLI output with next steps."""
        return self.format_result('cli', args)

    def format_for_mcp(self) -> str:
        """Format result for MCP tool output (concise)."""
        return self.format_result('mcp')

    def format_result(self, format_type: str = 'mcp', args=None) -> str:
        """Format result for CLI or MCP output.

        Args:
            format_type: Either "cli" or "mcp"
            args: CLI arguments (required for "cli" format)

        Returns:
            Formatted output string
        """
        lines = []

        # Validation output (shared logic)
        if not self.validation_passed:
            lines.append(self._format_validation_error())
            if format_type == 'mcp' and self.error_message:
                lines.append(f'\n❌ Validation failed: {self.error_message}')
            return '\n'.join(lines)

        # Validation success/warnings (shared logic)
        lines.append(self._format_validation_success())

        # Early exit for validate-only (shared logic)
        if self.validate_only:
            lines.append('🎉 Validation completed successfully!')
            return '\n'.join(lines)

        # Generation success (format-specific)
        if self.output_dir:
            if format_type == 'cli' and args:
                lines.append(f'\n✅ Jinja2 {args.language} code generated in {self.output_dir}')
            else:
                lines.append(f'\n✅ Code generated in {self.output_dir}')

            lines.append('🎉 Generation completed successfully!')

            if self.linting_passed is False:
                lines.append('⚠️ Linting found issues, but generation was successful')

        # CLI-specific next steps
        if format_type == 'cli' and args:
            lines.extend(self._format_next_steps(args))

        return '\n'.join(lines)

    # Private helper methods

    def _format_validation_error(self) -> str:
        """Format validation error output."""
        validator = SchemaValidator()
        validator.result = self.validation_result
        return validator.format_validation_result()

    def _format_validation_success(self) -> str:
        """Format validation success with warnings if any."""
        if self.validation_result.warnings:
            return self._format_validation_error()
        return '✅ Schema validation passed!'

    def _format_next_steps(self, args) -> list:
        """Format next steps for CLI output."""
        lines = ['\nNext steps:']
        lines.append('1. Review the generated code')
        lines.append('2. Install runtime dependencies: uv add pydantic boto3')
        lines.append('3. Set up your DynamoDB connection (local or AWS)')

        if args.generate_sample_usage:
            lines.append('4. Run usage_examples.py to test the generated code')
            next_step = 5
        else:
            lines.append('4. Generate usage examples with --generate_sample_usage flag')
            next_step = 5

        if args.no_lint:
            lines.append(f'{next_step}. Run without --no-lint to enable code quality checks')

        return lines


# Subprocess timeout constants (in seconds)
LINTER_VERSION_CHECK_TIMEOUT = 10  # Quick version check
LINTER_EXECUTION_TIMEOUT = 60  # 1 minute for linting/formatting operations


def _validate_linter_command(cmd: list) -> None:
    """Validate that command is in allowlist.

    Args:
        cmd: Command to validate

    Raises:
        ValueError: If command is not allowed
    """
    if not cmd or not isinstance(cmd, list):
        raise ValueError('Invalid command format')

    base_cmd = os.path.basename(cmd[0]) if cmd else ''
    if base_cmd.endswith('.exe'):
        base_cmd = base_cmd[:-4]

    if base_cmd not in ALLOWED_LINTER_COMMANDS:
        raise ValueError(f'Command not allowed: {base_cmd}')


def run_linter(output_dir: Path, language: str, fix: bool = False) -> bool:
    """Run language-specific linter on generated code.

    Args:
        output_dir: Directory containing generated code
        language: Programming language
        fix: Whether to auto-fix issues

    Returns:
        True if linting passed or was skipped, False if issues found
    """
    try:
        # Load language configuration
        language_config = LanguageConfigLoader.load(language)

        if not language_config.linter:
            logger.warning(f'No linter configured for {language}')
            return True

        # Check if linter config file exists
        config_file = output_dir / language_config.linter.config_file
        if not config_file.exists():
            logger.warning(f'No {language_config.linter.config_file} found, skipping linting')
            return True

        # Check if linter is available
        version_cmd = language_config.linter.command + ['--version']
        _validate_linter_command(version_cmd)
        result = subprocess.run(
            version_cmd, capture_output=True, text=True, timeout=LINTER_VERSION_CHECK_TIMEOUT
        )
        if result.returncode != 0:
            linter_name = ' '.join(language_config.linter.command)
            logger.warning(f'{linter_name} not available')
            return False

        # Run linter check
        cmd = language_config.linter.command + (
            language_config.linter.fix_args if fix else language_config.linter.check_args
        )
        # Replace {config_file} placeholder with actual config file path
        cmd = [arg.replace('{config_file}', str(config_file)) for arg in cmd]
        cmd.append(str(output_dir))

        _validate_linter_command(cmd)
        result = subprocess.run(cmd, timeout=LINTER_EXECUTION_TIMEOUT)

        # Run formatter if fixing and format command is available (regardless of linter result)
        if fix and language_config.linter.format_command:
            format_cmd = language_config.linter.format_command.copy()
            # Replace {config_file} placeholder with actual config file path
            format_cmd = [arg.replace('{config_file}', str(config_file)) for arg in format_cmd]
            format_cmd.append(str(output_dir))
            _validate_linter_command(format_cmd)
            subprocess.run(format_cmd, timeout=LINTER_EXECUTION_TIMEOUT)

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        logger.error('Linter execution timed out')
        return False
    except FileNotFoundError as e:
        logger.warning(f'Linter command not found: {e}')
        return False
    except Exception as e:
        logger.error(f'Error running linter: {e}')
        return False


def generate(
    schema_path: str,
    output_dir: str | None = None,
    language: str = 'python',
    generate_sample_usage: bool = False,
    generator: str = 'jinja2',
    no_lint: bool = False,
    no_fix: bool = False,
    validate_only: bool = False,
    templates_dir: str | None = None,
    allowed_base_dirs: list[Path] | None = None,
) -> GenerationResult:
    """Generate DynamoDB entities and repositories from a schema file.

    Args:
        schema_path: Path to the schema JSON file
        output_dir: Output directory for generated code (default: repo_generation_tool/generated/{language})
        language: Target programming language for generated code (default: python)
        generate_sample_usage: Generate usage examples and test cases
        generator: Generator type to use (default: jinja2)
        no_lint: Skip running linter on generated code
        no_fix: Skip auto-fixing linting issues
        validate_only: Only validate the schema without generating code
        templates_dir: Directory containing Jinja2 templates (optional)
        allowed_base_dirs: List of allowed base directories for schema files (security)
                          If None, allows current working directory only

    Returns:
        GenerationResult: Object containing validation and generation results

    Raises:
        FileNotFoundError: If schema file not found
        ValueError: If schema path is outside allowed directories (path traversal protection)
                   or if unsupported language is specified
    """
    # Validate language support
    if language not in SUPPORTED_LANGUAGES:
        supported_langs = ', '.join(SUPPORTED_LANGUAGES)
        raise ValueError(
            f"Unsupported language '{language}'. Supported languages are: {supported_langs}"
        )

    schema_path_obj = Path(schema_path).resolve()

    # Security: Validate path is within allowed directories
    if allowed_base_dirs is None:
        # Default: only allow files in current working directory and subdirectories
        allowed_base_dirs = [Path.cwd()]

    is_allowed = False
    for base_dir in allowed_base_dirs:
        try:
            base_dir_resolved = base_dir.resolve()
            # Check if schema_path is within this base directory
            schema_path_obj.relative_to(base_dir_resolved)
            is_allowed = True
            break
        except ValueError:
            # Not within this base directory, try next
            continue

    if not is_allowed:
        allowed_paths = ', '.join(str(d) for d in allowed_base_dirs)
        raise ValueError(
            f'Security: Schema file must be within allowed directories: {allowed_paths}. '
            f'Provided path: {schema_path_obj}'
        )

    if not schema_path_obj.exists():
        raise FileNotFoundError(f'Schema file {schema_path_obj} not found')

    # Set default output directory based on language if not specified
    if output_dir is None:
        output_dir_obj = Path(__file__).parent / 'generated' / language
    else:
        output_dir_obj = Path(output_dir)

    try:
        # Validate schema
        validation_result = validate_schema_file(str(schema_path_obj))

        # Create result with validation status
        result = GenerationResult(
            success=validation_result.is_valid,
            validation_passed=validation_result.is_valid,
            validation_result=validation_result,
            validate_only=validate_only,
        )

        # Handle validation failure
        if not validation_result.is_valid:
            result.error_message = 'Schema validation failed'
            return result

        # Early exit for validate-only mode
        if validate_only:
            return result

        # Generate code
        generator_obj = create_generator(
            'jinja2', str(schema_path_obj), language=language, templates_dir=templates_dir
        )
        generator_obj.generate_all(
            str(output_dir_obj), generate_usage_examples=generate_sample_usage
        )

        # Run linter by default (unless disabled)
        linting_passed = None
        if not no_lint:
            should_fix = not no_fix
            linting_passed = run_linter(output_dir_obj, language, fix=should_fix)

        return GenerationResult(
            success=True,
            validation_passed=True,
            validation_result=validation_result,
            validate_only=False,
            output_dir=output_dir_obj,
            linting_passed=linting_passed,
        )

    except Exception as e:
        logger.error(f'Error during generation: {e}')
        return GenerationResult(
            success=False,
            validation_passed=False,
            validation_result=ValidationResult(is_valid=False, errors=[], warnings=[]),
            validate_only=validate_only,
            error_message=str(e),
        )


def main():
    """CLI entry point for the code generator."""
    parser = argparse.ArgumentParser(description='Generate DynamoDB entities and repositories')
    parser.add_argument('--schema', default='schema.json', help='Path to the schema JSON file')
    parser.add_argument(
        '--output',
        default=None,  # Will be set dynamically based on language
        help='Output directory for generated code (default: repo_generation_tool/generated/{language})',
    )
    parser.add_argument(
        '--generator',
        choices=['jinja2'],
        default='jinja2',
        help='Generator type to use (only jinja2 supported)',
    )
    parser.add_argument(
        '--language',
        choices=['python'],  # Will expand to ["python", "typescript", "java"] later
        default='python',
        help='Target programming language for generated code',
    )
    parser.add_argument(
        '--templates-dir',
        default=None,
        help='Directory containing Jinja2 templates (for jinja2 generator)',
    )
    parser.add_argument(
        '--generate_sample_usage',
        action='store_true',
        default=False,
        help='Generate usage examples and test cases',
    )
    parser.add_argument(
        '--no-lint',
        action='store_true',
        default=False,
        help='Skip running language-specific linter on generated code (linting enabled by default)',
    )
    parser.add_argument(
        '--no-fix',
        action='store_true',
        default=False,
        help='Skip auto-fixing linting issues (auto-fix enabled by default)',
    )
    parser.add_argument(
        '--validate-only',
        action='store_true',
        default=False,
        help='Only validate the schema without generating code',
    )

    args = parser.parse_args()

    try:
        result = generate(
            schema_path=args.schema,
            output_dir=args.output,
            language=args.language,
            generate_sample_usage=args.generate_sample_usage,
            generator=args.generator,
            no_lint=args.no_lint,
            no_fix=args.no_fix,
            validate_only=args.validate_only,
            templates_dir=args.templates_dir,
        )

        # Print formatted output
        print(result.format_for_cli(args))

        return 0 if result.success else 1

    except FileNotFoundError as e:
        logger.error(f'File not found: {e}')
        return 1
    except Exception as e:
        logger.error(f'Unexpected error: {e}')
        return 1


if __name__ == '__main__':
    exit(main())
