"""Tests for AWSCalculatorAutomation BDD compatibility methods.

Covers the property accessors and BDD step definition delegates.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from awslabs.aws_calculator_mcp_server.calculator import AWSCalculatorAutomation


@pytest.fixture
def automation_with_page():
    """Create automation with a mocked browser manager and page."""
    auto = AWSCalculatorAutomation(headless=True)
    mock_page = MagicMock()
    mock_page.evaluate = AsyncMock(return_value=None)
    mock_page.wait_for_timeout = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.keyboard = MagicMock()
    mock_page.keyboard.type = AsyncMock()
    mock_page.keyboard.press = AsyncMock()

    auto._browser_manager = MagicMock()
    auto._browser_manager.page = mock_page
    auto._browser_manager._browser = MagicMock()
    auto._browser_manager.ensure_browser = AsyncMock(return_value=mock_page)
    auto._browser_manager.close = AsyncMock()

    return auto


class TestPageProperty:
    """Tests for _page compatibility property."""

    def test_returns_page_from_browser_manager(self, automation_with_page):
        """Should return page from browser manager."""
        result = automation_with_page._page
        assert result is automation_with_page._browser_manager.page


class TestBrowserProperty:
    """Tests for _browser compatibility property."""

    def test_returns_browser_from_browser_manager(self, automation_with_page):
        """Should return browser from browser manager."""
        result = automation_with_page._browser
        assert result is automation_with_page._browser_manager._browser


class TestDismissCookiesCompat:
    """Tests for _dismiss_cookies compatibility method."""

    @pytest.mark.asyncio
    async def test_delegates_to_navigation_helper(self, automation_with_page):
        """Should create NavigationHelper and call dismiss_cookies."""
        with patch(
            "awslabs.aws_calculator_mcp_server.calculator.NavigationHelper"
        ) as MockNav:
            MockNav.return_value.dismiss_cookies = AsyncMock()
            await automation_with_page._dismiss_cookies()
            MockNav.return_value.dismiss_cookies.assert_called_once()


class TestExpandAllSectionsCompat:
    """Tests for _expand_all_sections compatibility method."""

    @pytest.mark.asyncio
    async def test_delegates_to_navigation_helper(self, automation_with_page):
        """Should create NavigationHelper and call expand_all_sections."""
        with patch(
            "awslabs.aws_calculator_mcp_server.calculator.NavigationHelper"
        ) as MockNav:
            MockNav.return_value.expand_all_sections = AsyncMock()
            await automation_with_page._expand_all_sections()
            MockNav.return_value.expand_all_sections.assert_called_once()


class TestSelectRegionCompat:
    """Tests for _select_region compatibility method."""

    @pytest.mark.asyncio
    async def test_delegates_to_region_selector(self, automation_with_page):
        """Should create RegionSelector and call select_region."""
        with patch(
            "awslabs.aws_calculator_mcp_server.calculator.RegionSelector"
        ) as MockRegion:
            MockRegion.return_value.select_region = AsyncMock(return_value=True)
            result = await automation_with_page._select_region("US East (N. Virginia)")
            MockRegion.return_value.select_region.assert_called_once_with(
                "US East (N. Virginia)"
            )
            assert result is True


class TestFillNumberFieldCompat:
    """Tests for _fill_number_field compatibility method."""

    @pytest.mark.asyncio
    async def test_delegates_to_number_handler(self, automation_with_page):
        """Should create NumberFieldHandler and call handle."""
        with patch(
            "awslabs.aws_calculator_mcp_server.calculator.NumberFieldHandler",
            create=True,
        ) as MockHandler:
            MockHandler.return_value.handle = AsyncMock(return_value=True)

            # Import directly since it uses a local import
            page = automation_with_page._browser_manager.page
            from awslabs.aws_calculator_mcp_server.fields.input_handler import NumberFieldHandler

            with patch.object(NumberFieldHandler, "handle", new_callable=AsyncMock) as mock_handle:
                mock_handle.return_value = True
                # Call through the actual method - it does a local import
                result = await automation_with_page._fill_number_field("Storage", "100")
                assert result is True


class TestFillTextFieldCompat:
    """Tests for _fill_text_field compatibility method."""

    @pytest.mark.asyncio
    async def test_delegates_to_text_handler(self, automation_with_page):
        """Should create TextFieldHandler and call handle."""
        from awslabs.aws_calculator_mcp_server.fields.input_handler import TextFieldHandler

        with patch.object(TextFieldHandler, "handle", new_callable=AsyncMock) as mock_handle:
            mock_handle.return_value = True
            result = await automation_with_page._fill_text_field("Name", "test")
            assert result is True


class TestSelectCloudscapeDropdownCompat:
    """Tests for _select_cloudscape_dropdown compatibility method."""

    @pytest.mark.asyncio
    async def test_delegates_to_cloudscape_handler(self, automation_with_page):
        """Should create CloudscapeDropdownHandler and call handle."""
        from awslabs.aws_calculator_mcp_server.fields.dropdown_handler import CloudscapeDropdownHandler

        with patch.object(
            CloudscapeDropdownHandler, "handle", new_callable=AsyncMock
        ) as mock_handle:
            mock_handle.return_value = True
            result = await automation_with_page._select_cloudscape_dropdown("Deploy", "Multi-AZ")
            assert result is True


class TestFillAutosuggestCompat:
    """Tests for _fill_autosuggest compatibility method."""

    @pytest.mark.asyncio
    async def test_delegates_to_autosuggest_handler(self, automation_with_page):
        """Should create AutosuggestHandler and call handle."""
        from awslabs.aws_calculator_mcp_server.fields.autosuggest_handler import AutosuggestHandler

        with patch.object(AutosuggestHandler, "handle", new_callable=AsyncMock) as mock_handle:
            mock_handle.return_value = True
            result = await automation_with_page._fill_autosuggest("Search", "db.r6g.large")
            assert result is True


class TestClickRadioCompat:
    """Tests for _click_radio compatibility method."""

    @pytest.mark.asyncio
    async def test_delegates_to_radio_handler(self, automation_with_page):
        """Should create RadioHandler and call handle."""
        from awslabs.aws_calculator_mcp_server.fields.radio_handler import RadioHandler

        with patch.object(RadioHandler, "handle", new_callable=AsyncMock) as mock_handle:
            mock_handle.return_value = True
            result = await automation_with_page._click_radio("OnDemand")
            assert result is True


class TestSaveServiceCompat:
    """Tests for _save_service compatibility method."""

    @pytest.mark.asyncio
    async def test_delegates_to_estimate_manager(self, automation_with_page):
        """Should create EstimateManager and call save_service."""
        with patch(
            "awslabs.aws_calculator_mcp_server.calculator.EstimateManager"
        ) as MockEstimate:
            MockEstimate.return_value.save_service = AsyncMock()
            await automation_with_page._save_service()
            MockEstimate.return_value.save_service.assert_called_once()


class TestGetShareLinkCompat:
    """Tests for _get_share_link compatibility method."""

    @pytest.mark.asyncio
    async def test_delegates_to_estimate_manager(self, automation_with_page):
        """Should create EstimateManager and call get_share_link."""
        with patch(
            "awslabs.aws_calculator_mcp_server.calculator.EstimateManager"
        ) as MockEstimate:
            MockEstimate.return_value.get_share_link = AsyncMock(
                return_value="https://calculator.aws/#/estimate?id=abc"
            )
            result = await automation_with_page._get_share_link()
            assert result == "https://calculator.aws/#/estimate?id=abc"
