"""Radio button handler for AWS Calculator.

Handles clicking radio buttons/tiles by their label text.
"""

from loguru import logger
from playwright.async_api import Page


class RadioHandler:
    """Clicks a radio button/tile by its label text using Playwright native click.

    Waits 3 seconds after click to allow React state to stabilize.
    """

    def __init__(self, page: Page) -> None:
        """Initialize with a Playwright page.

        Args:
            page: Active Playwright Page instance.
        """
        self._page = page

    async def handle(self, field_label: str, value: str) -> bool:
        """Click a radio button by its label text.

        Args:
            field_label: Ignored (always "_radio").
            value: The radio button label text to click.

        Returns:
            True if the radio was clicked successfully.
        """
        page = self._page
        try:
            # Use Playwright's text locator - this triggers React state properly
            locator = page.locator(f"text={value}")
            count = await locator.count()
            if count > 0:
                await locator.first.click()
                await page.wait_for_timeout(3000)
                logger.info(f"  Radio clicked: {value}")
                return True
            logger.debug(f"Radio '{value}': 0 matches with text locator")
        except Exception as e:
            logger.debug(f"Could not click radio '{value}': {e}")
        return False
