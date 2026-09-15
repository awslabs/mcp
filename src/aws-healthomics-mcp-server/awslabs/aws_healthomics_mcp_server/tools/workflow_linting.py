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

"""Workflow linting tools for WDL and CWL workflow definitions."""

import asyncio
import os
import tempfile
from abc import ABC, abstractmethod
from awslabs.aws_healthomics_mcp_server.utils.content_resolver import (
    resolve_bundle_content,
    resolve_single_content,
)
from awslabs.aws_healthomics_mcp_server.utils.error_utils import handle_tool_error
from awslabs.aws_healthomics_mcp_server.vendor import wdl
from awslabs.aws_healthomics_mcp_server.vendor.wdl import Lint as wdl_lint
from loguru import logger
from mcp.server.mcpserver import Context
from pathlib import Path
from pydantic import Field
from typing import Any, Dict, List, Optional, Tuple, Union


def _format_wdl_position(pos: 'wdl.Error.SourcePosition') -> str:
    """Format a vendored-miniwdl SourcePosition as `uri:line:column`."""
    return f'{pos.uri}:{pos.line}:{pos.column}'


def _format_wdl_error(exc: Exception) -> str:
    """Format a WDL syntax/validation error (or MultipleValidationErrors) as readable text."""
    if isinstance(exc, wdl.Error.MultipleValidationErrors):
        return '\n'.join(_format_wdl_error(e) for e in exc.exceptions)
    pos = getattr(exc, 'pos', None)
    location = f'{_format_wdl_position(pos)}: ' if pos else ''
    return f'{location}({type(exc).__name__}) {exc}'


async def _check_wdl_document(uri: str, search_path: List[str]) -> Tuple[str, int]:
    """Parse and lint a WDL document using the vendored miniwdl parser/lint modules.

    Args:
        uri: Path to the main WDL file to load
        search_path: Local directories to search for WDL import statements

    Returns:
        Tuple of (human-readable output text, return code), mirroring the shape of
        `miniwdl check`'s CLI output (0 for a document that parsed and typechecked
        successfully, 1 for syntax/validation/import errors) for compatibility with
        existing raw_output consumers.
    """
    try:
        doc = await wdl.load_async(uri, path=search_path)
    except (
        wdl.Error.SyntaxError,
        wdl.Error.ValidationError,
        wdl.Error.MultipleValidationErrors,
        wdl.Error.ImportError,
    ) as e:
        return _format_wdl_error(e), 1

    wdl_lint.lint(doc)
    findings = [f for f in wdl_lint.collect(doc) if not f[3]]  # drop suppressed findings

    lines = [f'{uri} is syntactically valid WDL.']
    if findings:
        lines.append(f'{len(findings)} lint finding(s):')
        for pos, linter_class, message, _suppressed in findings:
            lines.append(f'  {_format_wdl_position(pos)} [{linter_class}] {message}')
    else:
        lines.append('No lint findings.')
    return '\n'.join(lines), 0


