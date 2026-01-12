# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Lightweight SVG generation utility for chart visualization."""

from typing import Optional


class SVGBuilder:
    """Builds SVG documents for chart visualization.

    This class provides a simple API for constructing SVG elements
    without external dependencies.
    """

    def __init__(self, width: int, height: int):
        """Initialize SVG builder.

        Args:
            width: SVG canvas width in pixels
            height: SVG canvas height in pixels
        """
        self.width = width
        self.height = height
        self.elements: list[str] = []
        self.defs: list[str] = []

    def add_title(self, text: str, x: Optional[int] = None, y: int = 30) -> None:
        """Add title text to SVG.

        Args:
            text: Title text
            x: X position (defaults to center)
            y: Y position
        """
        # Stub implementation - will be completed in Task 8
        raise NotImplementedError('SVGBuilder.add_title will be implemented in Task 8')

    def add_rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        fill: str,
        tooltip: Optional[str] = None,
    ) -> None:
        """Add rectangle element with optional tooltip.

        Args:
            x: X position
            y: Y position
            width: Rectangle width
            height: Rectangle height
            fill: Fill color
            tooltip: Optional tooltip text
        """
        # Stub implementation - will be completed in Task 8
        raise NotImplementedError('SVGBuilder.add_rect will be implemented in Task 8')

    def add_text(
        self,
        x: float,
        y: float,
        text: str,
        anchor: str = 'start',
        font_size: int = 10,
    ) -> None:
        """Add text element.

        Args:
            x: X position
            y: Y position
            text: Text content
            anchor: Text anchor (start, middle, end)
            font_size: Font size in pixels
        """
        # Stub implementation - will be completed in Task 8
        raise NotImplementedError('SVGBuilder.add_text will be implemented in Task 8')

    def add_line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        stroke: str = '#000',
        stroke_width: float = 1,
    ) -> None:
        """Add line element.

        Args:
            x1: Start X position
            y1: Start Y position
            x2: End X position
            y2: End Y position
            stroke: Stroke color
            stroke_width: Stroke width
        """
        # Stub implementation - will be completed in Task 8
        raise NotImplementedError('SVGBuilder.add_line will be implemented in Task 8')

    def add_x_axis(
        self,
        margin: dict,
        chart_width: float,
        max_value: float,
        unit: str,
        ticks: int = 10,
    ) -> None:
        """Add X axis with ticks and labels.

        Args:
            margin: Margin dictionary with top, right, bottom, left
            chart_width: Width of chart area
            max_value: Maximum axis value
            unit: Time unit label
            ticks: Number of tick marks
        """
        # Stub implementation - will be completed in Task 8
        raise NotImplementedError('SVGBuilder.add_x_axis will be implemented in Task 8')

    def _escape(self, text: str) -> str:
        """Escape special XML characters.

        Args:
            text: Text to escape

        Returns:
            Escaped text safe for XML
        """
        # Stub implementation - will be completed in Task 8
        raise NotImplementedError('SVGBuilder._escape will be implemented in Task 8')

    def build(self) -> str:
        """Build final SVG string.

        Returns:
            Complete SVG document as string
        """
        # Stub implementation - will be completed in Task 8
        raise NotImplementedError('SVGBuilder.build will be implemented in Task 8')
