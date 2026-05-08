"""Tests for BrowserManager lifecycle management.

Verifies browser initialization, page property, ensure_browser, and close
with fully mocked Playwright objects.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from awslabs.aws_calculator_mcp_server.browser import BrowserManager


class TestBrowserManagerInit:
    """Tests for BrowserManager initialization."""

    def test_default_headless(self):
        """Should default to headless=True."""
        manager = BrowserManager()
        assert manager._headless is True

    def test_custom_headless(self):
        """Should accept headless=False."""
        manager = BrowserManager(headless=False)
        assert manager._headless is False

    def test_initial_state_is_none(self):
        """All internal state should be None on init."""
        manager = BrowserManager()
        assert manager._playwright is None
        assert manager._browser is None
        assert manager._context is None
        assert manager._page is None


class TestBrowserManagerPage:
    """Tests for the page property."""

    def test_page_returns_none_before_ensure(self):
        """Should return None before ensure_browser is called."""
        manager = BrowserManager()
        assert manager.page is None

    def test_page_returns_page_after_set(self):
        """Should return the page object after it is set."""
        manager = BrowserManager()
        mock_page = MagicMock()
        manager._page = mock_page
        assert manager.page is mock_page


class TestBrowserManagerEnsureBrowser:
    """Tests for ensure_browser method."""

    @pytest.mark.asyncio
    async def test_launches_browser_on_first_call(self):
        """Should launch Playwright, browser, context, and page on first call."""
        manager = BrowserManager(headless=True)

        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser = MagicMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_playwright = MagicMock()
        mock_playwright.chromium = MagicMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_pw_cm = MagicMock()
        mock_pw_cm.start = AsyncMock(return_value=mock_playwright)

        with patch(
            "awslabs.aws_calculator_mcp_server.browser.async_playwright",
            return_value=mock_pw_cm,
        ):
            result = await manager.ensure_browser()

        assert result is mock_page
        assert manager._page is mock_page
        assert manager._browser is mock_browser
        assert manager._context is mock_context
        mock_playwright.chromium.launch.assert_called_once_with(headless=True)
        mock_browser.new_context.assert_called_once_with(
            viewport={"width": 1920, "height": 4000}
        )

    @pytest.mark.asyncio
    async def test_reuses_existing_browser_on_second_call(self):
        """Should not re-launch if browser already exists."""
        manager = BrowserManager()
        mock_page = MagicMock()
        mock_browser = MagicMock()
        manager._browser = mock_browser
        manager._page = mock_page

        result = await manager.ensure_browser()
        assert result is mock_page

    @pytest.mark.asyncio
    async def test_headless_false_passed_to_launch(self):
        """Should pass headless=False to chromium.launch."""
        manager = BrowserManager(headless=False)

        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser = MagicMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_playwright = MagicMock()
        mock_playwright.chromium = MagicMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_pw_cm = MagicMock()
        mock_pw_cm.start = AsyncMock(return_value=mock_playwright)

        with patch(
            "awslabs.aws_calculator_mcp_server.browser.async_playwright",
            return_value=mock_pw_cm,
        ):
            await manager.ensure_browser()

        mock_playwright.chromium.launch.assert_called_once_with(headless=False)


class TestBrowserManagerClose:
    """Tests for close method."""

    @pytest.mark.asyncio
    async def test_close_cleans_up_all_state(self):
        """Should close browser, stop playwright, and null all state."""
        manager = BrowserManager()
        mock_browser = MagicMock()
        mock_browser.close = AsyncMock()
        mock_playwright = MagicMock()
        mock_playwright.stop = AsyncMock()

        manager._browser = mock_browser
        manager._playwright = mock_playwright
        manager._page = MagicMock()
        manager._context = MagicMock()

        await manager.close()

        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()
        assert manager._browser is None
        assert manager._playwright is None
        assert manager._page is None
        assert manager._context is None

    @pytest.mark.asyncio
    async def test_close_when_no_browser(self):
        """Should handle close gracefully when no browser was started."""
        manager = BrowserManager()
        await manager.close()
        assert manager._page is None
        assert manager._context is None

    @pytest.mark.asyncio
    async def test_close_with_browser_but_no_playwright(self):
        """Should handle close when browser exists but playwright is None."""
        manager = BrowserManager()
        mock_browser = MagicMock()
        mock_browser.close = AsyncMock()
        manager._browser = mock_browser
        manager._playwright = None
        manager._page = MagicMock()
        manager._context = MagicMock()

        await manager.close()

        mock_browser.close.assert_called_once()
        assert manager._browser is None
        assert manager._page is None
        assert manager._context is None
