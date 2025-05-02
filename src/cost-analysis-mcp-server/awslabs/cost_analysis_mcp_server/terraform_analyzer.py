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
from typing import Any, Dict, List


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

            # Process line by line to handle resource declarations
            lines = content.split('\n')

            for line in lines:
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue

                # Check for AWS provider block
                if 'provider "aws"' in line:
                    logger.info('Found AWS provider declaration')
                    continue

                # Check for resource declarations
                resource_match = re.match(r'resource\s+"aws_(\w+)"', line)
                if resource_match:
                    service_name = resource_match.group(1)
                    # Extract the main service name (e.g., 'lambda' from 'lambda_function')
                    main_service = service_name.split('_')[0]
                    logger.info(f'Found AWS service in resource declaration: {main_service}')
                    services.append(
                        {
                            'name': main_service,
                            'source': 'terraform',
                            'configurations': [],
                        }
                    )
                    continue

                # Check for data source declarations
                data_match = re.match(r'data\s+"aws_(\w+)"', line)
                if data_match:
                    service_name = data_match.group(1)
                    # Extract the main service name
                    main_service = service_name.split('_')[0]
                    logger.info(f'Found AWS service in data source declaration: {main_service}')
                    services.append(
                        {
                            'name': main_service,
                            'source': 'terraform',
                            'configurations': [],
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

        # Deduplicate services by name
        seen_services = set()
        unique_services = []
        for service in all_services:
            if service['name'] not in seen_services:
                seen_services.add(service['name'])
                unique_services.append(service)

        logger.info(f'Found {len(unique_services)} unique services')

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