class WorkflowLinter(ABC):
    """Base class for workflow linters with core functionality and abstract methods."""

    def __init__(self, workflow_format: str):
        """Initialize the workflow linter with the supported format.

        Args:
            workflow_format: The workflow format this linter supports ('wdl' or 'cwl')
        """
        self.workflow_format = workflow_format.lower()

    @abstractmethod
    async def lint_workflow(
        self, workflow_content: str, filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """Lint a single workflow definition and return findings.

        Args:
            workflow_content: The workflow definition content
            filename: Optional filename for context

        Returns:
            Dictionary containing lint results and findings
        """
        pass

    @abstractmethod
    async def lint_workflow_bundle(
        self, workflow_files: Dict[str, str], main_workflow_file: str
    ) -> Dict[str, Any]:
        """Lint a multi-file workflow bundle and return findings.

        Args:
            workflow_files: Dictionary mapping file paths to their content
            main_workflow_file: Path to the main workflow file within the bundle

        Returns:
            Dictionary containing lint results and findings
        """
        pass

    def _create_error_response(
        self, message: str, filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a standardized error response.

        Args:
            message: Error message
            filename: Optional filename for context

        Returns:
            Dictionary containing error response
        """
        response = {
            'status': 'error',
            'format': self.workflow_format,
            'message': message,
        }
        if filename:
            response['filename'] = filename
        return response

    def _create_success_response(
        self, raw_output: str, linter: str, filename: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """Create a standardized success response.

        Args:
            raw_output: Raw output from the linter
            linter: Name of the linting tool used
            filename: Optional filename for context
            **kwargs: Additional fields to include in response

        Returns:
            Dictionary containing success response
        """
        response = {
            'status': 'success',
            'format': self.workflow_format,
            'linter': linter,
            'raw_output': raw_output,
        }
        if filename:
            response['filename'] = filename
        response.update(kwargs)
        return response


class WDLWorkflowLinter(WorkflowLinter):
    """Linter for WDL workflow definitions using a vendored subset of miniwdl's parser/lint code.

    miniwdl's own PyPI package declares a hard dependency on the GPL-licensed `pygtail`
    (used only by its task-execution runtime, not by parsing/linting), which blocks this
    Apache-2.0 project from depending on it directly. See
    awslabs/aws_healthomics_mcp_server/vendor/wdl/VENDORED.md for the vendoring rationale
    and provenance.
    """

    def __init__(self):
        """Initialize the WDL workflow linter."""
        super().__init__('wdl')

    async def lint_workflow(
        self, workflow_content: str, filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """Lint WDL workflow using the vendored miniwdl parser/lint modules."""
        tmp_path = None
        try:
            # Create temporary file for the WDL content
            with tempfile.NamedTemporaryFile(mode='w', suffix='.wdl', delete=False) as tmp_file:
                tmp_file.write(workflow_content)
                tmp_path = Path(tmp_file.name)

            output_text, return_code = await asyncio.wait_for(
                _check_wdl_document(str(tmp_path), search_path=[]), timeout=30
            )
            raw_output = (
                f'STDOUT:\n{output_text}\nSTDERR:\n\nReturn code: {return_code}'
                if return_code == 0
                else f'STDOUT:\n\nSTDERR:\n{output_text}\nReturn code: {return_code}'
            )

            return self._create_success_response(
                raw_output=raw_output, linter='miniwdl', filename=filename or tmp_path.name
            )

        except asyncio.TimeoutError:
            return self._create_error_response(
                'Linter execution timed out after 30 seconds',
                filename or (tmp_path.name if tmp_path else None),
            )
        except Exception as e:
            logger.error(f'Error in WDL linting: {str(e)}')
            return self._create_error_response(f'WDL linting failed: {str(e)}', filename)

        finally:
            # Clean up temporary file
            if tmp_path:
                try:
                    tmp_path.unlink()
                except Exception as e:
                    logger.warning(f'Failed to clean up temporary WDL file {tmp_path}: {str(e)}')

    async def lint_workflow_bundle(
        self, workflow_files: Dict[str, str], main_workflow_file: str
    ) -> Dict[str, Any]:
        """Lint WDL workflow bundle using the vendored miniwdl parser/lint modules."""
        try:
            # Create temporary directory structure
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)
                tmp_resolved = tmp_path.resolve()

                # Write all files to temporary directory maintaining structure
                for file_path, content in workflow_files.items():
                    try:
                        full_path = (tmp_path / file_path).resolve()
                    except Exception:
                        return self._create_error_response(
                            f'Invalid file path in workflow bundle: {file_path}'
                        )

                    if not str(full_path).startswith(str(tmp_resolved) + os.sep):
                        return self._create_error_response(
                            f'Path traversal detected in workflow file key: {file_path!r}. '
                            f'File paths must remain within the workflow bundle directory.'
                        )

                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content)

                # Validate main_workflow_file path stays within temp directory
                main_file_path = (tmp_path / main_workflow_file).resolve()
                if not str(main_file_path).startswith(str(tmp_resolved) + os.sep):
                    return self._create_error_response(
                        f'Path traversal detected in main_workflow_file: {main_workflow_file!r}. '
                        f'File paths must remain within the workflow bundle directory.'
                    )

                if not main_file_path.exists():
                    return self._create_error_response(
                        f'Main workflow file "{main_workflow_file}" not found in provided files'
                    )

                # Parse and lint the main file, searching the bundle directory for imports
                output_text, return_code = await asyncio.wait_for(
                    _check_wdl_document(str(main_file_path), search_path=[str(tmp_path)]),
                    timeout=30,
                )
                raw_output = (
                    f'STDOUT:\n{output_text}\nSTDERR:\n\nReturn code: {return_code}'
                    if return_code == 0
                    else f'STDOUT:\n\nSTDERR:\n{output_text}\nReturn code: {return_code}'
                )

                return self._create_success_response(
                    raw_output=raw_output,
                    linter='miniwdl',
                    main_file=main_workflow_file,
                    files_processed=list(workflow_files.keys()),
                )

        except asyncio.TimeoutError:
            return self._create_error_response('Linter execution timed out after 30 seconds')
        except Exception as e:
            logger.error(f'Error in WDL bundle linting: {str(e)}')
            return self._create_error_response(f'WDL bundle linting failed: {str(e)}')


class CWLWorkflowLinter(WorkflowLinter):
    """Linter for CWL workflow definitions using cwltool."""

    def __init__(self):
        """Initialize the CWL workflow linter."""
        super().__init__('cwl')

    async def lint_workflow(
        self, workflow_content: str, filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """Lint CWL workflow using cwltool."""
        import subprocess  # nosec B404 - subprocess needed for workflow linting
        import sys

        tmp_path = None
        try:
            # Create temporary file for the CWL content
            with tempfile.NamedTemporaryFile(mode='w', suffix='.cwl', delete=False) as tmp_file:
                tmp_file.write(workflow_content)
                tmp_path = Path(tmp_file.name)

            # Capture raw linter output using cwltool --validate
            result = subprocess.run(  # nosec B603 - safe: hardcoded cmd, no shell, timeout
                [sys.executable, '-m', 'cwltool', '--validate', str(tmp_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            raw_output = f'STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\nReturn code: {result.returncode}'

            return self._create_success_response(
                raw_output=raw_output, linter='cwltool', filename=filename or tmp_path.name
            )

        except subprocess.TimeoutExpired:
            return self._create_error_response(
                'Linter execution timed out after 30 seconds',
                filename or (tmp_path.name if tmp_path else None),
            )
        except Exception as e:
            logger.error(f'Error in CWL linting: {str(e)}')
            return self._create_error_response(f'CWL linting failed: {str(e)}', filename)

        finally:
            # Clean up temporary file
            if tmp_path:
                try:
                    tmp_path.unlink()
                except Exception as e:
                    logger.warning(f'Failed to clean up temporary CWL file {tmp_path}: {str(e)}')

    async def lint_workflow_bundle(
        self, workflow_files: Dict[str, str], main_workflow_file: str
    ) -> Dict[str, Any]:
        """Lint CWL workflow bundle using cwltool."""
        import subprocess  # nosec B404 - subprocess needed for workflow linting
        import sys

        try:
            # Create temporary directory structure
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)
                tmp_resolved = tmp_path.resolve()

                # Write all files to temporary directory maintaining structure
                for file_path, content in workflow_files.items():
                    try:
                        full_path = (tmp_path / file_path).resolve()
                    except Exception:
                        return self._create_error_response(
                            f'Invalid file path in workflow bundle: {file_path}'
                        )

                    if not str(full_path).startswith(str(tmp_resolved) + os.sep):
                        return self._create_error_response(
                            f'Path traversal detected in workflow file key: {file_path!r}. '
                            f'File paths must remain within the workflow bundle directory.'
                        )

                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content)

                # Validate main_workflow_file path stays within temp directory
                main_file_path = (tmp_path / main_workflow_file).resolve()
                if not str(main_file_path).startswith(str(tmp_resolved) + os.sep):
                    return self._create_error_response(
                        f'Path traversal detected in main_workflow_file: {main_workflow_file!r}. '
                        f'File paths must remain within the workflow bundle directory.'
                    )

                if not main_file_path.exists():
                    return self._create_error_response(
                        f'Main workflow file "{main_workflow_file}" not found in provided files'
                    )

                # Capture raw linter output using cwltool --validate
                result = subprocess.run(  # nosec B603 - safe: hardcoded cmd, no shell, timeout
                    [sys.executable, '-m', 'cwltool', '--validate', str(main_file_path)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=str(tmp_path),
                )
                raw_output = f'STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\nReturn code: {result.returncode}'

                return self._create_success_response(
                    raw_output=raw_output,
                    linter='cwltool',
                    main_file=main_workflow_file,
                    files_processed=list(workflow_files.keys()),
                )

        except subprocess.TimeoutExpired:
            return self._create_error_response('Linter execution timed out after 30 seconds')
        except Exception as e:
            logger.error(f'Error in CWL bundle linting: {str(e)}')
            return self._create_error_response(f'CWL bundle linting failed: {str(e)}')


# Global linter instances
_wdl_linter = WDLWorkflowLinter()
_cwl_linter = CWLWorkflowLinter()

# Linter registry
_linters = {
    'wdl': _wdl_linter,
    'cwl': _cwl_linter,
}


def get_linter(workflow_format: str) -> WorkflowLinter:
    """Get the appropriate linter for the given workflow format.

    Args:
        workflow_format: The workflow format ('wdl' or 'cwl')

    Returns:
        The appropriate linter instance

    Raises:
        ValueError: If the workflow format is not supported
    """
    format_lower = workflow_format.lower()
    if format_lower not in _linters:
        supported_formats = list(_linters.keys())
        raise ValueError(
            f'Unsupported workflow format: {workflow_format}. Supported formats: {supported_formats}'
        )
    return _linters[format_lower]


async def lint_workflow_definition(
    ctx: Context,
    workflow_content: str = Field(
        description='The workflow definition content to lint. Accepts inline content, a local file path, or an S3 URI (s3://bucket/key).'
    ),
    workflow_format: str = Field(description="The workflow format: 'wdl' or 'cwl'"),
    filename: Optional[str] = Field(default=None, description='Optional filename for context'),
) -> Dict[str, Any]:
    """Lint WDL or CWL workflow definitions and return validation findings.

    This tool validates workflow definitions using appropriate linting tools:
    - WDL workflows: Uses miniwdl package for parsing and validation
    - CWL workflows: Uses cwltool package for parsing and validation

    The tool checks for:
    - Syntax errors and parsing issues
    - Missing required fields (inputs, outputs, steps)
    - Runtime requirements for tasks
    - Common workflow structure issues

    Args:
        ctx: MCP context for error reporting
        workflow_content: The workflow definition content to lint. Accepts inline content,
            a local file path, or an S3 URI (s3://bucket/key).
        workflow_format: The workflow format ('wdl' or 'cwl')
        filename: Optional filename for context in error messages

    Returns:
        Dictionary containing:
        - status: 'success' or 'error'
        - format: The workflow format that was linted
        - filename: The filename that was processed (optional)
        - linter: Name of the linting tool used
        - raw_output: Raw output from the linter command execution
    """
    try:
        try:
            resolved = await resolve_single_content(workflow_content, mode='text')
        except (ValueError, FileNotFoundError, PermissionError) as e:
            return await handle_tool_error(ctx, e, 'Error resolving workflow content')

        logger.info(f'Linting {workflow_format} workflow definition')
        linter = get_linter(workflow_format)
        return await linter.lint_workflow(
            workflow_content=str(resolved.content), filename=filename
        )
    except ValueError as e:
        # Handle unsupported workflow format from get_linter
        error_message = str(e)
        logger.error(error_message)
        await ctx.error(error_message)
        return {'status': 'error', 'message': error_message}


async def lint_workflow_bundle(
    ctx: Context,
    workflow_files: Union[str, Dict[str, str]] = Field(
        description='Dictionary mapping file paths to their content, a local directory path, a ZIP file path, or an S3 URI (s3://bucket/prefix/ or s3://bucket/file.zip).'
    ),
    workflow_format: str = Field(description="The workflow format: 'wdl' or 'cwl'"),
    main_workflow_file: str = Field(
        description='Path to the main workflow file within the bundle'
    ),
) -> Dict[str, Any]:
    """Lint multi-file WDL or CWL workflow bundles and return validation findings.

    This tool validates multi-file workflow bundles using appropriate linting tools:
    - WDL workflows: Uses miniwdl package for parsing and validation with import support
    - CWL workflows: Uses cwltool package for parsing and validation with dependency resolution

    The tool creates a temporary directory structure that preserves the relative file paths,
    allowing proper resolution of imports and dependencies between workflow files.

    The tool checks for:
    - Syntax errors and parsing issues across all files
    - Missing required fields (inputs, outputs, steps)
    - Import/dependency resolution
    - Runtime requirements for tasks
    - Common workflow structure issues

    Args:
        ctx: MCP context for error reporting
        workflow_files: Dictionary mapping relative file paths to their content, a local
            directory path, a ZIP file path, or an S3 URI (s3://bucket/prefix/ or
            s3://bucket/file.zip).
        workflow_format: The workflow format ('wdl' or 'cwl')
        main_workflow_file: Path to the main workflow file within the bundle

    Returns:
        Dictionary containing:
        - status: 'success' or 'error'
        - format: The workflow format that was linted
        - main_file: The main workflow file that was processed
        - files_processed: List of all files that were processed
        - linter: Name of the linting tool used
        - raw_output: Raw output from the linter command execution
    """
    try:
        try:
            resolved = await resolve_bundle_content(workflow_files)
        except (ValueError, FileNotFoundError, PermissionError) as e:
            return await handle_tool_error(ctx, e, 'Error resolving workflow bundle')

        logger.info(f'Linting {workflow_format} workflow bundle with {len(resolved.files)} files')
        linter = get_linter(workflow_format)
        return await linter.lint_workflow_bundle(
            workflow_files=resolved.files,
            main_workflow_file=main_workflow_file,
        )
    except ValueError as e:
        # Handle unsupported workflow format from get_linter
        error_message = str(e)
        logger.error(error_message)
        await ctx.error(error_message)
        return {'status': 'error', 'message': error_message}
