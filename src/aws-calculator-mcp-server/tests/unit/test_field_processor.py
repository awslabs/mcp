"""Tests for FieldProcessor dispatch logic.

Verifies that field labels are routed to the correct handlers based on
their prefixes and that the fallback chain is tried in the correct order.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from awslabs.aws_calculator_mcp_server.fields import FieldProcessor


@pytest.fixture
def processor(mock_page):
    """Create a FieldProcessor with a mocked page."""
    return FieldProcessor(mock_page)


@pytest.mark.asyncio
async def test_radio_field_is_skipped(processor):
    """The _radio field label should be treated as already handled (returns True)."""
    result = await processor.process_field("_radio", "OnDemand")
    assert result is True


@pytest.mark.asyncio
async def test_unit_suffix_dispatches_to_unit_handler(processor):
    """Fields ending with _unit should dispatch to UnitHandler."""
    processor._unit_handler.handle = AsyncMock(return_value=True)

    result = await processor.process_field("Storage amount_unit", "GB")
    assert result is True
    processor._unit_handler.handle.assert_called_once_with("Storage amount", "GB")


@pytest.mark.asyncio
async def test_change_prefix_dispatches_to_change_handler(processor):
    """Fields starting with _change: should dispatch to ChangeDropdownHandler."""
    processor._change_dropdown_handler.handle = AsyncMock(return_value=True)

    result = await processor.process_field("_change:minutes", "hours")
    assert result is True
    processor._change_dropdown_handler.handle.assert_called_once_with("minutes", "hours")


@pytest.mark.asyncio
async def test_select_cloudscape_prefix(processor):
    """Fields starting with _select_cloudscape: should dispatch to CloudscapeDropdownHandler."""
    processor._cloudscape_dropdown_handler.handle = AsyncMock(return_value=True)

    result = await processor.process_field("_select_cloudscape:Deployment Option", "Multi-AZ")
    assert result is True
    processor._cloudscape_dropdown_handler.handle.assert_called_once_with(
        "Deployment Option", "Multi-AZ"
    )


@pytest.mark.asyncio
async def test_nth_dropdown_prefix(processor):
    """Fields starting with _nth_dropdown: should dispatch to PositionalDropdownHandler."""
    processor._positional_dropdown_handler.handle = AsyncMock(return_value=True)

    result = await processor.process_field("_nth_dropdown:2:Pricing", "Reserved")
    assert result is True
    processor._positional_dropdown_handler.handle.assert_called_once_with(
        "_nth_dropdown:2:Pricing", "Reserved"
    )


@pytest.mark.asyncio
async def test_nth_input_prefix(processor):
    """Fields starting with _nth_input: should dispatch to PositionalInputHandler."""
    processor._positional_input_handler.handle = AsyncMock(return_value=True)

    result = await processor.process_field("_nth_input:1:Enter Amount", "100")
    assert result is True
    processor._positional_input_handler.handle.assert_called_once_with(
        "_nth_input:1:Enter Amount", "100"
    )


@pytest.mark.asyncio
async def test_autosuggest_prefix(processor):
    """Fields starting with _autosuggest: should dispatch to AutosuggestHandler."""
    processor._autosuggest_handler.handle = AsyncMock(return_value=True)

    result = await processor.process_field("_autosuggest:Search instance type", "db.r6g.large")
    assert result is True
    processor._autosuggest_handler.handle.assert_called_once_with(
        "Search instance type", "db.r6g.large"
    )


@pytest.mark.asyncio
async def test_fallback_chain_tries_number_first(processor):
    """Generic fields should try NumberFieldHandler first."""
    processor._number_handler.handle = AsyncMock(return_value=True)
    processor._text_handler.handle = AsyncMock(return_value=False)

    result = await processor.process_field("Number of tasks", "5")
    assert result is True
    processor._number_handler.handle.assert_called_once_with("Number of tasks", "5")
    processor._text_handler.handle.assert_not_called()


@pytest.mark.asyncio
async def test_fallback_chain_tries_text_when_number_fails(processor):
    """If NumberFieldHandler fails, TextFieldHandler should be tried next."""
    processor._number_handler.handle = AsyncMock(return_value=False)
    processor._text_handler.handle = AsyncMock(return_value=True)

    result = await processor.process_field("Instance name", "web-server")
    assert result is True
    processor._number_handler.handle.assert_called_once()
    processor._text_handler.handle.assert_called_once_with("Instance name", "web-server")


@pytest.mark.asyncio
async def test_fallback_chain_tries_dropdown_when_text_fails(processor):
    """If TextFieldHandler fails, DropdownHandler should be tried next."""
    processor._number_handler.handle = AsyncMock(return_value=False)
    processor._text_handler.handle = AsyncMock(return_value=False)
    processor._dropdown_handler.handle = AsyncMock(return_value=True)

    result = await processor.process_field("Pricing Model", "OnDemand")
    assert result is True
    processor._dropdown_handler.handle.assert_called_once_with("Pricing Model", "OnDemand")


@pytest.mark.asyncio
async def test_fallback_chain_tries_cloudscape_last(processor):
    """If all others fail, CloudscapeDropdownHandler is the last in the chain."""
    processor._number_handler.handle = AsyncMock(return_value=False)
    processor._text_handler.handle = AsyncMock(return_value=False)
    processor._dropdown_handler.handle = AsyncMock(return_value=False)
    processor._cloudscape_dropdown_handler.handle = AsyncMock(return_value=True)

    result = await processor.process_field("Payment option", "All Upfront")
    assert result is True
    processor._cloudscape_dropdown_handler.handle.assert_called_once_with(
        "Payment option", "All Upfront"
    )


@pytest.mark.asyncio
async def test_fallback_chain_exhausted_returns_false(processor):
    """If all handlers fail and value is long, returns False."""
    processor._number_handler.handle = AsyncMock(return_value=False)
    processor._text_handler.handle = AsyncMock(return_value=False)
    processor._dropdown_handler.handle = AsyncMock(return_value=False)
    processor._cloudscape_dropdown_handler.handle = AsyncMock(return_value=False)

    result = await processor.process_field("Unknown field", "some long value")
    assert result is False


@pytest.mark.asyncio
async def test_short_value_tries_change_dropdown_as_last_resort(processor):
    """For short values (<=2 chars), ChangeDropdownHandler is tried as last resort."""
    processor._number_handler.handle = AsyncMock(return_value=False)
    processor._text_handler.handle = AsyncMock(return_value=False)
    processor._dropdown_handler.handle = AsyncMock(return_value=False)
    processor._cloudscape_dropdown_handler.handle = AsyncMock(return_value=False)
    processor._change_dropdown_handler.handle = AsyncMock(return_value=True)

    result = await processor.process_field("GB", "TB")
    assert result is True
    processor._change_dropdown_handler.handle.assert_called_once_with("GB", "TB")


@pytest.mark.asyncio
async def test_process_radio(processor):
    """process_radio should delegate to RadioHandler."""
    processor._radio_handler.handle = AsyncMock(return_value=True)

    result = await processor.process_radio("OnDemand")
    assert result is True
    processor._radio_handler.handle.assert_called_once_with("_radio", "OnDemand")
