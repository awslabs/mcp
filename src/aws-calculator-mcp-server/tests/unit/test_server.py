"""Tests for MCP server tool functions.

Verifies the tool entry points (create_estimate, update_estimate, list_service_fields)
with mocked calculator automation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from awslabs.aws_calculator_mcp_server.server import (
    _get_calculator,
    _save_result_json,
    list_service_fields,
)


class TestGetCalculator:
    """Tests for _get_calculator singleton."""

    def test_creates_calculator_instance(self):
        """Should create AWSCalculatorAutomation when called first time."""
        import awslabs.aws_calculator_mcp_server.server as server_module
        server_module._calculator = None  # Reset singleton

        with patch(
            "awslabs.aws_calculator_mcp_server.server.AWSCalculatorAutomation"
        ) as MockCalc:
            MockCalc.return_value = MagicMock()
            result = _get_calculator()
            MockCalc.assert_called_once_with(headless=True)
            assert result is MockCalc.return_value

        server_module._calculator = None  # Clean up

    def test_returns_existing_calculator(self):
        """Should return existing calculator on second call."""
        import awslabs.aws_calculator_mcp_server.server as server_module
        mock_calc = MagicMock()
        server_module._calculator = mock_calc

        result = _get_calculator()
        assert result is mock_calc

        server_module._calculator = None  # Clean up


class TestSaveResultJson:
    """Tests for _save_result_json helper."""

    def test_saves_json_with_timestamp(self, tmp_path):
        """Should save result dict as JSON with generated_at timestamp."""
        import json
        output_file = str(tmp_path / "result.json")
        result = {"estimate_url": "https://example.com", "monthly_cost": "$10.00 USD/month"}

        _save_result_json(result, output_file)

        with open(output_file) as f:
            data = json.load(f)

        assert "generated_at" in data
        assert data["estimate_url"] == "https://example.com"
        assert data["monthly_cost"] == "$10.00 USD/month"


class TestListServiceFields:
    """Tests for list_service_fields tool."""

    @pytest.mark.asyncio
    async def test_returns_all_services_when_no_filter(self):
        """Should return all services' descriptions when no service_name given."""
        mock_ctx = MagicMock()
        result = await list_service_fields(mock_ctx, service_name="")

        # Should be a dict with service names as keys
        assert isinstance(result, dict)
        assert "Amazon EC2" in result
        assert "AWS Lambda" in result

    @pytest.mark.asyncio
    async def test_returns_specific_service(self):
        """Should return details for a matching service."""
        mock_ctx = MagicMock()
        result = await list_service_fields(mock_ctx, service_name="Amazon EC2")

        assert "Amazon EC2" in result
        assert "fields" in result["Amazon EC2"]

    @pytest.mark.asyncio
    async def test_returns_error_for_unknown_service(self):
        """Should return error when no service matches."""
        mock_ctx = MagicMock()
        result = await list_service_fields(mock_ctx, service_name="NonexistentService12345")

        assert "error" in result
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_case_insensitive_search(self):
        """Should match service names case-insensitively."""
        mock_ctx = MagicMock()
        result = await list_service_fields(mock_ctx, service_name="amazon ec2")

        assert "Amazon EC2" in result


