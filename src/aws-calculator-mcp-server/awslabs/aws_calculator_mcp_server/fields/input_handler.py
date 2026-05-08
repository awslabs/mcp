"""Input field handlers (numeric and text) for AWS Calculator.

Implements Strategy pattern for filling number and text input fields.
"""

from playwright.async_api import Page
from loguru import logger


class NumberFieldHandler:
    """Fills numeric input fields identified by aria-label or nearby label text.

    Strategy: tries multiple approaches (direct fill, scroll, expand sections,
    force visibility) to handle fields that may be collapsed or hidden.
    """

    def __init__(self, page: Page) -> None:
        """Initialize with a Playwright page.

        Args:
            page: Active Playwright Page instance.
        """
        self._page = page

    async def _expand_all_sections(self) -> None:
        """Expand all collapsed/accordion sections on the page."""
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

    async def handle(self, field_label: str, value: str) -> bool:
        """Fill a numeric input field identified by aria-label or nearby label text.

        Args:
            field_label: The label text to match (partial match on aria-label).
            value: The numeric value to fill.

        Returns:
            True if the field was successfully filled.
        """
        page = self._page
        try:
            # Strategy 1: aria-label match
            inp = page.locator(f'input[aria-label*="{field_label}" i]')
            if await inp.count() > 0:
                # Try direct fill first (works if visible)
                try:
                    await inp.first.fill(value, timeout=3000)
                    await page.wait_for_timeout(300)
                    logger.debug(f"  Filled '{field_label}' = '{value}' via direct fill")
                    return True
                except Exception as e:
                    logger.debug(f"  Direct fill failed for '{field_label}': {type(e).__name__}")

                # Try scroll into view then fill
                try:
                    await inp.first.scroll_into_view_if_needed(timeout=3000)
                    await page.wait_for_timeout(200)
                    await inp.first.fill(value, timeout=3000)
                    await page.wait_for_timeout(300)
                    return True
                except Exception:
                    pass

                # Try expanding sections (iterate to catch nested collapsed)
                await self._expand_all_sections()
                await page.wait_for_timeout(500)
                try:
                    await inp.first.scroll_into_view_if_needed(timeout=3000)
                    await page.wait_for_timeout(200)
                    await inp.first.fill(value, timeout=3000)
                    await page.wait_for_timeout(300)
                    return True
                except Exception:
                    pass

                # Force visibility via JS then fill
                inp_id = await inp.first.get_attribute("id")
                if inp_id:
                    await page.evaluate(f"""
                        () => {{
                            const el = document.getElementById("{inp_id}");
                            if (el) {{
                                let parent = el;
                                while (parent && parent.tagName !== 'MAIN') {{
                                    parent.style.setProperty('display', 'block', 'important');
                                    parent.style.setProperty('visibility', 'visible', 'important');
                                    parent.style.setProperty('opacity', '1', 'important');
                                    parent.style.setProperty('height', 'auto', 'important');
                                    parent = parent.parentElement;
                                }}
                                el.scrollIntoView();
                            }}
                        }}
                    """)
                    await page.wait_for_timeout(500)
                    try:
                        await inp.first.fill(value, timeout=3000)
                        await page.wait_for_timeout(300)
                        return True
                    except Exception:
                        pass

            # Strategy 2: find input inside form-field container matching label text
            fields = await page.evaluate(f"""
                () => {{
                    const labels = document.querySelectorAll('label, [class*="label"]');
                    for (const label of labels) {{
                        if (label.textContent.includes("{field_label}")) {{
                            const container = label.closest('[class*="form-field"], [class*="FormField"], [class*="awsui_child"]');
                            if (container) {{
                                const input = container.querySelector('input[type="number"], input[type="text"]');
                                if (input) {{
                                    return input.id || null;
                                }}
                            }}
                        }}
                    }}
                    return null;
                }}
            """)
            if fields:
                inp = page.locator(f"#{fields}")
                await inp.scroll_into_view_if_needed(timeout=5000)
                await page.wait_for_timeout(200)
                await inp.fill("", timeout=5000)
                await inp.fill(value, timeout=5000)
                await page.wait_for_timeout(300)
                return True
        except Exception as e:
            logger.debug(f"Could not fill '{field_label}': {e}")
        return False


class TextFieldHandler:
    """Fills text input fields by finding the input inside a labelled form-field container.

    Used for instance search, node counts, and similar text-based inputs.
    """

    def __init__(self, page: Page) -> None:
        """Initialize with a Playwright page.

        Args:
            page: Active Playwright Page instance.
        """
        self._page = page

    async def handle(self, field_label: str, value: str) -> bool:
        """Fill a text input by label.

        Args:
            field_label: The label text to match (partial match).
            value: The text value to fill.

        Returns:
            True if the field was successfully filled.
        """
        page = self._page
        try:
            fields = await page.evaluate(f"""
                () => {{
                    const labels = document.querySelectorAll('label, [class*="label"]');
                    for (const label of labels) {{
                        if (label.textContent.includes("{field_label}")) {{
                            const container = label.closest('[class*="form-field"], [class*="FormField"], [class*="awsui_child"]');
                            if (container) {{
                                const input = container.querySelector('input');
                                if (input) return input.id || null;
                            }}
                        }}
                    }}
                    return null;
                }}
            """)
            if fields:
                inp = page.locator(f"#{fields}")
                await inp.fill("")
                await inp.fill(value)
                await page.wait_for_timeout(500)
                return True
        except Exception as e:
            logger.debug(f"Could not fill text '{field_label}': {e}")
        return False
