"""Playwright automation for AWS Pricing Calculator.

Scraped form field names (May 2026):
- RDS: Nodes (count), instance search, Deployment Option (dropdown: Multi-AZ/Single-AZ),
        Storage amount, Utilization, Pricing Model (OnDemand)
- Fargate: Number of tasks or pods, Average duration, Amount of memory allocated,
           Amount of ephemeral storage, OS (Linux), CPU Arch (x86), Region dropdown
- ELB: Number of Application Load Balancers, Processed bytes
- VPC: Number of Instances (NAT gateways)
- ElastiCache: Nodes (count), instance search, Utilization
- CloudWatch: Number of Metrics, Standard Logs: Data Ingested
- WAF: Number of Web Access Control Lists, Number of Rules, Number of web requests
- Shield: (subscription only, no config needed)
- Secrets Manager: Number of secrets, Average duration, Number of API calls
- KMS: Number of customer managed CMKs, Number of symmetric requests
- Route 53: Hosted Zones
- ECR: Amount of data stored
- Backup: Amount of primary data, retention periods
- CloudTrail: Management event trails
"""

import asyncio
import json
import re
from typing import Optional

from loguru import logger
from playwright.async_api import Browser, BrowserContext, Page, async_playwright


CALCULATOR_BASE_URL = "https://calculator.aws"


