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

"""Amazon SageMaker MCP Server implementation."""
import boto3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

import boto3
from awslabs.amazon_sagemaker_mcp_server import __version__
from awslabs.amazon_sagemaker_mcp_server.utils.aws_client import (
    get_sagemaker_client,
    get_sagemaker_runtime_client,
    validate_aws_credentials,
)
from awslabs.amazon_sagemaker_mcp_server.utils.permissions import (
    require_write_access,
    require_sensitive_data_access,
)
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, Field

# Logging
logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))

# Create FastMCP server
mcp = FastMCP('amazon-sagemaker-mcp-server')

# Notebook Instance
@mcp.tool(description="List SageMaker notebook instances with optional filtering and sorting")
async def list_sm_nb_instances(
    sort_by: str = Field(default="CreationTime", description="Sort criteria (Name, CreationTime, Status)"),
    sort_order: str = Field(default="Descending", description="Sort order (Ascending, Descending)"),
    name_contains: Optional[str] = Field(default=None, description="Filter instances by name containing this string"),
    status_equals: Optional[str] = Field(default=None, description="Filter instances by status"),
    max_results: int = Field(default=10, description="Maximum number of results to return")
) -> str:
    try:
        client = get_sagemaker_client()

        # Prepare the request
        request = {
            'SortBy': sort_by,
            'SortOrder': sort_order,
            'MaxResults': max_results
        }

        # Add filters if provided
        if name_contains:
            request['NameContains'] = name_contains
        if status_equals:
            request['StatusEquals'] = status_equals

        # List instances
        response = client.list_notebook_instances(**request)

        result = {
            "success": True,
            "instances": response.get('NotebookInstances', []),
            "next_token": response.get('NextToken'),
            "total_count": len(response.get('NotebookInstances', [])),
            "message": "Successfully retrieved SageMaker Notebook Instances list"
        }

        return json.dumps(result, indent=2, default=str)

    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "message": "Failed to list SageMaker Notebook Instances"
        }

        return json.dumps(error_result, indent=2)

@mcp.tool(description="Get detailed information about a specific SageMaker notebook instance")
async def describe_sm_nb_instance(
    notebook_instance_name: str = Field(..., description="Name of the notebook instance")
) -> str:
    try:
        client = get_sagemaker_client()

        # Describe the notebook instance
        response = client.describe_notebook_instance(NotebookInstanceName=notebook_instance_name)

        result = {
            "success": True,
            "instance_details": response,
            "instance_name": notebook_instance_name,
            "message": f"Successfully retrieved details for notebook instance: {notebook_instance_name}"
        }

        return json.dumps(result, indent=2, default=str)

    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "message": f"Failed to describe SageMaker Notebook Instance: {notebook_instance_name}"
        }

        return json.dumps(error_result, indent=2)

# start notebook instance
@mcp.tool(description="Start a stopped SageMaker notebook instance")
async def start_sm_nb_instance(
    notebook_instance_name: str = Field(..., description="Name of the notebook instance")
) -> str:
    try:
        client = get_sagemaker_client()

        # Start the notebook instance
        response = client.start_notebook_instance(NotebookInstanceName=notebook_instance_name)

        result = {
            "success": True,
            "instance_name": notebook_instance_name,
            "message": f"Successfully started SageMaker Notebook Instance: {notebook_instance_name}"
        }

        return json.dumps(result, indent=2, default=str)

    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "message": f"Failed to start SageMaker Notebook Instance: {notebook_instance_name}"
        }

        return json.dumps(error_result, indent=2)

# stop notebook instance
@mcp.tool(description="Stop a running SageMaker notebook instance")
async def stop_sm_nb_instance(
    notebook_instance_name: str = Field(..., description="Name of the notebook instance")
) -> str:
    try:
        client = get_sagemaker_client()

        # Stop the notebook instance
        response = client.stop_notebook_instance(NotebookInstanceName=notebook_instance_name)

        result = {
            "success": True,
            "instance_name": notebook_instance_name,
            "message": f"Successfully stopped SageMaker Notebook Instance: {notebook_instance_name}"
        }

        return json.dumps(result, indent=2, default=str)

    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "message": f"Failed to stop SageMaker Notebook Instance: {notebook_instance_name}"
        }

        return json.dumps(error_result, indent=2)

# Space App Tools

