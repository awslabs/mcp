"""
Transit Gateway Routes MCP Tool.

This tool provides comprehensive capabilities to manage routes in Transit Gateway route tables,
including listing, creating, deleting, and blackholing routes across AWS regions.

Features:
- List all routes in a specified Transit Gateway route table
- Create static routes pointing to Transit Gateway attachments
- Delete routes from Transit Gateway route tables
- Create blackhole routes for traffic filtering

Each operation returns a structured response with detailed information about the
route operation and its success status.
"""

import logging
from typing import Any, Dict

from botocore.exceptions import ClientError

from ...aws.client_manager import AWSClientManager
from ...config import CloudWANConfig
from ...models.network import (
    TGWRouteOperationResponse,
    RouteInfo,
)
from ..base import (
    BaseMCPTool,
    handle_errors,
    validate_cidr_block,
    ValidationError,
    AWSOperationError,
)


class TransitGatewayRoutesTool(BaseMCPTool):
    """
    Transit Gateway Routes MCP Tool.

    Provides capabilities to list, create, modify, and delete routes in
    Transit Gateway route tables across AWS regions.

    This tool enables direct control over Transit Gateway routing, allowing
    for comprehensive management of network traffic flows between VPCs,
    on-premises networks, and other AWS services connected via Transit Gateway.

    All operations perform validation checks and handle AWS errors gracefully,
    returning detailed status information for each operation.
    """

    @property
    def tool_name(self) -> str:
        return "manage_tgw_routes"

    @property
    def description(self) -> str:
        return """
        Manage routes in Transit Gateway route tables across AWS regions.
        
        Features:
        - List routes in a specified route table
        - Create static routes to Transit Gateway attachments
        - Delete routes from route tables
        - Create blackhole routes for traffic filtering
        
        This tool provides direct control over Transit Gateway route tables,
        allowing for fine-grained management of traffic flows between VPCs,
        on-premises networks, and other AWS services attached to your Transit Gateways.
        """

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "create", "delete", "blackhole"],
                    "description": "Action to perform",
                },
                "region": {
                    "type": "string",
                    "description": "AWS region containing the Transit Gateway",
                },
                "route_table_id": {
                    "type": "string",
                    "description": "Transit Gateway Route Table ID",
                },
                "cidr_block": {
                    "type": "string",
                    "description": "CIDR block for the route (required for create/delete/blackhole actions)",
                },
                "attachment_id": {
                    "type": "string",
                    "description": "Transit Gateway Attachment ID (required for create action)",
                },
                "blackhole": {
                    "type": "boolean",
                    "description": "Whether to create a blackhole route (default: false)",
                    "default": False,
                },
            },
            "required": ["action", "region", "route_table_id"],
        }

    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig):
        super().__init__(aws_manager, config)
        self.logger = logging.getLogger(__name__)

    @handle_errors
    async def execute(self, **kwargs) -> TGWRouteOperationResponse:
        """
        Execute Transit Gateway route operations.

        The following operations are supported:
        - "list": List all routes in a Transit Gateway route table
        - "create": Create a static route pointing to a Transit Gateway attachment
        - "delete": Delete a route from a Transit Gateway route table
        - "blackhole": Create a blackhole route in a Transit Gateway route table

        Args:
            **kwargs: Tool parameters from input schema
                action (str): Operation to perform (list, create, delete, blackhole)
                region (str): AWS region containing the Transit Gateway
                route_table_id (str): Transit Gateway Route Table ID
                cidr_block (str, optional): CIDR block for the route operation
                attachment_id (str, optional): Transit Gateway Attachment ID for create operation
                blackhole (bool, optional): Whether to create a blackhole route

        Returns:
            TGWRouteOperationResponse: Detailed response with operation results
                                      and route information

        Raises:
            ValidationError: If required parameters are missing or invalid
            AWSOperationError: If AWS API operations fail
        """
        # Validate and extract parameters
        action = kwargs.get("action")
        if not action:
            raise ValidationError("Action is required")

        region = kwargs.get("region")
        if not region:
            raise ValidationError("Region is required")

        route_table_id = kwargs.get("route_table_id")
        if not route_table_id:
            raise ValidationError("Transit Gateway Route Table ID is required")

        # Get EC2 client for region
        ec2_client = await self.aws_manager.get_client("ec2", region)

        # Dispatch to appropriate action method
        if action == "list":
            return await self._list_routes(ec2_client, route_table_id, region)
        elif action == "create":
            # Validate parameters for route creation
            cidr_block = kwargs.get("cidr_block")
            attachment_id = kwargs.get("attachment_id")
            blackhole = kwargs.get("blackhole", False)

            # For create action with blackhole=True, we'll redirect to blackhole action
            if blackhole:
                if not cidr_block:
                    raise ValidationError("CIDR block is required for blackhole route creation")
                return await self._blackhole_route(ec2_client, route_table_id, cidr_block, region)
            else:
                # Regular route creation
                if not cidr_block:
                    raise ValidationError("CIDR block is required for route creation")
                if not attachment_id:
                    raise ValidationError(
                        "Transit Gateway Attachment ID is required for route creation"
                    )
                return await self._create_route(
                    ec2_client, route_table_id, cidr_block, attachment_id, region
                )
        elif action == "delete":
            # Validate parameters for route deletion
            cidr_block = kwargs.get("cidr_block")
            if not cidr_block:
                raise ValidationError("CIDR block is required for route deletion")
            return await self._delete_route(ec2_client, route_table_id, cidr_block, region)
        elif action == "blackhole":
            # Validate parameters for blackhole route
            cidr_block = kwargs.get("cidr_block")
            if not cidr_block:
                raise ValidationError("CIDR block is required for blackhole route creation")
            return await self._blackhole_route(ec2_client, route_table_id, cidr_block, region)
        else:
            raise ValidationError(f"Invalid action: {action}")

    async def _list_routes(
        self, ec2_client: Any, route_table_id: str, region: str
    ) -> TGWRouteOperationResponse:
        """
        List routes in a Transit Gateway route table.

        This method retrieves all routes from the specified Transit Gateway route table
        and formats them into the response model. It validates that the route table exists
        before attempting to list routes.

        Args:
            ec2_client: Boto3 EC2 client for the specified region
            route_table_id: Transit Gateway Route Table ID (e.g., "tgw-rtb-12345")
            region: AWS region (e.g., "us-east-1")

        Returns:
            TGWRouteOperationResponse: Response containing the list of routes
                                      with their details

        Raises:
            ValidationError: If the specified route table doesn't exist
            AWSOperationError: If AWS API operations fail
        """
        try:
            # Validate that the route table exists
            try:
                await ec2_client.describe_transit_gateway_route_tables(
                    TransitGatewayRouteTableIds=[route_table_id]
                )
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                if error_code == "InvalidTransitGatewayRouteTableId.NotFound":
                    raise ValidationError(f"Transit Gateway Route Table {route_table_id} not found")
                raise e

            # Get routes from the route table
            # We'll use search_transit_gateway_routes to get all routes
            response = await ec2_client.search_transit_gateway_routes(
                TransitGatewayRouteTableId=route_table_id,
                Filters=[{"Name": "state", "Values": ["active", "blackhole"]}],
            )

            routes = response.get("Routes", [])

            # Process routes to format them according to our model
            processed_routes = []
            for route in routes:
                route_info = {
                    "destination_cidr": route.get("DestinationCidrBlock", ""),
                    "state": route.get("State", ""),
                    "route_type": route.get("Type", ""),
                    "prefix_length": self._get_prefix_length(route.get("DestinationCidrBlock", "")),
                    "target_type": None,
                    "target_id": None,
                    "origin": None,
                }

                # Extract target information
                attachments = route.get("TransitGatewayAttachments", [])
                if attachments:
                    attachment = attachments[0]  # Use first attachment
                    route_info["target_type"] = attachment.get("ResourceType")
                    route_info["target_id"] = attachment.get("ResourceId")
                    route_info["origin"] = attachment.get("TransitGatewayAttachmentId")

                processed_routes.append(RouteInfo(**route_info))

            return TGWRouteOperationResponse(
                operation="list",
                route_table_id=route_table_id,
                region=region,
                success=True,
                routes=processed_routes,
                regions_analyzed=[region],
                status="success",
            )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            self.logger.error(
                f"Failed to list routes for {route_table_id}: {error_code} - {error_message}"
            )
            raise AWSOperationError(f"Failed to list routes: {error_message}", error_code)

    async def _create_route(
        self,
        ec2_client: Any,
        route_table_id: str,
        cidr_block: str,
        attachment_id: str,
        region: str,
    ) -> TGWRouteOperationResponse:
        """
        Create a static route in a Transit Gateway route table.

        This method creates a static route in the specified Transit Gateway route table
        pointing to the specified Transit Gateway attachment. It performs validation
        on the CIDR block format and checks that both the route table and attachment exist.

        Args:
            ec2_client: Boto3 EC2 client for the specified region
            route_table_id: Transit Gateway Route Table ID (e.g., "tgw-rtb-12345")
            cidr_block: CIDR block for the route (e.g., "10.0.0.0/16")
            attachment_id: Transit Gateway Attachment ID (e.g., "tgw-attach-12345")
            region: AWS region (e.g., "us-east-1")

        Returns:
            TGWRouteOperationResponse: Response containing the result of the route
                                      creation operation

        Raises:
            ValidationError: If parameters are invalid or resources don't exist
            AWSOperationError: If AWS API operations fail
        """
        try:
            # Validate CIDR block
            try:
                validate_cidr_block(cidr_block)
            except ValidationError as e:
                raise ValidationError(f"Invalid CIDR block: {str(e)}")

            # Check if the route table exists
            try:
                await ec2_client.describe_transit_gateway_route_tables(
                    TransitGatewayRouteTableIds=[route_table_id]
                )
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                if error_code == "InvalidTransitGatewayRouteTableId.NotFound":
                    raise ValidationError(f"Transit Gateway Route Table {route_table_id} not found")
                raise e

            # Check if the attachment exists
            try:
                await ec2_client.describe_transit_gateway_attachments(
                    TransitGatewayAttachmentIds=[attachment_id]
                )
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                if error_code == "InvalidTransitGatewayAttachmentId.NotFound":
                    raise ValidationError(f"Transit Gateway Attachment {attachment_id} not found")
                raise e

            # Create the route
            response = await ec2_client.create_transit_gateway_route(
                DestinationCidrBlock=cidr_block,
                TransitGatewayRouteTableId=route_table_id,
                TransitGatewayAttachmentId=attachment_id,
            )

            # Check if the route was created successfully
            route = response.get("Route", {})
            state = route.get("State", "")

            return TGWRouteOperationResponse(
                operation="create",
                route_table_id=route_table_id,
                region=region,
                cidr_block=cidr_block,
                attachment_id=attachment_id,
                success=state == "active" or state == "blackhole",
                error_message=(
                    None
                    if state == "active" or state == "blackhole"
                    else f"Route created but in state: {state}"
                ),
                regions_analyzed=[region],
                status=("success" if state == "active" or state == "blackhole" else "partial"),
            )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            self.logger.error(
                f"Failed to create route in {route_table_id}: {error_code} - {error_message}"
            )
            raise AWSOperationError(f"Failed to create route: {error_message}", error_code)

    async def _delete_route(
        self, ec2_client: Any, route_table_id: str, cidr_block: str, region: str
    ) -> TGWRouteOperationResponse:
        """
        Delete a route from a Transit Gateway route table.

        This method deletes a route with the specified CIDR block from the Transit
        Gateway route table. It validates the CIDR block format and checks that the
        route table exists. If the route doesn't exist, it returns a response with
        success=False rather than raising an exception.

        Args:
            ec2_client: Boto3 EC2 client for the specified region
            route_table_id: Transit Gateway Route Table ID (e.g., "tgw-rtb-12345")
            cidr_block: CIDR block for the route to delete (e.g., "10.0.0.0/16")
            region: AWS region (e.g., "us-east-1")

        Returns:
            TGWRouteOperationResponse: Response containing the result of the route
                                      deletion operation

        Raises:
            ValidationError: If parameters are invalid or the route table doesn't exist
            AWSOperationError: If AWS API operations fail (except route not found)
        """
        try:
            # Validate CIDR block
            try:
                validate_cidr_block(cidr_block)
            except ValidationError as e:
                raise ValidationError(f"Invalid CIDR block: {str(e)}")

            # Check if the route table exists
            try:
                await ec2_client.describe_transit_gateway_route_tables(
                    TransitGatewayRouteTableIds=[route_table_id]
                )
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                if error_code == "InvalidTransitGatewayRouteTableId.NotFound":
                    raise ValidationError(f"Transit Gateway Route Table {route_table_id} not found")
                raise e

            # Delete the route
            response = await ec2_client.delete_transit_gateway_route(
                DestinationCidrBlock=cidr_block,
                TransitGatewayRouteTableId=route_table_id,
            )

            # Check if the route was deleted successfully
            return TGWRouteOperationResponse(
                operation="delete",
                route_table_id=route_table_id,
                region=region,
                cidr_block=cidr_block,
                success=True,
                regions_analyzed=[region],
                status="success",
            )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            # Handle case where route doesn't exist
            if error_code == "InvalidRoute.NotFound":
                return TGWRouteOperationResponse(
                    operation="delete",
                    route_table_id=route_table_id,
                    region=region,
                    cidr_block=cidr_block,
                    success=False,
                    error_message=f"Route with CIDR {cidr_block} not found",
                    regions_analyzed=[region],
                    status="error",
                )

            self.logger.error(
                f"Failed to delete route in {route_table_id}: {error_code} - {error_message}"
            )
            raise AWSOperationError(f"Failed to delete route: {error_message}", error_code)

    async def _blackhole_route(
        self, ec2_client: Any, route_table_id: str, cidr_block: str, region: str
    ) -> TGWRouteOperationResponse:
        """
        Create a blackhole route in a Transit Gateway route table.

        This method creates a blackhole route in the specified Transit Gateway route table.
        Blackhole routes explicitly drop traffic to the specified CIDR block. The method
        validates the CIDR block format and checks that the route table exists.

        Args:
            ec2_client: Boto3 EC2 client for the specified region
            route_table_id: Transit Gateway Route Table ID (e.g., "tgw-rtb-12345")
            cidr_block: CIDR block for the blackhole route (e.g., "192.168.0.0/16")
            region: AWS region (e.g., "us-east-1")

        Returns:
            TGWRouteOperationResponse: Response containing the result of the blackhole
                                      route creation operation

        Raises:
            ValidationError: If parameters are invalid or the route table doesn't exist
            AWSOperationError: If AWS API operations fail
        """
        try:
            # Validate CIDR block
            try:
                validate_cidr_block(cidr_block)
            except ValidationError as e:
                raise ValidationError(f"Invalid CIDR block: {str(e)}")

            # Check if the route table exists
            try:
                await ec2_client.describe_transit_gateway_route_tables(
                    TransitGatewayRouteTableIds=[route_table_id]
                )
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                if error_code == "InvalidTransitGatewayRouteTableId.NotFound":
                    raise ValidationError(f"Transit Gateway Route Table {route_table_id} not found")
                raise e

            # Create the blackhole route
            response = await ec2_client.create_transit_gateway_route(
                DestinationCidrBlock=cidr_block,
                TransitGatewayRouteTableId=route_table_id,
                Blackhole=True,
            )

            # Check if the route was created successfully
            route = response.get("Route", {})
            state = route.get("State", "")

            return TGWRouteOperationResponse(
                operation="blackhole",
                route_table_id=route_table_id,
                region=region,
                cidr_block=cidr_block,
                blackhole=True,
                success=state == "blackhole",
                error_message=(
                    None if state == "blackhole" else f"Route created but in state: {state}"
                ),
                regions_analyzed=[region],
                status="success" if state == "blackhole" else "partial",
            )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            self.logger.error(
                f"Failed to create blackhole route in {route_table_id}: {error_code} - {error_message}"
            )
            raise AWSOperationError(
                f"Failed to create blackhole route: {error_message}", error_code
            )

    def _get_prefix_length(self, cidr: str) -> int:
        """
        Extract prefix length from CIDR block.

        Args:
            cidr: CIDR block string (e.g., "10.0.0.0/16")

        Returns:
            int: Prefix length as integer (e.g., 16), or 32 if not specified
        """
        try:
            return int(cidr.split("/")[1]) if "/" in cidr else 32
        except (ValueError, IndexError):
            return 32
