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
import os
import requests
import uuid
from awslabs.healthlake_mcp_server.common import (
    Tag,
    handle_exceptions,
    mutation_check,
)
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.config import Config
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from typing import Any, Dict, List, Optional


# Initialize the MCP server
mcp = FastMCP('AWS HealthLake MCP Server')


def get_healthlake_client(region_name: Optional[str] = None):
    """Get a HealthLake client with proper configuration."""
    if not region_name:
        region_name = os.getenv('AWS_REGION', 'us-west-2')

    config = Config(region_name=region_name, retries={'max_attempts': 3, 'mode': 'adaptive'})

    return boto3.client('healthlake', config=config)


def _get_fhir_endpoint(datastore_id: str, region_name: Optional[str] = None) -> str:
    """Get the FHIR endpoint URL for a datastore."""
    client = get_healthlake_client(region_name)
    datastore_info = client.describe_fhir_datastore(DatastoreId=datastore_id)
    return datastore_info['DatastoreProperties']['DatastoreEndpoint']


def _make_fhir_request(
    method: str,
    url: str,
    region_name: str,
    json_data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Make an authenticated FHIR API request to HealthLake."""
    # Get AWS SigV4 signed headers
    session = boto3.Session()
    credentials = session.get_credentials()

    # Prepare headers
    request_headers = {'Content-Type': 'application/fhir+json', 'Accept': 'application/fhir+json'}
    if headers:
        request_headers.update(headers)

    # Create a request with AWS SigV4 authentication
    import json as json_module

    # Create an AWS request for signing
    aws_request = AWSRequest(
        method=method,
        url=url,
        data=json_module.dumps(json_data) if json_data else None,
        params=params,
        headers=request_headers,
    )

    # Sign the request
    auth = SigV4Auth(credentials, 'healthlake', region_name)
    auth.add_auth(aws_request)

    # Convert back to requests format and send
    with requests.Session() as session:
        response = session.request(
            method=aws_request.method,
            url=aws_request.url,
            headers=dict(aws_request.headers),
            data=aws_request.body,
            params=params,
        )

        # Handle FHIR-specific error responses
        if not response.ok:
            try:
                error_data = response.json()
                if error_data.get('resourceType') == 'OperationOutcome':
                    # Extract FHIR OperationOutcome details
                    issues = error_data.get('issue', [])
                    error_messages = []
                    for issue in issues:
                        severity = issue.get('severity', 'error')
                        code = issue.get('code', 'unknown')
                        details = issue.get('details', {}).get(
                            'text', issue.get('diagnostics', '')
                        )
                        error_messages.append(f'{severity.upper()}: {code} - {details}')

                    raise Exception(f'FHIR Operation Failed: {"; ".join(error_messages)}')
                else:
                    raise Exception(f'HTTP {response.status_code}: {response.text}')
            except ValueError:
                # Not JSON response
                response.raise_for_status()

        # Return JSON response or empty dict for successful operations without content
        if response.content:
            return response.json()
        else:
            return {'status': 'success', 'statusCode': response.status_code}


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
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new HealthLake datastore.

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
    params = {'DatastoreTypeVersion': datastore_type_version}

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
def delete_datastore(datastore_id: str, region_name: Optional[str] = None) -> Dict[str, Any]:
    """Delete a HealthLake datastore.

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
def describe_datastore(datastore_id: str, region_name: Optional[str] = None) -> Dict[str, Any]:
    """Describe a HealthLake datastore.

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
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """List HealthLake datastores.

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
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Start a FHIR import job.

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
        'DataAccessRoleArn': data_access_role_arn,
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
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Start a FHIR export job.

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
        'DataAccessRoleArn': data_access_role_arn,
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
    datastore_id: str, job_id: str, region_name: Optional[str] = None
) -> Dict[str, Any]:
    """Describe a FHIR import job.

    Args:
        datastore_id: The AWS-generated ID for the datastore
        job_id: The AWS-generated job ID
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)

    Returns:
        Dict containing the import job description
    """
    client = get_healthlake_client(region_name)
    response = client.describe_fhir_import_job(DatastoreId=datastore_id, JobId=job_id)
    return response


