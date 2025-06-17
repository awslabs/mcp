"""Data management tools for Amazon DataZone."""

from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from .common import ClientError, datazone_client, logger


def register_tools(mcp: FastMCP):
    """Register data management tools with the MCP server."""

    @mcp.tool()
    async def get_asset(
        domain_identifier: str, asset_identifier: str, revision: Optional[str] = None
    ) -> Any:
        """
        Retrieves detailed information about a specific asset in Amazon DataZone.

        Args:
            domain_identifier (str): The ID of the domain containing the asset
            asset_identifier (str): The ID of the asset to retrieve
            revision (str, optional): The specific revision of the asset to retrieve

        Returns:
            Any: The API response containing asset details including:
                - Basic info (name, description, ID)
                - Creation timestamps (createdAt, firstRevisionCreatedAt)
                - Domain and project IDs
                - Asset type and revision info
                - Forms and metadata
                - Glossary terms
                - Listing status
                - Time series data points
        """
        try:
            # Prepare the request parameters
            params = {"domainIdentifier": domain_identifier, "identifier": asset_identifier}

            # Add optional revision if provided
            if revision:
                params["revision"] = revision

            response = datazone_client.get_asset(**params)
            return response
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "AccessDeniedException":
                logger.error(
                    f"Access denied while getting asset {asset_identifier} in domain {domain_identifier}"
                )
                raise Exception(
                    f"Access denied while getting asset {asset_identifier} in domain {domain_identifier}"
                )
            elif error_code == "InternalServerException":
                logger.error(
                    f"Unknown error, exception or failure while getting asset {asset_identifier} in domain {domain_identifier}"
                )
                raise Exception(
                    f"Unknown error, exception or failure while getting asset {asset_identifier} in domain {domain_identifier}"
                )
            elif error_code == "ResourceNotFoundException":
                logger.error(
                    f"Data asset {asset_identifier} not found in domain {domain_identifier}"
                )
                raise Exception(
                    f"Data asset {asset_identifier} or domain {domain_identifier} not found"
                )
            elif error_code == "ThrottlingException":
                logger.error(
                    f"Request throttled while getting asset {asset_identifier} in domain {domain_identifier}"
                )
                raise Exception(
                    f"Request throttled while getting asset {asset_identifier} in domain {domain_identifier}"
                )
            elif error_code == "UnauthorizedException":
                logger.error(
                    f"Unauthorized to get asset {asset_identifier} in domain {domain_identifier}"
                )
                raise Exception(
                    f"Unauthorized to get asset {asset_identifier} in domain {domain_identifier}"
                )
            elif error_code == "ValidationException":
                logger.error(
                    f"Invalid input while getting asset {asset_identifier} in domain {domain_identifier}"
                )
                raise Exception(
                    f"Invalid input while getting asset {asset_identifier} in domain {domain_identifier}"
                )
            else:
                raise Exception(
                    f"Error getting asset {asset_identifier} in domain {domain_identifier}"
                )
        except Exception as e:
            raise Exception(
                f"Unexpected error getting asset {asset_identifier} in domain {domain_identifier}"
            )

    @mcp.tool()
    async def create_asset(
        domain_identifier: str,
        name: str,
        type_identifier: str,
        owning_project_identifier: str,
        description: Optional[str] = None,
        external_identifier: Optional[str] = None,
        forms_input: Optional[List[Dict[str, str]]] = None,
        glossary_terms: Optional[List[str]] = None,
        prediction_configuration: Optional[Dict[str, Dict[str, bool]]] = None,
        type_revision: Optional[str] = None,
        client_token: Optional[str] = None,
    ) -> Any:
        """
        Creates an asset in the Amazon DataZone catalog.

        Args:
            domain_identifier (str): The ID of the domain where the asset is created
            name (str): The name of the asset (1-256 characters)
            type_identifier (str): The ID of the asset type (1-513 characters)
            owning_project_identifier (str): The ID of the project that owns this asset
            description (str, optional): Description of the asset (0-2048 characters)
            external_identifier (str, optional): External ID of the asset (1-600 characters)
            forms_input (List[Dict[str, str]], optional): Metadata forms for the asset
                Example: [{
                    "content": "form-content",
                    "formName": "form-name",
                    "typeIdentifier": "type-id",
                    "typeRevision": "type-rev"
                }]
            glossary_terms (List[str], optional): Glossary terms to attach to the asset
                Example: ["term1", "term2"]
            prediction_configuration (Dict[str, Dict[str, bool]], optional): Configuration for business name generation
                Example: {"businessNameGeneration": {"enabled": True}}
            type_revision (str, optional): The revision of the asset type
            client_token (str, optional): Token for idempotency

        Returns:
            Any: The API response containing:
                - Asset ID and revision
                - Creation timestamps
                - Domain and project IDs
                - Forms and metadata
                - Glossary terms
                - Listing status
                - Time series data points
        """
        try:
            # Prepare the request parameters
            params: Dict[str, Any] = {
                "domainIdentifier": domain_identifier,
                "name": name,
                "typeIdentifier": type_identifier,
                "owningProjectIdentifier": owning_project_identifier,
            }

            # Add optional parameters if provided
            if description:
                params["description"] = description
            if external_identifier:
                params["externalIdentifier"] = external_identifier
            if forms_input:
                params["formsInput"] = forms_input
            if glossary_terms:
                params["glossaryTerms"] = glossary_terms
            if prediction_configuration:
                params["predictionConfiguration"] = prediction_configuration
            if type_revision:
                params["typeRevision"] = type_revision
            if client_token:
                params["clientToken"] = client_token

            response = datazone_client.create_asset(**params)
            return response
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "AccessDeniedException":
                logger.error(f"Access denied while creating asset in domain {domain_identifier}")
                raise Exception(f"Access denied while creating asset in domain {domain_identifier}")
            elif error_code == "InternalServerException":
                logger.error(
                    f"Unknown error, exception or failure while creating asset in domain {domain_identifier}"
                )
                raise Exception(
                    f"Unknown error, exception or failure while creating asset in domain {domain_identifier}"
                )
            elif error_code == "ResourceNotFoundException":
                logger.error(f"Domain {domain_identifier} not found")
                raise Exception(f"Domain {domain_identifier} not found")
            elif error_code == "ThrottlingException":
                logger.error(
                    f"Request throttled while creating asset in domain {domain_identifier}"
                )
                raise Exception(
                    f"Request throttled while creating asset in domain {domain_identifier}"
                )
            elif error_code == "UnauthorizedException":
                logger.error(f"Unauthorized to create asset in domain {domain_identifier}")
                raise Exception(f"Unauthorized to create asset in domain {domain_identifier}")
            elif error_code == "ValidationException":
                logger.error(f"Invalid input while creating asset in domain {domain_identifier}")
                raise Exception(f"Invalid input while creating asset in domain {domain_identifier}")
            elif error_code == "ConflictException":
                logger.error(
                    f"There is a conflict while creating asset in domain {domain_identifier}"
                )
                raise Exception(
                    f"There is a conflict while creating asset in domain {domain_identifier}"
                )
            else:
                raise Exception(f"Error creating asset in domain {domain_identifier}")
        except Exception as e:
            raise Exception(f"Unexpected error creating asset in domain {domain_identifier}")

    # @mcp.tool()
    # async def delete_asset(
    #     domain_identifier: str,
    #     asset_identifier: str
    # ) -> Any:
    #     """
    #     Deletes an asset in Amazon DataZone. This operation removes the specified asset from the given domain.
    #     No request body is required.

    #     This is specifically used for asset deletion in the Amazon DataZone MCP server.

    #     Args:
    #         domain_identifier (str): The ID of the Amazon DataZone domain in which the asset resides.
    #             Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
    #             Required: Yes

    #         identifier (str): The identifier of the asset to be deleted.
    #             Pattern: ^[a-zA-Z0-9_-]{1,36}$
    #             Required: Yes

    #     Returns:
    #         None: If successful, the service returns HTTP status code 204 (No Content) with an empty response body.
    #     """
    #     try:
    #         # Prepare the request parameters
    #         params = {
    #             "domainIdentifier": domain_identifier,
    #             "identifier": asset_identifier
    #         }
    #         response = datazone_client.delete_asset(**params)
    #         return response
    #     except ClientError as e:
    #         error_code = e.response['Error']['Code']
    #         if error_code == 'AccessDeniedException':
    #             logger.error(f"Access denied while deleting asset {asset_identifier} in domain {domain_identifier}")
    #             raise Exception(f"Access denied while deleting asset {asset_identifier} in domain {domain_identifier}")
    #         elif error_code == 'InternalServerException':
    #             logger.error(f"Unknown error, exception or failure while getdeletingting asset {asset_identifier} in domain {domain_identifier}")
    #             raise Exception(f"Unknown error, exception or failure while deleting asset {asset_identifier} in domain {domain_identifier}")
    #         elif error_code == 'ResourceNotFoundException':
    #             logger.error(f"Data asset {asset_identifier} not found in domain {domain_identifier}")
    #             raise Exception(f"Data asset {asset_identifier} or domain {domain_identifier} not found")
    #         elif error_code == 'ThrottlingException':
    #             logger.error(f"Request throttled while deleting asset {asset_identifier} in domain {domain_identifier}")
    #             raise Exception(f"Request throttled while deleting asset {asset_identifier} in domain {domain_identifier}")
    #         elif error_code == 'UnauthorizedException':
    #             logger.error(f"Unauthorized to delete asset {asset_identifier} in domain {domain_identifier}")
    #             raise Exception(f"Unauthorized to delete asset {asset_identifier} in domain {domain_identifier}")
    #         elif error_code == 'ValidationException':
    #             logger.error(f"Invalid input while deleting asset {asset_identifier} in domain {domain_identifier}")
    #             raise Exception(f"Invalid input while deleting asset {asset_identifier} in domain {domain_identifier}")
    #         else:
    #             raise Exception(f"Error deleting asset {asset_identifier} in domain {domain_identifier}")
    #     except Exception as e:
    #         raise Exception(f"Unexpected error deleting asset {asset_identifier} in domain {domain_identifier}")

    @mcp.tool()
    async def publish_asset(
        domain_identifier: str,
        asset_identifier: str,
        revision: Optional[str] = None,
        client_token: Optional[str] = None,
    ) -> Any:
        """
        Publishes an asset to the Amazon DataZone catalog.

        Args:
            domain_identifier (str): The ID of the domain containing the asset
            asset_identifier (str): The ID of the asset to publish

            revision (str, optional): The specific revision of the asset to publish
            client_token (str, optional): Token for idempotency

        Returns:
            Any: The API response containing:
                - Published asset ID and revision
                - Listing status
                - Creation and update timestamps
                - Domain and project IDs
                - Forms and metadata
                - Glossary terms
        """
        try:
            # Prepare the request parameters
            params = {"domainIdentifier": domain_identifier, "identifier": asset_identifier}

            # Add optional parameters if provided
            if revision:
                params["revision"] = revision
            if client_token:
                params["clientToken"] = client_token

            response = datazone_client.publish_asset(**params)
            return response
        except ClientError as e:
            raise Exception(
                f"Error publishing asset {asset_identifier} in domain {domain_identifier}: {e}"
            )

    # @mcp.tool()
    # async def get_asset_filter(
    #     domain_identifier: str,
    #     asset_identifier: str,
    #     identifier: str
    # ) -> Any:
    #     """
    #     Retrieves details of a specific asset filter for a data asset in Amazon DataZone.

    #     This operation uses URI parameters to identify the domain, asset, and asset filter. It returns metadata and configuration of the specified asset filter. The request does not contain a body.

    #     Args:
    #         asset_identifier (str): The ID of the data asset.
    #             Pattern: ^[a-zA-Z0-9_-]{1,36}$
    #         domain_identifier (str): The ID of the domain where the asset filter exists.
    #             Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
    #         identifier (str): The ID of the asset filter.
    #             Pattern: ^[a-zA-Z0-9_-]{1,36}$

    #     Returns:
    #         dict: A dictionary containing details about the asset filter, including:
    #             - assetId (str): ID of the data asset
    #             - configuration (dict): Configuration of the asset filter (union type)
    #             - createdAt (int): Timestamp of when the filter was created
    #             - description (str): Description of the filter (max 2048 chars)
    #             - domainId (str): ID of the domain
    #             - effectiveColumnNames (List[str]): Column names used in the filter
    #             - effectiveRowFilter (str): Row filter expression
    #             - errorMessage (str): Error message if applicable
    #             - id (str): ID of the asset filter
    #             - name (str): Name of the asset filter
    #                 Pattern: ^[\w -]+$
    #                 Length: 1–64 characters
    #             - status (str): Status of the filter (VALID | INVALID)
    #     """
    #     try:
    #         # Prepare the request parameters
    #         params = {
    #             "domainIdentifier": domain_identifier,
    #             "assetIdentifier": asset_identifier,
    #             "identifier": identifier
    #         }

    #         response = datazone_client.get_asset_filter(**params)
    #         return response
    #     except ClientError as e:
    #         error_code = e.response['Error']['Code']
    #         if error_code == 'AccessDeniedException':
    #             logger.error(f"Access denied while getting asset {asset_identifier}'s filter {identifier} in domain {domain_identifier}")
    #             raise Exception(f"Access denied while getting asset {asset_identifier}'s filter {identifier} in domain {domain_identifier}")
    #         elif error_code == 'InternalServerException':
    #             logger.error(f"Unknown error, exception or failure while getting asset {asset_identifier}'s filter {identifier} in domain {domain_identifier}")
    #             raise Exception(f"Unknown error, exception or failure while getting asset {asset_identifier}'s filter {identifier} in domain {domain_identifier}")
    #         elif error_code == 'ResourceNotFoundException':
    #             logger.error(f"Data asset {asset_identifier} or filter {identifier} not found in domain {domain_identifier}")
    #             raise Exception(f"Data asset {asset_identifier} or filter {identifier} or domain {domain_identifier} not found")
    #         elif error_code == 'ThrottlingException':
    #             logger.error(f"Request throttled while getting asset {asset_identifier}'s filter {identifier} in domain {domain_identifier}")
    #             raise Exception(f"Request throttled while getting asset {asset_identifier}'s filter {identifier} in domain {domain_identifier}")
    #         elif error_code == 'UnauthorizedException':
    #             logger.error(f"Unauthorized to get asset {asset_identifier}'s filter {identifier} in domain {domain_identifier}")
    #             raise Exception(f"Unauthorized to get asset {asset_identifier}'s filter {identifier} in domain {domain_identifier}")
    #         elif error_code == 'ValidationException':
    #             logger.error(f"Invalid input while getting asset {asset_identifier}'s filter {identifier} in domain {domain_identifier}")
    #             raise Exception(f"Invalid input while getting asset {asset_identifier}'s filter {identifier} in domain {domain_identifier}")
    #         else:
    #             raise Exception(f"Error getting asset {asset_identifier}'s filter {identifier} in domain {domain_identifier}")
    #     except Exception as e:
    #         raise Exception(f"Unexpected error getting asset {asset_identifier}'s filter {identifier} in domain {domain_identifier}")

    # @mcp.tool()
    # async def list_asset_filters(
    #     domain_identifier: str,
    #     asset_identifier: str,
    #     max_result: int = 50,
    #     next_token: str = None,
    #     status: str = None
    # ) -> Any:
    #     """
    #     Retrieves details of a specific asset filter for a data asset in Amazon DataZone.

    #     This operation uses URI parameters to identify the domain, asset, and asset filter. It returns metadata and configuration of the specified asset filter. The request does not contain a body.

    #     Args:
    #         asset_identifier (str): The ID of the data asset.
    #             Pattern: ^[a-zA-Z0-9_-]{1,36}$
    #         domain_identifier (str): The ID of the domain where the asset filter exists.
    #             Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
    #         identifier (str): The ID of the asset filter.
    #             Pattern: ^[a-zA-Z0-9_-]{1,36}$

    #     Returns:
    #         dict: A dictionary containing details about the asset filter, including:
    #             - assetId (str): ID of the data asset
    #             - configuration (dict): Configuration of the asset filter (union type)
    #             - createdAt (int): Timestamp of when the filter was created
    #             - description (str): Description of the filter (max 2048 chars)
    #             - domainId (str): ID of the domain
    #             - effectiveColumnNames (List[str]): Column names used in the filter
    #             - effectiveRowFilter (str): Row filter expression
    #             - errorMessage (str): Error message if applicable
    #             - id (str): ID of the asset filter
    #             - name (str): Name of the asset filter
    #                 Pattern: ^[\w -]+$
    #                 Length: 1–64 characters
    #             - status (str): Status of the filter (VALID | INVALID)
    #     """
    #     try:
    #         # Prepare the request parameters
    #         params = {
    #             "domainIdentifier": domain_identifier,
    #             "assetIdentifier": asset_identifier,
    #             "maxResults": min(50, max_result)
    #         }
    #         if next_token:
    #             params["nextToken"] = next_token
    #         valid_status = ["VALID", "INVALID"]
    #         if status:
    #             if status not in valid_status:
    #                 raise ValueError(f"status must be one of {valid_status}")
    #             params["status"] = status
    #         response = datazone_client.list_asset_filters(**params)
    #         return response
    #     except ClientError as e:
    #         error_code = e.response['Error']['Code']
    #         if error_code == 'AccessDeniedException':
    #             logger.error(f"Access denied while getting asset {asset_identifier} filters in domain {domain_identifier}")
    #             raise Exception(f"Access denied while getting asset {asset_identifier} filters in domain {domain_identifier}")
    #         elif error_code == 'InternalServerException':
    #             logger.error(f"Unknown error, exception or failure while getting asset {asset_identifier} filtes in domain {domain_identifier}")
    #             raise Exception(f"Unknown error, exception or failure while getting asset {asset_identifier} filters in domain {domain_identifier}")
    #         elif error_code == 'ResourceNotFoundException':
    #             logger.error(f"Data asset {asset_identifier} not found in domain {domain_identifier}")
    #             raise Exception(f"Data asset {asset_identifier} or domain {domain_identifier} not found")
    #         elif error_code == 'ThrottlingException':
    #             logger.error(f"Request throttled while getting asset {asset_identifier} filtes in domain {domain_identifier}")
    #             raise Exception(f"Request throttled while getting asset {asset_identifier} filters in domain {domain_identifier}")
    #         elif error_code == 'UnauthorizedException':
    #             logger.error(f"Unauthorized to get asset {asset_identifier} filters in domain {domain_identifier}")
    #             raise Exception(f"Unauthorized to get asset {asset_identifier} filters in domain {domain_identifier}")
    #         elif error_code == 'ValidationException':
    #             logger.error(f"Invalid input while getting asset {asset_identifier} filters in domain {domain_identifier}")
    #             raise Exception(f"Invalid input while getting asset {asset_identifier} filters in domain {domain_identifier}")
    #         else:
    #             raise Exception(f"Error getting asset {asset_identifier} filters in domain {domain_identifier}")
    #     except Exception as e:
    #         raise Exception(f"Unexpected error getting asset {asset_identifier} filters in domain {domain_identifier}")

    # @mcp.tool()
    # async def get_asset_type(
    #     domain_identifier: str,
    #     identifier: str,
    #     revision: str = None
    # ) -> Any:
    #     """
    #     Retrieves details about a specific asset type revision in an Amazon DataZone domain.

    #     This operation identifies the asset type by its domain, identifier, and optional revision. It returns metadata including creation and update details, ownership, and form configurations.

    #     Args:
    #         domain_identifier (str): The ID of the Amazon DataZone domain containing the asset type.
    #             Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
    #             Required: Yes
    #         identifier (str): The unique identifier of the asset type.
    #             Length: 1–513 characters
    #             Pattern: ^(?!\.)[\w\.]*\w$
    #             Required: Yes
    #         revision (str, optional): The revision of the asset type.
    #             Length: 1–64 characters

    #     Returns:
    #         dict: A dictionary containing metadata about the asset type, including:
    #             - createdAt (int): Timestamp of when the asset type was created
    #             - createdBy (str): The user who created the asset type
    #             - description (str): Description of the asset type (up to 2048 characters)
    #             - domainId (str): ID of the domain containing the asset type
    #             - formsOutput (dict): A map of form names to form metadata:
    #                 - required (bool): Whether the form is required
    #                 - typeName (str): Name of the form type
    #                 - typeRevision (str): Revision of the form type
    #             - name (str): Name of the asset type (1–256 characters; must not contain periods)
    #             - originDomainId (str): ID of the domain where the asset type was originally created
    #             - originProjectId (str): ID of the project where the asset type was originally created
    #             - owningProjectId (str): ID of the project that currently owns the asset type
    #             - revision (str): The revision string of the asset type
    #             - updatedAt (int): Timestamp of when the asset type was last updated
    #             - updatedBy (str): The user who last updated the asset type
    #     """
    #     try:
    #         # Prepare the request parameters
    #         params = {
    #             "domainIdentifier": domain_identifier,
    #             "identifier": identifier
    #         }

    #         # Add optional revision if provided
    #         if revision:
    #             params["revision"] = revision

    #         response = datazone_client.get_asset_type(**params)
    #         return response
    #     except ClientError as e:
    #         error_code = e.response['Error']['Code']
    #         if error_code == 'AccessDeniedException':
    #             logger.error(f"Access denied while getting asset type {identifier} in domain {domain_identifier}")
    #             raise Exception(f"Access denied while getting asset type {identifier} in domain {domain_identifier}")
    #         elif error_code == 'InternalServerException':
    #             logger.error(f"Unknown error, exception or failure while getting asset type {identifier} in domain {domain_identifier}")
    #             raise Exception(f"Unknown error, exception or failure while getting asset type {identifier} in domain {domain_identifier}")
    #         elif error_code == 'ResourceNotFoundException':
    #             logger.error(f"Data asset type {identifier} not found in domain {domain_identifier}")
    #             raise Exception(f"Data asset type {identifier} or domain {domain_identifier} not found")
    #         elif error_code == 'ThrottlingException':
    #             logger.error(f"Request throttled while getting asset type {identifier} in domain {domain_identifier}")
    #             raise Exception(f"Request throttled while getting asset type {identifier} in domain {domain_identifier}")
    #         elif error_code == 'UnauthorizedException':
    #             logger.error(f"Unauthorized to get asset type {identifier} in domain {domain_identifier}")
    #             raise Exception(f"Unauthorized to get asset type {identifier} in domain {domain_identifier}")
    #         elif error_code == 'ValidationException':
    #             logger.error(f"Invalid input while getting asset type {identifier} in domain {domain_identifier}")
    #             raise Exception(f"Invalid input while getting asset type {identifier} in domain {domain_identifier}")
    #         else:
    #             raise Exception(f"Error getting asset type {identifier} in domain {domain_identifier}")
    #     except Exception as e:
    #         raise Exception(f"Unexpected error getting asset type {identifier} in domain {domain_identifier}")

    @mcp.tool()
    async def get_listing(
        domain_identifier: str, identifier: str, listing_revision: Optional[str] = None
    ) -> Any:
        """
        Gets a listing (a record of an asset at a given time) in Amazon DataZone.

        If a listing version is specified, only details specific to that version are returned.

        Args:
            domain_identifier (str): The ID of the Amazon DataZone domain
                Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
            identifier (str): The ID of the listing
                Pattern: ^[a-zA-Z0-9_-]{1,36}$
            listing_revision (str, optional): The revision of the listing
                Length: 1-64 characters

        Returns:
            Any: The API response containing:
                - Listing ID and revision
                - Creation and update timestamps
                - Domain ID
                - Listing name and description
                - Listing status (CREATING | ACTIVE | INACTIVE)
                - Listing item details
                - Creator and updater information
        """
        try:
            # Prepare the request parameters
            params = {"domainIdentifier": domain_identifier, "identifier": identifier}

            # Add optional parameters if provided
            if listing_revision:
                params["listingRevision"] = listing_revision

            response = datazone_client.get_listing(**params)
            return response
        except ClientError as e:
            raise Exception(
                f"Error getting listing {identifier} in domain {domain_identifier}: {e}"
            )

    @mcp.tool()
    async def search_listings(
        domain_identifier: str,
        search_text: Optional[str] = None,
        max_results: int = 50,
        next_token: Optional[str] = None,
        additional_attributes: Optional[List[str]] = None,
        search_in: Optional[List[Dict[str, str]]] = None,
        sort: Optional[Dict[str, str]] = None,
    ) -> Any:
        """
        Searches listings (records of assets) in Amazon DataZone with various filtering and sorting options.

        Args:
            domain_identifier (str): The ID of the domain to search in
            search_text (str, optional): Text to search for
            max_results (int, optional): Maximum number of results to return (1-50, default: 50)
            next_token (str, optional): Token for pagination
            additional_attributes (List[str], optional): Additional attributes to include in search
                Valid values: ["FORMS", "TIME_SERIES_DATA_POINT_FORMS"]
            search_in (List[Dict[str, str]], optional): Attributes to search in
                Example: [{"attribute": "name"}, {"attribute": "description"}]
            sort (Dict[str, str], optional): Sorting criteria
                Example: {"attribute": "name", "order": "ASCENDING"}

        Returns:
            Any: The API response containing search results
        """
        try:
            # Prepare the request parameters
            params = {
                "domainIdentifier": domain_identifier,
                "maxResults": min(max_results, 50),  # Ensure maxResults is within valid range
            }

            # Add optional parameters if provided
            if search_text:
                params["searchText"] = search_text
            if next_token:
                params["nextToken"] = next_token
            if additional_attributes:
                params["additionalAttributes"] = additional_attributes
            if search_in:
                params["searchIn"] = search_in
            if sort:
                params["sort"] = sort

            response = datazone_client.search_listings(**params)
            return response
        except ClientError as e:
            raise Exception(f"Error searching listings in domain {domain_identifier}: {e}")

    @mcp.tool()
    async def create_data_source(
        domain_identifier: str,
        project_identifier: str,
        name: str,
        data_src_type: str,
        description: Optional[str] = None,
        enable_setting: str = "ENABLED",
        environment_identifier: Optional[str] = None,
        connection_identifier: Optional[str] = None,
        configuration: Optional[Dict[str, Any]] = None,
        asset_forms_input: Optional[List[Dict[str, str]]] = None,
        publish_on_import: bool = False,
        recommendation: Optional[Dict[str, bool]] = None,
        schedule: Optional[Dict[str, str]] = None,
        client_token: Optional[str] = None,
    ) -> Any:
        """
        Creates a data source in Amazon DataZone and associates it with a project.

        Args:
            domain_identifier (str): The ID of the domain where the data source is created
            project_identifier (str): The ID of the project to associate the data source with
            name (str): The name of the data source (1-256 characters)
            data_src_type (str): The type of data source (e.g., "S3", "GLUE", "REDSHIFT")
            description (str, optional): Description of the data source (0-2048 characters)
            enable_setting (str, optional): Whether the data source is enabled (ENABLED/DISABLED)
            environment_identifier (str, optional): ID of the environment to publish assets to
            connection_identifier (str, optional): ID of the connection to use
            configuration (Dict[str, Any], optional): Data source configuration
                Example for S3: {
                    "s3Configuration": {
                        "bucketName": "my-bucket",
                        "prefix": "data/"
                    }
                }
            asset_forms_input (List[Dict[str, str]], optional): Metadata forms for assets
                Example: [{
                    "content": "form-content",
                    "formName": "form-name",
                    "typeIdentifier": "type-id",
                    "typeRevision": "type-rev"
                }]
            publish_on_import (bool, optional): Whether to automatically publish imported assets
            recommendation (Dict[str, bool], optional): Recommendation settings
                Example: {"enableBusinessNameGeneration": True}
            schedule (Dict[str, str], optional): Schedule configuration
                Example: {
                    "schedule": "cron(0 12 * * ? *)",
                    "timezone": "UTC"
                }
            client_token (str, optional): Token for idempotency

        Returns:
            Any: The API response containing:
                - Data source ID and status
                - Creation and update timestamps
                - Domain and project IDs
                - Configuration details
                - Last run information
                - Error messages (if any)
        """
        try:
            # Prepare the request parameters
            params = {
                "domainIdentifier": domain_identifier,
                "projectIdentifier": project_identifier,
                "name": name,
                "type": data_src_type,
                "enableSetting": enable_setting,
                "publishOnImport": publish_on_import,
            }

            # Add optional parameters if provided
            if description:
                params["description"] = description
            if environment_identifier:
                params["environmentIdentifier"] = environment_identifier
            if connection_identifier:
                params["connectionIdentifier"] = connection_identifier
            if configuration:
                params["configuration"] = configuration
            if asset_forms_input:
                params["assetFormsInput"] = asset_forms_input
            if recommendation:
                params["recommendation"] = recommendation
            if schedule:
                params["schedule"] = schedule
            if client_token:
                params["clientToken"] = client_token

            response = datazone_client.create_data_source(**params)
            return response
        except ClientError as e:
            raise Exception(f"Error creating data source in domain {domain_identifier}: {e}")

    @mcp.tool()
    async def get_data_source(domain_identifier: str, identifier: str) -> Any:
        """
        Retrieves detailed information about a specific data source in Amazon DataZone.

        Args:
            domain_identifier (str): The ID of the domain where the data source exists
            identifier (str): The ID of the data source to retrieve

        Returns:
            Any: The API response containing data source details
        """
        try:
            response = datazone_client.get_data_source(
                domainIdentifier=domain_identifier, identifier=identifier
            )
            return response
        except ClientError as e:
            raise Exception(f"Error getting data source {identifier}: {e}")

    # @mcp.tool()
    # async def get_time_series_data_point(
    #     domain_identifier: str,
    #     entity_identifier: str,
    #     entity_type: str,
    #     form_name: str,
    #     identifier: str
    # ) -> Any:
    #     """
    #     Retrieves detailed information about a specific data source in Amazon DataZone.

    #     Args:
    #         domain_identifier (str): The ID of the domain where the data source exists
    #         identifier (str): The ID of the data source to retrieve

    #     Returns:
    #         Any: The API response containing data source details
    #     """
    #     try:
    #         valid_types = ["ASSET", "LISTING"]
    #         if entity_type not in valid_types:
    #             raise ValueError(f"entity_type must be one of {valid_types}")
    #         params = {
    #             "domainIdentifier": domain_identifier,
    #             "identifier": identifier,
    #             "entityIdentifier": entity_identifier,
    #             "entityType": entity_type,
    #             "formName": form_name
    #         }
    #         response = datazone_client.get_time_series_data_point(**params)
    #         return response
    #     except ClientError as e:
    #         raise Exception(f"Error getting time series data point {identifier}: {e}")

    # @mcp.tool()
    # async def list_time_series_data_points(
    #     domain_identifier: str,
    #     entity_identifier: str,
    #     entity_type: str,
    #     form_name: str,
    #     max_results: int = 50,
    #     ended_at: int = None,
    #     next_token: str = None,
    #     started_at: int = None
    # ) -> Any:
    #     """
    #     Lists time series data points for a specified asset or listing in an Amazon DataZone domain.

    #     Args:
    #         domain_identifier (str): The ID of the Amazon DataZone domain housing the assets.
    #             Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
    #             Required.
    #         ended_at (int, optional): The timestamp indicating the end time of the data points to list.
    #         entity_identifier (str): The ID of the asset or listing for which to list data points.
    #             Pattern: ^[a-zA-Z0-9_-]{1,36}$
    #             Required.
    #         entity_type (str): The type of the asset or listing.
    #             Valid values: "ASSET" | "LISTING"
    #             Required.
    #         form_name (str): The name of the time series data points form.
    #             Length: 1 to 128 characters.
    #             Required.
    #         max_results (int, optional): Maximum number of data points to return in one call.
    #             Valid range: 1 to 50.
    #         next_token (str, optional): Pagination token for retrieving the next set of results.
    #             Length: 1 to 8192 characters.
    #         started_at (int, optional): The timestamp indicating the start time of the data points to list.

    #     Returns:
    #         Any: The API response containing:
    #             - items (list of dict): List of time series data point summaries, each containing:
    #                 - contentSummary (str)
    #                 - formName (str)
    #                 - id (str)
    #                 - timestamp (int)
    #                 - typeIdentifier (str)
    #                 - typeRevision (str)
    #             - nextToken (str): Pagination token for fetching the next page of results, if any.
    #     """
    #     try:
    #         valid_types = ["ASSET", "LISTING"]
    #         if entity_type not in valid_types:
    #             raise ValueError(f"entity_type must be one of {valid_types}")
    #         params = {
    #             "domainIdentifier": domain_identifier,
    #             "entityIdentifier": entity_identifier,
    #             "entityType": entity_type,
    #             "formName": form_name,
    #             "maxResults": min(50, max_results)
    #         }
    #         if ended_at:
    #             params["endedAt"] = ended_at
    #         if nex_token:
    #             params["nextToken"] = next_token
    #         if started_at:
    #             params["startedAt"] = started_at
    #         response = datazone_client.list_time_series_data_points(**params)
    #         return response
    #     except ClientError as e:
    #         raise Exception(f"Error listing time series data points: {e}")

    # @mcp.tool()
    # async def get_data_product(
    #     domain_identifier: str,
    #     identifier: str
    # ) -> Any:
    #     """
    #     Retrieves metadata and detailed information about a specific revision of a data product in Amazon DataZone.

    #     This request identifies the data product by domain, identifier, and optional revision. It returns metadata including creation information, form outputs, glossary terms, and associated data assets. No request body is required.

    #     Args:
    #         domain_identifier (str): The ID of the domain where the data product resides.
    #             Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
    #             Required: Yes
    #         identifier (str): The unique identifier of the data product.
    #             Pattern: ^[a-zA-Z0-9_-]{1,36}$
    #             Required: Yes
    #         revision (str, optional): The specific revision of the data product.
    #             Length: 1–64 characters

    #     Returns:
    #         dict: A dictionary containing the metadata and contents of the data product, including:
    #             - createdAt (int): Timestamp when the data product was created
    #             - createdBy (str): User who created the data product
    #             - description (str): Description of the data product (1–4096 characters)
    #             - domainId (str): ID of the domain where the product resides
    #             - firstRevisionCreatedAt (int): Timestamp of the first revision's creation
    #             - firstRevisionCreatedBy (str): User who created the first revision
    #             - formsOutput (List[dict]): List of metadata forms, each containing:
    #                 - content (str): Content of the form
    #                 - formName (str): Name of the form
    #                 - typeName (str): Name of the form type
    #                 - typeRevision (str): Revision of the form type
    #             - glossaryTerms (List[str]): Associated glossary terms
    #                 Pattern: ^[a-zA-Z0-9_-]{1,36}$
    #                 Min: 1, Max: 20 items
    #             - id (str): ID of the data product
    #                 Pattern: ^[a-zA-Z0-9_-]{1,36}$
    #             - items (List[dict]): List of data assets in the product, each with:
    #                 - glossaryTerms (List[str]): Glossary terms for the asset
    #                 - identifier (str): Asset identifier
    #                 - itemType (str): Type of the item
    #                 - revision (str): Revision of the item
    #             - name (str): Name of the data product (1–64 characters)
    #             - owningProjectId (str): ID of the owning project
    #                 Pattern: ^[a-zA-Z0-9_-]{1,36}$
    #             - revision (str): Revision string of the data product
    #             - status (str): Status of the data product
    #                 Valid values: "CREATED", "CREATING", "CREATE_FAILED"

    #     """
    #     try:
    #         params = {
    #             "domainIdentifier": domain_identifier,
    #             "identifier": identifier
    #         }
    #         response = datazone_client.get_data_product(**params)
    #         return response
    #     except ClientError as e:
    #         raise Exception(f"Error getting data product {identifier} in domain {domain_identifier}: {e}")

    # @mcp.tool()
    # async def get_lineage_node(
    #     domain_identifier: str,
    #     identifier: str,
    #     #TODO
    #     event_time_stamp: str
    # ) -> Any:
    #     """
    #     Retrieves detailed information about a specific data lineage node in Amazon DataZone.

    #     Args:
    #         domain_identifier (str): The ID of the domain in which the data lineage node exists.
    #         identifier (str): The ID or source identifier of the data lineage node to retrieve.
    #         event_timestamp (int): The event timestamp (Unix epoch in milliseconds) for which to retrieve the data lineage node.

    #     Returns:
    #         Any: The API response containing lineage node details including:
    #             - Timestamps (createdAt, updatedAt, eventTimestamp)
    #             - User info (createdBy, updatedBy)
    #             - Node metadata (name, description, sourceIdentifier, typeName, typeRevision)
    #             - Domain ID and node ID
    #             - Downstream and upstream node references (id, eventTimestamp)
    #             - Forms and metadata associated with the node
    #     """
    #     try:
    #         params = {
    #             "domainIdentifier": domain_identifier,
    #             "identifier": identifier
    #         }
    #         if event_time_stamp:
    #             params["eventTimeStamp"] = event_time_stamp
    #         response = datazone_client.get_lineage_node(**params)
    #         return response
    #     except ClientError as e:
    #         raise Exception(f"Error getting data lineage node {identifier} in domain {domain_identifier}: {e}")

    @mcp.tool()
    async def start_data_source_run(
        domain_identifier: str, data_source_identifier: str, client_token: Optional[str] = None
    ) -> Any:
        """
        Starts a data source run in Amazon DataZone.

        Args:
            domain_identifier (str): The identifier of the Amazon DataZone domain in which to start a data source run
                Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
            data_source_identifier (str): The identifier of the data source
                Pattern: ^[a-zA-Z0-9_-]{1,36}$
            client_token (str, optional): A unique, case-sensitive identifier that is provided to ensure the idempotency of the request
                Length: 1-128 characters

        Returns:
            Any: The API response containing:
                - createdAt: Timestamp when the data source run was created
                - dataSourceConfigurationSnapshot: Configuration snapshot of the data source
                - dataSourceId: Identifier of the data source
                - domainId: Identifier of the domain
                - errorMessage: Error details if the operation failed
                - id: Identifier of the data source run
                - projectId: Identifier of the project
                - runStatisticsForAssets: Statistics about the run including:
                    - added: Number of assets added
                    - failed: Number of assets that failed
                    - skipped: Number of assets skipped
                    - unchanged: Number of assets unchanged
                    - updated: Number of assets updated
                - startedAt: Timestamp when the run started
                - status: Status of the run (REQUESTED, RUNNING, FAILED, PARTIALLY_SUCCEEDED, SUCCESS)
                - stoppedAt: Timestamp when the run stopped
                - type: Type of the run (PRIORITIZED, SCHEDULED)
                - updatedAt: Timestamp when the run was last updated

        Example:
            ```python
            response = await start_data_source_run(
                domain_identifier="dzd-1234567890",
                data_source_identifier="ds-1234567890",
                client_token="unique-token-123"
            )
            ```
        """
        try:
            # Prepare the request parameters
            params = {
                "domainIdentifier": domain_identifier,
                "dataSourceIdentifier": data_source_identifier,
            }

            # Add optional client_token if provided
            if client_token:
                params["clientToken"] = client_token

            response = datazone_client.start_data_source_run(**params)
            return response
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "AccessDeniedException":
                raise Exception(
                    f"Access denied while starting data source run for {data_source_identifier} in domain {domain_identifier}"
                )
            elif error_code == "ConflictException":
                raise Exception(
                    f"Conflict while starting data source run for {data_source_identifier} in domain {domain_identifier}"
                )
            elif error_code == "InternalServerException":
                raise Exception(
                    f"Internal server error while starting data source run for {data_source_identifier} in domain {domain_identifier}"
                )
            elif error_code == "ResourceNotFoundException":
                raise Exception(
                    f"Data source {data_source_identifier} or domain {domain_identifier} not found"
                )
            elif error_code == "ServiceQuotaExceededException":
                raise Exception(
                    f"Service quota exceeded while starting data source run for {data_source_identifier} in domain {domain_identifier}"
                )
            elif error_code == "ThrottlingException":
                raise Exception(
                    f"Request throttled while starting data source run for {data_source_identifier} in domain {domain_identifier}"
                )
            elif error_code == "UnauthorizedException":
                raise Exception(
                    f"Unauthorized to start data source run for {data_source_identifier} in domain {domain_identifier}"
                )
            elif error_code == "ValidationException":
                raise Exception(
                    f"Invalid input while starting data source run for {data_source_identifier} in domain {domain_identifier}"
                )
            else:
                raise Exception(
                    f"Error starting data source run for {data_source_identifier} in domain {domain_identifier}: {str(e)}"
                )
        except Exception as e:
            raise Exception(
                f"Unexpected error starting data source run for {data_source_identifier} in domain {domain_identifier}: {str(e)}"
            )

    # @mcp.tool()
    # async def get_job_run(
    #     domain_identifier: str,
    #     identifier: str
    # ) -> Any:
    #     """
    #     Starts a data source run in Amazon DataZone.

    #     Args:
    #         domain_identifier (str): The identifier of the Amazon DataZone domain in which to start a data source run
    #             Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
    #         data_source_identifier (str): The identifier of the data source
    #             Pattern: ^[a-zA-Z0-9_-]{1,36}$
    #         client_token (str, optional): A unique, case-sensitive identifier that is provided to ensure the idempotency of the request
    #             Length: 1-128 characters

    #     Returns:
    #         Any: The API response containing:
    #             - createdAt: Timestamp when the data source run was created
    #             - dataSourceConfigurationSnapshot: Configuration snapshot of the data source
    #             - dataSourceId: Identifier of the data source
    #             - domainId: Identifier of the domain
    #             - errorMessage: Error details if the operation failed
    #             - id: Identifier of the data source run
    #             - projectId: Identifier of the project
    #             - runStatisticsForAssets: Statistics about the run including:
    #                 - added: Number of assets added
    #                 - failed: Number of assets that failed
    #                 - skipped: Number of assets skipped
    #                 - unchanged: Number of assets unchanged
    #                 - updated: Number of assets updated
    #             - startedAt: Timestamp when the run started
    #             - status: Status of the run (REQUESTED, RUNNING, FAILED, PARTIALLY_SUCCEEDED, SUCCESS)
    #             - stoppedAt: Timestamp when the run stopped
    #             - type: Type of the run (PRIORITIZED, SCHEDULED)
    #             - updatedAt: Timestamp when the run was last updated

    #     Example:
    #         ```python
    #         response = await start_data_source_run(
    #             domain_identifier="dzd-1234567890",
    #             data_source_identifier="ds-1234567890",
    #             client_token="unique-token-123"
    #         )
    #         ```
    #     """
    #     try:
    #         # Prepare the request parameters
    #         params = {
    #             "domainIdentifier": domain_identifier,
    #             "identifier": identifier
    #         }

    #         response = datazone_client.get_job_run(**params)
    #         return response
    #     except ClientError as e:
    #         error_code = e.response['Error']['Code']
    #         if error_code == 'AccessDeniedException':
    #             raise Exception(f"Access denied while getting job run for {identifier} in domain {domain_identifier}")
    #         elif error_code == 'ConflictException':
    #             raise Exception(f"Conflict while getting job run for {identifier} in domain {domain_identifier}")
    #         elif error_code == 'InternalServerException':
    #             raise Exception(f"Internal server error while getting job run for {identifier} in domain {domain_identifier}")
    #         elif error_code == 'ResourceNotFoundException':
    #             raise Exception(f"Job run {identifier} or domain {domain_identifier} not found")
    #         elif error_code == 'ServiceQuotaExceededException':
    #             raise Exception(f"Service quota exceeded while getting job run for {identifier} in domain {domain_identifier}")
    #         elif error_code == 'ThrottlingException':
    #             raise Exception(f"Request throttled while getting job run for {identifier} in domain {domain_identifier}")
    #         elif error_code == 'UnauthorizedException':
    #             raise Exception(f"Unauthorized to get job run for {identifier} in domain {domain_identifier}")
    #         elif error_code == 'ValidationException':
    #             raise Exception(f"Invalid input while getting job run for {identifier} in domain {domain_identifier}")
    #         else:
    #             raise Exception(f"Error getting job run for {identifier} in domain {domain_identifier}: {str(e)}")
    #     except Exception as e:
    #         raise Exception(f"Unexpected error getting job run for {identifier} in domain {domain_identifier}: {str(e)}")

    # @mcp.tool()
    # async def list_job_runs(
    #     domain_identifier: str,
    #     job_identifier: str,
    #     max_results: int = 50,
    #     next_token: str = None,
    #     sort_order: str = None,
    #     status: str = None
    # ) -> Any:

    #     """
    #     Lists the job runs for a specified job in an Amazon DataZone domain.

    #     Args:
    #         domain_identifier (str): The ID of the domain where the job runs exist.
    #         job_identifier (str): The ID of the job whose runs are to be listed.
    #         max_results (int, optional): Maximum number of job runs to return (1–50).
    #         next_token (str, optional): Pagination token from a previous response to retrieve the next set of job runs.
    #         sort_order (str, optional): Sort order for the job runs. Valid values: "ASCENDING", "DESCENDING".
    #         status (str, optional): Filter by job run status. Valid values include:
    #             - "SCHEDULED"
    #             - "IN_PROGRESS"
    #             - "SUCCESS"
    #             - "PARTIALLY_SUCCEEDED"
    #             - "FAILED"
    #             - "ABORTED"
    #             - "TIMED_OUT"
    #             - "CANCELED"

    #     Returns:
    #         Any: The API response including:
    #             - A list of job run summaries (`items`), each with timestamps, status, and error info if applicable
    #             - A pagination token (`nextToken`) if more results are available
    #     """
    #     try:
    #         # Prepare the request parameters
    #         params = {
    #             "domainIdentifier": domain_identifier,
    #             "jobIdentifier": job_identifier,
    #             "maxResults": min(50, max_results)
    #         }
    #         if next_token:
    #             params["nextToken"] = next_token
    #         if sort_order:
    #             if sort_order not in ["ASCENDING", "DESCENDING"]:
    #                 raise ValueError("sort_order must be either 'ASCENDING' or 'DESCENDING'")
    #             params["sortOrder"] = sort_order
    #         if status:
    #             valid_types = ["SCHEDULED", "IN_PROGRESS", "SUCCESS", "PARTIALLY_SUCCEEDED", "FAILED", "ABORTED", "TIMED_OUT", "CANCELED"]
    #             if status not in valid_types:
    #                 raise ValueError(f"status must be one of {valid_types}")
    #             params["status"] = status

    #         response = datazone_client.list_job_runs(**params)
    #         return response
    #     except ClientError as e:
    #         error_code = e.response['Error']['Code']
    #         if error_code == 'AccessDeniedException':
    #             raise Exception(f"Access denied while listing job runs for {job_identifier} in domain {domain_identifier}")
    #         elif error_code == 'ConflictException':
    #             raise Exception(f"Conflict while listing job runs for {job_identifier} in domain {domain_identifier}")
    #         elif error_code == 'InternalServerException':
    #             raise Exception(f"Internal server error while listing job runs for {job_identifier} in domain {domain_identifier}")
    #         elif error_code == 'ResourceNotFoundException':
    #             raise Exception(f"Job {job_identifier} or domain {domain_identifier} not found")
    #         elif error_code == 'ServiceQuotaExceededException':
    #             raise Exception(f"Service quota exceeded while listing job runs for {job_identifier} in domain {domain_identifier}")
    #         elif error_code == 'ThrottlingException':
    #             raise Exception(f"Request throttled while listing job runs for {job_identifier} in domain {domain_identifier}")
    #         elif error_code == 'UnauthorizedException':
    #             raise Exception(f"Unauthorized to get job run for {job_identifier} in domain {domain_identifier}")
    #         elif error_code == 'ValidationException':
    #             raise Exception(f"Invalid input while listing job runs for {job_identifier} in domain {domain_identifier}")
    #         else:
    #             raise Exception(f"Error listing job runs for {job_identifier} in domain {domain_identifier}: {str(e)}")
    #     except Exception as e:
    #         raise Exception(f"Unexpected error listing job runs for {job_identifier} in domain {domain_identifier}: {str(e)}")

    @mcp.tool()
    async def create_subscription_request(
        domain_identifier: str,
        request_reason: str,
        subscribed_listings: List[Dict[str, str]],
        subscribed_principals: List[Dict[str, Any]],
        metadata_forms: Optional[List[Dict[str, str]]] = None,
        client_token: Optional[str] = None,
    ) -> Any:
        """
        Creates a subscription request in Amazon DataZone.

        Args:
            domain_identifier (str): The ID of the domain where the subscription request is created
            request_reason (str): The reason for the subscription request (1-4096 characters)
            subscribed_listings (List[Dict[str, str]]): The published assets to subscribe to
                Example: [{"identifier": "listing-id"}]
            subscribed_principals (List[Dict[str, Any]]): The principals to subscribe using tagged union format
                Example for project: [{"project": {"identifier": "project-id"}}]
                Example for user: [{"user": {"userId": "user-id"}}]
            metadata_forms (List[Dict[str, str]], optional): Additional metadata forms
                Example: [{
                    "content": "form-content",
                    "formName": "form-name",
                    "typeIdentifier": "type-id",
                    "typeRevision": "type-rev"
                }]
            client_token (str, optional): A unique token to ensure idempotency

        Returns:
            Any: The API response containing:
                - Subscription request ID and status
                - Creation and update timestamps
                - Domain ID
                - Request reason and decision comment
                - Subscribed listings and principals
                - Metadata forms
                - Reviewer information
        """
        try:
            # Prepare the request parameters
            params = {
                "domainIdentifier": domain_identifier,
                "requestReason": request_reason,
                "subscribedListings": subscribed_listings,
                "subscribedPrincipals": subscribed_principals,
            }

            # Add optional parameters if provided
            if metadata_forms:
                params["metadataForms"] = metadata_forms
            if client_token:
                params["clientToken"] = client_token

            response = datazone_client.create_subscription_request(**params)
            return response
        except ClientError as e:
            raise Exception(
                f"Error creating subscription request in domain {domain_identifier}: {e}"
            )

    @mcp.tool()
    async def accept_subscription_request(
        domain_identifier: str,
        identifier: str,
        asset_scopes: Optional[List[Dict[str, Any]]] = None,
        decision_comment: Optional[str] = None,
    ) -> Any:
        """
        Accepts a subscription request to a specific asset in Amazon DataZone.

        Args:
            domain_identifier (str): The ID of the domain where the subscription request exists
            identifier (str): The unique identifier of the subscription request to accept
            asset_scopes (List[Dict[str, Any]], optional): The asset scopes of the accept subscription request
                Example: [{"assetId": "asset-id", "filterIds": ["filter-id"]}]
            decision_comment (str, optional): A description that specifies the reason for accepting the request
                Length: 1-4096 characters

        Returns:
            Any: The API response containing:
                - Subscription request ID and status
                - Creation and update timestamps
                - Domain ID
                - Decision comment
                - Subscribed listings and principals
                - Metadata forms
                - Reviewer information
        """
        try:
            # Prepare the request parameters
            params: Dict[str, Any] = {
                "domainIdentifier": domain_identifier,
                "identifier": identifier,
            }

            # Add optional parameters if provided
            if asset_scopes:
                params["assetScopes"] = asset_scopes
            if decision_comment:
                params["decisionComment"] = decision_comment

            response = datazone_client.accept_subscription_request(**params)
            return response
        except ClientError as e:
            raise Exception(
                f"Error accepting subscription request {identifier} in domain {domain_identifier}: {e}"
            )

    @mcp.tool()
    async def get_subscription(domain_identifier: str, identifier: str) -> Any:
        """
        Gets a subscription in Amazon DataZone.

        Args:
            domain_identifier (str): The ID of the Amazon DataZone domain in which the subscription exists
                Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
            identifier (str): The ID of the subscription
                Pattern: ^[a-zA-Z0-9_-]{1,36}$

        Returns:
            Any: The API response containing:
                - Subscription ID and status (APPROVED | REVOKED | CANCELLED)
                - Creation and update timestamps
                - Domain ID
                - Retain permissions flag
                - Subscribed listing details
                - Subscribed principal information
                - Subscription request ID
                - Creator and updater information
        """
        try:
            response = datazone_client.get_subscription(
                domainIdentifier=domain_identifier, identifier=identifier
            )
            return response
        except ClientError as e:
            raise Exception(
                f"Error getting subscription {identifier} in domain {domain_identifier}: {e}"
            )

    @mcp.tool()
    async def get_form_type(
        domain_identifier: str, form_type_identifier: str, revision: Optional[str] = None
    ) -> Any:
        """
        Retrieves detailed information about a specific metadata form type in Amazon DataZone.

        Args:
            domain_identifier (str): The ID of the domain where the form type exists
                Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
            form_type_identifier (str): The ID of the form type to retrieve
                Length: 1-385 characters
            revision (str, optional): The revision of the form type to retrieve
                Length: 1-64 characters

        Returns:
            Any: The API response containing form type details including:
                - createdAt (number): Timestamp of when the form type was created
                - createdBy (str): The user who created the form type
                - description (str): The description of the form type (0-2048 characters)
                - domainId (str): The ID of the domain
                - imports (list): The imports of the form type (1-10 items)
                    Each import contains:
                        - name (str): The name of the import
                        - revision (str): The revision of the import
                - model (dict): The model of the form type (Union type)
                - name (str): The name of the form type (1-128 characters)
                - originDomainId (str): The ID of the domain where the form type was originally created
                - originProjectId (str): The ID of the project where the form type was originally created
                - owningProjectId (str): The ID of the project that owns the form type
                - revision (str): The revision of the form type (1-64 characters)
                - status (str): The status of the form type (ENABLED or DISABLED)

        Example:
            ```python
            response = await get_form_type(
                domain_identifier="dzd_123456789",
                form_type_identifier="amazon.datazone.customer_profile",
                revision="1.0.0"
            )
            ```
        """
        try:
            # Prepare the request parameters
            params = {
                "domainIdentifier": domain_identifier,
                "formTypeIdentifier": form_type_identifier,
            }

            # Add optional revision if provided
            if revision:
                params["revision"] = revision

            response = datazone_client.get_form_type(**params)
            return response
        except ClientError as e:
            raise Exception(
                f"Error getting form type {form_type_identifier} in domain {domain_identifier}: {e}"
            )

    # @mcp.tool()
    # async def list_form_types(
    #     domain_identifier: str,
    #     max_results: int = 50,
    #     next_token: str = None,
    #     status: str = None
    # ) -> Any:
    #     """
    #     Lists all form types available in an Amazon DataZone domain.

    #     Args:
    #         domain_identifier (str): The ID of the domain
    #         max_results (int, optional): Maximum number of form types to return (1-50, default: 50)
    #         next_token (str, optional): Token for pagination
    #         status (str, optional): Filter form types by status (ENABLED/DISABLED)

    #     Returns:
    #         Any: The API response containing:
    #             - List of form types with their details
    #             - Pagination token if more results are available
    #             - Total count of form types
    #     """
    #     try:
    #         # Prepare the request parameters
    #         params = {
    #             "domainIdentifier": domain_identifier,
    #             "maxResults": min(max_results, 50)  # Ensure maxResults is within valid range
    #         }

    #         # Add optional parameters if provided
    #         if next_token:
    #             params["nextToken"] = next_token
    #         if status:
    #             params["status"] = status

    #         response = datazone_client.list_form_types(**params)
    #         return response
    #     except ClientError as e:
    #         raise Exception(f"Error listing form types in domain {domain_identifier}: {e}")

    @mcp.tool()
    async def create_form_type(
        domain_identifier: str,
        name: str,
        model: Dict[str, Any],
        owning_project_identifier: str,
        description: Optional[str] = None,
        status: str = "ENABLED",
    ) -> Any:
        """
        Creates a new metadata form type in Amazon DataZone.

        Args:
            domain_identifier (str): The ID of the domain where the form type will be created
                Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
            name (str): The name of the form type (1-128 characters)
            model (Dict[str, Any]): The model of the form type
                Note: This is a Union type object where only one member can be specified
            owning_project_identifier (str): The ID of the project that owns the form type
                Pattern: ^[a-zA-Z0-9_-]{1,36}$
            description (str, optional): The description of the form type (0-2048 characters)
            status (str, optional): The status of the form type (ENABLED or DISABLED, default: ENABLED)

        Returns:
            Any: The API response containing:
                - description (str): The description of the form type
                - domainId (str): The ID of the domain
                - name (str): The name of the form type
                - originDomainId (str): The ID of the domain where the form type was originally created
                - originProjectId (str): The ID of the project where the form type was originally created
                - owningProjectId (str): The ID of the project that owns the form type
                - revision (str): The revision of the form type (1-64 characters)

        Example:
            ```python
            response = await create_form_type(
                domain_identifier="dzd_123456789",
                name="amazon.datazone.customer_profile",
                model={
                    "schema": {
                        "type": "object",
                        "properties": {
                            "customer_id": {"type": "string"},
                            "customer_name": {"type": "string"},
                            "email": {"type": "string", "format": "email"}
                        },
                        "required": ["customer_id", "customer_name"]
                    }
                },
                owning_project_identifier="prj_987654321",
                description="Form type for customer profile information",
                status="ENABLED"
            )
            ```
        """
        try:
            # Validate status
            if status not in ["ENABLED", "DISABLED"]:
                raise ValueError("status must be either 'ENABLED' or 'DISABLED'")

            # Prepare the request parameters
            params = {
                "name": name,
                "model": model,
                "owningProjectIdentifier": owning_project_identifier,
                "status": status,
            }

            # Add optional parameters if provided
            if description:
                params["description"] = description

            response = datazone_client.create_form_type(
                domainIdentifier=domain_identifier, **params
            )
            return response
        except ClientError as e:
            raise Exception(f"Error creating form type in domain {domain_identifier}: {e}")

    @mcp.tool()
    async def list_data_sources(
        domain_identifier: str,
        project_identifier: str,
        connection_identifier: Optional[str] = None,
        environment_identifier: Optional[str] = None,
        max_results: int = 50,
        name: Optional[str] = None,
        next_token: Optional[str] = None,
        status: Optional[str] = None,
        data_source_type: Optional[str] = None,
    ) -> Any:
        """
        Lists all form types available in an Amazon DataZone domain.

        Args:
            domain_identifier (str): The identifier of the Amazon DataZone domain in which to list the data sources.
                Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
                Required: Yes
            project_identifier (str): The identifier of the project in which to list data sources.
                Required: Yes
            connection_identifier (str, optional): The ID of the connection used to filter the data sources.
            environment_identifier (str, optional): The identifier of the environment in which to list the data sources.
            max_results (int, optional): The maximum number of data sources to return in one response.
                Valid Range: 1–50
            name (str, optional): Filter by name of the data source.
                Length Constraints: 1–256 characters
            next_token (str, optional): A pagination token for fetching the next set of results.
                Length Constraints: 1–8192 characters
            status (str, optional): Filter data sources by their current status.
                Valid values:
                    - CREATING
                    - FAILED_CREATION
                    - READY
                    - UPDATING
                    - FAILED_UPDATE
                    - RUNNING
                    - DELETING
                    - FAILED_DELETION
            data_source_type (str, optional): Filter by the type of data source (e.g., GLUE, REDSHIFT).
                Length Constraints: 1–256 characters

        Returns:
            dict: A dictionary with the following keys:
                - items (List[dict]): A list of DataSourceSummary objects containing:
                    - connectionId (str)
                    - createdAt (str)
                    - dataSourceId (str)
                    - description (str)
                    - domainId (str)
                    - enableSetting (str)
                    - environmentId (str)
                    - lastRunAssetCount (int)
                    - lastRunAt (str)
                    - lastRunErrorMessage (dict): Contains "errorDetail" and "errorType"
                    - lastRunStatus (str)
                    - name (str)
                    - schedule (dict): Contains "schedule" and "timezone"
                    - status (str)
                    - type (str)
                    - updatedAt (str)

                - nextToken (str): Token to retrieve the next page of results, if any.
        """
        try:
            # Prepare the request parameters
            params = {
                "domainIdentifier": domain_identifier,
                "maxResults": min(max_results, 50),  # Ensure maxResults is within valid range
                "projectIdentifier": project_identifier,
            }

            # Add optional parameters if provided
            if next_token:
                params["nextToken"] = next_token
            if status:
                params["status"] = status
            if connection_identifier:
                params["connectionIdentifier"] = connection_identifier
            if environment_identifier:
                params["environmentIdentifier"] = environment_identifier
            if name:
                params["name"] = name
            if data_source_type:
                params["type"] = data_source_type

            response = datazone_client.list_data_sources(**params)
            return response
        except ClientError as e:
            raise Exception(
                f"Error listing data sources in project {project_identifier} in domain {domain_identifier}: {e}"
            )

    # Return the decorated functions for testing purposes
    return {
        "get_asset": get_asset,
        "create_asset": create_asset,
        # "delete_asset": delete_asset,
        "publish_asset": publish_asset,
        # "get_asset_filter": get_asset_filter,
        # "list_asset_filters": list_asset_filters,
        # "get_asset_type": get_asset_type,
        "get_listing": get_listing,
        "search_listings": search_listings,
        "create_data_source": create_data_source,
        "get_data_source": get_data_source,
        # "get_time_series_data_point": get_time_series_data_point,
        # "list_time_series_data_points": list_time_series_data_points,
        # "get_data_product": get_data_product,
        # "get_lineage_node": get_lineage_node,
        "start_data_source_run": start_data_source_run,
        # "get_job_run": get_job_run,
        # "list_job_runs": list_job_runs,
        "create_subscription_request": create_subscription_request,
        "accept_subscription_request": accept_subscription_request,
        "get_subscription": get_subscription,
        "get_form_type": get_form_type,
        # "list_form_types": list_form_types,
        "create_form_type": create_form_type,
        "list_data_sources": list_data_sources,
    }
