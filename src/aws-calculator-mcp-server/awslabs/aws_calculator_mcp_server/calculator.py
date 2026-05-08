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

This module is the Facade (GoF) — it exposes the same public API as before
but delegates to internal components:
- BrowserManager: browser lifecycle
- NavigationHelper: page navigation, cookies, section expansion
- RegionSelector: region dropdown logic
- FieldProcessor: dispatches to the correct FieldHandler strategy
- CostReader: reads costs with polling
- EstimateManager: save, share, get link
"""

from typing import Optional

from loguru import logger

from .browser import BrowserManager
from .cost import CostReader
from .estimate import EstimateManager
from .fields import FieldProcessor
from .navigation import NavigationHelper, CALCULATOR_BASE_URL
from .region import RegionSelector


class AWSCalculatorAutomation:
    """Automates AWS Pricing Calculator using Playwright.

    This is the public Facade that delegates to specialized components.
    The public API is unchanged: create_estimate, update_estimate, close.
    """

    def __init__(self, headless: bool = True) -> None:
        """Initialize the calculator automation.

        Args:
            headless: Whether to run the browser in headless mode.
        """
        self._browser_manager = BrowserManager(headless=headless)

    async def _ensure_browser(self) -> None:
        """Ensure the browser is running."""
        await self._browser_manager.ensure_browser()

    async def close(self) -> None:
        """Close the browser and release all resources."""
        await self._browser_manager.close()

    # --- Compatibility properties for BDD step definitions ---

    @property
    def _page(self):
        """Access the Playwright page (used by BDD steps)."""
        return self._browser_manager.page

    @property
    def _browser(self):
        """Access the browser instance (used by BDD steps)."""
        return self._browser_manager._browser

    async def _dismiss_cookies(self):
        """Dismiss cookie banner (used by BDD steps)."""
        nav = NavigationHelper(self._browser_manager.page)
        await nav.dismiss_cookies()

    async def _expand_all_sections(self):
        """Expand collapsed sections (used by BDD steps)."""
        nav = NavigationHelper(self._browser_manager.page)
        await nav.expand_all_sections()

    async def _select_region(self, region_name: str):
        """Select region (used by BDD steps)."""
        selector = RegionSelector(self._browser_manager.page)
        return await selector.select_region(region_name)

    async def _fill_number_field(self, label: str, value: str):
        """Fill number field (used by BDD steps)."""
        from .fields.input_handler import NumberFieldHandler
        handler = NumberFieldHandler(self._browser_manager.page)
        return await handler.handle(label, value)

    async def _fill_text_field(self, label: str, value: str):
        """Fill text field (used by BDD steps)."""
        from .fields.input_handler import TextFieldHandler
        handler = TextFieldHandler(self._browser_manager.page)
        return await handler.handle(label, value)

    async def _select_cloudscape_dropdown(self, label: str, value: str):
        """Select cloudscape dropdown (used by BDD steps)."""
        from .fields.dropdown_handler import CloudscapeDropdownHandler
        handler = CloudscapeDropdownHandler(self._browser_manager.page)
        return await handler.handle(label, value)

    async def _fill_autosuggest(self, placeholder: str, value: str):
        """Fill autosuggest (used by BDD steps)."""
        from .fields.autosuggest_handler import AutosuggestHandler
        handler = AutosuggestHandler(self._browser_manager.page)
        return await handler.handle(placeholder, value)

    async def _click_radio(self, label: str):
        """Click radio button (used by BDD steps)."""
        from .fields.radio_handler import RadioHandler
        handler = RadioHandler(self._browser_manager.page)
        return await handler.handle("_radio", label)

    async def _save_service(self):
        """Save service (used by BDD steps)."""
        manager = EstimateManager(self._browser_manager.page)
        await manager.save_service()

    async def _get_share_link(self):
        """Get share link (used by BDD steps)."""
        manager = EstimateManager(self._browser_manager.page)
        return await manager.get_share_link()

    async def _configure_service(
        self,
        service_name: str,
        config: dict,
        region: str,
        navigation: NavigationHelper,
    ) -> dict:
        """Template Method: shared service configuration flow.

        Handles search -> configure -> region -> fill fields -> blur -> read cost -> save.
        Used by both create_estimate and update_estimate.

        Args:
            service_name: The AWS service name to configure.
            config: Dict of field_label -> value pairs.
            region: Region display name.
            navigation: The NavigationHelper instance.

        Returns:
            Dict with service_name, status, and monthly_cost.
        """
        page = self._browser_manager.page

        if not await navigation.search_and_configure(service_name):
            logger.warning(f"Could not find: {service_name}")
            return {"service_name": service_name, "status": "not_found"}

        # Select region
        region_selector = RegionSelector(page)
        await region_selector.select_region(region)
        await page.wait_for_timeout(2000)

        # Create field processor for this page state
        field_processor = FieldProcessor(page)

        # Process _radio first (must come after region change stabilizes)
        radio_value = config.get("_radio")
        if radio_value:
            logger.debug(f"  Page URL before radio: {page.url}")
            body = await page.locator("main").text_content()
            if str(radio_value) in body:
                logger.debug(f"  Radio text FOUND in page body")
            else:
                logger.debug(f"  Radio text NOT in page body. First 200: {body[:200]}")
            await field_processor.process_radio(str(radio_value))

        # Fill all config fields via the FieldProcessor
        for field_label, value in config.items():
            await field_processor.process_field(field_label, value)

        # Trigger recalculation: click description field to blur all, wait for price
        desc = page.locator('input[aria-label*="Description" i]')
        if await desc.count() > 0:
            await desc.first.click()
            await page.wait_for_timeout(500)
        await page.wait_for_timeout(3000)

        # Get cost before saving
        cost_reader = CostReader(page)
        cost = await cost_reader.get_current_cost()

        # Save service
        estimate_manager = EstimateManager(page)
        await estimate_manager.save_service()

        return {
            "service_name": service_name,
            "status": "added",
            "monthly_cost": cost,
        }

    async def create_estimate(self, services: list[dict]) -> dict:
        """Create an estimate with the given services and return the share link.

        Args:
            services: List of service configurations. Each should have:
                - service_name: Name to search in calculator
                - config: Dict of field_label -> value pairs
                - region: Optional region (default: US East (N. Virginia))

        Returns:
            Dict with estimate_url, monthly_cost, and services details.
        """
        await self._ensure_browser()
        page = self._browser_manager.page

        logger.info("Navigating to AWS Calculator...")
        await page.goto(f"{CALCULATOR_BASE_URL}/#/addService", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        navigation = NavigationHelper(page)
        await navigation.dismiss_cookies()

        results = []
        for svc in services:
            service_name = svc["service_name"]
            config = svc.get("config", {})
            region = svc.get("region", "US East (N. Virginia)")

            logger.info(f"Adding: {service_name}")
            result = await self._configure_service(service_name, config, region, navigation)
            results.append(result)

        # Get share link
        estimate_manager = EstimateManager(page)
        share_url = await estimate_manager.get_share_link()

        # Navigate to saved URL to get accurate total (includes all tiers/recalculation)
        if share_url and "calculator.aws" in share_url:
            await page.goto(share_url, wait_until="networkidle")
            await page.wait_for_timeout(5000)

        cost_reader = CostReader(page)
        final_cost = await cost_reader.get_total_cost()

        return {
            "estimate_url": share_url,
            "monthly_cost": final_cost,
            "services": results,
        }

    async def update_estimate(
        self,
        estimate_url: str,
        add_services: Optional[list[dict]] = None,
        remove_services: Optional[list[str]] = None,
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
        page = self._browser_manager.page

        # 1. Load existing estimate
        logger.info(f"Loading estimate: {estimate_url}")
        await page.goto(estimate_url, wait_until="networkidle")
        await page.wait_for_timeout(5000)

        navigation = NavigationHelper(page)
        await navigation.dismiss_cookies()

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
            await navigation.dismiss_cookies()

            for svc_name in remove_services:
                logger.info(f"  Removing: {svc_name}")
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
                result = await self._configure_service(
                    service_name, config, region, navigation
                )
                results.append(result)

        # 5. Generate new share link
        estimate_manager = EstimateManager(page)
        share_url = await estimate_manager.get_share_link()

        # 6. Navigate to the saved URL to get accurate total
        if share_url and "calculator.aws" in share_url:
            await page.goto(share_url, wait_until="networkidle")
            await page.wait_for_timeout(5000)

        cost_reader = CostReader(page)
        final_cost = await cost_reader.get_total_cost()

        return {
            "estimate_url": share_url,
            "monthly_cost": final_cost,
            "services_added": results,
            "services_removed": remove_services or [],
            "based_on": estimate_url,
        }
