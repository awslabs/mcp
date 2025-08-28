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

import tempfile
from loguru import logger
from mcp.server.fastmcp import Context
from pathlib import Path
from pydantic import Field
from typing import Any, Dict, Optional


class WorkflowLinter:
    """Lints WDL and CWL workflow definitions using appropriate linting tools."""

    def __init__(self):
        """Initialize the workflow linter with supported formats."""
        self.supported_formats = ['wdl', 'cwl']

    async def lint_workflow_bundle(
        self, workflow_files: Dict[str, str], workflow_format: str, main_workflow_file: str
    ) -> Dict[str, Any]:
        """Lint a multi-file workflow bundle and return findings.

        Args:
            workflow_files: Dictionary mapping file paths to their content
            workflow_format: The workflow format ('wdl' or 'cwl')
            main_workflow_file: Path to the main workflow file within the bundle

        Returns:
            Dictionary containing lint results and findings
        """
        if workflow_format.lower() not in self.supported_formats:
            return {
                'status': 'error',
                'message': f'Unsupported workflow format: {workflow_format}. Supported formats: {self.supported_formats}',
            }

        try:
            if workflow_format.lower() == 'wdl':
                return await self._lint_wdl_bundle(workflow_files, main_workflow_file)
            elif workflow_format.lower() == 'cwl':
                return await self._lint_cwl_bundle(workflow_files, main_workflow_file)
        except Exception as e:
            logger.error(f'Error linting {workflow_format} workflow bundle: {str(e)}')
            return {
                'status': 'error',
                'message': f'Failed to lint {workflow_format} workflow bundle: {str(e)}',
            }

    async def lint_workflow(
        self, workflow_content: str, workflow_format: str, filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """Lint a workflow definition and return findings.

        Args:
            workflow_content: The workflow definition content
            workflow_format: The workflow format ('wdl' or 'cwl')
            filename: Optional filename for context

        Returns:
            Dictionary containing lint results and findings
        """
        if workflow_format.lower() not in self.supported_formats:
            return {
                'status': 'error',
                'message': f'Unsupported workflow format: {workflow_format}. Supported formats: {self.supported_formats}',
            }

        try:
            if workflow_format.lower() == 'wdl':
                return await self._lint_wdl(workflow_content, filename)
            elif workflow_format.lower() == 'cwl':
                return await self._lint_cwl(workflow_content, filename)
        except Exception as e:
            logger.error(f'Error linting {workflow_format} workflow: {str(e)}')
            return {
                'status': 'error',
                'message': f'Failed to lint {workflow_format} workflow: {str(e)}',
            }

    async def _lint_wdl(self, content: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """Lint WDL workflow using miniwdl."""
        import subprocess
        import sys

        try:
            # Create temporary file for the WDL content
            with tempfile.NamedTemporaryFile(mode='w', suffix='.wdl', delete=False) as tmp_file:
                tmp_file.write(content)
                tmp_path = Path(tmp_file.name)

            try:
                # Capture raw linter output using miniwdl check command
                result = subprocess.run(
                    [sys.executable, '-m', 'WDL', 'check', str(tmp_path)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                raw_output = f'STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\nReturn code: {result.returncode}'

                return {
                    'status': 'success',
                    'format': 'wdl',
                    'filename': filename or tmp_path.name,
                    'linter': 'miniwdl',
                    'raw_output': raw_output,
                }

            except subprocess.TimeoutExpired:
                return {
                    'status': 'error',
                    'format': 'wdl',
                    'filename': filename or tmp_path.name,
                    'linter': 'miniwdl',
                    'raw_output': 'Linter execution timed out after 30 seconds',
                }
            except Exception as e:
                return {
                    'status': 'error',
                    'format': 'wdl',
                    'filename': filename or tmp_path.name,
                    'linter': 'miniwdl',
                    'raw_output': f'Failed to execute linter: {str(e)}',
                }

            finally:
                # Clean up temporary file
                try:
                    tmp_path.unlink()
                except Exception:
                    pass

        except Exception as e:
            logger.error(f'Error in WDL linting: {str(e)}')
            return {'status': 'error', 'format': 'wdl', 'message': f'WDL linting failed: {str(e)}'}

    async def _lint_cwl(self, content: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """Lint CWL workflow using cwltool."""
        import subprocess
        import sys

        try:
            # Create temporary file for the CWL content
            with tempfile.NamedTemporaryFile(mode='w', suffix='.cwl', delete=False) as tmp_file:
                tmp_file.write(content)
                tmp_path = Path(tmp_file.name)

            try:
                # Capture raw linter output using cwltool --validate
                result = subprocess.run(
                    [sys.executable, '-m', 'cwltool', '--validate', str(tmp_path)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                raw_output = f'STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\nReturn code: {result.returncode}'

                return {
                    'status': 'success',
                    'format': 'cwl',
                    'filename': filename or tmp_path.name,
                    'linter': 'cwltool',
                    'raw_output': raw_output,
                }

            except subprocess.TimeoutExpired:
                return {
                    'status': 'error',
                    'format': 'cwl',
                    'filename': filename or tmp_path.name,
                    'linter': 'cwltool',
                    'raw_output': 'Linter execution timed out after 30 seconds',
                }
            except Exception as e:
                return {
                    'status': 'error',
                    'format': 'cwl',
                    'filename': filename or tmp_path.name,
                    'linter': 'cwltool',
                    'raw_output': f'Failed to execute linter: {str(e)}',
                }

            finally:
                # Clean up temporary file
                try:
                    tmp_path.unlink()
                except Exception:
                    pass

        except Exception as e:
            logger.error(f'Error in CWL linting: {str(e)}')
            return {'status': 'error', 'format': 'cwl', 'message': f'CWL linting failed: {str(e)}'}

    async def _lint_wdl_bundle(
        self, workflow_files: Dict[str, str], main_workflow_file: str
    ) -> Dict[str, Any]:
        """Lint WDL workflow bundle using miniwdl."""
        import subprocess
        import sys

        try:
            # Create temporary directory structure
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)

                # Write all files to temporary directory maintaining structure
                for file_path, content in workflow_files.items():
                    full_path = tmp_path / file_path
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content)

                main_file_path = tmp_path / main_workflow_file

                if not main_file_path.exists():
                    return {
                        'status': 'error',
                        'format': 'wdl',
                        'message': f'Main workflow file "{main_workflow_file}" not found in provided files',
                    }

                try:
                    # Capture raw linter output using miniwdl check command
                    result = subprocess.run(
                        [sys.executable, '-m', 'WDL', 'check', str(main_file_path)],
                        capture_output=True,
                        text=True,
                        timeout=30,
                        cwd=str(tmp_path),
                    )
                    raw_output = f'STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\nReturn code: {result.returncode}'

                    return {
                        'status': 'success',
                        'format': 'wdl',
                        'main_file': main_workflow_file,
                        'files_processed': list(workflow_files.keys()),
                        'linter': 'miniwdl',
                        'raw_output': raw_output,
                    }

                except subprocess.TimeoutExpired:
                    return {
                        'status': 'error',
                        'format': 'wdl',
                        'main_file': main_workflow_file,
                        'linter': 'miniwdl',
                        'raw_output': 'Linter execution timed out after 30 seconds',
                    }
                except Exception as e:
                    return {
                        'status': 'error',
                        'format': 'wdl',
                        'main_file': main_workflow_file,
                        'message': f'Failed to execute linter: {str(e)}',
                        'linter': 'miniwdl',
                        'raw_output': f'Failed to execute linter: {str(e)}',
                    }

        except Exception as e:
            logger.error(f'Error in WDL bundle linting: {str(e)}')
            return {
                'status': 'error',
                'format': 'wdl',
                'message': f'WDL bundle linting failed: {str(e)}',
            }

    async def _lint_cwl_bundle(
        self, workflow_files: Dict[str, str], main_workflow_file: str
    ) -> Dict[str, Any]:
        """Lint CWL workflow bundle using cwltool."""
        import subprocess
        import sys

        try:
            # Create temporary directory structure
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)

                # Write all files to temporary directory maintaining structure
                for file_path, content in workflow_files.items():
                    full_path = tmp_path / file_path
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content)

                main_file_path = tmp_path / main_workflow_file

                if not main_file_path.exists():
                    return {
                        'status': 'error',
                        'format': 'cwl',
                        'message': f'Main workflow file "{main_workflow_file}" not found in provided files',
                    }

                try:
                    # Capture raw linter output using cwltool --validate
                    result = subprocess.run(
                        [sys.executable, '-m', 'cwltool', '--validate', str(main_file_path)],
                        capture_output=True,
                        text=True,
                        timeout=30,
                        cwd=str(tmp_path),
                    )
                    raw_output = f'STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\nReturn code: {result.returncode}'

                    return {
                        'status': 'success',
                        'format': 'cwl',
                        'main_file': main_workflow_file,
                        'files_processed': list(workflow_files.keys()),
                        'linter': 'cwltool',
                        'raw_output': raw_output,
                    }

                except subprocess.TimeoutExpired:
                    return {
                        'status': 'error',
                        'format': 'cwl',
                        'main_file': main_workflow_file,
                        'linter': 'cwltool',
                        'raw_output': 'Linter execution timed out after 30 seconds',
                    }
                except Exception as e:
                    return {
                        'status': 'error',
                        'format': 'cwl',
                        'main_file': main_workflow_file,
                        'message': f'Failed to execute linter: {str(e)}',
                        'linter': 'cwltool',
                        'raw_output': f'Failed to execute linter: {str(e)}',
                    }

        except Exception as e:
            logger.error(f'Error in CWL bundle linting: {str(e)}')
            return {
                'status': 'error',
                'format': 'cwl',
                'message': f'CWL bundle linting failed: {str(e)}',
            }


# Global linter instance
workflow_linter = WorkflowLinter()


async def lint_workflow_definition(
    ctx: Context,
    workflow_content: str = Field(description='The workflow definition content to lint'),
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
        workflow_content: The workflow definition content to lint
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
        logger.info(f'Linting {workflow_format} workflow definition')

        result = await workflow_linter.lint_workflow(
            workflow_content=workflow_content, workflow_format=workflow_format, filename=filename
        )

        return result

    except Exception as e:
        error_message = f'Error during workflow linting: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        return {'status': 'error', 'message': f'Workflow linting failed: {str(e)}'}


async def lint_workflow_bundle(
    ctx: Context,
    workflow_files: Dict[str, str] = Field(
        description='Dictionary mapping file paths to their content'
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
        workflow_files: Dictionary mapping relative file paths to their content
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
        logger.info(f'Linting {workflow_format} workflow bundle with {len(workflow_files)} files')

        result = await workflow_linter.lint_workflow_bundle(
            workflow_files=workflow_files,
            workflow_format=workflow_format,
            main_workflow_file=main_workflow_file,
        )

        return result

    except Exception as e:
        error_message = f'Error during workflow bundle linting: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        return {'status': 'error', 'message': f'Workflow bundle linting failed: {str(e)}'}
