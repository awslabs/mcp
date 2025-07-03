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
"""Data management tools for Amazon DataZone."""

from .common import ClientError, _get_param_value, datazone_client, logger
from ..context import Context
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Any, Dict, List, Optional


def register_tools(mcp: FastMCP):
    """Register data management tools with the MCP server."""

    @mcp.tool()
    async def get_asset(
        domain_identifier: str = Field(
            ..., description='The ID of the domain containing the asset'
        ),
        asset_identifier: str = Field(..., description='The ID of the asset to retrieve'),
        revision: Optional[str] = Field(
            default=None, description='The specific revision of the asset to retrieve'
        ),
    ) -> Any:
        """Retrieves detailed information about one specific asset (specified by user) in Amazon DataZone.

        Use this API when you want to inspect or manage a particular **known asset** dataset, or table and want to retrieve its:
        - Full metadata (business and technical)
        - Lineage information
        - Forms and glossary terms
        - Time-series details
        - Revision history
        - Access and listing info

        Data asset is a specific dataset or table, while data source is a location where your data resides.

        related tools:
        - search: use when user is **trying to discover or explore** unknown assets based on keywords, metadata, or filters.
        - get_data_source: get detailed information about one specific data source in a domain.

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
            # Handle optional parameters
            revision_value = _get_param_value(revision)

            # Prepare the request parameters
            params = {'domainIdentifier': domain_identifier, 'identifier': asset_identifier}

            # Add optional revision if provided
            if revision_value:
                params['revision'] = revision_value

            response = datazone_client.get_asset(**params)
            return response
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDeniedException':
                logger.error(
                    f'Access denied while getting asset {asset_identifier} in domain {domain_identifier}'
                )
                raise Exception(
                    f'Access denied while getting asset {asset_identifier} in domain {domain_identifier}'
                )
            elif error_code == 'InternalServerException':
                logger.error(
                    f'Unknown error, exception or failure while getting asset {asset_identifier} in domain {domain_identifier}'
                )
                raise Exception(
                    f'Unknown error, exception or failure while getting asset {asset_identifier} in domain {domain_identifier}'
                )
            elif error_code == 'ResourceNotFoundException':
                logger.error(
                    f'Data asset {asset_identifier} not found in domain {domain_identifier}'
                )
                raise Exception(
                    f'Data asset {asset_identifier} or domain {domain_identifier} not found'
                )
            elif error_code == 'ThrottlingException':
                logger.error(
                    f'Request throttled while getting asset {asset_identifier} in domain {domain_identifier}'
                )
                raise Exception(
                    f'Request throttled while getting asset {asset_identifier} in domain {domain_identifier}'
                )
            elif error_code == 'UnauthorizedException':
                logger.error(
                    f'Unauthorized to get asset {asset_identifier} in domain {domain_identifier}'
                )
                raise Exception(
                    f'Unauthorized to get asset {asset_identifier} in domain {domain_identifier}'
                )
            elif error_code == 'ValidationException':
                logger.error(
                    f'Invalid input while getting asset {asset_identifier} in domain {domain_identifier}'
                )
                raise Exception(
                    f'Invalid input while getting asset {asset_identifier} in domain {domain_identifier}'
                )
            else:
                raise Exception(
                    f'Error getting asset {asset_identifier} in domain {domain_identifier}'
                )
        except Exception:
            raise Exception(
                f'Unexpected error getting asset {asset_identifier} in domain {domain_identifier}'
            )

    @mcp.tool()
    async def create_asset(
        domain_identifier: str = Field(
            ..., description='The ID of the domain where the asset is created'
        ),
        name: str = Field(..., description='The name of the asset (1-256 characters)'),
        type_identifier: str = Field(
            ..., description='The ID of the asset type (1-513 characters)'
        ),
        owning_project_identifier: str = Field(
            ..., description='The ID of the project that owns this asset'
        ),
        description: Optional[str] = Field(
            default=None, description='Description of the asset (0-2048 characters)'
        ),
        external_identifier: Optional[str] = Field(
            default=None, description='External ID of the asset (1-600 characters)'
        ),
        forms_input: Optional[List[Dict[str, str]]] = Field(
            default=None, description='Metadata forms for the asset'
        ),
        glossary_terms: Optional[List[str]] = Field(
            default=None, description='Glossary terms to attach to the asset'
        ),
        prediction_configuration: Optional[Dict[str, Dict[str, bool]]] = Field(
            default=None, description='Configuration for business name generation'
        ),
        type_revision: Optional[str] = Field(
            default=None, description='The revision of the asset type'
        ),
        client_token: Optional[str] = Field(default=None, description='Token for idempotency'),
    ) -> Any:
        """Creates an asset in the Amazon DataZone catalog.

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
            # Handle optional parameters
            description_value = _get_param_value(description)
            external_identifier_value = _get_param_value(external_identifier)
            forms_input_value = _get_param_value(forms_input)
            glossary_terms_value = _get_param_value(glossary_terms)
            prediction_configuration_value = _get_param_value(prediction_configuration)
            type_revision_value = _get_param_value(type_revision)
            client_token_value = _get_param_value(client_token)

            # Prepare the request parameters
            params: Dict[str, Any] = {
                'domainIdentifier': domain_identifier,
                'name': name,
                'typeIdentifier': type_identifier,
                'owningProjectIdentifier': owning_project_identifier,
            }

            # Add optional parameters if provided
            if description_value:
                params['description'] = description_value
            if external_identifier_value:
                params['externalIdentifier'] = external_identifier_value
            if forms_input_value:
                params['formsInput'] = forms_input_value
            if glossary_terms_value:
                params['glossaryTerms'] = glossary_terms_value
            if prediction_configuration_value:
                params['predictionConfiguration'] = prediction_configuration_value
            if type_revision_value:
                params['typeRevision'] = type_revision_value
            if client_token_value:
                params['clientToken'] = client_token_value

            response = datazone_client.create_asset(**params)
            return response
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDeniedException':
                logger.error(f'Access denied while creating asset in domain {domain_identifier}')
                raise Exception(
                    f'Access denied while creating asset in domain {domain_identifier}'
                )
            elif error_code == 'InternalServerException':
                logger.error(
                    f'Unknown error, exception or failure while creating asset in domain {domain_identifier}'
                )
                raise Exception(
                    f'Unknown error, exception or failure while creating asset in domain {domain_identifier}'
                )
            elif error_code == 'ResourceNotFoundException':
                logger.error(f'Domain {domain_identifier} not found')
                raise Exception(f'Domain {domain_identifier} not found')
            elif error_code == 'ThrottlingException':
                logger.error(
                    f'Request throttled while creating asset in domain {domain_identifier}'
                )
                raise Exception(
                    f'Request throttled while creating asset in domain {domain_identifier}'
                )
            elif error_code == 'UnauthorizedException':
                logger.error(f'Unauthorized to create asset in domain {domain_identifier}')
                raise Exception(f'Unauthorized to create asset in domain {domain_identifier}')
            elif error_code == 'ValidationException':
                logger.error(f'Invalid input while creating asset in domain {domain_identifier}')
                raise Exception(
                    f'Invalid input while creating asset in domain {domain_identifier}'
                )
            elif error_code == 'ConflictException':
                logger.error(
                    f'There is a conflict while creating asset in domain {domain_identifier}'
                )
                raise Exception(
                    f'There is a conflict while creating asset in domain {domain_identifier}'
                )
            else:
                raise Exception(f'Error creating asset in domain {domain_identifier}')
        except Exception:
            raise Exception(f'Unexpected error creating asset in domain {domain_identifier}')

    @mcp.tool()
    async def publish_asset(
        domain_identifier: str = Field(
            ..., description='The ID of the domain containing the asset'
        ),
        asset_identifier: str = Field(..., description='The ID of the asset to publish'),
        revision: Optional[str] = Field(
            default=None, description='The specific revision of the asset to publish'
        ),
        client_token: Optional[str] = Field(default=None, description='Token for idempotency'),
    ) -> Any:
        """Publishes an asset to the Amazon DataZone catalog.

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
        # Check write permissions
        Context.check_write_permission('publish_asset')
        try:
            # Handle optional parameters
            revision_value = _get_param_value(revision)
            client_token_value = _get_param_value(client_token)

            # Prepare the request parameters
            params = {'domainIdentifier': domain_identifier, 'identifier': asset_identifier}

            # Add optional parameters if provided
            if revision_value:
                params['revision'] = revision_value
            if client_token_value:
                params['clientToken'] = client_token_value

            response = datazone_client.publish_asset(**params)
            return response
        except ClientError as e:
            raise Exception(
                f'Error publishing asset {asset_identifier} in domain {domain_identifier}: {e}'
            )

    @mcp.tool()
    async def get_listing(
        domain_identifier: str = Field(..., description='The ID of the Amazon DataZone domain'),
        identifier: str = Field(..., description='The ID of the listing'),
        listing_revision: Optional[str] = Field(
            default=None, description='The revision of the listing'
        ),
    ) -> Any:
        """Gets a listing (a record of an asset at a given time) in Amazon DataZone.

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
            # Handle optional parameters
            listing_revision_value = _get_param_value(listing_revision)

            # Prepare the request parameters
            params = {'domainIdentifier': domain_identifier, 'identifier': identifier}

            # Add optional parameters if provided
            if listing_revision_value:
                params['listingRevision'] = listing_revision_value

            response = datazone_client.get_listing(**params)
            return response
        except ClientError as e:
            raise Exception(
                f'Error getting listing {identifier} in domain {domain_identifier}: {e}'
            )

    @mcp.tool()
    async def search_listings(
        domain_identifier: str = Field(..., description='The ID of the domain to search in'),
        search_text: Optional[str] = Field(default=None, description='Text to search for'),
        max_results: int = Field(
            default=50, description='Maximum number of results to return (1-50)'
        ),
        next_token: Optional[str] = Field(default=None, description='Token for pagination'),
        additional_attributes: Optional[List[str]] = Field(
            default=None, description='Additional attributes to include in search'
        ),
        search_in: Optional[List[Dict[str, str]]] = Field(
            default=None, description='Attributes to search in'
        ),
        sort: Optional[Dict[str, str]] = Field(default=None, description='Sorting criteria'),
    ) -> Any:
        """Search published **data asset listings** in Amazon DataZone using keyword, filter, and sort options.

        Use it to search only within published data asset listings.

        related tools:
        - search: Use only when the user needs general discovery across **all** entity types (e.g., glossary terms, data products).

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
            # Handle optional parameters
            max_results_value = _get_param_value(max_results)
            search_text_value = _get_param_value(search_text)
            next_token_value = _get_param_value(next_token)
            additional_attributes_value = _get_param_value(additional_attributes)
            search_in_value = _get_param_value(search_in)
            sort_value = _get_param_value(sort)

            # Prepare the request parameters
            params = {
                'domainIdentifier': domain_identifier,
                'maxResults': min(
                    max_results_value, 50
                ),  # Ensure maxResults is within valid range
            }

            # Add optional parameters if provided
            if search_text_value:
                params['searchText'] = search_text_value
            if next_token_value:
                params['nextToken'] = next_token_value
            if additional_attributes_value:
                params['additionalAttributes'] = additional_attributes_value
            if search_in_value:
                params['searchIn'] = search_in_value
            if sort_value:
                params['sort'] = sort_value

            response = datazone_client.search_listings(**params)
            return response
        except ClientError as e:
            raise Exception(f'Error searching listings in domain {domain_identifier}: {e}')

    @mcp.tool()
    async def create_data_source(
        domain_identifier: str = Field(
            ..., description='The ID of the domain where the data source is created'
        ),
        project_identifier: str = Field(
            ..., description='The ID of the project to associate the data source with'
        ),
        name: str = Field(..., description='The name of the data source (1-256 characters)'),
        data_src_type: str = Field(
            ..., description="The type of data source (e.g., 'S3', 'GLUE', 'REDSHIFT')"
        ),
        description: Optional[str] = Field(
            default=None, description='Description of the data source (0-2048 characters)'
        ),
        enable_setting: str = Field(
            default='ENABLED', description='Whether the data source is enabled (ENABLED/DISABLED)'
        ),
        environment_identifier: Optional[str] = Field(
            default=None, description='ID of the environment to publish assets to'
        ),
        connection_identifier: Optional[str] = Field(
            default=None, description='ID of the connection to use'
        ),
        configuration: Optional[Dict[str, Any]] = Field(
            default=None, description='Data source configuration'
        ),
        asset_forms_input: Optional[List[Dict[str, str]]] = Field(
            default=None, description='Metadata forms for assets'
        ),
        publish_on_import: bool = Field(
            default=False, description='Whether to automatically publish imported assets'
        ),
        recommendation: Optional[Dict[str, bool]] = Field(
            default=None, description='Recommendation settings'
        ),
        schedule: Optional[Dict[str, str]] = Field(
            default=None, description='Schedule configuration'
        ),
        client_token: Optional[str] = Field(default=None, description='Token for idempotency'),
    ) -> Any:
        """Creates a data source in Amazon DataZone and associates it with a project.

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
        # Check write permissions
        Context.check_write_permission('create_data_source')
        try:
            # Handle optional parameters
            description_value = _get_param_value(description)
            enable_setting_value = _get_param_value(enable_setting)
            environment_identifier_value = _get_param_value(environment_identifier)
            connection_identifier_value = _get_param_value(connection_identifier)
            configuration_value = _get_param_value(configuration)
            asset_forms_input_value = _get_param_value(asset_forms_input)
            publish_on_import_value = _get_param_value(publish_on_import)
            recommendation_value = _get_param_value(recommendation)
            schedule_value = _get_param_value(schedule)
            client_token_value = _get_param_value(client_token)

            # Prepare the request parameters
            params = {
                'domainIdentifier': domain_identifier,
                'projectIdentifier': project_identifier,
                'name': name,
                'type': data_src_type,
                'enableSetting': enable_setting_value,
                'publishOnImport': publish_on_import_value,
            }

            # Add optional parameters if provided
            if description_value:
                params['description'] = description_value
            if environment_identifier_value:
                params['environmentIdentifier'] = environment_identifier_value
            if connection_identifier_value:
                params['connectionIdentifier'] = connection_identifier_value
            if configuration_value:
                params['configuration'] = configuration_value
            if asset_forms_input_value:
                params['assetFormsInput'] = asset_forms_input_value
            if recommendation_value:
                params['recommendation'] = recommendation_value
            if schedule_value:
                params['schedule'] = schedule_value
            if client_token_value:
                params['clientToken'] = client_token_value

            response = datazone_client.create_data_source(**params)
            return response
        except ClientError as e:
            raise Exception(f'Error creating data source in domain {domain_identifier}: {e}')

    @mcp.tool()
    async def get_data_source(
        domain_identifier: str = Field(
            ..., description='The ID of the domain where the data source exists'
        ),
        identifier: str = Field(..., description='The ID of the data source to retrieve'),
    ) -> Any:
        """Retrieves detailed information about a **specific, known data source** in Amazon DataZone.

        Use this API when the user mentions a **specific data source by name, type, or context** (e.g., "Redshift data source in analytics domain") and wants details like:
        - Connection settings
        - Ingestion configuration
        - Authentication and scheduling details
        - Last run status and errors

        Data source is a location that defines where your data resides, while data asset is a specific dataset or table.
        Connections are credentials + config for accessing a system, while data source is a specific location where your data resides using a connection.

        related tools:
        - list_data_sources: retrieve ea list of data sources in a domain by name, status, type, etc.
        - get_asset: get detailed information about one specific data asset in a data source.

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
            raise Exception(f'Error getting data source {identifier}: {e}')

    @mcp.tool()
    async def start_data_source_run(
        domain_identifier: str = Field(
            ...,
            description='The identifier of the Amazon DataZone domain in which to start a data source run',
        ),
        data_source_identifier: str = Field(..., description='The identifier of the data source'),
        client_token: Optional[str] = Field(
            default=None,
            description='A unique, case-sensitive identifier that is provided to ensure the idempotency of the request',
        ),
    ) -> Any:
        """Starts a data source run in Amazon DataZone.

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
                domain_identifier='dzd-1234567890',
                data_source_identifier='ds-1234567890',
                client_token='unique-token-123',
            )
            ```
        """
        # Check write permissions
        Context.check_write_permission('start_data_source_run')
        try:
            # Handle optional parameters
            client_token_value = _get_param_value(client_token)

            # Prepare the request parameters
            params = {
                'domainIdentifier': domain_identifier,
                'dataSourceIdentifier': data_source_identifier,
            }

            # Add optional client_token if provided
            if client_token_value:
                params['clientToken'] = client_token_value

            response = datazone_client.start_data_source_run(**params)
            return response
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDeniedException':
                raise Exception(
                    f'Access denied while starting data source run for {data_source_identifier} in domain {domain_identifier}'
                )
            elif error_code == 'ConflictException':
                raise Exception(
                    f'Conflict while starting data source run for {data_source_identifier} in domain {domain_identifier}'
                )
            elif error_code == 'InternalServerException':
                raise Exception(
                    f'Internal server error while starting data source run for {data_source_identifier} in domain {domain_identifier}'
                )
            elif error_code == 'ResourceNotFoundException':
                raise Exception(
                    f'Data source {data_source_identifier} or domain {domain_identifier} not found'
                )
            elif error_code == 'ServiceQuotaExceededException':
                raise Exception(
                    f'Service quota exceeded while starting data source run for {data_source_identifier} in domain {domain_identifier}'
                )
            elif error_code == 'ThrottlingException':
                raise Exception(
                    f'Request throttled while starting data source run for {data_source_identifier} in domain {domain_identifier}'
                )
            elif error_code == 'UnauthorizedException':
                raise Exception(
                    f'Unauthorized to start data source run for {data_source_identifier} in domain {domain_identifier}'
                )
            elif error_code == 'ValidationException':
                raise Exception(
                    f'Invalid input while starting data source run for {data_source_identifier} in domain {domain_identifier}'
                )
            else:
                raise Exception(
                    f'Error starting data source run for {data_source_identifier} in domain {domain_identifier}: {str(e)}'
                )
        except Exception as e:
            raise Exception(
                f'Unexpected error starting data source run for {data_source_identifier} in domain {domain_identifier}: {str(e)}'
            )

    @mcp.tool()
    async def create_subscription_request(
        domain_identifier: str = Field(
            ..., description='The ID of the domain where the subscription request is created'
        ),
        request_reason: str = Field(
            ..., description='The reason for the subscription request (1-4096 characters)'
        ),
        subscribed_listings: List[Dict[str, str]] = Field(
            ..., description='The published assets to subscribe to'
        ),
        subscribed_principals: List[Dict[str, Any]] = Field(
            ..., description='The principals to subscribe using tagged union format'
        ),
        metadata_forms: Optional[List[Dict[str, str]]] = Field(
            default=None, description='Additional metadata forms'
        ),
        client_token: Optional[str] = Field(
            default=None, description='A unique token to ensure idempotency'
        ),
    ) -> Any:
        """Creates a subscription request in Amazon DataZone.

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
        Context.check_write_permission('create_subscription_request')
        try:
            # Handle optional parameters
            metadata_forms_value = _get_param_value(metadata_forms)
            client_token_value = _get_param_value(client_token)

            # Prepare the request parameters
            params = {
                'domainIdentifier': domain_identifier,
                'requestReason': request_reason,
                'subscribedListings': subscribed_listings,
                'subscribedPrincipals': subscribed_principals,
            }

            # Add optional parameters if provided
            if metadata_forms_value:
                params['metadataForms'] = metadata_forms_value
            if client_token_value:
                params['clientToken'] = client_token_value

            response = datazone_client.create_subscription_request(**params)
            return response
        except ClientError as e:
            raise Exception(
                f'Error creating subscription request in domain {domain_identifier}: {e}'
            )

    @mcp.tool()
    async def accept_subscription_request(
        domain_identifier: str = Field(
            ..., description='The ID of the domain where the subscription request exists'
        ),
        identifier: str = Field(
            ..., description='The unique identifier of the subscription request to accept'
        ),
        asset_scopes: Optional[List[Dict[str, Any]]] = Field(
            default=None, description='The asset scopes of the accept subscription request'
        ),
        decision_comment: Optional[str] = Field(
            default=None,
            description='A description that specifies the reason for accepting the request',
        ),
    ) -> Any:
        """Accepts a subscription request to a specific asset in Amazon DataZone.

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
        Context.check_write_permission('accept_subscription_request')
        try:
            # Handle optional parameters
            asset_scopes_value = _get_param_value(asset_scopes)
            decision_comment_value = _get_param_value(decision_comment)

            # Prepare the request parameters
            params: Dict[str, Any] = {
                'domainIdentifier': domain_identifier,
                'identifier': identifier,
            }

            # Add optional parameters if provided
            if asset_scopes_value:
                params['assetScopes'] = asset_scopes_value
            if decision_comment_value:
                params['decisionComment'] = decision_comment_value

            response = datazone_client.accept_subscription_request(**params)
            return response
        except ClientError as e:
            raise Exception(
                f'Error accepting subscription request {identifier} in domain {domain_identifier}: {e}'
            )

    @mcp.tool()
    async def get_subscription(
        domain_identifier: str = Field(
            ...,
            description='The ID of the Amazon DataZone domain in which the subscription exists',
        ),
        identifier: str = Field(..., description='The ID of the subscription'),
    ) -> Any:
        """Gets a subscription in Amazon DataZone.

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
                f'Error getting subscription {identifier} in domain {domain_identifier}: {e}'
            )

    @mcp.tool()
    async def get_form_type(
        domain_identifier: str = Field(
            ..., description='The ID of the domain where the form type exists'
        ),
        form_type_identifier: str = Field(..., description='The ID of the form type to retrieve'),
        revision: Optional[str] = Field(
            default=None, description='The revision of the form type to retrieve'
        ),
    ) -> Any:
        """Retrieves detailed information about a specific metadata form type in Amazon DataZone.

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
                domain_identifier='dzd_123456789',
                form_type_identifier='amazon.datazone.customer_profile',
                revision='1.0.0',
            )
            ```
        """
        try:
            # Handle optional parameters
            revision_value = _get_param_value(revision)

            # Prepare the request parameters
            params = {
                'domainIdentifier': domain_identifier,
                'formTypeIdentifier': form_type_identifier,
            }

            # Add optional revision if provided
            if revision_value:
                params['revision'] = revision_value

            response = datazone_client.get_form_type(**params)
            return response
        except ClientError as e:
            raise Exception(
                f'Error getting form type {form_type_identifier} in domain {domain_identifier}: {e}'
            )

    @mcp.tool()
    async def create_form_type(
        domain_identifier: str = Field(
            ..., description='The ID of the domain where the form type will be created'
        ),
        name: str = Field(..., description='The name of the form type (1-128 characters)'),
        model: Dict[str, Any] = Field(..., description='The model of the form type'),
        owning_project_identifier: str = Field(
            ..., description='The ID of the project that owns the form type'
        ),
        description: Optional[str] = Field(
            default=None, description='The description of the form type (0-2048 characters)'
        ),
        status: str = Field(
            default='ENABLED', description='The status of the form type (ENABLED or DISABLED)'
        ),
    ) -> Any:
        """Creates a new metadata form type in Amazon DataZone.

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
                domain_identifier='dzd_123456789',
                name='amazon.datazone.customer_profile',
                model={
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'customer_id': {'type': 'string'},
                            'customer_name': {'type': 'string'},
                            'email': {'type': 'string', 'format': 'email'},
                        },
                        'required': ['customer_id', 'customer_name'],
                    }
                },
                owning_project_identifier='prj_987654321',
                description='Form type for customer profile information',
                status='ENABLED',
            )
            ```
        """
        Context.check_write_permission('create_form_type')
        try:
            # Handle optional parameters
            description_value = _get_param_value(description)
            status_value = 'ENABLED' if status is None else status

            # Validate status
            if status_value not in ['ENABLED', 'DISABLED']:
                raise ValueError("status must be either 'ENABLED' or 'DISABLED'")

            # Prepare the request parameters
            params = {
                'name': name,
                'model': model,
                'owningProjectIdentifier': owning_project_identifier,
                'status': status_value,
            }

            # Add optional parameters if provided
            if description_value:
                params['description'] = description_value

            response = datazone_client.create_form_type(
                domainIdentifier=domain_identifier, **params
            )
            return response
        except ClientError as e:
            raise Exception(f'Error creating form type in domain {domain_identifier}: {e}')

    @mcp.tool()
    async def list_data_sources(
        domain_identifier: str = Field(
            ...,
            description='The identifier of the Amazon DataZone domain in which to list the data sources',
        ),
        project_identifier: str = Field(
            ..., description='The identifier of the project in which to list data sources'
        ),
        connection_identifier: Optional[str] = Field(
            default=None, description='The ID of the connection used to filter the data sources'
        ),
        environment_identifier: Optional[str] = Field(
            default=None,
            description='The identifier of the environment in which to list the data sources',
        ),
        max_results: int = Field(
            default=50, description='The maximum number of data sources to return in one response'
        ),
        name: Optional[str] = Field(default=None, description='Filter by name of the data source'),
        next_token: Optional[str] = Field(
            default=None, description='A pagination token for fetching the next set of results'
        ),
        status: Optional[str] = Field(
            default=None, description='Filter data sources by their current status'
        ),
        data_source_type: Optional[str] = Field(
            default=None, description='Filter by the type of data source (e.g., GLUE, REDSHIFT)'
        ),
    ) -> Any:
        """Retrieve a list of data sources in Datazone domain.

        Use this API when the user is **browsing, searching, or filtering** data sources — especially if they **don't know the exact ID** or want to find a list to choose from.
        This is **not** the correct API if the user asks for config details of a known data source — use `get_data_source` in that case.

        related tools:
        get_data_source: Retrieves detailed information about a known data source. Use get_data_source when you want to fetch info about the connection details, authentication settings, or ingestion configuration of a particular data source.

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
            # Handle optional parameters
            connection_identifier_value = _get_param_value(connection_identifier)
            environment_identifier_value = _get_param_value(environment_identifier)
            max_results_value = _get_param_value(max_results)
            name_value = _get_param_value(name)
            next_token_value = _get_param_value(next_token)
            status_value = _get_param_value(status)
            data_source_type_value = _get_param_value(data_source_type)

            # Prepare the request parameters
            params = {
                'domainIdentifier': domain_identifier,
                'maxResults': min(
                    max_results_value, 50
                ),  # Ensure maxResults is within valid range
                'projectIdentifier': project_identifier,
            }

            # Add optional parameters if provided
            if next_token_value:
                params['nextToken'] = next_token_value
            if status_value:
                params['status'] = status_value
            if connection_identifier_value:
                params['connectionIdentifier'] = connection_identifier_value
            if environment_identifier_value:
                params['environmentIdentifier'] = environment_identifier_value
            if name_value:
                params['name'] = name_value
            if data_source_type_value:
                params['type'] = data_source_type_value

            response = datazone_client.list_data_sources(**params)
            return response
        except ClientError as e:
            raise Exception(
                f'Error listing data sources in project {project_identifier} in domain {domain_identifier}: {e}'
            )

    # Return the decorated functions for testing purposes
    return {
        'get_asset': get_asset,
        'create_asset': create_asset,
        'publish_asset': publish_asset,
        'get_listing': get_listing,
        'search_listings': search_listings,
        'create_data_source': create_data_source,
        'get_data_source': get_data_source,
        'start_data_source_run': start_data_source_run,
        'create_subscription_request': create_subscription_request,
        'accept_subscription_request': accept_subscription_request,
        'get_subscription': get_subscription,
        'get_form_type': get_form_type,
        'create_form_type': create_form_type,
        'list_data_sources': list_data_sources,
    }