@mcp.tool()
@handle_exceptions
def describe_fhir_export_job(
    datastore_id: str, job_id: str, region_name: Optional[str] = None
) -> Dict[str, Any]:
    """Describe a FHIR export job.

    Args:
        datastore_id: The AWS-generated ID for the datastore
        job_id: The AWS-generated job ID
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)

    Returns:
        Dict containing the export job description
    """
    client = get_healthlake_client(region_name)
    response = client.describe_fhir_export_job(DatastoreId=datastore_id, JobId=job_id)
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
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """List FHIR import jobs.

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
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """List FHIR export jobs.

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
def read_fhir_resource(
    datastore_id: str,
    resource_type: str,
    resource_id: str,
    version_id: Optional[str] = None,
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Read a FHIR resource by ID using HealthLake FHIR API.

    Args:
        datastore_id: The AWS-generated ID for the datastore
        resource_type: The FHIR resource type (e.g., Patient, Observation)
        resource_id: The ID of the FHIR resource
        version_id: Optional specific version ID to retrieve
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)

    Returns:
        Dict containing the FHIR resource
    """
    if not region_name:
        region_name = os.getenv('AWS_REGION', 'us-west-2')

    # Get the datastore endpoint
    endpoint = _get_fhir_endpoint(datastore_id, region_name)

    # Construct the URL for the FHIR resource
    if version_id:
        url = f'{endpoint}{resource_type}/{resource_id}/_history/{version_id}'
    else:
        url = f'{endpoint}{resource_type}/{resource_id}'

    return _make_fhir_request('GET', url, region_name)


@mcp.tool()
@handle_exceptions
def search_fhir_resources(
    datastore_id: str,
    resource_type: str,
    query_parameters: Optional[Dict[str, str]] = None,
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Search for FHIR resources using HealthLake FHIR API.

    Args:
        datastore_id: The AWS-generated ID for the datastore
        resource_type: The FHIR resource type to search (e.g., Patient, Observation)
        query_parameters: Optional dictionary of search parameters
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)

    Returns:
        Dict containing the search results as a FHIR Bundle
    """
    if not region_name:
        region_name = os.getenv('AWS_REGION', 'us-west-2')

    # Get the datastore endpoint
    endpoint = _get_fhir_endpoint(datastore_id, region_name)

    # Construct the URL for the FHIR search
    url = f'{endpoint}{resource_type}'

    return _make_fhir_request('GET', url, region_name, params=query_parameters)


