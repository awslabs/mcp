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
"""Environment management tools for Amazon DataZone."""

from .common import ClientError, _get_param_value, datazone_client, logger
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Any, Dict, Optional


def register_tools(mcp: FastMCP):
    """Register environment management tools with the MCP server."""

    @mcp.tool()
    async def list_environments(
        domain_identifier: str = Field(
            ..., description='The identifier of the Amazon DataZone domain'
        ),
        project_identifier: str = Field(
            ..., description='The identifier of the Amazon DataZone project'
        ),
        max_results: int = Field(default=50, description='Maximum number of environments to return'),
        next_token: Optional[str] = Field(default=None, description='Token for pagination'),
        aws_account_id: Optional[str] = Field(
            default=None, description='The identifier of the AWS account where you want to list environments'
        ),
        aws_account_region: Optional[str] = Field(
            default=None, description='The AWS region where you want to list environments'
        ),
        environment_blueprint_identifier: Optional[str] = Field(
            default=None, description='The identifier of the Amazon DataZone blueprint'
        ),
        environment_profile_identifier: Optional[str] = Field(
            default=None, description='The identifier of the environment profile'
        ),
        name: Optional[str] = Field(default=None, description='The name of the environment'),
        provider: Optional[str] = Field(default=None, description='The provider of the environment'),
        status: Optional[str] = Field(default=None, description='The status of the environments to list'),
    ) -> Any:
        """Lists environments in Amazon DataZone.

        Args:
            domain_identifier (str): The identifier of the Amazon DataZone domain.
            project_identifier (str): The identifier of the Amazon DataZone project.
            max_results (int, optional): Maximum number of environments to return. Defaults to 50.
            next_token (str, optional): Token for pagination. Defaults to None.
            aws_account_id (str, optional): The identifier of the AWS account where you want to list environments.
            aws_account_region (str, optional): The AWS region where you want to list environments.
            environment_blueprint_identifier (str, optional): The identifier of the Amazon DataZone blueprint.
            environment_profile_identifier (str, optional): The identifier of the environment profile.
            name (str, optional): The name of the environment.
            provider (str, optional): The provider of the environment.
            status (str, optional): The status of the environments to list.
                Valid values: ACTIVE, CREATING, UPDATING, DELETING, CREATE_FAILED, UPDATE_FAILED,
                DELETE_FAILED, VALIDATION_FAILED, SUSPENDED, DISABLED, EXPIRED, DELETED, INACCESSIBLE

        Returns:
            Any: The API response containing environment details or None if an error occurs

        Example:
            >>> list_environments(
            ...     domain_identifier='dzd_4p9n6sw4qt9xgn',
            ...     project_identifier='prj_123456789',
            ...     status='ACTIVE',
            ... )
        """
        try:
            # Handle optional parameters
            max_results_value = _get_param_value(max_results)
            next_token_value = _get_param_value(next_token)
            aws_account_id_value = _get_param_value(aws_account_id)
            aws_account_region_value = _get_param_value(aws_account_region)
            environment_blueprint_identifier_value = _get_param_value(environment_blueprint_identifier)
            environment_profile_identifier_value = _get_param_value(environment_profile_identifier)
            name_value = _get_param_value(name)
            provider_value = _get_param_value(provider)
            status_value = _get_param_value(status)

            params = {
                'domainIdentifier': domain_identifier,
                'projectIdentifier': project_identifier,
                'maxResults': max_results_value,
            }

            # Add optional parameters if provided
            if next_token_value:  # pragma: no cover
                params['nextToken'] = next_token_value
            if aws_account_id_value:  # pragma: no cover
                params['awsAccountId'] = aws_account_id_value
            if aws_account_region_value:  # pragma: no cover
                params['awsAccountRegion'] = aws_account_region_value
            if environment_blueprint_identifier_value:  # pragma: no cover
                params['environmentBlueprintIdentifier'] = environment_blueprint_identifier_value
            if environment_profile_identifier_value:  # pragma: no cover
                params['environmentProfileIdentifier'] = environment_profile_identifier_value
            if name_value:  # pragma: no cover
                params['name'] = name_value
            if provider_value:  # pragma: no cover
                params['provider'] = provider_value
            if status_value:  # pragma: no cover
                params['status'] = status_value

            response = datazone_client.list_environments(**params)
            return response
        except ClientError as e:  # pragma: no cover
            raise Exception(f'Error listing environments: {e}')

    @mcp.tool()
    async def create_connection(
        domain_identifier: str = Field(
            ..., description='The ID of the domain where the connection is created'
        ),
        name: str = Field(..., description='The connection name (0-64 characters)'),
        environment_identifier: Optional[str] = Field(
            default=None, description='The ID of the environment where the connection is created'
        ),
        aws_location: Optional[Dict[str, str]] = Field(
            default=None, description='The location where the connection is created'
        ),
        description: Optional[str] = Field(
            default=None, description='A connection description (0-128 characters)'
        ),
        client_token: Optional[str] = Field(
            default=None, description='A unique, case-sensitive identifier to ensure idempotency'
        ),
        props: Optional[Dict[str, Any]] = Field(default=None, description='The connection properties'),
    ) -> Any:
        """Creates a new connection in Amazon DataZone. A connection enables you to connect your resources.

        (domains, projects, and environments) to external resources and services.

        This is specifically for creating DataZone connections and should be used in the DataZone MCP server.

        Args:
            domain_identifier (str): The ID of the domain where the connection is created.
                Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
            name (str): The connection name.
                Length Constraints: Minimum length of 0. Maximum length of 64.
            environment_identifier (str, optional): The ID of the environment where the connection is created.
                Pattern: ^[a-zA-Z0-9_-]{1,36}$
            aws_location (Dict[str, str], optional): The location where the connection is created.
                Contains:
                    - accessRole (str): The access role for the connection
                    - awsAccountId (str): The AWS account ID
                    - awsRegion (str): The AWS region
                    - iamConnectionId (str): The IAM connection ID
            description (str, optional): A connection description.
                Length Constraints: Minimum length of 0. Maximum length of 128.
            client_token (str, optional): A unique, case-sensitive identifier to ensure idempotency.
            props (Dict[str, Any], optional): The connection properties.
                Type: ConnectionPropertiesInput object (Union type)

        Returns:
            Any: The API response containing:
                - connectionId (str): The ID of the created connection
                - description (str): The connection description
                - domainId (str): The domain ID
                - domainUnitId (str): The domain unit ID
                - environmentId (str): The environment ID
                - name (str): The connection name
                - physicalEndpoints (list): The physical endpoints of the connection
                - projectId (str): The project ID
                - props (dict): The connection properties
                - type (str): The connection type

        Example:
            >>> create_connection(
            ...     domain_identifier='dzd_4p9n6sw4qt9xgn',
            ...     name='MyConnection',
            ...     environment_identifier='env_123456789',
            ...     aws_location={
            ...         'accessRole': 'arn:aws:iam::123456789012:role/DataZoneAccessRole',
            ...         'awsAccountId': '123456789012',
            ...         'awsRegion': 'us-east-1',
            ...         'iamConnectionId': 'iam-123456789',
            ...     },
            ...     description='Connection to external service',
            ... )
        """
        try:
            # Handle optional parameters
            environment_identifier_value = _get_param_value(environment_identifier)
            aws_location_value = _get_param_value(aws_location)
            description_value = _get_param_value(description)
            client_token_value = _get_param_value(client_token)
            props_value = _get_param_value(props)

            # Prepare the request parameters
            params: Dict[str, Any] = {'domainIdentifier': domain_identifier, 'name': name}

            # Add optional parameters if provided
            if environment_identifier_value:  # pragma: no cover
                params['environmentIdentifier'] = environment_identifier_value
            if aws_location_value:  # pragma: no cover
                params['awsLocation'] = aws_location_value
            if description_value:  # pragma: no cover
                params['description'] = description_value
            if client_token_value:  # pragma: no cover
                params['clientToken'] = client_token_value
            if props_value:  # pragma: no cover
                params['props'] = props_value

            response = datazone_client.create_connection(**params)
            return response
        except ClientError as e:  # pragma: no cover
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']

            if error_code == 'AccessDeniedException':  # pragma: no cover
                raise Exception(
                    f'Access denied while creating connection in domain {domain_identifier}: {error_message}'
                )
            elif error_code == 'ConflictException':  # pragma: no cover
                raise Exception(
                    f'Conflict while creating connection in domain {domain_identifier}: {error_message}'
                )
            elif error_code == 'ResourceNotFoundException':  # pragma: no cover
                raise Exception(
                    f'Resource not found while creating connection in domain {domain_identifier}: {error_message}'
                )
            elif error_code == 'ServiceQuotaExceededException':  # pragma: no cover
                raise Exception(
                    f'Service quota exceeded while creating connection in domain {domain_identifier}: {error_message}'
                )
            elif error_code == 'ValidationException':  # pragma: no cover
                raise Exception(
                    f'Invalid parameters while creating connection in domain {domain_identifier}: {error_message}'
                )
            else:  # pragma: no cover
                raise Exception(
                    f'Unexpected error creating connection in domain {domain_identifier}: {error_message}'
                )

    @mcp.tool()
    async def get_connection(
        domain_identifier: str = Field(
            ..., description='The ID of the domain containing the connection'
        ),
        identifier: str = Field(..., description='The ID of the connection to retrieve'),
        with_secret: bool = Field(
            default=False, description='Whether to include secret information in the response'
        )
    ) -> Any:
        """Gets a connection in Amazon DataZone. A connection enables you to connect your resources.

        (domains, projects, and environments) to external resources and services.

        Connections are credentials + config for accessing a system, while data source is a specific location where your data resides using a connection.

        related tools:
        - get_data_source: get detailed information about one specific data source (a data locatin)

        Args:
            domain_identifier (str): The ID of the domain where the connection exists.
                Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
            identifier (str): The ID of the connection to retrieve.
                Length Constraints: Minimum length of 0. Maximum length of 128.
            with_secret (bool, optional): Specifies whether to include connection secrets.
                Defaults to False.

        Returns:
            Any: The API response containing:
                - connectionId (str): The ID of the connection
                - description (str): The connection description
                - domainId (str): The domain ID
                - domainUnitId (str): The domain unit ID
                - environmentId (str): The environment ID
                - environmentUserRole (str): The environment user role
                - name (str): The connection name
                - physicalEndpoints (list): The physical endpoints of the connection
                - projectId (str): The project ID
                - props (dict): The connection properties
                - type (str): The connection type
                - connectionCredentials (dict, optional): If with_secret is True, includes:
                    - accessKeyId (str)
                    - expiration (str)
                    - secretAccessKey (str)
                    - sessionToken (str)

        Example:
            >>> get_connection(
            ...     domain_identifier='dzd_4p9n6sw4qt9xgn',
            ...     identifier='conn_123456789',
            ...     with_secret=True,
            ... )
        """
        try:
            # Prepare the request parameters
            params: Dict[str, Any] = {
                'domainIdentifier': domain_identifier,
                'identifier': identifier,
            }
            with_secret_value = _get_param_value(with_secret)
            # Add with_secret parameter if True
            if with_secret_value:  # pragma: no cover
                params['withSecret'] = with_secret_value

            response = datazone_client.get_connection(**params)
            return response
        except ClientError as e:  # pragma: no cover
            error_code = e.response.get('Error', {}).get('Code', '')
            error_message = e.response.get('Error', {}).get('Message', str(e))

            if error_code == 'AccessDeniedException':  # pragma: no cover
                raise Exception(
                    f'Access denied while getting connection {identifier} in domain {domain_identifier}: {error_message}'
                )
            elif error_code == 'ResourceNotFoundException':  # pragma: no cover
                raise Exception(
                    f'Connection {identifier} not found in domain {domain_identifier}: {error_message}'
                )
            elif error_code == 'ValidationException':  # pragma: no cover
                raise Exception(
                    f'Invalid parameters while getting connection {identifier} in domain {domain_identifier}: {error_message}'
                )
            else:  # pragma: no cover
                raise Exception(
                    f'Error getting connection {identifier} in domain {domain_identifier}: {error_message}'
                )

    @mcp.tool()
    async def get_environment(
        domain_identifier: str = Field(
            ..., description='The ID of the domain containing the environment'
        ),
        identifier: str = Field(..., description='The ID of the environment to retrieve')
    ) -> Any:
        """Gets an Amazon DataZone environment.

        Args:
            domain_identifier (str): The ID of the domain where the environment exists.
                Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
            identifier (str): The ID of the environment to retrieve.
                Length Constraints: Minimum length of 0. Maximum length of 128.

        Returns:
            Any: The API response containing:
                - awsAccountId (str): The AWS account ID associated with the environment.
                - awsAccountRegion (str): The AWS region where the environment is located.
                - createdAt (str): Timestamp when the environment was created.
                - createdBy (str): The identifier of the user who created the environment.
                - deploymentProperties (dict): Properties related to deployment, including:
                    - endTimeoutMinutes (int): Timeout in minutes for ending the deployment.
                    - startTimeoutMinutes (int): Timeout in minutes for starting the deployment.
                - description (str): Description of the environment.
                - domainId (str): The domain ID associated with the environment.
                - environmentActions (list): A list of actions for the environment, each containing:
                    - auth (str): Authorization type for the action.
                    - parameters (list): Parameters for the action, each including:
                        - key (str): Parameter key.
                        - value (str): Parameter value.
                    - type (str): The type of environment action.
                - environmentBlueprintId (str): ID of the blueprint used for the environment.
                - environmentConfigurationId (str): ID of the environment configuration.
                - environmentProfileId (str): ID of the environment profile.
                - glossaryTerms (list): List of glossary term strings associated with the environment.
                - id (str): The unique ID of the environment.
                - lastDeployment (dict): Information about the last deployment, including:
                    - deploymentId (str): ID of the last deployment.
                    - deploymentStatus (str): Status of the deployment.
                    - deploymentType (str): Type of deployment.
                    - failureReason (dict): Details of any failure, including:
                        - code (str): Error code for the failure.
                        - message (str): Human-readable error message.
                    - isDeploymentComplete (bool): Whether the deployment is complete.
                    - messages (list): List of messages related to the deployment.
                - name (str): Name of the environment.
                - projectId (str): The project ID associated with the environment.
                - provider (str): Provider responsible for provisioning the environment.
                - provisionedResources (list): List of provisioned resources, each including:
                    - name (str): Name of the resource.
                    - provider (str): Resource provider.
                    - type (str): Type of the resource.
                    - value (str): Value associated with the resource.
                - provisioningProperties (dict): Additional properties used during provisioning.
                - status (str): Current status of the environment.
                - updatedAt (str): Timestamp when the environment was last updated.
                - userParameters (list): Parameters provided by the user, each including:
                    - defaultValue (str): Default value of the parameter.
                    - description (str): Description of the parameter.
                    - fieldType (str): Type of input field.
                    - isEditable (bool): Whether the parameter is editable.
                    - isOptional (bool): Whether the parameter is optional.
                    - keyName (str): Key name for the parameter.

        Example:
            >>> get_environment(
            ...     domain_identifier='dzd_4p9n6sw4qt9xgn', identifier='conn_123456789'
            ... )
        """
        try:
            # Prepare the request parameters
            params = {'domainIdentifier': domain_identifier, 'identifier': identifier}

            response = datazone_client.get_environment(**params)
            return response
        except ClientError as e:  # pragma: no cover
            error_code = e.response.get('Error', {}).get('Code', '')
            error_message = e.response.get('Error', {}).get('Message', str(e))

            if error_code == 'AccessDeniedException':  # pragma: no cover
                raise Exception(
                    f'Access denied while getting environment {identifier} in domain {domain_identifier}: {error_message}'
                )
            elif error_code == 'ResourceNotFoundException':  # pragma: no cover
                raise Exception(
                    f'Environment {identifier} not found in domain {domain_identifier}: {error_message}'
                )
            elif error_code == 'ValidationException':  # pragma: no cover
                raise Exception(
                    f'Invalid parameters while getting environment {identifier} in domain {domain_identifier}: {error_message}'
                )
            else:  # pragma: no cover
                raise Exception(
                    f'Error getting environment {identifier} in domain {domain_identifier}: {error_message}'
                )

    @mcp.tool()
    async def get_environment_blueprint(
        domain_identifier: str = Field(
            ..., description='The ID of the domain containing the environment blueprint'
        ),
        identifier: str = Field(..., description='The ID of the environment blueprint to retrieve')
    ) -> Any:
        r"""Retrieves metadata and definition of an environment blueprint.

        related tools:
        - get_environment_blueprint_configuration: Retrieves the configuration schema and parameters that must be provided when provisioning an environment from a given blueprint.

        Args:
            domain_identifier (str): The ID of the domain in which this blueprint exists.
                Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
            identifier (str): The ID of the environment to retrieve.
                Length Constraints: Minimum length of 0. Maximum length of 128.

        Returns:
            Any: The API response containing the Amazon DataZone blueprint metadata:

                - createdAt (str): Timestamp indicating when the blueprint was created.
                - deploymentProperties (dict): Deployment-related configuration, including:
                    - endTimeoutMinutes (int): Timeout in minutes for ending deployment.
                    - startTimeoutMinutes (int): Timeout in minutes for starting deployment.
                - description (str): A description of the blueprint.
                    - Constraints: 0–2048 characters.
                - glossaryTerms (list of str): Glossary terms associated with the blueprint.
                    - Constraints: 1–20 items.
                    - Pattern: ^[a-zA-Z0-9_-]{1,36}$
                - id (str): Unique ID of the blueprint.
                    - Pattern: ^[a-zA-Z0-9_-]{1,36}$
                - name (str): Name of the blueprint.
                    - Constraints: 1–64 characters.
                    - Pattern: r"^[\w -]+$"
                - provider (str): The provider of the blueprint.
                - provisioningProperties (dict): Provisioning configuration for the blueprint.
                    - Note: This is a union object—only one configuration type may be present.
                - updatedAt (str): Timestamp indicating when the blueprint was last updated.
                - userParameters (list of dict): Custom parameters defined by the user, each including:
                    - defaultValue (str): Default value for the parameter.
                    - description (str): Description of the parameter.
                    - fieldType (str): Type of input field (e.g., string, boolean).
                    - isEditable (bool): Whether the parameter is user-editable.
                    - isOptional (bool): Whether the parameter is optional.
                    - keyName (str): Key name for the parameter.
        """
        try:
            # Prepare the request parameters
            params = {'domainIdentifier': domain_identifier, 'identifier': identifier}

            response = datazone_client.get_environment_blueprint(**params)
            return response
        except ClientError as e:  # pragma: no cover
            error_code = e.response.get('Error', {}).get('Code', '')
            error_message = e.response.get('Error', {}).get('Message', str(e))

            if error_code == 'AccessDeniedException':  # pragma: no cover
                raise Exception(
                    f'Access denied while getting environment {identifier} blueprint in domain {domain_identifier}: {error_message}'
                )
            elif error_code == 'ResourceNotFoundException':  # pragma: no cover
                raise Exception(
                    f'Environment {identifier} not found in domain {domain_identifier}: {error_message}'
                )
            elif error_code == 'ValidationException':  # pragma: no cover
                raise Exception(
                    f'Invalid parameters while getting environment {identifier} blueprint in domain {domain_identifier}: {error_message}'
                )
            else:  # pragma: no cover
                raise Exception(
                    f'Error getting environment {identifier} blueprint in domain {domain_identifier}: {error_message}'
                )

    @mcp.tool()
    async def get_environment_blueprint_configuration(
        domain_identifier: str = Field(
            ..., description='The ID of the domain containing the environment blueprint configuration'
        ),
        identifier: str = Field(
            ..., description='The ID of the environment blueprint configuration to retrieve'
        )
    ) -> Any:
        r"""Gets an Amazon DataZone environment blueprint configuration.

        Retrieves the configuration schema and parameters that must be provided when provisioning an environment from a given blueprint.

        Args:
            domain_identifier (str): The ID of the domain where where this blueprint exists.
                Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
            identifier (str): The ID of the environment blueprint.
                Pattern: ^[a-zA-Z0-9_-]{1,36}$

        Returns:
            Any: The API response containing information about the Amazon DataZone environment blueprint configuration:

                - createdAt (str): Timestamp indicating when the blueprint was created.
                - domainId (str): ID of the DataZone domain associated with the blueprint.
                    - Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
                - enabledRegions (list of str): List of AWS regions where the blueprint is enabled.
                    - Each region string must follow the pattern: ^[a-z]{2}-?(iso|gov)?-{1}[a-z]*-{1}[0-9]$
                    - Length constraints: 4–16 characters.
                - environmentBlueprintId (str): Unique ID of the blueprint.
                    - Pattern: ^[a-zA-Z0-9_-]{1,36}$
                - environmentRolePermissionBoundary (str): ARN of the IAM policy that defines the permission boundary for environment roles.
                    - Pattern: r"^arn:aws[^:]*:iam::(aws|\d{12}):policy/[\w+=,.@-]*$"
                - manageAccessRoleArn (str): ARN of the IAM role used to manage access to the blueprint.
                    - Pattern: ^arn:aws[^:]*:iam::\d{12}:(role|role/service-role)/[\w+=,.@-]*$
                - provisioningConfigurations (list of dict): Provisioning configurations associated with the blueprint.
                    - Each item is a `ProvisioningConfiguration` object describing how resources are provisioned.
                - provisioningRoleArn (str): ARN of the IAM role used for provisioning resources.
                    - Pattern: ^arn:aws[^:]*:iam::\d{12}:(role|role/service-role)/[\w+=,.@-]*$
                - regionalParameters (dict): A nested map of region-specific parameters.
                    - Outer keys: Region codes (e.g., "us-west-2")
                        - Constraints: 4–16 characters, pattern: ^[a-z]{2}-?(iso|gov)?-{1}[a-z]*-{1}[0-9]$
                    - Inner dicts: Key-value pairs of configuration parameters for that region.
                - updatedAt (str): Timestamp indicating when the blueprint was last updated.
        """
        try:
            # Prepare the request parameters
            params = {
                'domainIdentifier': domain_identifier,
                'environmentBlueprintIdentifier': identifier,
            }
            response = datazone_client.get_environment_blueprint_configuration(**params)
            return response
        except ClientError as e:  # pragma: no cover
            error_code = e.response.get('Error', {}).get('Code', '')
            error_message = e.response.get('Error', {}).get('Message', str(e))

            if error_code == 'AccessDeniedException':  # pragma: no cover
                raise Exception(
                    f'Access denied while getting environment blueprint {identifier}  configuration in domain {domain_identifier}: {error_message}'
                )
            elif error_code == 'ResourceNotFoundException':  # pragma: no cover
                raise Exception(
                    f'Environment blueprint {identifier} not found in domain {domain_identifier}: {error_message}'
                )
            elif error_code == 'ValidationException':  # pragma: no cover
                raise Exception(
                    f'Invalid parameters while getting environment blueprint {identifier} configuration in domain {domain_identifier}: {error_message}'
                )
            else:  # pragma: no cover
                raise Exception(
                    f'Error getting environment blueprint {identifier} configuration in domain {domain_identifier}: {error_message}'
                )

    @mcp.tool()
    async def list_connections(
        domain_identifier: str = Field(
            ..., description='The ID of the domain containing the connections'
        ),
        project_identifier: str = Field(
            ..., description='The ID of the project containing the connections'
        ),
        max_results: int = Field(default=50, description='Maximum number of connections to return'),
        next_token: Optional[str] = Field(default=None, description='Token for pagination'),
        environment_identifier: Optional[str] = Field(
            default=None, description='The ID of the environment to filter connections by'
        ),
        name: Optional[str] = Field(
            default=None, description='The name of the connection to filter by'
        ),
        sort_by: Optional[str] = Field(
            default=None, description='The field to sort connections by'
        ),
        sort_order: Optional[str] = Field(
            default=None, description='The sort order (ASC or DESC)'
        ),
        type: Optional[str] = Field(
            default=None, description='The type of connection to filter by'
        ),
    ) -> Dict[str, Any]:
        """Lists connections in Amazon DataZone.

        This is specifically for listing DataZone connections and should be used in the DataZone MCP server.

        Args:
            domain_identifier (str): The ID of the domain where you want to list connections
            project_identifier (str): The ID of the project where you want to list connections
            max_results (int, optional): Maximum number of connections to return (1-50, default: 50)
            next_token (str, optional): Token for pagination
            environment_identifier (str, optional): The ID of the environment where you want to list connections
            name (str, optional): The name of the connection to filter by (0-64 characters)
            sort_by (str, optional): How to sort the listed connections (valid: "NAME")
            sort_order (str, optional): Sort order (valid: "ASCENDING" or "DESCENDING")
            type (str, optional): The type of connection to filter by (valid: ATHENA, BIGQUERY, DATABRICKS, etc.)

        Returns:
            Dict[str, Any]: The list of connections including:
                - items: Array of connection summaries
                - nextToken: Token for pagination if more results are available
        """
        try:
            # Handle optional parameters
            max_results_value = _get_param_value(max_results)
            next_token_value = _get_param_value(next_token)
            environment_identifier_value = _get_param_value(environment_identifier)
            name_value = _get_param_value(name)
            sort_by_value = _get_param_value(sort_by)
            sort_order_value = _get_param_value(sort_order)
            type_value = _get_param_value(type)

            # Prepare the request parameters
            params = {
                'domainIdentifier': domain_identifier,
                'projectIdentifier': project_identifier,
                'maxResults': min(max_results_value, 50),  # Ensure maxResults is within valid range
            }

            # Add optional parameters if provided
            if next_token_value:  # pragma: no cover
                params['nextToken'] = next_token_value
            if environment_identifier_value:  # pragma: no cover
                params['environmentIdentifier'] = environment_identifier_value
            if name_value:  # pragma: no cover
                params['name'] = name_value
            if sort_by_value:  # pragma: no cover
                params['sortBy'] = sort_by_value
            if sort_order_value:  # pragma: no cover
                params['sortOrder'] = sort_order_value
            if type_value:  # pragma: no cover
                params['type'] = type_value

            response = datazone_client.list_connections(**params)
            return response
        except ClientError as e:  # pragma: no cover
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']

            if error_code == 'AccessDeniedException':  # pragma: no cover
                raise Exception(
                    f'Access denied while listing connections in domain {domain_identifier}: {error_message}'
                )
            elif error_code == 'ValidationException':  # pragma: no cover
                raise Exception(
                    f'Invalid parameters while listing connections in domain {domain_identifier}: {error_message}'
                )
            else:  # pragma: no cover
                raise Exception(
                    f'Unexpected error listing connections in domain {domain_identifier}: {error_message}'
                )

    @mcp.tool()
    async def list_environment_blueprints(
        domain_identifier: str = Field(
            ..., description='The ID of the domain containing the environment blueprints'
        ),
        managed: Optional[bool] = Field(
            default=None, description='Whether to list managed environment blueprints'
        ),
        max_results: int = Field(
            default=50, description='Maximum number of environment blueprints to return'
        ),
        name: Optional[str] = Field(
            default=None, description='The name of the environment blueprint to filter by'
        ),
        next_token: Optional[str] = Field(default=None, description='Token for pagination'),
    ) -> Dict[str, Any]:
        r"""Lists environment blueprints in an Amazon DataZone domain.

        Args:
            domain_identifier (str): The ID of the domain where the blueprints are listed
                Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
            managed (bool, optional): Specifies whether to list only managed blueprints
            max_results (int, optional): Maximum number of blueprints to return (1-50, default: 50)
            name (str, optional): Filter blueprints by name (1-64 characters)
                Pattern: ^[\\w -]+$
            next_token (str, optional): Token for pagination (1-8192 characters)

        Returns:
            Dict containing:
                - items: List of environment blueprints, each containing:
                    - id: Blueprint identifier
                    - name: Blueprint name
                    - description: Blueprint description
                    - provider: Blueprint provider
                    - provisioning_properties: Blueprint provisioning properties
                    - created_at: Creation timestamp
                    - updated_at: Last update timestamp
                - next_token: Token for pagination if more results are available
        """
        try:
            # Handle optional parameters
            managed_value = _get_param_value(managed)
            max_results_value = _get_param_value(max_results)
            name_value = _get_param_value(name)
            next_token_value = _get_param_value(next_token)

            logger.info(f'Listing environment blueprints in domain {domain_identifier}')

            # Prepare request parameters
            params = {
                'domainIdentifier': domain_identifier,
                'maxResults': min(max_results_value, 50),  # Ensure maxResults is within valid range
            }

            # Add optional parameters
            if managed_value is not None:  # pragma: no cover
                params['managed'] = managed_value
            if name_value:  # pragma: no cover
                params['name'] = name_value
            if next_token_value:  # pragma: no cover
                params['nextToken'] = next_token_value

            # List the environment blueprints
            response = datazone_client.list_environment_blueprints(**params)

            # Format the response
            result = {'items': [], 'next_token': response.get('nextToken')}

            # Format each blueprint
            for blueprint in response.get('items', []):
                formatted_blueprint = {
                    'id': blueprint.get('id'),
                    'name': blueprint.get('name'),
                    'description': blueprint.get('description'),
                    'provider': blueprint.get('provider'),
                    'provisioning_properties': blueprint.get('provisioningProperties'),
                    'created_at': blueprint.get('createdAt'),
                    'updated_at': blueprint.get('updatedAt'),
                }
                result['items'].append(formatted_blueprint)

            logger.info(
                f'Successfully listed {len(result["items"])} environment blueprints in domain {domain_identifier}'
            )
            return result

        except ClientError as e:  # pragma: no cover
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDeniedException':  # pragma: no cover
                logger.error(
                    f'Access denied while listing environment blueprints in domain {domain_identifier}'
                )
                raise Exception(
                    f'Access denied while listing environment blueprints in domain {domain_identifier}'
                )
            elif error_code == 'ResourceNotFoundException':  # pragma: no cover
                logger.error(
                    f'Domain {domain_identifier} not found while listing environment blueprints'
                )
                raise Exception(
                    f'Domain {domain_identifier} not found while listing environment blueprints'
                )
            elif error_code == 'ValidationException':  # pragma: no cover
                logger.error(
                    f'Invalid parameters for listing environment blueprints in domain {domain_identifier}'
                )
                raise Exception(
                    f'Invalid parameters for listing environment blueprints in domain {domain_identifier}'
                )
            else:  # pragma: no cover
                logger.error(
                    f'Error listing environment blueprints in domain {domain_identifier}: {str(e)}'
                )
                raise Exception(
                    f'Error listing environment blueprints in domain {domain_identifier}: {str(e)}'
                )
        except Exception as e:  # pragma: no cover
            logger.error(
                f'Unexpected error listing environment blueprints in domain {domain_identifier}: {str(e)}'
            )
            raise Exception(
                f'Unexpected error listing environment blueprints in domain {domain_identifier}: {str(e)}'
            )

    @mcp.tool()
    async def list_environment_blueprint_configurations(
        domain_identifier: str = Field(
            ..., description='The ID of the domain containing the environment blueprint configurations'
        ),
        max_results: int = Field(
            default=50, description='Maximum number of environment blueprint configurations to return'
        ),
        next_token: Optional[str] = Field(default=None, description='Token for pagination')
    ) -> Dict[str, Any]:
        """Lists environment blueprints in an Amazon DataZone domain.

        Args:
            domain_identifier (str): The ID of the domain where the blueprint configurations are listed
                Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
            max_results (int, optional): Maximum number of blueprint configurations to return (1-50, default: 50)
            next_token (str, optional): Token for pagination (1-8192 characters)

        Returns:
            dict: A dictionary with the following structure:

        Args:
                items (List[dict]): A list of environment blueprint summaries, each including:
                    - createdAt (str): The timestamp when the blueprint was created.
                    - domainId (str): The identifier of the Amazon DataZone domain.
                    - enabledRegions (List[str]): A list of AWS regions where the blueprint is enabled.
                    - environmentBlueprintId (str): Unique ID of the environment blueprint.
                    - environmentRolePermissionBoundary (str): ARN of the permission boundary used for environment roles.
                    - manageAccessRoleArn (str): ARN of the IAM role used to manage environment access.
                    - provisioningConfigurations (List[dict]): A list of provisioning configuration objects.
                        (Details not expanded here — structure is custom and tool-dependent.)
                    - provisioningRoleArn (str): ARN of the IAM role used to provision environments.
                    - regionalParameters (dict): A dictionary mapping region names to parameter maps.
                        Example: { "us-west-2": { "param1": "value1" } }
                    - updatedAt (str): The timestamp when the blueprint was last updated.

                nextToken (str): Token for paginated results. Use in subsequent requests to retrieve the next set of environment blueprints.
        """
        try:
            # Handle optional parameters
            max_results_value = _get_param_value(max_results)
            next_token_value = _get_param_value(next_token)

            logger.info(
                f'Listing environment blueprint configurations in domain {domain_identifier}'
            )

            # Prepare request parameters
            params = {
                'domainIdentifier': domain_identifier,
                'maxResults': min(max_results_value, 50),  # Ensure maxResults is within valid range
            }

            if next_token_value:  # pragma: no cover
                params['nextToken'] = next_token_value

            # List the environment blueprint configurations
            response = datazone_client.list_environment_blueprint_configurations(**params)

            # Format the response
            result = {'items': [], 'next_token': response.get('nextToken')}

            # Format each blueprint
            for configuration in response.get('items', []):
                formatted_configuration = {
                    'createdAt': configuration.get('createdAt'),
                    'domainId': configuration.get('domainId'),
                    'enabledRegions': configuration.get('enabledRegions'),
                    'environmentBlueprintId': configuration.get('environmentBlueprintId'),
                    'environmentRolePermissionBoundary': configuration.get(
                        'environmentRolePermissionBoundary'
                    ),
                    'manageAccessRoleArn': configuration.get('manageAccessRoleArn'),
                    'provisioningConfigurations': configuration.get('provisioningConfigurations'),
                    'provisioningRoleArn': configuration.get('provisioningRoleArn'),
                    'regionalParameters': configuration.get('regionalParameters'),
                    'updatedAt': configuration.get('updatedAt'),
                }
                result['items'].append(formatted_configuration)

            logger.info(
                f'Successfully listed {len(result["items"])} environment blueprint configurations in domain {domain_identifier}'
            )
            return result

        except ClientError as e:  # pragma: no cover
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDeniedException':  # pragma: no cover
                logger.error(
                    f'Access denied while listing environment blueprint configurations in domain {domain_identifier}'
                )
                raise Exception(
                    f'Access denied while listing environment blueprint configurations in domain {domain_identifier}'
                )
            elif error_code == 'ResourceNotFoundException':  # pragma: no cover
                logger.error(
                    f'Domain {domain_identifier} not found while listing environment blueprint configurations'
                )
                raise Exception(
                    f'Domain {domain_identifier} not found while listing environment blueprint configurations'
                )
            elif error_code == 'ValidationException':  # pragma: no cover
                logger.error(
                    f'Invalid parameters for listing environment blueprint configurations in domain {domain_identifier}'
                )
                raise Exception(
                    f'Invalid parameters for listing environment blueprint configurations in domain {domain_identifier}'
                )
            else:  # pragma: no cover
                logger.error(
                    f'Error listing environment blueprint configurations in domain {domain_identifier}: {str(e)}'
                )
                raise Exception(
                    f'Error listing environment blueprint configurations in domain {domain_identifier}: {str(e)}'
                )
        except Exception as e:  # pragma: no cover
            logger.error(
                f'Unexpected error listing environment blueprint configurations in domain {domain_identifier}: {str(e)}'
            )
            raise Exception(
                f'Unexpected error listing environment blueprint configurations in domain {domain_identifier}: {str(e)}'
            )

    @mcp.tool()
    async def list_environment_profiles(
        domain_identifier: str = Field(
            ..., description='The ID of the domain containing the environment profiles'
        ),
        aws_account_id: Optional[str] = Field(
            default=None, description='The AWS account ID to filter environment profiles by'
        ),
        aws_account_region: Optional[str] = Field(
            default=None, description='The AWS region to filter environment profiles by'
        ),
        environment_blueprint_identifier: Optional[str] = Field(
            default=None, description='The environment blueprint ID to filter environment profiles by'
        ),
        max_results: int = Field(
            default=50, description='Maximum number of environment profiles to return'
        ),
        name: Optional[str] = Field(
            default=None, description='The name of the environment profile to filter by'
        ),
        next_token: Optional[str] = Field(default=None, description='Token for pagination'),
        project_identifier: Optional[str] = Field(
            default=None, description='The project ID to filter environment profiles by'
        ),
    ) -> Dict[str, Any]:
        r"""Lists environment profiles within a specified Amazon DataZone domain, optionally filtered by AWS account, region, blueprint, and project.

        Args:
            domain_identifier (str): The identifier of the Amazon DataZone domain.
                Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
                Required: Yes

            aws_account_id (str, optional): The AWS account ID to filter results.
                Pattern: r"^\d{12}$"

            aws_account_region (str, optional): The AWS region to filter results.
                Pattern: ^[a-z]{2}-[a-z]{4,10}-\d$

            environment_blueprint_identifier (str, optional): The identifier of the blueprint used to create the environment profiles.
                Pattern: ^[a-zA-Z0-9_-]{1,36}$

            max_results (int, optional): Maximum number of results to return (1–50).

            name (str, optional): Filter environment profiles by name.
                Length: 1–64 characters
                Pattern: ^[\w -]+$

            next_token (str, optional): A pagination token returned from a previous call to retrieve the next set of results.
                Length: 1–8192 characters

            project_identifier (str, optional): The identifier of the Amazon DataZone project.
                Pattern: ^[a-zA-Z0-9_-]{1,36}$

        Returns:
            dict: A dictionary containing:
                - items (List[dict]): A list of environment profile summaries. Each item includes:
                    - awsAccountId (str): AWS account where the profile exists.
                    - awsAccountRegion (str): AWS region of the profile.
                    - createdAt (str): Timestamp when the profile was created.
                    - createdBy (str): Identifier of the user who created the profile.
                    - description (str): Description of the profile.
                    - domainId (str): The domain associated with the profile.
                    - environmentBlueprintId (str): ID of the blueprint used.
                    - id (str): Unique ID of the environment profile.
                    - name (str): Name of the environment profile.
                    - projectId (str): ID of the associated project.
                    - updatedAt (str): Timestamp of last update.

                - nextToken (str): Token for retrieving the next page of results, if any.
        """
        try:
            # Handle optional parameters
            aws_account_id_value = _get_param_value(aws_account_id)
            aws_account_region_value = _get_param_value(aws_account_region)
            environment_blueprint_identifier_value = _get_param_value(environment_blueprint_identifier)
            max_results_value = _get_param_value(max_results)
            name_value = _get_param_value(name)
            next_token_value = _get_param_value(next_token)
            project_identifier_value = _get_param_value(project_identifier)

            logger.info(f'Listing environment profiles in domain {domain_identifier}')

            # Prepare request parameters
            params = {
                'domainIdentifier': domain_identifier,
                'maxResults': min(max_results_value, 50),  # Ensure maxResults is within valid range
            }

            # Add optional parameters
            if aws_account_id_value:  # pragma: no cover
                params['awsAccountId'] = aws_account_id_value
            if aws_account_region_value:  # pragma: no cover
                params['awsAccountRegion'] = aws_account_region_value
            if environment_blueprint_identifier_value:  # pragma: no cover
                params['environmentBlueprintIdentifier'] = environment_blueprint_identifier_value
            if name_value:  # pragma: no cover
                params['name'] = name_value
            if next_token_value:  # pragma: no cover
                params['nextToken'] = next_token_value
            if project_identifier_value:  # pragma: no cover
                params['projectIdentifier'] = project_identifier_value

            # List the environment profiles
            response = datazone_client.list_environment_profiles(**params)

            # Format the response
            result = {'items': [], 'next_token': response.get('nextToken')}

            # Format each profile
            for profile in response.get('items', []):
                formatted_profile = {
                    'aws_account_id': profile.get('awsAccountId'),
                    'aws_account_region': profile.get('awsAccountRegion'),
                    'created_at': profile.get('createdAt'),
                    'created_by': profile.get('createdBy'),
                    'domain_id': profile.get('domain_id'),
                    'environment_blueprint_id': profile.get('environmentBlueprintId'),
                    'id': profile.get('id'),
                    'name': profile.get('name'),
                    'description': profile.get('description'),
                    'project_id': profile.get('projectId'),
                    'updated_at': profile.get('updatedAt'),
                }
                result['items'].append(formatted_profile)

            logger.info(
                f'Successfully listed {len(result["items"])} environment profiles in domain {domain_identifier}'
            )
            return result

        except ClientError as e:  # pragma: no cover
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDeniedException':  # pragma: no cover
                logger.error(
                    f'Access denied while listing environment profiles in domain {domain_identifier}'
                )
                raise Exception(
                    f'Access denied while listing environment profiles in domain {domain_identifier}'
                )
            elif error_code == 'ResourceNotFoundException':  # pragma: no cover
                logger.error(
                    f'Domain {domain_identifier} not found while listing environment profiles'
                )
                raise Exception(
                    f'Domain {domain_identifier} not found while listing environment profiles'
                )
            elif error_code == 'ValidationException':  # pragma: no cover
                logger.error(
                    f'Invalid parameters for listing environment profiles in domain {domain_identifier}'
                )
                raise Exception(
                    f'Invalid parameters for listing environment profiles in domain {domain_identifier}'
                )
            else:  # pragma: no cover
                logger.error(
                    f'Error listing environment profiles in domain {domain_identifier}: {str(e)}'
                )
                raise Exception(
                    f'Error listing environment profiles in domain {domain_identifier}: {str(e)}'
                )
        except Exception as e:  # pragma: no cover
            logger.error(
                f'Unexpected error listing environment profiles in domain {domain_identifier}: {str(e)}'
            )
            raise Exception(
                f'Unexpected error listing environment profiles in domain {domain_identifier}: {str(e)}'
            )

    # Return the decorated functions for testing purposes
    return {
        'list_environments': list_environments,
        'create_connection': create_connection,
        'get_connection': get_connection,
        'get_environment': get_environment,
        'get_environment_blueprint': get_environment_blueprint,
        'get_environment_blueprint_configuration': get_environment_blueprint_configuration,
        'list_connections': list_connections,
        'list_environment_blueprints': list_environment_blueprints,
        'list_environment_blueprint_configurations': list_environment_blueprint_configurations,
        'list_environment_profiles': list_environment_profiles,
    }
