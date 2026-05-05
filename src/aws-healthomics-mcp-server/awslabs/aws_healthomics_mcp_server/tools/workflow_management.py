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

"""Workflow management tools for the AWS HealthOmics MCP server."""

from awslabs.aws_healthomics_mcp_server.consts import (
    DEFAULT_MAX_RESULTS,
    ERROR_INVALID_ACCELERATOR,
    ERROR_INVALID_ENGINE,
    ERROR_INVALID_EXPORT_TYPE,
    ERROR_INVALID_STORAGE_TYPE,
    ERROR_INVALID_WORKFLOW_TYPE,
    ERROR_STATIC_STORAGE_REQUIRES_CAPACITY,
    STORAGE_TYPES,
)
from awslabs.aws_healthomics_mcp_server.models.core import (
    AcceleratorType,
    ExportType,
    GetWorkflowType,
    StorageType,
    WorkflowEngine,
)
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
    get_omics_client,
)
from awslabs.aws_healthomics_mcp_server.utils.error_utils import (
    handle_tool_error,
)
from awslabs.aws_healthomics_mcp_server.utils.validation_utils import (
    parse_tags,
    validate_container_registry_params,
    validate_definition_sources,
    validate_path_to_main,
    validate_readme_input,
    validate_repository_path_params,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any, Dict, Optional


async def list_workflows(
    ctx: Context,
    max_results: int = Field(
        DEFAULT_MAX_RESULTS,
        description='Maximum number of results to return',
        ge=1,
        le=100,
    ),
    next_token: Optional[str] = Field(
        None,
        description='Token for pagination from a previous response',
    ),
    aws_profile: Optional[str] = Field(
        None,
        description='AWS profile name for this operation. Overrides the default credential chain.',
    ),
    aws_region: Optional[str] = Field(
        None,
        description='AWS region for this operation. Overrides the server default.',
    ),
) -> Dict[str, Any]:
    """List available HealthOmics workflows.

    Args:
        ctx: MCP context for error reporting
        max_results: Maximum number of results to return (default: 10)
        next_token: Token for pagination
        aws_profile: Optional AWS profile name override
        aws_region: Optional AWS region override

    Returns:
        Dictionary containing workflow information and next token if available
    """
    client = get_omics_client(region_name=aws_region, profile_name=aws_profile)

    params: dict[str, Any] = {'maxResults': max_results}
    if next_token:
        params['startingToken'] = next_token

    try:
        response = client.list_workflows(**params)

        # Transform the response to a more user-friendly format
        workflows = []
        for workflow in response.get('items', []):
            creation_time = workflow.get('creationTime')
            workflows.append(
                {
                    'id': workflow.get('id'),
                    'arn': workflow.get('arn'),
                    'name': workflow.get('name'),
                    'description': workflow.get('description'),
                    'status': workflow.get('status'),
                    'parameters': workflow.get('parameters'),
                    'storageType': workflow.get('storageType'),
                    'storageCapacity': workflow.get('storageCapacity'),
                    'type': workflow.get('type'),
                    'creationTime': creation_time.isoformat()
                    if creation_time is not None
                    else None,
                }
            )

        result: Dict[str, Any] = {'workflows': workflows}
        if 'nextToken' in response:
            result['nextToken'] = response['nextToken']

        return result
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error listing workflows')


async def create_workflow(
    ctx: Context,
    name: str = Field(
        ...,
        description='Name of the workflow',
    ),
    definition_source: Optional[str] = Field(
        None,
        description='Workflow definition content: a local ZIP file path, S3 URI (s3://bucket/key.zip), or base64-encoded ZIP content. Cannot be used together with definition_uri or definition_repository.',
    ),
    description: Optional[str] = Field(
        None,
        description='Optional description of the workflow',
    ),
    parameter_template: Optional[Dict[str, Any]] = Field(
        None,
        description='Optional parameter template for the workflow',
    ),
    container_registry_map: Optional[Dict[str, Any]] = Field(
        None,
        description='Optional container registry map with registryMappings (upstreamRegistryUrl, ecrRepositoryPrefix, upstreamRepositoryPrefix, ecrAccountId) and imageMappings (sourceImage, destinationImage) arrays',
    ),
    container_registry_map_uri: Optional[str] = Field(
        None,
        description='Optional S3 URI pointing to a JSON file containing container registry mappings. Cannot be used together with container_registry_map',
    ),
    definition_uri: Optional[str] = Field(
        None,
        description='S3 URI of the workflow definition ZIP file. Cannot be used together with definition_source or definition_repository',
    ),
    path_to_main: Annotated[
        Optional[str],
        Field(
            description='Path to the main file in the workflow definition ZIP file. Not required if there is a top level main.wdl, main.cwl or main.nf files in the workflow package. Not required if there is only a single top level workflow file.',
        ),
    ] = None,
    readme: Optional[str] = Field(
        None,
        description='README documentation: markdown content, local .md file path, or S3 URI (s3://bucket/key)',
    ),
    definition_repository: Optional[Dict[str, Any]] = Field(
        None,
        description='Git repository configuration with connection_arn, full_repository_id, source_reference (type and value), and optional exclude_file_patterns. Cannot be used together with definition_source or definition_uri',
    ),
    parameter_template_path: Optional[str] = Field(
        None,
        description='Path to parameter template JSON file within the repository (only valid with definition_repository)',
    ),
    readme_path: Optional[str] = Field(
        None,
        description='Path to README markdown file within the repository (only valid with definition_repository)',
    ),
    engine: Optional[str] = Field(
        None,
        description="Workflow engine type (WDL, NEXTFLOW, CWL, WDL_LENIENT). WDL_LENIENT allows for some WDL directives that don't strictly meet the WDL spec and can be useful when migrating legacy workflows designed to run on Cromwell",
    ),
    storage_type: Optional[str] = Field(
        None,
        description='Storage type for workflow runs (STATIC or DYNAMIC)',
    ),
    storage_capacity: Optional[int] = Field(
        None,
        description='Default static storage capacity in GiB for workflow runs (required when storage_type is STATIC)',
        ge=1024,
    ),
    tags: Optional[Any] = Field(
        None,
        description='Tags to apply to the workflow as a dict or JSON string, e.g. {"key": "value"}',
    ),
    accelerators: Optional[str] = Field(
        None,
        description='Computational accelerator type (GPU). Currently unused by the HealthOmics service. Reserved for future support.',
    ),
    workflow_bucket_owner_id: Optional[str] = Field(
        None,
        description='Expected AWS account ID of the S3 bucket owner for definition URI validation',
    ),
    definition_zip_base64: Optional[str] = Field(
        None,
        description='[Deprecated: use definition_source] Base64-encoded workflow definition ZIP file.',
    ),
    aws_profile: Optional[str] = Field(
        None,
        description='AWS profile name for this operation. Overrides the default credential chain.',
    ),
    aws_region: Optional[str] = Field(
        None,
        description='AWS region for this operation. Overrides the server default.',
    ),
) -> Dict[str, Any]:
    """Create a new HealthOmics workflow.

    Args:
        ctx: MCP context for error reporting
        name: Name of the workflow
        definition_source: Workflow definition content — a local ZIP file path,
            S3 URI (s3://bucket/key.zip), or base64-encoded ZIP content.
            Cannot be used together with definition_uri or definition_repository
        description: Optional description of the workflow
        parameter_template: Optional parameter template for the workflow
        container_registry_map: Optional container registry map with registryMappings (upstreamRegistryUrl, ecrRepositoryPrefix, upstreamRepositoryPrefix, ecrAccountId) and imageMappings (sourceImage, destinationImage) arrays
        container_registry_map_uri: Optional S3 URI pointing to a JSON file containing container registry mappings. Cannot be used together with container_registry_map
        definition_uri: S3 URI of the workflow definition ZIP file. Cannot be used together with definition_source or definition_repository
        path_to_main: Path to the main file in the workflow definition ZIP file. Not required if there is a top level main.wdl, main.cwl or main.nf files in the workflow package. Not required if there is only a single top level workflow file.
        readme: README documentation - can be markdown content, local .md file path, or S3 URI (s3://bucket/key)
        definition_repository: Git repository configuration with connection_arn, full_repository_id, source_reference, and optional exclude_file_patterns
        parameter_template_path: Path to parameter template JSON file within the repository (only valid with definition_repository)
        readme_path: Path to README markdown file within the repository (only valid with definition_repository)
        engine: Workflow engine type. WDL_LENIENT allows for some WDL directives
            that don't strictly meet the WDL spec and can be useful when migrating
            legacy workflows designed to run on Cromwell.
        storage_type: Storage type for workflow runs (STATIC or DYNAMIC)
        storage_capacity: Default static storage capacity in GiB (required when
            storage_type is STATIC). Minumum of 1024.
        tags: Tags to apply to the workflow as a dict or JSON string
        accelerators: Computational accelerator type. Currently unused by the
            HealthOmics service. Reserved for future support.
        workflow_bucket_owner_id: Expected AWS account ID of the S3 bucket owner
        definition_zip_base64: **Deprecated** — use definition_source instead.
            Base64-encoded workflow definition ZIP file.
        aws_profile: Optional AWS profile name override
        aws_region: Optional AWS region override

    Returns:
        Dictionary containing the created workflow information or error dict
    """
    try:
        # Handle Field objects for optional parameters (FastMCP compatibility)
        if hasattr(engine, 'default') and not isinstance(engine, (str, type(None))):
            engine = getattr(engine, 'default', None)
        if hasattr(storage_type, 'default') and not isinstance(storage_type, (str, type(None))):
            storage_type = getattr(storage_type, 'default', None)
        if hasattr(storage_capacity, 'default') and not isinstance(
            storage_capacity, (int, type(None))
        ):
            storage_capacity = getattr(storage_capacity, 'default', None)
        if hasattr(tags, 'default') and not isinstance(tags, (dict, str, type(None))):
            tags = getattr(tags, 'default', None)
        if hasattr(accelerators, 'default') and not isinstance(accelerators, (str, type(None))):
            accelerators = getattr(accelerators, 'default', None)
        if hasattr(workflow_bucket_owner_id, 'default') and not isinstance(
            workflow_bucket_owner_id, (str, type(None))
        ):
            workflow_bucket_owner_id = getattr(workflow_bucket_owner_id, 'default', None)

        # Validate definition sources and container registry parameters
        (
            definition_zip,
            validated_definition_uri,
            validated_repository,
        ) = await validate_definition_sources(
            ctx, definition_source, definition_uri, definition_repository, definition_zip_base64
        )
        validated_container_registry_map = await validate_container_registry_params(
            ctx, container_registry_map, container_registry_map_uri
        )

        # Validate path_to_main parameter
        validated_path_to_main = await validate_path_to_main(ctx, path_to_main)

        # Validate repository-specific path parameters
        (
            validated_param_template_path,
            validated_readme_path,
        ) = await validate_repository_path_params(
            ctx, definition_repository, parameter_template_path, readme_path
        )

        # Validate and process README input
        readme_markdown, readme_uri = await validate_readme_input(ctx, readme)

        # Validate engine parameter
        if engine is not None:
            try:
                WorkflowEngine(engine)
            except ValueError:
                error_message = ERROR_INVALID_ENGINE.format(
                    ', '.join(e.value for e in WorkflowEngine)
                )
                logger.error(error_message)
                await ctx.error(error_message)
                raise ValueError(error_message)

        # Validate storage_type parameter
        if storage_type is not None:
            try:
                StorageType(storage_type)
            except ValueError:
                error_message = ERROR_INVALID_STORAGE_TYPE.format(', '.join(STORAGE_TYPES))
                logger.error(error_message)
                await ctx.error(error_message)
                raise ValueError(error_message)
            if storage_type == 'STATIC':
                if not storage_capacity:
                    error_message = ERROR_STATIC_STORAGE_REQUIRES_CAPACITY
                    logger.error(error_message)
                    await ctx.error(error_message)
                    raise ValueError(error_message)

        # Validate tags parameter
        validated_tags = None
        if tags is not None:
            validated_tags = parse_tags(tags)

        # Validate accelerators parameter
        if accelerators is not None:
            try:
                AcceleratorType(accelerators)
            except ValueError:
                error_message = ERROR_INVALID_ACCELERATOR.format(
                    ', '.join(e.value for e in AcceleratorType)
                )
                logger.error(error_message)
                await ctx.error(error_message)
                raise ValueError(error_message)

        client = get_omics_client(region_name=aws_region, profile_name=aws_profile)

        params: Dict[str, Any] = {
            'name': name,
        }

        # Add definition source (either ZIP, S3 URI, or repository)
        if definition_zip is not None:
            params['definitionZip'] = definition_zip
        elif validated_definition_uri is not None:
            params['definitionUri'] = validated_definition_uri
        elif validated_repository is not None:
            params['definitionRepository'] = validated_repository

        if description:
            params['description'] = description

        if parameter_template:
            params['parameterTemplate'] = parameter_template

        if validated_container_registry_map is not None:
            params['containerRegistryMap'] = validated_container_registry_map

        if container_registry_map_uri:
            params['containerRegistryMapUri'] = container_registry_map_uri

        if validated_path_to_main is not None:
            params['main'] = validated_path_to_main

        # Add repository-specific path parameters
        if validated_param_template_path is not None:
            params['parameterTemplatePath'] = validated_param_template_path

        if validated_readme_path is not None:
            params['readmePath'] = validated_readme_path

        if readme_markdown is not None:
            params['readmeMarkdown'] = readme_markdown

        if readme_uri is not None:
            params['readmeUri'] = readme_uri

        # Add new parameters
        if engine is not None:
            params['engine'] = engine

        if storage_type is not None:
            params['storageType'] = storage_type
            if storage_type == 'STATIC':
                params['storageCapacity'] = storage_capacity

        if validated_tags is not None:
            params['tags'] = validated_tags

        if accelerators is not None:
            params['accelerators'] = accelerators

        if workflow_bucket_owner_id is not None:
            params['workflowBucketOwnerId'] = workflow_bucket_owner_id

        response = client.create_workflow(**params)

        return {
            'id': response.get('id'),
            'arn': response.get('arn'),
            'status': response.get('status'),
            'name': name,
            'description': description,
            'tags': response.get('tags'),
            'uuid': response.get('uuid'),
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error creating workflow')


async def get_workflow(
    ctx: Context,
    workflow_id: str = Field(
        ...,
        description='ID of the workflow to retrieve',
    ),
    export_definition: bool = Field(
        False,
        description='Whether to include a presigned URL for downloading the workflow definition ZIP file',
    ),
    workflow_type: Optional[str] = Field(
        None,
        description='Workflow type filter (PRIVATE or READY2RUN). Use READY2RUN to access AWS-provided workflows',
    ),
    workflow_owner_id: Optional[str] = Field(
        None,
        description='AWS account ID of the workflow owner, used for accessing shared workflows',
    ),
    export: Optional[list] = Field(
        None,
        description='List of export types (DEFINITION, README) specifying what presigned URLs to include. Takes precedence over export_definition when provided',
    ),
    aws_profile: Optional[str] = Field(
        None,
        description='AWS profile name for this operation. Overrides the default credential chain.',
    ),
    aws_region: Optional[str] = Field(
        None,
        description='AWS region for this operation. Overrides the server default.',
    ),
) -> Dict[str, Any]:
    """Get details about a specific workflow.

    Args:
        ctx: MCP context for error reporting
        workflow_id: ID of the workflow to retrieve
        export_definition: Whether to include a presigned URL for downloading the
            workflow definition ZIP file
        workflow_type: Workflow type filter (PRIVATE or READY2RUN)
        workflow_owner_id: AWS account ID of the workflow owner
        export: List of export types (DEFINITION, README) for presigned URLs.
            Takes precedence over export_definition when provided.
        aws_profile: Optional AWS profile name override
        aws_region: Optional AWS region override

    Returns:
        Dictionary containing workflow details. When export or export_definition is set,
        includes presigned URLs for downloading the requested workflow artifacts.
    """
    try:
        # Handle Field objects for optional parameters (FastMCP compatibility)
        if hasattr(workflow_type, 'default') and not isinstance(workflow_type, (str, type(None))):
            workflow_type = getattr(workflow_type, 'default', None)
        if hasattr(workflow_owner_id, 'default') and not isinstance(
            workflow_owner_id, (str, type(None))
        ):
            workflow_owner_id = getattr(workflow_owner_id, 'default', None)
        if hasattr(export, 'default') and not isinstance(export, (list, type(None))):
            export = getattr(export, 'default', None)

        # Validate workflow_type parameter
        if workflow_type is not None:
            try:
                GetWorkflowType(workflow_type)
            except ValueError:
                error_message = ERROR_INVALID_WORKFLOW_TYPE.format(
                    ', '.join(e.value for e in GetWorkflowType)
                )
                logger.error(error_message)
                await ctx.error(error_message)
                raise ValueError(error_message)

        # Validate export list parameter
        if export is not None:
            for item in export:
                try:
                    ExportType(item)
                except ValueError:
                    error_message = ERROR_INVALID_EXPORT_TYPE.format(
                        ', '.join(e.value for e in ExportType)
                    )
                    logger.error(error_message)
                    await ctx.error(error_message)
                    raise ValueError(error_message)

        client = get_omics_client(region_name=aws_region, profile_name=aws_profile)

        params: dict[str, Any] = {'id': workflow_id}

        # Determine export list: explicit export takes precedence over export_definition
        if export is not None:
            params['export'] = export
        elif export_definition:
            params['export'] = ['DEFINITION']

        if workflow_type is not None:
            params['type'] = workflow_type

        if workflow_owner_id is not None:
            params['workflowOwnerId'] = workflow_owner_id

        response = client.get_workflow(**params)

        result = {
            'id': response.get('id'),
            'arn': response.get('arn'),
            'name': response.get('name'),
            'status': response.get('status'),
            'type': response.get('type'),
            'creationTime': response.get('creationTime').isoformat()
            if response.get('creationTime')
            else None,
        }

        if 'description' in response:
            result['description'] = response['description']

        if 'statusMessage' in response:
            result['statusMessage'] = response['statusMessage']

        if 'parameterTemplate' in response:
            result['parameterTemplate'] = response['parameterTemplate']

        if 'definition' in response:
            result['definition'] = response['definition']

        if 'containerRegistryMap' in response:
            result['containerRegistryMap'] = response['containerRegistryMap']

        if 'engine' in response:
            result['engine'] = response['engine']

        if 'main' in response:
            result['main'] = response['main']

        if 'digest' in response:
            result['digest'] = response['digest']

        if 'storageCapacity' in response:
            result['storageCapacity'] = response['storageCapacity']

        if 'storageType' in response:
            result['storageType'] = response['storageType']

        if 'tags' in response:
            result['tags'] = response['tags']

        if 'metadata' in response:
            result['metadata'] = dict(response['metadata'])

        if 'accelerators' in response:
            result['accelerators'] = response['accelerators']

        if 'uuid' in response:
            result['uuid'] = response['uuid']

        if 'readme' in response:
            result['readme'] = response['readme']

        if 'definitionRepositoryDetails' in response:
            result['definitionRepositoryDetails'] = response['definitionRepositoryDetails']

        if 'readmePath' in response:
            result['readmePath'] = response['readmePath']

        return result
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error getting workflow')


async def create_workflow_version(
    ctx: Context,
    workflow_id: str = Field(
        ...,
        description='ID of the workflow',
    ),
    version_name: str = Field(
        ...,
        description='Name for the new version',
    ),
    definition_source: Optional[str] = Field(
        None,
        description='Workflow definition content: a local ZIP file path, S3 URI (s3://bucket/key.zip), or base64-encoded ZIP content. Cannot be used together with definition_uri or definition_repository.',
    ),
    description: Optional[str] = Field(
        None,
        description='Optional description of the workflow version',
    ),
    parameter_template: Optional[Dict[str, Any]] = Field(
        None,
        description='Optional parameter template for the workflow',
    ),
    storage_type: Optional[str] = Field(
        'DYNAMIC',
        description='Storage type (STATIC or DYNAMIC)',
    ),
    storage_capacity: Optional[int] = Field(
        None,
        description='Storage capacity in GB (required for STATIC)',
        ge=1,
    ),
    container_registry_map: Optional[Dict[str, Any]] = Field(
        None,
        description='Optional container registry map with registryMappings (upstreamRegistryUrl, ecrRepositoryPrefix, upstreamRepositoryPrefix, ecrAccountId) and imageMappings (sourceImage, destinationImage) arrays',
    ),
    container_registry_map_uri: Optional[str] = Field(
        None,
        description='Optional S3 URI pointing to a JSON file containing container registry mappings. Cannot be used together with container_registry_map',
    ),
    definition_uri: Optional[str] = Field(
        None,
        description='S3 URI of the workflow definition ZIP file. Cannot be used together with definition_source or definition_repository',
    ),
    path_to_main: Annotated[
        Optional[str],
        Field(
            description='Path to the main file in the workflow definition ZIP file. Not required if there is a top level main.wdl, main.cwl or main.nf files in the workflow package. Not required if there is only a single top level workflow file.',
        ),
    ] = None,
    readme: Optional[str] = Field(
        None,
        description='README documentation: markdown content, local .md file path, or S3 URI (s3://bucket/key)',
    ),
    definition_repository: Optional[Dict[str, Any]] = Field(
        None,
        description='Git repository configuration with connection_arn, full_repository_id, source_reference (type and value), and optional exclude_file_patterns. Cannot be used together with definition_source or definition_uri',
    ),
    parameter_template_path: Optional[str] = Field(
        None,
        description='Path to parameter template JSON file within the repository (only valid with definition_repository)',
    ),
    readme_path: Optional[str] = Field(
        None,
        description='Path to README markdown file within the repository (only valid with definition_repository)',
    ),
    engine: Optional[str] = Field(
        None,
        description="Workflow engine type (WDL, NEXTFLOW, CWL, WDL_LENIENT). WDL_LENIENT allows for some WDL directives that don't strictly meet the WDL spec and can be useful when migrating legacy workflows designed to run on Cromwell",
    ),
    tags: Optional[Any] = Field(
        None,
        description='Tags to apply to the workflow version as a dict or JSON string, e.g. {"key": "value"}',
    ),
    accelerators: Optional[str] = Field(
        None,
        description='Computational accelerator type (GPU). Currently unused by the HealthOmics service. Reserved for future support.',
    ),
    workflow_bucket_owner_id: Optional[str] = Field(
        None,
        description='Expected AWS account ID of the S3 bucket owner for definition URI validation',
    ),
    definition_zip_base64: Optional[str] = Field(
        None,
        description='[Deprecated: use definition_source] Base64-encoded workflow definition ZIP file.',
    ),
    aws_profile: Optional[str] = Field(
        None,
        description='AWS profile name for this operation. Overrides the default credential chain.',
    ),
    aws_region: Optional[str] = Field(
        None,
        description='AWS region for this operation. Overrides the server default.',
    ),
) -> Dict[str, Any]:
    """Create a new version of an existing workflow.

    Args:
        ctx: MCP context for error reporting
        workflow_id: ID of the workflow
        version_name: Name for the new version
        definition_source: Workflow definition content — a local ZIP file path,
            S3 URI (s3://bucket/key.zip), or base64-encoded ZIP content.
            Cannot be used together with definition_uri or definition_repository
        description: Optional description of the workflow version
        parameter_template: Optional parameter template for the workflow
        storage_type: Storage type (STATIC or DYNAMIC)
        storage_capacity: Storage capacity in GB (required for STATIC)
        container_registry_map: Optional container registry map with registryMappings (upstreamRegistryUrl, ecrRepositoryPrefix, upstreamRepositoryPrefix, ecrAccountId) and imageMappings (sourceImage, destinationImage) arrays
        container_registry_map_uri: Optional S3 URI pointing to a JSON file containing container registry mappings. Cannot be used together with container_registry_map
        definition_uri: S3 URI of the workflow definition ZIP file. Cannot be used together with definition_source or definition_repository
        path_to_main: Path to the main file in the workflow definition ZIP file. Not required if there is a top level main.wdl, main.cwl or main.nf files in the workflow package. Not required if there is only a single top level workflow file.
        readme: README documentation - can be markdown content, local .md file path, or S3 URI (s3://bucket/key)
        definition_repository: Git repository configuration with connection_arn, full_repository_id, source_reference, and optional exclude_file_patterns
        parameter_template_path: Path to parameter template JSON file within the repository (only valid with definition_repository)
        readme_path: Path to README markdown file within the repository (only valid with definition_repository)
        engine: Workflow engine type. WDL_LENIENT allows for some WDL directives
            that don't strictly meet the WDL spec and can be useful when migrating
            legacy workflows designed to run on Cromwell.
        tags: Tags to apply to the workflow version as a dict or JSON string
        accelerators: Computational accelerator type. Currently unused by the
            HealthOmics service. Reserved for future support.
        workflow_bucket_owner_id: Expected AWS account ID of the S3 bucket owner
        definition_zip_base64: **Deprecated** — use definition_source instead.
            Base64-encoded workflow definition ZIP file.
        aws_profile: Optional AWS profile name override
        aws_region: Optional AWS region override

    Returns:
        Dictionary containing the created workflow version information
    """
    try:
        # Handle Field objects for optional parameters (FastMCP compatibility)
        if hasattr(engine, 'default') and not isinstance(engine, (str, type(None))):
            engine = getattr(engine, 'default', None)
        if hasattr(storage_type, 'default') and not isinstance(storage_type, (str, type(None))):
            storage_type = getattr(storage_type, 'default', None)
        if hasattr(storage_capacity, 'default') and not isinstance(
            storage_capacity, (int, type(None))
        ):
            storage_capacity = getattr(storage_capacity, 'default', None)
        if hasattr(tags, 'default') and not isinstance(tags, (dict, str, type(None))):
            tags = getattr(tags, 'default', None)
        if hasattr(accelerators, 'default') and not isinstance(accelerators, (str, type(None))):
            accelerators = getattr(accelerators, 'default', None)
        if hasattr(workflow_bucket_owner_id, 'default') and not isinstance(
            workflow_bucket_owner_id, (str, type(None))
        ):
            workflow_bucket_owner_id = getattr(workflow_bucket_owner_id, 'default', None)

        # Validate definition sources and container registry parameters
        (
            definition_zip,
            validated_definition_uri,
            validated_repository,
        ) = await validate_definition_sources(
            ctx, definition_source, definition_uri, definition_repository, definition_zip_base64
        )
        validated_container_registry_map = await validate_container_registry_params(
            ctx, container_registry_map, container_registry_map_uri
        )

        # Validate path_to_main parameter
        validated_path_to_main = await validate_path_to_main(ctx, path_to_main)

        # Validate repository-specific path parameters
        (
            validated_param_template_path,
            validated_readme_path,
        ) = await validate_repository_path_params(
            ctx, definition_repository, parameter_template_path, readme_path
        )

        # Validate engine parameter
        if engine is not None:
            try:
                WorkflowEngine(engine)
            except ValueError:
                error_message = ERROR_INVALID_ENGINE.format(
                    ', '.join(e.value for e in WorkflowEngine)
                )
                logger.error(error_message)
                await ctx.error(error_message)
                raise ValueError(error_message)

        # Validate storage_type parameter
        if storage_type is not None:
            try:
                StorageType(storage_type)
            except ValueError:
                error_message = ERROR_INVALID_STORAGE_TYPE.format(', '.join(STORAGE_TYPES))
                logger.error(error_message)
                await ctx.error(error_message)
                raise ValueError(error_message)
            if storage_type == 'STATIC':
                if not storage_capacity:
                    error_message = ERROR_STATIC_STORAGE_REQUIRES_CAPACITY
                    logger.error(error_message)
                    await ctx.error(error_message)
                    raise ValueError(error_message)

        # Validate tags parameter
        validated_tags = None
        if tags is not None:
            validated_tags = parse_tags(tags)

        # Validate accelerators parameter
        if accelerators is not None:
            try:
                AcceleratorType(accelerators)
            except ValueError:
                error_message = ERROR_INVALID_ACCELERATOR.format(
                    ', '.join(e.value for e in AcceleratorType)
                )
                logger.error(error_message)
                await ctx.error(error_message)
                raise ValueError(error_message)

        # Validate and process README input
        readme_markdown, readme_uri = await validate_readme_input(ctx, readme)

        client = get_omics_client(region_name=aws_region, profile_name=aws_profile)

        params: Dict[str, Any] = {
            'workflowId': workflow_id,
            'versionName': version_name,
        }

        if storage_type is not None:
            params['storageType'] = storage_type

        # Add definition source (either ZIP, S3 URI, or repository)
        if definition_zip is not None:
            params['definitionZip'] = definition_zip
        elif validated_definition_uri is not None:
            params['definitionUri'] = validated_definition_uri
        elif validated_repository is not None:
            params['definitionRepository'] = validated_repository

        if description:
            params['description'] = description

        if parameter_template:
            params['parameterTemplate'] = parameter_template

        if storage_type == 'STATIC':
            params['storageCapacity'] = storage_capacity

        if validated_container_registry_map is not None:
            params['containerRegistryMap'] = validated_container_registry_map

        if container_registry_map_uri:
            params['containerRegistryMapUri'] = container_registry_map_uri

        if validated_path_to_main is not None:
            params['main'] = validated_path_to_main

        # Add repository-specific path parameters
        if validated_param_template_path is not None:
            params['parameterTemplatePath'] = validated_param_template_path

        if validated_readme_path is not None:
            params['readmePath'] = validated_readme_path

        if readme_markdown is not None:
            params['readmeMarkdown'] = readme_markdown

        if readme_uri is not None:
            params['readmeUri'] = readme_uri

        # Add new parameters
        if engine is not None:
            params['engine'] = engine

        if validated_tags is not None:
            params['tags'] = validated_tags

        if accelerators is not None:
            params['accelerators'] = accelerators

        if workflow_bucket_owner_id is not None:
            params['workflowBucketOwnerId'] = workflow_bucket_owner_id

        response = client.create_workflow_version(**params)

        return {
            'id': response.get('id'),
            'arn': response.get('arn'),
            'status': response.get('status'),
            'name': response.get('name'),
            'versionName': version_name,
            'description': description,
            'tags': response.get('tags'),
            'uuid': response.get('uuid'),
        }
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error creating workflow version')


async def list_workflow_versions(
    ctx: Context,
    workflow_id: str = Field(
        ...,
        description='ID of the workflow',
    ),
    max_results: int = Field(
        DEFAULT_MAX_RESULTS,
        description='Maximum number of results to return',
        ge=1,
        le=100,
    ),
    next_token: Optional[str] = Field(
        None,
        description='Token for pagination from a previous response',
    ),
    aws_profile: Optional[str] = Field(
        None,
        description='AWS profile name for this operation. Overrides the default credential chain.',
    ),
    aws_region: Optional[str] = Field(
        None,
        description='AWS region for this operation. Overrides the server default.',
    ),
) -> Dict[str, Any]:
    """List versions of a workflow.

    Args:
        ctx: MCP context for error reporting
        workflow_id: ID of the workflow
        max_results: Maximum number of results to return (default: 10)
        next_token: Token for pagination
        aws_profile: Optional AWS profile name override
        aws_region: Optional AWS region override

    Returns:
        Dictionary containing workflow version information and next token if available
    """
    client = get_omics_client(region_name=aws_region, profile_name=aws_profile)

    params: Dict[str, Any] = {
        'workflowId': workflow_id,
        'maxResults': max_results,
    }

    if next_token:
        params['startingToken'] = next_token

    try:
        response = client.list_workflow_versions(**params)

        # Transform the response to a more user-friendly format
        versions = []
        for version in response.get('items', []):
            creation_time = version.get('creationTime')
            versions.append(
                {
                    'id': version.get('id'),
                    'arn': version.get('arn'),
                    'name': version.get('name'),
                    'versionName': version.get('versionName'),
                    'status': version.get('status'),
                    'type': version.get('type'),
                    'description': version.get('description'),
                    'creationTime': (
                        creation_time
                        if isinstance(creation_time, str)
                        else creation_time.isoformat()
                        if creation_time is not None
                        else None
                    ),
                }
            )

        result: Dict[str, Any] = {'versions': versions}
        if 'nextToken' in response:
            result['nextToken'] = response['nextToken']

        return result
    except Exception as e:
        return await handle_tool_error(ctx, e, 'Error listing workflow versions')
