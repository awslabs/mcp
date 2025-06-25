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
"""Domain management tools for Amazon DataZone."""

from .common import ClientError, datazone_client, logger, _get_param_value
from mcp.server.fastmcp import FastMCP
from typing import Any, Dict, List, Optional
from pydantic import Field


def register_tools(mcp: FastMCP):
    """Register domain management tools with the MCP server."""

    @mcp.tool()
    async def get_domain(identifier: str = Field(..., description="The domain identifier")) -> Any:
        """Calls the Amazon DataZone GetDomain API for a given domain identifier.

        Args:
            identifier (str): The domain identifier (e.g., "dzd_4p9n6sw4qt9xgn")

        Returns:
            Any: The API response containing domain details or None if an error occurs
        """
        try:
            response = datazone_client.get_domain(identifier=identifier)
            return response
        except ClientError as e:
            raise Exception(f'Error getting domain {identifier}: {e}')

    @mcp.tool()
    async def create_domain(
        name: str = Field(..., description="The name of the domain"),
        domain_execution_role: str = Field(..., description="The ARN of the domain execution role"),
        service_role: str = Field(..., description="The ARN of the service role"),
        domain_version: str = Field(default='V2', description="The version of the domain (V1 or V2)"),
        description: Optional[str] = Field(default=None, description="Description of the domain"),
        kms_key_identifier: Optional[str] = Field(default=None, description="ARN of the KMS key for encryption"),
        tags: Optional[Dict[str, str]] = Field(default=None, description="Tags to associate with the domain"),
        single_sign_on: Optional[Dict[str, str]] = Field(default=None, description="Single sign-on configuration"),
    ) -> Dict[str, Any]:
        """Creates a new Amazon DataZone domain.

        Args:
            name (str): The name of the domain
            domain_execution_role (str): The ARN of the domain execution role
            service_role (str): The ARN of the service role
            domain_version (str, optional): The version of the domain (V1 or V2) (default: "V2")
            description (str, optional): Description of the domain
            kms_key_identifier (str, optional): ARN of the KMS key for encryption
            tags (Dict[str, str], optional): Tags to associate with the domain
            single_sign_on (Dict[str, str], optional): Single sign-on configuration

        Returns:
            Dict containing:
                - id: Domain identifier
                - arn: Domain ARN
                - name: Domain name
                - description: Domain description
                - domain_version: Domain version
                - status: Domain status
                - portal_url: Data portal URL
                - root_domain_unit_id: Root domain unit ID
        """
        try:
            # Handle optional parameters
            description_value = _get_param_value(description)
            kms_key_identifier_value = _get_param_value(kms_key_identifier)
            tags_value = _get_param_value(tags)
            single_sign_on_value = _get_param_value(single_sign_on)

            logger.info(f'Creating {domain_version} domain: {name}')

            # Prepare request parameters
            params: Dict[str, Any] = {
                'name': name,
                'domainExecutionRole': domain_execution_role,
                'domainVersion': domain_version,
            }

            # Add optional parameters
            if description_value:  # pragma: no cover
                params['description'] = description_value
            if kms_key_identifier_value:  # pragma: no cover
                params['kmsKeyIdentifier'] = kms_key_identifier_value
            if tags_value:  # pragma: no cover
                params['tags'] = tags_value
            if single_sign_on_value:  # pragma: no cover
                params['singleSignOn'] = single_sign_on_value
            if service_role:  # pragma: no cover
                params['serviceRole'] = service_role

            # Create the domain
            response = datazone_client.create_domain(**params)

            # Format the response
            result = {
                'id': response.get('id'),
                'arn': response.get('arn'),
                'name': response.get('name'),
                'description': response.get('description'),
                'domain_version': response.get('domainVersion'),
                'status': response.get('status'),
                'portal_url': response.get('portalUrl'),
                'root_domain_unit_id': response.get('rootDomainUnitId'),
            }

            logger.info(f'Successfully created {domain_version} domain: {name}')
            return result

        except ClientError as e:  # pragma: no cover
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDeniedException':  # pragma: no cover
                logger.error(f'Access denied while creating domain {name}')
                raise Exception(f'Access denied while creating domain {name}')
            elif error_code == 'ConflictException':  # pragma: no cover
                logger.error(f'Domain {name} already exists')
                raise Exception(f'Domain {name} already exists')
            elif error_code == 'ValidationException':  # pragma: no cover
                logger.error(f'Invalid parameters for creating domain {name}')
                raise Exception(f'Invalid parameters for creating domain {name}')
            else:  # pragma: no cover
                logger.error(f'Error creating domain {name}: {str(e)}')
                raise Exception(f'Error creating domain {name}: {str(e)}')
        except Exception as e:  # pragma: no cover
            logger.error(f'Unexpected error creating domain {name}: {str(e)}')
            raise Exception(f'Unexpected error creating domain {name}: {str(e)}')

    @mcp.tool()
    async def list_domain_units(
        domain_identifier: str = Field(..., description="The identifier of the domain"),
        parent_domain_unit_identifier: str = Field(..., description="The identifier of the parent domain unit")
    ) -> Any:
        """Lists child domain units for the specified parent domain unit in an Amazon DataZone domain.

        Args:
            domain_identifier (str): The identifier of the domain (e.g., "dzd_4p9n6sw4qt9xgn")
            parent_domain_unit_identifier (str): The identifier of the parent domain unit (e.g., "3thjq258ficc2v")

        Returns:
            Any: The API response containing the list of domain units
        """
        try:
            response = datazone_client.list_domain_units_for_parent(
                domainIdentifier=domain_identifier,
                parentDomainUnitIdentifier=parent_domain_unit_identifier,
            )
            return response
        except ClientError as e:  # pragma: no cover
            raise Exception(f'Error listing domain units for domain {domain_identifier}: {e}')

    @mcp.tool()
    async def list_domains(
        max_results: int = Field(default=25, description="Maximum number of results to return (max: 25)"),
        next_token: Optional[str] = Field(default=None, description="Token for pagination to get next page of results"),
        status: Optional[str] = Field(default=None, description="Filter domains by status")
    ) -> Any:
        """Lists Amazon DataZone domains.

        Args:
            max_results (int, optional): Maximum number of results to return (default: 25, max: 25)
            next_token (str, optional): Token for pagination to get next page of results
            status (str, optional): Filter domains by status (e.g., "AVAILABLE", "CREATING", "DELETING")

        Returns:
            Dict containing:
                - items: List of domains with details including ID, name, status, ARN, etc.
                - next_token: Token for next page of results (if available)
        """
        try:
            # Handle optional parameters
            max_results_value = int(max_results) if max_results is not None else 25
            next_token_value = _get_param_value(next_token)
            status_value = _get_param_value(status)

            logger.info('Listing domains')
            params: Dict[str, Any] = {
                'maxResults': min(max_results_value, 25)
            }  # Ensure maxResults is within valid range
            if next_token_value:  # pragma: no cover
                params['nextToken'] = (
                    next_token_value  # Fixed: Amazon API expects 'nextToken', not 'next_token'
                )
            if status_value:  # pragma: no cover
                params['status'] = status_value

            response = datazone_client.list_domains(**params)
            result = {'items': [], 'next_token': response.get('nextToken')}

            # Format each domain unit
            for domain in response.get('items', []):
                formatted_domain = {
                    'arn': domain.get('arn'),
                    'createdAt': domain.get('createdAt'),
                    'description': domain.get('description'),
                    'domainVersion': domain.get('domainVersion'),
                    'id': domain.get('id'),
                    'lastUpdatedAt': domain.get('lastUpdatedAt'),
                    'managedAccountId': domain.get('managedAccountId'),
                    'name': domain.get('name'),
                    'portalUrl': domain.get('portalUrl'),
                    'status': domain.get('status'),
                }
                result['items'].append(formatted_domain)

            logger.info('Successfully listed domains')
            return result
        except ClientError as e:  # pragma: no cover
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDeniedException':  # pragma: no cover
                logger.error('Access denied while listing domains')
                raise Exception('Access denied while listing domains')
            elif error_code == 'InternalServerException':  # pragma: no cover
                logger.error(
                    'The request has failed because of an unknown error, exception or failure'
                )
                raise Exception(
                    'The request has failed because of an unknown error, exception or failure'
                )
            elif error_code == 'ThrottlingException':  # pragma: no cover
                logger.error('The request was denied due to request throttling')
                raise Exception('The request was denied due to request throttling')
            elif error_code == 'ConflictException':  # pragma: no cover
                logger.error('There is a conflict listing the domains')
                raise Exception('There is a conflict listing the domains')
            elif error_code == 'UnauthorizedException':  # pragma: no cover
                logger.error('Insufficient permission to list domains')
                raise Exception('Insufficient permission to list domains')
            elif error_code == 'ValidationException':  # pragma: no cover
                logger.error(
                    'input fails to satisfy the constraints specified by the Amazon service'
                )
                raise Exception(
                    'input fails to satisfy the constraints specified by the Amazon service'
                )
            elif error_code == 'ResourceNotFoundException':  # pragma: no cover
                logger.error(
                    'input fails to satisfy the constraints specified by the Amazon service'
                )
                raise Exception(
                    'input fails to satisfy the constraints specified by the Amazon service'
                )
        except Exception:  # pragma: no cover
            logger.error('Unexpected error listing domains')
            raise Exception('Unexpected error listing domains')

    @mcp.tool()
    async def create_domain_unit(
        domain_identifier: str = Field(..., description="The identifier of the domain"),
        name: str = Field(..., description="The name of the domain unit"),
        parent_domain_unit_identifier: str = Field(..., description="The identifier of the parent domain unit"),
        description: Optional[str] = Field(default=None, description="Description of the domain unit"),
        client_token: Optional[str] = Field(default=None, description="Token for idempotency"),
    ) -> Dict[str, Any]:
        r"""Creates a new domain unit in Amazon DataZone.

        Args:
            domain_identifier (str): The ID of the domain where the domain unit will be created
                Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
            name (str): The name of the domain unit (1-128 characters)
                Pattern: ^[\\w -]+$
            parent_domain_unit_identifier (str): The ID of the parent domain unit
                Pattern: ^[a-z0-9_-]+$
            description (str, optional): Description of the domain unit (0-2048 characters)
            client_token (str, optional): A unique token to ensure idempotency (1-128 characters)
                Pattern: ^[\\x21-\\x7E]+$

        Returns:
            Dict containing:
                - id: Domain unit identifier
                - name: Domain unit name
                - description: Domain unit description
                - domain_id: Domain ID
                - parent_domain_unit_id: Parent domain unit ID
                - ancestor_domain_unit_ids: List of ancestor domain unit IDs
                - created_at: Creation timestamp
                - created_by: Creator information
                - owners: List of domain unit owners
        """
        try:
            # Handle optional parameters
            description_value = _get_param_value(description)
            client_token_value = _get_param_value(client_token)

            logger.info(f"Creating domain unit '{name}' in domain {domain_identifier}")

            # Prepare request parameters
            params = {
                'domainIdentifier': domain_identifier,
                'name': name,
                'parentDomainUnitIdentifier': parent_domain_unit_identifier,
            }

            # Add optional parameters
            if description_value:  # pragma: no cover
                params['description'] = description_value
            if client_token_value:  # pragma: no cover
                params['clientToken'] = client_token_value

            # Create the domain unit
            response = datazone_client.create_domain_unit(**params)

            # Format the response
            result = {
                'id': response.get('id'),
                'name': response.get('name'),
                'description': response.get('description'),
                'domain_id': response.get('domainId'),
                'parent_domain_unit_id': response.get('parentDomainUnitId'),
                'ancestor_domain_unit_ids': response.get('ancestorDomainUnitIds', []),
                'created_at': response.get('createdAt'),
                'created_by': response.get('createdBy'),
                'owners': response.get('owners', []),
            }

            logger.info(f"Successfully created domain unit '{name}' in domain {domain_identifier}")
            return result

        except ClientError as e:  # pragma: no cover
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDeniedException':  # pragma: no cover
                logger.error(
                    f"Access denied while creating domain unit '{name}' in domain {domain_identifier}"
                )
                raise Exception(
                    f"Access denied while creating domain unit '{name}' in domain {domain_identifier}"
                )
            elif error_code == 'ConflictException':  # pragma: no cover
                logger.error(f"Domain unit '{name}' already exists in domain {domain_identifier}")
                raise Exception(
                    f"Domain unit '{name}' already exists in domain {domain_identifier}"
                )
            elif error_code == 'ServiceQuotaExceededException':  # pragma: no cover
                logger.error(
                    f"Service quota exceeded while creating domain unit '{name}' in domain {domain_identifier}"
                )
                raise Exception(
                    f"Service quota exceeded while creating domain unit '{name}' in domain {domain_identifier}"
                )
            elif error_code == 'ValidationException':  # pragma: no cover
                logger.error(
                    f"Invalid parameters for creating domain unit '{name}' in domain {domain_identifier}"
                )
                raise Exception(
                    f"Invalid parameters for creating domain unit '{name}' in domain {domain_identifier}"
                )
            else:  # pragma: no cover
                logger.error(
                    f"Error creating domain unit '{name}' in domain {domain_identifier}: {str(e)}"
                )
                raise Exception(
                    f"Error creating domain unit '{name}' in domain {domain_identifier}: {str(e)}"
                )
        except Exception as e:  # pragma: no cover
            logger.error(
                f"Unexpected error creating domain unit '{name}' in domain {domain_identifier}: {str(e)}"
            )
            raise Exception(
                f"Unexpected error creating domain unit '{name}' in domain {domain_identifier}: {str(e)}"
            )

    @mcp.tool()
    async def get_domain_unit(
        domain_identifier: str = Field(..., description="The identifier of the domain"),
        identifier: str = Field(..., description="The identifier of the domain unit")
    ) -> Dict[str, Any]:
        """Retrieves detailed information about a specific domain unit in Amazon DataZone.

        Args:
            domain_identifier (str): The ID of the domain where the domain unit exists
                Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
            identifier (str): The ID of the domain unit to retrieve
                Pattern: ^[a-z0-9_-]+$

        Returns:
            Dict containing:
                - id: Domain unit identifier
                - name: Domain unit name
                - description: Domain unit description
                - domain_id: Domain ID
                - parent_domain_unit_id: Parent domain unit ID
                - created_at: Creation timestamp
                - created_by: Creator information
                - owners: List of domain unit owners
                - lastUpdatedAt: The timestamp at which the domain unit was last updated
                - lastUpdatedBy: The user who last updated the domain unit
        """
        try:
            logger.info(f'Getting domain unit {identifier} in domain {domain_identifier}')

            # Get the domain unit
            response = datazone_client.get_domain_unit(
                domainIdentifier=domain_identifier, identifier=identifier
            )

            # Format the response
            result = {
                'id': response.get('id'),
                'name': response.get('name'),
                'description': response.get('description'),
                'domain_id': response.get('domainId'),
                'parent_domain_unit_id': response.get('parentDomainUnitId'),
                'created_at': response.get('createdAt'),
                'created_by': response.get('createdBy'),
                'owners': response.get('owners', []),
                'lastUpdatedAt': response.get('lastUpdatedAt'),
                'lastUpdatedBy': response.get('lastUpdatedBy'),
            }

            logger.info(
                f'Successfully retrieved domain unit {identifier} in domain {domain_identifier}'
            )
            return result

        except ClientError as e:  # pragma: no cover
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDeniedException':  # pragma: no cover
                logger.error(
                    f'Access denied while getting domain unit {identifier} in domain {domain_identifier}'
                )
                raise Exception(
                    f'Access denied while getting domain unit {identifier} in domain {domain_identifier}'
                )
            elif error_code == 'ResourceNotFoundException':  # pragma: no cover
                logger.error(f'Domain unit {identifier} not found in domain {domain_identifier}')
                raise Exception(
                    f'Domain unit {identifier} not found in domain {domain_identifier}'
                )
            else:  # pragma: no cover
                logger.error(
                    f'Error getting domain unit {identifier} in domain {domain_identifier}: {str(e)}'
                )
                raise Exception(
                    f'Error getting domain unit {identifier} in domain {domain_identifier}: {str(e)}'
                )
        except Exception as e:  # pragma: no cover
            logger.error(
                f'Unexpected error getting domain unit {identifier} in domain {domain_identifier}: {str(e)}'
            )
            raise Exception(
                f'Unexpected error getting domain unit {identifier} in domain {domain_identifier}: {str(e)}'
            )

    @mcp.tool()
    async def add_entity_owner(
        domain_identifier: str = Field(..., description="The identifier of the domain"),
        entity_identifier: str = Field(..., description="The identifier of the entity"),
        owner_identifier: str = Field(..., description="The identifier of the owner"),
        entity_type: str = Field(default='DOMAIN_UNIT', description="The type of the entity"),
        owner_type: str = Field(default='USER', description="The type of the owner"),
        client_token: Optional[str] = Field(default=None, description="Token for idempotency"),
    ) -> Any:
        """Adds an owner to an entity (domain unit or project) in Amazon DataZone.

        Args:
            domain_identifier (str): The ID of the domain
            entity_identifier (str): The ID or name of the entity (domain unit or project) to add the owner to
            owner_identifier (str): The identifier of the owner to add (can be IAM ARN for users)
            entity_type (str, optional): The type of entity (DOMAIN_UNIT or PROJECT, default: DOMAIN_UNIT)
            owner_type (str, optional): The type of owner (default: "USER")
            client_token (str, optional): A unique token to ensure idempotency

        Returns:
            Any: The API response
        """
        try:
            # Handle optional parameters
            client_token_value = _get_param_value(client_token)

            logger.info(
                f'Adding owner {owner_identifier} to {entity_type.lower()} {entity_identifier} in domain {domain_identifier}'
            )
            # Validate entity type
            if entity_type not in ['DOMAIN_UNIT', 'PROJECT']:
                raise ValueError("entity_type must be either 'DOMAIN_UNIT' or 'PROJECT'")

            # Prepare the owner object
            owner = {'type': owner_type}

            # Handle IAM ARN format
            # TODO
            if owner_identifier.startswith('arn:aws:iam::'):
                # Extract the username from the ARN
                username = owner_identifier.split('/')[-1]
                owner['identifier'] = username
            else:
                owner['identifier'] = owner_identifier

            # Prepare the request parameters
            params = {'entityType': entity_type, 'owner': owner}

            # Add optional client token if provided
            if client_token_value:  # pragma: no cover
                params['clientToken'] = client_token_value

            response = datazone_client.add_entity_owner(
                domainIdentifier=domain_identifier, entityIdentifier=entity_identifier, **params
            )
            logger.info(
                f'Successfully added owner {owner_identifier} to {entity_type.lower()} {entity_identifier} in domain {domain_identifier}'
            )
            return response
        except ClientError as e:  # pragma: no cover
            raise Exception(
                f'Error adding owner to {entity_type.lower()} {entity_identifier} in domain {domain_identifier}: {e}'
            )

    @mcp.tool()
    async def add_policy_grant(
        domain_identifier: str = Field(..., description="The identifier of the domain"),
        entity_identifier: str = Field(..., description="The identifier of the entity"),
        entity_type: str = Field(..., description="The type of the entity"),
        policy_type: str = Field(..., description="The type of the policy"),
        principal_identifier: str = Field(..., description="The identifier of the principal"),
        principal_type: str = Field(default='USER', description="The type of the principal"),
        client_token: Optional[str] = Field(default=None, description="Token for idempotency"),
        detail: Optional[dict] = Field(default=None, description="Additional policy details"),
    ) -> Any:
        """Adds a policy grant to a specified entity in Amazon DataZone.

        Args:
            domain_identifier (str): The ID of the domain
            entity_identifier (str): The ID of the entity to add the policy grant to
            entity_type (str): The type of entity (DOMAIN_UNIT, ENVIRONMENT_BLUEPRINT_CONFIGURATION, or ENVIRONMENT_PROFILE)
            policy_type (str): The type of policy to grant (e.g., CREATE_DOMAIN_UNIT, OVERRIDE_DOMAIN_UNIT_OWNERS, etc.)
            principal_identifier (str): The identifier of the principal to grant permissions to
            principal_type (str, optional): The type of principal (default: "USER")
            client_token (str, optional): A unique token to ensure idempotency
            detail (dict, optional): Additional details for the policy grant

        Returns:
            Any: The API response
        """
        try:
            # Handle optional parameters
            client_token_value = _get_param_value(client_token)
            detail_value = _get_param_value(detail)

            logger.info(
                f'Adding policy {policy_type.lower()} to {principal_type.lower()} {principal_identifier} for {entity_type.lower()} {entity_identifier} in domain {domain_identifier}'
            )
            # Prepare the request parameters
            params = {
                'policyType': policy_type,
                'principal': {'identifier': principal_identifier, 'type': principal_type},
            }

            # Add optional parameters if provided
            if client_token_value:  # pragma: no cover
                params['clientToken'] = client_token_value
            if detail_value:  # pragma: no cover
                params['detail'] = detail_value

            response = datazone_client.add_policy_grant(
                domainIdentifier=domain_identifier,
                entityIdentifier=entity_identifier,
                entityType=entity_type,
                **params,
            )
            logger.info(
                f'Successfully added policy {policy_type.lower()} to {principal_type.lower()} {principal_identifier} for {entity_type.lower()} {entity_identifier} in domain {domain_identifier}'
            )
            return response
        except ClientError as e:  # pragma: no cover
            raise Exception(
                f'Error adding policy grant to entity {entity_identifier} in domain {domain_identifier}: {e}'
            )

    @mcp.tool()
    async def search(
        domain_identifier: str = Field(..., description="The identifier of the domain"),
        search_scope: str = Field(..., description="The scope of the search"),
        additional_attributes: Optional[List[str]] = Field(default=None, description="Additional attributes to include"),
        filters: Optional[Dict[str, Any]] = Field(default=None, description="Filters to apply to the search"),
        max_results: int = Field(default=50, description="Maximum number of results to return"),
        next_token: Optional[str] = Field(default=None, description="Token for pagination"),
        owning_project_identifier: Optional[str] = Field(default=None, description="The identifier of the owning project"),
        search_in: Optional[List[Dict[str, str]]] = Field(default=None, description="Attributes to search in"),
        search_text: Optional[str] = Field(default=None, description="Text to search for"),
        sort: Optional[Dict[str, str]] = Field(default=None, description="Sorting criteria"),
    ) -> Any:
        """Search across **multiple entity types**, such as: assets, glossary, glossary term, data product, etc. based on keywords, metadata, or filters.

        This API is designed for **broad discovery**, not detailed inspection of specific items.

        Do **not** use this if the user asks for detailed information about a known asset.

        Use when:
        - A user is **exploring** datasets by theme (e.g., “sales” or “IoT”)
        - Searching by keyword, tag, or business term
        - Filtering results by project, type, or glossary

        Args:
            domain_identifier (str): The identifier of the Amazon DataZone domain
                Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
            search_scope (str): The scope of the search
                Valid Values: ASSET | GLOSSARY | GLOSSARY_TERM | DATA_PRODUCT
            additional_attributes (List[str], optional): Specifies additional attributes for the search
                Valid Values: FORMS | TIME_SERIES_DATA_POINT_FORMS
            filters (Dict[str, Any], optional): Specifies the search filters
                Type: FilterClause object (Union type)
            max_results (int, optional): Maximum number of results to return (1-50, default: 50)
            next_token (str, optional): Token for pagination (1-8192 characters)
            owning_project_identifier (str, optional): The identifier of the owning project
                Pattern: ^[a-zA-Z0-9_-]{1,36}$
            search_in (List[Dict[str, str]], optional): The details of the search
                Array Members: 1-10 items
                Each item contains:
                    - attribute (str): The attribute to search in
            search_text (str, optional): The text to search for (1-4096 characters)
            sort (Dict[str, str], optional): Specifies how to sort the results
                Contains:
                    - attribute (str): The attribute to sort by
                    - order (str): The sort order (ASCENDING | DESCENDING)

        Returns:
            Any: The API response containing:
                - items (list): The search results
                - nextToken (str): Token for pagination if more results are available
                - totalMatchCount (int): Total number of search results

        Example:
            ```python
            response = await search(
                domain_identifier='dzd-1234567890',
                search_scope='ASSET',
                search_text='customer data',
                search_in=[{'attribute': 'name'}, {'attribute': 'description'}],
                sort={'attribute': 'name', 'order': 'ASCENDING'},
                max_results=25,
            )
            ```
        """
        try:
            # Handle optional parameters
            additional_attributes_value = _get_param_value(additional_attributes)
            filters_value = _get_param_value(filters)
            max_results_value = int(max_results) if max_results is not None else 50
            next_token_value = _get_param_value(next_token)
            owning_project_identifier_value = _get_param_value(owning_project_identifier)
            search_in_value = _get_param_value(search_in)
            search_text_value = _get_param_value(search_text)
            sort_value = _get_param_value(sort)

            logger.info(f'Searching {search_scope.lower()} in domain {domain_identifier}')
            # Validate search_scope
            valid_scopes = ['ASSET', 'GLOSSARY', 'GLOSSARY_TERM', 'DATA_PRODUCT']
            if search_scope not in valid_scopes:
                raise ValueError(f'search_scope must be one of {valid_scopes}')

            # Prepare the request parameters
            params = {
                'domainIdentifier': domain_identifier,
                'searchScope': search_scope,
                'maxResults': min(max_results_value, 50),  # Ensure maxResults is within valid range
            }

            # Add optional parameters if provided
            if additional_attributes_value:  # pragma: no cover
                params['additionalAttributes'] = additional_attributes_value
            if filters_value:  # pragma: no cover
                params['filters'] = filters_value
            if next_token_value:  # pragma: no cover
                params['nextToken'] = next_token_value
            if owning_project_identifier_value:  # pragma: no cover
                params['owningProjectIdentifier'] = owning_project_identifier_value
            if search_in_value:  # pragma: no cover
                params['searchIn'] = search_in_value
            if search_text_value:  # pragma: no cover
                params['searchText'] = search_text_value
            if sort_value:  # pragma: no cover
                params['sort'] = sort_value

            response = datazone_client.search(**params)
            logger.info(
                f'Successfully searched {search_scope.lower()} in domain {domain_identifier}'
            )
            return response
        except ClientError as e:  # pragma: no cover
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDeniedException':  # pragma: no cover
                raise Exception(f'Access denied while searching in domain {domain_identifier}')
            elif error_code == 'InternalServerException':  # pragma: no cover
                raise Exception(
                    f'Internal server error while searching in domain {domain_identifier}'
                )
            elif error_code == 'ThrottlingException':  # pragma: no cover
                raise Exception(f'Request throttled while searching in domain {domain_identifier}')
            elif error_code == 'UnauthorizedException':  # pragma: no cover
                raise Exception(f'Unauthorized to search in domain {domain_identifier}')
            elif error_code == 'ValidationException':  # pragma: no cover
                raise Exception(f'Invalid input while searching in domain {domain_identifier}')
            else:  # pragma: no cover
                raise Exception(f'Error searching in domain {domain_identifier}: {str(e)}')
        except Exception as e:  # pragma: no cover
            raise Exception(f'Unexpected error searching in domain {domain_identifier}: {str(e)}')

    @mcp.tool()
    async def search_types(
        domain_identifier: str = Field(..., description="The identifier of the domain"),
        managed: bool = Field(..., description="Whether to search managed types"),
        search_scope: str = Field(..., description="The scope of the search"),
        filters: Optional[Dict[str, Any]] = Field(default=None, description="Filters to apply to the search"),
        max_results: int = Field(default=50, description="Maximum number of results to return"),
        next_token: Optional[str] = Field(default=None, description="Token for pagination"),
        search_in: Optional[List[Dict[str, str]]] = Field(default=None, description="Attributes to search in"),
        search_text: Optional[str] = Field(default=None, description="Text to search for"),
        sort: Optional[Dict[str, str]] = Field(default=None, description="Sorting criteria"),
    ) -> Any:
        """Invokes the SearchTypes action in a specified Amazon DataZone domain to retrieve type definitions.

        (e.g., asset types, form types, or lineage node types) that match the search criteria.

        Args:
            domain_identifier (str): The identifier of the Amazon DataZone domain in which to invoke the SearchTypes action.
                Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$ (Required)

            managed (bool): Whether the search is for managed types. (Required)

            filters (dict, optional): A FilterClause object specifying a single filter for the search.
                Only one member of the union type may be used.

            max_results (int, optional): The maximum number of results to return in a single call.
                Valid range: 1–50. Default is service-defined.

            next_token (str, optional): Token for paginating results. Used to retrieve the next page of results
                when the number of results exceeds max_results.
                Length constraints: 1–8192 characters.

            search_in (List[dict], optional): A list of SearchInItem objects specifying search fields.
                Minimum of 1 item, maximum of 10.

            search_scope (str): The scope of the search. Valid values:
                "ASSET_TYPE", "FORM_TYPE", "LINEAGE_NODE_TYPE". (Required)

            search_text (str, optional): The free-text string to search for.
                Length constraints: 1–4096 characters.

            sort (dict, optional): A SearchSort object specifying how to sort the results.

        Returns:
            dict: A response object containing:
                - items (List[dict]): A list of SearchTypesResultItem objects matching the query.
                - nextToken (str): A pagination token for retrieving the next set of results.
                - totalMatchCount (int): Total number of matching items.
        """
        try:
            # Handle optional parameters
            filters_value = _get_param_value(filters)
            max_results_value = int(max_results) if max_results is not None else 50
            next_token_value = _get_param_value(next_token)
            search_in_value = _get_param_value(search_in)
            search_text_value = _get_param_value(search_text)
            sort_value = _get_param_value(sort)

            logger.info(f'Searching types {search_scope.lower()} in domain {domain_identifier}')
            # Validate search_scope
            valid_scopes = ['ASSET_TYPE', 'FORM_TYPE', 'LINEAGE_NODE_TYPE']
            if search_scope not in valid_scopes:
                raise ValueError(f'search_scope must be one of {valid_scopes}')

            # Prepare the request parameters
            params = {
                'domainIdentifier': domain_identifier,
                'searchScope': search_scope,
                'maxResults': min(max_results_value, 50),  # Ensure maxResults is within valid range
                'managed': managed,
            }

            # Add optional parameters if provided
            if filters_value:  # pragma: no cover
                params['filters'] = filters_value
            if next_token_value:  # pragma: no cover
                params['nextToken'] = next_token_value
            if search_in_value:  # pragma: no cover
                params['searchIn'] = search_in_value
            if search_text_value:  # pragma: no cover
                params['searchText'] = search_text_value
            if sort_value:  # pragma: no cover
                params['sort'] = sort_value

            response = datazone_client.search_types(**params)
            logger.info(
                f'Successfully searched types {search_scope.lower()} in domain {domain_identifier}'
            )
            return response
        except ClientError as e:  # pragma: no cover
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDeniedException':  # pragma: no cover
                raise Exception(
                    f'Access denied while searching types in domain {domain_identifier}'
                )
            elif error_code == 'InternalServerException':  # pragma: no cover
                raise Exception(
                    f'Internal server error while searching types in domain {domain_identifier}'
                )
            elif error_code == 'ThrottlingException':  # pragma: no cover
                raise Exception(
                    f'Request throttled while searching types in domain {domain_identifier}'
                )
            elif error_code == 'UnauthorizedException':  # pragma: no cover
                raise Exception(f'Unauthorized to search types in domain {domain_identifier}')
            elif error_code == 'ValidationException':  # pragma: no cover
                raise Exception(
                    f'Invalid input while searching types in domain {domain_identifier}'
                )
            else:  # pragma: no cover
                raise Exception(f'Error searching types in domain {domain_identifier}: {str(e)}')
        except Exception as e:  # pragma: no cover
            raise Exception(
                f'Unexpected error searching types in domain {domain_identifier}: {str(e)}'
            )

    @mcp.tool()
    async def get_user_profile(
        domain_identifier: str = Field(..., description="The identifier of the domain"),
        user_identifier: str = Field(..., description="The identifier of the user"),
        user_type: Optional[str] = Field(default=None, description="The type of the user")
    ) -> Any:
        r"""Retrieves the user profile in a specified Amazon DataZone domain for one given user.

        get_user_profile is for retrieving a specific user's details (especially related to roles and access), while search_user_profiles is for discovering users based on filters.

        Args:
            domain_identifier (str): The ID of the Amazon DataZone domain from which to retrieve the user profile.
                Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
                Required: Yes

            user_type (str): The type of the user profile.
                Valid values: "IAM" | "SSO"

            user_identifier (str): The identifier of the user for whom to retrieve the profile.
                Pattern: r"(^([0-9a-f]{10}-|)[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]
                {4}-[A-Fa-f0-9]{12}$|^[a-zA-Z_0-9+=,.@-]+$|^arn:aws:iam::\d{12}:.+$)"
                Required: Yes

        Returns:
            dict: A response object containing:
                - details (dict): A UserProfileDetails object with specific IAM or SSO profile data.
                - domainId (str): The identifier of the DataZone domain.
                - id (str): The identifier of the user profile.
                - status (str): The status of the user profile. Valid values: "ASSIGNED", "NOT_ASSIGNED", "ACTIVATED", "DEACTIVATED".
                - type (str): The type of the user profile. Valid values: "IAM", "SSO".
        """
        try:
            # Handle optional parameters
            user_type_value = _get_param_value(user_type)

            params = {'domainIdentifier': domain_identifier, 'userIdentifier': user_identifier}

            # Add optional parameters if provided
            if user_type_value:  # pragma: no cover
                valid_types = ['IAM', 'SSO']
                if user_type_value not in valid_types:  # pragma: no cover
                    raise ValueError(f'user_type must be one of {valid_types}')
                params['type'] = user_type_value
            response = datazone_client.get_user_profile(**params)
            return response
        except ClientError as e:  # pragma: no cover
            raise Exception(
                f'Error getting user {user_identifier} profile in domain {domain_identifier}: {e}'
            )

    @mcp.tool()
    async def search_user_profiles(
        domain_identifier: str = Field(..., description="The identifier of the domain"),
        user_type: str = Field(..., description="The type of the user"),
        max_results: int = Field(default=50, description="Maximum number of results to return"),
        next_token: Optional[str] = Field(default=None, description="Token for pagination"),
        search_text: Optional[str] = Field(default=None, description="Text to search for"),
    ) -> Any:
        """Searches for user profiles within a specified Amazon DataZone domain.

        This API supports filtering results by user type and search text, as well as pagination through `maxResults` and `nextToken`.

        get_user_profile is for retrieving a specific user's details (especially related to roles and access), while search_user_profiles is for discovering users based on filters.

        Args:
            domain_identifier (str): The identifier of the Amazon DataZone domain in which to perform the search.
                Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
                Required: Yes

            max_results (int, optional): The maximum number of user profiles to return in a single call.
                Valid Range: 1–50
                Required: No

            next_token (str, optional): Pagination token from a previous response. Use to retrieve the next page of results.
                Min length: 1, Max length: 8192
                Required: No

            search_text (str, optional): Text to search for in user profiles.
                Max length: 1024
                Required: No

            user_type (str): The type of user profile to search for.
                Valid values:
                    - "SSO_USER"
                    - "DATAZONE_USER"
                    - "DATAZONE_SSO_USER"
                    - "DATAZONE_IAM_USER"
                Required: Yes

        Returns:
            dict: A response object containing:
                - items (List[dict]): A list of user profile summaries. Each summary includes:
                    - details (dict): UserProfileDetails (union type)
                    - domainId (str): Domain ID the user profile belongs to.
                    - id (str): The identifier of the user profile.
                    - status (str): Profile status. Possible values: "ASSIGNED", "NOT_ASSIGNED", "ACTIVATED", "DEACTIVATED".
                    - type (str): Type of the user profile. Possible values: "IAM", "SSO".
                - nextToken (str, optional): Token for paginated responses.
                    Min length: 1, Max length: 8192
        """
        try:
            # Handle optional parameters
            max_results_value = int(max_results) if max_results is not None else 50
            next_token_value = _get_param_value(next_token)
            search_text_value = _get_param_value(search_text)

            logger.info(f'Searching {user_type} user profiles in domain {domain_identifier}')
            # Validate user_type
            valid_types = ['SSO_USER', 'DATAZONE_USER', 'DATAZONE_SSO_USER', 'DATAZONE_IAM_USER']
            if user_type not in valid_types:
                raise ValueError(f'user_type must be one of {valid_types}')

            # Prepare the request parameters
            params = {
                'domainIdentifier': domain_identifier,
                'userType': user_type,
                'maxResults': min(max_results_value, 50),
            }

            # Add optional parameters if provided
            if search_text_value:  # pragma: no cover
                params['searchText'] = search_text_value
            if next_token_value:  # pragma: no cover
                params['nextToken'] = next_token_value

            response = datazone_client.search_user_profiles(**params)
            logger.info(
                f'Successfully searched {user_type} user profiles in domain {domain_identifier}'
            )
            return response
        except ClientError as e:  # pragma: no cover
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDeniedException':  # pragma: no cover
                raise Exception(
                    f'Access denied while searching {user_type} user profiles in domain {domain_identifier}'
                )
            elif error_code == 'InternalServerException':  # pragma: no cover
                raise Exception(
                    f'Internal server error while searching {user_type} user profiles in domain {domain_identifier}'
                )
            elif error_code == 'ThrottlingException':  # pragma: no cover
                raise Exception(
                    f'Request throttled while searching {user_type} user profiles in domain {domain_identifier}'
                )
            elif error_code == 'UnauthorizedException':  # pragma: no cover
                raise Exception(
                    f'Unauthorized to search {user_type} user profiles in domain {domain_identifier}'
                )
            elif error_code == 'ValidationException':  # pragma: no cover
                raise Exception(
                    f'Invalid input while searching {user_type} user profiles in domain {domain_identifier}'
                )
            else:  # pragma: no cover
                raise Exception(
                    f'Error searching {user_type} user profiles in domain {domain_identifier}: {str(e)}'
                )
        except Exception as e:  # pragma: no cover
            raise Exception(
                f'Unexpected error searching t{user_type} user profiles in domain {domain_identifier}: {str(e)}'
            )

    @mcp.tool()
    async def search_group_profiles(
        domain_identifier: str = Field(..., description="The identifier of the domain"),
        group_type: str = Field(..., description="The type of the group"),
        max_results: int = Field(default=50, description="Maximum number of results to return"),
        next_token: Optional[str] = Field(default=None, description="Token for pagination"),
        search_text: Optional[str] = Field(default=None, description="Text to search for"),
    ) -> Any:
        """Searches for group profiles within a specified Amazon DataZone domain.

        This operation allows you to find groups by specifying a group type and optional search text. Pagination is supported through `maxResults` and `nextToken`.

        Args:
            domain_identifier (str): The identifier of the Amazon DataZone domain in which to search group profiles.
                Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
                Required: Yes

            group_type (str): The type of group to search for.
                Valid values:
                    - "SSO_GROUP"
                    - "DATAZONE_SSO_GROUP"
                Required: Yes

            max_results (int, optional): The maximum number of results to return in a single call.
                Valid range: 1–50
                Required: No

            next_token (str, optional): Pagination token from a previous response. Use this to retrieve the next set of results.
                Length: 1–8192 characters
                Required: No

            search_text (str, optional): Free-text string used to filter group profiles.
                Max length: 1024
                Required: No

        Returns:
            dict: A response object containing:
                - items (List[dict]): A list of group profile summaries. Each summary includes:
                    - domainId (str): The domain to which the group belongs.
                    - groupName (str): The name of the group.
                    - id (str): The unique identifier of the group profile.
                    - status (str): The current status of the group profile.
                - nextToken (str, optional): A token to retrieve the next page of results, if more are available.
                    Length: 1–8192 characters

        Raises:
            HTTPError: If the API request fails or returns an error.
        """
        try:
            # Handle optional parameters
            max_results_value = int(max_results) if max_results is not None else 50
            next_token_value = _get_param_value(next_token)
            search_text_value = _get_param_value(search_text)

            logger.info(f'Searching {group_type} group profiles in domain {domain_identifier}')
            # Validate user_type
            valid_types = ['SSO_GROUP', 'DATAZONE_SSO_GROUP']
            if group_type not in valid_types:
                raise ValueError(f'group_type must be one of {valid_types}')

            # Prepare the request parameters
            params = {
                'domainIdentifier': domain_identifier,
                'groupType': group_type,
                'maxResults': min(max_results_value, 50),
            }

            # Add optional parameters if provided
            if search_text_value:  # pragma: no cover
                params['searchText'] = search_text_value
            if next_token_value:  # pragma: no cover
                params['nextToken'] = next_token_value

            response = datazone_client.search_group_profiles(**params)
            logger.info(
                f'Successfully searched {group_type} group profiles in domain {domain_identifier}'
            )
            return response
        except ClientError as e:  # pragma: no cover
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDeniedException':  # pragma: no cover
                raise Exception(
                    f'Access denied while searching {group_type} group profiles in domain {domain_identifier}'
                )
            elif error_code == 'InternalServerException':  # pragma: no cover
                raise Exception(
                    f'Internal server error while searching {group_type} group profiles in domain {domain_identifier}'
                )
            elif error_code == 'ThrottlingException':  # pragma: no cover
                raise Exception(
                    f'Request throttled while searching {group_type} group profiles in domain {domain_identifier}'
                )
            elif error_code == 'UnauthorizedException':  # pragma: no cover
                raise Exception(
                    f'Unauthorized to search {group_type} group profiles in domain {domain_identifier}'
                )
            elif error_code == 'ValidationException':  # pragma: no cover
                raise Exception(
                    f'Invalid input while searching {group_type} group profiles in domain {domain_identifier}'
                )
            else:  # pragma: no cover
                raise Exception(
                    f'Error searching {group_type} group profiles in domain {domain_identifier}: {str(e)}'
                )
        except Exception as e:  # pragma: no cover
            raise Exception(
                f'Unexpected error searching t{group_type} group profiles in domain {domain_identifier}: {str(e)}'
            )

    # Return the decorated functions for testing purposes
    return {
        'get_domain': get_domain,
        'create_domain': create_domain,
        'list_domain_units': list_domain_units,
        'list_domains': list_domains,
        'create_domain_unit': create_domain_unit,
        'get_domain_unit': get_domain_unit,
        'add_entity_owner': add_entity_owner,
        'add_policy_grant': add_policy_grant,
        'search': search,
        'search_types': search_types,
        'get_user_profile': get_user_profile,
        'search_user_profiles': search_user_profiles,
        'search_group_profiles': search_group_profiles,
    }
