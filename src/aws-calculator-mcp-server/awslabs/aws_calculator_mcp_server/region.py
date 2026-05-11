"""Region selection logic for AWS Calculator.

Handles the Cloudscape region dropdown on service configuration pages.
"""

from loguru import logger
from playwright.async_api import Page


class RegionSelector:
    """Selects a region from the Cloudscape dropdown on a configure page.

    Args:
        page: The Playwright Page instance to operate on.
    """

    def __init__(self, page: Page) -> None:
        """Initialize with a Playwright page.

        Args:
            page: Active Playwright Page instance.
        """
        self._page = page

    @staticmethod
    def extract_keyword(region_name: str) -> str:
        """Extract the keyword from a region display name for searching.

        Args:
            region_name: Full region display name, e.g. "US East (N. Virginia)".

        Returns:
            The keyword portion, e.g. "N. Virginia".
        """
        if "(" in region_name:
            return region_name.split("(")[-1].rstrip(")").strip()
        return region_name

    async def select_region(self, region_name: str = "US East (N. Virginia)") -> bool:
        """Select region from the Cloudscape dropdown on the configure page.

        Identifies the region dropdown by finding a button near the 'Region' label,
        then searches for the target region by keyword.

        Args:
            region_name: Full region display name, e.g. "South America (Sao Paulo)",
                        "US East (N. Virginia)", "EU (Ireland)", "Asia Pacific (Tokyo)".

        Returns:
            True if the region was successfully selected.
        """
        page = self._page
        region_keyword = self.extract_keyword(region_name)

        try:
            # Strategy 1: Find region dropdown via the "Region" label button
            region_btn = page.locator('button:has-text("Region")')
            if await region_btn.count() > 0:
                # The actual dropdown is the NEXT button[aria-haspopup] sibling
                # Find it via JS traversal from the Region label
                btn_found = await page.evaluate("""
                    () => {
                        const btns = document.querySelectorAll('main button[aria-haspopup]');
                        for (let i = 0; i < btns.length; i++) {
                            if (btns[i].textContent.trim() === 'Region' && btns[i+1]) {
                                btns[i+1].setAttribute('data-region-btn', 'true');
                                return true;
                            }
                        }
                        // Fallback: find any button near a "Region" label
                        const labels = document.querySelectorAll('label, [class*="label"]');
                        for (const lbl of labels) {
                            if (lbl.textContent.trim() === 'Region') {
                                const container = lbl.closest('[class*="form-field"], [class*="FormField"]')
                                    || lbl.parentElement?.parentElement;
                                if (container) {
                                    const btn = container.querySelector('button[aria-haspopup]');
                                    if (btn) {
                                        btn.setAttribute('data-region-btn', 'true');
                                        return true;
                                    }
                                }
                            }
                        }
                        return false;
                    }
                """)

                if btn_found:
                    dropdown = page.locator('[data-region-btn="true"]')
                    await dropdown.click(force=True)
                    await page.wait_for_timeout(800)
                    await page.evaluate(
                        "document.querySelector('[data-region-btn]')?.removeAttribute('data-region-btn')"
                    )
                else:
                    # Strategy 2: Click the second button[aria-haspopup] in main
                    all_btns = page.locator('main button[aria-haspopup]')
                    if await all_btns.count() >= 2:
                        await all_btns.nth(1).click(force=True)
                        await page.wait_for_timeout(800)
                    else:
                        return False
            else:
                return False

            # Now find and click the target region option
            option = page.locator(f'[role="option"]:has-text("{region_keyword}")')
            if await option.count() > 0:
                await option.first.click()
                await page.wait_for_timeout(1000)
                logger.info(f"  Region set to {region_name}")
                return True

            # Type to filter if not immediately visible
            await page.keyboard.type(region_keyword)
            await page.wait_for_timeout(500)
            option = page.locator(f'[role="option"]:has-text("{region_keyword}")')
            if await option.count() > 0:
                await option.first.click()
                await page.wait_for_timeout(1000)
                logger.info(f"  Region set to {region_name}")
                return True

            await page.keyboard.press("Escape")
        except Exception as e:
            logger.warning(f"Region selection failed: {e}")
        return False
