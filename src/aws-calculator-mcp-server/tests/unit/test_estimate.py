"""Tests for EstimateManager.

Verifies save_service, rename_estimate, and get_share_link with mocked page.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from awslabs.aws_calculator_mcp_server.estimate import EstimateManager, CALCULATOR_BASE_URL


class TestSaveService:
    """Tests for save_service method."""

    @pytest.mark.asyncio
    async def test_clicks_save_button(self, mock_page):
        """Should click the 'Save and add service' button."""
        save_btn = MagicMock()
        save_btn.click = AsyncMock()
        mock_page.get_by_role = MagicMock(return_value=save_btn)
        mock_page.wait_for_timeout = AsyncMock()

        manager = EstimateManager(mock_page)
        await manager.save_service()

        mock_page.get_by_role.assert_called_once_with(
            "button", name="Save and add service"
        )
        save_btn.click.assert_called_once_with(force=True, timeout=10000)
        mock_page.wait_for_timeout.assert_called_once_with(2000)


class TestRenameEstimate:
    """Tests for rename_estimate method."""

    @pytest.mark.asyncio
    async def test_successful_rename(self, mock_page):
        """Should click edit, clear name, type new name, and save."""
        edit_link = MagicMock()
        edit_link.count = AsyncMock(return_value=1)
        edit_link.first = MagicMock()
        edit_link.first.click = AsyncMock()

        name_input = MagicMock()
        name_input.count = AsyncMock(return_value=1)
        name_input.first = MagicMock()
        name_input.first.click = AsyncMock()

        save_btn = MagicMock()
        save_btn.count = AsyncMock(return_value=1)
        save_btn.first = MagicMock()
        save_btn.first.click = AsyncMock()

        def locator_router(sel):
            if 'has-text("Edit")' in sel:
                return edit_link
            if 'value="My Estimate"' in sel:
                return name_input
            if 'has-text("Save")' in sel:
                return save_btn
            return MagicMock(count=AsyncMock(return_value=0))

        mock_page.locator = MagicMock(side_effect=locator_router)
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.keyboard = MagicMock()
        mock_page.keyboard.type = AsyncMock()

        manager = EstimateManager(mock_page)
        await manager.rename_estimate("Production Estimate")

        edit_link.first.click.assert_called_once()
        name_input.first.click.assert_called_once_with(click_count=3)
        mock_page.keyboard.type.assert_called_once_with("Production Estimate")
        save_btn.first.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_edit_link_does_nothing(self, mock_page):
        """Should do nothing if Edit link is not found."""
        no_link = MagicMock()
        no_link.count = AsyncMock(return_value=0)
        mock_page.locator = MagicMock(return_value=no_link)
        mock_page.wait_for_timeout = AsyncMock()

        manager = EstimateManager(mock_page)
        await manager.rename_estimate("New Name")

        # No exception, no keyboard interaction
        assert not hasattr(mock_page.keyboard, "type") or not mock_page.keyboard.type.called

    @pytest.mark.asyncio
    async def test_no_name_input_does_not_type(self, mock_page):
        """Should not type if name input is not found after clicking Edit."""
        edit_link = MagicMock()
        edit_link.count = AsyncMock(return_value=1)
        edit_link.first = MagicMock()
        edit_link.first.click = AsyncMock()

        no_input = MagicMock()
        no_input.count = AsyncMock(return_value=0)

        def locator_router(sel):
            if 'has-text("Edit")' in sel:
                return edit_link
            return no_input

        mock_page.locator = MagicMock(side_effect=locator_router)
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.keyboard = MagicMock()
        mock_page.keyboard.type = AsyncMock()

        manager = EstimateManager(mock_page)
        await manager.rename_estimate("Test")

        mock_page.keyboard.type.assert_not_called()

    @pytest.mark.asyncio
    async def test_exception_is_caught_gracefully(self, mock_page):
        """Should catch exceptions without re-raising."""
        mock_page.locator = MagicMock(side_effect=Exception("DOM error"))
        mock_page.wait_for_timeout = AsyncMock()

        manager = EstimateManager(mock_page)
        # Should not raise
        await manager.rename_estimate("Broken")


class TestGetShareLink:
    """Tests for get_share_link method."""

    @pytest.mark.asyncio
    async def test_returns_share_url(self, mock_page):
        """Should navigate to estimate, click Share, Agree, and return URL."""
        share_btn = MagicMock()
        share_btn.count = AsyncMock(return_value=1)
        share_btn.first = MagicMock()
        share_btn.first.click = AsyncMock()

        agree_btn = MagicMock()
        agree_btn.count = AsyncMock(return_value=1)
        agree_btn.first = MagicMock()
        agree_btn.first.click = AsyncMock()

        link_input = MagicMock()
        link_input.count = AsyncMock(return_value=1)
        link_input.first = MagicMock()
        link_input.first.get_attribute = AsyncMock(
            return_value="https://calculator.aws/#/estimate?id=abc123"
        )

        def locator_router(sel):
            if 'has-text("Share")' in sel:
                return share_btn
            if 'has-text("Agree and continue")' in sel:
                return agree_btn
            if 'value*="calculator.aws"' in sel:
                return link_input
            return MagicMock(count=AsyncMock(return_value=0))

        mock_page.locator = MagicMock(side_effect=locator_router)
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=None)

        manager = EstimateManager(mock_page)
        result = await manager.get_share_link()

        assert result == "https://calculator.aws/#/estimate?id=abc123"
        mock_page.goto.assert_called_once_with(
            f"{CALCULATOR_BASE_URL}/#/estimate", wait_until="networkidle"
        )

    @pytest.mark.asyncio
    async def test_returns_error_when_no_share_button(self, mock_page):
        """Should return error message when Share button is not found."""
        no_btn = MagicMock()
        no_btn.count = AsyncMock(return_value=0)
        mock_page.locator = MagicMock(return_value=no_btn)
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=None)

        manager = EstimateManager(mock_page)
        result = await manager.get_share_link()

        assert result == "Could not generate share link"

    @pytest.mark.asyncio
    async def test_returns_error_when_no_link_input(self, mock_page):
        """Should return error when link input is not found after clicking Share."""
        share_btn = MagicMock()
        share_btn.count = AsyncMock(return_value=1)
        share_btn.first = MagicMock()
        share_btn.first.click = AsyncMock()

        agree_btn = MagicMock()
        agree_btn.count = AsyncMock(return_value=0)

        no_link = MagicMock()
        no_link.count = AsyncMock(return_value=0)

        def locator_router(sel):
            if 'has-text("Share")' in sel:
                return share_btn
            if 'has-text("Agree and continue")' in sel:
                return agree_btn
            if 'value*="calculator.aws"' in sel:
                return no_link
            return MagicMock(count=AsyncMock(return_value=0))

        mock_page.locator = MagicMock(side_effect=locator_router)
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=None)

        manager = EstimateManager(mock_page)
        result = await manager.get_share_link()

        assert result == "Could not generate share link"

    @pytest.mark.asyncio
    async def test_renames_estimate_before_sharing(self, mock_page):
        """Should call rename_estimate when estimate_name is provided."""
        share_btn = MagicMock()
        share_btn.count = AsyncMock(return_value=1)
        share_btn.first = MagicMock()
        share_btn.first.click = AsyncMock()

        agree_btn = MagicMock()
        agree_btn.count = AsyncMock(return_value=1)
        agree_btn.first = MagicMock()
        agree_btn.first.click = AsyncMock()

        link_input = MagicMock()
        link_input.count = AsyncMock(return_value=1)
        link_input.first = MagicMock()
        link_input.first.get_attribute = AsyncMock(
            return_value="https://calculator.aws/#/estimate?id=xyz"
        )

        # For rename: edit link
        edit_link = MagicMock()
        edit_link.count = AsyncMock(return_value=1)
        edit_link.first = MagicMock()
        edit_link.first.click = AsyncMock()

        name_input = MagicMock()
        name_input.count = AsyncMock(return_value=1)
        name_input.first = MagicMock()
        name_input.first.click = AsyncMock()

        save_rename_btn = MagicMock()
        save_rename_btn.count = AsyncMock(return_value=1)
        save_rename_btn.first = MagicMock()
        save_rename_btn.first.click = AsyncMock()

        def locator_router(sel):
            if 'has-text("Share")' in sel:
                return share_btn
            if 'has-text("Agree and continue")' in sel:
                return agree_btn
            if 'value*="calculator.aws"' in sel:
                return link_input
            if 'has-text("Edit")' in sel:
                return edit_link
            if 'value="My Estimate"' in sel:
                return name_input
            if 'has-text("Save")' in sel:
                return save_rename_btn
            return MagicMock(count=AsyncMock(return_value=0))

        mock_page.locator = MagicMock(side_effect=locator_router)
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=None)
        mock_page.keyboard = MagicMock()
        mock_page.keyboard.type = AsyncMock()

        manager = EstimateManager(mock_page)
        result = await manager.get_share_link(estimate_name="My Production Stack")

        assert result == "https://calculator.aws/#/estimate?id=xyz"
        mock_page.keyboard.type.assert_called_once_with("My Production Stack")

    @pytest.mark.asyncio
    async def test_no_agree_button_still_gets_link(self, mock_page):
        """Should still try to get link when Agree button is not present."""
        share_btn = MagicMock()
        share_btn.count = AsyncMock(return_value=1)
        share_btn.first = MagicMock()
        share_btn.first.click = AsyncMock()

        no_agree = MagicMock()
        no_agree.count = AsyncMock(return_value=0)

        link_input = MagicMock()
        link_input.count = AsyncMock(return_value=1)
        link_input.first = MagicMock()
        link_input.first.get_attribute = AsyncMock(
            return_value="https://calculator.aws/#/estimate?id=direct"
        )

        def locator_router(sel):
            if 'has-text("Share")' in sel:
                return share_btn
            if 'has-text("Agree and continue")' in sel:
                return no_agree
            if 'value*="calculator.aws"' in sel:
                return link_input
            return MagicMock(count=AsyncMock(return_value=0))

        mock_page.locator = MagicMock(side_effect=locator_router)
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=None)

        manager = EstimateManager(mock_page)
        result = await manager.get_share_link()

        assert result == "https://calculator.aws/#/estimate?id=direct"