@mcp.tool()
@handle_exceptions
def create_fhir_resource(
    datastore_id: str,
    resource_type: str,
    resource_data: Dict[str, Any],
    if_none_exist: Optional[str] = None,
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new FHIR resource using HealthLake FHIR API.

    Args:
        datastore_id: The AWS-generated ID for the datastore
        resource_type: The FHIR resource type (e.g., Patient, Observation)
        resource_data: The FHIR resource data as a dictionary
        if_none_exist: Optional conditional create parameter to prevent duplicates
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)

    Returns:
        Dict containing the created FHIR resource with server-assigned ID
    """
    mutation_check()

    if not region_name:
        region_name = os.getenv('AWS_REGION', 'us-west-2')

    # Validate that resourceType matches the URL
    if resource_data.get('resourceType') != resource_type:
        raise ValueError(
            f"Resource type mismatch: URL specifies '{resource_type}' but resource contains '{resource_data.get('resourceType')}'"
        )

    # Remove id field for create operations (server will assign)
    resource_data = resource_data.copy()
    if 'id' in resource_data:
        del resource_data['id']

    # Get the datastore endpoint
    endpoint = _get_fhir_endpoint(datastore_id, region_name)

    # Construct the URL for the FHIR resource
    url = f'{endpoint}{resource_type}'

    # Add conditional create header if specified
    headers = {}
    if if_none_exist:
        headers['If-None-Exist'] = if_none_exist

    return _make_fhir_request('POST', url, region_name, json_data=resource_data, headers=headers)


@mcp.tool()
@handle_exceptions
def update_fhir_resource(
    datastore_id: str,
    resource_type: str,
    resource_id: str,
    resource_data: Dict[str, Any],
    if_match: Optional[str] = None,
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Update an existing FHIR resource using HealthLake FHIR API.

    Args:
        datastore_id: The AWS-generated ID for the datastore
        resource_type: The FHIR resource type (e.g., Patient, Observation)
        resource_id: The ID of the FHIR resource to update
        resource_data: The updated FHIR resource data as a dictionary
        if_match: Optional version ID for optimistic concurrency control
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)

    Returns:
        Dict containing the updated FHIR resource
    """
    mutation_check()

    if not region_name:
        region_name = os.getenv('AWS_REGION', 'us-west-2')

    # Validate that resourceType matches the URL
    if resource_data.get('resourceType') != resource_type:
        raise ValueError(
            f"Resource type mismatch: URL specifies '{resource_type}' but resource contains '{resource_data.get('resourceType')}'"
        )

    # Ensure the resource ID in the URL matches the one in the resource data
    resource_data = resource_data.copy()
    if 'id' not in resource_data:
        resource_data['id'] = resource_id
    elif resource_data['id'] != resource_id:
        raise ValueError(
            f"Resource ID mismatch: URL specifies '{resource_id}' but resource contains '{resource_data['id']}'"
        )

    # Get the datastore endpoint
    endpoint = _get_fhir_endpoint(datastore_id, region_name)

    # Construct the URL for the FHIR resource
    url = f'{endpoint}{resource_type}/{resource_id}'

    # Add conditional update header if specified
    headers = {}
    if if_match:
        headers['If-Match'] = if_match

    return _make_fhir_request('PUT', url, region_name, json_data=resource_data, headers=headers)


@mcp.tool()
@handle_exceptions
def delete_fhir_resource(
    datastore_id: str,
    resource_type: str,
    resource_id: str,
    if_match: Optional[str] = None,
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Delete a FHIR resource using HealthLake FHIR API.

    Args:
        datastore_id: The AWS-generated ID for the datastore
        resource_type: The FHIR resource type (e.g., Patient, Observation)
        resource_id: The ID of the FHIR resource to delete
        if_match: Optional version ID for optimistic concurrency control
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)

    Returns:
        Dict containing the deletion response
    """
    mutation_check()

    if not region_name:
        region_name = os.getenv('AWS_REGION', 'us-west-2')

    # Get the datastore endpoint
    endpoint = _get_fhir_endpoint(datastore_id, region_name)

    # Construct the URL for the FHIR resource
    url = f'{endpoint}{resource_type}/{resource_id}'

    # Add conditional delete header if specified
    headers = {}
    if if_match:
        headers['If-Match'] = if_match

    return _make_fhir_request('DELETE', url, region_name, headers=headers)


@mcp.tool()
@handle_exceptions
def tag_resource(
    resource_arn: str, tags: List[Dict[str, str]], region_name: Optional[str] = None
) -> Dict[str, Any]:
    """Add tags to a HealthLake resource.

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

    response = client.tag_resource(ResourceARN=resource_arn, Tags=tag_objects)
    return response


@mcp.tool()
@handle_exceptions
def untag_resource(
    resource_arn: str, tag_keys: List[str], region_name: Optional[str] = None
) -> Dict[str, Any]:
    """Remove tags from a HealthLake resource.

    Args:
        resource_arn: The Amazon Resource Name (ARN) of the resource
        tag_keys: List of tag keys to remove from the resource
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)

    Returns:
        Dict containing the untag resource response
    """
    mutation_check()

    client = get_healthlake_client(region_name)

    response = client.untag_resource(ResourceARN=resource_arn, TagKeys=tag_keys)
    return response


