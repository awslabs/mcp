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
    without external dependencies. It generates standalone SVG output
    that does not require external JavaScript libraries.
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
        x = x if x is not None else self.width // 2
        self.elements.append(
            f'<text x="{x}" y="{y}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="14" font-weight="bold">'
            f'{self._escape(text)}</text>'
        )

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
        # Ensure minimum width for visibility
        rect_width = max(0.5, width)
        rect = (
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{rect_width:.2f}" '
            f'height="{height:.2f}" fill="{fill}"'
        )
        if tooltip:
            rect += f'><title>{self._escape(tooltip)}</title></rect>'
        else:
            rect += '/>'
        self.elements.append(rect)

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
        self.elements.append(
            f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="{anchor}" '
            f'font-family="sans-serif" font-size="{font_size}" '
            f'dominant-baseline="middle">{self._escape(text)}</text>'
        )

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
        self.elements.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{stroke}" stroke-width="{stroke_width}"/>'
        )

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
        y = self.height - margin['bottom']

        # Axis line
        self.add_line(margin['left'], y, margin['left'] + chart_width, y)

        # Ticks and labels
        for i in range(ticks + 1):
            x = margin['left'] + (i / ticks) * chart_width
            value = (i / ticks) * max_value

            # Tick mark
            self.add_line(x, y, x, y + 5)
            # Tick label
            self.add_text(x, y + 15, f'{value:.1f}', anchor='middle', font_size=9)

        # Axis label
        self.add_text(
            margin['left'] + chart_width / 2,
            self.height - 10,
            f'Time ({unit})',
            anchor='middle',
            font_size=11,
        )

    def _escape(self, text: str) -> str:
        """Escape special XML characters and remove invalid control characters.

        Args:
            text: Text to escape

        Returns:
            Escaped text safe for XML
        """
        # First, remove invalid XML control characters (0x00-0x08, 0x0B, 0x0C, 0x0E-0x1F)
        # Valid XML 1.0 characters: #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD]
        cleaned = ''.join(
            char
            for char in text
            if char in '\t\n\r'
            or (ord(char) >= 0x20 and ord(char) <= 0xD7FF)
            or (ord(char) >= 0xE000 and ord(char) <= 0xFFFD)
        )

        # Then escape XML special characters
        return (
            cleaned.replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;')
        )

    def build(self) -> str:
        """Build final SVG string.

        Returns:
            Complete SVG document as string
        """
        svg_parts = [
            f'<svg width="{self.width}" height="{self.height}" '
            f'xmlns="http://www.w3.org/2000/svg">',
            '<style>rect:hover { opacity: 0.8; cursor: pointer; }</style>',
        ]

        if self.defs:
            svg_parts.append('<defs>')
            svg_parts.extend(self.defs)
            svg_parts.append('</defs>')

        svg_parts.extend(self.elements)
        svg_parts.append('</svg>')

        return '\n'.join(svg_parts)