# list apps
@mcp.tool(description="List SageMaker Space apps with optional filtering and sorting")
async def list_sm_space_apps(
    sort_by: str = Field(default="CreationTime", description="Sort criteria (Name, CreationTime, Status)"),
    sort_order: str = Field(default="Descending", description="Sort order (Ascending, Descending)"),
    domain_id_contains: Optional[str] = Field(default=None, description="Filter apps by Domain Id"),
    space_name_contains: Optional[str] = Field(default=None, description="Filter apps by space name"),
    max_results: int = Field(default=10, description="Maximum number of results to return")
) -> str:
    try:
        client = get_sagemaker_client()

        # Prepare the request
        request = {
            'SortBy': sort_by,
            'SortOrder': sort_order,
            'MaxResults': max_results,
        }

        # Add filters if provided
        if domain_id_contains:
            request['DomainIdEquals'] = domain_id_contains
        if space_name_contains:
            request['SpaceNameEquals'] = space_name_contains

        # List apps
        response = client.list_apps(**request)

        result = {
            "success": True,
            "apps": response.get('Apps', []),
            "next_token": response.get('NextToken'),
            "total_count": len(response.get('Apps', [])),
            "message": "Successfully retrieved SageMaker Space Apps list"
        }

        return json.dumps(result, indent=2, default=str)

    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "message": "Failed to list SageMaker Space Apps"
        }

        return json.dumps(error_result, indent=2)

# create_app
@mcp.tool(description="Create a new SageMaker Space app")
async def create_sm_space_app(
    domain_id: str = Field(..., description="Domain ID of the app"),
    space_name: str = Field(..., description="Space name of the app"),
    app_type: str = Field(..., description="Type of the app (JupyterServer, KernelGateway, or Space)"),
    app_name: str = Field(..., description="Name of the app")
) -> str:
    try:
        client = get_sagemaker_client()

        # Create the app
        response = client.create_app(
            DomainId=domain_id,
            SpaceName=space_name,
            AppType=app_type,
            AppName=app_name
        )

        result = {
            "success": True,
            "app_details": response,
            "message": f"Successfully created SageMaker Space App: {app_name}"
        }

        return json.dumps(result, indent=2, default=str)

    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "message": f"Failed to create SageMaker Space App: {app_name}"
        }

        return json.dumps(error_result, indent=2)

# delete_app
@mcp.tool(description="Stop/Delete a SageMaker Space app")
async def delete_sm_space_app(
    domain_id: str = Field(..., description="Domain ID of the app"),
    space_name: str = Field(..., description="Space name of the app"),
    app_type: str = Field(..., description="Type of the app - JupyterServer|KernelGateway|DetailedProfiler|TensorBoard|CodeEditor|JupyterLab|RStudioServerPro|RSessionGateway|Canvas"),
    app_name: str = Field(..., description="Name of the app")
) -> str:
    try:
        client = get_sagemaker_client()

        # Delete the app
        response = client.delete_app(
            DomainId=domain_id,
            SpaceName=space_name,
            AppType=app_type,
            AppName=app_name
        )

        result = {
            "success": True,
            "message": f"Successfully deleted SageMaker Space App: {app_name}"
        }

        return json.dumps(result, indent=2, default=str)

    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "message": f"Failed to delete SageMaker Space App: {app_name}"
        }

        return json.dumps(error_result, indent=2)
# Domain Tools
@mcp.tool(description="List SageMaker Studio domains in your AWS account")
async def list_sm_domains(
    max_results: int = Field(default=10, description="Maximum number of results to return")
) -> str:
    try:
        client = get_sagemaker_client()
        
        # Prepare the request
        request = {
            'MaxResults': max_results
        }
       
        # List domains
        response = client.list_domains(**request)
        
        result = {
            "success": True,
            "domains": response.get('Domains', []),
            "next_token": response.get('NextToken'),
            "total_count": len(response.get('Domains', [])),
            "message": "Successfully retrieved SageMaker Domains list"
        }
        
        return json.dumps(result, indent=2, default=str)
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "message": "Failed to list SageMaker Domains"
        }
        
        return json.dumps(error_result, indent=2)    

@mcp.tool(description="Get detailed information about a specific SageMaker Studio domain")
async def describe_sm_domain(
    domain_id: str = Field(..., description="Unique identifier of the domain")
) -> str:
    try:
        client = get_sagemaker_client()

        # Describe the domain
        response = client.describe_domain(DomainId=domain_id)

        result = {
            "success": True,
            "domain_details": response,
            "domain_id": domain_id,
            "message": f"Successfully retrieved details for domain: {domain_id}"
        }

        return json.dumps(result, indent=2, default=str)

    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "message": f"Failed to describe SageMaker Domain: {domain_id}"
        }

        return json.dumps(error_result, indent=2)

