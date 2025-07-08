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

#!/usr/bin/env python3

import boto3
import json
import os
from typing import Any, Dict, List, Optional

from awslabs.healthlake_mcp_server.common import (
    CreateDatastoreInput,
    StartFHIRImportJobInput,
    StartFHIRExportJobInput,
    Tag,
    handle_exceptions,
    mutation_check,
)
from botocore.config import Config
from mcp.server.fastmcp import FastMCP


# Initialize the MCP server
mcp = FastMCP("AWS HealthLake MCP Server")


def get_healthlake_client(region_name: Optional[str] = None):
    """Get a HealthLake client with proper configuration."""
    if not region_name:
        region_name = os.getenv('AWS_REGION', 'us-west-2')
    
    config = Config(
        region_name=region_name,
        retries={'max_attempts': 3, 'mode': 'adaptive'}
    )
    
    return boto3.client('healthlake', config=config)


@mcp.tool()
@handle_exceptions
def create_datastore(
    datastore_type_version: str,
    datastore_name: Optional[str] = None,
    sse_configuration: Optional[Dict[str, Any]] = None,
    preload_data_config: Optional[Dict[str, Any]] = None,
    client_token: Optional[str] = None,
    tags: Optional[List[Dict[str, str]]] = None,
    identity_provider_configuration: Optional[Dict[str, Any]] = None,
    region_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new HealthLake datastore.
    
    Args:
        datastore_type_version: The FHIR version of the datastore (R4)
        datastore_name: Optional user-generated name for the datastore
        sse_configuration: Optional server-side encryption configuration
        preload_data_config: Optional parameter to preload data upon creation
        client_token: Optional user provided token for idempotency
        tags: Optional list of tags to apply to the datastore
        identity_provider_configuration: Optional identity provider configuration
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)
    
    Returns:
        Dict containing the datastore creation response
    """
    mutation_check()
    
    client = get_healthlake_client(region_name)
    
    # Build the request parameters
    params = {
        'DatastoreTypeVersion': datastore_type_version
    }
    
    if datastore_name:
        params['DatastoreName'] = datastore_name
    if sse_configuration:
        params['SseConfiguration'] = sse_configuration
    if preload_data_config:
        params['PreloadDataConfig'] = preload_data_config
    if client_token:
        params['ClientToken'] = client_token
    if tags:
        params['Tags'] = [Tag(**tag).model_dump(by_alias=True) for tag in tags]
    if identity_provider_configuration:
        params['IdentityProviderConfiguration'] = identity_provider_configuration
    
    response = client.create_fhir_datastore(**params)
    return response


@mcp.tool()
@handle_exceptions
def delete_datastore(
    datastore_id: str,
    region_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Delete a HealthLake datastore.
    
    Args:
        datastore_id: The AWS-generated ID for the datastore
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)
    
    Returns:
        Dict containing the datastore deletion response
    """
    mutation_check()
    
    client = get_healthlake_client(region_name)
    response = client.delete_fhir_datastore(DatastoreId=datastore_id)
    return response


@mcp.tool()
@handle_exceptions
def describe_datastore(
    datastore_id: str,
    region_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Describe a HealthLake datastore.
    
    Args:
        datastore_id: The AWS-generated ID for the datastore
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)
    
    Returns:
        Dict containing the datastore description
    """
    client = get_healthlake_client(region_name)
    response = client.describe_fhir_datastore(DatastoreId=datastore_id)
    return response


@mcp.tool()
@handle_exceptions
def list_datastores(
    filter_dict: Optional[Dict[str, Any]] = None,
    next_token: Optional[str] = None,
    max_results: Optional[int] = None,
    region_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    List HealthLake datastores.
    
    Args:
        filter_dict: Optional filter to apply to the datastore list
        next_token: Optional token for pagination
        max_results: Optional maximum number of results to return
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)
    
    Returns:
        Dict containing the list of datastores
    """
    client = get_healthlake_client(region_name)
    
    params = {}
    if filter_dict:
        params['Filter'] = filter_dict
    if next_token:
        params['NextToken'] = next_token
    if max_results:
        params['MaxResults'] = max_results
    
    response = client.list_fhir_datastores(**params)
    return response


