"""Estimate management (save, share, rename) for AWS Calculator.

Handles the estimate page interactions: saving a service, sharing an estimate,
and renaming.
"""

from loguru import logger
from playwright.async_api import Page

CALCULATOR_BASE_URL = "https://calculator.aws"


class EstimateManager:
    """Manages estimate-level operations: save service, share link, rename.

    Args:
        page: The Playwright Page instance to operate on.
    """

    def __init__(self, page: Page) -> None:
        """Initialize with a Playwright page.

        Args:
            page: Active Playwright Page instance.
        """
        self._page = page

    async def save_service(self) -> None:
        """Click 'Save and add service' button on the configure page."""
        page = self._page
        save_btn = page.get_by_role("button", name="Save and add service")
        await save_btn.scroll_into_view_if_needed(timeout=5000)
        await save_btn.click(timeout=10000)
        await page.wait_for_timeout(2000)

    async def rename_estimate(self, name: str) -> None:
        """Rename the estimate on the estimate page.

        Args:
            name: The new name for the estimate.
        """
        page = self._page
        try:
            edit_link = page.locator('a:has-text("Edit")')
            if await edit_link.count() > 0:
                await edit_link.first.click()
                await page.wait_for_timeout(1000)
                name_input = page.locator('input[value="My Estimate"]')
                if await name_input.count() > 0:
                    await name_input.first.click(click_count=3)
                    await page.keyboard.type(name)
                    await page.wait_for_timeout(500)
                    save_btn = page.locator('button:has-text("Save")')
                    if await save_btn.count() > 0:
                        await save_btn.first.click()
                        await page.wait_for_timeout(1000)
                        logger.info(f"  Estimate renamed: {name}")
        except Exception as e:
            logger.debug(f"Could not rename estimate: {e}")

    async def get_share_link(self, estimate_name: str = "") -> str:
        """Navigate to My Estimate, optionally rename, and generate a share link.

        Args:
            estimate_name: Optional new name for the estimate before sharing.

        Returns:
            The shareable URL string, or an error message.
        """
        page = self._page
        await page.goto(f"{CALCULATOR_BASE_URL}/#/estimate", wait_until="networkidle")
        await page.wait_for_timeout(3000)
        # Dismiss cookies inline (avoid circular dependency on NavigationHelper)
        await page.evaluate("document.getElementById('awsccc-sb-ux-c')?.remove()")

        if estimate_name:
            await self.rename_estimate(estimate_name)

        share_btn = page.locator('button:has-text("Share")')
        if await share_btn.count() > 0:
            await share_btn.first.click(force=True)
            await page.wait_for_timeout(2000)

            agree_btn = page.locator('button:has-text("Agree and continue")')
            if await agree_btn.count() > 0:
                await agree_btn.first.click(force=True)
                await page.wait_for_timeout(5000)

            link_input = page.locator('input[value*="calculator.aws"]')
            if await link_input.count() > 0:
                return await link_input.first.get_attribute("value")

        return "Could not generate share link"
