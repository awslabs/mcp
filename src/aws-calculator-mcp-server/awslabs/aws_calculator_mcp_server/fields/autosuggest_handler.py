"""Autosuggest field handler for AWS Calculator.

Handles Cloudscape Autosuggest components (e.g., instance type search).
"""

from loguru import logger
from playwright.async_api import Page


class AutosuggestHandler:
    """Fills a Cloudscape Autosuggest component (click, select-all, type, Enter).

    Uses keyboard Enter to confirm selection - clicking options doesn't
    trigger React state updates properly in Cloudscape components.
    """

    def __init__(self, page: Page) -> None:
        """Initialize with a Playwright page.

        Args:
            page: Active Playwright Page instance.
        """
        self._page = page

    async def handle(self, placeholder: str, value: str) -> bool:
        """Fill a Cloudscape Autosuggest component.

        Args:
            placeholder: The input placeholder text to identify the component.
            value: The value to type and select.

        Returns:
            True if the autosuggest was successfully filled.
        """
        page = self._page
        try:
            inp = page.locator(f'input[placeholder="{placeholder}"]')
            if await inp.count() == 0:
                inp = page.locator(f'input[placeholder*="{placeholder}" i]')
            if await inp.count() == 0:
                return False

            await inp.first.click()
            await page.wait_for_timeout(300)
            await inp.first.click(click_count=3)
            await page.wait_for_timeout(200)
            await page.keyboard.type(value)
            await page.wait_for_timeout(2000)

            # Use keyboard to select: ArrowDown to highlight first option, Enter to confirm
            await page.keyboard.press("ArrowDown")
            await page.wait_for_timeout(300)
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(1000)
            return True
        except Exception as e:
            logger.debug(f"Autosuggest '{placeholder}' = '{value}' failed: {e}")
        return False
