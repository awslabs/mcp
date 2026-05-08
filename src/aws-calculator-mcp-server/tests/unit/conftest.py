"""Shared fixtures for unit tests.

Provides mock Playwright page and related objects for testing handlers
without launching a real browser.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_page():
    """Create a mock Playwright Page with common methods stubbed.

    Returns a MagicMock configured to behave like an async Playwright Page.
    All methods that return awaitables are set up as AsyncMock.
    """
    page = MagicMock()

    # Core page methods
    page.evaluate = AsyncMock(return_value=None)
    page.goto = AsyncMock()
    page.wait_for_timeout = AsyncMock()

    # Keyboard
    page.keyboard = MagicMock()
    page.keyboard.type = AsyncMock()
    page.keyboard.press = AsyncMock()

    # Locator setup - return a mock locator by default
    mock_locator = MagicMock()
    mock_locator.count = AsyncMock(return_value=0)
    mock_locator.first = MagicMock()
    mock_locator.first.click = AsyncMock()
    mock_locator.first.fill = AsyncMock()
    mock_locator.first.get_attribute = AsyncMock(return_value=None)
    mock_locator.first.text_content = AsyncMock(return_value="")
    mock_locator.first.scroll_into_view_if_needed = AsyncMock()
    mock_locator.nth = MagicMock(return_value=mock_locator.first)
    mock_locator.fill = AsyncMock()
    mock_locator.click = AsyncMock()
    mock_locator.scroll_into_view_if_needed = AsyncMock()
    mock_locator.text_content = AsyncMock(return_value="")
    mock_locator.get_attribute = AsyncMock(return_value=None)

    page.locator = MagicMock(return_value=mock_locator)
    page.get_by_role = MagicMock(return_value=mock_locator)

    return page


@pytest.fixture
def mock_locator_with_count(mock_page):
    """Factory fixture to create locators with specific counts.

    Returns a function that configures mock_page.locator to return
    a locator with the specified count for a given selector.
    """
    def _factory(selector: str, count: int, text_content: str = ""):
        locator = MagicMock()
        locator.count = AsyncMock(return_value=count)
        locator.first = MagicMock()
        locator.first.click = AsyncMock()
        locator.first.fill = AsyncMock()
        locator.first.get_attribute = AsyncMock(return_value="test-id")
        locator.first.text_content = AsyncMock(return_value=text_content)
        locator.first.scroll_into_view_if_needed = AsyncMock()
        locator.nth = MagicMock(return_value=locator.first)
        locator.fill = AsyncMock()
        locator.click = AsyncMock()
        locator.scroll_into_view_if_needed = AsyncMock()
        locator.text_content = AsyncMock(return_value=text_content)
        locator.get_attribute = AsyncMock(return_value="test-id")

        original_locator = mock_page.locator

        def smart_locator(sel):
            if selector in sel:
                return locator
            return original_locator(sel)

        mock_page.locator = MagicMock(side_effect=smart_locator)
        return locator

    return _factory
