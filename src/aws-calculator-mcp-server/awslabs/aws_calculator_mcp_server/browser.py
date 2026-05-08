"""Browser lifecycle management for AWS Calculator automation.

Encapsulates Playwright browser/context/page creation and teardown
using a simple manager pattern.
"""

from typing import Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright


class BrowserManager:
    """Manages Playwright browser lifecycle (launch, context, page, close).

    Attributes:
        page: The active Playwright Page instance (None until ensure_browser is called).
    """

    def __init__(self, headless: bool = True) -> None:
        """Initialize the browser manager.

        Args:
            headless: Whether to run the browser in headless mode.
        """
        self._headless = headless
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    @property
    def page(self) -> Optional[Page]:
        """Return the current Playwright page."""
        return self._page

    async def ensure_browser(self) -> Page:
        """Ensure a browser is running and return the page.

        Returns:
            The active Playwright Page instance.
        """
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=self._headless)
            self._context = await self._browser.new_context(
                viewport={"width": 1920, "height": 4000},
            )
            self._page = await self._context.new_page()
        return self._page

    async def close(self) -> None:
        """Close the browser and stop Playwright."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._page = None
        self._context = None
