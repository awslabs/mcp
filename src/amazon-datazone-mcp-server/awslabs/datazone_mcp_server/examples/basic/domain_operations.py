#!/usr/bin/env python3
"""
Example: Domain Operations.

Description: Demonstrates basic domain operations including getting domain information,
listing available domains, and understanding domain structure.

Prerequisites:
- AWS credentials configured
- DataZone domain access
- DATAZONE_DOMAIN_ID environment variable (optional)

Usage:
    python examples/basic/domain_operations.py
    
    # With custom domain ID
    DATAZONE_DOMAIN_ID=dzd_abc123 python examples/basic/domain_operations.py
"""

import asyncio
import json
import os
from typing import Any, Dict

from mcp import create_client


class DomainOperationsExample:
    """Example class demonstrating domain operations."""

    def __init__(self, domain_id: str = None):
        self.domain_id = domain_id or os.getenv("DATAZONE_DOMAIN_ID")
        self.client = None

    async def setup_client(self):
        """Initialize the MCP client connection."""
        print("Setting up MCP client connection...")
        self.client = await create_client("stdio", ["python", "-m", "datazone_mcp_server.server"])
        print("Client connection established")

    async def get_domain_details(self) -> Dict[str, Any]:
        """
        Retrieve detailed information about a specific domain.

        Returns:
            Dict containing domain details
        """
        print(f"\nGetting details for domain: {self.domain_id}")

        try:
            result = await self.client.call_tool("get_domain", {"identifier": self.domain_id})

            domain_data = json.loads(result.content[0].text)

            print("Domain Details:")
            print(f"   Name: {domain_data.get('name', 'N/A')}")
            print(f"   ID: {domain_data.get('id', 'N/A')}")
            print(f"   ARN: {domain_data.get('arn', 'N/A')}")
            print(f"   Status: {domain_data.get('status', 'N/A')}")
            print(f"   Description: {domain_data.get('description', 'No description')}")
            print(f"   Created: {domain_data.get('createdAt', 'N/A')}")
            print(f"   Portal URL: {domain_data.get('portalUrl', 'N/A')}")

            if domain_data.get("singleSignOn"):
                sso = domain_data["singleSignOn"]
                print(f"   SSO Type: {sso.get('type', 'N/A')}")
                print(f"   SSO User Assignment: {sso.get('userAssignment', 'N/A')}")

            return domain_data

        except Exception as e:
            print(f"Error getting domain details: {e}")
            return {}

    async def list_all_domains(self) -> list:
        """
        List all available domains in the AWS account.

        Returns:
            List of domain information
        """
        print("\nListing all available domains...")

        try:
            result = await self.client.call_tool("list_domains", {})
            domains_data = json.loads(result.content[0].text)

            domains = domains_data.get("items", [])
            print(f"Found {len(domains)} domains:")

            for i, domain in enumerate(domains, 1):
                print(f"\n   {i}. {domain.get('name', 'Unnamed')}")
                print(f"      ID: {domain.get('id', 'N/A')}")
                print(f"      Status: {domain.get('status', 'N/A')}")
                print(f"      Created: {domain.get('createdAt', 'N/A')}")
                if domain.get("description"):
                    print(f"      Description: {domain['description']}")

            return domains

        except Exception as e:
            print(f"Error listing domains: {e}")
            return []

    async def check_domain_access(self) -> bool:
        """
        Check if we have access to the specified domain.

        Returns:
            True if domain is accessible, False otherwise
        """
        print(f"\nChecking access to domain: {self.domain_id}")

        try:
            # Try to get domain details
            result = await self.client.call_tool("get_domain", {"identifier": self.domain_id})

            domain_data = json.loads(result.content[0].text)
            print(f"Access confirmed - Domain '{domain_data.get('name')}' is accessible")
            return True

        except Exception as e:
            print(f"Access denied or domain not found: {e}")
            print("Tips:")
            print("   - Verify your DATAZONE_DOMAIN_ID is correct")
            print("   - Check your AWS credentials and permissions")
            print("   - Ensure the domain exists in your AWS region")
            return False

    async def get_domain_units(self) -> list:
        """
        List organizational units within the domain.

        Returns:
            List of domain units
        """
        print(f"\nGetting organizational units for domain: {self.domain_id}")

        try:
            result = await self.client.call_tool(
                "list_domain_units", {"domain_identifier": self.domain_id}
            )

            units_data = json.loads(result.content[0].text)
            units = units_data.get("items", [])

            print(f"Found {len(units)} organizational units:")

            for i, unit in enumerate(units, 1):
                print(f"\n   {i}. {unit.get('name', 'Unnamed')}")
                print(f"      ID: {unit.get('id', 'N/A')}")
                print(f"      Created: {unit.get('createdAt', 'N/A')}")
                if unit.get("description"):
                    print(f"      Description: {unit['description']}")

            return units

        except Exception as e:
            print(f"Error getting domain units: {e}")
            return []

    async def cleanup(self):
        """Clean up resources."""
        if self.client:
            print("\n🧹 Cleaning up...")
            # The client will be cleaned up automatically
            print("Cleanup complete")


async def main():
    """
    Main function demonstrating domain operations.
    """
    print("AWS DataZone Domain Operations Example")
    print("=" * 50)

    # Configuration
    domain_id = os.getenv("DATAZONE_DOMAIN_ID")

    if not domain_id:
        print("No DATAZONE_DOMAIN_ID found in environment variables")
        print("Set it with: export DATAZONE_DOMAIN_ID=dzd_your_domain_id")
        print("Proceeding with domain listing only...")

    # Initialize example
    example = DomainOperationsExample(domain_id)

    try:
        # Step 1: Setup client
        await example.setup_client()

        # Step 2: List all domains (works without specific domain ID)
        all_domains = await example.list_all_domains()

        # If no specific domain ID, use the first available domain
        if not domain_id and all_domains:
            domain_id = all_domains[0].get("id")
            print(f"\nUsing first available domain: {domain_id}")
            example.domain_id = domain_id

        if domain_id:
            # Step 3: Check domain access
            has_access = await example.check_domain_access()

            if has_access:
                # Step 4: Get detailed domain information
                domain_details = await example.get_domain_details()

                # Step 5: Get domain organizational units
                domain_units = await example.get_domain_units()

                # Summary
                print("\n" + "=" * 50)
                print("SUMMARY")
                print("=" * 50)
                print(f"Domain Name: {domain_details.get('name', 'N/A')}")
                print(f"Domain ID: {domain_details.get('id', 'N/A')}")
                print(f"Status: {domain_details.get('status', 'N/A')}")
                print(f"Total Domains Available: {len(all_domains)}")
                print(f"Organizational Units: {len(domain_units)}")

        else:
            print("\nNo domains available or accessible")
            print("Ensure you have DataZone domains set up in your AWS account")

    except Exception as e:
        print(f"\nUnexpected error: {e}")
        print("Check your AWS credentials and DataZone access")

    finally:
        # Step 6: Cleanup
        await example.cleanup()
        print("\nExample completed successfully!")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