@mcp.tool()
@handle_exceptions
def list_tags_for_resource(resource_arn: str, region_name: Optional[str] = None) -> Dict[str, Any]:
    """List tags for a HealthLake resource.

    Args:
        resource_arn: The Amazon Resource Name (ARN) of the resource
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)

    Returns:
        Dict containing the resource tags
    """
    client = get_healthlake_client(region_name)

    response = client.list_tags_for_resource(ResourceARN=resource_arn)
    return response


@mcp.tool()
@handle_exceptions
def create_fhir_bundle(
    datastore_id: str,
    bundle_resources: List[Dict[str, Any]],
    bundle_type: str = 'transaction',
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a FHIR Bundle with multiple resources for batch processing using HealthLake FHIR API.

    Args:
        datastore_id: The AWS-generated ID for the datastore
        bundle_resources: List of FHIR resources to include in the bundle
        bundle_type: Type of bundle (transaction, batch, collection, etc.)
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)

    Returns:
        Dict containing the created FHIR Bundle response
    """
    mutation_check()

    if not region_name:
        region_name = os.getenv('AWS_REGION', 'us-west-2')

    # Create FHIR Bundle structure
    bundle = {
        'resourceType': 'Bundle',
        'id': str(uuid.uuid4()),
        'type': bundle_type,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'entry': [],
    }

    # Add resources to bundle
    for resource in bundle_resources:
        entry = {'resource': resource}

        # Add request information for transaction/batch bundles
        if bundle_type in ['transaction', 'batch']:
            resource_type = resource.get('resourceType', '')
            if 'id' in resource:
                entry['request'] = {'method': 'PUT', 'url': f'{resource_type}/{resource["id"]}'}
            else:
                entry['request'] = {'method': 'POST', 'url': resource_type}

        bundle['entry'].append(entry)

    # Get the datastore endpoint
    endpoint = _get_fhir_endpoint(datastore_id, region_name)

    # Send bundle to HealthLake
    url = f'{endpoint}'

    return _make_fhir_request('POST', url, region_name, json_data=bundle)


@mcp.tool()
@handle_exceptions
def search_fhir_resources_advanced(
    datastore_id: str,
    resource_type: str,
    search_parameters: Optional[Dict[str, Any]] = None,
    include_parameters: Optional[List[str]] = None,
    revinclude_parameters: Optional[List[str]] = None,
    sort_parameters: Optional[List[str]] = None,
    count: Optional[int] = None,
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Advanced search for FHIR resources with additional parameters using HealthLake FHIR API.

    Args:
        datastore_id: The AWS-generated ID for the datastore
        resource_type: The FHIR resource type to search
        search_parameters: Dictionary of search parameters
        include_parameters: List of _include parameters for related resources
        revinclude_parameters: List of _revinclude parameters for reverse includes
        sort_parameters: List of _sort parameters for result ordering
        count: Number of results to return per page
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)

    Returns:
        Dict containing the advanced search results as a FHIR Bundle
    """
    if not region_name:
        region_name = os.getenv('AWS_REGION', 'us-west-2')

    # Build query parameters
    params = {}

    if search_parameters:
        params.update(search_parameters)

    if include_parameters:
        params['_include'] = include_parameters

    if revinclude_parameters:
        params['_revinclude'] = revinclude_parameters

    if sort_parameters:
        params['_sort'] = ','.join(sort_parameters)

    if count:
        params['_count'] = count

    # Get the datastore endpoint
    endpoint = _get_fhir_endpoint(datastore_id, region_name)

    # Construct the URL for the FHIR search
    url = f'{endpoint}{resource_type}'

    return _make_fhir_request('GET', url, region_name, params=params)


