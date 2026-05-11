"""Tests for CostReader polling logic.

Verifies that cost reading correctly parses different patterns and
handles polling (multiple attempts) with mocked page.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from awslabs.aws_calculator_mcp_server.cost import CostReader


@pytest.fixture
def cost_reader(mock_page):
    """Create a CostReader with a mocked page."""
    return CostReader(mock_page)


def _make_body_locator(text_content_value):
    """Helper to create a mock locator with count and text_content for cost tests."""
    locator = MagicMock()
    locator.count = AsyncMock(return_value=0)
    locator.text_content = AsyncMock(return_value=text_content_value)
    locator.first = MagicMock()
    locator.first.text_content = AsyncMock(return_value=text_content_value)
    return locator


def _make_body_locator_side_effect(side_effects):
    """Helper to create a mock locator with side_effect text_content."""
    locator = MagicMock()
    locator.count = AsyncMock(return_value=0)
    locator.text_content = AsyncMock(side_effect=side_effects)
    locator.first = MagicMock()
    locator.first.text_content = AsyncMock(side_effect=side_effects)
    return locator


@pytest.mark.asyncio
async def test_get_current_cost_finds_total_monthly_cost(mock_page):
    """Should parse 'Total Monthly cost: 12.50 USD' pattern."""
    body_locator = _make_body_locator(
        "Some text Total Monthly cost: 12.50 USD more text"
    )
    mock_page.locator = MagicMock(return_value=body_locator)

    reader = CostReader(mock_page)
    result = await reader.get_current_cost(max_attempts=1)
    assert result == "12.50"


@pytest.mark.asyncio
async def test_get_current_cost_finds_estimated_monthly(mock_page):
    """Should parse 'Estimated monthly cost 250.00 USD' pattern."""
    body_locator = _make_body_locator("Estimated monthly cost 250.00 USD")
    mock_page.locator = MagicMock(return_value=body_locator)

    reader = CostReader(mock_page)
    result = await reader.get_current_cost(max_attempts=1)
    assert result == "250.00"


@pytest.mark.asyncio
async def test_get_current_cost_finds_dollar_sign_pattern(mock_page):
    """Should parse 'monthly cost: $1,234.56 USD' pattern."""
    body_locator = _make_body_locator("monthly cost: $1,234.56 USD")
    mock_page.locator = MagicMock(return_value=body_locator)

    reader = CostReader(mock_page)
    result = await reader.get_current_cost(max_attempts=1)
    assert result == "1,234.56"


@pytest.mark.asyncio
async def test_get_current_cost_returns_zero_when_no_match(mock_page):
    """Should return '0.00' when no cost pattern matches."""
    body_locator = _make_body_locator("No cost info here")
    mock_page.locator = MagicMock(return_value=body_locator)

    reader = CostReader(mock_page)
    result = await reader.get_current_cost(max_attempts=2)
    assert result == "0.00"


@pytest.mark.asyncio
async def test_get_current_cost_skips_zero_values(mock_page):
    """Should skip matches where cost is 0.00 and continue polling."""
    body_locator = _make_body_locator_side_effect([
        "Total Monthly cost: 0.00 USD",
        "Total Monthly cost: 0.00 USD",
        "Total Monthly cost: 45.67 USD",
        "Total Monthly cost: 45.67 USD",
    ])
    mock_page.locator = MagicMock(return_value=body_locator)

    reader = CostReader(mock_page)
    result = await reader.get_current_cost(max_attempts=3)
    assert result == "45.67"


@pytest.mark.asyncio
async def test_get_current_cost_handles_exception(mock_page):
    """Should handle exceptions gracefully and continue polling."""
    body_locator = _make_body_locator_side_effect([
        Exception("network error"),
        Exception("network error"),
        "Total Monthly cost: 99.99 USD",
        "Total Monthly cost: 99.99 USD",
    ])
    mock_page.locator = MagicMock(return_value=body_locator)

    reader = CostReader(mock_page)
    result = await reader.get_current_cost(max_attempts=3)
    assert result == "99.99"


@pytest.mark.asyncio
async def test_get_total_cost_returns_formatted(mock_page):
    """Should return '$X USD/month' format for estimate page."""
    body_locator = MagicMock()
    body_locator.text_content = AsyncMock(
        return_value="Total monthly cost: 1,500.00 USD"
    )
    mock_page.locator = MagicMock(return_value=body_locator)

    reader = CostReader(mock_page)
    result = await reader.get_total_cost(max_attempts=1)
    assert result == "$1,500.00 USD/month"


@pytest.mark.asyncio
async def test_get_total_cost_returns_unknown_when_no_cost(mock_page):
    """Should return 'Unknown' if no cost found after all attempts."""
    body_locator = MagicMock()
    body_locator.text_content = AsyncMock(return_value="Loading...")
    mock_page.locator = MagicMock(return_value=body_locator)

    reader = CostReader(mock_page)
    result = await reader.get_total_cost(max_attempts=2)
    assert result == "Unknown"


@pytest.mark.asyncio
async def test_get_total_cost_finds_monthly_cost_pattern(mock_page):
    """Should parse 'Monthly cost 89.00 USD' pattern."""
    body_locator = MagicMock()
    body_locator.text_content = AsyncMock(return_value="Monthly cost 89.00 USD")
    mock_page.locator = MagicMock(return_value=body_locator)

    reader = CostReader(mock_page)
    result = await reader.get_total_cost(max_attempts=1)
    assert result == "$89.00 USD/month"


@pytest.mark.asyncio
async def test_get_total_cost_skips_zero(mock_page):
    """Should skip zero cost values and keep polling."""
    body_locator = MagicMock()
    body_locator.text_content = AsyncMock(
        side_effect=[
            "Total monthly cost: 0.00 USD",
            "Total monthly cost: 200.00 USD",
        ]
    )
    mock_page.locator = MagicMock(return_value=body_locator)

    reader = CostReader(mock_page)
    result = await reader.get_total_cost(max_attempts=3)
    assert result == "$200.00 USD/month"
