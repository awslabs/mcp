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
"""Implementation for terraform_awscc_provider_resources_listing resource."""

import sys
from loguru import logger
from pathlib import Path


# Configure logger for enhanced diagnostics with stacktraces
logger.configure(
    handlers=[
        {
            'sink': sys.stderr,
            'backtrace': True,
            'diagnose': True,
            'format': '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>',
        }
    ]
)

# Path to the static markdown file
STATIC_RESOURCES_PATH = (
    Path(__file__).parent.parent.parent / 'static' / 'AWSCC_PROVIDER_RESOURCES.md'
)


async def terraform_awscc_provider_resources_listing_impl() -> str:
    """Generate a comprehensive listing of AWSCC provider resources and data sources.

    This implementation reads from a pre-generated static markdown file instead of
    scraping the web in real-time. The static file should be generated using the
    generate_awscc_provider_resources.py script.

    Returns:
        A markdown formatted string with categorized resources and data sources
    """
    logger.info('Loading AWSCC provider resources listing from static file')

    try:
        # Check if the static file exists
        if STATIC_RESOURCES_PATH.exists():
            # Read the static file content
            with open(STATIC_RESOURCES_PATH, 'r', encoding='utf-8') as f:
                content = f.read()

            logger.info(
                f'Successfully loaded AWSCC provider resources from {STATIC_RESOURCES_PATH}'
            )
            return content
        else:
            # Send error if static file does not exist
            logger.debug(f"Static assets list file not found at '{STATIC_RESOURCES_PATH}'")
            raise Exception('Static assets list file not found')
    except Exception as e:
        logger.error(f'Error generating AWSCC provider resources listing: {e}')
        return f'# AWSCC Provider Resources Listing\n\nError generating listing: {str(e)}'
