"""Extended tests for positional handlers.

Tests fallback paths for PositionalDropdownHandler, PositionalInputHandler,
and UnitHandler.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from awslabs.aws_calculator_mcp_server.fields.positional_handler import (
    PositionalDropdownHandler,
    PositionalInputHandler,
    UnitHandler,
)


class TestPositionalDropdownFallback:
    """Tests for PositionalDropdownHandler fallback to has-text option."""

    @pytest.mark.asyncio
    async def test_falls_back_to_has_text_option(self, mock_page):
        """Should try has-text match when exact role option not found."""
        btn_locator = MagicMock()
        btn_locator.count = AsyncMock(return_value=3)
        btn_nth = MagicMock()
        btn_nth.click = AsyncMock()
        btn_locator.nth = MagicMock(return_value=btn_nth)

        # Exact role option: not found
        exact_option = MagicMock()
        exact_option.count = AsyncMock(return_value=0)

        # Has-text option: found
        text_option = MagicMock()
        text_option.count = AsyncMock(return_value=1)
        text_option.first = MagicMock()
        text_option.first.click = AsyncMock()

        def locator_fn(sel):
            if "button:has-text" in sel:
                return btn_locator
            if 'role="option"' in sel:
                return text_option
            return MagicMock(count=AsyncMock(return_value=0))

        mock_page.locator = MagicMock(side_effect=locator_fn)
        mock_page.get_by_role = MagicMock(return_value=exact_option)
        mock_page.wait_for_timeout = AsyncMock()

        handler = PositionalDropdownHandler(mock_page)
        result = await handler.handle("_nth_dropdown:1:Pricing", "Custom Value")

        assert result is True
        text_option.first.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_presses_escape_when_no_option_found(self, mock_page):
        """Should press Escape and return True (still clicked btn) when no option matches."""
        btn_locator = MagicMock()
        btn_locator.count = AsyncMock(return_value=2)
        btn_nth = MagicMock()
        btn_nth.click = AsyncMock()
        btn_locator.nth = MagicMock(return_value=btn_nth)

        no_option = MagicMock()
        no_option.count = AsyncMock(return_value=0)

        def locator_fn(sel):
            if "button:has-text" in sel:
                return btn_locator
            return no_option

        mock_page.locator = MagicMock(side_effect=locator_fn)
        mock_page.get_by_role = MagicMock(return_value=no_option)
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.keyboard = MagicMock()
        mock_page.keyboard.press = AsyncMock()

        handler = PositionalDropdownHandler(mock_page)
        result = await handler.handle("_nth_dropdown:1:Select", "Nonexistent")

        assert result is True
        mock_page.keyboard.press.assert_called_with("Escape")

    @pytest.mark.asyncio
    async def test_handles_exception_returns_false(self, mock_page):
        """Should catch exceptions and return False."""
        mock_page.locator = MagicMock(side_effect=Exception("DOM error"))

        handler = PositionalDropdownHandler(mock_page)
        result = await handler.handle("_nth_dropdown:1:X", "value")

        assert result is False


class TestPositionalInputException:
    """Tests for PositionalInputHandler exception handling."""

    @pytest.mark.asyncio
    async def test_handles_exception_returns_false(self, mock_page):
        """Should catch exceptions and return False."""
        mock_page.locator = MagicMock(side_effect=Exception("DOM error"))

        handler = PositionalInputHandler(mock_page)
        result = await handler.handle("_nth_input:1:Enter Amount", "50")

        assert result is False


class TestUnitHandlerFallback:
    """Tests for UnitHandler Escape fallback and exception."""

    @pytest.mark.asyncio
    async def test_presses_escape_when_no_option_found(self, mock_page):
        """Should press Escape when option is not found after clicking unit button."""
        mock_page.evaluate = AsyncMock(side_effect=[True, None])

        btn_locator = MagicMock()
        btn_locator.click = AsyncMock()

        option_locator = MagicMock()
        option_locator.count = AsyncMock(return_value=0)

        def locator_fn(sel):
            if "data-calc-unit-target" in sel:
                return btn_locator
            if 'role="option"' in sel:
                return option_locator
            return MagicMock(count=AsyncMock(return_value=0))

        mock_page.locator = MagicMock(side_effect=locator_fn)
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.keyboard = MagicMock()
        mock_page.keyboard.press = AsyncMock()

        handler = UnitHandler(mock_page)
        result = await handler.handle("Storage amount", "PB")

        assert result is False
        mock_page.keyboard.press.assert_called_with("Escape")

    @pytest.mark.asyncio
    async def test_handles_exception_returns_false(self, mock_page):
        """Should catch exceptions and return False."""
        mock_page.evaluate = AsyncMock(side_effect=Exception("JS error"))

        handler = UnitHandler(mock_page)
        result = await handler.handle("Field", "GB")

        assert result is False
