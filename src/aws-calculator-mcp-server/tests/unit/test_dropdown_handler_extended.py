"""Extended tests for dropdown handlers.

Tests ChangeDropdownHandler exact match logic, CloudscapeDropdownHandler
keyboard fallback, and DropdownHandler iteration logic.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from awslabs.aws_calculator_mcp_server.fields.dropdown_handler import (
    DropdownHandler,
    ChangeDropdownHandler,
    CloudscapeDropdownHandler,
)


class TestDropdownHandlerIteration:
    """Tests for DropdownHandler iterating over multiple selects."""

    @pytest.mark.asyncio
    async def test_skips_non_matching_selects(self, mock_page):
        """Should skip selects whose parent label doesn't match."""
        select_locator = MagicMock()
        select_locator.count = AsyncMock(return_value=2)

        nth_select_0 = MagicMock()
        nth_select_0.evaluate = AsyncMock(return_value="Storage Type")
        nth_select_0.select_option = AsyncMock()

        nth_select_1 = MagicMock()
        nth_select_1.evaluate = AsyncMock(return_value="Pricing Model")
        nth_select_1.select_option = AsyncMock()

        select_locator.nth = MagicMock(
            side_effect=lambda i: nth_select_0 if i == 0 else nth_select_1
        )

        mock_page.locator = MagicMock(return_value=select_locator)
        mock_page.wait_for_timeout = AsyncMock()

        handler = DropdownHandler(mock_page)
        result = await handler.handle("Pricing Model", "OnDemand")

        assert result is True
        nth_select_0.select_option.assert_not_called()
        nth_select_1.select_option.assert_called_once_with(label="OnDemand")

    @pytest.mark.asyncio
    async def test_returns_false_when_no_label_matches(self, mock_page):
        """Should return False when none of the selects match the label."""
        select_locator = MagicMock()
        select_locator.count = AsyncMock(return_value=2)

        nth_select = MagicMock()
        nth_select.evaluate = AsyncMock(return_value="Other Label")
        select_locator.nth = MagicMock(return_value=nth_select)

        mock_page.locator = MagicMock(return_value=select_locator)
        mock_page.wait_for_timeout = AsyncMock()

        handler = DropdownHandler(mock_page)
        result = await handler.handle("Nonexistent", "value")

        assert result is False

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(self, mock_page):
        """Should return False on exception."""
        mock_page.locator = MagicMock(side_effect=Exception("DOM error"))

        handler = DropdownHandler(mock_page)
        result = await handler.handle("Field", "value")

        assert result is False


class TestChangeDropdownHandlerExactMatch:
    """Tests for ChangeDropdownHandler exact text matching logic."""

    @pytest.mark.asyncio
    async def test_exact_text_match(self, mock_page):
        """Should match when button text exactly equals current_text."""
        all_btns = MagicMock()
        all_btns.count = AsyncMock(return_value=2)

        btn0 = MagicMock()
        btn0.text_content = AsyncMock(return_value="days")
        btn0.scroll_into_view_if_needed = AsyncMock()
        btn0.click = AsyncMock()

        btn1 = MagicMock()
        btn1.text_content = AsyncMock(return_value="hours")
        btn1.scroll_into_view_if_needed = AsyncMock()
        btn1.click = AsyncMock()

        all_btns.nth = MagicMock(side_effect=lambda i: btn0 if i == 0 else btn1)

        option = MagicMock()
        option.count = AsyncMock(return_value=1)
        option.first = MagicMock()
        option.first.click = AsyncMock()

        mock_page.locator = MagicMock(return_value=all_btns)
        mock_page.get_by_role = MagicMock(return_value=option)
        mock_page.wait_for_timeout = AsyncMock()

        handler = ChangeDropdownHandler(mock_page)
        result = await handler.handle("hours", "days")

        assert result is True
        btn1.click.assert_called_once()
        option.first.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_match_when_text_is_different(self, mock_page):
        """Should not match when button text differs from current_text (not exact)."""
        all_btns = MagicMock()
        all_btns.count = AsyncMock(return_value=1)

        btn = MagicMock()
        btn.text_content = AsyncMock(return_value="per year")
        btn.scroll_into_view_if_needed = AsyncMock()
        btn.click = AsyncMock()
        all_btns.nth = MagicMock(return_value=btn)

        mock_page.locator = MagicMock(return_value=all_btns)
        mock_page.get_by_role = MagicMock(return_value=MagicMock(count=AsyncMock(return_value=0)))
        mock_page.wait_for_timeout = AsyncMock()

        handler = ChangeDropdownHandler(mock_page)
        result = await handler.handle("month", "year")

        assert result is False

    @pytest.mark.asyncio
    async def test_exact_text_match_with_whitespace(self, mock_page):
        """Should match when stripped button text exactly equals current_text."""
        all_btns = MagicMock()
        all_btns.count = AsyncMock(return_value=1)

        btn = MagicMock()
        btn.text_content = AsyncMock(return_value="  GB  ")
        btn.scroll_into_view_if_needed = AsyncMock()
        btn.click = AsyncMock()
        all_btns.nth = MagicMock(return_value=btn)

        option = MagicMock()
        option.count = AsyncMock(return_value=1)
        option.first = MagicMock()
        option.first.click = AsyncMock()

        mock_page.locator = MagicMock(return_value=all_btns)
        mock_page.get_by_role = MagicMock(return_value=option)
        mock_page.wait_for_timeout = AsyncMock()

        handler = ChangeDropdownHandler(mock_page)
        result = await handler.handle("GB", "TB")

        assert result is True

    @pytest.mark.asyncio
    async def test_fallback_to_has_text_option(self, mock_page):
        """Should try has-text match when exact role-based option not found."""
        all_btns = MagicMock()
        all_btns.count = AsyncMock(return_value=1)

        btn = MagicMock()
        btn.text_content = AsyncMock(return_value="minutes")
        btn.scroll_into_view_if_needed = AsyncMock()
        btn.click = AsyncMock()
        all_btns.nth = MagicMock(return_value=btn)

        # Role-based option: not found
        role_option = MagicMock()
        role_option.count = AsyncMock(return_value=0)

        # Has-text option: found
        text_option = MagicMock()
        text_option.count = AsyncMock(return_value=1)
        text_option.first = MagicMock()
        text_option.first.click = AsyncMock()

        def locator_fn(sel):
            if "main button" in sel:
                return all_btns
            if 'role="option"' in sel:
                return text_option
            return MagicMock(count=AsyncMock(return_value=0))

        mock_page.locator = MagicMock(side_effect=locator_fn)
        mock_page.get_by_role = MagicMock(return_value=role_option)
        mock_page.wait_for_timeout = AsyncMock()

        handler = ChangeDropdownHandler(mock_page)
        result = await handler.handle("minutes", "seconds")

        assert result is True
        text_option.first.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_escape_pressed_when_no_option_found(self, mock_page):
        """Should press Escape and return False when no option matches."""
        all_btns = MagicMock()
        all_btns.count = AsyncMock(return_value=1)

        btn = MagicMock()
        btn.text_content = AsyncMock(return_value="minutes")
        btn.scroll_into_view_if_needed = AsyncMock()
        btn.click = AsyncMock()
        all_btns.nth = MagicMock(return_value=btn)

        no_option = MagicMock()
        no_option.count = AsyncMock(return_value=0)

        def locator_fn(sel):
            if "main button" in sel:
                return all_btns
            return no_option

        mock_page.locator = MagicMock(side_effect=locator_fn)
        mock_page.get_by_role = MagicMock(return_value=no_option)
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.keyboard = MagicMock()
        mock_page.keyboard.press = AsyncMock()

        handler = ChangeDropdownHandler(mock_page)
        result = await handler.handle("minutes", "nonexistent_option")

        assert result is False
        mock_page.keyboard.press.assert_called_with("Escape")

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(self, mock_page):
        """Should return False on exception."""
        mock_page.locator = MagicMock(side_effect=Exception("error"))

        handler = ChangeDropdownHandler(mock_page)
        result = await handler.handle("text", "value")

        assert result is False


