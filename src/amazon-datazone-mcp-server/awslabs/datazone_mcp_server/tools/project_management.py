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
"""Project management tools for Amazon DataZone."""

from .common import USER_AGENT, ClientError, datazone_client, httpx, logger
from mcp.server.fastmcp import FastMCP
from typing import Any, Dict, List, Optional
from pydantic import Field


def register_tools(mcp: FastMCP):
    """Register project management tools with the MCP server."""

    @mcp.tool()
    async def create_project(
        domain_identifier: str = Field(description="The ID of the domain where the project will be created"),
        name: str = Field(description="The name of the project"),
        description: str = Field(default='', description="The description of the project"),
        domain_unit_id: Optional[str] = Field(default=None, description="The ID of the domain unit where the project will be created"),
        glossary_terms: Optional[List[str]] = Field(default=None, description="List of glossary terms that can be used in the project"),
        project_profile_id: Optional[str] = Field(default=None, description="The ID of the project profile"),
        user_parameters: Optional[List[Dict[str, Any]]] = Field(default=None, description="The user parameters of the project"),
    ) -> Any:
        """Creates a new project in an Amazon DataZone domain.

        Args:
            domain_identifier (str): The ID of the domain where the project will be created
            name (str): The name of the project (required)
            description (str, optional): The description of the project
            domain_unit_id (str, optional): The ID of the domain unit where the project will be created
            glossary_terms (List[str], optional): List of glossary terms that can be used in the project
            project_profile_id (str, optional): The ID of the project profile
            user_parameters (List[Dict[str, Any]], optional): The user parameters of the project

        Returns:
            Any: The API response containing the created project details
        """
        try:
            # Prepare the request parameters
            params: Dict[str, Any] = {'name': name, 'description': description}

            # Add optional parameters if provided
            if domain_unit_id:  # pragma: no cover
                params['domainUnitId'] = domain_unit_id
            if glossary_terms:  # pragma: no cover
                params['glossaryTerms'] = glossary_terms
            if project_profile_id:  # pragma: no cover
                params['projectProfileId'] = project_profile_id
            if user_parameters:  # pragma: no cover
                params['userParameters'] = user_parameters

            response = datazone_client.create_project(domainIdentifier=domain_identifier, **params)
            return response
        except ClientError as e:  # pragma: no cover
            raise Exception(f'Error creating project in domain {domain_identifier}: {e}')

    @mcp.tool()
    async def get_project(
        domain_identifier: str = Field(description="The ID of the domain where the project exists"),
        project_identifier: str = Field(description="The ID of the project to retrieve")
    ) -> Any:
        """Retrieves detailed information, metadata and configuration, of a specific project in Amazon DataZone.

        Use this API when the user is asking about a **known project by name or context** and wants to:
        - View deployment status, user roles, or configurations
        - Audit metadata for compliance or review

        Returns:
            Any: The API response containing project details including:
                - Basic info (name, description, ID)
                - Timestamps (createdAt, lastUpdatedAt)
                - Domain IDs (domainId, domainUnitId)
                - Project status and profile
                - Environment deployment details
                - User parameters
                - Glossary terms
                - Failure reasons (if any)
        """
        try:
            response = datazone_client.get_project(
                domainIdentifier=domain_identifier, identifier=project_identifier
            )
            return response
        except ClientError as e:  # pragma: no cover
            raise Exception(
                f'Error getting project {project_identifier} in domain {domain_identifier}: {e}'
            )

    @mcp.tool()
    async def list_projects(
        domain_identifier: str = Field(description="The identifier of the domain"),
        max_results: int = Field(default=50, description="Maximum number of projects to return (1-50)"),
        next_token: Optional[str] = Field(default=None, description="Token for pagination"),
        name: Optional[str] = Field(default=None, description="Filter projects by name"),
        user_identifier: Optional[str] = Field(default=None, description="Filter projects by user"),
        group_identifier: Optional[str] = Field(default=None, description="Filter projects by group"),
    ) -> Any:
        """Lists projects in an Amazon DataZone domain with optional filtering and pagination.

        Args:
            domain_identifier (str): The identifier of the domain
            max_results (int, optional): Maximum number of projects to return (1-50, default: 50)
            next_token (str, optional): Token for pagination
            name (str, optional): Filter projects by name
            user_identifier (str, optional): Filter projects by user
            group_identifier (str, optional): Filter projects by group

        Returns:
            Any: The API response containing the list of projects
        """
        try:
            # Prepare the request parameters
            params = {
                'domainIdentifier': domain_identifier,
                'maxResults': min(max_results, 50),  # Ensure maxResults is within valid range
            }

            # Add optional parameters if provided
            if next_token:  # pragma: no cover
                params['nextToken'] = next_token
            if name:  # pragma: no cover
                params['name'] = name
            if user_identifier:  # pragma: no cover
                params['userIdentifier'] = user_identifier
            if group_identifier:  # pragma: no cover
                params['groupIdentifier'] = group_identifier

            response = datazone_client.list_projects(**params)
            return response
        except ClientError as e:  # pragma: no cover
            raise Exception(f'Error listing projects in domain {domain_identifier}: {e}')

    @mcp.tool()
    async def create_project_membership(
        domainIdentifier: str = Field(description="The identifier of the domain"),
        projectIdentifier: str = Field(description="The identifier of the project"),
        designation: str = Field(description="The designation of the member"),
        memberIdentifier: str = Field(description="The identifier of the member")
    ) -> Any:
        """Make a request to the Amazon DataZone CreateProjectMembership API.

        Args:
            domainIdentifier (str): The identifier of the domain.
            projectIdentifier (str): The identifier of the project.
            designation (str): The designation of the member.
            memberIdentifier (str): The identifier of the member.
        """
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'application/json',
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f'https://{domainIdentifier}.datazone.aws.dev/v2/domains/{domainIdentifier}/projects/{projectIdentifier}/createMembership',
                    headers=headers,
                    json={'designation': designation, 'member': {'identifier': memberIdentifier}},
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:  # pragma: no cover
                raise Exception(f'Failed to create project membership: {e}')

    @mcp.tool()
    async def list_project_profiles(
        domain_identifier: str = Field(description="The ID of the domain"),
        max_results: int = Field(default=50, description="Maximum number of profiles to return (1-50)"),
        next_token: Optional[str] = Field(default=None, description="Token for pagination")
    ) -> Any:
        """Lists all project profiles available in an Amazon DataZone domain.

        Args:
            domain_identifier (str): The ID of the domain
            max_results (int, optional): Maximum number of profiles to return (1-50, default: 50)
            next_token (str, optional): Token for pagination

        Returns:
            Any: The API response containing the list of project profiles
        """
        try:
            # Prepare the request parameters
            params = {
                'domainIdentifier': domain_identifier,
                'maxResults': min(max_results, 50),  # Ensure maxResults is within valid range
            }

            # Add optional next token if provided
            if next_token:  # pragma: no cover
                params['nextToken'] = next_token

            response = datazone_client.list_project_profiles(**params)
            return response
        except ClientError as e:  # pragma: no cover
            raise Exception(f'Error listing project profiles in domain {domain_identifier}: {e}')

    @mcp.tool()
    async def create_project_profile(
        domain_identifier: str = Field(description="The ID of the domain where the project profile will be created"),
        name: str = Field(description="The name of the project profile (1-64 characters)"),
        description: Optional[str] = Field(default=None, description="Description of the project profile (0-2048 characters)"),
        domain_unit_identifier: Optional[str] = Field(default=None, description="The ID of the domain unit where the project profile will be created"),
        environment_configurations: Optional[List[Dict[str, Any]]] = Field(default=None, description="Environment configurations for the project profile"),
        status: str = Field(default='ENABLED', description="The status of the project profile (ENABLED or DISABLED)"),
    ) -> Dict[str, Any]:
        r"""Creates a new project profile in Amazon DataZone.

        Args:
            domain_identifier (str): The ID of the domain where the project profile will be created
                Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
            name (str): The name of the project profile (1-64 characters)
                Pattern: ^[\\w -]+$
            description (str, optional): Description of the project profile (0-2048 characters)
            domain_unit_identifier (str, optional): The ID of the domain unit where the project profile will be created
                Pattern: ^[a-z0-9_-]+$
            environment_configurations (List[Dict[str, Any]], optional): Environment configurations for the project profile
                Each configuration should include:
                    - awsAccount: AWS account details
                    - awsRegion: AWS region details
                    - configurationParameters: Configuration parameters
                    - deploymentMode: Deployment mode
                    - deploymentOrder: Deployment order
                    - description: Environment description
                    - environmentBlueprintId: Environment blueprint ID
                    - id: Environment ID
                    - name: Environment name
            status (str, optional): The status of the project profile (ENABLED or DISABLED, default: ENABLED)

        Returns:
            Dict containing:
                - id: Project profile identifier
                - name: Project profile name
                - description: Project profile description
                - domain_id: Domain ID
                - domain_unit_id: Domain unit ID
                - environment_configurations: Environment configurations
                - status: Project profile status
                - created_at: Creation timestamp
                - created_by: Creator information
                - last_updated_at: Last update timestamp
        """
        try:
            logger.info(f"Creating project profile '{name}' in domain {domain_identifier}")

            # Prepare request parameters
            params: Dict[str, Any] = {
                'domainIdentifier': domain_identifier,
                'name': name,
                'status': status,
            }

            # Add optional parameters
            if description:  # pragma: no cover
                params['description'] = description
            if domain_unit_identifier:  # pragma: no cover
                params['domainUnitIdentifier'] = domain_unit_identifier
            if environment_configurations:  # pragma: no cover
                params['environmentConfigurations'] = environment_configurations

            # Create the project profile
            response = datazone_client.create_project_profile(**params)

            # Format the response
            result = {
                'id': response.get('id'),
                'name': response.get('name'),
                'description': response.get('description'),
                'domain_id': response.get('domainId'),
                'domain_unit_id': response.get('domainUnitId'),
                'environment_configurations': response.get('environmentConfigurations', []),
                'status': response.get('status'),
                'created_at': response.get('createdAt'),
                'created_by': response.get('createdBy'),
                'last_updated_at': response.get('lastUpdatedAt'),
            }

            logger.info(
                f"Successfully created project profile '{name}' in domain {domain_identifier}"
            )
            return result

        except ClientError as e:  # pragma: no cover
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDeniedException':  # pragma: no cover
                logger.error(
                    f"Access denied while creating project profile '{name}' in domain {domain_identifier}"
                )
                raise Exception(
                    f"Access denied while creating project profile '{name}' in domain {domain_identifier}"
                )
            elif error_code == 'ConflictException':  # pragma: no cover
                logger.error(
                    f"Project profile '{name}' already exists in domain {domain_identifier}"
                )
                raise Exception(
                    f"Project profile '{name}' already exists in domain {domain_identifier}"
                )
            elif error_code == 'ResourceNotFoundException':  # pragma: no cover
                logger.error(
                    f"Domain or domain unit not found while creating project profile '{name}' in domain {domain_identifier}"
                )
                raise Exception(
                    f"Domain or domain unit not found while creating project profile '{name}' in domain {domain_identifier}"
                )
            elif error_code == 'ServiceQuotaExceededException':  # pragma: no cover
                logger.error(
                    f"Service quota exceeded while creating project profile '{name}' in domain {domain_identifier}"
                )
                raise Exception(
                    f"Service quota exceeded while creating project profile '{name}' in domain {domain_identifier}"
                )
            elif error_code == 'ValidationException':  # pragma: no cover
                logger.error(
                    f"Invalid parameters for creating project profile '{name}' in domain {domain_identifier}"
                )
                raise Exception(
                    f"Invalid parameters for creating project profile '{name}' in domain {domain_identifier}"
                )
            else:  # pragma: no cover
                logger.error(
                    f"Error creating project profile '{name}' in domain {domain_identifier}: {str(e)}"
                )
                raise Exception(
                    f"Error creating project profile '{name}' in domain {domain_identifier}: {str(e)}"
                )
        except Exception as e:  # pragma: no cover
            logger.error(
                f"Unexpected error creating project profile '{name}' in domain {domain_identifier}: {str(e)}"
            )
            raise Exception(
                f"Unexpected error creating project profile '{name}' in domain {domain_identifier}: {str(e)}"
            )

    @mcp.tool()
    async def get_project_profile(
        domain_identifier: str = Field(description="The ID of the domain"),
        identifier: str = Field(description="The ID of the project profile")
    ) -> Any:
        r"""Get the details of the project profile in an Amazon DataZone domain.

        Args:
            domain_identifier (str): The ID of the domain
                Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
            identifier (str): The ID of the project profile (1-50, default: 50)
                Pattern: ^[a-zA-Z0-9_-]{1,36}$

        Returns:
            dict: A dictionary with the following fields:
                createdAt (str): The timestamp when the project profile was created.
                createdBy (str): The user who created the project profile.
                description (str): Description of the project profile. (0–2048 characters)
                domainId (str): The identifier of the domain the project profile belongs to.
                    Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
                domainUnitId (str): The identifier of the domain unit within the domain.
                    Pattern: r"^[a-z0-9_\-]+$", length 1–256
                environmentConfigurations (List[dict]): A list of environment configurations. Each item includes:
                    - awsAccount (dict): AWS account details.
                    - awsRegion (dict): AWS region.
                    - configurationParameters (dict): Parameters for deployment.
                        - parameterOverrides (List[dict]): Overridden parameters with:
                            - isEditable (bool): Whether the parameter can be edited.
                            - name (str): Parameter name.
                            - value (str): Parameter value.
                        - resolvedParameters (List[dict]): Final resolved parameters, same structure as above.
                        - ssmPath (str): SSM path for configuration parameters.
                    - deploymentMode (str): Mode of deployment.
                    - deploymentOrder (int): Order in which to deploy this environment.
                    - description (str): Description of the environment configuration.
                    - environmentBlueprintId (str): Identifier of the environment blueprint.
                    - id (str): Unique ID of the environment configuration.
                    - name (str): Name of the environment configuration.
                id (str): Unique identifier for the project profile.
                    Pattern: ^[a-zA-Z0-9_-]{1,36}$
                lastUpdatedAt (str): The timestamp when the project profile was last updated.
                name (str): The name of the project profile (1–64 characters).
                    Pattern: ^[\w -]+$
                status (str): Status of the project profile. Valid values: "ENABLED" | "DISABLED"
        """
        try:
            # Prepare the request parameters
            params = {'domainIdentifier': domain_identifier, 'identifier': identifier}

            response = datazone_client.get_project_profile(**params)
            return response
        except ClientError as e:  # pragma: no cover
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDeniedException':  # pragma: no cover
                logger.error(
                    f"Access denied while getting project profile '{identifier}' in domain {domain_identifier}"
                )
                raise Exception(
                    f"Access denied while getting project profile '{identifier}' in domain {domain_identifier}"
                )
            elif error_code == 'ResourceNotFoundException':  # pragma: no cover
                logger.error('Domain or project profile not found')
                raise Exception('Domain or project profile not found')
            elif error_code == 'InternalServerException':  # pragma: no cover
                logger.error(
                    f"Getting project profile '{identifier}' in domain {domain_identifier} failed because of an unknown error, exception or failure"
                )
                raise Exception(
                    f"Getting project profile '{identifier}' in domain {domain_identifier} failed because of an unknown error, exception or failure"
                )
            elif error_code == 'ValidationException':  # pragma: no cover
                logger.error(
                    f"Invalid parameters for getting project profile '{identifier}' in domain {domain_identifier}"
                )
                raise Exception(
                    f"Invalid parameters for getting project profile '{identifier}' in domain {domain_identifier}"
                )
            elif error_code == 'UnauthorizedException':  # pragma: no cover
                logger.error(
                    f"You do not have permission to get project profile '{identifier}' in domain {domain_identifier}"
                )
                raise Exception(
                    f"You do not have permission to get project profile '{identifier}' in domain {domain_identifier}"
                )
            elif error_code == 'ThrottlingException':  # pragma: no cover
                logger.error(
                    f"Request to get project profile '{identifier}' in domain {domain_identifier} is denied due to request throttling"
                )
                raise Exception(
                    f"Request to get project profile '{identifier}' in domain {domain_identifier} is denied due to request throttling"
                )
            else:  # pragma: no cover
                logger.error(
                    f"Error creating project profile '{identifier}' in domain {domain_identifier}: {str(e)}"
                )
                raise Exception(
                    f"Error creating project profile '{identifier}' in domain {domain_identifier}: {str(e)}"
                )
        except Exception as e:  # pragma: no cover
            logger.error(
                f"Unexpected error creating project profile '{identifier}' in domain {domain_identifier}: {str(e)}"
            )
            raise Exception(
                f"Unexpected error creating project profile '{identifier}' in domain {domain_identifier}: {str(e)}"
            )

    @mcp.tool()
    async def list_project_memberships(
        domain_identifier: str = Field(description="The identifier of the Amazon DataZone domain"),
        project_identifier: str = Field(description="The identifier of the project whose memberships you want to list"),
        max_results: int = Field(default=50, description="The maximum number of memberships to return in a single call (1-50)"),
        next_token: Optional[str] = Field(default=None, description="A token for pagination"),
        sort_by: Optional[str] = Field(default=None, description="The attribute by which to sort the memberships (NAME)"),
        sort_order: Optional[str] = Field(default=None, description="The sort order for the results (ASCENDING or DESCENDING)"),
    ) -> Any:
        """Lists the memberships of a specified Amazon DataZone project within a domain.

        Args:
            domain_identifier (str): The identifier of the Amazon DataZone domain.
                Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
                Required: Yes

            project_identifier (str): The identifier of the project whose memberships you want to list.
                Pattern: ^[a-zA-Z0-9_-]{1,36}$
                Required: Yes

            max_results (int, optional): The maximum number of memberships to return in a single call (1–50).

            next_token (str, optional): A token for pagination. Use this token from a previous response to retrieve the next set of memberships.
                Length: 1–8192 characters

            sort_by (str, optional): The attribute by which to sort the memberships.
                Valid Values: "NAME"

            sort_order (str, optional): The sort order for the results.
                Valid Values: "ASCENDING" | "DESCENDING"

        Returns:
            dict: A dictionary containing:
                - members (List[dict]): A list of project members, where each member includes:
                    - designation (str): The role or designation of the member within the project.
                    - memberDetails (dict): Additional details about the member (structure depends on implementation).

                - nextToken (str, optional): A token to retrieve the next page of results if more memberships exist.
                    Length: 1–8192 characters
        """
        try:
            # Prepare the request parameters
            params = {
                'domainIdentifier': domain_identifier,
                'projectIdentifier': project_identifier,
                'maxResults': min(max_results, 50),  # Ensure maxResults is within valid range
            }

            # Add optional next token if provided
            if next_token:  # pragma: no cover
                params['nextToken'] = next_token
            if sort_by:  # pragma: no cover
                params['sortBy'] = sort_by
            if sort_order:  # pragma: no cover
                params['sortOrder'] = sort_order

            response = datazone_client.list_project_memberships(**params)
            return response
        except ClientError as e:  # pragma: no cover
            raise Exception(
                f'Error listing project {project_identifier} memberships in domain {domain_identifier}: {e}'
            )

    # Return the decorated functions for testing purposes
    return {
        'create_project': create_project,
        'get_project': get_project,
        'list_projects': list_projects,
        'create_project_membership': create_project_membership,
        'list_project_profiles': list_project_profiles,
        'create_project_profile': create_project_profile,
        'get_project_profile': get_project_profile,
        'list_project_memberships': list_project_memberships,
    }