@mcp.tool()
@handle_exceptions
def validate_fhir_resource(
    resource_data: Dict[str, Any], resource_type: Optional[str] = None
) -> Dict[str, Any]:
    """Validate a FHIR resource structure and provide feedback.

    Args:
        resource_data: The FHIR resource data to validate
        resource_type: Expected resource type (optional)

    Returns:
        Dict containing validation results and any issues found
    """
    validation_result = {'valid': True, 'issues': [], 'warnings': []}

    # Check if resourceType is present
    if 'resourceType' not in resource_data:
        validation_result['valid'] = False
        validation_result['issues'].append("Missing required 'resourceType' field")
    else:
        actual_type = resource_data['resourceType']

        # Check if resource type matches expected type
        if resource_type and actual_type != resource_type:
            validation_result['valid'] = False
            validation_result['issues'].append(
                f"Resource type mismatch: expected '{resource_type}', got '{actual_type}'"
            )

    # Check for required fields based on resource type
    resource_type_to_check = resource_type or resource_data.get('resourceType')

    if resource_type_to_check == 'Patient':
        # Basic Patient validation
        if 'name' not in resource_data and 'identifier' not in resource_data:
            validation_result['warnings'].append(
                "Patient should have either 'name' or 'identifier' field"
            )

    elif resource_type_to_check == 'Observation':
        # Basic Observation validation
        required_fields = ['status', 'code']
        for field in required_fields:
            if field not in resource_data:
                validation_result['valid'] = False
                validation_result['issues'].append(f"Missing required field: '{field}'")

    elif resource_type_to_check == 'Condition':
        # Basic Condition validation
        if 'subject' not in resource_data:
            validation_result['valid'] = False
            validation_result['issues'].append("Missing required field: 'subject'")

    # Check for common FHIR patterns
    if 'id' in resource_data:
        resource_id = resource_data['id']
        if not isinstance(resource_id, str) or len(resource_id) == 0:
            validation_result['issues'].append("Resource 'id' must be a non-empty string")

    return validation_result


