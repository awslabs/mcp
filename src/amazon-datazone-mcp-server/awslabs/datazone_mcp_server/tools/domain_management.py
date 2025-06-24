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

from .common import ClientError, datazone_client, logger
from mcp.server.fastmcp import FastMCP
from typing import Any, Dict, List, Optional
from pydantic import Field


def register_tools(mcp: FastMCP):
    """Register domain management tools with the MCP server."""

    @mcp.tool()
    async def get_domain(
        identifier: str = Field(..., description="The domain identifier (e.g., 'dzd_4p9n6sw4qt9xgn')")
    ) -> Any:
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
        domain_version: str = Field('V2', description="The version of the domain (V1 or V2)"),
        description: Optional[str] = Field(None, description="Description of the domain"),
        kms_key_identifier: Optional[str] = Field(None, description="ARN of the KMS key for encryption"),
        tags: Optional[Dict[str, str]] = Field(None, description="Tags to associate with the domain"),
        single_sign_on: Optional[Dict[str, str]] = Field(None, description="Single sign-on configuration"),
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
            logger.info(f'Creating {domain_version} domain: {name}')

            # Prepare request parameters
            params: Dict[str, Any] = {
                'name': name,
                'domainExecutionRole': domain_execution_role,
                'domainVersion': domain_version,
            }

            # Add optional parameters
            if description:  # pragma: no cover
                params['description'] = description
            if kms_key_identifier:  # pragma: no cover
                params['kmsKeyIdentifier'] = kms_key_identifier
            if tags:  # pragma: no cover
                params['tags'] = tags
            if single_sign_on:  # pragma: no cover
                params['singleSignOn'] = single_sign_on
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
        domain_identifier: str = Field(..., description="The identifier of the domain (e.g., 'dzd_4p9n6sw4qt9xgn')"),
        parent_domain_unit_identifier: str = Field(..., description="The identifier of the parent domain unit (e.g., '3thjq258ficc2v')")
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
        max_results: int = Field(25, description="Maximum number of results to return (default: 25, max: 25)"),
        next_token: Optional[str] = Field(None, description="Token for pagination to get next page of results"),
        status: Optional[str] = Field(None, description="Filter domains by status (e.g., 'AVAILABLE', 'CREATING', 'DELETING')")
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
            logger.info('Listing domains')
            params: Dict[str, Any] = {
                'maxResults': min(max_results, 25)
            }  # Ensure maxResults is within valid range
            if next_token:  # pragma: no cover
                params['nextToken'] = (
                    next_token  # Fixed: Amazon API expects 'nextToken', not 'next_token'
                )
            if status:  # pragma: no cover
                params['status'] = status

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
        description: Optional[str] = Field(None, description="Description of the domain unit"),
        client_token: Optional[str] = Field(None, description="A unique token for idempotency"),
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
            logger.info(f"Creating domain unit '{name}' in domain {domain_identifier}")

            # Prepare request parameters
            params = {
                'domainIdentifier': domain_identifier,
                'name': name,
                'parentDomainUnitIdentifier': parent_domain_unit_identifier,
            }

            # Add optional parameters
            if description:  # pragma: no cover
                params['description'] = description
            if client_token:  # pragma: no cover
                params['clientToken'] = client_token

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

    # @mcp.tool()
    # async def list_domain_units_for_parent(
    #     domain_identifier: str,
    #     parent_domain_unit_identifier: str,
    #     max_results: int = 25,
    #     next_token: str = None
    # ) -> Dict[str, Any]:
    #     """
    #     Lists child domain units for a specific parent domain unit in Amazon DataZone.

    #     Args:
    #         domain_identifier (str): The ID of the domain where the domain units exist
    #             Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
    #         parent_domain_unit_identifier (str): The ID of the parent domain unit
    #             Pattern: ^[a-z0-9_-]+$
    #         max_results (int, optional): Maximum number of domain units to return (1-50, default: 50)
    #         next_token (str, optional): Token for pagination (1-8192 characters)

    #     Returns:
    #         Dict containing:
    #             - items: List of domain units, each containing:
    #                 - id: Domain unit identifier
    #                 - name: Domain unit name
    #             - next_token: Token for pagination if more results are available
    #     """
    #     try:
    #         logger.info(f"Listing domain units for parent {parent_domain_unit_identifier} in domain {domain_identifier}")

    #         # Prepare request parameters
    #         params = {
    #             'domainIdentifier': domain_identifier,
    #             'parentDomainUnitIdentifier': parent_domain_unit_identifier,
    #             'maxResults': min(max_results, 25)  # Ensure maxResults is within valid range
    #         }

    #         # Add optional next token if provided
    #         if next_token:
    #             params['nextToken'] = next_token

    #         # List the domain units
    #         response = datazone_client.list_domain_units_for_parent(**params)

    #         # Format the response
    #         result = {
    #             'items': [],
    #             'next_token': response.get('nextToken')
    #         }

    #         # Format each domain unit
    #         for domain_unit in response.get('items', []):
    #             formatted_domain_unit = {
    #                 'id': domain_unit.get('id'),
    #                 'name': domain_unit.get('name')
    #             }
    #             result['items'].append(formatted_domain_unit)

    #         logger.info(f"Successfully listed {len(result['items'])} domain units for parent {parent_domain_unit_identifier} in domain {domain_identifier}")
    #         return result

    #     except ClientError as e:
    #         error_code = e.response['Error']['Code']
    #         if error_code == 'AccessDeniedException':
    #             logger.error(f"Access denied while listing domain units for parent {parent_domain_unit_identifier} in domain {domain_identifier}")
    #             raise Exception(f"Access denied while listing domain units for parent {parent_domain_unit_identifier} in domain {domain_identifier}")
    #         elif error_code == 'ResourceNotFoundException':
    #             logger.error(f"Parent domain unit {parent_domain_unit_identifier} not found in domain {domain_identifier}")
    #             raise Exception(f"Parent domain unit {parent_domain_unit_identifier} not found in domain {domain_identifier}")
    #         else:
    #             logger.error(f"Error listing domain units for parent {parent_domain_unit_identifier} in domain {domain_identifier}: {str(e)}")
    #             raise Exception(f"Error listing domain units for parent {parent_domain_unit_identifier} in domain {domain_identifier}: {str(e)}")
    #     except Exception as e:
    #         logger.error(f"Unexpected error listing domain units for parent {parent_domain_unit_identifier} in domain {domain_identifier}: {str(e)}")
    #         raise Exception(f"Unexpected error listing domain units for parent {parent_domain_unit_identifier} in domain {domain_identifier}: {str(e)}")

    # @mcp.tool()
    # async def update_domain_unit(
    #     domain_identifier: str,
    #     identifier: str,
    #     name: str = None,
    #     description: str = None
    # ) -> Dict[str, Any]:
    #     """
    #     Updates an existing domain unit in Amazon DataZone.

    #     Args:
    #         domain_identifier (str): The ID of the domain where the domain unit exists
    #             Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
    #         identifier (str): The ID of the domain unit to update
    #             Pattern: ^[a-z0-9_-]+$
    #         name (str, optional): New name for the domain unit (1-128 characters)
    #             Pattern: ^[\\w -]+$
    #         description (str, optional): New description for the domain unit (0-2048 characters)

    #     Returns:
    #         Dict containing:
    #             - id: Domain unit identifier
    #             - name: Updated domain unit name
    #             - description: Updated domain unit description
    #             - domain_id: Domain ID
    #             - parent_domain_unit_id: Parent domain unit ID
    #             - created_at: Creation timestamp
    #             - created_by: Creator information
    #             - owners: List of domain unit owners
    #             - last_updated_at: Last update timestamp
    #             - last_updated_by: Last updater information
    #     """
    #     try:
    #         logger.info(f"Updating domain unit {identifier} in domain {domain_identifier}")

    #         # Prepare request parameters
    #         params = {
    #             'domainIdentifier': domain_identifier,
    #             'identifier': identifier
    #         }

    #         # Add optional parameters
    #         if name:
    #             params['name'] = name
    #         if description:
    #             params['description'] = description
    #         # if client_token:
    #         #     params['clientToken'] = client_token

    #         # Update the domain unit
    #         response = datazone_client.update_domain_unit(**params)

    #         # Format the response
    #         result = {
    #             'id': response.get('id'),
    #             'name': response.get('name'),
    #             'description': response.get('description'),
    #             'domain_id': response.get('domainId'),
    #             'parent_domain_unit_id': response.get('parentDomainUnitId'),
    #             'created_at': response.get('createdAt'),
    #             'created_by': response.get('createdBy'),
    #             'owners': response.get('owners', []),
    #             'updated_at': response.get('updatedAt'),
    #             'updated_by': response.get('updatedBy')
    #         }

    #         logger.info(f"Successfully updated domain unit {identifier} in domain {domain_identifier}")
    #         return result

    #     except ClientError as e:
    #         error_code = e.response['Error']['Code']
    #         if error_code == 'AccessDeniedException':
    #             logger.error(f"Access denied while updating domain unit {identifier} in domain {domain_identifier}")
    #             raise Exception(f"Access denied while updating domain unit {identifier} in domain {domain_identifier}")
    #         elif error_code == 'ResourceNotFoundException':
    #             logger.error(f"Domain unit {identifier} not found in domain {domain_identifier}")
    #             raise Exception(f"Domain unit {identifier} not found in domain {domain_identifier}")
    #         elif error_code == 'ValidationException':
    #             logger.error(f"Invalid parameters for updating domain unit {identifier} in domain {domain_identifier}")
    #             raise Exception(f"Invalid parameters for updating domain unit {identifier} in domain {domain_identifier}")
    #         else:
    #             logger.error(f"Error updating domain unit {identifier} in domain {domain_identifier}: {str(e)}")
    #             raise Exception(f"Error updating domain unit {identifier} in domain {domain_identifier}: {str(e)}")
    #     except Exception as e:
    #         logger.error(f"Unexpected error updating domain unit {identifier} in domain {domain_identifier}: {str(e)}")
    #         raise Exception(f"Unexpected error updating domain unit {identifier} in domain {domain_identifier}: {str(e)}")

    @mcp.tool()
    async def add_entity_owner(
        domain_identifier: str = Field(..., description="The identifier of the domain"),
        entity_identifier: str = Field(..., description="The identifier of the entity"),
        owner_identifier: str = Field(..., description="The identifier of the owner"),
        entity_type: str = Field('DOMAIN_UNIT', description="The type of the entity"),
        owner_type: str = Field('USER', description="The type of the owner"),
        client_token: Optional[str] = Field(None, description="A unique token for idempotency"),
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
            logger.info(
                f'Adding owner {owner_identifier} to {entity_type.lower()} {entity_identifier} in domain {domain_identifier}'
            )
            # Validate entity type
            if entity_type not in ['DOMAIN_UNIT', 'PROJECT']:
                raise ValueError("entity_type must be either 'DOMAIN_UNIT' or 'PROJECT'")

            # Prepare the owner object
            owner = {'type': owner_type}

            # Handle IAM ARN format
            if owner_identifier.startswith('arn:aws:iam::'):
                # Extract the username from the ARN
                username = owner_identifier.split('/')[-1]
                owner['identifier'] = username
            else:
                owner['identifier'] = owner_identifier

            # Prepare the request parameters
            params = {'entityType': entity_type, 'owner': owner}

            # Add optional client token if provided
            if client_token:  # pragma: no cover
                params['clientToken'] = client_token

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

    # @mcp.tool()
    # async def list_entity_owners(
    #     domain_identifier: str,
    #     entity_identifier: str,
    #     entity_type: str = "DOMAIN_UNIT",
    #     max_results: int = 25,
    #     next_token: str = None
    # ) -> Any:
    #     """
    #     Lists the owners of a specific entity in an Amazon DataZone domain.

    #     Args:
    #         domain_identifier (str): The ID of the domain in which the entity exists.
    #         entity_identifier (str): The ID of the entity whose owners are to be listed.
    #         entity_type (str): The type of the entity. Valid value: "DOMAIN_UNIT".
    #         max_results (int, optional): The maximum number of owners to return (1–25). Defaults to the service’s default.
    #         next_token (str, optional): A pagination token from a previous request. Use to retrieve the next set of results.

    #     Returns:
    #         Any: The API response containing:
    #             - A list of owner property objects (`owners`)
    #             - A pagination token (`nextToken`) if more results are available
    #     """
    #     try:
    #         logger.info(f"Listing owners of {entity_type.lower()} {entity_identifier} in domain {domain_identifier}")
    #         # Validate entity type
    #         if entity_type not in ["DOMAIN_UNIT"]:
    #             raise ValueError("entity_type must be'DOMAIN_UNIT'")

    #         # Prepare the request parameters
    #         params = {
    #             "domainIdentifier": domain_identifier,
    #             "entityIdentifier": entity_identifier,
    #             "maxResults": min(25, max_results),
    #             "entityType": entity_type
    #         }

    #         # Add optional client token if provided
    #         if next_token:
    #             params["nextToken"] = next_token

    #         response = datazone_client.list_entity_owners(**params)
    #         logger.info(f"Successfully listed owners of {entity_type.lower()} {entity_identifier} in domain {domain_identifier}")
    #         return response
    #     except ClientError as e:
    #         raise Exception(f"Error listing owners of {entity_type.lower()} {entity_identifier} in domain {domain_identifier}: {e}")

    @mcp.tool()
    async def add_policy_grant(
        domain_identifier: str = Field(..., description="The identifier of the domain"),
        entity_identifier: str = Field(..., description="The identifier of the entity"),
        entity_type: str = Field(..., description="The type of the entity"),
        policy_type: str = Field(..., description="The type of the policy"),
        principal_identifier: str = Field(..., description="The identifier of the principal"),
        principal_type: str = Field('USER', description="The type of the principal"),
        client_token: Optional[str] = Field(None, description="A unique token for idempotency"),
        detail: Optional[dict] = Field(None, description="Additional details for the policy grant"),
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
            logger.info(
                f'Adding policy {policy_type.lower()} to {principal_type.lower()} {principal_identifier} for {entity_type.lower()} {entity_identifier} in domain {domain_identifier}'
            )
            # Prepare the request parameters
            params = {
                'policyType': policy_type,
                'principal': {'identifier': principal_identifier, 'type': principal_type},
            }

            # Add optional parameters if provided
            if client_token:  # pragma: no cover
                params['clientToken'] = client_token
            if detail:  # pragma: no cover
                params['detail'] = detail

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

    # @mcp.tool()
    # async def list_policy_grants(
    #     domain_identifier: str,
    #     entity_identifier: str,
    #     entity_type: str,
    #     policy_type: str,
    #     max_results: int = 25,
    #     next_token: str = None
    # ) -> Any:
    #     """
    #     Lists policy grants for a specified entity in Amazon DataZone.

    #     Args:
    #         domain_identifier (str): The ID of the domain
    #         entity_identifier (str): The ID of the entity to list policy grants for
    #         entity_type (str): The type of entity (DOMAIN_UNIT, ENVIRONMENT_BLUEPRINT_CONFIGURATION, or ENVIRONMENT_PROFILE)
    #         policy_type (str): The type of policy to list grants for
    #         max_results (int, optional): Maximum number of grants to return (1-50, default: 50)
    #         next_token (str, optional): Token for pagination

    #     Returns:
    #         Any: The API response containing the list of policy grants
    #     """
    #     try:
    #         logger.info(f"Listing {policy_type.lower()} policy grant of {entity_type.lower()} {entity_identifier} in domain {domain_identifier}")
    #         # Prepare the request parameters
    #         params = {
    #             "domainIdentifier": domain_identifier,
    #             "entityIdentifier": entity_identifier,
    #             "entityType": entity_type,
    #             "policyType": policy_type,
    #             "maxResults": min(max_results, 25)  # Ensure maxResults is within valid range
    #         }

    #         # Add optional next token if provided
    #         if next_token:
    #             params["nextToken"] = next_token

    #         response = datazone_client.list_policy_grants(**params)
    #         logger.info(f"Successfully listed {policy_type.lower()} policy grant of {entity_type.lower()} {entity_identifier} in domain {domain_identifier}")
    #         return response
    #     except ClientError as e:
    #         raise Exception(f"Error listing policy grants for entity {entity_identifier} in domain {domain_identifier}: {e}")

    # @mcp.tool()
    # async def remove_policy_grant(
    #     domain_identifier: str,
    #     entity_identifier: str,
    #     entity_type: str,
    #     policy_type: str,
    #     principal_identifier: str,
    #     principal_type: str = "USER",
    #     client_token: str = None
    # ) -> Dict[str, Any]:
    #     """
    #     Removes a policy grant from a specified entity in Amazon DataZone.

    #     Args:
    #         domain_identifier (str): The ID of the domain
    #         entity_identifier (str): The ID of the entity to remove the policy grant from
    #         entity_type (str): The type of entity (DOMAIN_UNIT, ENVIRONMENT_BLUEPRINT_CONFIGURATION, or ENVIRONMENT_PROFILE)
    #         policy_type (str): The type of policy to remove (e.g., CREATE_DOMAIN_UNIT, OVERRIDE_DOMAIN_UNIT_OWNERS, etc.)
    #         principal_identifier (str): The identifier of the principal to remove permissions from
    #         principal_type (str, optional): The type of principal (default: "USER")
    #         client_token (str, optional): A unique token to ensure idempotency

    #     Returns:
    #         Dict[str, Any]: The API response (204 No Content on success)

    #     Raises:
    #         Exception: If there's an error removing the policy grant, with specific error messages for different types of errors
    #     """
    #     try:
    #         logger.info(f"Removing {policy_type.lower()} policy grant from {principal_type.lower()} {principal_identifier} for {entity_type.lower()} {entity_identifier} in domain {domain_identifier}")
    #         # Prepare the request parameters
    #         params = {
    #             "policyType": policy_type,
    #             "principal": {
    #                 "identifier": principal_identifier,
    #                 "type": principal_type
    #             }
    #         }

    #         # Add optional client token if provided
    #         if client_token:
    #             params["clientToken"] = client_token

    #         response = datazone_client.remove_policy_grant(
    #             domainIdentifier=domain_identifier,
    #             entityIdentifier=entity_identifier,
    #             entityType=entity_type,
    #             **params
    #         )
    #         logger.info(f"Successfully removed {policy_type.lower()} policy grant from {principal_type.lower()} {principal_identifier} for {entity_type.lower()} {entity_identifier} in domain {domain_identifier}")
    #         return response
    #     except ClientError as e:
    #         error_code = e.response["Error"]["Code"]
    #         error_message = e.response["Error"]["Message"]

    #         if error_code == "AccessDeniedException":
    #             raise Exception(f"Access denied while removing policy grant from entity {entity_identifier} in domain {domain_identifier}: {error_message}")
    #         elif error_code == "ResourceNotFoundException":
    #             raise Exception(f"Resource not found while removing policy grant from entity {entity_identifier} in domain {domain_identifier}: {error_message}")
    #         elif error_code == "ValidationException":
    #             raise Exception(f"Invalid parameters while removing policy grant from entity {entity_identifier} in domain {domain_identifier}: {error_message}")
    #         else:
    #             raise Exception(f"Unexpected error removing policy grant from entity {entity_identifier} in domain {domain_identifier}: {error_message}")

    # @mcp.tool()
    # async def get_iam_portal_login_url(
    #     domain_identifier: str
    # ) -> Any:
    #     """
    #     Retrieves the data portal URL and associated user profile ID for a specified Amazon DataZone domain.

    #     This operation uses a domain identifier to return the login authorization URL for the data portal, along with the user's profile ID. No request body is required.

    #     Args:
    #         domain_identifier (str): The ID of the Amazon DataZone domain whose data portal information is being requested.
    #             Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
    #             Required: Yes

    #     Returns:
    #         dict: A dictionary containing:
    #             - authCodeUrl (str): The URL for the data portal login of the specified domain.
    #             - userProfileId (str): The ID of the user's profile in the domain.
    #     """
    #     try:
    #         response = datazone_client.get_iam_portal_login_url(domainIdentifier = domain_identifier)
    #         return response
    #     except ClientError as e:
    #         raise Exception(f"Error getting IAM portal login URL in domain {domain_identifier}: {e}")

    @mcp.tool()
    async def search(
        domain_identifier: str = Field(..., description="The identifier of the domain"),
        search_scope: str = Field(..., description="The scope of the search"),
        additional_attributes: Optional[List[str]] = Field(None, description="Additional attributes to include in the search"),
        filters: Optional[Dict[str, Any]] = Field(None, description="Filters to apply to the search"),
        max_results: int = Field(50, description="Maximum number of results to return"),
        next_token: Optional[str] = Field(None, description="Token for pagination"),
        owning_project_identifier: Optional[str] = Field(None, description="The identifier of the owning project"),
        search_in: Optional[List[Dict[str, str]]] = Field(None, description="Attributes to search within"),
        search_text: Optional[str] = Field(None, description="Text to search for"),
        sort: Optional[Dict[str, str]] = Field(None, description="Sorting criteria"),
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
                domain_identifier="dzd-1234567890",
                search_scope="ASSET",
                search_text="customer data",
                search_in=[{"attribute": "name"}, {"attribute": "description"}],
                sort={"attribute": "name", "order": "ASCENDING"},
                max_results=25
            )
            ```
        """
        try:
            logger.info(f'Searching {search_scope.lower()} in domain {domain_identifier}')
            # Validate search_scope
            valid_scopes = ['ASSET', 'GLOSSARY', 'GLOSSARY_TERM', 'DATA_PRODUCT']
            if search_scope not in valid_scopes:
                raise ValueError(f'search_scope must be one of {valid_scopes}')

            # Prepare the request parameters
            params = {
                'domainIdentifier': domain_identifier,
                'searchScope': search_scope,
                'maxResults': min(max_results, 50),  # Ensure maxResults is within valid range
            }

            # Add optional parameters if provided
            if additional_attributes:  # pragma: no cover
                params['additionalAttributes'] = additional_attributes
            if filters:  # pragma: no cover
                params['filters'] = filters
            if next_token:  # pragma: no cover
                params['nextToken'] = next_token
            if owning_project_identifier:  # pragma: no cover
                params['owningProjectIdentifier'] = owning_project_identifier
            if search_in:  # pragma: no cover
                params['searchIn'] = search_in
            if search_text:  # pragma: no cover
                params['searchText'] = search_text
            if sort:  # pragma: no cover
                params['sort'] = sort

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
        managed: bool = Field(..., description="Whether to search for managed types"),
        search_scope: str = Field(..., description="The scope of the search"),
        filters: Optional[Dict[str, Any]] = Field(None, description="Filters to apply to the search"),
        max_results: int = Field(50, description="Maximum number of results to return"),
        next_token: Optional[str] = Field(None, description="Token for pagination"),
        search_in: Optional[List[Dict[str, str]]] = Field(None, description="Attributes to search within"),
        search_text: Optional[str] = Field(None, description="Text to search for"),
        sort: Optional[Dict[str, str]] = Field(None, description="Sorting criteria"),
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
            logger.info(f'Searching types {search_scope.lower()} in domain {domain_identifier}')
            # Validate search_scope
            valid_scopes = ['ASSET_TYPE', 'FORM_TYPE', 'LINEAGE_NODE_TYPE']
            if search_scope not in valid_scopes:
                raise ValueError(f'search_scope must be one of {valid_scopes}')

            # Prepare the request parameters
            params = {
                'domainIdentifier': domain_identifier,
                'searchScope': search_scope,
                'maxResults': min(max_results, 50),  # Ensure maxResults is within valid range
                'managed': managed,
            }

            # Add optional parameters if provided
            if filters:  # pragma: no cover
                params['filters'] = filters
            if next_token:  # pragma: no cover
                params['nextToken'] = next_token
            if search_in:  # pragma: no cover
                params['searchIn'] = search_in
            if search_text:  # pragma: no cover
                params['searchText'] = search_text
            if sort:  # pragma: no cover
                params['sort'] = sort

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
        user_type: Optional[str] = Field(None, description="The type of the user")
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
            params = {'domainIdentifier': domain_identifier, 'userIdentifier': user_identifier}

            # Add optional parameters if provided
            if user_type:  # pragma: no cover
                valid_types = ['IAM', 'SSO']
                if user_type not in valid_types:  # pragma: no cover
                    raise ValueError(f'user_type must be one of {valid_types}')
                params['type'] = user_type
            response = datazone_client.get_user_profile(**params)
            return response
        except ClientError as e:  # pragma: no cover
            raise Exception(
                f'Error getting user {user_identifier} profile in domain {domain_identifier}: {e}'
            )

    # @mcp.tool()
    # async def get_group_profile(
    #     domain_identifier: str,
    #     group_identifier: str
    #     ) -> Any:
    #     """
    #     Retrieves metadata for a specific group profile within an Amazon DataZone domain.

    #     This operation identifies a group profile by its domain and group identifier, and returns information such as the group name, ID, and assignment status. No request body is required.

    #     Args:
    #         domain_identifier (str): The identifier of the Amazon DataZone domain containing the group profile.
    #             Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
    #             Required: Yes
    #         group_identifier (str): The identifier of the group profile.
    #             Pattern: (^([0-9a-f]{10}-|)[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}$|[\p{L}\p{M}\p{S}\p{N}\p{P}\t\n\r ]+)
    #             Required: Yes

    #     Returns:
    #         dict: A dictionary containing metadata about the group profile:
    #             - domainId (str): The ID of the domain the group profile belongs to
    #                 Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
    #             - groupName (str): The name of the group (1–1024 characters)
    #                 Pattern: ^[a-zA-Z_0-9+=,.@-]+$
    #             - id (str): The identifier of the group profile
    #                 Pattern: ^([0-9a-f]{10}-|)[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}$
    #             - status (str): The assignment status of the group profile
    #                 Valid values: "ASSIGNED", "NOT_ASSIGNED"

    #     Raises:
    #         HTTPError: If the request is invalid or the server returns an error.
    #     """
    #     try:
    #         params = {
    #             "domainIdentifier": domain_identifier,
    #             "groupIdentifier": group_identifier
    #         }
    #         response = datazone_client.get_group_profile(**params)
    #         return response
    #     except ClientError as e:
    #         raise Exception(f"Error getting group {group_identifier} profile in domain {domain_identifier}: {e}")

    @mcp.tool()
    async def search_user_profiles(
        domain_identifier: str = Field(..., description="The identifier of the domain"),
        user_type: str = Field(..., description="The type of the user"),
        max_results: int = Field(50, description="Maximum number of results to return"),
        next_token: Optional[str] = Field(None, description="Token for pagination"),
        search_text: Optional[str] = Field(None, description="Text to search for"),
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
            logger.info(f'Searching {user_type} user profiles in domain {domain_identifier}')
            # Validate user_type
            valid_types = ['SSO_USER', 'DATAZONE_USER', 'DATAZONE_SSO_USER', 'DATAZONE_IAM_USER']
            if user_type not in valid_types:
                raise ValueError(f'user_type must be one of {valid_types}')

            # Prepare the request parameters
            params = {
                'domainIdentifier': domain_identifier,
                'userType': user_type,
                'maxResults': min(max_results, 50),
            }

            # Add optional parameters if provided
            if search_text:  # pragma: no cover
                params['searchText'] = search_text
            if next_token:  # pragma: no cover
                params['nextToken'] = next_token

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
        max_results: int = Field(50, description="Maximum number of results to return"),
        next_token: Optional[str] = Field(None, description="Token for pagination"),
        search_text: Optional[str] = Field(None, description="Text to search for"),
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
            logger.info(f'Searching {group_type} group profiles in domain {domain_identifier}')
            # Validate user_type
            valid_types = ['SSO_GROUP', 'DATAZONE_SSO_GROUP']
            if group_type not in valid_types:
                raise ValueError(f'group_type must be one of {valid_types}')

            # Prepare the request parameters
            params = {
                'domainIdentifier': domain_identifier,
                'groupType': group_type,
                'maxResults': min(max_results, 50),
            }

            # Add optional parameters if provided
            if search_text:  # pragma: no cover
                params['searchText'] = search_text
            if next_token:  # pragma: no cover
                params['nextToken'] = next_token

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

    # @mcp.tool()
    # async def list_notifications(
    #     domain_identifier: str,
    #     notification_type = str,
    #     after_timestamp: int = None,
    #     before_timestamp: int = None,
    #     max_results: int = 50,
    #     next_token: str = None,
    #     subjects: str = None,
    #     task_status: str = None,
    # ) -> Any:
    #     """
    #     Lists notifications in a specified Amazon DataZone domain.

    #     Args:
    #         domain_identifier (str): The identifier of the Amazon DataZone domain.
    #             Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
    #         type (str): The type of notifications to retrieve.
    #             Valid values: 'TASK', 'EVENT'
    #         after_timestamp (int, optional): Unix timestamp (in milliseconds) representing the start time filter for notifications.
    #         before_timestamp (int, optional): Unix timestamp (in milliseconds) representing the end time filter for notifications.
    #         max_results (int, optional): The maximum number of notifications to return.
    #             Valid range: 1 to 50
    #         next_token (str, optional): A pagination token returned from a previous call.
    #             Used to retrieve the next set of results.
    #         subjects (List[str], optional): List of subjects to filter notifications.
    #         task_status (str, optional): Filter for task status of notifications.
    #             Valid values: 'ACTIVE', 'INACTIVE'

    #     Returns:
    #         Any: The API response containing a list of notifications, including:
    #             - actionLink (str): Optional link to further action.
    #             - creationTimestamp (datetime): Time when the notification was created.
    #             - domainIdentifier (str): ID of the domain the notification belongs to.
    #             - identifier (str): Unique ID of the notification.
    #             - lastUpdatedTimestamp (datetime): Time when the notification was last updated.
    #             - message (str): Message content of the notification.
    #             - metadata (dict): Additional key-value metadata.
    #             - status (str): Status of the notification.
    #             - title (str): Notification title.
    #             - topic (dict): Object describing the topic context, including resource, role, and subject.
    #             - type (str): Notification type ('TASK' or 'EVENT')
    #             - nextToken (str): Pagination token for retrieving additional results.
    #     """
    #     try:
    #         logger.info(f"Listing notifications in domain {domain_identifier}")
    #         if notification_type not in ["TASK", "EVENT"]:
    #             raise ValueError("notification_type must be'TASK' or 'EVENT'")

    #         # Prepare the request parameters
    #         params = {
    #             "domainIdentifier": domain_identifier,
    #             "type": notification_type,
    #             "maxResults": min(50, max_results)
    #         }

    #         # Add optional client token if provided
    #         if next_token:
    #             params["nextToken"] = next_token
    #         if task_status:
    #             if task_status not in ["ACTIVE", "INACTIVE"]:
    #                 raise ValueError("task_status must be'ACTIVE' or 'INACTIVE'")
    #         if after_timestamp:
    #             params["afterTimestamp"] = after_timestamp
    #         if before_timestamp:
    #             params["beforeTimestamp"] = before_timestamp
    #         if subjects:
    #             params["subjects"] = subjects
    #         response = datazone_client.list_notifications(**params)
    #         logger.info(f"Successfully listed notifications in domain {domain_identifier}")
    #         return response
    #     except ClientError as e:
    #         raise Exception(f"Error listing notifications in domain {domain_identifier}: {e}")

    # @mcp.tool()
    # async def list_rules(
    #     domain_identifier: str,
    #     target_identifier: str,
    #     target_type: str = "DOMAIN_UNIT",
    #     action: str = None,
    #     asset_types: List[str] = None,
    #     data_product: str = None,
    #     included_cascaded: bool = True,
    #     max_results: int = 50,
    #     next_token: str = None,
    #     project_ids:List[str] = None,
    #     rule_type: str = "METADATA_FORM_ENFORCEMENT"
    # ) -> Any:
    #     """
    #     Lists rules configured in an Amazon DataZone domain, optionally filtered by project, asset type, target, or action.

    #     Args:
    #         domain_identifier (str): The ID of the domain in which rules are to be listed.
    #         target_identifier (str): The target ID of the rule.
    #         target_type (str): The type of the target. Valid value: "DOMAIN_UNIT".
    #         action (str, optional): The action type of the rule. Valid values:
    #             - "CREATE_LISTING_CHANGE_SET"
    #             - "CREATE_SUBSCRIPTION_REQUEST"
    #         asset_types (List[str], optional): The asset types to filter rules by.
    #             Each type must match the pattern `^(?!\.)[\w\.]*\w$`.
    #         data_product (bool, optional): Whether the rule applies to a data product.
    #         include_cascaded (bool, optional): Whether to include cascaded rules in the result.
    #         max_results (int, optional): Maximum number of rules to return (between 25 and 50).
    #         next_token (str, optional): Pagination token for retrieving the next set of results.
    #         project_ids (List[str], optional): A list of project IDs to filter the rules by.
    #             Each project ID must match the pattern `^[a-zA-Z0-9_-]{1,36}$`.
    #         rule_type (str, optional): The type of rule. Valid value: "METADATA_FORM_ENFORCEMENT".

    #     Returns:
    #         Any: The API response including:
    #             - items (List[RuleSummary]):
    #                 A list of rules matching the provided filters.
    #                 Each rule includes:
    #                     - action (str)
    #                     - identifier (str)
    #                     - name (str)
    #                     - ruleType (str)
    #                     - revision (str)
    #                     - lastUpdatedBy (str)
    #                     - updatedAt (int timestamp)
    #                     - scope (dict): Rule scope including asset types, data product flag, and specific projects
    #                     - target (dict): The rule's target object
    #                     - targetType (str)
    #             - nextToken (str, optional): Token to retrieve the next page of results, if available.
    #     """
    #     try:
    #         logger.info(f"Listing rules in domain {domain_identifier}")
    #         if target_type != "DOMAIN_UNIT":
    #             raise ValueError("target_type must be'DOMAIN_UNIT'")

    #         # Prepare the request parameters
    #         params = {
    #             "domainIdentifier": domain_identifier,
    #             "targetIdentifier": target_identifier,
    #             "target_type": target_type,
    #             "maxResults": max(25, min(50, max_results))
    #         }

    #         # Add optional client token if provided
    #         if next_token:
    #             params["nextToken"] = next_token
    #         if action:
    #             if action not in ["CREATE_LISTING_CHANGE_SET", "CREATE_SUBSCRIPTION_REQUEST"]:
    #                 raise ValueError("action must be'CREATE_LISTING_CHANGE_SET' or 'CREATE_SUBSCRIPTION_REQUEST'")
    #         if asset_types:
    #             params["assetTypes"] = asset_types
    #         if data_product:
    #             params["dataProduct"] = data_product
    #         if included_cascaded:
    #             params["includedCascaded"] = included_cascaded
    #         if project_ids:
    #             params["projectIds"] = project_ids
    #         if rule_type:
    #             if rule_type != "METADATA_FORM_ENFORCEMENT":
    #                 raise ValueError("actrule_typeion must be'METADATA_FORM_ENFORCEMENT'")
    #             params["ruleType"] = rule_type
    #         response = datazone_client.list_rules(**params)
    #         logger.info(f"Successfully listed rules in domain {domain_identifier}")
    #         return response
    #     except ClientError as e:
    #         raise Exception(f"Error listing rules in domain {domain_identifier}: {e}")

    # @mcp.tool()
    # async def list_tags_for_resource(
    #     resource_arn: str
    # ) -> Any:
    #     """
    #     Lists the tags associated with a specific resource in Amazon DataZone.

    #     Args:
    #         resource_arn (str): The Amazon Resource Name (ARN) of the resource whose tags are to be retrieved.

    #     Returns:
    #         Any: The API response containing the tags as key-value pairs:
    #             - tags (dict[str, str]): A dictionary where each key is a tag name and each value is the corresponding tag value.
    #                 - Key constraints:
    #                     - Length: 1–128 characters
    #                     - Pattern: ^[\\w \\.:/=+@-]+$
    #                 - Value constraints:
    #                     - Length: 0–256 characters
    #                     - Pattern: ^[\\w \\.:/=+@-]*$
    #     """
    #     try:
    #         logger.info(f"Listing tags for resource {resource_arn}")
    #         response = datazone_client.list_tags_for_resource(resource_arn)
    #         logger.info(f"Successfully listed tags for resource {resource_arn}")
    #         return response
    #     except ClientError as e:
    #         raise Exception(f"Error listing tags for resource {resource_arn}: {e}")

    # Return the decorated functions for testing purposes
    return {
        'get_domain': get_domain,
        'create_domain': create_domain,
        'list_domain_units': list_domain_units,
        'list_domains': list_domains,
        'create_domain_unit': create_domain_unit,
        'get_domain_unit': get_domain_unit,
        # "list_domain_units_for_parent": list_domain_units_for_parent,
        # "update_domain_unit": update_domain_unit,
        'add_entity_owner': add_entity_owner,
        # "list_entity_owners": list_entity_owners,
        'add_policy_grant': add_policy_grant,
        # "list_policy_grants": list_policy_grants,
        # "remove_policy_grant": remove_policy_grant,
        # "get_iam_portal_login_url": get_iam_portal_login_url,
        'search': search,
        'search_types': search_types,
        'get_user_profile': get_user_profile,
        # "get_group_profile": get_group_profile,
        'search_user_profiles': search_user_profiles,
        'search_group_profiles': search_group_profiles,
        # "list_notifications": list_notifications,
        # "list_rules": list_rules,
        # "list_tags_for_resource": list_tags_for_resource
    }
