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

"""Helper tools for the AWS HealthOmics MCP server."""

import botocore
import botocore.exceptions
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    create_zip_file,
    encode_to_base64,
    get_aws_session,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict, Optional


async def package_workflow(
    ctx: Context,
    main_file_content: str = Field(
        ...,
        description='Content of the main workflow file',
    ),
    main_file_name: str = Field(
        'main.wdl',
        description='Name of the main workflow file',
    ),
    additional_files: Optional[Dict[str, str]] = Field(
        None,
        description='Dictionary of additional files (filename: content)',
    ),
) -> str:
    """Package workflow definition files into a base64-encoded ZIP.

    Args:
        ctx: MCP context for error reporting
        main_file_content: Content of the main workflow file
        main_file_name: Name of the main workflow file (default: main.wdl)
        additional_files: Dictionary of additional files (filename: content)

    Returns:
        Base64-encoded ZIP file containing the workflow definition
    """
    try:
        # Create a dictionary of files
        files = {main_file_name: main_file_content}

        if additional_files:
            files.update(additional_files)

        # Create ZIP file
        zip_data = create_zip_file(files)

        # Encode to base64
        base64_data = encode_to_base64(zip_data)

        return base64_data
    except Exception as e:
        error_message = f'Error packaging workflow: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        raise


async def get_supported_regions(
    ctx: Context,
) -> Dict[str, Any]:
    """Get the list of AWS regions where HealthOmics is available.

    Args:
        ctx: MCP context for error reporting

    Returns:
        Dictionary containing the list of supported region codes and the total count
        of regions where HealthOmics is available
    """
    try:
        # Create a boto3 SSM client
        session = get_aws_session()
        ssm_client = session.client('ssm')

        # Get the parameters from the SSM parameter store
        response = ssm_client.get_parameters_by_path(
            Path='/aws/service/global-infrastructure/services/omics/regions'
        )

        # Extract the region values
        regions = [param['Value'] for param in response['Parameters']]

        # If no regions found, use the hardcoded list as fallback
        if not regions:
            from awslabs.aws_healthomics_mcp_server.consts import HEALTHOMICS_SUPPORTED_REGIONS

            regions = HEALTHOMICS_SUPPORTED_REGIONS
            logger.warning('No regions found in SSM parameter store. Using hardcoded region list.')

        return {'regions': sorted(regions), 'count': len(regions)}
    except botocore.exceptions.BotoCoreError as e:
        error_message = f'AWS error retrieving supported regions: {str(e)}'
        logger.error(error_message)
        logger.info('Using hardcoded region list as fallback')

        # Use hardcoded list as fallback
        from awslabs.aws_healthomics_mcp_server.consts import HEALTHOMICS_SUPPORTED_REGIONS

        return {
            'regions': sorted(HEALTHOMICS_SUPPORTED_REGIONS),
            'count': len(HEALTHOMICS_SUPPORTED_REGIONS),
            'note': 'Using hardcoded region list due to error: ' + str(e),
        }
    except Exception as e:
        error_message = f'Unexpected error retrieving supported regions: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)

        # Use hardcoded list as fallback
        from awslabs.aws_healthomics_mcp_server.consts import HEALTHOMICS_SUPPORTED_REGIONS

        return {
            'regions': sorted(HEALTHOMICS_SUPPORTED_REGIONS),
            'count': len(HEALTHOMICS_SUPPORTED_REGIONS),
            'note': 'Using hardcoded region list due to error: ' + str(e),
        }