@mcp.tool()
@handle_exceptions
def create_patient_template(
    family_name: str,
    given_names: List[str],
    gender: str,
    birth_date: str,
    identifier_system: Optional[str] = None,
    identifier_value: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    address: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a FHIR Patient resource template with common fields.

    Args:
        family_name: Patient's family name
        given_names: List of given names
        gender: Patient's gender (male, female, other, unknown)
        birth_date: Birth date in YYYY-MM-DD format
        identifier_system: Optional identifier system (e.g., SSN, MRN)
        identifier_value: Optional identifier value
        phone: Optional phone number
        email: Optional email address
        address: Optional address dictionary

    Returns:
        Dict containing a FHIR Patient resource template
    """
    patient = {
        'resourceType': 'Patient',
        'name': [{'family': family_name, 'given': given_names}],
        'gender': gender,
        'birthDate': birth_date,
    }

    # Add identifier if provided
    if identifier_system and identifier_value:
        patient['identifier'] = [{'system': identifier_system, 'value': identifier_value}]

    # Add contact information
    telecom = []
    if phone:
        telecom.append({'system': 'phone', 'value': phone, 'use': 'home'})

    if email:
        telecom.append({'system': 'email', 'value': email})

    if telecom:
        patient['telecom'] = telecom

    # Add address if provided
    if address:
        patient['address'] = [address]

    return patient


@mcp.tool()
@handle_exceptions
def create_observation_template(
    patient_reference: str,
    code_system: str,
    code_value: str,
    code_display: str,
    status: str = 'final',
    value_quantity: Optional[Dict[str, Any]] = None,
    value_string: Optional[str] = None,
    effective_datetime: Optional[str] = None,
    category_code: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a FHIR Observation resource template.

    Args:
        patient_reference: Reference to the patient (e.g., "Patient/123")
        code_system: Coding system for the observation code
        code_value: The observation code value
        code_display: Human-readable display for the code
        status: Observation status (final, preliminary, etc.)
        value_quantity: Optional quantity value with unit
        value_string: Optional string value
        effective_datetime: Optional datetime when observation was made
        category_code: Optional category code (vital-signs, laboratory, etc.)

    Returns:
        Dict containing a FHIR Observation resource template
    """
    observation = {
        'resourceType': 'Observation',
        'status': status,
        'code': {'coding': [{'system': code_system, 'code': code_value, 'display': code_display}]},
        'subject': {'reference': patient_reference},
    }

    # Add category if provided
    if category_code:
        observation['category'] = [
            {
                'coding': [
                    {
                        'system': 'http://terminology.hl7.org/CodeSystem/observation-category',
                        'code': category_code,
                    }
                ]
            }
        ]

    # Add value
    if value_quantity:
        observation['valueQuantity'] = value_quantity
    elif value_string:
        observation['valueString'] = value_string

    # Add effective datetime
    if effective_datetime:
        observation['effectiveDateTime'] = effective_datetime
    else:
        observation['effectiveDateTime'] = datetime.utcnow().isoformat() + 'Z'

    return observation


@mcp.tool()
@handle_exceptions
def get_fhir_resource_history(
    datastore_id: str,
    resource_type: str,
    resource_id: str,
    count: Optional[int] = None,
    since: Optional[str] = None,
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Get the version history of a FHIR resource using HealthLake FHIR API.

    Args:
        datastore_id: The AWS-generated ID for the datastore
        resource_type: The FHIR resource type
        resource_id: The ID of the FHIR resource
        count: Optional number of history entries to return
        since: Optional timestamp to get history since (ISO 8601 format)
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)

    Returns:
        Dict containing the resource version history as a FHIR Bundle
    """
    if not region_name:
        region_name = os.getenv('AWS_REGION', 'us-west-2')

    # Get the datastore endpoint
    endpoint = _get_fhir_endpoint(datastore_id, region_name)

    # Construct the URL for the FHIR resource history
    url = f'{endpoint}{resource_type}/{resource_id}/_history'

    # Build query parameters
    params = {}
    if count:
        params['_count'] = count
    if since:
        params['_since'] = since

    return _make_fhir_request('GET', url, region_name, params=params)


@mcp.tool()
@handle_exceptions
def get_datastore_capabilities(
    datastore_id: str, region_name: Optional[str] = None
) -> Dict[str, Any]:
    """Get the FHIR capabilities statement for a datastore using HealthLake FHIR API.

    Args:
        datastore_id: The AWS-generated ID for the datastore
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)

    Returns:
        Dict containing the FHIR CapabilityStatement
    """
    if not region_name:
        region_name = os.getenv('AWS_REGION', 'us-west-2')

    # Get the datastore endpoint
    endpoint = _get_fhir_endpoint(datastore_id, region_name)

    # Construct the URL for the capabilities statement
    url = f'{endpoint}metadata'

    return _make_fhir_request('GET', url, region_name)


@mcp.tool()
@handle_exceptions
def patch_fhir_resource(
    datastore_id: str,
    resource_type: str,
    resource_id: str,
    patch_operations: List[Dict[str, Any]],
    patch_format: str = 'json-patch',
    if_match: Optional[str] = None,
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Patch a FHIR resource using JSON Patch or FHIRPath Patch operations.

    Args:
        datastore_id: The AWS-generated ID for the datastore
        resource_type: The FHIR resource type (e.g., Patient, Observation)
        resource_id: The ID of the FHIR resource to patch
        patch_operations: List of patch operations
        patch_format: Format of patch operations (json-patch or fhir-patch)
        if_match: Optional version ID for optimistic concurrency control
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)

    Returns:
        Dict containing the patched FHIR resource
    """
    mutation_check()

    if not region_name:
        region_name = os.getenv('AWS_REGION', 'us-west-2')

    # Get the datastore endpoint
    endpoint = _get_fhir_endpoint(datastore_id, region_name)

    # Construct the URL for the FHIR resource
    url = f'{endpoint}{resource_type}/{resource_id}'

    # Set appropriate content type based on patch format
    headers = {}
    if patch_format == 'json-patch':
        headers['Content-Type'] = 'application/json-patch+json'
    elif patch_format == 'fhir-patch':
        headers['Content-Type'] = 'application/fhir+json'

    if if_match:
        headers['If-Match'] = if_match

    return _make_fhir_request(
        'PATCH', url, region_name, json_data=patch_operations, headers=headers
    )


