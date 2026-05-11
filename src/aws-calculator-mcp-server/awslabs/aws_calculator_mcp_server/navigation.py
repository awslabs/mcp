"""Navigation helpers for AWS Calculator pages.

Handles cookie dismissal, section expansion, and search-and-configure flow.
"""

from playwright.async_api import Page

CALCULATOR_BASE_URL = "https://calculator.aws"


class NavigationHelper:
    """Handles page navigation, cookie banners, and section expansion.

    Args:
        page: The Playwright Page instance to operate on.
    """

    def __init__(self, page: Page) -> None:
        """Initialize with a Playwright page.

        Args:
            page: Active Playwright Page instance.
        """
        self._page = page

    async def dismiss_cookies(self) -> None:
        """Remove the AWS cookie consent banner via DOM manipulation."""
        await self._page.evaluate("document.getElementById('awsccc-sb-ux-c')?.remove()")

    async def expand_all_sections(self) -> None:
        """Expand all collapsed/accordion sections on the page.

        Iterates up to 3 times to handle nested collapsed sections.
        """
        page = self._page
        for _ in range(3):
            try:
                expanded_count = await page.evaluate("""
                    () => {
                        let count = 0;
                        document.querySelectorAll(
                            'button[aria-expanded="false"]'
                        ).forEach(btn => {
                            btn.click();
                            count++;
                        });
                        return count;
                    }
                """)
                await page.wait_for_timeout(600)
                if expanded_count == 0:
                    break
            except Exception:
                break

    async def search_and_configure(self, service_name: str) -> bool:
        """Navigate to add-service page, search for a service, and click Configure.

        Args:
            service_name: The AWS service name to search for.

        Returns:
            True if the service was found and Configure was clicked.
        """
        page = self._page
        await page.goto(f"{CALCULATOR_BASE_URL}/#/addService", wait_until="networkidle")
        await self.dismiss_cookies()

        search = page.locator('input[type="search"]')
        if await search.count() > 0:
            await search.first.fill(service_name)
            await page.wait_for_timeout(1000)

        # Prefer precise aria-label match, fall back to generic
        configure_btn = page.locator(f'button[aria-label*="Configure {service_name}"]')
        if await configure_btn.count() == 0:
            configure_btn = page.locator('button:has-text("Configure")')
        if await configure_btn.count() > 0:
            await configure_btn.first.click()
            await page.wait_for_load_state("networkidle")
            await self.dismiss_cookies()
            await self.expand_all_sections()
            return True
        return False