# Endpoint Tools
@mcp.tool(description="List SageMaker endpoints with optional filtering and sorting")
async def list_sm_endpoints(
    sort_by: str = Field(default="CreationTime", description="Sort criteria (Name, CreationTime, Status)"),
    sort_order: str = Field(default="Descending", description="Sort order (Ascending, Descending)"),
    name_contains: Optional[str] = Field(default=None, description="Filter endpoints by name containing this string"),
    status_equals: Optional[str] = Field(default=None, description="Filter endpoints by status"),
    max_results: int = Field(default=10, description="Maximum number of results to return")
) -> str:
    """List SageMaker endpoints with optional filtering."""
    try:
        client = get_sagemaker_client()
        
        # Prepare the request
        request = {
            'SortBy': sort_by,
            'SortOrder': sort_order,
            'MaxResults': max_results
        }
        
        if name_contains:
            request['NameContains'] = name_contains
        
        if status_equals:
            request['StatusEquals'] = status_equals
        
        # List endpoints
        response = client.list_endpoints(**request)
        
        result = {
            "success": True,
            "endpoints": response.get('Endpoints', []),
            "next_token": response.get('NextToken'),
            "total_count": len(response.get('Endpoints', [])),
            "message": "Successfully retrieved SageMaker endpoints list"
        }
        
        return json.dumps(result, indent=2, default=str)
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "message": "Failed to list SageMaker endpoints"
        }
        
        return json.dumps(error_result, indent=2)


@mcp.tool(description="Get detailed information about a specific SageMaker endpoint")
async def describe_sm_endpoint(
    endpoint_name: str = Field(..., description="Name of the endpoint to describe")
) -> str:
    """Get detailed information about a SageMaker endpoint."""
    try:
        client = get_sagemaker_client()
        
        # Describe the endpoint
        response = client.describe_endpoint(EndpointName=endpoint_name)
        
        result = {
            "success": True,
            "endpoint_details": response,
            "endpoint_name": endpoint_name,
            "message": f"Successfully retrieved details for endpoint: {endpoint_name}"
        }
        
        return json.dumps(result, indent=2, default=str)
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "message": f"Failed to describe SageMaker endpoint: {endpoint_name}"
        }
        
        return json.dumps(error_result, indent=2)


@mcp.tool(description="Invoke a SageMaker endpoint for real-time inference with input data")
async def invoke_sm_endpoint(
    endpoint_name: str = Field(..., description="Name of the endpoint to invoke"),
    body: str = Field(..., description="Input data for the endpoint (JSON string)"),
    content_type: str = Field(default="application/json", description="Content type of the input data"),
    accept: str = Field(default="application/json", description="Accept header for the response")
) -> str:
    """Invoke a SageMaker endpoint for inference."""
    try:
        require_sensitive_data_access()
        
        client = get_sagemaker_runtime_client()
        
        # Invoke the endpoint
        response = client.invoke_endpoint(
            EndpointName=endpoint_name,
            Body=body,
            ContentType=content_type,
            Accept=accept
        )
        
        # Read the response body
        response_body = response['Body'].read().decode('utf-8')
        
        result = {
            "success": True,
            "endpoint_name": endpoint_name,
            "response_body": response_body,
            "content_type": response.get('ContentType'),
            "invoked_production_variant": response.get('InvokedProductionVariant'),
            "message": f"Successfully invoked endpoint: {endpoint_name}"
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "message": "Failed to invoke SageMaker endpoint"
        }
        
        return json.dumps(error_result, indent=2)

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Amazon SageMaker MCP Server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'amazon-sagemaker-mcp-server {__version__}'
    )
    
    parser.add_argument(
        '--allow-write',
        action='store_true',
        help='Allow write operations (create, update, delete resources)'
    )
    
    parser.add_argument(
        '--allow-sensitive-data-access',
        action='store_true',
        help='Allow access to sensitive data (endpoint invocation results)'
    )
    
    return parser.parse_args()


def main():
    """Main entry point for the server."""
    args = parse_args()
    
    # Set global flags based on arguments
    os.environ['ALLOW_WRITE'] = str(args.allow_write).lower()
    os.environ['ALLOW_SENSITIVE_DATA_ACCESS'] = str(args.allow_sensitive_data_access).lower()
    
    # Validate AWS configuration
    if not os.getenv('AWS_REGION'):
        os.environ['AWS_REGION'] = 'us-east-1'
    
    # Validate AWS credentials
    if not validate_aws_credentials():
        logger.error("Failed to validate AWS credentials. Please check your AWS configuration.")
        sys.exit(1)
    
    # Run the server
    mcp.run()


if __name__ == '__main__':
    main()
