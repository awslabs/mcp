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

# Import linting dependencies
import cwltool
import cwltool.load_tool
import cwltool.main

# Import nest_asyncio to handle nested event loops
import nest_asyncio
import tempfile
import WDL
import WDL.CLI
from cwltool.context import LoadingContext
from loguru import logger
from mcp.server.fastmcp import Context
from pathlib import Path
from pydantic import Field
from typing import Any, Dict, Optional


nest_asyncio.apply()


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
        try:
            # Create temporary file for the WDL content
            with tempfile.NamedTemporaryFile(mode='w', suffix='.wdl', delete=False) as tmp_file:
                tmp_file.write(content)
                tmp_path = Path(tmp_file.name)

            try:
                # Parse and validate the WDL document
                # Handle potential event loop conflicts
                try:
                    doc = WDL.load(str(tmp_path))
                except RuntimeError as e:
                    if 'event loop' in str(e).lower() or 'already running' in str(e).lower():
                        # Try to handle nested event loop issues
                        logger.info('Attempting to resolve event loop conflict with nest_asyncio')
                        doc = WDL.load(str(tmp_path))
                    else:
                        raise

                # Run basic validation
                findings = []
                warnings = []

                # Check for common issues
                if hasattr(doc, 'workflow') and doc.workflow:
                    workflow = doc.workflow

                    # Check for missing inputs
                    if not workflow.available_inputs:
                        warnings.append(
                            {
                                'type': 'warning',
                                'message': 'Workflow has no inputs defined',
                                'location': 'workflow',
                            }
                        )

                    # Check for missing outputs
                    if not workflow.outputs:
                        warnings.append(
                            {
                                'type': 'warning',
                                'message': 'Workflow has no outputs defined',
                                'location': 'workflow',
                            }
                        )

                # Check for tasks
                if hasattr(doc, 'tasks') and doc.tasks:
                    for task in doc.tasks:
                        # Check for missing runtime requirements
                        if not task.runtime:
                            warnings.append(
                                {
                                    'type': 'warning',
                                    'message': f'Task "{task.name}" has no runtime requirements defined',
                                    'location': f'task.{task.name}',
                                }
                            )

                return {
                    'status': 'success',
                    'format': 'wdl',
                    'filename': filename or tmp_path.name,
                    'valid': True,
                    'findings': findings,
                    'warnings': warnings,
                    'summary': {
                        'total_issues': len(findings) + len(warnings),
                        'errors': len(findings),
                        'warnings': len(warnings),
                    },
                    'linter': 'miniwdl',
                }

            except WDL.Error.ValidationError as e:
                # Handle WDL validation errors
                findings = []
                for error in e.errors if hasattr(e, 'errors') else [e]:
                    findings.append(
                        {
                            'type': 'error',
                            'message': str(error),
                            'location': getattr(error, 'pos', {}).get('filename', 'unknown')
                            if hasattr(error, 'pos')
                            else 'unknown',
                            'line': getattr(error, 'pos', {}).get('line', None)
                            if hasattr(error, 'pos')
                            else None,
                            'column': getattr(error, 'pos', {}).get('column', None)
                            if hasattr(error, 'pos')
                            else None,
                        }
                    )

                return {
                    'status': 'validation_failed',
                    'format': 'wdl',
                    'filename': filename or tmp_path.name,
                    'valid': False,
                    'findings': findings,
                    'warnings': [],
                    'summary': {
                        'total_issues': len(findings),
                        'errors': len(findings),
                        'warnings': 0,
                    },
                    'linter': 'miniwdl',
                }

            except Exception as e:
                return {
                    'status': 'error',
                    'format': 'wdl',
                    'filename': filename or tmp_path.name,
                    'message': f'Failed to parse WDL: {str(e)}',
                    'linter': 'miniwdl',
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
        try:
            # Create temporary file for the CWL content
            with tempfile.NamedTemporaryFile(mode='w', suffix='.cwl', delete=False) as tmp_file:
                tmp_file.write(content)
                tmp_path = Path(tmp_file.name)

            try:
                # Set up loading context
                loading_context = LoadingContext()
                loading_context.strict = True  # Enable strict validation

                # Load and validate the CWL document
                # Handle potential event loop conflicts
                try:
                    tool = cwltool.load_tool.load_tool(str(tmp_path), loading_context)
                except RuntimeError as e:
                    if 'event loop' in str(e).lower() or 'already running' in str(e).lower():
                        # Try to handle nested event loop issues
                        logger.info('Attempting to resolve event loop conflict with nest_asyncio')
                        tool = cwltool.load_tool.load_tool(str(tmp_path), loading_context)
                    else:
                        raise

                findings = []
                warnings = []

                # Basic validation checks
                if hasattr(tool, 'tool') and tool.tool:
                    cwl_tool = tool.tool

                    # Check for required fields
                    if 'inputs' not in cwl_tool or not cwl_tool['inputs']:
                        warnings.append(
                            {
                                'type': 'warning',
                                'message': 'Workflow has no inputs defined',
                                'location': 'workflow',
                            }
                        )

                    if 'outputs' not in cwl_tool or not cwl_tool['outputs']:
                        warnings.append(
                            {
                                'type': 'warning',
                                'message': 'Workflow has no outputs defined',
                                'location': 'workflow',
                            }
                        )

                    # Check for steps in workflow
                    if cwl_tool.get('class') == 'Workflow':
                        if 'steps' not in cwl_tool or not cwl_tool['steps']:
                            warnings.append(
                                {
                                    'type': 'warning',
                                    'message': 'Workflow has no steps defined',
                                    'location': 'workflow',
                                }
                            )
                        else:
                            # Check each step
                            for step_name, step in cwl_tool['steps'].items():
                                if 'run' not in step:
                                    findings.append(
                                        {
                                            'type': 'error',
                                            'message': f'Step "{step_name}" is missing required "run" field',
                                            'location': f'steps.{step_name}',
                                        }
                                    )

                return {
                    'status': 'success',
                    'format': 'cwl',
                    'filename': filename or tmp_path.name,
                    'valid': True,
                    'findings': findings,
                    'warnings': warnings,
                    'summary': {
                        'total_issues': len(findings) + len(warnings),
                        'errors': len(findings),
                        'warnings': len(warnings),
                    },
                    'linter': 'cwltool',
                }

            except Exception as e:
                # Handle CWL validation errors
                error_msg = str(e)
                findings = [{'type': 'error', 'message': error_msg, 'location': 'document'}]

                return {
                    'status': 'validation_failed',
                    'format': 'cwl',
                    'filename': filename or tmp_path.name,
                    'valid': False,
                    'findings': findings,
                    'warnings': [],
                    'summary': {
                        'total_issues': len(findings),
                        'errors': len(findings),
                        'warnings': 0,
                    },
                    'linter': 'cwltool',
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
                    # Parse and validate the WDL document with imports
                    # Handle potential event loop conflicts
                    try:
                        doc = WDL.load(str(main_file_path))
                    except RuntimeError as e:
                        if 'event loop' in str(e).lower() or 'already running' in str(e).lower():
                            # Try to handle nested event loop issues
                            logger.info(
                                'Attempting to resolve event loop conflict with nest_asyncio'
                            )
                            doc = WDL.load(str(main_file_path))
                        else:
                            raise

                    # Run basic validation
                    findings = []
                    warnings = []

                    # Check for common issues in main workflow
                    if hasattr(doc, 'workflow') and doc.workflow:
                        workflow = doc.workflow

                        # Check for missing inputs
                        if not workflow.available_inputs:
                            warnings.append(
                                {
                                    'type': 'warning',
                                    'message': 'Workflow has no inputs defined',
                                    'location': 'workflow',
                                    'file': main_workflow_file,
                                }
                            )

                        # Check for missing outputs
                        if not workflow.outputs:
                            warnings.append(
                                {
                                    'type': 'warning',
                                    'message': 'Workflow has no outputs defined',
                                    'location': 'workflow',
                                    'file': main_workflow_file,
                                }
                            )

                    # Check for tasks across all files
                    all_tasks = []
                    if hasattr(doc, 'tasks'):
                        all_tasks.extend(doc.tasks)

                    # Check imported documents for tasks
                    for imported_doc in getattr(doc, 'imports', []):
                        if hasattr(imported_doc, 'tasks'):
                            all_tasks.extend(imported_doc.tasks)

                    for task in all_tasks:
                        # Check for missing runtime requirements
                        if not task.runtime:
                            warnings.append(
                                {
                                    'type': 'warning',
                                    'message': f'Task "{task.name}" has no runtime requirements defined',
                                    'location': f'task.{task.name}',
                                    'file': getattr(task, 'pos', {}).get('filename', 'unknown')
                                    if hasattr(task, 'pos')
                                    else 'unknown',
                                }
                            )

                    return {
                        'status': 'success',
                        'format': 'wdl',
                        'main_file': main_workflow_file,
                        'files_processed': list(workflow_files.keys()),
                        'valid': True,
                        'findings': findings,
                        'warnings': warnings,
                        'summary': {
                            'total_issues': len(findings) + len(warnings),
                            'errors': len(findings),
                            'warnings': len(warnings),
                            'files_count': len(workflow_files),
                        },
                        'linter': 'miniwdl',
                    }

                except WDL.Error.ValidationError as e:
                    # Handle WDL validation errors
                    findings = []
                    for error in e.errors if hasattr(e, 'errors') else [e]:
                        error_file = (
                            getattr(error, 'pos', {}).get('filename', 'unknown')
                            if hasattr(error, 'pos')
                            else 'unknown'
                        )
                        # Convert absolute path back to relative path
                        if error_file.startswith(str(tmp_path)):
                            error_file = str(Path(error_file).relative_to(tmp_path))

                        findings.append(
                            {
                                'type': 'error',
                                'message': str(error),
                                'location': error_file,
                                'file': error_file,
                                'line': getattr(error, 'pos', {}).get('line', None)
                                if hasattr(error, 'pos')
                                else None,
                                'column': getattr(error, 'pos', {}).get('column', None)
                                if hasattr(error, 'pos')
                                else None,
                            }
                        )

                    return {
                        'status': 'validation_failed',
                        'format': 'wdl',
                        'main_file': main_workflow_file,
                        'files_processed': list(workflow_files.keys()),
                        'valid': False,
                        'findings': findings,
                        'warnings': [],
                        'summary': {
                            'total_issues': len(findings),
                            'errors': len(findings),
                            'warnings': 0,
                            'files_count': len(workflow_files),
                        },
                        'linter': 'miniwdl',
                    }

                except Exception as e:
                    return {
                        'status': 'error',
                        'format': 'wdl',
                        'main_file': main_workflow_file,
                        'message': f'Failed to parse WDL bundle: {str(e)}',
                        'linter': 'miniwdl',
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
                    # Set up loading context
                    loading_context = LoadingContext()
                    loading_context.strict = True  # Enable strict validation

                    # Load and validate the CWL document
                    # Handle potential event loop conflicts
                    try:
                        tool = cwltool.load_tool.load_tool(str(main_file_path), loading_context)
                    except RuntimeError as e:
                        if 'event loop' in str(e).lower() or 'already running' in str(e).lower():
                            # Try to handle nested event loop issues
                            logger.info(
                                'Attempting to resolve event loop conflict with nest_asyncio'
                            )
                            tool = cwltool.load_tool.load_tool(
                                str(main_file_path), loading_context
                            )
                        else:
                            raise

                    findings = []
                    warnings = []

                    # Basic validation checks
                    if hasattr(tool, 'tool') and tool.tool:
                        cwl_tool = tool.tool

                        # Check for required fields
                        if 'inputs' not in cwl_tool or not cwl_tool['inputs']:
                            warnings.append(
                                {
                                    'type': 'warning',
                                    'message': 'Workflow has no inputs defined',
                                    'location': 'workflow',
                                    'file': main_workflow_file,
                                }
                            )

                        if 'outputs' not in cwl_tool or not cwl_tool['outputs']:
                            warnings.append(
                                {
                                    'type': 'warning',
                                    'message': 'Workflow has no outputs defined',
                                    'location': 'workflow',
                                    'file': main_workflow_file,
                                }
                            )

                        # Check for steps in workflow
                        if cwl_tool.get('class') == 'Workflow':
                            if 'steps' not in cwl_tool or not cwl_tool['steps']:
                                warnings.append(
                                    {
                                        'type': 'warning',
                                        'message': 'Workflow has no steps defined',
                                        'location': 'workflow',
                                        'file': main_workflow_file,
                                    }
                                )
                            else:
                                # Check each step
                                for step_name, step in cwl_tool['steps'].items():
                                    if 'run' not in step:
                                        findings.append(
                                            {
                                                'type': 'error',
                                                'message': f'Step "{step_name}" is missing required "run" field',
                                                'location': f'steps.{step_name}',
                                                'file': main_workflow_file,
                                            }
                                        )

                    return {
                        'status': 'success',
                        'format': 'cwl',
                        'main_file': main_workflow_file,
                        'files_processed': list(workflow_files.keys()),
                        'valid': True,
                        'findings': findings,
                        'warnings': warnings,
                        'summary': {
                            'total_issues': len(findings) + len(warnings),
                            'errors': len(findings),
                            'warnings': len(warnings),
                            'files_count': len(workflow_files),
                        },
                        'linter': 'cwltool',
                    }

                except Exception as e:
                    # Handle CWL validation errors
                    error_msg = str(e)
                    findings = [
                        {
                            'type': 'error',
                            'message': error_msg,
                            'location': 'document',
                            'file': main_workflow_file,
                        }
                    ]

                    return {
                        'status': 'validation_failed',
                        'format': 'cwl',
                        'main_file': main_workflow_file,
                        'files_processed': list(workflow_files.keys()),
                        'valid': False,
                        'findings': findings,
                        'warnings': [],
                        'summary': {
                            'total_issues': len(findings),
                            'errors': len(findings),
                            'warnings': 0,
                            'files_count': len(workflow_files),
                        },
                        'linter': 'cwltool',
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
        - status: 'success', 'validation_failed', or 'error'
        - format: The workflow format that was linted
        - valid: Boolean indicating if the workflow is valid
        - findings: List of errors found during linting
        - warnings: List of warnings found during linting
        - summary: Summary statistics of issues found
        - linter: Name of the linting tool used
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
        - status: 'success', 'validation_failed', or 'error'
        - format: The workflow format that was linted
        - main_file: The main workflow file that was processed
        - files_processed: List of all files that were processed
        - valid: Boolean indicating if the workflow bundle is valid
        - findings: List of errors found during linting
        - warnings: List of warnings found during linting
        - summary: Summary statistics including file count and issues found
        - linter: Name of the linting tool used
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