class TestCreateEstimateTool:
    """Tests for create_estimate MCP tool."""

    @pytest.mark.asyncio
    async def test_create_estimate_success(self):
        """Should call calculator.create_estimate and return result."""
        from awslabs.aws_calculator_mcp_server.server import create_estimate
        import awslabs.aws_calculator_mcp_server.server as server_module

        mock_calc = MagicMock()
        mock_calc.create_estimate = AsyncMock(
            return_value={
                "estimate_url": "https://calculator.aws/#/estimate?id=test",
                "monthly_cost": "$100.00 USD/month",
                "services": [],
            }
        )
        mock_calc.close = AsyncMock()
        server_module._calculator = mock_calc

        mock_ctx = MagicMock()
        mock_ctx.info = AsyncMock()

        services = [{"service_name": "Amazon EC2", "config": {"Number of instances": "1"}}]
        result = await create_estimate(mock_ctx, services=services)

        assert result["estimate_url"] == "https://calculator.aws/#/estimate?id=test"
        mock_calc.close.assert_called_once()

        server_module._calculator = None

    @pytest.mark.asyncio
    async def test_create_estimate_handles_exception(self):
        """Should return error dict when exception occurs."""
        from awslabs.aws_calculator_mcp_server.server import create_estimate
        import awslabs.aws_calculator_mcp_server.server as server_module

        mock_calc = MagicMock()
        mock_calc.create_estimate = AsyncMock(side_effect=Exception("Browser crashed"))
        mock_calc.close = AsyncMock()
        server_module._calculator = mock_calc

        mock_ctx = MagicMock()
        mock_ctx.info = AsyncMock()

        result = await create_estimate(mock_ctx, services=[])

        assert "error" in result
        assert "Browser crashed" in result["error"]
        mock_calc.close.assert_called_once()

        server_module._calculator = None

    @pytest.mark.asyncio
    async def test_create_estimate_saves_output(self, tmp_path):
        """Should save result JSON when output_file is specified."""
        from awslabs.aws_calculator_mcp_server.server import create_estimate
        import awslabs.aws_calculator_mcp_server.server as server_module

        mock_calc = MagicMock()
        mock_calc.create_estimate = AsyncMock(
            return_value={
                "estimate_url": "https://calculator.aws/#/estimate?id=save",
                "monthly_cost": "$50.00 USD/month",
                "services": [],
            }
        )
        mock_calc.close = AsyncMock()
        server_module._calculator = mock_calc

        mock_ctx = MagicMock()
        mock_ctx.info = AsyncMock()

        output_file = str(tmp_path / "output.json")
        result = await create_estimate(mock_ctx, services=[], output_file=output_file)

        import json
        with open(output_file) as f:
            saved = json.load(f)
        assert saved["estimate_url"] == "https://calculator.aws/#/estimate?id=save"

        server_module._calculator = None


class TestUpdateEstimateTool:
    """Tests for update_estimate MCP tool."""

    @pytest.mark.asyncio
    async def test_update_estimate_success(self):
        """Should call calculator.update_estimate and return result."""
        from awslabs.aws_calculator_mcp_server.server import update_estimate
        import awslabs.aws_calculator_mcp_server.server as server_module

        mock_calc = MagicMock()
        mock_calc.update_estimate = AsyncMock(
            return_value={
                "estimate_url": "https://calculator.aws/#/estimate?id=updated",
                "monthly_cost": "$200.00 USD/month",
                "services_added": [],
                "services_removed": ["AWS Shield"],
                "based_on": "https://calculator.aws/#/estimate?id=old",
            }
        )
        mock_calc.close = AsyncMock()
        server_module._calculator = mock_calc

        mock_ctx = MagicMock()
        mock_ctx.info = AsyncMock()

        result = await update_estimate(
            mock_ctx,
            estimate_url="https://calculator.aws/#/estimate?id=old",
            remove_services=["AWS Shield"],
        )

        assert result["estimate_url"] == "https://calculator.aws/#/estimate?id=updated"
        mock_calc.close.assert_called_once()

        server_module._calculator = None

    @pytest.mark.asyncio
    async def test_update_estimate_handles_exception(self):
        """Should return error dict on exception."""
        from awslabs.aws_calculator_mcp_server.server import update_estimate
        import awslabs.aws_calculator_mcp_server.server as server_module

        mock_calc = MagicMock()
        mock_calc.update_estimate = AsyncMock(side_effect=Exception("Network timeout"))
        mock_calc.close = AsyncMock()
        server_module._calculator = mock_calc

        mock_ctx = MagicMock()
        mock_ctx.info = AsyncMock()

        result = await update_estimate(
            mock_ctx, estimate_url="https://calculator.aws/#/estimate?id=fail"
        )

        assert "error" in result
        assert "Network timeout" in result["error"]
        mock_calc.close.assert_called_once()

        server_module._calculator = None
