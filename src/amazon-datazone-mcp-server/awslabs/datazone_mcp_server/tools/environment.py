"""Environment management tools for Amazon DataZone."""

from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from .common import ClientError, datazone_client, logger


def register_tools(mcp: FastMCP):
    """Register environment management tools with the MCP server."""

    # @mcp.tool()
    # async def create_environment(
    #     domain_identifier: str,
    #     environment_profile_identifier: str,
    #     project_identifier: str,
    #     name: str,
    #     deployment_order: int = None,
    #     description: str = None,
    #     environment_account_identifier: str = None,
    #     environment_account_region: str = None,
    #     environment_blueprint_identifier: str = None,
    #     environment_configuration_id: str = None,
    #     glossary_terms: str = None,
    #     user_parameters: List[Dict[str, str]] = None
    # ) -> Any:
    #     """
    #     Creates a new environment in Amazon DataZone. Environments define infrastructure that projects can deploy into,
    #     using a specified blueprint and optional configurations, glossary terms, and user parameters.

    #     This is specifically for creating environments in the Amazon DataZone MCP server.

    #     Args:
    #         domain_identifier (str): The identifier of the Amazon DataZone domain in which the environment is created.
    #             Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
    #             Required: Yes
    #         deployment_order (int, optional): The deployment order of the environment.
    #             Type: Integer
    #             Required: No
    #         description (str, optional): A description for the environment.
    #             Type: String
    #             Required: No
    #         environment_account_identifier (str, optional): The AWS account ID where the environment is created.
    #             Type: String
    #             Required: No
    #         environment_account_region (str, optional): The AWS region where the environment is created.
    #             Type: String
    #             Required: No
    #         environment_blueprint_identifier (str, optional): The ID of the blueprint used to create the environment.
    #             Pattern: ^[a-zA-Z0-9_-]{1,36}$
    #             Required: No
    #         environment_configuration_id (str, optional): The configuration ID of the environment.
    #             Type: String
    #             Required: No
    #         environment_profile_identifier (str): The ID of the environment profile used to create this environment.
    #             Pattern: ^[a-zA-Z0-9_-]{0,36}$
    #             Required: Yes
    #         glossary_terms (List[str], optional): Glossary terms associated with this environment.
    #             Type: List of strings
    #             Constraints: 1–20 items, each matching ^[a-zA-Z0-9_-]{1,36}$
    #             Required: No
    #         name (str): The name of the environment.
    #             Type: String
    #             Length: 1–64 characters
    #             Pattern: ^[\w -]+$
    #             Required: Yes
    #         project_identifier (str): The identifier of the Amazon DataZone project for the environment.
    #             Pattern: ^[a-zA-Z0-9_-]{1,36}$
    #             Required: Yes
    #         user_parameters (List[Dict[str, Any]], optional): A list of user-defined parameters used by the environment.
    #             Each item is an EnvironmentParameter object.
    #             Required: No

    #     Returns:
    #         dict: A dictionary with the created environment's details, including:
    #             - awsAccountId (str): AWS account in which the environment is created.
    #             - awsAccountRegion (str): AWS region of the environment.
    #             - createdAt (str): Timestamp when the environment was created.
    #             - createdBy (str): The creator of the environment.
    #             - deploymentProperties (dict): Deployment timeout settings.
    #             - description (str): The environment's description.
    #             - domainId (str): The domain ID.
    #             - environmentActions (list): Configurable actions of the environment.
    #             - environmentBlueprintId (str): The blueprint ID used.
    #             - environmentConfigurationId (str): Configuration ID.
    #             - environmentProfileId (str): The environment profile ID used.
    #             - glossaryTerms (list): Glossary terms associated.
    #             - id (str): The environment ID.
    #             - lastDeployment (dict): Info about the last deployment status and messages.
    #             - name (str): The environment name.
    #             - projectId (str): The associated project ID.
    #             - provider (str): The provider of the environment.
    #             - provisionedResources (list): Resources provisioned for the environment.
    #             - provisioningProperties (dict): Union-type provisioning properties.
    #             - status (str): Status of the environment.
    #             - updatedAt (str): Last updated timestamp.
    #             - userParameters (list): Custom parameter objects used in the environment.
    #     """
    #     try:
    #         # Prepare the request parameters
    #         params = {
    #             "domainIdentifier": domain_identifier,
    #             "name": name,
    #             "environmentProfileIdentifier": environment_profile_identifier,
    #             "projectIdentifier": project_identifier
    #         }

    #         # Add optional parameters if provided
    #         if deployment_order:
    #             params["deploymentOrder"] = deployment_order
    #         if description:
    #             params["description"] = description
    #         if environment_account_identifier:
    #             params["environmentAccountIdentifier"] = environment_account_identifier
    #         if environment_account_region:
    #             params["environmentAccountRegion"] = environment_account_region
    #         if environment_blueprint_identifier:
    #             params["environmentBlueprintIdentifier"] = environment_blueprint_identifier
    #         if environment_configuration_id:
    #             params["environmentConfigurationId"] = environment_configuration_id
    #         if glossary_terms:
    #             params["glossaryTerms"] = glossary_terms
    #         if user_parameters:
    #             params["userParameters"] = user_parameters

    #         response = datazone_client.create_environment(**params)
    #         return response
    #     except ClientError as e:
    #         error_code = e.response["Error"]["Code"]
    #         error_message = e.response["Error"]["Message"]

    #         if error_code == "AccessDeniedException":
    #             raise Exception(f"Access denied while creating environment in domain {domain_identifier}: {error_message}")
    #         elif error_code == "ConflictException":
    #             raise Exception(f"Conflict while creating environment in domain {domain_identifier}: {error_message}")
    #         elif error_code == "ResourceNotFoundException":
    #             raise Exception(
    #                 f"Resource not found while creating environment in domain {domain_identifier}: {error_message}")
    #         elif error_code == "ServiceQuotaExceededException":
    #             raise Exception(
    #                 f"Service quota exceeded while creating environment in domain {domain_identifier}: {error_message}")
    #         elif error_code == "ValidationException":
    #             raise Exception(
    #                 f"Invalid parameters while creating environment in domain {domain_identifier}: {error_message}")
    #         else:
    #             raise Exception(f"Unexpected error creating environment in domain {domain_identifier}: {error_message}")

    @mcp.tool()
    async def list_environments(
        domain_identifier: str,
        project_identifier: str,
        max_results: int = 50,
        next_token: Optional[str] = None,
        aws_account_id: Optional[str] = None,
        aws_account_region: Optional[str] = None,
        environment_blueprint_identifier: Optional[str] = None,
        environment_profile_identifier: Optional[str] = None,
        name: Optional[str] = None,
        provider: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Any:
        """
        Lists environments in Amazon DataZone.

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
            ...     domain_identifier="dzd_4p9n6sw4qt9xgn",
            ...     project_identifier="prj_123456789",
            ...     status="ACTIVE"
            ... )
        """
        try:
            params = {
                "domainIdentifier": domain_identifier,
                "projectIdentifier": project_identifier,
                "maxResults": max_results,
            }

            # Add optional parameters if provided
            if next_token:
                params["nextToken"] = next_token
            if aws_account_id:
                params["awsAccountId"] = aws_account_id
            if aws_account_region:
                params["awsAccountRegion"] = aws_account_region
            if environment_blueprint_identifier:
                params["environmentBlueprintIdentifier"] = environment_blueprint_identifier
            if environment_profile_identifier:
                params["environmentProfileIdentifier"] = environment_profile_identifier
            if name:
                params["name"] = name
            if provider:
                params["provider"] = provider
            if status:
                params["status"] = status

            response = datazone_client.list_environments(**params)
            return response
        except ClientError as e:
            raise Exception(f"Error listing environments: {e}")

    @mcp.tool()
    async def create_connection(
        domain_identifier: str,
        name: str,
        environment_identifier: Optional[str] = None,
        aws_location: Optional[Dict[str, str]] = None,
        description: Optional[str] = None,
        client_token: Optional[str] = None,
        props: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Creates a new connection in Amazon DataZone. A connection enables you to connect your resources

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
            ...     domain_identifier="dzd_4p9n6sw4qt9xgn",
            ...     name="MyConnection",
            ...     environment_identifier="env_123456789",
            ...     aws_location={
            ...         "accessRole": "arn:aws:iam::123456789012:role/DataZoneAccessRole",
            ...         "awsAccountId": "123456789012",
            ...         "awsRegion": "us-east-1",
            ...         "iamConnectionId": "iam-123456789"
            ...     },
            ...     description="Connection to external service"
            ... )
        """
        try:
            # Prepare the request parameters
            params: Dict[str, Any] = {"domainIdentifier": domain_identifier, "name": name}

            # Add optional parameters if provided
            if environment_identifier:
                params["environmentIdentifier"] = environment_identifier
            if aws_location:
                params["awsLocation"] = aws_location
            if description:
                params["description"] = description
            if client_token:
                params["clientToken"] = client_token
            if props:
                params["props"] = props

            response = datazone_client.create_connection(**params)
            return response
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            if error_code == "AccessDeniedException":
                raise Exception(
                    f"Access denied while creating connection in domain {domain_identifier}: {error_message}"
                )
            elif error_code == "ConflictException":
                raise Exception(
                    f"Conflict while creating connection in domain {domain_identifier}: {error_message}"
                )
            elif error_code == "ResourceNotFoundException":
                raise Exception(
                    f"Resource not found while creating connection in domain {domain_identifier}: {error_message}"
                )
            elif error_code == "ServiceQuotaExceededException":
                raise Exception(
                    f"Service quota exceeded while creating connection in domain {domain_identifier}: {error_message}"
                )
            elif error_code == "ValidationException":
                raise Exception(
                    f"Invalid parameters while creating connection in domain {domain_identifier}: {error_message}"
                )
            else:
                raise Exception(
                    f"Unexpected error creating connection in domain {domain_identifier}: {error_message}"
                )

    # @mcp.tool()
    # async def delete_connection(
    #     domain_identifier: str,
    #     identifier: str
    # ) -> Any:
    #     """
    #     Deletes a connection in Amazon DataZone. This operation removes the specified connection from the given domain.

    #     This is specifically used for connection deletion in the Amazon DataZone MCP server. The request does not contain a body.

    #     Args:
    #         domain_identifier (str): The ID of the Amazon DataZone domain where the connection is deleted.
    #             Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
    #             Required: Yes

    #         identifier (str): The ID of the connection to be deleted.
    #             Length Constraints: Minimum length of 0. Maximum length of 128.
    #             Required: Yes

    #     Returns:
    #         dict: A dictionary containing:
    #             - status (str): The status of the deletion action.

    #         The API returns HTTP 202 if the deletion request is accepted successfully.
    #     """
    #     try:
    #         # Prepare the request parameters
    #         params = {
    #             "domainIdentifier": domain_identifier,
    #             "identifier": identifier
    #         }

    #         response = datazone_client.delete_connection(**params)
    #         return response
    #     except ClientError as e:
    #         error_code = e.response.get("Error", {}).get("Code", "")
    #         error_message = e.response.get("Error", {}).get("Message", str(e))

    #         if error_code == "AccessDeniedException":
    #             raise Exception(f"Access denied while deleting connection {identifier} in domain {domain_identifier}: {error_message}")
    #         elif error_code == "ResourceNotFoundException":
    #             raise Exception(f"Connection {identifier} not found in domain {domain_identifier}: {error_message}")
    #         elif error_code == "ValidationException":
    #             raise Exception(f"Invalid parameters while deleting connection {identifier} in domain {domain_identifier}: {error_message}")
    #         else:
    #             raise Exception(f"Error deleting connection {identifier} in domain {domain_identifier}: {error_message}")

    @mcp.tool()
    async def get_connection(
        domain_identifier: str, identifier: str, with_secret: bool = False
    ) -> Any:
        """
        Gets a connection in Amazon DataZone. A connection enables you to connect your resources

        (domains, projects, and environments) to external resources and services.

        This is specifically for retrieving DataZone connections and should be used in the DataZone MCP server.

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
            ...     domain_identifier="dzd_4p9n6sw4qt9xgn",
            ...     identifier="conn_123456789",
            ...     with_secret=True
            ... )
        """
        try:
            # Prepare the request parameters
            params: Dict[str, Any] = {
                "domainIdentifier": domain_identifier,
                "identifier": identifier,
            }

            # Add with_secret parameter if True
            if with_secret:
                params["withSecret"] = with_secret

            response = datazone_client.get_connection(**params)
            return response
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            if error_code == "AccessDeniedException":
                raise Exception(
                    f"Access denied while getting connection {identifier} in domain {domain_identifier}: {error_message}"
                )
            elif error_code == "ResourceNotFoundException":
                raise Exception(
                    f"Connection {identifier} not found in domain {domain_identifier}: {error_message}"
                )
            elif error_code == "ValidationException":
                raise Exception(
                    f"Invalid parameters while getting connection {identifier} in domain {domain_identifier}: {error_message}"
                )
            else:
                raise Exception(
                    f"Error getting connection {identifier} in domain {domain_identifier}: {error_message}"
                )

    @mcp.tool()
    async def get_environment(domain_identifier: str, identifier: str) -> Any:
        """
        Gets an Amazon DataZone environment.

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
            ...     domain_identifier="dzd_4p9n6sw4qt9xgn",
            ...     identifier="conn_123456789"
            ... )
        """
        try:
            # Prepare the request parameters
            params = {"domainIdentifier": domain_identifier, "identifier": identifier}

            response = datazone_client.get_environment(**params)
            return response
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            if error_code == "AccessDeniedException":
                raise Exception(
                    f"Access denied while getting environment {identifier} in domain {domain_identifier}: {error_message}"
                )
            elif error_code == "ResourceNotFoundException":
                raise Exception(
                    f"Environment {identifier} not found in domain {domain_identifier}: {error_message}"
                )
            elif error_code == "ValidationException":
                raise Exception(
                    f"Invalid parameters while getting environment {identifier} in domain {domain_identifier}: {error_message}"
                )
            else:
                raise Exception(
                    f"Error getting environment {identifier} in domain {domain_identifier}: {error_message}"
                )

    @mcp.tool()
    async def get_environment_blueprint(domain_identifier: str, identifier: str) -> Any:
        r"""
        Gets an Amazon DataZone environment blueprint.

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
            params = {"domainIdentifier": domain_identifier, "identifier": identifier}

            response = datazone_client.get_environment_blueprint(**params)
            return response
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            if error_code == "AccessDeniedException":
                raise Exception(
                    f"Access denied while getting environment {identifier} blueprint in domain {domain_identifier}: {error_message}"
                )
            elif error_code == "ResourceNotFoundException":
                raise Exception(
                    f"Environment {identifier} not found in domain {domain_identifier}: {error_message}"
                )
            elif error_code == "ValidationException":
                raise Exception(
                    f"Invalid parameters while getting environment {identifier} blueprint in domain {domain_identifier}: {error_message}"
                )
            else:
                raise Exception(
                    f"Error getting environment {identifier} blueprint in domain {domain_identifier}: {error_message}"
                )

    @mcp.tool()
    async def get_environment_blueprint_configuration(
        domain_identifier: str, identifier: str
    ) -> Any:
        r"""
        Gets an Amazon DataZone environment blueprint configuration.

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
                "domainIdentifier": domain_identifier,
                "environmentBlueprintIdentifier": identifier,
            }
            response = datazone_client.get_environment_blueprint_configuration(**params)
            return response
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            if error_code == "AccessDeniedException":
                raise Exception(
                    f"Access denied while getting environment blueprint {identifier}  configuration in domain {domain_identifier}: {error_message}"
                )
            elif error_code == "ResourceNotFoundException":
                raise Exception(
                    f"Environment blueprint {identifier} not found in domain {domain_identifier}: {error_message}"
                )
            elif error_code == "ValidationException":
                raise Exception(
                    f"Invalid parameters while getting environment blueprint {identifier} configuration in domain {domain_identifier}: {error_message}"
                )
            else:
                raise Exception(
                    f"Error getting environment blueprint {identifier} configuration in domain {domain_identifier}: {error_message}"
                )

    # @mcp.tool()
    # async def get_environment_credentials(
    #     domain_identifier: str,
    #     environment_identifier: str
    # ) -> Any:
    #     """
    #     Retrieves temporary credentials for a specified environment within an Amazon DataZone domain.

    #     This request uses URI parameters to specify the target domain and environment. No request body is required. The operation returns temporary AWS credentials associated with the environment, including access keys and a session token.

    #     Args:
    #         domain_identifier (str): The ID of the Amazon DataZone domain where the environment exists.
    #             Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
    #             Required: Yes
    #         environment_identifier (str): The ID of the environment for which credentials are being retrieved.
    #             Pattern: ^[a-zA-Z0-9_-]{1,36}$
    #             Required: Yes

    #     Returns:
    #         dict: A dictionary containing temporary credentials for the specified environment:
    #             - accessKeyId (str): The access key ID
    #             - secretAccessKey (str): The secret access key
    #             - sessionToken (str): The session token
    #             - expiration (str): The ISO 8601 timestamp when the credentials expire

    #     Raises:
    #         HTTPError: If the request is invalid or the server encounters an error.
    #     """
    #     try:
    #         params = {
    #             "domainIdentifier": domain_identifier,
    #             "environmentIdentifier": environment_identifier
    #         }

    #         response = datazone_client.get_environment_credentials(**params)
    #         return response
    #     except ClientError as e:
    #         error_code = e.response.get("Error", {}).get("Code", "")
    #         error_message = e.response.get("Error", {}).get("Message", str(e))

    #         if error_code == "AccessDeniedException":
    #             raise Exception(f"Access denied while getting environment {environment_identifier} credentials in domain {domain_identifier}: {error_message}")
    #         elif error_code == "ResourceNotFoundException":
    #             raise Exception(f"Environment {environment_identifier} not found in domain {domain_identifier}: {error_message}")
    #         elif error_code == "ValidationException":
    #             raise Exception(f"Invalid parameters while getting environment {environment_identifier} credentials in domain {domain_identifier}: {error_message}")
    #         else:
    #             raise Exception(f"Error getting environment {environment_identifier} credentials in domain {domain_identifier}: {error_message}")

    @mcp.tool()
    async def list_connections(
        domain_identifier: str,
        project_identifier: str,
        max_results: int = 50,
        next_token: Optional[str] = None,
        environment_identifier: Optional[str] = None,
        name: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
        type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Lists connections in Amazon DataZone.

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
            # Prepare the request parameters
            params = {
                "domainIdentifier": domain_identifier,
                "projectIdentifier": project_identifier,
                "maxResults": min(max_results, 50),  # Ensure maxResults is within valid range
            }

            # Add optional parameters if provided
            if next_token:
                params["nextToken"] = next_token
            if environment_identifier:
                params["environmentIdentifier"] = environment_identifier
            if name:
                params["name"] = name
            if sort_by:
                params["sortBy"] = sort_by
            if sort_order:
                params["sortOrder"] = sort_order
            if type:
                params["type"] = type

            response = datazone_client.list_connections(**params)
            return response
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            if error_code == "AccessDeniedException":
                raise Exception(
                    f"Access denied while listing connections in domain {domain_identifier}: {error_message}"
                )
            elif error_code == "ValidationException":
                raise Exception(
                    f"Invalid parameters while listing connections in domain {domain_identifier}: {error_message}"
                )
            else:
                raise Exception(
                    f"Unexpected error listing connections in domain {domain_identifier}: {error_message}"
                )

    @mcp.tool()
    async def list_environment_blueprints(
        domain_identifier: str,
        managed: Optional[bool] = None,
        max_results: int = 50,
        name: Optional[str] = None,
        next_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""
        Lists environment blueprints in an Amazon DataZone domain.

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
            logger.info(f"Listing environment blueprints in domain {domain_identifier}")

            # Prepare request parameters
            params = {
                "domainIdentifier": domain_identifier,
                "maxResults": min(max_results, 50),  # Ensure maxResults is within valid range
            }

            # Add optional parameters
            if managed is not None:
                params["managed"] = managed
            if name:
                params["name"] = name
            if next_token:
                params["nextToken"] = next_token

            # List the environment blueprints
            response = datazone_client.list_environment_blueprints(**params)

            # Format the response
            result = {"items": [], "next_token": response.get("nextToken")}

            # Format each blueprint
            for blueprint in response.get("items", []):
                formatted_blueprint = {
                    "id": blueprint.get("id"),
                    "name": blueprint.get("name"),
                    "description": blueprint.get("description"),
                    "provider": blueprint.get("provider"),
                    "provisioning_properties": blueprint.get("provisioningProperties"),
                    "created_at": blueprint.get("createdAt"),
                    "updated_at": blueprint.get("updatedAt"),
                }
                result["items"].append(formatted_blueprint)

            logger.info(
                f"Successfully listed {len(result['items'])} environment blueprints in domain {domain_identifier}"
            )
            return result

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "AccessDeniedException":
                logger.error(
                    f"Access denied while listing environment blueprints in domain {domain_identifier}"
                )
                raise Exception(
                    f"Access denied while listing environment blueprints in domain {domain_identifier}"
                )
            elif error_code == "ResourceNotFoundException":
                logger.error(
                    f"Domain {domain_identifier} not found while listing environment blueprints"
                )
                raise Exception(
                    f"Domain {domain_identifier} not found while listing environment blueprints"
                )
            elif error_code == "ValidationException":
                logger.error(
                    f"Invalid parameters for listing environment blueprints in domain {domain_identifier}"
                )
                raise Exception(
                    f"Invalid parameters for listing environment blueprints in domain {domain_identifier}"
                )
            else:
                logger.error(
                    f"Error listing environment blueprints in domain {domain_identifier}: {str(e)}"
                )
                raise Exception(
                    f"Error listing environment blueprints in domain {domain_identifier}: {str(e)}"
                )
        except Exception as e:
            logger.error(
                f"Unexpected error listing environment blueprints in domain {domain_identifier}: {str(e)}"
            )
            raise Exception(
                f"Unexpected error listing environment blueprints in domain {domain_identifier}: {str(e)}"
            )

    @mcp.tool()
    async def list_environment_blueprint_configurations(
        domain_identifier: str, max_results: int = 50, next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Lists environment blueprints in an Amazon DataZone domain.

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
            logger.info(
                f"Listing environment blueprint configurations in domain {domain_identifier}"
            )

            # Prepare request parameters
            params = {
                "domainIdentifier": domain_identifier,
                "maxResults": min(max_results, 50),  # Ensure maxResults is within valid range
            }

            if next_token:
                params["nextToken"] = next_token

            # List the environment blueprint configurations
            response = datazone_client.list_environment_blueprint_configurations(**params)

            # Format the response
            result = {"items": [], "next_token": response.get("nextToken")}

            # Format each blueprint
            for configuration in response.get("items", []):
                formatted_configuration = {
                    "createdAt": configuration.get("createdAt"),
                    "domainId": configuration.get("domainId"),
                    "enabledRegions": configuration.get("enabledRegions"),
                    "environmentBlueprintId": configuration.get("environmentBlueprintId"),
                    "environmentRolePermissionBoundary": configuration.get(
                        "environmentRolePermissionBoundary"
                    ),
                    "manageAccessRoleArn": configuration.get("manageAccessRoleArn"),
                    "provisioningConfigurations": configuration.get("provisioningConfigurations"),
                    "provisioningRoleArn": configuration.get("provisioningRoleArn"),
                    "regionalParameters": configuration.get("regionalParameters"),
                    "updatedAt": configuration.get("updatedAt"),
                }
                result["items"].append(formatted_configuration)

            logger.info(
                f"Successfully listed {len(result['items'])} environment blueprint configurations in domain {domain_identifier}"
            )
            return result

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "AccessDeniedException":
                logger.error(
                    f"Access denied while listing environment blueprint configurations in domain {domain_identifier}"
                )
                raise Exception(
                    f"Access denied while listing environment blueprint configurations in domain {domain_identifier}"
                )
            elif error_code == "ResourceNotFoundException":
                logger.error(
                    f"Domain {domain_identifier} not found while listing environment blueprint configurations"
                )
                raise Exception(
                    f"Domain {domain_identifier} not found while listing environment blueprint configurations"
                )
            elif error_code == "ValidationException":
                logger.error(
                    f"Invalid parameters for listing environment blueprint configurations in domain {domain_identifier}"
                )
                raise Exception(
                    f"Invalid parameters for listing environment blueprint configurations in domain {domain_identifier}"
                )
            else:
                logger.error(
                    f"Error listing environment blueprint configurations in domain {domain_identifier}: {str(e)}"
                )
                raise Exception(
                    f"Error listing environment blueprint configurations in domain {domain_identifier}: {str(e)}"
                )
        except Exception as e:
            logger.error(
                f"Unexpected error listing environment blueprint configurations in domain {domain_identifier}: {str(e)}"
            )
            raise Exception(
                f"Unexpected error listing environment blueprint configurations in domain {domain_identifier}: {str(e)}"
            )

    @mcp.tool()
    async def list_environment_profiles(
        domain_identifier: str,
        aws_account_id: Optional[str] = None,
        aws_account_region: Optional[str] = None,
        environment_blueprint_identifier: Optional[str] = None,
        max_results: int = 50,
        name: Optional[str] = None,
        next_token: Optional[str] = None,
        project_identifier: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""
        Lists environment profiles within a specified Amazon DataZone domain, optionally filtered by AWS account, region, blueprint, and project.

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
            logger.info(f"Listing environment profiles in domain {domain_identifier}")

            # Prepare request parameters
            params = {
                "domainIdentifier": domain_identifier,
                "maxResults": min(max_results, 50),  # Ensure maxResults is within valid range
            }

            # Add optional parameters
            if aws_account_id:
                params["awsAccountId"] = aws_account_id
            if aws_account_region:
                params["awsAccountRegion"] = aws_account_region
            if environment_blueprint_identifier:
                params["environmentBlueprintIdentifier"] = environment_blueprint_identifier
            if name:
                params["name"] = name
            if next_token:
                params["nextToken"] = next_token
            if project_identifier:
                params["projectIdentifier"] = project_identifier

            # List the environment profiles
            response = datazone_client.list_environment_profiles(**params)

            # Format the response
            result = {"items": [], "next_token": response.get("nextToken")}

            # Format each profile
            for profile in response.get("items", []):
                formatted_profile = {
                    "aws_account_id": profile.get("awsAccountId"),
                    "aws_account_region": profile.get("awsAccountRegion"),
                    "created_at": profile.get("createdAt"),
                    "created_by": profile.get("createdBy"),
                    "domain_id": profile.get("domain_id"),
                    "environment_blueprint_id": profile.get("environmentBlueprintId"),
                    "id": profile.get("id"),
                    "name": profile.get("name"),
                    "description": profile.get("description"),
                    "project_id": profile.get("projectId"),
                    "updated_at": profile.get("updatedAt"),
                }
                result["items"].append(formatted_profile)

            logger.info(
                f"Successfully listed {len(result['items'])} environment profiles in domain {domain_identifier}"
            )
            return result

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "AccessDeniedException":
                logger.error(
                    f"Access denied while listing environment profiles in domain {domain_identifier}"
                )
                raise Exception(
                    f"Access denied while listing environment profiles in domain {domain_identifier}"
                )
            elif error_code == "ResourceNotFoundException":
                logger.error(
                    f"Domain {domain_identifier} not found while listing environment profiles"
                )
                raise Exception(
                    f"Domain {domain_identifier} not found while listing environment profiles"
                )
            elif error_code == "ValidationException":
                logger.error(
                    f"Invalid parameters for listing environment profiles in domain {domain_identifier}"
                )
                raise Exception(
                    f"Invalid parameters for listing environment profiles in domain {domain_identifier}"
                )
            else:
                logger.error(
                    f"Error listing environment profiles in domain {domain_identifier}: {str(e)}"
                )
                raise Exception(
                    f"Error listing environment profiles in domain {domain_identifier}: {str(e)}"
                )
        except Exception as e:
            logger.error(
                f"Unexpected error listing environment profiles in domain {domain_identifier}: {str(e)}"
            )
            raise Exception(
                f"Unexpected error listing environment profiles in domain {domain_identifier}: {str(e)}"
            )

    # Return the decorated functions for testing purposes
    return {
        # "create_environment": create_environment,
        "list_environments": list_environments,
        "create_connection": create_connection,
        # "delete_connection": delete_connection,
        "get_connection": get_connection,
        "get_environment": get_environment,
        "get_environment_blueprint": get_environment_blueprint,
        "get_environment_blueprint_configuration": get_environment_blueprint_configuration,
        # "get_environment_credentials": get_environment_credentials,
        "list_connections": list_connections,
        "list_environment_blueprints": list_environment_blueprints,
        "list_environment_blueprint_configurations": list_environment_blueprint_configurations,
        "list_environment_profiles": list_environment_profiles,
    }
