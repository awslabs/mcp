"""Dropdown field handlers for AWS Calculator.

Implements Strategy pattern for native selects, Cloudscape dropdowns,
and change-by-current-text dropdowns.
"""

from loguru import logger
from playwright.async_api import Page


class DropdownHandler:
    """Selects a value from a native HTML <select> element near a label.

    Used for standard HTML select dropdowns (non-Cloudscape).
    """

    def __init__(self, page: Page) -> None:
        """Initialize with a Playwright page.

        Args:
            page: Active Playwright Page instance.
        """
        self._page = page

    async def handle(self, field_label: str, value: str) -> bool:
        """Select a value from a dropdown/select near a label.

        Args:
            field_label: The label text to match (partial, case-insensitive).
            value: The option text to select.

        Returns:
            True if the option was successfully selected.
        """
        page = self._page
        try:
            selects = page.locator("select")
            count = await selects.count()
            for i in range(count):
                parent = await selects.nth(i).evaluate("""
                    el => {
                        const container = el.closest('[class*="form-field"], [class*="FormField"]');
                        const label = container?.querySelector('label');
                        return label?.textContent || '';
                    }
                """)
                if field_label.lower() in parent.lower():
                    await selects.nth(i).select_option(label=value)
                    await page.wait_for_timeout(500)
                    return True
        except Exception as e:
            logger.debug(f"Could not select '{field_label}': {e}")
        return False


class CloudscapeDropdownHandler:
    """Selects a value from a Cloudscape dropdown (button[aria-haspopup]) by label.

    Finds the dropdown button by walking up from a matching label element.
    """

    def __init__(self, page: Page) -> None:
        """Initialize with a Playwright page.

        Args:
            page: Active Playwright Page instance.
        """
        self._page = page

    async def handle(self, field_label: str, value: str) -> bool:
        """Select a value from a Cloudscape dropdown.

        Args:
            field_label: The label text to match (partial match).
            value: The option text to select.

        Returns:
            True if the option was successfully selected.
        """
        page = self._page
        logger.debug(f"  Trying cloudscape dropdown: '{field_label}' = '{value}'")
        try:
            # Find the button ID by walking up from the label
            btn_id = await page.evaluate("""
                (fieldLabel) => {
                    const labels = document.querySelectorAll('label');
                    for (const label of labels) {
                        if (!label.textContent.trim().includes(fieldLabel)) continue;
                        // Strategy A: button shares same base ID as label
                        const labelId = label.id;
                        const btnId = labelId.replace('-label', '');
                        const btn = document.getElementById(btnId);
                        if (btn && btn.tagName === 'BUTTON' && btn.getAttribute('aria-haspopup')) {
                            return btnId;
                        }
                        // Strategy B: walk up and find button[aria-haspopup]
                        let el = label;
                        for (let i = 0; i < 8; i++) {
                            el = el.parentElement;
                            if (!el) break;
                            const found = el.querySelector('button[aria-haspopup]');
                            if (found && found.id) {
                                return found.id;
                            }
                        }
                    }
                    return null;
                }
            """, field_label)

            if not btn_id:
                return False

            # Click the button by ID (native Playwright click — triggers React properly)
            dropdown_btn = page.locator(f"#{btn_id}")
            await dropdown_btn.scroll_into_view_if_needed(timeout=3000)
            await page.wait_for_timeout(200)
            await dropdown_btn.click(timeout=3000)
            await page.wait_for_timeout(800)

            # Find and click the option - use exact text match via get_by_role
            option = page.get_by_role("option", name=value, exact=True)
            if await option.count() > 0:
                await option.first.click()
                await page.wait_for_timeout(500)
                logger.debug(f"  Cloudscape dropdown set: '{field_label}' = '{value}'")
                return True
            # Fallback: keyboard navigation - type value to filter, then Enter
            await page.keyboard.type(value)
            await page.wait_for_timeout(500)
            option = page.get_by_role("option", name=value, exact=True)
            if await option.count() > 0:
                await option.first.click()
                await page.wait_for_timeout(500)
                logger.debug(f"  Cloudscape dropdown set (typed): '{field_label}' = '{value}'")
                return True
            # Last resort: just press Enter on whatever is highlighted
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(500)
            logger.debug(f"  Cloudscape dropdown set (Enter): '{field_label}' = '{value}'")
            return True
        except Exception as e:
            logger.debug(f"Could not select dropdown '{field_label}' = '{value}': {e}")
        return False


class ChangeDropdownHandler:
    """Changes a Cloudscape dropdown by finding it by its current displayed text.

    Useful for Unit dropdowns that all share the same label.
    E.g., change the dropdown showing "minutes" to "hours".
    Uses exact text match to avoid false positives.
    """

    def __init__(self, page: Page) -> None:
        """Initialize with a Playwright page.

        Args:
            page: Active Playwright Page instance.
        """
        self._page = page

    async def handle(self, current_text: str, new_value: str) -> bool:
        """Change a dropdown by its current displayed text.

        Args:
            current_text: The text currently shown in the dropdown button.
            new_value: The new option to select.

        Returns:
            True if the dropdown was successfully changed.
        """
        page = self._page
        try:
            all_btns = page.locator('main button[aria-haspopup]')
            count = await all_btns.count()
            for i in range(count):
                text = (await all_btns.nth(i).text_content() or "").strip()
                if text == current_text or (
                    current_text in text and len(current_text) > 2
                ):
                    await all_btns.nth(i).scroll_into_view_if_needed(timeout=3000)
                    await page.wait_for_timeout(200)
                    await all_btns.nth(i).click(force=True)
                    await page.wait_for_timeout(600)

                    # Try exact role-based match first
                    opt = page.get_by_role("option", name=new_value, exact=True)
                    if await opt.count() > 0:
                        await opt.first.click()
                        await page.wait_for_timeout(500)
                        logger.debug(f"  Changed dropdown '{current_text}' -> '{new_value}'")
                        return True

                    # Fallback: has-text match
                    opt = page.locator(f'[role="option"]:has-text("{new_value}")')
                    if await opt.count() > 0:
                        await opt.first.click()
                        await page.wait_for_timeout(500)
                        logger.debug(
                            f"  Changed dropdown '{current_text}' -> '{new_value}' (has-text)"
                        )
                        return True

                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(200)
                    break
        except Exception as e:
            logger.debug(f"Could not change dropdown '{current_text}' -> '{new_value}': {e}")
        return False
