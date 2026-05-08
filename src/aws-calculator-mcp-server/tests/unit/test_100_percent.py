"""Tests to reach 100% unit coverage — covers remaining edge cases."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest_asyncio


@pytest.fixture
def mock_page():
    page = AsyncMock()
    page.locator.return_value = AsyncMock()
    page.locator.return_value.count = AsyncMock(return_value=0)
    page.locator.return_value.first = AsyncMock()
    page.evaluate = AsyncMock(return_value=None)
    page.wait_for_timeout = AsyncMock()
    page.keyboard = AsyncMock()
    return page


# --- calculator.py line 176: radio text NOT in page body ---

@pytest.mark.asyncio
async def test_configure_service_radio_not_in_body(mock_page):
    """Test _configure_service when radio text is not found in page body."""
    from awslabs.aws_calculator_mcp_server.calculator import AWSCalculatorAutomation

    calc = AWSCalculatorAutomation.__new__(AWSCalculatorAutomation)
    calc._browser_manager = MagicMock()
    calc._browser_manager.page = mock_page

    # Mock navigation to succeed
    with patch("awslabs.aws_calculator_mcp_server.calculator.NavigationHelper") as MockNav, \
         patch("awslabs.aws_calculator_mcp_server.calculator.RegionSelector") as MockRegion, \
         patch("awslabs.aws_calculator_mcp_server.calculator.FieldProcessor") as MockFP, \
         patch("awslabs.aws_calculator_mcp_server.calculator.CostReader") as MockCost, \
         patch("awslabs.aws_calculator_mcp_server.calculator.EstimateManager") as MockEM:

        nav = MockNav.return_value
        nav.search_and_configure = AsyncMock(return_value=True)
        nav.dismiss_cookies = AsyncMock()

        region_sel = MockRegion.return_value
        region_sel.select_region = AsyncMock()

        fp = MockFP.return_value
        fp.process_radio = AsyncMock()
        fp.process_field = AsyncMock()

        cost = MockCost.return_value
        cost.get_current_cost = AsyncMock(return_value="10.00")

        em = MockEM.return_value
        em.save_service = AsyncMock()

        # main content does NOT contain the radio text
        main_locator = AsyncMock()
        main_locator.text_content = AsyncMock(return_value="Some other content")
        desc_locator = AsyncMock()
        desc_locator.count = AsyncMock(return_value=1)
        desc_locator.first = AsyncMock()
        desc_locator.first.click = AsyncMock()

        def page_locator(sel):
            if "main" in sel:
                return main_locator
            return desc_locator

        mock_page.locator = MagicMock(side_effect=page_locator)

        result = await calc._configure_service(
            "TestService",
            {"_radio": "NonexistentRadio", "SomeField": "10"},
            "US East (N. Virginia)",
            nav,
        )
        assert result["status"] == "added"


# --- cost.py lines 84-85: exception in get_total_cost ---

@pytest.mark.asyncio
async def test_cost_reader_get_total_cost_exception(mock_page):
    """Test get_total_cost when page.locator raises exception."""
    from awslabs.aws_calculator_mcp_server.cost import CostReader

    mock_page.locator.side_effect = Exception("page crashed")
    mock_page.wait_for_timeout = AsyncMock()

    reader = CostReader(mock_page)
    result = await reader.get_total_cost()
    assert result == "Unknown"


# --- fields/__init__.py line 44: FieldProcessor init ---

def test_field_processor_stores_page(mock_page):
    """Test that FieldProcessor stores the page reference."""
    from awslabs.aws_calculator_mcp_server.fields import FieldProcessor
    fp = FieldProcessor(mock_page)
    assert fp._page is mock_page


# --- autosuggest_handler.py lines 56-58: exception path ---

@pytest.mark.asyncio
async def test_autosuggest_handler_exception(mock_page):
    """Test AutosuggestHandler when an exception occurs."""
    from awslabs.aws_calculator_mcp_server.fields.autosuggest_handler import AutosuggestHandler

    mock_page.locator.side_effect = Exception("DOM error")
    handler = AutosuggestHandler(mock_page)
    result = await handler.handle("placeholder", "value")
    assert result is False


# --- input_handler.py lines 118-119: exception in JS force visibility ---

@pytest.mark.asyncio
async def test_number_field_handler_js_exception(mock_page):
    """Test NumberFieldHandler when JS force visibility raises."""
    from awslabs.aws_calculator_mcp_server.fields.input_handler import NumberFieldHandler

    # Locator that finds element but all fill attempts fail
    locator = AsyncMock()
    locator.count = AsyncMock(return_value=1)
    locator.first = AsyncMock()
    locator.first.fill = AsyncMock(side_effect=Exception("not interactable"))
    locator.first.scroll_into_view_if_needed = AsyncMock(side_effect=Exception("no scroll"))
    locator.first.get_attribute = AsyncMock(return_value="test-id")
    mock_page.locator.return_value = locator
    mock_page.evaluate = AsyncMock(side_effect=[None, Exception("JS error")])

    handler = NumberFieldHandler(mock_page)
    result = await handler.handle("SomeField", "42")
    # Should not crash, returns False after exhausting strategies
    assert result is False


# --- radio_handler.py lines 45-46: exception path ---

@pytest.mark.asyncio
async def test_radio_handler_exception(mock_page):
    """Test RadioHandler when locator throws."""
    from awslabs.aws_calculator_mcp_server.fields.radio_handler import RadioHandler

    mock_page.locator.side_effect = Exception("radio broken")
    handler = RadioHandler(mock_page)
    result = await handler.handle("_radio", "SomeOption")
    assert result is False


# --- region.py lines 98-103: fallback to nth(1) button ---

@pytest.mark.asyncio
async def test_region_selector_fallback_nth1(mock_page):
    """Test RegionSelector fallback when no data-region-btn found."""
    from awslabs.aws_calculator_mcp_server.region import RegionSelector

    # region button locator returns count > 0
    region_btn_locator = AsyncMock()
    region_btn_locator.count = AsyncMock(return_value=1)

    # evaluate returns False (no btn_found)
    mock_page.evaluate = AsyncMock(return_value=False)

    # all_btns has >=2 elements
    all_btns = AsyncMock()
    all_btns.count = AsyncMock(return_value=3)
    all_btns.nth = MagicMock(return_value=AsyncMock())
    all_btns.nth.return_value.click = AsyncMock()

    # option found
    option_locator = AsyncMock()
    option_locator.count = AsyncMock(return_value=1)
    option_locator.first = AsyncMock()
    option_locator.first.click = AsyncMock()

    def locator_side_effect(selector):
        if "Region" in selector:
            return region_btn_locator
        elif "option" in selector:
            return option_locator
        else:
            return all_btns

    mock_page.locator = MagicMock(side_effect=locator_side_effect)
    mock_page.wait_for_timeout = AsyncMock()

    selector = RegionSelector(mock_page)
    result = await selector.select_region("Asia Pacific (Tokyo)")
    assert result is True


# --- region.py line 103: fallback returns False when < 2 buttons ---

@pytest.mark.asyncio
async def test_region_selector_fallback_no_buttons(mock_page):
    """Test RegionSelector returns False when fewer than 2 buttons."""
    from awslabs.aws_calculator_mcp_server.region import RegionSelector

    region_btn_locator = AsyncMock()
    region_btn_locator.count = AsyncMock(return_value=1)

    mock_page.evaluate = AsyncMock(return_value=False)

    all_btns = AsyncMock()
    all_btns.count = AsyncMock(return_value=1)  # Less than 2!

    def locator_side_effect(selector):
        if "Region" in selector:
            return region_btn_locator
        return all_btns

    mock_page.locator = MagicMock(side_effect=locator_side_effect)
    mock_page.wait_for_timeout = AsyncMock()

    selector = RegionSelector(mock_page)
    result = await selector.select_region("EU (Frankfurt)")
    assert result is False


# --- region.py line 125: Escape when option not found ---

@pytest.mark.asyncio
async def test_region_selector_escape_no_option(mock_page):
    """Test RegionSelector presses Escape when region not found."""
    from awslabs.aws_calculator_mcp_server.region import RegionSelector

    region_btn_locator = AsyncMock()
    region_btn_locator.count = AsyncMock(return_value=1)

    # evaluate finds the btn, then cleanup
    mock_page.evaluate = AsyncMock(side_effect=[True, None])

    # dropdown click works
    dropdown = AsyncMock()
    dropdown.click = AsyncMock()

    # option NOT found (count=0 both times - before and after type)
    option_locator = AsyncMock()
    option_locator.count = AsyncMock(return_value=0)
    option_locator.first = AsyncMock()

    def locator_side_effect(selector):
        if 'button:has-text("Region")' in selector:
            return region_btn_locator
        elif "data-region-btn" in selector:
            return dropdown
        else:
            return option_locator

    mock_page.locator = MagicMock(side_effect=locator_side_effect)
    mock_page.wait_for_timeout = AsyncMock()
    mock_page.keyboard = AsyncMock()
    mock_page.keyboard.type = AsyncMock()
    mock_page.keyboard.press = AsyncMock()

    selector = RegionSelector(mock_page)
    result = await selector.select_region("NonExistent (Region)")
    assert result is False
    mock_page.keyboard.press.assert_called_with("Escape")


# --- server.py lines 176-177: output_file in update_estimate ---

@pytest.mark.asyncio
async def test_update_estimate_with_output_file():
    """Test update_estimate saves JSON when output_file provided."""
    import tempfile, os, json
    from awslabs.aws_calculator_mcp_server.server import update_estimate, _get_calculator

    with patch("awslabs.aws_calculator_mcp_server.server._get_calculator") as mock_get:
        mock_calc = AsyncMock()
        mock_calc.update_estimate = AsyncMock(return_value={
            "estimate_url": "https://calculator.aws/#/test",
            "monthly_cost": "$100.00 USD/month",
            "services_added": [],
            "services_removed": [],
        })
        mock_calc.close = AsyncMock()
        mock_get.return_value = mock_calc

        ctx = AsyncMock()

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name

        try:
            result = await update_estimate(
                ctx=ctx,
                estimate_url="https://calculator.aws/#/test",
                output_file=tmp_path,
            )
            assert os.path.exists(tmp_path)
            with open(tmp_path) as f:
                data = json.load(f)
            assert "generated_at" in data
            assert data["estimate_url"] == "https://calculator.aws/#/test"
        finally:
            os.unlink(tmp_path)


# --- server.py line 211, 215: main() entry point ---

def test_server_main_entrypoint():
    """Test that main() calls mcp.run."""
    from awslabs.aws_calculator_mcp_server import server
    with patch.object(server.mcp, "run") as mock_run:
        server.main()
        mock_run.assert_called_once_with(transport="stdio")
