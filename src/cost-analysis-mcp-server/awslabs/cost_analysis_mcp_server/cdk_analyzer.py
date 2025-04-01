"""CDK Project Analyzer.

This module provides functionality for analyzing CDK projects to identify AWS services
and their configurations.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CDKAnalyzer:
    """Analyzes CDK projects to identify AWS services and configurations."""

    def __init__(self, project_path: str):
        """Initialize the CDK analyzer.

        Args:
            project_path: Path to the CDK project root
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
        logger.info(f"Analyzing file: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                logger.info("Successfully read file content")

            # Process line by line to handle imports
            lines = content.split("\n")
            in_import_block = False

            for line in lines:
                line = line.strip()

                # Python: Start of import block
                if line.startswith("from aws_cdk import ("):
                    in_import_block = True
                    continue

                # Python: End of import block
                if in_import_block and line.startswith(")"):
                    in_import_block = False
                    continue

                # Python: Process lines in import block
                if in_import_block:
                    if "aws_" in line:
                        # Extract service name from aws_X as Y format
                        match = re.match(r"\s*aws_(\w+)\s+as\s+\w+", line)
                        if match:
                            service_name = match.group(1)
                            logger.info(
                                f"Found AWS service in import block: {service_name}"
                            )
                            services.append(
                                {
                                    "name": service_name,
                                    "source": "cdk",
                                    "configurations": [],
                                }
                            )
                    continue

                # Python: Process direct imports
                if line.startswith("from aws_cdk.aws_"):
                    match = re.match(r"from\s+aws_cdk\.aws_(\w+)\s+import", line)
                    if match:
                        service_name = match.group(1)
                        logger.info(
                            f"Found AWS service in direct import: {service_name}"
                        )
                        services.append(
                            {
                                "name": service_name,
                                "source": "cdk",
                                "configurations": [],
                            }
                        )

                # TypeScript: Process imports from aws-cdk-lib/aws-*
                if "aws-cdk-lib/aws-" in line:
                    match = re.match(
                        r'.*from\s+[\'"]aws-cdk-lib/aws-(\w+)[\'"].*', line
                    )
                    if match:
                        service_name = match.group(1)
                        logger.info(
                            f"Found AWS service in TypeScript import: {service_name}"
                        )
                        services.append(
                            {
                                "name": service_name,
                                "source": "cdk",
                                "configurations": [],
                            }
                        )

        except Exception as e:
            logger.warning(f"Error analyzing file {file_path}: {e}")

        return services

    async def analyze_project(self) -> Dict[str, Any]:
        """Analyze the CDK project to identify AWS services and their configurations.

        Returns:
            Dictionary containing identified services and their configurations
        """
        logger.info("Starting project analysis")
        all_services = []

        # Get all Python and TypeScript files in the project
        source_files = list(self.project_path.rglob("*.py")) + list(
            self.project_path.rglob("*.ts")
        )
        logger.info(f"Found source files: {source_files}")

        for file_path in source_files:
            if file_path.name != "__init__.py":
                logger.info(f"Analyzing file: {file_path}")
                try:
                    file_services = self._analyze_file(file_path)
                    if file_services:
                        logger.info(f"Found services in {file_path}: {file_services}")
                        all_services.extend(file_services)
                except Exception as e:
                    logger.error(f"Error analyzing {file_path}: {e}")

        # Deduplicate services by name
        seen_services = set()
        unique_services = []
        for service in all_services:
            if service["name"] not in seen_services:
                seen_services.add(service["name"])
                unique_services.append(service)

        logger.info(f"Found {len(unique_services)} unique services")

        # Return in the format expected by the wrapper
        result = {
            "status": "success",
            "services": unique_services,
            "message": f"Analyzed CDK project at {self.project_path}",
            "details": {
                "services": unique_services,
                "project_path": str(self.project_path),
                "analysis_type": "cdk",
            },
        }

        logger.info(f"Returning result: {result}")
        return result


async def analyze_cdk_project(project_path: str) -> Dict[str, Any]:
    """Analyze a CDK project to identify AWS services.

    Args:
        project_path: Path to the CDK project root

    Returns:
        Dictionary containing identified services and their configurations
    """
    logger.info(f"Starting analysis for project at {project_path}")
    analyzer = CDKAnalyzer(project_path)
    result = await analyzer.analyze_project()
    logger.info(f"Analysis complete, result: {result}")
    return result
