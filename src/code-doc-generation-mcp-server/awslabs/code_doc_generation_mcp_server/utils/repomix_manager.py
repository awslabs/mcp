"""Manager for repomix operations and output parsing."""

import logging
import re
import subprocess
from mcp.server.fastmcp import Context
from pathlib import Path
from typing import Any, Dict, Optional


# Set up logging
logging.basicConfig(level=logging.INFO)


class RepomixManager:
    """Manages repomix operations including running analysis and parsing output."""

    def __init__(self):
        """Initialize RepomixManager with logger."""
        self.logger = logging.getLogger(__name__)

    def extract_directory_structure(self, repomix_output: str) -> Optional[str]:
        """Extract directory structure from repomix output file.

        Args:
            repomix_output: Content of the repomix output file

        Returns:
            String containing the directory structure or None if not found
        """
        # Extract directory structure - match the format in the repomix output

        # Pattern: Directory structure directly after the heading until the next heading
        dir_structure_match = re.search(
            r'# Directory Structure\s+(.*?)(?=\n# |\Z)', repomix_output, re.DOTALL
        )
        if dir_structure_match:
            return dir_structure_match.group(1).strip()

        return None

    def parse_file_stats(self, line: str) -> Dict[str, int]:
        """Parse a file statistics line into character and token counts."""
        match = re.match(r'.*\((\d+) chars, (\d+) tokens\)', line)
        if match:
            return {'chars': int(match.group(1)), 'tokens': int(match.group(2))}
        return {'chars': 0, 'tokens': 0}

    def parse_output(self, stdout: str) -> Dict[str, Any]:
        """Parse repomix stdout into structured metadata.

        Args:
            stdout: Raw stdout from repomix command

        Returns:
            Dict containing parsed metadata including:
            - top_files: List of files with their stats
            - security: Security check results
            - summary: Overall pack summary
        """
        lines = stdout.split('\n')
        metadata = {
            'top_files': [],
            'security': {'status': 'unknown'},
            'summary': {'total_files': 0, 'total_chars': 0, 'total_tokens': 0},
        }

        in_top_files = False
        in_security = False
        in_summary = False

        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue

            # Check section headers
            if '📈 Top 5 Files' in line:
                in_top_files = True
                in_security = False
                in_summary = False
                continue
            elif '🔎 Security Check' in line:
                in_top_files = False
                in_security = True
                in_summary = False
                continue
            elif '📊 Pack Summary' in line:
                in_top_files = False
                in_security = False
                in_summary = True
                continue

            # Parse top files
            if in_top_files and line.startswith('  '):
                parts = line.strip().split('  ')
                if len(parts) >= 2:
                    file_path = parts[-1].strip('() ')
                    stats = self.parse_file_stats(line)
                    metadata['top_files'].append({'path': file_path, **stats})

            # Parse security check
            elif in_security and '✔' in line:
                metadata['security'] = {
                    'status': 'passed',
                    'message': line.replace('✔', '').strip(),
                }

            # Parse summary
            elif in_summary:
                if 'Total Files:' in line:
                    metadata['summary']['total_files'] = int(re.search(r'(\d+)', line).group(1))
                elif 'Total Chars:' in line:
                    metadata['summary']['total_chars'] = int(re.search(r'(\d+)', line).group(1))
                elif 'Total Tokens:' in line:
                    metadata['summary']['total_tokens'] = int(re.search(r'(\d+)', line).group(1))

        return metadata

    async def prepare_repository(
        self, project_root: str | Path, output_path: str | Path, ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Prepare repository for documentation by consolidating code.

        This function consolidates the repository code using repomix and handles various
        error cases that might occur during the process. It also handles chunking of large
        outputs to prevent memory issues.

        Args:
            project_root: Path to the project to prepare
            output_path: Path where output files should be saved
            ctx: Optional MCP context for progress reporting

        Returns:
            Dict containing consolidated code and metadata

        Raises:
            ValueError: If project path is invalid or output path is not writable
            RuntimeError: If repomix preparation fails
        """
        try:
            # Validate project path
            project_path = Path(project_root)
            if not project_path.exists():
                raise ValueError(f'Project path does not exist: {project_path}')
            if not project_path.is_dir():
                raise ValueError(f'Project path is not a directory: {project_path}')

            # Get project name from path
            project_name = project_path.name

            # Validate and create output directory
            output_dir = Path(output_path)
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                # Test if directory is writable
                self.logger.info(f'output_dir type {type(output_dir)}')
                test_file = output_dir / '.write_test'
                test_file.touch()
                test_file.unlink()
            except (OSError, IOError) as e:
                raise ValueError(f'Output directory is not writable: {output_dir}\nError: {e}')

            # Run repomix to prepare repository
            self.logger.info(f'Preparing repository: {project_path}')
            if ctx:
                ctx.info(f'Running repomix on {project_path}')

            try:
                # Save repomix output to a file
                repomix_output_file = output_dir / 'repomix_output.md'

                ignore_patterns = (
                    '**/*.svg,**/*.drawio,**/.*,**/.*/**, **/cdk.out, **/cdk.out/**, **/**/cdk.out/**, '
                    'packages/cdk_infra/cdk.out,packages/cdk_infra/cdk.out/**, **/__init__.py,**/test/**,'
                    '**/__snapshots__/**,**/*.test.ts,**/dist/**,**/node_modules/**,**/.projen/**,'
                    '**/.husky/**,**/.nx/**,**/cdk.out/**,**/*.d.ts,**/*.js.map,**/*.tsbuildinfo,'
                    '**/coverage/**,**/*.pyc,**/__pycache__/**,**/venv/**,**/.venv/**,**/build/**,'
                    '**/out/**,**/.git/**,**/.github/**,**/*.min.js,**/*.min.css,**/generated-docs/**'
                )

                result = subprocess.run(
                    [
                        'repomix',
                        str(project_path),
                        '--style',
                        'markdown',
                        '--output',
                        str(repomix_output_file),
                        '--ignore',
                        ignore_patterns,
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )

                if result.stderr:
                    self.logger.warning(f'Repomix warnings: {result.stderr}')
                    if ctx:
                        ctx.warning(f'Repomix warnings: {result.stderr}')

                # Read the repomix output from the file
                repomix_output = repomix_output_file.read_text()

                # Parse metadata and handle content
                metadata = self.parse_output(result.stdout)

                # Debug: Log the repomix output to see what it contains
                self.logger.info(f'Repomix output length: {len(repomix_output)}')
                self.logger.info(f'Repomix output first 500 chars: {repomix_output[:500]}')

                # Check if the output contains the directory structure section
                if '# Directory Structure' in repomix_output:
                    self.logger.info("Found '# Directory Structure' in repomix output")
                else:
                    self.logger.warning("Could not find '# Directory Structure' in repomix output")

                # Extract directory structure from the file content
                directory_structure = self.extract_directory_structure(repomix_output)

                if directory_structure:
                    self.logger.info(
                        f'Successfully extracted directory structure, length: {len(directory_structure)}'
                    )
                    if ctx:
                        ctx.info('Extracted directory structure from repomix output')
                else:
                    self.logger.warning(
                        'Failed to extract directory structure from repomix output'
                    )
                    if ctx:
                        ctx.warning('Failed to extract directory structure from repomix output')

                # Save structured analysis with metadata and directory structure
                analysis_data = {
                    'stderr': result.stderr if result.stderr else None,
                    'output_dir': str(output_dir),
                    'repomix_output': result.stdout,  # Include the raw repomix output
                    'project_info': {
                        'path': str(project_path),
                        'name': project_name,
                    },
                    'metadata': metadata,  # Include repomix metadata directly
                    'directory_structure': directory_structure,  # Include extracted directory structure
                }

                return analysis_data

            except Exception as e:
                error_msg = f'Error running repomix: {e}'
                self.logger.error(error_msg)
                if ctx:
                    ctx.error(error_msg)
                raise RuntimeError(error_msg)

        except Exception as e:
            error_msg = f'Unexpected error during preparation: {e}'
            self.logger.error(error_msg)
            if ctx:
                ctx.error(error_msg)
            raise RuntimeError(error_msg)