@mcp.tool()
@handle_exceptions
def start_fhir_import_job(
    input_data_config: Dict[str, Any],
    job_output_data_config: Dict[str, Any],
    datastore_id: str,
    data_access_role_arn: str,
    job_name: Optional[str] = None,
    client_token: Optional[str] = None,
    region_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Start a FHIR import job.
    
    Args:
        input_data_config: The input properties of the FHIR Import job
        job_output_data_config: The output data configuration
        datastore_id: The AWS-generated datastore ID
        data_access_role_arn: The ARN that gives HealthLake access permission
        job_name: Optional name of the FHIR Import job
        client_token: Optional user provided token
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)
    
    Returns:
        Dict containing the import job response
    """
    mutation_check()
    
    client = get_healthlake_client(region_name)
    
    params = {
        'InputDataConfig': input_data_config,
        'JobOutputDataConfig': job_output_data_config,
        'DatastoreId': datastore_id,
        'DataAccessRoleArn': data_access_role_arn
    }
    
    if job_name:
        params['JobName'] = job_name
    if client_token:
        params['ClientToken'] = client_token
    
    response = client.start_fhir_import_job(**params)
    return response


@mcp.tool()
@handle_exceptions
def start_fhir_export_job(
    output_data_config: Dict[str, Any],
    datastore_id: str,
    data_access_role_arn: str,
    job_name: Optional[str] = None,
    client_token: Optional[str] = None,
    region_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Start a FHIR export job.
    
    Args:
        output_data_config: The output data configuration
        datastore_id: The AWS generated ID for the datastore
        data_access_role_arn: The ARN that gives HealthLake access permission
        job_name: Optional user generated name for an export job
        client_token: Optional user provided token
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)
    
    Returns:
        Dict containing the export job response
    """
    mutation_check()
    
    client = get_healthlake_client(region_name)
    
    params = {
        'OutputDataConfig': output_data_config,
        'DatastoreId': datastore_id,
        'DataAccessRoleArn': data_access_role_arn
    }
    
    if job_name:
        params['JobName'] = job_name
    if client_token:
        params['ClientToken'] = client_token
    
    response = client.start_fhir_export_job(**params)
    return response


@mcp.tool()
@handle_exceptions
def describe_fhir_import_job(
    datastore_id: str,
    job_id: str,
    region_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Describe a FHIR import job.
    
    Args:
        datastore_id: The AWS-generated ID for the datastore
        job_id: The AWS-generated job ID
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)
    
    Returns:
        Dict containing the import job description
    """
    client = get_healthlake_client(region_name)
    response = client.describe_fhir_import_job(
        DatastoreId=datastore_id,
        JobId=job_id
    )
    return response


@mcp.tool()
@handle_exceptions
def describe_fhir_export_job(
    datastore_id: str,
    job_id: str,
    region_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Describe a FHIR export job.
    
    Args:
        datastore_id: The AWS-generated ID for the datastore
        job_id: The AWS-generated job ID
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)
    
    Returns:
        Dict containing the export job description
    """
    client = get_healthlake_client(region_name)
    response = client.describe_fhir_export_job(
        DatastoreId=datastore_id,
        JobId=job_id
    )
    return response


