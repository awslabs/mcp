"""Tests for AWSCalculatorAutomation (calculator.py).

Verifies _configure_service, create_estimate, and update_estimate
orchestration with all dependencies mocked.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from awslabs.aws_calculator_mcp_server.calculator import AWSCalculatorAutomation


@pytest.fixture
def automation():
    """Create an AWSCalculatorAutomation with a mocked BrowserManager."""
    auto = AWSCalculatorAutomation(headless=True)
    # Mock the browser manager
    mock_page = MagicMock()
    mock_page.goto = AsyncMock()
    mock_page.wait_for_timeout = AsyncMock()
    mock_page.url = "https://calculator.aws/#/addService/test"

    # Description input for triggering recalculation
    desc_locator = MagicMock()
    desc_locator.count = AsyncMock(return_value=1)
    desc_locator.first = MagicMock()
    desc_locator.first.click = AsyncMock()

    # Main locator for radio check
    main_locator = MagicMock()
    main_locator.text_content = AsyncMock(return_value="OnDemand Reserved Spot")

    def locator_fn(sel):
        if "Description" in sel:
            return desc_locator
        if sel == "main":
            return main_locator
        return MagicMock(count=AsyncMock(return_value=0))

    mock_page.locator = MagicMock(side_effect=locator_fn)
    mock_page.evaluate = AsyncMock(return_value=None)
    mock_page.keyboard = MagicMock()
    mock_page.keyboard.type = AsyncMock()
    mock_page.keyboard.press = AsyncMock()

    auto._browser_manager = MagicMock()
    auto._browser_manager.page = mock_page
    auto._browser_manager.ensure_browser = AsyncMock(return_value=mock_page)
    auto._browser_manager.close = AsyncMock()

    return auto


class TestConfigureService:
    """Tests for _configure_service method."""

    @pytest.mark.asyncio
    async def test_returns_not_found_when_search_fails(self, automation):
        """Should return status 'not_found' when search_and_configure returns False."""
        mock_nav = MagicMock()
        mock_nav.search_and_configure = AsyncMock(return_value=False)

        result = await automation._configure_service(
            "NonExistent", {"field": "value"}, "US East (N. Virginia)", mock_nav
        )

        assert result == {"service_name": "NonExistent", "status": "not_found"}

    @pytest.mark.asyncio
    async def test_configures_service_successfully(self, automation):
        """Should process fields, read cost, and save when service is found."""
        mock_nav = MagicMock()
        mock_nav.search_and_configure = AsyncMock(return_value=True)

        with patch(
            "awslabs.aws_calculator_mcp_server.calculator.RegionSelector"
        ) as MockRegion, patch(
            "awslabs.aws_calculator_mcp_server.calculator.FieldProcessor"
        ) as MockFieldProc, patch(
            "awslabs.aws_calculator_mcp_server.calculator.CostReader"
        ) as MockCost, patch(
            "awslabs.aws_calculator_mcp_server.calculator.EstimateManager"
        ) as MockEstimate:
            MockRegion.return_value.select_region = AsyncMock()
            MockFieldProc.return_value.process_radio = AsyncMock()
            MockFieldProc.return_value.process_field = AsyncMock(return_value=True)
            MockCost.return_value.get_current_cost = AsyncMock(return_value="45.67")
            MockEstimate.return_value.save_service = AsyncMock()

            result = await automation._configure_service(
                "Amazon RDS",
                {"Nodes": "2", "Storage amount": "100"},
                "US East (N. Virginia)",
                mock_nav,
            )

        assert result["service_name"] == "Amazon RDS"
        assert result["status"] == "added"
        assert result["monthly_cost"] == "45.67"

    @pytest.mark.asyncio
    async def test_processes_radio_field(self, automation):
        """Should process _radio field before other fields."""
        mock_nav = MagicMock()
        mock_nav.search_and_configure = AsyncMock(return_value=True)

        with patch(
            "awslabs.aws_calculator_mcp_server.calculator.RegionSelector"
        ) as MockRegion, patch(
            "awslabs.aws_calculator_mcp_server.calculator.FieldProcessor"
        ) as MockFieldProc, patch(
            "awslabs.aws_calculator_mcp_server.calculator.CostReader"
        ) as MockCost, patch(
            "awslabs.aws_calculator_mcp_server.calculator.EstimateManager"
        ) as MockEstimate:
            MockRegion.return_value.select_region = AsyncMock()
            MockFieldProc.return_value.process_radio = AsyncMock()
            MockFieldProc.return_value.process_field = AsyncMock(return_value=True)
            MockCost.return_value.get_current_cost = AsyncMock(return_value="10.00")
            MockEstimate.return_value.save_service = AsyncMock()

            result = await automation._configure_service(
                "Amazon EC2",
                {"_radio": "OnDemand", "Number of instances": "3"},
                "US East (N. Virginia)",
                mock_nav,
            )

        assert result["status"] == "added"
        MockFieldProc.return_value.process_radio.assert_called_once_with("OnDemand")


class TestCreateEstimate:
    """Tests for create_estimate method."""

    @pytest.mark.asyncio
    async def test_creates_estimate_with_services(self, automation):
        """Should configure services and return share link and cost."""
        with patch.object(
            automation, "_configure_service", new_callable=AsyncMock
        ) as mock_configure, patch(
            "awslabs.aws_calculator_mcp_server.calculator.EstimateManager"
        ) as MockEstimate, patch(
            "awslabs.aws_calculator_mcp_server.calculator.CostReader"
        ) as MockCost, patch(
            "awslabs.aws_calculator_mcp_server.calculator.NavigationHelper"
        ) as MockNav:
            mock_configure.return_value = {
                "service_name": "Amazon RDS",
                "status": "added",
                "monthly_cost": "50.00",
            }
            MockNav.return_value.dismiss_cookies = AsyncMock()
            MockEstimate.return_value.get_share_link = AsyncMock(
                return_value="https://calculator.aws/#/estimate?id=test123"
            )
            MockCost.return_value.get_total_cost = AsyncMock(
                return_value="$50.00 USD/month"
            )

            services = [
                {
                    "service_name": "Amazon RDS",
                    "config": {"Nodes": "1"},
                    "region": "US East (N. Virginia)",
                }
            ]
            result = await automation.create_estimate(services)

        assert result["estimate_url"] == "https://calculator.aws/#/estimate?id=test123"
        assert result["monthly_cost"] == "$50.00 USD/month"
        assert len(result["services"]) == 1

    @pytest.mark.asyncio
    async def test_create_estimate_default_region(self, automation):
        """Should use default region when not specified."""
        with patch.object(
            automation, "_configure_service", new_callable=AsyncMock
        ) as mock_configure, patch(
            "awslabs.aws_calculator_mcp_server.calculator.EstimateManager"
        ) as MockEstimate, patch(
            "awslabs.aws_calculator_mcp_server.calculator.CostReader"
        ) as MockCost, patch(
            "awslabs.aws_calculator_mcp_server.calculator.NavigationHelper"
        ) as MockNav:
            mock_configure.return_value = {
                "service_name": "AWS Lambda",
                "status": "added",
                "monthly_cost": "5.00",
            }
            MockNav.return_value.dismiss_cookies = AsyncMock()
            MockEstimate.return_value.get_share_link = AsyncMock(
                return_value="https://calculator.aws/#/estimate?id=lam"
            )
            MockCost.return_value.get_total_cost = AsyncMock(
                return_value="$5.00 USD/month"
            )

            services = [{"service_name": "AWS Lambda", "config": {"Number of requests": "1000"}}]
            result = await automation.create_estimate(services)

        # Verify default region was passed
        call_args = mock_configure.call_args
        assert call_args[0][2] == "US East (N. Virginia)"

    @pytest.mark.asyncio
    async def test_create_estimate_no_share_url_skips_navigation(self, automation):
        """Should not navigate to share URL if it doesn't contain calculator.aws."""
        with patch.object(
            automation, "_configure_service", new_callable=AsyncMock
        ) as mock_configure, patch(
            "awslabs.aws_calculator_mcp_server.calculator.EstimateManager"
        ) as MockEstimate, patch(
            "awslabs.aws_calculator_mcp_server.calculator.CostReader"
        ) as MockCost, patch(
            "awslabs.aws_calculator_mcp_server.calculator.NavigationHelper"
        ) as MockNav:
            mock_configure.return_value = {
                "service_name": "Test",
                "status": "added",
                "monthly_cost": "0.00",
            }
            MockNav.return_value.dismiss_cookies = AsyncMock()
            MockEstimate.return_value.get_share_link = AsyncMock(
                return_value="Could not generate share link"
            )
            MockCost.return_value.get_total_cost = AsyncMock(return_value="Unknown")

            services = [{"service_name": "Test", "config": {}}]
            result = await automation.create_estimate(services)

        assert result["estimate_url"] == "Could not generate share link"
        # page.goto should only be called once (initial navigation)
        page = automation._browser_manager.page
        page.goto.assert_called_once()


