"""Local integration test for selector-scoped snapshots against a real browser.

Launches a local Chromium browser via Playwright, loads test HTML, and
exercises SnapshotManager.capture() with various selectors to verify that
CDP queryAXTree scoping works on real pages.

Run with:
    uv run pytest tests/test_local_snapshot_scoping.py -v -m local_browser -s

Requires: playwright chromium installed (uv run playwright install chromium)
"""

import pytest
from playwright.async_api import async_playwright
from awslabs.amazon_bedrock_agentcore_browser_mcp_server.browser.snapshot_manager import (
    SnapshotManager,
)


TEST_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Snapshot Scoping Test</title></head>
<body>
  <header>
    <nav aria-label="Main navigation">
      <a href="/home">Home</a>
      <a href="/about">About</a>
      <a href="/contact">Contact</a>
    </nav>
  </header>
  <main id="content">
    <h1>Welcome</h1>
    <p>This is the main content area.</p>
    <form aria-label="Search form">
      <input type="text" aria-label="Search query" />
      <button type="submit">Search</button>
    </form>
    <section id="results">
      <h2>Results</h2>
      <ul>
        <li><a href="/item1">Item 1</a></li>
        <li><a href="/item2">Item 2</a></li>
        <li><a href="/item3">Item 3</a></li>
      </ul>
    </section>
  </main>
  <footer>
    <p>Footer content</p>
    <a href="/privacy">Privacy Policy</a>
    <a href="/terms">Terms of Service</a>
  </footer>
</body>
</html>
"""

pytestmark = pytest.mark.local_browser


@pytest.fixture
async def browser_page():
    """Launch a local Chromium, load test HTML, and yield (page, snapshot_manager)."""
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True)
    context = await browser.new_context()
    page = await context.new_page()
    await page.set_content(TEST_PAGE_HTML)
    await page.wait_for_load_state("domcontentloaded")

    yield page, SnapshotManager()

    await browser.close()
    await pw.stop()


class TestSelectorScopingLive:
    """Verify queryAXTree scoping against a real Chromium browser."""

    async def test_full_page_snapshot(self, browser_page):
        """No selector returns the entire page."""
        page, sm = browser_page
        result = await sm.capture(page, "local-test")

        assert "Home" in result
        assert "About" in result
        assert "Welcome" in result
        assert "Search" in result
        assert "Item 1" in result
        assert "Privacy Policy" in result
        assert "Warning" not in result
        print(f"\n--- Full page snapshot ({len(result)} chars) ---")
        print(result)

    async def test_selector_scopes_to_main(self, browser_page):
        """selector='main' returns only the main content subtree."""
        page, sm = browser_page
        result = await sm.capture(page, "local-main", selector="main")

        # Main content should be present
        assert "Welcome" in result
        assert "Search" in result
        assert "Item 1" in result

        # Nav and footer should be excluded
        assert "Warning" not in result, f"Got unexpected warning: {result[:200]}"
        assert "Home" not in result, "Nav link 'Home' should be excluded from main scope"
        assert "About" not in result, "Nav link 'About' should be excluded from main scope"
        assert "Privacy Policy" not in result, "Footer link should be excluded from main scope"
        print(f"\n--- Scoped to main ({len(result)} chars) ---")
        print(result)

    async def test_selector_scopes_to_footer(self, browser_page):
        """selector='footer' returns only the footer subtree."""
        page, sm = browser_page
        result = await sm.capture(page, "local-footer", selector="footer")

        assert "Privacy Policy" in result
        assert "Terms of Service" in result

        assert "Warning" not in result, f"Got unexpected warning: {result[:200]}"
        assert "Welcome" not in result, "Main heading should be excluded from footer scope"
        assert "Home" not in result, "Nav link should be excluded from footer scope"
        assert "Search" not in result, "Search form should be excluded from footer scope"
        print(f"\n--- Scoped to footer ({len(result)} chars) ---")
        print(result)

    async def test_selector_scopes_to_section_by_id(self, browser_page):
        """selector='#results' returns only the results section."""
        page, sm = browser_page
        result = await sm.capture(page, "local-results", selector="#results")

        assert "Item 1" in result
        assert "Item 2" in result
        assert "Item 3" in result

        assert "Warning" not in result
        assert "Welcome" not in result, "Main heading should be excluded from #results scope"
        assert "Search" not in result, "Search form should be excluded from #results scope"
        print(f"\n--- Scoped to #results ({len(result)} chars) ---")
        print(result)

    async def test_selector_scopes_to_nav(self, browser_page):
        """selector='nav' returns only the navigation subtree."""
        page, sm = browser_page
        result = await sm.capture(page, "local-nav", selector="nav")

        assert "Home" in result
        assert "About" in result
        assert "Contact" in result

        assert "Warning" not in result
        assert "Welcome" not in result
        assert "Item 1" not in result
        assert "Privacy Policy" not in result
        print(f"\n--- Scoped to nav ({len(result)} chars) ---")
        print(result)

    async def test_nonexistent_selector_falls_back(self, browser_page):
        """selector='#nonexistent' falls back to full page with warning."""
        page, sm = browser_page
        result = await sm.capture(page, "local-missing", selector="#nonexistent")

        assert "Warning" in result
        assert "#nonexistent" in result
        # Full page content should be present as fallback
        assert "Home" in result
        assert "Welcome" in result
        print(f"\n--- Nonexistent selector ({len(result)} chars) ---")
        print(result[:300])

    async def test_selector_form_scope(self, browser_page):
        """selector='form' scopes to just the search form."""
        page, sm = browser_page
        result = await sm.capture(page, "local-form", selector="form")

        assert "Search" in result

        assert "Warning" not in result
        assert "Home" not in result
        assert "Item 1" not in result
        assert "Privacy Policy" not in result
        print(f"\n--- Scoped to form ({len(result)} chars) ---")
        print(result)
