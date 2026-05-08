"""Tests for RegionSelector.

Verifies keyword extraction logic and region selection with mocked page.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from awslabs.aws_calculator_mcp_server.region import RegionSelector


class TestExtractKeyword:
    """Tests for RegionSelector.extract_keyword static method."""

    def test_extracts_from_parentheses(self):
        """Should extract content inside parentheses."""
        assert RegionSelector.extract_keyword("US East (N. Virginia)") == "N. Virginia"

    def test_extracts_last_parenthesized_part(self):
        """Should extract from the last opening parenthesis."""
        assert RegionSelector.extract_keyword("Asia Pacific (Tokyo)") == "Tokyo"

    def test_handles_no_parentheses(self):
        """Should return the full string if no parentheses."""
        assert RegionSelector.extract_keyword("us-east-1") == "us-east-1"

    def test_south_america(self):
        """Should extract Sao Paulo from South America region."""
        assert RegionSelector.extract_keyword("South America (Sao Paulo)") == "Sao Paulo"

    def test_eu_region(self):
        """Should extract Ireland from EU region."""
        assert RegionSelector.extract_keyword("EU (Ireland)") == "Ireland"

    def test_middle_east(self):
        """Should extract Bahrain from Middle East region."""
        assert RegionSelector.extract_keyword("Middle East (Bahrain)") == "Bahrain"

    def test_empty_string(self):
        """Should handle empty string."""
        assert RegionSelector.extract_keyword("") == ""

    def test_nested_parentheses(self):
        """Should handle edge case of nested parentheses by taking last group."""
        # rstrip(")") strips ALL trailing ")" chars, so "Ohio))" -> "Ohio"
        assert RegionSelector.extract_keyword("AWS (US East (Ohio))") == "Ohio"


@pytest.mark.asyncio
async def test_select_region_returns_false_when_no_region_button(mock_page):
    """Should return False if no Region button found on page."""
    mock_locator = MagicMock()
    mock_locator.count = AsyncMock(return_value=0)
    mock_page.locator = MagicMock(return_value=mock_locator)

    selector = RegionSelector(mock_page)
    result = await selector.select_region("US East (N. Virginia)")
    assert result is False


@pytest.mark.asyncio
async def test_select_region_clicks_option_when_found(mock_page):
    """Should click the matching option when the region is found."""
    # Setup: Region button exists
    region_btn_locator = MagicMock()
    region_btn_locator.count = AsyncMock(return_value=1)

    # The data-region-btn locator
    dropdown_locator = MagicMock()
    dropdown_locator.click = AsyncMock()

    # The option locator
    option_locator = MagicMock()
    option_locator.count = AsyncMock(return_value=1)
    option_locator.first = MagicMock()
    option_locator.first.click = AsyncMock()

    def locator_router(selector):
        if 'has-text("Region")' in selector:
            return region_btn_locator
        if 'data-region-btn' in selector:
            return dropdown_locator
        if 'role="option"' in selector:
            return option_locator
        return MagicMock(count=AsyncMock(return_value=0))

    mock_page.locator = MagicMock(side_effect=locator_router)
    mock_page.evaluate = AsyncMock(side_effect=[True, None])  # btn_found=True, remove attr

    selector = RegionSelector(mock_page)
    result = await selector.select_region("US East (N. Virginia)")

    assert result is True
    option_locator.first.click.assert_called_once()


@pytest.mark.asyncio
async def test_select_region_types_keyword_when_option_not_immediately_visible(mock_page):
    """Should type the keyword to filter when option is not found initially."""
    region_btn_locator = MagicMock()
    region_btn_locator.count = AsyncMock(return_value=1)

    dropdown_locator = MagicMock()
    dropdown_locator.click = AsyncMock()

    # First call: no options, second call (after typing): options found
    call_count = [0]

    option_locator_empty = MagicMock()
    option_locator_empty.count = AsyncMock(return_value=0)

    option_locator_found = MagicMock()
    option_locator_found.count = AsyncMock(return_value=1)
    option_locator_found.first = MagicMock()
    option_locator_found.first.click = AsyncMock()

    def locator_router(selector):
        if 'has-text("Region")' in selector:
            return region_btn_locator
        if 'data-region-btn' in selector:
            return dropdown_locator
        if 'role="option"' in selector:
            call_count[0] += 1
            if call_count[0] <= 1:
                return option_locator_empty
            return option_locator_found
        return MagicMock(count=AsyncMock(return_value=0))

    mock_page.locator = MagicMock(side_effect=locator_router)
    mock_page.evaluate = AsyncMock(side_effect=[True, None])

    selector = RegionSelector(mock_page)
    result = await selector.select_region("Asia Pacific (Tokyo)")

    assert result is True
    mock_page.keyboard.type.assert_called_once_with("Tokyo")


@pytest.mark.asyncio
async def test_select_region_handles_exception_gracefully(mock_page):
    """Should return False on exception without raising."""
    mock_locator = MagicMock()
    mock_locator.count = AsyncMock(return_value=1)
    mock_page.locator = MagicMock(return_value=mock_locator)
    mock_page.evaluate = AsyncMock(side_effect=Exception("JS error"))

    selector = RegionSelector(mock_page)
    result = await selector.select_region("US East (N. Virginia)")
    assert result is False