class TestCloudscapeDropdownHandlerExtended:
    """Extended tests for CloudscapeDropdownHandler."""

    @pytest.mark.asyncio
    async def test_keyboard_type_fallback(self, mock_page):
        """Should type value to filter when first option search fails."""
        mock_page.evaluate = AsyncMock(return_value="btn-42")

        btn_locator = MagicMock()
        btn_locator.scroll_into_view_if_needed = AsyncMock()
        btn_locator.click = AsyncMock()

        # First option search: nothing, second (after type): found
        call_count = [0]
        option_empty = MagicMock()
        option_empty.count = AsyncMock(return_value=0)

        option_found = MagicMock()
        option_found.count = AsyncMock(return_value=1)
        option_found.first = MagicMock()
        option_found.first.click = AsyncMock()

        def get_by_role_fn(role, name=None, exact=False):
            call_count[0] += 1
            if call_count[0] <= 1:
                return option_empty
            return option_found

        def locator_fn(sel):
            if "btn-42" in sel:
                return btn_locator
            return MagicMock(count=AsyncMock(return_value=0))

        mock_page.locator = MagicMock(side_effect=locator_fn)
        mock_page.get_by_role = MagicMock(side_effect=get_by_role_fn)
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.keyboard = MagicMock()
        mock_page.keyboard.type = AsyncMock()
        mock_page.keyboard.press = AsyncMock()

        handler = CloudscapeDropdownHandler(mock_page)
        result = await handler.handle("Deployment", "Multi-AZ")

        assert result is True
        mock_page.keyboard.type.assert_called_once_with("Multi-AZ")
        option_found.first.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_enter_fallback_when_nothing_found(self, mock_page):
        """Should press Enter as last resort when no option is ever found."""
        mock_page.evaluate = AsyncMock(return_value="btn-99")

        btn_locator = MagicMock()
        btn_locator.scroll_into_view_if_needed = AsyncMock()
        btn_locator.click = AsyncMock()

        option_empty = MagicMock()
        option_empty.count = AsyncMock(return_value=0)

        def locator_fn(sel):
            if "btn-99" in sel:
                return btn_locator
            return MagicMock(count=AsyncMock(return_value=0))

        mock_page.locator = MagicMock(side_effect=locator_fn)
        mock_page.get_by_role = MagicMock(return_value=option_empty)
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.keyboard = MagicMock()
        mock_page.keyboard.type = AsyncMock()
        mock_page.keyboard.press = AsyncMock()

        handler = CloudscapeDropdownHandler(mock_page)
        result = await handler.handle("Region", "custom-value")

        assert result is True
        mock_page.keyboard.press.assert_called_with("Enter")

    @pytest.mark.asyncio
    async def test_handles_exception_returns_false(self, mock_page):
        """Should catch exceptions and return False."""
        mock_page.evaluate = AsyncMock(side_effect=Exception("JS crash"))

        handler = CloudscapeDropdownHandler(mock_page)
        result = await handler.handle("Label", "value")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_btn_id_is_none(self, mock_page):
        """Should return False immediately when evaluate returns None."""
        mock_page.evaluate = AsyncMock(return_value=None)

        handler = CloudscapeDropdownHandler(mock_page)
        result = await handler.handle("Unknown", "value")

        assert result is False
