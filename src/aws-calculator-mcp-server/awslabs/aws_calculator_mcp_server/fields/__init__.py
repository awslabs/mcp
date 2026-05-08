"""Field processing using Strategy and Chain of Responsibility patterns.

This package provides:
- FieldHandler: Abstract base for all field-handling strategies.
- FieldProcessor: Dispatches field labels to the correct handler strategy,
  and uses a fallback chain for unrecognized fields.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from loguru import logger
from playwright.async_api import Page

from .input_handler import NumberFieldHandler, TextFieldHandler
from .dropdown_handler import (
    DropdownHandler,
    ChangeDropdownHandler,
    CloudscapeDropdownHandler,
)
from .autosuggest_handler import AutosuggestHandler
from .radio_handler import RadioHandler
from .positional_handler import (
    PositionalDropdownHandler,
    PositionalInputHandler,
    UnitHandler,
)


class FieldHandler(ABC):
    """Abstract base class for field-handling strategies (Strategy pattern).

    Each concrete handler knows how to fill a specific type of calculator field.
    """

    def __init__(self, page: Page) -> None:
        """Initialize with a Playwright page.

        Args:
            page: Active Playwright Page instance.
        """
        self._page = page

    @abstractmethod
    async def handle(self, field_label: str, value: str) -> bool:
        """Attempt to handle the given field.

        Args:
            field_label: The field identifier (may include prefix).
            value: The value to set.

        Returns:
            True if the field was successfully handled.
        """
        ...


class FieldProcessor:
    """Dispatches field labels to the correct handler strategy.

    Uses prefix-based routing for special fields and a Chain of Responsibility
    fallback for generic fields (number -> text -> dropdown -> cloudscape).

    Args:
        page: The Playwright Page instance for all handlers.
    """

    def __init__(self, page: Page) -> None:
        """Initialize handlers for the given page.

        Args:
            page: Active Playwright Page instance.
        """
        self._page = page

        # Instantiate all strategy handlers
        self._number_handler = NumberFieldHandler(page)
        self._text_handler = TextFieldHandler(page)
        self._dropdown_handler = DropdownHandler(page)
        self._cloudscape_dropdown_handler = CloudscapeDropdownHandler(page)
        self._change_dropdown_handler = ChangeDropdownHandler(page)
        self._autosuggest_handler = AutosuggestHandler(page)
        self._radio_handler = RadioHandler(page)
        self._positional_dropdown_handler = PositionalDropdownHandler(page)
        self._positional_input_handler = PositionalInputHandler(page)
        self._unit_handler = UnitHandler(page)

        # Fallback chain: try these in order for generic fields
        self._fallback_chain: list[FieldHandler] = [
            self._number_handler,
            self._text_handler,
            self._dropdown_handler,
            self._cloudscape_dropdown_handler,
        ]

    async def process_radio(self, value: str) -> bool:
        """Process a radio button selection.

        Args:
            value: The radio button label text to click.

        Returns:
            True if the radio was clicked.
        """
        return await self._radio_handler.handle("_radio", value)

    async def process_field(self, field_label: str, value: str) -> bool:
        """Route a field to the appropriate handler based on its prefix.

        Args:
            field_label: The field identifier, possibly with a special prefix.
            value: The value to set.

        Returns:
            True if the field was successfully handled.
        """
        str_value = str(value)

        # Skip _radio — handled separately via process_radio
        if field_label == "_radio":
            return True

        # _unit suffix: set unit dropdown for a field
        if field_label.endswith("_unit"):
            parent_field = field_label[:-5]
            return await self._unit_handler.handle(parent_field, str_value)

        # _change:current_text — change dropdown by visible text
        if field_label.startswith("_change:"):
            current_text = field_label[8:]
            return await self._change_dropdown_handler.handle(current_text, str_value)

        # _select_cloudscape:label — select cloudscape dropdown by label
        if field_label.startswith("_select_cloudscape:"):
            label = field_label[19:]
            return await self._cloudscape_dropdown_handler.handle(label, str_value)

        # _nth_dropdown:N:text — positional dropdown
        if field_label.startswith("_nth_dropdown:"):
            return await self._positional_dropdown_handler.handle(field_label, str_value)

        # _nth_input:N:pattern — positional input
        if field_label.startswith("_nth_input:"):
            return await self._positional_input_handler.handle(field_label, str_value)

        # _autosuggest:placeholder — autosuggest component
        if field_label.startswith("_autosuggest:"):
            placeholder = field_label[13:]
            return await self._autosuggest_handler.handle(placeholder, str_value)

        # Generic field: try fallback chain (Chain of Responsibility)
        for handler in self._fallback_chain:
            if await handler.handle(field_label, str_value):
                return True

        # Last resort for short values: try change_dropdown_by_current_text
        if len(str_value) <= 2:
            if await self._change_dropdown_handler.handle(field_label, str_value):
                return True

        logger.debug(f"  Could not set: {field_label} = {value}")
        return False


__all__ = [
    "FieldHandler",
    "FieldProcessor",
    "NumberFieldHandler",
    "TextFieldHandler",
    "DropdownHandler",
    "ChangeDropdownHandler",
    "CloudscapeDropdownHandler",
    "AutosuggestHandler",
    "RadioHandler",
    "PositionalDropdownHandler",
    "PositionalInputHandler",
    "UnitHandler",
]
