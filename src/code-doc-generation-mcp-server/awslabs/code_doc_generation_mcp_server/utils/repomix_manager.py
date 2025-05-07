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

"""Manager for repomix operations with streamlined directory structure extraction."""

import time
from pathlib import Path
from typing import Any, Dict, Optional
from repomix import RepoProcessor, RepomixConfig
from mcp.server.fastmcp import Context
from loguru import logger


class RepomixManager:
    """Manages repomix operations with simplified directory structure extraction."""

    def __init__(self):
        """Initialize RepomixManager with logger."""
        self.logger = logger

    def extract_statistics(self, xml_path: str) -> Dict[str, Any]:
        """Extract statistics from repomix XML output file.

        Args:
            xml_path: Path to the XML output file from repomix

        Returns:
            Dictionary containing statistics or empty dict if not found
        """
        import xml.etree.ElementTree as ET
        import os
        
        self.logger.info(f"Extracting statistics from {xml_path}")
        
        try:
            # Verify file exists
            if not os.path.exists(xml_path):
                self.logger.error(f"XML file does not exist: {xml_path}")
                return {}

            # Parse XML
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Find statistics element
            stats_elem = root.find('.//statistics')
            if stats_elem is not None:
                self.logger.info("Found statistics element")
                stats = {}
                
                # Extract each statistic
                for child in stats_elem:
                    try:
                        # Try to convert to appropriate type (int for numeric values)
                        tag = child.tag
                        if tag in ['total_files', 'total_chars', 'total_tokens']:
                            stats[tag] = int(child.text) if child.text else 0
                        else:
                            stats[tag] = child.text
                    except (ValueError, TypeError):
                        # Fallback to string if conversion fails
                        stats[child.tag] = child.text
                
                return stats
            
            self.logger.warning("Statistics element not found in XML")
            return {}
            
        except Exception as e:
            self.logger.error(f"Error extracting statistics: {str(e)}")
            return {}

    def extract_directory_structure(self, xml_path: str) -> Optional[str]:
        """Extract directory structure from repomix XML output file.
        
        Supports both formats:
        1. Plain text in <directory_structure> element (for compatibility with tests)
        2. Nested <repository_structure> XML format (new repomix format)

        Args:
            xml_path: Path to the XML output file from repomix

        Returns:
            String containing the directory structure or None if not found
        """
        import xml.etree.ElementTree as ET
        import os
        
        self.logger.info(f"Extracting directory structure from {xml_path}")
        
        try:
            # Verify file exists
            if not os.path.exists(xml_path):
                self.logger.error(f"XML file does not exist: {xml_path}")
                return None

            # Parse XML
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # First try the old format with <directory_structure> containing plain text
            for xpath in ['.//directory_structure', 'directory_structure', './directory_structure']:
                dir_elem = root.find(xpath)
                if dir_elem is not None and dir_elem.text:
                    directory_structure = dir_elem.text.strip()
                    self.logger.info(f"Extracted directory structure using xpath: {xpath}")
                    return directory_structure
            
            # If not found, look for nested <repository_structure> format
            repo_structure = root.find('.//repository_structure')
            if repo_structure is not None:
                self.logger.info("Found repository_structure element, converting to text format")
                lines = []
                self._convert_repository_structure(repo_structure, lines)
                if lines:
                    return '\n'.join(lines)
                    
            self.logger.warning("Directory structure element not found in XML")
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting directory structure: {str(e)}")
            return None
    
    def _convert_repository_structure(self, element, lines, indent=0):
        """Recursively convert repository_structure XML to text-based representation.
        
        Args:
            element: XML element (repository_structure or a child element)
            lines: List to append text lines to
            indent: Current indentation level
        """
        # Process all children of this element
        for child in element:
            if child.tag == 'file':
                name = child.get('name', 'unnamed_file')
                lines.append(' ' * indent + name)
            elif child.tag == 'directory':
                name = child.get('name', 'unnamed_dir')
                lines.append(' ' * indent + name + '/')
                # Recursively process directory contents with increased indent
                self._convert_repository_structure(child, lines, indent + 2)

    async def prepare_repository(
        self, project_root: str | Path, output_path: str | Path, ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Prepare repository for documentation by extracting directory structure.

        Streamlined implementation that focuses only on directory structure extraction.

        Args:
            project_root: Path to the project to prepare
            output_path: Path where output files should be saved
            ctx: Optional MCP context for progress reporting

        Returns:
            Dict containing directory structure and basic metadata

        Raises:
            ValueError: If project path is invalid or output path is not writable
            RuntimeError: If repomix preparation fails
        """
        start_time = time.time()
        self.logger.info(f"Starting prepare_repository at {start_time}")
        
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
                test_file = output_dir / '.write_test'
                test_file.touch()
                test_file.unlink()
            except (OSError, IOError) as e:
                raise ValueError(f'Output directory is not writable: {output_dir}\nError: {e}')

            # Run repomix to prepare repository
            self.logger.info(f'Preparing repository: {project_path}')
            if ctx:
                ctx.info(f'Running repomix on {project_path}')

            # Save repomix output to a file in the output directory
            repomix_output_file = output_dir / 'repomix_output.xml'

            # Define standard ignore patterns
            ignore_patterns = (
                '**/*.svg,**/*.drawio,**/.*,**/.*/**, **/cdk.out, **/cdk.out/**, **/**/cdk.out/**, '
                'packages/cdk_infra/cdk.out,packages/cdk_infra/cdk.out/**, **/__init__.py,**/test/**,'
                '**/__snapshots__/**,**/*.test.ts,**/dist/**,**/node_modules/**,**/.projen/**,'
                '**/.husky/**,**/.nx/**,**/cdk.out/**,**/*.d.ts,**/*.js.map,**/*.tsbuildinfo,'
                '**/coverage/**,**/*.pyc,**/__pycache__/**,**/venv/**,**/.venv/**,**/build/**,'
                '**/.git/**,**/.github/**,**/*.min.js,**/*.min.css,**/generated-docs/**'
            )

            try:
                # Configure repomix
                config = RepomixConfig()
                config.output.file_path = str(repomix_output_file)
                config.output.style = "xml"
                config.ignore.custom_patterns = ignore_patterns.split(',')
                config.ignore.use_gitignore = False
                
                if ctx:
                    ctx.info("Using repomix to generate directory structure...")
                
                # Process repository
                processor = RepoProcessor(str(project_path), config=config)
                result_obj = processor.process()
                
                # Try to get directory structure directly from result object
                directory_structure = None
                try:
                    directory_structure = getattr(result_obj, 'directory_structure', None)
                    if directory_structure:
                        self.logger.info("Extracted directory structure directly from result object")
                except Exception as e:
                    self.logger.warning(f"Could not access directory_structure attribute: {e}")
                
                # Fall back to extracting from XML file if needed
                if not directory_structure:
                    directory_structure = self.extract_directory_structure(str(repomix_output_file))
                
                # Extract file structure from raw_analysis as a second fallback
                if not directory_structure and hasattr(result_obj, 'file_structure'):
                    try:
                        file_structure = getattr(result_obj, 'file_structure', {})
                        if isinstance(file_structure, dict) and 'directory_structure' in file_structure:
                            directory_structure = file_structure['directory_structure']
                            self.logger.info("Extracted directory structure from file_structure attribute")
                    except Exception as e:
                        self.logger.warning(f"Could not access file_structure attribute: {e}")
                
                # Update the user on status
                if directory_structure and ctx:
                    ctx.info('Successfully extracted directory structure')
                elif ctx:
                    ctx.warning('Failed to extract directory structure')

                # Return simplified analysis data
                return {
                    'output_dir': str(output_dir),
                    'project_info': {
                        'path': str(project_path),
                        'name': project_name,
                    },
                    'metadata': {
                        'summary': self.extract_statistics(str(repomix_output_file)),
                    },
                    'directory_structure': directory_structure,
                }

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
