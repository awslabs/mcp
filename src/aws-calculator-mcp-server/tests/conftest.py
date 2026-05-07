# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
"""Pytest configuration and fixtures for AWS Calculator BDD tests."""

import asyncio

import pytest

from awslabs.aws_calculator_mcp_server.calculator import AWSCalculatorAutomation


class CalculatorContext:
    """Holds shared state across BDD steps within a scenario."""

    def __init__(self):
        self.service_name: str = ""
        self.region: str = "US East (N. Virginia)"
        self.fields_filled: dict = {}
        self.service_added: bool = False
        self.estimate_url: str = ""
        self.error: str = ""


_calculator: AWSCalculatorAutomation = None


def run(coro):
    """Run async code from sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            raise RuntimeError("loop running")
        return loop.run_until_complete(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)


def get_calculator():
    """Get or create a shared calculator instance."""
    global _calculator
    if _calculator is None:
        _calculator = AWSCalculatorAutomation(headless=True)
        run(_calculator._ensure_browser())
    return _calculator


@pytest.fixture(scope="session", autouse=True)
def cleanup_calculator(request):
    """Close browser at end of session."""
    yield
    global _calculator
    if _calculator:
        run(_calculator.close())
        _calculator = None


@pytest.fixture
def calculator():
    """Provide the shared calculator instance."""
    return get_calculator()


@pytest.fixture
def ctx():
    """Provide a fresh context per scenario."""
    return CalculatorContext()
