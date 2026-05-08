"""Positional field handlers for AWS Calculator.

Handles fields identified by position (nth dropdown, nth input) and unit dropdowns.
"""

from playwright.async_api import Page
from loguru import logger


class PositionalDropdownHandler:
    """Selects from the Nth dropdown matching a text pattern.

    Field label format: _nth_dropdown:N:text
    Where N is 1-based index and text is the button text to match.
    """

    def __init__(self, page: Page) -> None:
        """Initialize with a Playwright page.

        Args:
            page: Active Playwright Page instance.
        """
        self._page = page

    async def handle(self, field_label: str, value: str) -> bool:
        """Select from the Nth dropdown matching a text pattern.

        Args:
            field_label: Full field label in format "_nth_dropdown:N:text".
            value: The option to select from the dropdown.

        Returns:
            True if the option was successfully selected.
        """
        page = self._page
        try:
            parts = field_label[14:].split(":", 1)
            idx = int(parts[0]) - 1
            match_text = parts[1] if len(parts) > 1 else ""
            btns = page.locator(f'main button:has-text("{match_text}")')
            if await btns.count() > idx:
                await btns.nth(idx).click(force=True)
                await page.wait_for_timeout(600)
                opt = page.get_by_role("option", name=str(value), exact=True)
                if await opt.count() > 0:
                    await opt.first.click()
                else:
                    opt = page.locator(f'[role="option"]:has-text("{value}")')
                    if await opt.count() > 0:
                        await opt.first.click()
                    else:
                        await page.keyboard.press("Escape")
                await page.wait_for_timeout(500)
                return True
        except Exception as e:
            logger.debug(f"Positional dropdown failed for '{field_label}': {e}")
        return False


class PositionalInputHandler:
    """Fills the Nth input matching an aria-label pattern.

    Field label format: _nth_input:N:pattern
    Where N is 1-based index and pattern is the aria-label substring to match.
    """

    def __init__(self, page: Page) -> None:
        """Initialize with a Playwright page.

        Args:
            page: Active Playwright Page instance.
        """
        self._page = page

    async def handle(self, field_label: str, value: str) -> bool:
        """Fill the Nth input matching an aria-label pattern.

        Args:
            field_label: Full field label in format "_nth_input:N:pattern".
            value: The value to fill.

        Returns:
            True if the input was successfully filled.
        """
        page = self._page
        try:
            parts = field_label[11:].split(":", 1)
            idx = int(parts[0]) - 1
            aria_pattern = parts[1] if len(parts) > 1 else "Enter Amount"
            inputs = page.locator(f'input[aria-label*="{aria_pattern}"]')
            if await inputs.count() > idx:
                await inputs.nth(idx).fill("")
                await inputs.nth(idx).fill(str(value))
                await page.wait_for_timeout(300)
                return True
        except Exception as e:
            logger.debug(f"Positional input failed for '{field_label}': {e}")
        return False


class UnitHandler:
    """Sets the Unit dropdown that is a sibling of a specific field.

    Many calculator fields have a Value input + Unit dropdown side by side.
    This finds the Unit dropdown adjacent to the field with the given label.
    """

    def __init__(self, page: Page) -> None:
        """Initialize with a Playwright page.

        Args:
            page: Active Playwright Page instance.
        """
        self._page = page

    async def handle(self, field_label: str, unit_value: str) -> bool:
        """Set the Unit dropdown for a field.

        Args:
            field_label: The parent field label (without _unit suffix).
            unit_value: The unit option to select (e.g. "hours", "GB").

        Returns:
            True if the unit was successfully set.
        """
        page = self._page
        try:
            result = await page.evaluate(f"""
                () => {{
                    const labels = document.querySelectorAll('label');
                    for (const label of labels) {{
                        if (!label.textContent.trim().includes("{field_label}")) continue;
                        // Go up to the row/container that holds both Value and Unit
                        let container = label;
                        for (let i = 0; i < 6; i++) {{
                            container = container.parentElement;
                            if (!container) break;
                            // Look for a Unit dropdown sibling
                            const unitLabels = container.querySelectorAll('label');
                            for (const ul of unitLabels) {{
                                if (ul.textContent.trim() === 'Unit') {{
                                    const unitContainer = ul.parentElement;
                                    const btn = unitContainer?.querySelector('button[aria-haspopup]');
                                    if (btn) {{
                                        btn.setAttribute('data-calc-unit-target', 'true');
                                        return true;
                                    }}
                                }}
                            }}
                        }}
                    }}
                    return false;
                }}
            """)

            if not result:
                return False

            btn = page.locator('button[data-calc-unit-target="true"]')
            await btn.click(force=True)
            await page.wait_for_timeout(500)
            await page.evaluate(
                "document.querySelector('[data-calc-unit-target]')?.removeAttribute('data-calc-unit-target')"
            )

            option = page.locator(f'[role="option"]:has-text("{unit_value}")')
            if await option.count() > 0:
                await option.first.click()
                await page.wait_for_timeout(500)
                return True
            else:
                await page.keyboard.press("Escape")
        except Exception as e:
            logger.debug(f"Could not set unit for '{field_label}': {e}")
        return False