@mcp.tool()
@handle_exceptions
def search_all_resources(
    datastore_id: str,
    query_parameters: Optional[Dict[str, str]] = None,
    count: Optional[int] = None,
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Search across all resource types in a datastore using HealthLake FHIR API.

    Args:
        datastore_id: The AWS-generated ID for the datastore
        query_parameters: Optional dictionary of search parameters
        count: Optional number of results to return per page
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)

    Returns:
        Dict containing the search results as a FHIR Bundle
    """
    if not region_name:
        region_name = os.getenv('AWS_REGION', 'us-west-2')

    # Build query parameters
    params = {}
    if query_parameters:
        params.update(query_parameters)
    if count:
        params['_count'] = count

    # Get the datastore endpoint
    endpoint = _get_fhir_endpoint(datastore_id, region_name)

    # Search across all resources using the base URL
    url = f'{endpoint}'

    return _make_fhir_request('GET', url, region_name, params=params)


@mcp.tool()
@handle_exceptions
def validate_fhir_resource_against_profile(
    datastore_id: str,
    resource_data: Dict[str, Any],
    profile_url: Optional[str] = None,
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Validate a FHIR resource against a profile using HealthLake FHIR API.

    Args:
        datastore_id: The AWS-generated ID for the datastore
        resource_data: The FHIR resource data to validate
        profile_url: Optional URL of the profile to validate against
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)

    Returns:
        Dict containing the validation results as an OperationOutcome
    """
    if not region_name:
        region_name = os.getenv('AWS_REGION', 'us-west-2')

    # Get the datastore endpoint
    endpoint = _get_fhir_endpoint(datastore_id, region_name)

    # Construct the URL for validation
    resource_type = resource_data.get('resourceType', '')
    url = f'{endpoint}{resource_type}/$validate'

    # Add profile parameter if specified
    params = {}
    if profile_url:
        params['profile'] = profile_url

    return _make_fhir_request('POST', url, region_name, json_data=resource_data, params=params)


@mcp.tool()
@handle_exceptions
def get_fhir_resource_compartment(
    datastore_id: str,
    compartment_type: str,
    compartment_id: str,
    resource_type: Optional[str] = None,
    query_parameters: Optional[Dict[str, str]] = None,
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Get resources from a FHIR compartment (e.g., Patient compartment).

    Args:
        datastore_id: The AWS-generated ID for the datastore
        compartment_type: The compartment type (e.g., Patient, Encounter)
        compartment_id: The ID of the compartment resource
        resource_type: Optional specific resource type to search within compartment
        query_parameters: Optional dictionary of search parameters
        region_name: AWS region name (defaults to AWS_REGION env var or us-west-2)

    Returns:
        Dict containing the compartment search results as a FHIR Bundle
    """
    if not region_name:
        region_name = os.getenv('AWS_REGION', 'us-west-2')

    # Get the datastore endpoint
    endpoint = _get_fhir_endpoint(datastore_id, region_name)

    # Construct the URL for compartment search
    if resource_type:
        url = f'{endpoint}{compartment_type}/{compartment_id}/{resource_type}'
    else:
        url = f'{endpoint}{compartment_type}/{compartment_id}/*'

    return _make_fhir_request('GET', url, region_name, params=query_parameters)


def main():
    """Main entry point for the HealthLake MCP server."""
    mcp.run()


if __name__ == '__main__':
    main()
