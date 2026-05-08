"""Tests for individual field handlers.

Each handler is tested with mocked Playwright page objects to verify
the correct DOM interactions without launching a browser.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from awslabs.aws_calculator_mcp_server.fields.input_handler import (
    NumberFieldHandler,
    TextFieldHandler,
)
from awslabs.aws_calculator_mcp_server.fields.dropdown_handler import (
    DropdownHandler,
    ChangeDropdownHandler,
    CloudscapeDropdownHandler,
)
from awslabs.aws_calculator_mcp_server.fields.autosuggest_handler import AutosuggestHandler
from awslabs.aws_calculator_mcp_server.fields.radio_handler import RadioHandler
from awslabs.aws_calculator_mcp_server.fields.positional_handler import (
    PositionalDropdownHandler,
    PositionalInputHandler,
    UnitHandler,
)


# --- NumberFieldHandler ---


class TestNumberFieldHandler:
    """Tests for NumberFieldHandler."""

    @pytest.mark.asyncio
    async def test_fills_by_aria_label(self, mock_page):
        """Should fill input found by aria-label match."""
        inp_locator = MagicMock()
        inp_locator.count = AsyncMock(return_value=1)
        inp_locator.first = MagicMock()
        inp_locator.first.fill = AsyncMock()

        mock_page.locator = MagicMock(return_value=inp_locator)
        mock_page.wait_for_timeout = AsyncMock()

        handler = NumberFieldHandler(mock_page)
        result = await handler.handle("Number of tasks", "5")

        assert result is True
        inp_locator.first.fill.assert_called_with("5", timeout=3000)

    @pytest.mark.asyncio
    async def test_returns_false_when_no_input_found(self, mock_page):
        """Should return False when no matching input exists."""
        inp_locator = MagicMock()
        inp_locator.count = AsyncMock(return_value=0)
        mock_page.locator = MagicMock(return_value=inp_locator)
        mock_page.evaluate = AsyncMock(return_value=None)

        handler = NumberFieldHandler(mock_page)
        result = await handler.handle("Nonexistent field", "10")

        assert result is False

    @pytest.mark.asyncio
    async def test_falls_back_to_label_strategy(self, mock_page):
        """Should fall back to finding input via label container when aria-label fails."""
        # aria-label locator returns 0 matches
        no_match = MagicMock()
        no_match.count = AsyncMock(return_value=0)

        # Label-based strategy returns an ID
        found_locator = MagicMock()
        found_locator.scroll_into_view_if_needed = AsyncMock()
        found_locator.fill = AsyncMock()

        def locator_fn(sel):
            if "aria-label" in sel:
                return no_match
            return found_locator

        mock_page.locator = MagicMock(side_effect=locator_fn)
        mock_page.evaluate = AsyncMock(return_value="field-123")
        mock_page.wait_for_timeout = AsyncMock()

        handler = NumberFieldHandler(mock_page)
        result = await handler.handle("Storage amount", "100")

        assert result is True
        # fill called twice: once with "" to clear, once with value
        assert found_locator.fill.call_count == 2


# --- TextFieldHandler ---


class TestTextFieldHandler:
    """Tests for TextFieldHandler."""

    @pytest.mark.asyncio
    async def test_fills_text_field_by_label(self, mock_page):
        """Should find and fill a text input by its label."""
        mock_page.evaluate = AsyncMock(return_value="input-42")

        inp_locator = MagicMock()
        inp_locator.fill = AsyncMock()
        mock_page.locator = MagicMock(return_value=inp_locator)

        handler = TextFieldHandler(mock_page)
        result = await handler.handle("Instance name", "web-server")

        assert result is True
        # fill called with "" then with value
        assert inp_locator.fill.call_count == 2

    @pytest.mark.asyncio
    async def test_returns_false_when_no_label_match(self, mock_page):
        """Should return False when evaluate returns None (no label found)."""
        mock_page.evaluate = AsyncMock(return_value=None)

        handler = TextFieldHandler(mock_page)
        result = await handler.handle("Missing label", "value")

        assert result is False


# --- DropdownHandler ---


class TestDropdownHandler:
    """Tests for DropdownHandler (native HTML select)."""

    @pytest.mark.asyncio
    async def test_selects_option_from_native_select(self, mock_page):
        """Should select an option from a native <select> element."""
        select_locator = MagicMock()
        select_locator.count = AsyncMock(return_value=1)

        nth_select = MagicMock()
        nth_select.evaluate = AsyncMock(return_value="Pricing Model")
        nth_select.select_option = AsyncMock()
        select_locator.nth = MagicMock(return_value=nth_select)

        mock_page.locator = MagicMock(return_value=select_locator)

        handler = DropdownHandler(mock_page)
        result = await handler.handle("Pricing Model", "OnDemand")

        assert result is True
        nth_select.select_option.assert_called_once_with(label="OnDemand")

    @pytest.mark.asyncio
    async def test_returns_false_when_no_select_exists(self, mock_page):
        """Should return False when no select elements are on the page."""
        select_locator = MagicMock()
        select_locator.count = AsyncMock(return_value=0)
        mock_page.locator = MagicMock(return_value=select_locator)

        handler = DropdownHandler(mock_page)
        result = await handler.handle("Unknown", "value")

        assert result is False


# --- CloudscapeDropdownHandler ---


class TestCloudscapeDropdownHandler:
    """Tests for CloudscapeDropdownHandler."""

    @pytest.mark.asyncio
    async def test_selects_cloudscape_dropdown_by_label(self, mock_page):
        """Should find button by label, click, and select option."""
        mock_page.evaluate = AsyncMock(return_value="btn-42")

        btn_locator = MagicMock()
        btn_locator.scroll_into_view_if_needed = AsyncMock()
        btn_locator.click = AsyncMock()

        option_locator = MagicMock()
        option_locator.count = AsyncMock(return_value=1)
        option_locator.first = MagicMock()
        option_locator.first.click = AsyncMock()

        def locator_fn(sel):
            if "btn-42" in sel:
                return btn_locator
            return MagicMock(count=AsyncMock(return_value=0))

        mock_page.locator = MagicMock(side_effect=locator_fn)
        mock_page.get_by_role = MagicMock(return_value=option_locator)

        handler = CloudscapeDropdownHandler(mock_page)
        result = await handler.handle("Deployment Option", "Multi-AZ")

        assert result is True
        btn_locator.click.assert_called_once()
        option_locator.first.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_when_no_button_found(self, mock_page):
        """Should return False when no button ID is found for the label."""
        mock_page.evaluate = AsyncMock(return_value=None)

        handler = CloudscapeDropdownHandler(mock_page)
        result = await handler.handle("Unknown Label", "value")

        assert result is False


# --- ChangeDropdownHandler ---


class TestChangeDropdownHandler:
    """Tests for ChangeDropdownHandler."""

    @pytest.mark.asyncio
    async def test_changes_dropdown_by_current_text(self, mock_page):
        """Should find button by current text and select new option."""
        btn_locator = MagicMock()
        btn_locator.count = AsyncMock(return_value=1)

        btn_nth = MagicMock()
        btn_nth.text_content = AsyncMock(return_value="minutes")
        btn_nth.scroll_into_view_if_needed = AsyncMock()
        btn_nth.click = AsyncMock()
        btn_locator.nth = MagicMock(return_value=btn_nth)

        option_locator = MagicMock()
        option_locator.count = AsyncMock(return_value=1)
        option_locator.first = MagicMock()
        option_locator.first.click = AsyncMock()

        mock_page.locator = MagicMock(return_value=btn_locator)
        mock_page.get_by_role = MagicMock(return_value=option_locator)

        handler = ChangeDropdownHandler(mock_page)
        result = await handler.handle("minutes", "hours")

        assert result is True
        option_locator.first.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_when_no_matching_button(self, mock_page):
        """Should return False when no button matches the current text."""
        btn_locator = MagicMock()
        btn_locator.count = AsyncMock(return_value=0)
        mock_page.locator = MagicMock(return_value=btn_locator)

        handler = ChangeDropdownHandler(mock_page)
        result = await handler.handle("nonexistent", "value")

        assert result is False


# --- AutosuggestHandler ---


class TestAutosuggestHandler:
    """Tests for AutosuggestHandler."""

    @pytest.mark.asyncio
    async def test_fills_autosuggest_component(self, mock_page):
        """Should click input, type value, and use keyboard to confirm."""
        inp_locator = MagicMock()
        inp_locator.count = AsyncMock(return_value=1)
        inp_locator.first = MagicMock()
        inp_locator.first.click = AsyncMock()

        mock_page.locator = MagicMock(return_value=inp_locator)

        handler = AutosuggestHandler(mock_page)
        result = await handler.handle("Search instance type", "db.r6g.large")

        assert result is True
        mock_page.keyboard.type.assert_called_once_with("db.r6g.large")
        mock_page.keyboard.press.assert_any_call("ArrowDown")
        mock_page.keyboard.press.assert_any_call("Enter")

    @pytest.mark.asyncio
    async def test_returns_false_when_no_input_found(self, mock_page):
        """Should return False when no input with placeholder exists."""
        inp_locator = MagicMock()
        inp_locator.count = AsyncMock(return_value=0)
        mock_page.locator = MagicMock(return_value=inp_locator)

        handler = AutosuggestHandler(mock_page)
        result = await handler.handle("Missing placeholder", "value")

        assert result is False


# --- RadioHandler ---


class TestRadioHandler:
    """Tests for RadioHandler."""

    @pytest.mark.asyncio
    async def test_clicks_radio_by_text(self, mock_page):
        """Should find radio by text and click it."""
        radio_locator = MagicMock()
        radio_locator.count = AsyncMock(return_value=1)
        radio_locator.first = MagicMock()
        radio_locator.first.click = AsyncMock()

        mock_page.locator = MagicMock(return_value=radio_locator)

        handler = RadioHandler(mock_page)
        result = await handler.handle("_radio", "OnDemand")

        assert result is True
        radio_locator.first.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_when_no_radio_found(self, mock_page):
        """Should return False when no matching text element exists."""
        radio_locator = MagicMock()
        radio_locator.count = AsyncMock(return_value=0)
        mock_page.locator = MagicMock(return_value=radio_locator)

        handler = RadioHandler(mock_page)
        result = await handler.handle("_radio", "Nonexistent")

        assert result is False


# --- PositionalDropdownHandler ---


class TestPositionalDropdownHandler:
    """Tests for PositionalDropdownHandler."""

    @pytest.mark.asyncio
    async def test_selects_nth_dropdown(self, mock_page):
        """Should click the Nth button and select the option."""
        btn_locator = MagicMock()
        btn_locator.count = AsyncMock(return_value=3)
        btn_nth = MagicMock()
        btn_nth.click = AsyncMock()
        btn_locator.nth = MagicMock(return_value=btn_nth)

        option_locator = MagicMock()
        option_locator.count = AsyncMock(return_value=1)
        option_locator.first = MagicMock()
        option_locator.first.click = AsyncMock()

        mock_page.locator = MagicMock(return_value=btn_locator)
        mock_page.get_by_role = MagicMock(return_value=option_locator)

        handler = PositionalDropdownHandler(mock_page)
        result = await handler.handle("_nth_dropdown:2:Pricing", "Reserved")

        assert result is True
        btn_locator.nth.assert_called_with(1)  # 0-indexed
        option_locator.first.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_when_not_enough_buttons(self, mock_page):
        """Should return False if fewer buttons than requested index."""
        btn_locator = MagicMock()
        btn_locator.count = AsyncMock(return_value=0)
        mock_page.locator = MagicMock(return_value=btn_locator)
        mock_page.get_by_role = MagicMock(
            return_value=MagicMock(count=AsyncMock(return_value=0))
        )

        handler = PositionalDropdownHandler(mock_page)
        result = await handler.handle("_nth_dropdown:5:Missing", "value")

        assert result is False


# --- PositionalInputHandler ---


class TestPositionalInputHandler:
    """Tests for PositionalInputHandler."""

    @pytest.mark.asyncio
    async def test_fills_nth_input(self, mock_page):
        """Should fill the Nth input matching the aria-label pattern."""
        inp_locator = MagicMock()
        inp_locator.count = AsyncMock(return_value=3)
        inp_nth = MagicMock()
        inp_nth.fill = AsyncMock()
        inp_locator.nth = MagicMock(return_value=inp_nth)

        mock_page.locator = MagicMock(return_value=inp_locator)

        handler = PositionalInputHandler(mock_page)
        result = await handler.handle("_nth_input:2:Enter Amount", "500")

        assert result is True
        inp_locator.nth.assert_called_with(1)  # 0-indexed
        # fill called twice: clear then set value
        assert inp_nth.fill.call_count == 2

    @pytest.mark.asyncio
    async def test_uses_default_pattern_when_not_specified(self, mock_page):
        """Should use 'Enter Amount' as default aria-label pattern."""
        inp_locator = MagicMock()
        inp_locator.count = AsyncMock(return_value=1)
        inp_nth = MagicMock()
        inp_nth.fill = AsyncMock()
        inp_locator.nth = MagicMock(return_value=inp_nth)

        mock_page.locator = MagicMock(return_value=inp_locator)

        handler = PositionalInputHandler(mock_page)
        # Only index, no pattern after second colon
        result = await handler.handle("_nth_input:1", "100")

        assert result is True
        # Verify the locator was called with "Enter Amount" default
        mock_page.locator.assert_called_with('input[aria-label*="Enter Amount"]')

    @pytest.mark.asyncio
    async def test_returns_false_when_not_enough_inputs(self, mock_page):
        """Should return False if fewer inputs than the requested index."""
        inp_locator = MagicMock()
        inp_locator.count = AsyncMock(return_value=0)
        mock_page.locator = MagicMock(return_value=inp_locator)

        handler = PositionalInputHandler(mock_page)
        result = await handler.handle("_nth_input:3:Enter Amount", "50")

        assert result is False


# --- UnitHandler ---


class TestUnitHandler:
    """Tests for UnitHandler."""

    @pytest.mark.asyncio
    async def test_sets_unit_dropdown(self, mock_page):
        """Should find and click the Unit dropdown, then select option."""
        # evaluate returns True (found the button)
        mock_page.evaluate = AsyncMock(side_effect=[True, None])

        btn_locator = MagicMock()
        btn_locator.click = AsyncMock()

        option_locator = MagicMock()
        option_locator.count = AsyncMock(return_value=1)
        option_locator.first = MagicMock()
        option_locator.first.click = AsyncMock()

        def locator_fn(sel):
            if "data-calc-unit-target" in sel:
                return btn_locator
            if 'role="option"' in sel:
                return option_locator
            return MagicMock(count=AsyncMock(return_value=0))

        mock_page.locator = MagicMock(side_effect=locator_fn)

        handler = UnitHandler(mock_page)
        result = await handler.handle("Storage amount", "GB")

        assert result is True
        btn_locator.click.assert_called_once()
        option_locator.first.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_when_unit_button_not_found(self, mock_page):
        """Should return False when evaluate can't find the Unit button."""
        mock_page.evaluate = AsyncMock(return_value=False)

        handler = UnitHandler(mock_page)
        result = await handler.handle("Missing field", "GB")

        assert result is False
