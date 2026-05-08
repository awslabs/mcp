"""Extended tests for NumberFieldHandler and TextFieldHandler fallback strategies.

Tests the scroll, expand sections, JS setter, and exception fallback paths
that aren't covered by the basic tests in test_handlers.py.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from awslabs.aws_calculator_mcp_server.fields.input_handler import (
    NumberFieldHandler,
    TextFieldHandler,
)


class TestNumberFieldHandlerScrollFallback:
    """Tests for NumberFieldHandler scroll-into-view fallback."""

    @pytest.mark.asyncio
    async def test_scroll_into_view_fallback_succeeds(self, mock_page):
        """Should scroll into view and fill when direct fill fails."""
        inp_locator = MagicMock()
        inp_locator.count = AsyncMock(return_value=1)
        inp_locator.first = MagicMock()
        # Direct fill fails
        inp_locator.first.fill = AsyncMock(
            side_effect=[Exception("not visible"), None, None]
        )
        inp_locator.first.scroll_into_view_if_needed = AsyncMock()

        mock_page.locator = MagicMock(return_value=inp_locator)
        mock_page.wait_for_timeout = AsyncMock()

        handler = NumberFieldHandler(mock_page)
        result = await handler.handle("Storage amount", "100")

        assert result is True
        inp_locator.first.scroll_into_view_if_needed.assert_called()


class TestNumberFieldHandlerExpandFallback:
    """Tests for NumberFieldHandler expand sections fallback."""

    @pytest.mark.asyncio
    async def test_expand_sections_fallback_succeeds(self, mock_page):
        """Should expand sections and then fill when direct fill and scroll+fill fail."""
        inp_locator = MagicMock()
        inp_locator.count = AsyncMock(return_value=1)
        inp_locator.first = MagicMock()

        # Flow:
        # 1. Direct fill (line 65): fails (fill_calls=1)
        # 2. scroll (line 74): fails -> except on line 79
        # 3. expand + scroll (line 86): succeeds
        # 4. fill (line 88): succeeds (fill_calls=2)
        fill_calls = [0]

        async def fill_side_effect(value, **kwargs):
            fill_calls[0] += 1
            if fill_calls[0] <= 1:
                raise Exception("not visible")
            return None

        inp_locator.first.fill = AsyncMock(side_effect=fill_side_effect)
        # scroll: first call fails (line 74), second call succeeds (line 86)
        scroll_calls = [0]

        async def scroll_side_effect(**kwargs):
            scroll_calls[0] += 1
            if scroll_calls[0] <= 1:
                raise Exception("can't scroll")
            return None

        inp_locator.first.scroll_into_view_if_needed = AsyncMock(side_effect=scroll_side_effect)
        inp_locator.first.get_attribute = AsyncMock(return_value=None)

        mock_page.locator = MagicMock(return_value=inp_locator)
        mock_page.wait_for_timeout = AsyncMock()
        # expand_all_sections evaluates: returns 0 (no sections to expand, breaks)
        mock_page.evaluate = AsyncMock(return_value=0)

        handler = NumberFieldHandler(mock_page)
        result = await handler.handle("Data amount", "50")

        assert result is True


class TestNumberFieldHandlerJSForceFallback:
    """Tests for NumberFieldHandler JS force-visibility fallback."""

    @pytest.mark.asyncio
    async def test_js_force_visibility_fallback(self, mock_page):
        """Should use JS to force visibility when all other strategies fail."""
        inp_locator = MagicMock()
        inp_locator.count = AsyncMock(return_value=1)
        inp_locator.first = MagicMock()

        # Flow: direct fill fails (call 1), scroll always fails so no more fill
        # until JS force visibility, then fill succeeds (call 2)
        fill_calls = [0]

        async def fill_side_effect(value, **kwargs):
            fill_calls[0] += 1
            if fill_calls[0] <= 1:
                raise Exception("still not visible")
            return None

        inp_locator.first.fill = AsyncMock(side_effect=fill_side_effect)
        # scroll always fails so we skip scroll+fill and expand+scroll+fill paths
        inp_locator.first.scroll_into_view_if_needed = AsyncMock(
            side_effect=Exception("can't scroll")
        )
        inp_locator.first.get_attribute = AsyncMock(return_value="field-abc-123")

        mock_page.locator = MagicMock(return_value=inp_locator)
        mock_page.wait_for_timeout = AsyncMock()
        # evaluate calls:
        # 1. _expand_all_sections -> returns 0 (breaks loop)
        # 2. force-visibility JS -> returns None
        mock_page.evaluate = AsyncMock(side_effect=[0, None])

        handler = NumberFieldHandler(mock_page)
        result = await handler.handle("Hidden field", "25")

        assert result is True
        calls = mock_page.evaluate.call_args_list
        assert len(calls) >= 2

    @pytest.mark.asyncio
    async def test_js_force_fallback_skipped_when_no_id(self, mock_page):
        """Should skip JS force fallback when input has no ID, and fall to strategy 2."""
        inp_locator = MagicMock()
        inp_locator.count = AsyncMock(return_value=1)
        inp_locator.first = MagicMock()

        # All fills fail
        inp_locator.first.fill = AsyncMock(side_effect=Exception("not visible"))
        inp_locator.first.scroll_into_view_if_needed = AsyncMock(
            side_effect=Exception("can't scroll")
        )
        inp_locator.first.get_attribute = AsyncMock(return_value=None)

        # Strategy 2: find by label - returns a field ID
        label_locator = MagicMock()
        label_locator.scroll_into_view_if_needed = AsyncMock()
        label_locator.fill = AsyncMock()

        call_count = [0]

        def locator_fn(sel):
            call_count[0] += 1
            if "aria-label" in sel:
                return inp_locator
            return label_locator

        mock_page.locator = MagicMock(side_effect=locator_fn)
        mock_page.wait_for_timeout = AsyncMock()
        # evaluate calls: expand sections (0), strategy 2 label search (returns field ID)
        mock_page.evaluate = AsyncMock(side_effect=[0, "field-xyz"])

        handler = NumberFieldHandler(mock_page)
        result = await handler.handle("Some field", "10")

        assert result is True
        # label_locator should be filled via strategy 2
        assert label_locator.fill.call_count == 2  # clear + value


class TestNumberFieldHandlerAllFail:
    """Tests for NumberFieldHandler when all strategies fail."""

    @pytest.mark.asyncio
    async def test_returns_false_when_all_strategies_fail(self, mock_page):
        """Should return False when both strategies fail completely."""
        inp_locator = MagicMock()
        inp_locator.count = AsyncMock(return_value=0)

        mock_page.locator = MagicMock(return_value=inp_locator)
        mock_page.wait_for_timeout = AsyncMock()
        # Strategy 2: no label match
        mock_page.evaluate = AsyncMock(return_value=None)

        handler = NumberFieldHandler(mock_page)
        result = await handler.handle("Nonexistent", "0")

        assert result is False

    @pytest.mark.asyncio
    async def test_handles_top_level_exception(self, mock_page):
        """Should return False when an unexpected exception occurs."""
        mock_page.locator = MagicMock(side_effect=Exception("Unexpected error"))
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=None)

        handler = NumberFieldHandler(mock_page)
        result = await handler.handle("Field", "5")

        assert result is False


class TestNumberFieldHandlerExpandSections:
    """Tests for _expand_all_sections internal method."""

    @pytest.mark.asyncio
    async def test_expand_iterates_until_zero(self, mock_page):
        """Should call evaluate up to 3 times or until 0."""
        mock_page.evaluate = AsyncMock(side_effect=[2, 1, 0])
        mock_page.wait_for_timeout = AsyncMock()

        handler = NumberFieldHandler(mock_page)
        await handler._expand_all_sections()

        assert mock_page.evaluate.call_count == 3

    @pytest.mark.asyncio
    async def test_expand_breaks_on_exception(self, mock_page):
        """Should break on exception during expansion."""
        mock_page.evaluate = AsyncMock(side_effect=Exception("DOM error"))

        handler = NumberFieldHandler(mock_page)
        await handler._expand_all_sections()

        assert mock_page.evaluate.call_count == 1


class TestTextFieldHandlerExtended:
    """Extended tests for TextFieldHandler."""

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(self, mock_page):
        """Should return False on exception without raising."""
        mock_page.evaluate = AsyncMock(side_effect=Exception("JS error"))

        handler = TextFieldHandler(mock_page)
        result = await handler.handle("Bad Field", "value")

        assert result is False
