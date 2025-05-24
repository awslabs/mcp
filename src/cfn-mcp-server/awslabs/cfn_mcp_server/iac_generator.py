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

"""CloudFormation IaC Generator tool implementation."""

import os
import json
from typing import Dict, List, Optional
from awslabs.cfn_mcp_server.aws_client import get_aws_client
from awslabs.cfn_mcp_server.errors import ClientError, handle_aws_api_error


async def create_template(
    template_name: Optional[str] = None,
    resources: Optional[List[Dict[str, str]]] = None,
    output_format: str = "YAML",
    deletion_policy: str = "RETAIN",
    update_replace_policy: str = "RETAIN",
    template_id: Optional[str] = None,
    save_to_file: Optional[str] = None,
    region_name: Optional[str] = None,
) -> Dict:
    """
    Create a CloudFormation template from existing resources using the IaC Generator API.

    This function handles three main scenarios:
    1. Starting a new template generation process
    2. Checking the status of an existing template generation process
    3. Retrieving a generated template

    Args:
        template_name: Name for the generated template
        resources: List of resources to include in the template, each with 'ResourceType' and 'ResourceIdentifier'
        output_format: Output format for the template (JSON or YAML)
        deletion_policy: Default DeletionPolicy for resources in the template (RETAIN, DELETE, or SNAPSHOT)
        update_replace_policy: Default UpdateReplacePolicy for resources in the template (RETAIN, DELETE, or SNAPSHOT)
        template_id: ID of an existing template generation process to check status or retrieve template
        save_to_file: Path to save the generated template to a file
        region_name: AWS region name

    Returns:
        A dictionary containing information about the template generation process or the generated template
    """
    # Validate parameters
    if not template_id and not template_name:
        raise ClientError("Either template_name or template_id must be provided")

    if output_format not in ["JSON", "YAML"]:
        raise ClientError("output_format must be either 'JSON' or 'YAML'")

    if deletion_policy not in ["RETAIN", "DELETE", "SNAPSHOT"]:
        raise ClientError("deletion_policy must be one of 'RETAIN', 'DELETE', or 'SNAPSHOT'")

    if update_replace_policy not in ["RETAIN", "DELETE", "SNAPSHOT"]:
        raise ClientError("update_replace_policy must be one of 'RETAIN', 'DELETE', or 'SNAPSHOT'")

    # Get CloudFormation client
    cfn_client = get_aws_client('cloudformation', region_name)

    # Case 1: Check status or retrieve template for an existing template generation process
    if template_id:
        return await _handle_existing_template(
            cfn_client, template_id, save_to_file, output_format
        )

    # Case 2: Start a new template generation process
    return await _start_template_generation(
        cfn_client,
        template_name,
        resources,
        deletion_policy,
        update_replace_policy
    )


async def _start_template_generation(
    cfn_client,
    template_name: str,
    resources: Optional[List[Dict[str, str]]],
    deletion_policy: str,
    update_replace_policy: str
) -> Dict:
    """
    Start a new template generation process.

    Args:
        cfn_client: Boto3 CloudFormation client
        template_name: Name for the generated template
        resources: List of resources to include in the template
        output_format: Output format for the template (JSON or YAML)
        deletion_policy: DeletionPolicy for resources in the template
        update_replace_policy: UpdateReplacePolicy for resources in the template

    Returns:
        A dictionary containing information about the template generation process
    """
    # Prepare parameters for the API call
    params = {
        'GeneratedTemplateName': template_name,
        'TemplateConfiguration': {
            'DeletionPolicy': deletion_policy,
            'UpdateReplacePolicy': update_replace_policy
        }
    }

    # Add resources if provided
    if resources:
        resource_identifiers = []
        for resource in resources:
            if 'ResourceType' not in resource or 'ResourceIdentifier' not in resource:
                raise ClientError("Each resource must have 'ResourceType' and 'ResourceIdentifier'")
            resource_identifiers.append({
                'ResourceType': resource['ResourceType'],
                'ResourceIdentifier': resource['ResourceIdentifier']
            })
        params['Resources'] = resource_identifiers

    # Call the API
    try:
        response = cfn_client.create_generated_template(**params)
        return {
            "status": "INITIATED",
            "template_id": response['GeneratedTemplateId'],
            "message": "Template generation initiated. Use the template_id to check status."
        }
    except Exception as e:
        raise handle_aws_api_error(e)


async def _handle_existing_template(
    cfn_client,
    template_id: str,
    save_to_file: Optional[str],
    output_format: str = "YAML"
) -> Dict:
    """
    Handle an existing template generation process - check status or retrieve template.

    Args:
        cfn_client: Boto3 CloudFormation client
        template_id: ID of the template generation process
        save_to_file: Path to save the generated template to a file

    Returns:
        A dictionary containing information about the template generation process or the generated template
    """
    # Check the status of the template generation process
    try:
        status_response = cfn_client.describe_generated_template(
            GeneratedTemplateName=template_id
        )

        status = status_response['Status']

        # Return status information if the template is not yet complete
        if status != 'COMPLETE':
            return {
                "status": status,
                "template_id": template_id,
                "message": f"Template generation {status.lower()}."
            }

        # If the template is complete, retrieve it
        template_response = cfn_client.get_generated_template(
            GeneratedTemplateName=template_id,
            Format=output_format
        )

        template_content = template_response['TemplateBody']
        resources = status_response.get('ResourceIdentifiers', [])

        # Save the template to a file if requested
        file_path = None
        if save_to_file:
            try:
                # Ensure the directory exists
                os.makedirs(os.path.dirname(os.path.abspath(save_to_file)), exist_ok=True)

                # Write the template to the file
                with open(save_to_file, 'w') as f:
                    f.write(template_content)
                file_path = save_to_file
            except Exception as e:
                raise ClientError(f"Failed to save template to file: {str(e)}")

        # Return the template and related information
        result = {
            "status": "COMPLETED",
            "template_id": template_id,
            "template": template_content,
            "resources": resources,
            "message": "Template generation completed."
        }

        if file_path:
            result["file_path"] = file_path

        return result

    except Exception as e:
        raise handle_aws_api_error(e)