class AWSCalculatorAutomation:
    """Automates AWS Pricing Calculator using Playwright."""

    def __init__(self, headless: bool = True):
        self._headless = headless
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def _ensure_browser(self):
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=self._headless)
            self._context = await self._browser.new_context(
                viewport={"width": 1920, "height": 4000},
            )
            self._page = await self._context.new_page()

    async def _dismiss_cookies(self):
        await self._page.evaluate("document.getElementById('awsccc-sb-ux-c')?.remove()")

    async def close(self):
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def _select_region(self, region_name: str = "US East (N. Virginia)"):
        """Select region from the Cloudscape dropdown on the configure page.

        Identifies the region dropdown by finding a button near the 'Region' label,
        then searches for the target region by keyword.

        Args:
            region_name: Full region display name, e.g. "South America (Sao Paulo)",
                        "US East (N. Virginia)", "EU (Ireland)", "Asia Pacific (Tokyo)"
        """
        page = self._page
        region_keyword = region_name.split("(")[-1].rstrip(")").strip() if "(" in region_name else region_name

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
                    await page.evaluate("document.querySelector('[data-region-btn]')?.removeAttribute('data-region-btn')")
                else:
                    # Strategy 2: Click the second button[aria-haspopup] in main
                    # (first is typically "Region" label, second is the value)
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

    async def _set_unit_for_field(self, field_label: str, unit_value: str) -> bool:
        """Set the Unit dropdown that's a sibling of a specific field.

        Many calculator fields have a Value input + Unit dropdown side by side.
        This finds the Unit dropdown adjacent to the field with the given label.
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
            await page.evaluate("document.querySelector('[data-calc-unit-target]')?.removeAttribute('data-calc-unit-target')")

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

    async def _click_radio(self, label_text: str) -> bool:
        """Click a radio button/tile by its label text using Playwright native click."""
        page = self._page
        try:
            # Use Playwright's text locator — this triggers React state properly
            locator = page.locator(f"text={label_text}")
            count = await locator.count()
            if count > 0:
                await locator.first.click()
                await page.wait_for_timeout(3000)
                logger.info(f"  Radio clicked: {label_text}")
                return True
            logger.debug(f"Radio '{label_text}': 0 matches with text locator")
        except Exception as e:
            logger.debug(f"Could not click radio '{label_text}': {e}")
        return False

    async def _fill_autosuggest(self, placeholder: str, value: str) -> bool:
        """Fill a Cloudscape Autosuggest component (click, select-all, type, Enter).

        Uses keyboard Enter to confirm selection — clicking options doesn't
        trigger React state updates properly in Cloudscape components.
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

    async def _expand_all_sections(self):
        """Expand all collapsed/accordion sections on the page (iterates for nested)."""
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
            except:
                break

    async def _fill_number_field(self, label_contains: str, value: str) -> bool:
        """Fill a numeric input field identified by aria-label or nearby label text."""
        page = self._page
        try:
            # Strategy 1: aria-label match
            inp = page.locator(f'input[aria-label*="{label_contains}" i]')
            if await inp.count() > 0:
                # Try direct fill first (works if visible)
                try:
                    await inp.first.fill(value, timeout=3000)
                    await page.wait_for_timeout(300)
                    logger.debug(f"  Filled '{label_contains}' = '{value}' via direct fill")
                    return True
                except Exception as e:
                    logger.debug(f"  Direct fill failed for '{label_contains}': {type(e).__name__}")

                # Try scroll into view then fill
                try:
                    await inp.first.scroll_into_view_if_needed(timeout=3000)
                    await page.wait_for_timeout(200)
                    await inp.first.fill(value, timeout=3000)
                    await page.wait_for_timeout(300)
                    return True
                except:
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
                except:
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
                    except:
                        pass

            # Strategy 2: find input inside form-field container matching label text
            fields = await page.evaluate(f"""
                () => {{
                    const labels = document.querySelectorAll('label, [class*="label"]');
                    for (const label of labels) {{
                        if (label.textContent.includes("{label_contains}")) {{
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
            logger.debug(f"Could not fill '{label_contains}': {e}")
        return False

    async def _fill_text_field(self, label_contains: str, value: str) -> bool:
        """Fill a text input by label (used for instance search, node counts, etc.)."""
        page = self._page
        try:
            fields = await page.evaluate(f"""
                () => {{
                    const labels = document.querySelectorAll('label, [class*="label"]');
                    for (const label of labels) {{
                        if (label.textContent.includes("{label_contains}")) {{
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
            logger.debug(f"Could not fill text '{label_contains}': {e}")
        return False

    async def _select_cloudscape_dropdown(self, label_contains: str, value: str) -> bool:
        """Select a value from a Cloudscape dropdown (button[aria-haspopup])."""
        page = self._page
        logger.debug(f"  Trying cloudscape dropdown: '{label_contains}' = '{value}'")
        try:
            # Find the button ID by walking up from the label
            btn_id = await page.evaluate(f"""
                () => {{
                    const labels = document.querySelectorAll('label');
                    for (const label of labels) {{
                        if (!label.textContent.trim().includes("{label_contains}")) continue;
                        // Strategy A: button shares same base ID as label
                        const labelId = label.id; // e.g. formField1299-xxx-label
                        const btnId = labelId.replace('-label', '');
                        const btn = document.getElementById(btnId);
                        if (btn && btn.tagName === 'BUTTON' && btn.getAttribute('aria-haspopup')) {{
                            return btnId;
                        }}
                        // Strategy B: walk up and find button[aria-haspopup]
                        let el = label;
                        for (let i = 0; i < 8; i++) {{
                            el = el.parentElement;
                            if (!el) break;
                            const found = el.querySelector('button[aria-haspopup]');
                            if (found && found.id) {{
                                return found.id;
                            }}
                        }}
                    }}
                    return null;
                }}
            """)

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
                logger.debug(f"  Cloudscape dropdown set: '{label_contains}' = '{value}'")
                return True
            # Fallback: keyboard navigation - type value to filter, then Enter
            await page.keyboard.type(value)
            await page.wait_for_timeout(500)
            option = page.get_by_role("option", name=value, exact=True)
            if await option.count() > 0:
                await option.first.click()
                await page.wait_for_timeout(500)
                logger.debug(f"  Cloudscape dropdown set (typed): '{label_contains}' = '{value}'")
                return True
            # Last resort: just press Enter on whatever is highlighted
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(500)
            logger.debug(f"  Cloudscape dropdown set (Enter): '{label_contains}' = '{value}'")
            return True
        except Exception as e:
            logger.debug(f"Could not select dropdown '{label_contains}' = '{value}': {e}")
        return False

    async def _change_dropdown_by_current_text(self, current_text: str, new_value: str) -> bool:
        """Change a Cloudscape dropdown by finding it by its current displayed text.

        Useful for Unit dropdowns that all share the same label.
        E.g., change the dropdown showing "minutes" to "hours".
        Uses exact text match to avoid false positives (e.g., "1" matching "10").
        """
        page = self._page
        try:
            all_btns = page.locator('main button[aria-haspopup]')
            count = await all_btns.count()
            for i in range(count):
                text = (await all_btns.nth(i).text_content() or "").strip()
                # Exact match: the button text must be exactly the current_text
                # or the current_text must be a complete word boundary match
                if text == current_text or (
                    current_text in text and
                    len(current_text) > 2 and
                    not any(c.isdigit() for c in current_text and len(current_text) == 1)
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
                        logger.debug(f"  Changed dropdown '{current_text}' -> '{new_value}' (has-text)")
                        return True

                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(200)
                    break
        except Exception as e:
            logger.debug(f"Could not change dropdown '{current_text}' -> '{new_value}': {e}")
        return False

    async def _select_dropdown(self, label_contains: str, option_text: str) -> bool:
        """Select a value from a dropdown/select near a label."""
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
                if label_contains.lower() in parent.lower():
                    await selects.nth(i).select_option(label=option_text)
                    await page.wait_for_timeout(500)
                    return True
        except Exception as e:
            logger.debug(f"Could not select '{label_contains}': {e}")
        return False

    async def _search_and_configure(self, service_name: str) -> bool:
        """Navigate to add service, search, and click Configure."""
        page = self._page
        await page.goto(f"{CALCULATOR_BASE_URL}/#/addService", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await self._dismiss_cookies()

        search = page.locator('input[type="search"]')
        if await search.count() > 0:
            await search.first.fill(service_name)
            await page.wait_for_timeout(2000)

        # Prefer precise aria-label match, fall back to generic
        configure_btn = page.locator(f'button[aria-label*="Configure {service_name}"]')
        if await configure_btn.count() == 0:
            configure_btn = page.locator('button:has-text("Configure")')
        if await configure_btn.count() > 0:
            await configure_btn.first.click()
            await page.wait_for_timeout(3000)
            await self._dismiss_cookies()
            await self._expand_all_sections()
            return True
        return False

    async def _save_service(self):
        """Click 'Save and add service'."""
        page = self._page
        save_btn = page.get_by_role("button", name="Save and add service")
        await save_btn.click(force=True, timeout=10000)
        await page.wait_for_timeout(2000)

    async def _get_current_cost(self) -> str:
        """Read the current total monthly cost from the footer."""
        page = self._page
        try:
            text = await page.locator("body").text_content()
            match = re.search(r"Total Monthly cost:\s*([\d,]+\.?\d*)\s*USD", text)
            if match:
                return match.group(1)
        except:
            pass
        return "0"

    async def create_estimate(self, services: list[dict]) -> dict:
        """Create an estimate with the given services and return the share link.

        Args:
            services: List of service configurations. Each should have:
                - service_name: Name to search in calculator
                - config: Dict of field_label -> value pairs
                - region: Optional region (default: sa-east-1)

        Returns:
            Dict with estimate_url, monthly_cost, and services details.
        """
        await self._ensure_browser()
        page = self._page

        logger.info("Navigating to AWS Calculator...")
        await page.goto(f"{CALCULATOR_BASE_URL}/#/addService", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await self._dismiss_cookies()

        results = []
        for svc in services:
            service_name = svc["service_name"]
            config = svc.get("config", {})
            region = svc.get("region", "US East (N. Virginia)")

            logger.info(f"Adding: {service_name}")

            if not await self._search_and_configure(service_name):
                logger.warning(f"Could not find: {service_name}")
                results.append({"service_name": service_name, "status": "not_found"})
                continue

            # Set region
            await self._select_region(region)
            await page.wait_for_timeout(2000)

            # Process _radio first (must come after region change stabilizes)
            radio_value = config.get("_radio")
            if radio_value:
                # Debug: log page URL and check text exists
                logger.debug(f"  Page URL before radio: {page.url}")
                body = await page.locator("main").text_content()
                if radio_value in body:
                    logger.debug(f"  Radio text FOUND in page body")
                else:
                    logger.debug(f"  Radio text NOT in page body. First 200: {body[:200]}")
                await self._click_radio(str(radio_value))

            # Fill config fields - try native inputs first, then Cloudscape dropdowns
            for field_label, value in config.items():
                # Special: "_unit" suffix means set Unit dropdown for a field
                if field_label.endswith("_unit"):
                    parent_field = field_label[:-5]
                    await self._set_unit_for_field(parent_field, str(value))
                    continue

                # Special: "_change:current_text" means change a dropdown by its visible text
                if field_label.startswith("_change:"):
                    current_text = field_label[8:]
                    await self._change_dropdown_by_current_text(current_text, str(value))
                    continue

                # Special: "_select_cloudscape:label" means select from a Cloudscape dropdown by label
                if field_label.startswith("_select_cloudscape:"):
                    label = field_label[19:]
                    await self._select_cloudscape_dropdown(label, str(value))
                    continue

                # Special: "_nth_dropdown:N:text" means click Nth dropdown matching text, select value
                if field_label.startswith("_nth_dropdown:"):
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
                    continue

                # Special: "_nth_input:N" means fill Nth input matching aria-label pattern
                if field_label.startswith("_nth_input:"):
                    parts = field_label[11:].split(":", 1)
                    idx = int(parts[0]) - 1
                    aria_pattern = parts[1] if len(parts) > 1 else "Enter Amount"
                    inputs = page.locator(f'input[aria-label*="{aria_pattern}"]')
                    if await inputs.count() > idx:
                        await inputs.nth(idx).fill("")
                        await inputs.nth(idx).fill(str(value))
                        await page.wait_for_timeout(300)
                    continue

                # Special: "_autosuggest:placeholder" means use autosuggest component
                if field_label.startswith("_autosuggest:"):
                    placeholder = field_label[13:]
                    await self._fill_autosuggest(placeholder, str(value))
                    continue

                # Special: "_radio" already handled pre-loop, skip here
                if field_label == "_radio":
                    continue

                filled = await self._fill_number_field(field_label, str(value))
                if not filled:
                    filled = await self._fill_text_field(field_label, str(value))
                if not filled:
                    filled = await self._select_dropdown(field_label, str(value))
                if not filled:
                    filled = await self._select_cloudscape_dropdown(field_label, str(value))
                if not filled:
                    # Last resort: try _change_dropdown_by_current_text for single-char values
                    if len(str(value)) <= 2:
                        filled = await self._change_dropdown_by_current_text(field_label, str(value))
                if not filled:
                    logger.debug(f"  Could not set: {field_label} = {value}")

            # Trigger recalculation: click description field to blur all, wait for price
            desc = page.locator('input[aria-label*="Description" i]')
            if await desc.count() > 0:
                await desc.first.click()
                await page.wait_for_timeout(500)
            await page.wait_for_timeout(3000)

            # Get cost before saving
            cost = await self._get_current_cost()

            await self._save_service()
            results.append({
                "service_name": service_name,
                "status": "added",
                "monthly_cost": cost,
            })

        # Get share link
        share_url = await self._get_share_link()
        final_cost = await self._get_total_cost()

        return {
            "estimate_url": share_url,
            "monthly_cost": final_cost,
            "services": results,
        }

    async def _rename_estimate(self, name: str):
        """Rename the estimate on the estimate page."""
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

    async def _get_share_link(self, estimate_name: str = "") -> str:
        """Navigate to My Estimate, rename if needed, and share."""
        page = self._page
        await page.goto(f"{CALCULATOR_BASE_URL}/#/estimate", wait_until="networkidle")
        await page.wait_for_timeout(3000)
        await self._dismiss_cookies()

        if estimate_name:
            await self._rename_estimate(estimate_name)

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

    async def _get_total_cost(self) -> str:
        """Get total monthly cost from estimate page."""
        page = self._page
        try:
            text = await page.locator("body").text_content()
            match = re.search(r"Monthly cost\s*([\d,]+\.?\d*)\s*USD", text)
            if match:
                return f"${match.group(1)} USD/month"
        except:
            pass
        return "Unknown"

    async def update_estimate(
        self,
        estimate_url: str,
        add_services: list[dict] = None,
        remove_services: list[str] = None,
    ) -> dict:
        """Load an existing estimate, modify it, and return a new share link.

        Args:
            estimate_url: The shareable calculator.aws URL to load.
            add_services: Services to add (same format as create_estimate).
            remove_services: Service names to remove.

        Returns:
            Dict with new estimate_url, monthly_cost, and services.
        """
        await self._ensure_browser()
        page = self._page

        # 1. Load existing estimate
        logger.info(f"Loading estimate: {estimate_url}")
        await page.goto(estimate_url, wait_until="networkidle")
        await page.wait_for_timeout(5000)
        await self._dismiss_cookies()

        # 2. Click "Update estimate" to load into local session
        update_btn = page.locator('button[aria-label="Update estimate button"]')
        if await update_btn.count() > 0:
            await update_btn.click()
            await page.wait_for_timeout(3000)
            logger.info("  Loaded estimate into session")
        else:
            return {"error": "Could not find 'Update estimate' button"}

        # 3. Remove services if requested
        if remove_services:
            await page.goto(f"{CALCULATOR_BASE_URL}/#/estimate", wait_until="networkidle")
            await page.wait_for_timeout(3000)
            await self._dismiss_cookies()

            for svc_name in remove_services:
                logger.info(f"  Removing: {svc_name}")
                # Find the service row and click its delete button
                delete_btn = page.locator(
                    f'button[aria-label*="Delete"][aria-label*="{svc_name}"]'
                )
                if await delete_btn.count() > 0:
                    await delete_btn.first.click()
                    await page.wait_for_timeout(1000)
                    # Confirm deletion if dialog appears
                    confirm = page.locator('button:has-text("Delete")')
                    if await confirm.count() > 1:
                        await confirm.last.click()
                        await page.wait_for_timeout(1000)
                else:
                    logger.warning(f"  Could not find delete button for: {svc_name}")

        # 4. Add new services if requested
        results = []
        if add_services:
            for svc in add_services:
                service_name = svc["service_name"]
                config = svc.get("config", {})
                region = svc.get("region", "US East (N. Virginia)")

                logger.info(f"  Adding: {service_name}")

                if not await self._search_and_configure(service_name):
                    logger.warning(f"  Could not find: {service_name}")
                    results.append({"service_name": service_name, "status": "not_found"})
                    continue

                await self._select_region(region)
                await page.wait_for_timeout(2000)

                # Process radio first
                radio_value = config.get("_radio")
                if radio_value:
                    await self._click_radio(str(radio_value))

                # Fill fields
                for field_label, value in config.items():
                    if field_label.endswith("_unit"):
                        await self._set_unit_for_field(field_label[:-5], str(value))
                    elif field_label.startswith("_change:"):
                        await self._change_dropdown_by_current_text(field_label[8:], str(value))
                    elif field_label.startswith("_select_cloudscape:"):
                        await self._select_cloudscape_dropdown(field_label[19:], str(value))
                    elif field_label.startswith("_autosuggest:"):
                        await self._fill_autosuggest(field_label[13:], str(value))
                    elif field_label == "_radio":
                        continue
                    else:
                        filled = await self._fill_number_field(field_label, str(value))
                        if not filled:
                            filled = await self._fill_text_field(field_label, str(value))
                        if not filled:
                            filled = await self._select_cloudscape_dropdown(field_label, str(value))

                cost = await self._get_current_cost()
                await self._save_service()
                results.append({
                    "service_name": service_name,
                    "status": "added",
                    "monthly_cost": cost,
                })

        # 5. Generate new share link
        share_url = await self._get_share_link()
        final_cost = await self._get_total_cost()

        return {
            "estimate_url": share_url,
            "monthly_cost": final_cost,
            "services_added": results,
            "services_removed": remove_services or [],
            "based_on": estimate_url,
        }
