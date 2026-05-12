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

import argparse
import logging
import os
import subprocess  # nosec B404 - used to invoke allowlisted linters (see line 50: ALLOWED_LINTER_COMMANDS)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.language_config import (
    LanguageConfigLoader,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_validator import (
    SchemaValidator,
    validate_schema_file,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.usage_data_validator import (
    UsageDataValidator,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.validation_utils import (
    ValidationResult,
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
    usage_data_validation_passed: bool | None = None
    usage_data_validation_result: ValidationResult | None = None

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
        lines = []

        # Schema validation errors
        validator = SchemaValidator()
        validator.result = self.validation_result
        lines.append(validator.format_validation_result())

        # Usage data validation errors (if applicable)
        if self.usage_data_validation_result and not self.usage_data_validation_result.is_valid:
            usage_validator = UsageDataValidator()
            usage_validator.result = self.usage_data_validation_result
            lines.append('\n' + usage_validator.format_validation_result())

        return '\n'.join(lines)

    def _format_validation_success(self) -> str:
        """Format validation success."""
        lines = []

        # Schema validation
        if self.validation_result.warnings:
            validator = SchemaValidator()
            validator.result = self.validation_result
            lines.append(validator.format_validation_result())
        else:
            lines.append('✅ Schema validation passed!')

        # Usage data validation (if applicable)
        if self.usage_data_validation_result and self.usage_data_validation_passed:
            lines.append('✅ Usage data validation passed!')

        return '\n'.join(lines)

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


def _validate_path_within_allowed_dirs(
    file_path: Path, resolved_base_dirs: list[Path], file_type: str
) -> None:
    """Validate that a file path is within allowed directories.

    Args:
        file_path: Resolved path to validate
        resolved_base_dirs: List of pre-resolved allowed base directories
        file_type: Description for error messages (e.g., "Schema file", "Usage data file")

    Raises:
        ValueError: If path is outside allowed directories
    """
    for base_dir in resolved_base_dirs:
        try:
            file_path.relative_to(base_dir)
            return  # Path is within this base directory
        except ValueError:
            continue

    allowed_paths = ', '.join(str(d) for d in resolved_base_dirs)
    raise ValueError(
        f'Security: {file_type} must be within allowed directories: {allowed_paths}. '
        f'Provided path: {file_path}'
    )


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
        result = subprocess.run(  # nosec B603, B607 - user local env, hardcoded cmd, no shell, timeout
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
        result = subprocess.run(cmd, timeout=LINTER_EXECUTION_TIMEOUT)  # nosec B603, B607 - user local env, hardcoded cmd, no shell, timeout

        # Run formatter if fixing and format command is available (regardless of linter result)
        if fix and language_config.linter.format_command:
            format_cmd = language_config.linter.format_command.copy()
            # Replace {config_file} placeholder with actual config file path
            format_cmd = [arg.replace('{config_file}', str(config_file)) for arg in format_cmd]
            format_cmd.append(str(output_dir))
            _validate_linter_command(format_cmd)
            subprocess.run(format_cmd, timeout=LINTER_EXECUTION_TIMEOUT)  # nosec B603, B607 - user local env, hardcoded cmd, no shell, timeout

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
    usage_data_path: str | None = None,
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
        usage_data_path: Path to usage_data.json file for realistic sample data (optional)
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

    # Security: Validate paths are within allowed directories
    # Default to cwd for security; callers (CLI/MCP) should pass schema's parent explicitly
    if allowed_base_dirs is None:
        allowed_base_dirs = [Path.cwd()]
    resolved_base_dirs = [d.resolve() for d in allowed_base_dirs]

    _validate_path_within_allowed_dirs(schema_path_obj, resolved_base_dirs, 'Schema file')

    if not schema_path_obj.exists():
        raise FileNotFoundError(f'Schema file {schema_path_obj} not found')

    if usage_data_path and isinstance(usage_data_path, str):
        _validate_path_within_allowed_dirs(
            Path(usage_data_path).resolve(), resolved_base_dirs, 'Usage data file'
        )

    # Set default output directory based on language if not specified
    if output_dir is None:
        output_dir_obj = Path(__file__).parent / 'generated' / language
    else:
        output_dir_obj = Path(output_dir)

    try:
        # Validate schema
        validation_result = validate_schema_file(str(schema_path_obj))

        # Initialize usage_data validation results
        usage_data_validation_result = None
        usage_data_validation_passed = None

        # Validate usage_data if provided (using pre-extracted entity information)
        if usage_data_path and isinstance(usage_data_path, str):
            if validation_result.is_valid and validation_result.extracted_entities is not None:
                # Use pre-extracted entity information (efficient path)
                validator = UsageDataValidator()
                usage_data_validation_result = validator.validate_usage_data_file(
                    usage_data_path,
                    validation_result.extracted_entities,
                    validation_result.extracted_entity_fields,
                )
            else:
                # Schema validation failed, skip usage_data validation
                usage_data_validation_result = ValidationResult(
                    is_valid=False, errors=[], warnings=[]
                )
                usage_data_validation_result.add_error(
                    'schema',
                    'Cannot validate usage_data because schema validation failed',
                    'Fix schema errors first',
                )

            usage_data_validation_passed = usage_data_validation_result.is_valid

            # Log errors to provide immediate feedback to users
            if usage_data_validation_result.errors:
                for error in usage_data_validation_result.errors:
                    logger.error(f'usage_data.json: {error.message}')

        # Create result with validation status
        result = GenerationResult(
            success=validation_result.is_valid,
            validation_passed=validation_result.is_valid,
            validation_result=validation_result,
            validate_only=validate_only,
            usage_data_validation_passed=usage_data_validation_passed,
            usage_data_validation_result=usage_data_validation_result,
        )

        # Handle validation failure (schema or usage_data)
        overall_validation_passed = validation_result.is_valid
        if usage_data_validation_result and not usage_data_validation_result.is_valid:
            overall_validation_passed = False

        if not overall_validation_passed:
            result.success = False
            result.validation_passed = False
            if not validation_result.is_valid:
                result.error_message = 'Schema validation failed'
            elif usage_data_validation_result and not usage_data_validation_result.is_valid:
                result.error_message = 'Usage data validation failed'
            return result

        # Early exit for validate-only mode
        if validate_only:
            return result

        # Generate code
        generator_obj = create_generator(
            generator,
            str(schema_path_obj),
            language=language,
            templates_dir=templates_dir,
            usage_data_path=usage_data_path,
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
            usage_data_validation_passed=usage_data_validation_passed,
            usage_data_validation_result=usage_data_validation_result,
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
    parser.add_argument(
        '--usage-data-path',
        default=None,
        help='Path to usage_data.json file for realistic sample data',
    )

    args = parser.parse_args()

    try:
        # For CLI, allow schema's parent directory and usage_data's parent (if different)
        schema_parent = Path(args.schema).resolve().parent
        allowed_dirs = [schema_parent]

        if args.usage_data_path:
            usage_data_parent = Path(args.usage_data_path).resolve().parent
            if usage_data_parent != schema_parent:
                allowed_dirs.append(usage_data_parent)

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
            usage_data_path=args.usage_data_path,
            allowed_base_dirs=allowed_dirs,
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
