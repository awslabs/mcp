from dataclasses import dataclass
from typing import List

from botocore.exceptions import ClientError

from ..aws.client_manager import AWSClientManager


@dataclass
class CrossAccountTGWConnection:
    source_account: str
    target_account: str
    transit_gateway_arn: str
    shared_with: List[str]


class CrossAccountTransitGatewayAnalyzer:
    """Analyzes TGWs shared across AWS accounts."""

    def __init__(self, aws_manager: AWSClientManager):
        self.aws_manager = aws_manager

    async def discover_shared_tgws(self) -> List[CrossAccountTGWConnection]:
        """Discover all TGWs shared via AWS RAM."""
        try:
            ram_client = await self.aws_manager.get_client("ram", "us-east-1")
            resources = await ram_client.list_resources(
                resourceType="networkmanager:transit-gateway"
            )
            return [
                CrossAccountTGWConnection(
                    source_account=res["arn"].split(":")[4],
                    target_account=share["principal"],
                    transit_gateway_arn=res["arn"],
                    shared_with=[share["principal"] for share in res["resourceShares"]],
                )
                for res in resources["resources"]
            ]
        except ClientError:
            return []
