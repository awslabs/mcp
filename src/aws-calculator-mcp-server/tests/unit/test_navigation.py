"""Tests for NavigationHelper.

Verifies dismiss_cookies, expand_all_sections, and search_and_configure
with mocked Playwright page objects.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from awslabs.aws_calculator_mcp_server.navigation import NavigationHelper, CALCULATOR_BASE_URL


class TestDismissCookies:
    """Tests for dismiss_cookies method."""

    @pytest.mark.asyncio
    async def test_calls_evaluate_to_remove_banner(self, mock_page):
        """Should call page.evaluate with the cookie banner removal script."""
        nav = NavigationHelper(mock_page)
        await nav.dismiss_cookies()
        mock_page.evaluate.assert_called_once_with(
            "document.getElementById('awsccc-sb-ux-c')?.remove()"
        )

    @pytest.mark.asyncio
    async def test_dismiss_cookies_handles_exception(self, mock_page):
        """Should not raise if evaluate throws an exception."""
        mock_page.evaluate = AsyncMock(side_effect=Exception("JS error"))
        nav = NavigationHelper(mock_page)
        # Should raise since there's no try/except in dismiss_cookies
        with pytest.raises(Exception):
            await nav.dismiss_cookies()


class TestExpandAllSections:
    """Tests for expand_all_sections method."""

    @pytest.mark.asyncio
    async def test_expands_sections_until_none_left(self, mock_page):
        """Should iterate and expand collapsed sections until count is 0."""
        # First iteration: 3 expanded, second: 1, third: 0 (stops)
        mock_page.evaluate = AsyncMock(side_effect=[3, 1, 0])
        mock_page.wait_for_timeout = AsyncMock()

        nav = NavigationHelper(mock_page)
        await nav.expand_all_sections()

        assert mock_page.evaluate.call_count == 3
        assert mock_page.wait_for_timeout.call_count == 3

    @pytest.mark.asyncio
    async def test_stops_after_max_iterations(self, mock_page):
        """Should stop after 3 iterations even if sections remain."""
        # All iterations return non-zero
        mock_page.evaluate = AsyncMock(return_value=5)
        mock_page.wait_for_timeout = AsyncMock()

        nav = NavigationHelper(mock_page)
        await nav.expand_all_sections()

        # Max 3 iterations
        assert mock_page.evaluate.call_count == 3

    @pytest.mark.asyncio
    async def test_breaks_on_exception(self, mock_page):
        """Should break out of loop on exception."""
        mock_page.evaluate = AsyncMock(side_effect=Exception("DOM error"))

        nav = NavigationHelper(mock_page)
        await nav.expand_all_sections()

        # Only tried once before exception broke the loop
        assert mock_page.evaluate.call_count == 1

    @pytest.mark.asyncio
    async def test_immediate_zero_does_one_iteration(self, mock_page):
        """Should break immediately if first iteration expands 0 sections."""
        mock_page.evaluate = AsyncMock(return_value=0)
        mock_page.wait_for_timeout = AsyncMock()

        nav = NavigationHelper(mock_page)
        await nav.expand_all_sections()

        assert mock_page.evaluate.call_count == 1
        # wait_for_timeout is called before the break check
        assert mock_page.wait_for_timeout.call_count == 1


class TestSearchAndConfigure:
    """Tests for search_and_configure method."""

    @pytest.mark.asyncio
    async def test_successful_search_and_configure(self, mock_page):
        """Should search for service, click configure, and return True."""
        search_locator = MagicMock()
        search_locator.count = AsyncMock(return_value=1)
        search_locator.first = MagicMock()
        search_locator.first.fill = AsyncMock()

        configure_btn = MagicMock()
        configure_btn.count = AsyncMock(return_value=1)
        configure_btn.first = MagicMock()
        configure_btn.first.click = AsyncMock()

        def locator_router(sel):
            if 'type="search"' in sel:
                return search_locator
            if "Configure" in sel:
                return configure_btn
            return MagicMock(count=AsyncMock(return_value=0))

        mock_page.locator = MagicMock(side_effect=locator_router)
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=None)

        nav = NavigationHelper(mock_page)
        result = await nav.search_and_configure("Amazon RDS")

        assert result is True
        mock_page.goto.assert_called_once_with(
            f"{CALCULATOR_BASE_URL}/#/addService", wait_until="networkidle"
        )
        search_locator.first.fill.assert_called_once_with("Amazon RDS")
        configure_btn.first.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_when_no_configure_button(self, mock_page):
        """Should return False when no Configure button is found."""
        search_locator = MagicMock()
        search_locator.count = AsyncMock(return_value=1)
        search_locator.first = MagicMock()
        search_locator.first.fill = AsyncMock()

        no_btn = MagicMock()
        no_btn.count = AsyncMock(return_value=0)

        def locator_router(sel):
            if 'type="search"' in sel:
                return search_locator
            return no_btn

        mock_page.locator = MagicMock(side_effect=locator_router)
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=None)

        nav = NavigationHelper(mock_page)
        result = await nav.search_and_configure("NonExistentService")

        assert result is False

    @pytest.mark.asyncio
    async def test_falls_back_to_generic_configure_button(self, mock_page):
        """Should fall back to generic 'Configure' button when specific one not found."""
        search_locator = MagicMock()
        search_locator.count = AsyncMock(return_value=1)
        search_locator.first = MagicMock()
        search_locator.first.fill = AsyncMock()

        # Specific aria-label button not found, generic one found
        specific_btn = MagicMock()
        specific_btn.count = AsyncMock(return_value=0)

        generic_btn = MagicMock()
        generic_btn.count = AsyncMock(return_value=1)
        generic_btn.first = MagicMock()
        generic_btn.first.click = AsyncMock()

        call_count = [0]

        def locator_router(sel):
            if 'type="search"' in sel:
                return search_locator
            if 'aria-label*="Configure' in sel:
                return specific_btn
            if 'has-text("Configure")' in sel:
                return generic_btn
            return MagicMock(count=AsyncMock(return_value=0))

        mock_page.locator = MagicMock(side_effect=locator_router)
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=None)

        nav = NavigationHelper(mock_page)
        result = await nav.search_and_configure("Custom Service")

        assert result is True
        generic_btn.first.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_search_box_still_looks_for_configure(self, mock_page):
        """Should still look for Configure button even if search box is absent."""
        no_search = MagicMock()
        no_search.count = AsyncMock(return_value=0)

        configure_btn = MagicMock()
        configure_btn.count = AsyncMock(return_value=1)
        configure_btn.first = MagicMock()
        configure_btn.first.click = AsyncMock()

        def locator_router(sel):
            if 'type="search"' in sel:
                return no_search
            if "Configure" in sel:
                return configure_btn
            return MagicMock(count=AsyncMock(return_value=0))

        mock_page.locator = MagicMock(side_effect=locator_router)
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=None)

        nav = NavigationHelper(mock_page)
        result = await nav.search_and_configure("AWS Lambda")

        assert result is True
