import json
from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError

from awslabs.cloudwan_mcp_server.server import analyze_network_function_group


class TestNetworkFunctionAnalysis:
    @pytest.mark.asyncio
    async def test_analyze_nfg_success(self) -> None:
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_client:
            mock_client.return_value.describe_network_manager_groups.return_value = {
                "NetworkManagerGroups": [{"GroupId": "nfg-123"}]
            }
            result = await analyze_network_function_group("nfg-123")
            response = json.loads(result)
            assert response["success"] is True
            assert "analysis" in response

    @pytest.mark.asyncio
    async def test_analyze_nfg_not_found(self) -> None:
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_client:
            mock_client.return_value.describe_network_manager_groups.side_effect = ClientError(
                error_response={"Error": {"Code": "NotFoundException"}}, operation_name="DescribeNetworkManagerGroups"
            )
            result = await analyze_network_function_group("missing-nfg")
            response = json.loads(result)
            assert response["success"] is False
            assert response["error_code"] == "NotFoundException"