@mcp.tool()
@handle_exceptions
def list_fhir_import_jobs(
    datastore_id: str,
    next_token: Optional[str] = None,
    max_results: Optional[int] = None,
    job_name: Optional[str] = None,
    job_status: Optional[str] = None,
    submitted_before: Optional[str] = None,
    submitted_after: Optional[str] = None,
    region_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    List FHIR import jobs.
    
    Args:
        datastore_id: The AWS-generated ID for the datastore
        next_token: Optional token for pagination
        max_results: Optional maximum number of results to return
        job_name: Optional job name filter
        job_status: Optional job status filter
        submitted_before: Optional filter for jobs submitted before this date
        submitted_after: Optional filter for jobs submitted after this date
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)
    
    Returns:
        Dict containing the list of import jobs
    """
    client = get_healthlake_client(region_name)
    
    params = {'DatastoreId': datastore_id}
    
    if next_token:
        params['NextToken'] = next_token
    if max_results:
        params['MaxResults'] = max_results
    if job_name:
        params['JobName'] = job_name
    if job_status:
        params['JobStatus'] = job_status
    if submitted_before:
        params['SubmittedBefore'] = submitted_before
    if submitted_after:
        params['SubmittedAfter'] = submitted_after
    
    response = client.list_fhir_import_jobs(**params)
    return response


@mcp.tool()
@handle_exceptions
def list_fhir_export_jobs(
    datastore_id: str,
    next_token: Optional[str] = None,
    max_results: Optional[int] = None,
    job_name: Optional[str] = None,
    job_status: Optional[str] = None,
    submitted_before: Optional[str] = None,
    submitted_after: Optional[str] = None,
    region_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    List FHIR export jobs.
    
    Args:
        datastore_id: The AWS-generated ID for the datastore
        next_token: Optional token for pagination
        max_results: Optional maximum number of results to return
        job_name: Optional job name filter
        job_status: Optional job status filter
        submitted_before: Optional filter for jobs submitted before this date
        submitted_after: Optional filter for jobs submitted after this date
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)
    
    Returns:
        Dict containing the list of export jobs
    """
    client = get_healthlake_client(region_name)
    
    params = {'DatastoreId': datastore_id}
    
    if next_token:
        params['NextToken'] = next_token
    if max_results:
        params['MaxResults'] = max_results
    if job_name:
        params['JobName'] = job_name
    if job_status:
        params['JobStatus'] = job_status
    if submitted_before:
        params['SubmittedBefore'] = submitted_before
    if submitted_after:
        params['SubmittedAfter'] = submitted_after
    
    response = client.list_fhir_export_jobs(**params)
    return response


@mcp.tool()
@handle_exceptions
def tag_resource(
    resource_arn: str,
    tags: List[Dict[str, str]],
    region_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Add tags to a HealthLake resource.
    
    Args:
        resource_arn: The Amazon Resource Name (ARN) of the resource
        tags: List of tags to add to the resource
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)
    
    Returns:
        Dict containing the tag resource response
    """
    mutation_check()
    
    client = get_healthlake_client(region_name)
    
    tag_objects = [Tag(**tag).model_dump(by_alias=True) for tag in tags]
    
    response = client.tag_resource(
        ResourceARN=resource_arn,
        Tags=tag_objects
    )
    return response


@mcp.tool()
@handle_exceptions
def untag_resource(
    resource_arn: str,
    tag_keys: List[str],
    region_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Remove tags from a HealthLake resource.
    
    Args:
        resource_arn: The Amazon Resource Name (ARN) of the resource
        tag_keys: List of tag keys to remove from the resource
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)
    
    Returns:
        Dict containing the untag resource response
    """
    mutation_check()
    
    client = get_healthlake_client(region_name)
    
    response = client.untag_resource(
        ResourceARN=resource_arn,
        TagKeys=tag_keys
    )
    return response


@mcp.tool()
@handle_exceptions
def list_tags_for_resource(
    resource_arn: str,
    region_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    List tags for a HealthLake resource.
    
    Args:
        resource_arn: The Amazon Resource Name (ARN) of the resource
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)
    
    Returns:
        Dict containing the resource tags
    """
    client = get_healthlake_client(region_name)
    
    response = client.list_tags_for_resource(ResourceARN=resource_arn)
    return response


def main():
    """Main entry point for the HealthLake MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
