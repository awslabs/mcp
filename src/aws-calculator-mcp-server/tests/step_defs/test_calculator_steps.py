# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
"""Step definitions for AWS Calculator BDD certification tests."""

from pytest_bdd import given, when, then, parsers, scenarios

from tests.conftest import run, get_calculator

scenarios("../features/calculator_services.feature")


# --- Background ---

@given("the AWS Calculator browser is initialized")
def browser_initialized(calculator):
    """Ensure browser is ready."""
    assert calculator._browser is not None


@given("the calculator is at the add service page")
def at_add_service_page(calculator):
    """Navigate to add service (handled by search step)."""
    pass


# --- Given ---

@given(parsers.parse('I search for "{service_name}"'))
def search_for_service(calculator, ctx, service_name):
    """Search for a service in the calculator."""
    ctx.service_name = service_name
    page = calculator._page
    run(page.goto("https://calculator.aws/#/addService", wait_until="networkidle"))
    run(page.wait_for_timeout(2000))
    run(calculator._dismiss_cookies())
    search = page.locator('input[type="search"]')
    run(search.first.fill(service_name))
    run(page.wait_for_timeout(2000))


@given("I click Configure")
def click_configure(calculator, ctx):
    """Click Configure button for the searched service."""
    page = calculator._page
    btn = page.locator(f'button[aria-label*="Configure {ctx.service_name}"]')
    if run(btn.count()) == 0:
        btn = page.locator('button:has-text("Configure")')
    assert run(btn.count()) > 0, f"No Configure button for {ctx.service_name}"
    run(btn.first.click())
    run(page.wait_for_timeout(3000))
    run(calculator._dismiss_cookies())
    run(calculator._expand_all_sections())


# --- When ---

@when(parsers.parse('I set the region to "{region}"'))
def set_region(calculator, ctx, region):
    """Set the AWS region."""
    ctx.region = region
    run(calculator._select_region(region))


@when(parsers.parse('I fill "{field_label}" with "{value}"'))
def fill_field(calculator, ctx, field_label, value):
    """Fill a numeric or text field."""
    filled = run(calculator._fill_number_field(field_label, value))
    if not filled:
        filled = run(calculator._fill_text_field(field_label, value))
    if not filled:
        filled = run(calculator._select_cloudscape_dropdown(field_label, value))
    ctx.fields_filled[field_label] = filled


@when(parsers.parse('I select "{value}" via autosuggest for "{placeholder}"'))
def fill_autosuggest(calculator, ctx, value, placeholder):
    """Fill an autosuggest field (e.g., instance type)."""
    filled = run(calculator._fill_autosuggest(placeholder, value))
    ctx.fields_filled[f"autosuggest:{placeholder}"] = filled


@when(parsers.parse('I select "{value}" from dropdown "{label}"'))
def select_dropdown(calculator, ctx, value, label):
    """Select a value from a Cloudscape dropdown."""
    selected = run(calculator._select_cloudscape_dropdown(label, value))
    ctx.fields_filled[f"dropdown:{label}={value}"] = selected


@when(parsers.parse('I select "{value}" via radio button'))
def click_radio(calculator, ctx, value):
    """Click a radio button by label text."""
    clicked = run(calculator._click_radio(value))
    ctx.fields_filled[f"radio:{value}"] = clicked


@when("I click Save and add service")
def click_save(calculator, ctx):
    """Save the service to the estimate."""
    try:
        run(calculator._page.wait_for_timeout(1000))
        run(calculator._save_service())
        ctx.service_added = True
    except Exception as e:
        ctx.error = str(e)
        ctx.service_added = False


# --- Then ---

@then(parsers.parse('the service "{service_name}" should be added successfully'))
def service_added(ctx, service_name):
    """Verify service was added."""
    assert ctx.service_added, f"Service '{service_name}' not added. Error: {ctx.error}"


@then("a shareable estimate URL should be generated")
def estimate_url_generated(calculator, ctx):
    """Verify a shareable URL is generated."""
    url = run(calculator._get_share_link())
    ctx.estimate_url = url
    assert url and "calculator.aws" in url, f"No valid URL. Got: {url}"
