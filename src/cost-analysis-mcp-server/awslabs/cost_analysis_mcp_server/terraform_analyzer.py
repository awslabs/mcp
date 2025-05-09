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

"""Terraform Project Analyzer.

This module provides functionality for analyzing Terraform projects to identify AWS services
and their configurations.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TerraformAnalyzer:
    """Analyzes Terraform projects to identify AWS services and configurations."""

    def __init__(self, project_path: str):
        """Initialize the Terraform analyzer.

        Args:
            project_path: Path to the Terraform project root
        """
        self.project_path = Path(project_path)

    def _find_aws_services_from_module(
        self, source: str, variables: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Find AWS services used by a module based on its source and variables.

        Args:
            source: The module source path or URL
            variables: Dictionary of input variables for the module

        Returns:
            List of found AWS services
        """
        found_services = []
        # Extract service names from the module source and variables
        # instead of using hardcoded patterns

        # Debug logging
        logger.info(f'Finding AWS services from module source: {source}')
        logger.info(f'Module variables: {variables}')

        # Extract service names from the module source
        module_name = None

        # Handle terraform-aws-modules format
        if 'terraform-aws-modules/' in source:
            match = re.search(r'terraform-aws-modules/([^/]+)/aws', source)
            if match:
                module_name = match.group(1)
                logger.info(f'Extracted module name from terraform-aws-modules: {module_name}')

                # Extract service name from module name
                parts = module_name.split('-')
                if parts:
                    # Use the first part as the service name
                    service_name = parts[0]
                    logger.info(f'Extracted service name from module name: {service_name}')
                    found_services.append(
                        {
                            'name': service_name,
                            'source': 'terraform-module',
                            'provider': 'aws',
                            'configurations': [],
                            'module_source': source,
                        }
                    )

        # Handle aws-ia modules
        if 'aws-ia/' in source:
            match = re.search(r'aws-ia/([^/]+)/aws', source)
            if match:
                module_name = match.group(1)
                logger.info(f'Extracted module name from aws-ia: {module_name}')

                # Extract service name from module name
                parts = module_name.split('-')
                if parts:
                    # Use the first part as the service name
                    service_name = parts[0]
                    logger.info(f'Extracted service name from aws-ia module name: {service_name}')
                    found_services.append(
                        {
                            'name': service_name,
                            'source': 'terraform-module',
                            'provider': 'aws',
                            'configurations': [],
                            'module_source': source,
                        }
                    )

        # Handle other modules with AWS provider (e.g., namespace/module_name/aws)
        if not found_services and '/aws' in source:
            # Extract module name from the source
            match = re.search(r'([^/]+)/([^/]+)/aws', source)
            if match:
                namespace = match.group(1)
                module_name = match.group(2)
                logger.info(f'Extracted module from {namespace}/{module_name}/aws')

                # Extract service name from module name
                parts = module_name.split('-')
                if parts:
                    # Use the first part as the service name
                    service_name = parts[0]
                    logger.info(f'Extracted service name from module name: {service_name}')
                    found_services.append(
                        {
                            'name': service_name,
                            'source': 'terraform-module',
                            'provider': 'aws',
                            'configurations': [],
                            'module_source': source,
                        }
                    )

        # Handle local modules
        if not found_services and (source.startswith('./') or source.startswith('../')):
            # For local modules, we need to resolve the path relative to the project root
            try:
                # Resolve the local module path
                module_path = self.project_path / source
                if module_path.exists() and module_path.is_dir():
                    logger.info(f'Found local module directory: {module_path}')

                    # Analyze the local module directory
                    local_analyzer = TerraformAnalyzer(str(module_path))
                    local_services = []

                    # Get all Terraform files in the module directory
                    local_files = list(module_path.glob('*.tf')) + list(module_path.glob('*.hcl'))
                    for local_file in local_files:
                        try:
                            file_services = local_analyzer._analyze_file(local_file)
                            if file_services:
                                local_services.extend(file_services)
                        except Exception as e:
                            logger.warning(f'Error analyzing local module file {local_file}: {e}')

                    # Extract service names from the local module
                    for service in local_services:
                        if service['source'] == 'terraform' and service['provider'] == 'aws':
                            logger.info(f'Found AWS service in local module: {service["name"]}')
                            found_services.append(
                                {
                                    'name': service['name'],
                                    'source': 'terraform-module',
                                    'provider': 'aws',
                                    'configurations': [],
                                    'module_source': source,
                                }
                            )
            except Exception as e:
                logger.warning(f'Error analyzing local module at {source}: {e}')

        return found_services

    def _extract_module_info(
        self, content: str, start_line_idx: int
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """Extract module source and variables from module block.

        Args:
            content: The file content as a list of lines
            start_line_idx: The index of the line where the module block starts

        Returns:
            Tuple of (source, variables_dict)
        """
        lines = content.split('\n')
        source = None
        variables = {}

        # Find the opening brace
        brace_count = 0
        in_module_block = False

        for i in range(start_line_idx, len(lines)):
            line = lines[i].strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Count braces to track when we're inside the module block
            if '{' in line:
                brace_count += line.count('{')
                in_module_block = True

            if '}' in line:
                brace_count -= line.count('}')

            # We're inside the module block
            if in_module_block and brace_count > 0:
                # Look for source attribute
                source_match = re.match(r'source\s*=\s*"([^"]+)"', line)
                if source_match:
                    source = source_match.group(1)
                    logger.info(f'Found module source: {source}')

                # Look for variable assignments
                var_match = re.match(r'(\w+)\s*=\s*(.+)', line)
                if var_match and var_match.group(1) != 'source':
                    var_name = var_match.group(1)
                    var_value = var_match.group(2).strip()

                    # Remove trailing comma if present
                    if var_value.endswith(','):
                        var_value = var_value[:-1]

                    # Remove quotes if present
                    if var_value.startswith('"') and var_value.endswith('"'):
                        var_value = var_value[1:-1]

                    variables[var_name] = var_value
                    logger.info(f'Found module variable: {var_name} = {var_value}')

            # If we've exited the module block, we're done
            if in_module_block and brace_count == 0:
                break

        return source, variables

    def _analyze_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Analyze a file for AWS service usage.

        Args:
            file_path: Path to the file

        Returns:
            List of identified AWS services and their configurations
        """
        services = []
        logger.info(f'Analyzing file: {file_path}')

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.info('Successfully read file content')

            # Process line by line to handle declarations
            lines = content.split('\n')
            for i, line in enumerate(lines):
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue

                # Check for provider blocks
                if 'provider "aws"' in line or 'provider "awscc"' in line:
                    provider_type = 'aws' if 'provider "aws"' in line else 'awscc'
                    logger.info(f'Found {provider_type.upper()} provider declaration')
                    continue

                # Check for resource declarations
                resource_match = re.match(r'resource\s+"(aws_|awscc_)(\w+)"', line)
                if resource_match:
                    provider = resource_match.group(1).rstrip('_')
                    service_name = resource_match.group(2)
                    # Extract the main service name (e.g., 'lambda' from 'lambda_function')
                    main_service = service_name.split('_')[0]
                    logger.info(
                        f'Found {provider.upper()} service in resource declaration: {main_service}'
                    )
                    services.append(
                        {
                            'name': main_service,
                            'source': 'terraform',
                            'provider': provider,
                            'configurations': [],
                        }
                    )
                    continue

                # Check for data source declarations
                data_match = re.match(r'data\s+"(aws_|awscc_)(\w+)"', line)
                if data_match:
                    provider = data_match.group(1).rstrip('_')
                    service_name = data_match.group(2)
                    # Extract the main service name
                    main_service = service_name.split('_')[0]
                    logger.info(
                        f'Found {provider.upper()} service in data source declaration: {main_service}'
                    )
                    services.append(
                        {
                            'name': main_service,
                            'source': 'terraform',
                            'provider': provider,
                            'configurations': [],
                        }
                    )
                    continue

                # Check for module blocks
                module_match = re.match(r'module\s+"([^"]+)"\s*\{', line)
                if module_match:
                    module_name = module_match.group(1)
                    logger.info(f'Found module declaration: {module_name}')

                    # Extract module source and variables
                    source, variables = self._extract_module_info(content, i)

                    if source:
                        # Find AWS services from module source and variables
                        found_services = self._find_aws_services_from_module(source, variables)

                        if found_services:
                            services.extend(found_services)
                        else:
                            # If we couldn't find any services, add a generic module entry
                            logger.info(f'Could not find AWS services for module: {module_name}')
                            services.append(
                                {
                                    'name': module_name,
                                    'source': 'terraform-module',
                                    'provider': 'unknown',
                                    'configurations': [],
                                    'module_name': module_name,
                                    'module_source': source,
                                }
                            )

        except Exception as e:
            logger.warning(f'Error analyzing file {file_path}: {e}')

        return services

    async def analyze_project(self) -> Dict[str, Any]:
        """Analyze the Terraform project to identify AWS services and their configurations.

        Returns:
            Dictionary containing identified services and their configurations
        """
        logger.info('Starting project analysis')

        # Check if project path exists
        if not self.project_path.exists():
            logger.error(f'Project path does not exist: {self.project_path}')
            error_msg = f'Error: Project path does not exist: {self.project_path}'
            logger.error(error_msg)
            return {
                'status': 'error',
                'services': [],
                'message': error_msg,
                'details': {
                    'services': [],
                    'project_path': str(self.project_path),
                    'analysis_type': 'terraform',
                    'error': 'Path not found',
                },
            }

        all_services = []

        # Get all Terraform files in the project
        source_files = list(self.project_path.rglob('*.tf')) + list(
            self.project_path.rglob('*.hcl')
        )
        logger.info(f'Found source files: {source_files}')

        for file_path in source_files:
            logger.info(f'Analyzing file: {file_path}')
            try:
                file_services = self._analyze_file(file_path)
                if file_services:
                    logger.info(f'Found services in {file_path}: {file_services}')
                    all_services.extend(file_services)
            except Exception as e:
                logger.error(f'Error analyzing {file_path}: {e}')

        # Debug logging for all services
        logger.info(f'All services before deduplication: {all_services}')

        # Deduplicate services by name and source
        seen_services = set()
        unique_services = []
        for service in all_services:
            # Create a unique key based on name and source
            service_key = f'{service["name"]}_{service["source"]}'
            if service_key not in seen_services:
                seen_services.add(service_key)
                unique_services.append(service)

        logger.info(f'Found {len(unique_services)} unique services')
        logger.info(f'Unique services: {unique_services}')

        # Return in the format expected by the wrapper
        result = {
            'status': 'success',
            'services': unique_services,
            'message': f'Analyzed Terraform project at {self.project_path}',
            'details': {
                'services': unique_services,
                'project_path': str(self.project_path),
                'analysis_type': 'terraform',
            },
        }

        logger.info(f'Returning result: {result}')
        return result


async def analyze_terraform_project(project_path: str) -> Dict[str, Any]:
    """Analyze a Terraform project to identify AWS services.

    Args:
        project_path: Path to the Terraform project root

    Returns:
        Dictionary containing identified services and their configurations
    """
    logger.info(f'Starting analysis for project at {project_path}')
    analyzer = TerraformAnalyzer(project_path)
    result = await analyzer.analyze_project()
    logger.info(f'Analysis complete, result: {result}')
    return result
