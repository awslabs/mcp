"""Cost reading logic for AWS Calculator.

Reads and polls for cost values from both configuration and estimate pages.
"""

import re

from playwright.async_api import Page


class CostReader:
    """Reads cost values from AWS Calculator pages with polling.

    Args:
        page: The Playwright Page instance to read costs from.
    """

    # Patterns for the configure-page footer cost
    SERVICE_COST_PATTERNS: list[str] = [
        r"Total Monthly cost:\s*([\d,]+\.?\d*)\s*USD",
        r"Estimated monthly cost\s*([\d,]+\.?\d*)\s*USD",
        r"monthly cost:?\s*\$?([\d,]+\.?\d*)\s*USD",
    ]

    # Patterns for the estimate summary page
    TOTAL_COST_PATTERNS: list[str] = [
        r"Total monthly cost:?\s*([\d,]+\.?\d*)\s*USD",
        r"Monthly cost\s*([\d,]+\.?\d*)\s*USD",
    ]

    def __init__(self, page: Page) -> None:
        """Initialize with a Playwright page.

        Args:
            page: Active Playwright Page instance.
        """
        self._page = page

    async def get_current_cost(self, max_attempts: int = 5) -> str:
        """Read the current service monthly cost from the configure page footer.

        Polls for up to max_attempts seconds waiting for the cost to recalculate.

        Args:
            max_attempts: Number of polling attempts (1 second apart).

        Returns:
            The cost string (e.g. "12.50") or "0.00" if not found.
        """
        page = self._page
        for attempt in range(max_attempts):
            try:
                text = await page.locator("body").text_content()
                for pattern in self.SERVICE_COST_PATTERNS:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match and float(match.group(1).replace(",", "")) > 0:
                        return match.group(1)
            except Exception:
                pass
            await page.wait_for_timeout(1000)
        return "0.00"

    async def get_total_cost(self, max_attempts: int = 15) -> str:
        """Get total monthly cost from the estimate summary page.

        Polls the page until a non-zero cost appears or timeout.

        Args:
            max_attempts: Number of polling attempts (1 second apart).

        Returns:
            Formatted cost string (e.g. "$12.50 USD/month") or "Unknown".
        """
        page = self._page
        for attempt in range(max_attempts):
            try:
                text = await page.locator("body").text_content()
                for pattern in self.TOTAL_COST_PATTERNS:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        value = match.group(1)
                        if float(value.replace(",", "")) > 0:
                            return f"${value} USD/month"
            except Exception:
                pass
            await page.wait_for_timeout(1000)
        return "Unknown"
