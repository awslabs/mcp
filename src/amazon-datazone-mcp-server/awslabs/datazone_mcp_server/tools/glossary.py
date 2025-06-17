# Copyright 2024 AWS DataZone MCP Server Contributors
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
"""Glossary management tools for Amazon DataZone."""

from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from .common import ClientError, datazone_client, logger


def register_tools(mcp: FastMCP):
    """Register glossary tools with the MCP server."""

    @mcp.tool()
    async def create_glossary(
        domain_identifier: str,
        name: str,
        owning_project_identifier: str,
        description: Optional[str] = None,
        status: str = "ENABLED",
        client_token: Optional[str] = None,
    ) -> Any:
        """
        Creates a new business glossary in Amazon DataZone.

        Args:
            domain_identifier (str): The ID of the domain where the glossary will be created
            name (str): The name of the glossary (1-256 characters)
            owning_project_identifier (str): The ID of the project that will own the glossary
            description (str, optional): The description of the glossary (0-4096 characters)
            status (str, optional): The status of the glossary (ENABLED or DISABLED, default: ENABLED)
            client_token (str, optional): A unique token to ensure idempotency (1-128 characters)

        Returns:
            Any: The API response containing the created glossary details

        Example:
            ```python
            response = await create_glossary(
                domain_identifier="dzd_123456789",
                name="Sales Glossary",
                owning_project_identifier="prj_987654321",
                description="Glossary for sales-related terms",
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
                "owningProjectIdentifier": owning_project_identifier,
                "status": status,
            }

            # Add optional parameters if provided
            if description:
                params["description"] = description
            if client_token:
                params["clientToken"] = client_token

            response = datazone_client.create_glossary(domainIdentifier=domain_identifier, **params)
            return response
        except ClientError as e:
            raise Exception(f"Error creating glossary in domain {domain_identifier}: {e}")

    @mcp.tool()
    async def create_glossary_term(
        domain_identifier: str,
        glossary_identifier: str,
        name: str,
        short_description: Optional[str] = None,
        long_description: Optional[str] = None,
        status: str = "ENABLED",
        term_relations: Optional[Dict[str, List[str]]] = None,
        client_token: Optional[str] = None,
    ) -> Any:
        r"""
        Creates a new business glossary term in Amazon DataZone.

        Args:
            domain_identifier (str): The ID of the domain where the glossary term will be created
                Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
            glossary_identifier (str): The ID of the glossary where the term will be created
                Pattern: ^[a-zA-Z0-9_-]{1,36}$
            name (str): The name of the glossary term (1-256 characters)
            short_description (str, optional): A short description of the term (0-1024 characters)
            long_description (str, optional): A detailed description of the term (0-4096 characters)
            status (str, optional): The status of the term (ENABLED or DISABLED, default: ENABLED)
            term_relations (Dict[str, List[str]], optional): The term relations
                Example: {
                    "classifies": ["term-id-1", "term-id-2"],
                    "isA": ["term-id-3"]
                }
            client_token (str, optional): A unique token to ensure idempotency (1-128 characters)
                Pattern: ^[\x21-\x7E]+$

        Returns:
            Any: The API response containing the created glossary term details

        Example:
            ```python
            response = await create_glossary_term(
                domain_identifier="dzd_123456789",
                glossary_identifier="gloss_987654321",
                name="Customer",
                short_description="A person or organization that purchases goods or services",
                long_description="In business, a customer is an individual or organization that purchases goods or services from a company. Customers are vital to the success of any business as they provide revenue and feedback.",
                status="ENABLED",
                term_relations={
                    "classifies": ["term_123", "term_456"],
                    "isA": ["term_789"]
                }
            )
            ```
        """
        try:
            # Validate status
            if status not in ["ENABLED", "DISABLED"]:
                raise ValueError("status must be either 'ENABLED' or 'DISABLED'")

            # Prepare the request parameters
            params: Dict[str, Any] = {
                "glossaryIdentifier": glossary_identifier,
                "name": name,
                "status": status,
            }

            # Add optional parameters if provided
            if short_description:
                params["shortDescription"] = short_description
            if long_description:
                params["longDescription"] = long_description
            if term_relations:
                params["termRelations"] = term_relations
            if client_token:
                params["clientToken"] = client_token

            response = datazone_client.create_glossary_term(
                domainIdentifier=domain_identifier, **params
            )
            return response
        except ClientError as e:
            raise Exception(f"Error creating glossary term in domain {domain_identifier}: {e}")

    @mcp.tool()
    async def get_glossary(domain_identifier: str, identifier: str) -> Any:
        """
        Retrieves detailed information about a specific business glossary in Amazon DataZone.

        Args:
            domain_identifier (str): The ID of the domain where the glossary exists
                Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
            identifier (str): The ID of the glossary to retrieve
                Pattern: ^[a-zA-Z0-9_-]{1,36}$

        Returns:
            Any: The API response containing glossary details including:
                - createdAt (number): Timestamp of when the glossary was created
                - createdBy (str): The user who created the glossary
                - description (str): The description of the glossary (0-4096 characters)
                - domainId (str): The ID of the domain
                - id (str): The ID of the glossary
                - name (str): The name of the glossary (1-256 characters)
                - owningProjectId (str): The ID of the project that owns the glossary
                - status (str): The status of the glossary (DISABLED or ENABLED)
                - updatedAt (number): Timestamp of when the glossary was updated
                - updatedBy (str): The user who updated the glossary

        Example:
            ```python
            response = await get_glossary(
                domain_identifier="dzd_123456789",
                identifier="gloss_987654321"
            )
            ```
        """
        try:
            response = datazone_client.get_glossary(
                domainIdentifier=domain_identifier, identifier=identifier
            )
            return response
        except ClientError as e:
            raise Exception(
                f"Error getting glossary {identifier} in domain {domain_identifier}: {e}"
            )

    @mcp.tool()
    async def get_glossary_term(domain_identifier: str, identifier: str) -> Any:
        """
        Retrieves detailed information about a specific business glossary term in Amazon DataZone.

        Args:
            domain_identifier (str): The ID of the domain where the glossary term exists
                Pattern: ^dzd[-_][a-zA-Z0-9_-]{1,36}$
            identifier (str): The ID of the glossary term to retrieve
                Pattern: ^[a-zA-Z0-9_-]{1,36}$

        Returns:
            Any: The API response containing glossary term details including:
                - createdAt (number): Timestamp of when the term was created
                - createdBy (str): The user who created the term
                - domainId (str): The ID of the domain
                - glossaryId (str): The ID of the glossary containing the term
                - id (str): The ID of the glossary term
                - longDescription (str): The long description of the term (0-4096 characters)
                - name (str): The name of the term (1-256 characters)
                - shortDescription (str): The short description of the term (0-1024 characters)
                - status (str): The status of the term (ENABLED or DISABLED)
                - termRelations (dict): The relations of the term
                    Example: {
                        "classifies": ["term-id-1", "term-id-2"],
                        "isA": ["term-id-3"]
                    }
                - updatedAt (number): Timestamp of when the term was updated
                - updatedBy (str): The user who updated the term

        Example:
            ```python
            response = await get_glossary_term(
                domain_identifier="dzd_123456789",
                identifier="term_987654321"
            )
            ```
        """
        try:
            response = datazone_client.get_glossary_term(
                domainIdentifier=domain_identifier, identifier=identifier
            )
            return response
        except ClientError as e:
            raise Exception(
                f"Error getting glossary term {identifier} in domain {domain_identifier}: {e}"
            )

    # Return the decorated functions for testing purposes
    return {
        "create_glossary": create_glossary,
        "create_glossary_term": create_glossary_term,
        "get_glossary": get_glossary,
        "get_glossary_term": get_glossary_term,
    }