class TestUpdateEstimate:
    """Tests for update_estimate method."""

    @pytest.mark.asyncio
    async def test_update_estimate_with_add_and_remove(self, automation):
        """Should load estimate, remove services, add services, and return new link."""
        page = automation._browser_manager.page

        # Update button
        update_btn = MagicMock()
        update_btn.count = AsyncMock(return_value=1)
        update_btn.click = AsyncMock()

        # Delete button for removal
        delete_btn = MagicMock()
        delete_btn.count = AsyncMock(return_value=1)
        delete_btn.first = MagicMock()
        delete_btn.first.click = AsyncMock()

        # Confirm delete dialog
        confirm_btn = MagicMock()
        confirm_btn.count = AsyncMock(return_value=2)
        confirm_btn.last = MagicMock()
        confirm_btn.last.click = AsyncMock()

        desc_locator = MagicMock()
        desc_locator.count = AsyncMock(return_value=1)
        desc_locator.first = MagicMock()
        desc_locator.first.click = AsyncMock()

        def locator_fn(sel):
            if "Update estimate" in sel:
                return update_btn
            if "Delete" in sel and "aria-label" in sel:
                return delete_btn
            if 'has-text("Delete")' in sel:
                return confirm_btn
            if "Description" in sel:
                return desc_locator
            return MagicMock(count=AsyncMock(return_value=0))

        page.locator = MagicMock(side_effect=locator_fn)

        with patch.object(
            automation, "_configure_service", new_callable=AsyncMock
        ) as mock_configure, patch(
            "awslabs.aws_calculator_mcp_server.calculator.EstimateManager"
        ) as MockEstimate, patch(
            "awslabs.aws_calculator_mcp_server.calculator.CostReader"
        ) as MockCost, patch(
            "awslabs.aws_calculator_mcp_server.calculator.NavigationHelper"
        ) as MockNav:
            mock_configure.return_value = {
                "service_name": "AWS Fargate",
                "status": "added",
                "monthly_cost": "30.00",
            }
            MockNav.return_value.dismiss_cookies = AsyncMock()
            MockEstimate.return_value.get_share_link = AsyncMock(
                return_value="https://calculator.aws/#/estimate?id=updated"
            )
            MockCost.return_value.get_total_cost = AsyncMock(
                return_value="$80.00 USD/month"
            )

            result = await automation.update_estimate(
                estimate_url="https://calculator.aws/#/estimate?id=old",
                add_services=[
                    {"service_name": "AWS Fargate", "config": {"Number of tasks": "4"}}
                ],
                remove_services=["AWS Shield"],
            )

        assert result["estimate_url"] == "https://calculator.aws/#/estimate?id=updated"
        assert result["monthly_cost"] == "$80.00 USD/month"
        assert result["services_removed"] == ["AWS Shield"]
        assert result["based_on"] == "https://calculator.aws/#/estimate?id=old"

    @pytest.mark.asyncio
    async def test_update_estimate_no_update_button(self, automation):
        """Should return error when Update estimate button is not found."""
        page = automation._browser_manager.page

        no_btn = MagicMock()
        no_btn.count = AsyncMock(return_value=0)
        page.locator = MagicMock(return_value=no_btn)

        with patch(
            "awslabs.aws_calculator_mcp_server.calculator.NavigationHelper"
        ) as MockNav:
            MockNav.return_value.dismiss_cookies = AsyncMock()

            result = await automation.update_estimate(
                estimate_url="https://calculator.aws/#/estimate?id=nope"
            )

        assert "error" in result
        assert "Update estimate" in result["error"]

    @pytest.mark.asyncio
    async def test_update_estimate_no_services_to_add_or_remove(self, automation):
        """Should handle case with no add or remove services."""
        page = automation._browser_manager.page

        update_btn = MagicMock()
        update_btn.count = AsyncMock(return_value=1)
        update_btn.click = AsyncMock()

        def locator_fn(sel):
            if "Update estimate" in sel:
                return update_btn
            return MagicMock(count=AsyncMock(return_value=0))

        page.locator = MagicMock(side_effect=locator_fn)

        with patch(
            "awslabs.aws_calculator_mcp_server.calculator.EstimateManager"
        ) as MockEstimate, patch(
            "awslabs.aws_calculator_mcp_server.calculator.CostReader"
        ) as MockCost, patch(
            "awslabs.aws_calculator_mcp_server.calculator.NavigationHelper"
        ) as MockNav:
            MockNav.return_value.dismiss_cookies = AsyncMock()
            MockEstimate.return_value.get_share_link = AsyncMock(
                return_value="https://calculator.aws/#/estimate?id=unchanged"
            )
            MockCost.return_value.get_total_cost = AsyncMock(
                return_value="$100.00 USD/month"
            )

            result = await automation.update_estimate(
                estimate_url="https://calculator.aws/#/estimate?id=orig"
            )

        assert result["estimate_url"] == "https://calculator.aws/#/estimate?id=unchanged"
        assert result["services_added"] == []
        assert result["services_removed"] == []

    @pytest.mark.asyncio
    async def test_update_estimate_delete_button_not_found(self, automation):
        """Should log warning when delete button for a service is not found."""
        page = automation._browser_manager.page

        update_btn = MagicMock()
        update_btn.count = AsyncMock(return_value=1)
        update_btn.click = AsyncMock()

        no_delete = MagicMock()
        no_delete.count = AsyncMock(return_value=0)

        def locator_fn(sel):
            if "Update estimate" in sel:
                return update_btn
            return no_delete

        page.locator = MagicMock(side_effect=locator_fn)

        with patch(
            "awslabs.aws_calculator_mcp_server.calculator.EstimateManager"
        ) as MockEstimate, patch(
            "awslabs.aws_calculator_mcp_server.calculator.CostReader"
        ) as MockCost, patch(
            "awslabs.aws_calculator_mcp_server.calculator.NavigationHelper"
        ) as MockNav:
            MockNav.return_value.dismiss_cookies = AsyncMock()
            MockEstimate.return_value.get_share_link = AsyncMock(
                return_value="https://calculator.aws/#/estimate?id=partial"
            )
            MockCost.return_value.get_total_cost = AsyncMock(
                return_value="$50.00 USD/month"
            )

            result = await automation.update_estimate(
                estimate_url="https://calculator.aws/#/estimate?id=x",
                remove_services=["Nonexistent Service"],
            )

        # Should still return a result even if deletion failed
        assert result["estimate_url"] == "https://calculator.aws/#/estimate?id=partial"


class TestClose:
    """Tests for close method."""

    @pytest.mark.asyncio
    async def test_close_delegates_to_browser_manager(self, automation):
        """Should delegate close to the browser manager."""
        await automation.close()
        automation._browser_manager.close.assert_called_once()
