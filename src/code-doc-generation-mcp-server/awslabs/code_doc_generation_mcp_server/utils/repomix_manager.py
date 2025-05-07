# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""Manager for repomix operations and output parsing."""

import logging
import re
import subprocess  # Always import subprocess for fallback
import tempfile
from mcp.server.fastmcp import Context
from pathlib import Path
from typing import Any, Dict, Optional, Union

# Import repomix as a module
try:
    from repomix import RepoProcessor, RepomixConfig
    REPOMIX_MODULE_AVAILABLE = True
except ImportError:
    REPOMIX_MODULE_AVAILABLE = False
    logging.warning("Repomix module import failed, falling back to subprocess")


# Set up logging
logging.basicConfig(level=logging.INFO)


class RepomixManager:
    """Manages repomix operations including running analysis and parsing output."""

    def __init__(self):
        """Initialize RepomixManager with logger."""
        self.logger = logging.getLogger(__name__)

    def extract_directory_structure(self, xml_path: str) -> Optional[str]:
        """Extract directory structure from repomix XML output file with enhanced error handling.

        Args:
            xml_path: Path to the XML output file from repomix

        Returns:
            String containing the directory structure or None if not found
        """
        import xml.etree.ElementTree as ET
        import os
        import re
        from io import StringIO
        
        self.logger.info(f"Extracting directory structure from {xml_path}")
        
        try:
            # Verify file exists and is readable
            if not os.path.exists(xml_path):
                self.logger.error(f"XML file does not exist: {xml_path}")
                return None
                
            # Report file size for debugging
            file_size = os.path.getsize(xml_path)
            self.logger.info(f"XML file size: {file_size} bytes")
            
            # Try parsing the XML structure first
            try:
                self.logger.info("Attempting XML structure parsing")
                tree = ET.parse(xml_path)
                root = tree.getroot()
                
                # Look for repository_structure element (new format)
                repo_structure = root.find('.//repository_structure')
                if repo_structure is not None:
                    self.logger.info("Found repository_structure element")
                    
                    # Convert the XML structure to a text representation
                    output = StringIO()
                    self._process_repository_structure(repo_structure, output)
                    directory_structure = output.getvalue().strip()
                    
                    if directory_structure:
                        self.logger.info(f"Extracted directory structure (length: {len(directory_structure)})")
                        return directory_structure
                
                # Fallback to looking for directory_structure element (old format)
                for xpath in ['.//directory_structure', 'directory_structure', './directory_structure']:
                    dir_elem = root.find(xpath)
                    if dir_elem is not None:
                        self.logger.info(f"Found directory_structure using xpath: {xpath}")
                        directory_structure = dir_elem.text.strip() if dir_elem.text else None
                        
                        if directory_structure:
                            self.logger.info(f"Extracted directory structure (length: {len(directory_structure)})")
                            return directory_structure
                
                # Debug: List available elements
                self.logger.info("Available top-level elements:")
                for child in root:
                    self.logger.info(f" - {child.tag}")
                    
            except Exception as e:
                self.logger.warning(f"XML parsing failed: {str(e)}")
            
            # Fallback to regex methods as last resort
            try:
                self.logger.info("Attempting regex extraction")
                with open(xml_path, 'r') as f:
                    content = f.read()
                
                # Try to find repository_structure first (new format)
                match = re.search(r'<repository_structure>(.*?)</repository_structure>', content, re.DOTALL)
                if match:
                    # We need to parse this XML snippet and convert it to a directory structure
                    try:
                        xml_snippet = f"<root>{match.group(1)}</root>"
                        snippet_root = ET.fromstring(xml_snippet)
                        output = StringIO()
                        self._process_repository_structure(snippet_root, output)
                        directory_structure = output.getvalue().strip()
                        self.logger.info(f"Extracted directory structure from repository_structure via regex (length: {len(directory_structure)})")
                        return directory_structure
                    except Exception as e:
                        self.logger.warning(f"Error processing repository_structure XML snippet: {str(e)}")
                
                # Try original directory_structure pattern
                match = re.search(r'<directory_structure>(.*?)</directory_structure>', content, re.DOTALL)
                if match:
                    directory_structure = match.group(1).strip()
                    self.logger.info(f"Extracted directory structure via regex (length: {len(directory_structure)})")
                    return directory_structure
                
                # Try to find a directory structure from file listing sections
                # Pattern for markdown code block with directory listing
                match = re.search(r'# (?:File|Directory) (?:Structure|Listing).*?```(?:\w*)\s*(.*?)```', content, re.DOTALL | re.IGNORECASE)
                if match:
                    directory_structure = match.group(1).strip()
                    self.logger.info(f"Extracted directory structure from markdown (length: {len(directory_structure)})")
                    return directory_structure
                    
                # Last resort - try to find any file listing in the document
                matches = re.findall(r'(?:bin/|src/|lib/|app/|\.py|\.js|\.ts|\.tsx|\.jsx).*?(?:\n\s+[^\n]+){1,20}', content)
                if matches:
                    # Take the longest match as it's likely the directory structure
                    best_match = max(matches, key=len)
                    if len(best_match) > 100:  # Only use if it's substantial
                        self.logger.info(f"Extracted directory structure using file pattern heuristics (length: {len(best_match)})")
                        return best_match
                
                self.logger.warning("Could not find directory structure with any regex pattern")
            except Exception as e3:
                self.logger.warning(f"Regex extraction failed: {str(e3)}")
                    
            # If all methods failed, return None
            self.logger.error("All extraction methods failed")
            return None
        
        except Exception as e:
            self.logger.error(f"Error in extract_directory_structure: {str(e)}")
            return None
    
    def _process_repository_structure(self, element, output, indent=0):
        """Process repository_structure XML element and convert to text representation.
        
        Args:
            element: XML element to process
            output: StringIO to write output
            indent: Current indentation level
        """
        # Process all children (file and directory elements)
        for child in element:
            if child.tag == 'file':
                name = child.get('name', 'unnamed_file')
                output.write(' ' * indent + name + '\n')
            elif child.tag == 'directory':
                name = child.get('name', 'unnamed_dir')
                output.write(' ' * indent + name + '/\n')
                # Process children with increased indent
                self._process_repository_structure(child, output, indent + 2)

    def parse_file_stats(self, line: str) -> Dict[str, int]:
        """Parse a file statistics line into character and token counts."""
        match = re.match(r'.*\((\d+) chars, (\d+) tokens\)', line)
        if match:
            return {'chars': int(match.group(1)), 'tokens': int(match.group(2))}
        return {'chars': 0, 'tokens': 0}

    def extract_statistics(self, xml_path: str) -> Dict[str, Any]:
        """Extract statistics directly from the XML statistics element.
        
        Args:
            xml_path: Path to the XML output file from repomix
            
        Returns:
            Dict containing statistics data or empty dict if not found
        """
        import xml.etree.ElementTree as ET
        import os
        
        try:
            if not os.path.exists(xml_path):
                self.logger.error(f"XML file does not exist: {xml_path}")
                return {}
            
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            stats_elem = root.find('.//statistics')
            if stats_elem is not None:
                self.logger.info("Found statistics element")
                
                total_files = stats_elem.find('total_files')
                total_chars = stats_elem.find('total_chars')
                total_tokens = stats_elem.find('total_tokens')
                
                return {
                    'total_files': int(total_files.text) if total_files is not None and total_files.text else 0,
                    'total_chars': int(total_chars.text) if total_chars is not None and total_chars.text else 0,
                    'total_tokens': int(total_tokens.text) if total_tokens is not None and total_tokens.text else 0,
                }
            
            self.logger.warning("Statistics element not found")
            return {}
            
        except Exception as e:
            self.logger.error(f"Error in extract_statistics: {str(e)}")
            return {}

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

            # Save repomix output to a permanent file in the output directory
            repomix_output_file = output_dir / 'repomix_output.xml'
            
            # Create the output directory if it doesn't exist
            output_dir.mkdir(parents=True, exist_ok=True)

            ignore_patterns = (
                '**/*.svg,**/*.drawio,**/.*,**/.*/**, **/cdk.out, **/cdk.out/**, **/**/cdk.out/**, '
                'packages/cdk_infra/cdk.out,packages/cdk_infra/cdk.out/**, **/__init__.py,**/test/**,'
                '**/__snapshots__/**,**/*.test.ts,**/dist/**,**/node_modules/**,**/.projen/**,'
                '**/.husky/**,**/.nx/**,**/cdk.out/**,**/*.d.ts,**/*.js.map,**/*.tsbuildinfo,'
                '**/coverage/**,**/*.pyc,**/__pycache__/**,**/venv/**,**/.venv/**,**/build/**,'
                '**/out/**,**/.git/**,**/.github/**,**/*.min.js,**/*.min.css,**/generated-docs/**'
            )

            try:
                if REPOMIX_MODULE_AVAILABLE:
                    # Use repomix as a Python module
                    self.logger.info("Using repomix as a Python module")
                    if ctx:
                        ctx.info("Using repomix as a Python module")
                    
                    # Create custom configuration
                    config = RepomixConfig()
                    config.output.file_path = str(repomix_output_file)
                    config.output.style = "xml"
                    config.ignore.custom_patterns = ignore_patterns.split(',')
                    config.ignore.use_gitignore = True
                    config.security.enable_security_check = True
                    
                    # Process repository with custom config
                    processor = RepoProcessor(str(project_path), config=config)
                    result_obj = processor.process()
                    
                    # Extract metadata from result object using getattr to safely access attributes
                    security_passed = False
                    try:
                        # Safely check security status with getattr
                        security_passed = getattr(result_obj, 'security_check_passed', False)
                    except Exception:
                        self.logger.warning("Could not access security_check_passed attribute")
                        
                    metadata = {
                        'top_files': [],  # Will populate if available
                        'security': {'status': 'passed' if security_passed else 'unknown'},
                        'summary': {
                            'total_files': getattr(result_obj, 'total_files', 0),
                            'total_chars': getattr(result_obj, 'total_chars', 0),
                            'total_tokens': getattr(result_obj, 'total_tokens', 0),
                        },
                    }
                    
                    # Try to extract top files if available
                    top_files = []
                    try:
                        top_files = getattr(result_obj, 'top_files', []) or []
                    except Exception:
                        self.logger.warning("Could not access top_files attribute")
                        
                    # Process top files safely
                    for i, file_info in enumerate(top_files):
                        if i >= 5:  # Only process top 5
                            break
                        try:
                            path = getattr(file_info, 'path', 'unknown')
                            chars = getattr(file_info, 'chars', 0)
                            tokens = getattr(file_info, 'tokens', 0)
                            metadata['top_files'].append({
                                'path': path,
                                'chars': chars,
                                'tokens': tokens
                            })
                        except Exception as e:
                            self.logger.warning(f"Error processing file info: {e}")
                    
                    # Get directory structure from result or file
                    directory_structure = None
                    try:
                        directory_structure = getattr(result_obj, 'directory_structure', None)
                        if directory_structure:
                            self.logger.info(f"Extracted directory structure directly from result object (length: {len(directory_structure)})")
                    except Exception as e:
                        self.logger.warning(f"Could not access directory_structure attribute: {e}")
                        
                    # Fall back to extracting from file if needed
                    if not directory_structure:
                        directory_structure = self.extract_directory_structure(str(repomix_output_file))
                    
                    # Get stderr if available
                    stderr = None
                    try:
                        stderr = getattr(result_obj, 'warnings', None)
                        if stderr and ctx:
                            ctx.warning(f'Repomix warnings: {stderr}')
                    except Exception:
                        self.logger.warning("Could not access warnings attribute")
                    
                    # Create a similar output format to what we had with subprocess
                    repomix_output = ""
                    try:
                        repomix_output = getattr(result_obj, 'output', "") or ""
                    except Exception:
                        self.logger.warning("Could not access output attribute")
                    
                else:
                    # Fall back to subprocess if module import failed
                    self.logger.info("Falling back to subprocess for repomix")
                    if ctx:
                        ctx.info("Falling back to subprocess for repomix")
                    
                    # We need to import subprocess here for the fallback
                    import subprocess
                    
                    result = subprocess.run(
                        [
                            'repomix',
                            str(project_path),
                            '--ignore',
                            ignore_patterns,
                            '--style',
                            'xml',
                        ],
                        capture_output=True,
                        text=True,
                        check=True,
                    )

                    if result.stderr:
                        self.logger.warning(f'Repomix warnings: {result.stderr}')
                        if ctx:
                            ctx.warning(f'Repomix warnings: {result.stderr}')
                    
                    # Parse metadata from subprocess result
                    metadata = self.parse_output(result.stdout)
                    
                # Extract directory structure from file
                directory_structure = self.extract_directory_structure(str(repomix_output_file))
                
                # Also extract statistics directly from the XML (new format) if directory_structure was found
                if directory_structure:
                    statistics = self.extract_statistics(str(repomix_output_file))
                    if statistics:
                        metadata['summary'] = statistics
                
                # Initialize stderr and repomix_output in case they're not set
                # These could be set in the subprocess path, so only initialize if using the module path
                if 'result' in locals():  # When using subprocess path
                    stderr = result.stderr if result.stderr else None
                    repomix_output = result.stdout
                else:  # Make sure we have initial values if not using subprocess
                    stderr = stderr if 'stderr' in locals() else None
                    repomix_output = repomix_output if 'repomix_output' in locals() else ""
                
                # Read the repomix output from the permanent file
                if repomix_output_file.exists():
                    file_content = repomix_output_file.read_text()
                    self.logger.info(
                        f'Successfully read repomix output from file: {repomix_output_file}, size: {len(file_content)} bytes'
                    )
                    if ctx:
                        ctx.info(f'Successfully generated repomix output: {repomix_output_file}')
                else:
                    self.logger.error(f'Repomix output file not found: {repomix_output_file}')
                    if ctx:
                        ctx.error(f'Repomix output file not found: {repomix_output_file}')

                # Debug: Log the repomix output info
                self.logger.info(f'Repomix output length: {len(repomix_output)}')
                if repomix_output:
                    self.logger.info(f'Repomix output first 500 chars: {repomix_output[:500]}')

                # Basic notification about directory structure extraction status
                if directory_structure and ctx:
                    ctx.info('Extracted directory structure from repomix output')
                elif ctx:
                    ctx.warning('Failed to extract directory structure from repomix output')

                # Save structured analysis with metadata and directory structure
                analysis_data = {
                    'stderr': stderr,
                    'output_dir': str(output_dir),
                    'repomix_output': repomix_output,
                    'project_info': {
                        'path': str(project_path),
                        'name': project_name,
                    },
                    'metadata': metadata,
                    'directory_structure': directory_structure,
                }

                # Special case: Force directory structure even if extraction failed
                if 'file_structure' in analysis_data and directory_structure:
                    analysis_data['file_structure']['directory_structure'] = directory_structure

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
