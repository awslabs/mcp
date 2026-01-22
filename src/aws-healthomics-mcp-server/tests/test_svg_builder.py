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

"""Tests for SVGBuilder visualization utility."""

import pytest
import xml.etree.ElementTree as ET
from awslabs.aws_healthomics_mcp_server.visualization.svg_builder import SVGBuilder
from hypothesis import given, settings
from hypothesis import strategies as st


class TestSVGBuilderBasic:
    """Basic unit tests for SVGBuilder."""

    def test_init(self):
        """Test SVGBuilder initialization."""
        builder = SVGBuilder(800, 600)
        assert builder.width == 800
        assert builder.height == 600
        assert builder.elements == []
        assert builder.defs == []

    def test_add_title_default_position(self):
        """Test add_title with default x position (centered)."""
        builder = SVGBuilder(800, 600)
        builder.add_title('Test Title')
        assert len(builder.elements) == 1
        assert 'Test Title' in builder.elements[0]
        assert 'x="400"' in builder.elements[0]  # Centered at width/2

    def test_add_title_custom_position(self):
        """Test add_title with custom position."""
        builder = SVGBuilder(800, 600)
        builder.add_title('Test Title', x=100, y=50)
        assert len(builder.elements) == 1
        assert 'x="100"' in builder.elements[0]
        assert 'y="50"' in builder.elements[0]

    def test_add_rect_without_tooltip(self):
        """Test add_rect without tooltip."""
        builder = SVGBuilder(800, 600)
        builder.add_rect(10, 20, 100, 50, '#ff0000')
        assert len(builder.elements) == 1
        assert 'x="10.00"' in builder.elements[0]
        assert 'y="20.00"' in builder.elements[0]
        assert 'width="100.00"' in builder.elements[0]
        assert 'height="50.00"' in builder.elements[0]
        assert 'fill="#ff0000"' in builder.elements[0]
        assert '/>' in builder.elements[0]  # Self-closing tag

    def test_add_rect_with_tooltip(self):
        """Test add_rect with tooltip."""
        builder = SVGBuilder(800, 600)
        builder.add_rect(10, 20, 100, 50, '#ff0000', tooltip='Test tooltip')
        assert len(builder.elements) == 1
        assert '<title>Test tooltip</title>' in builder.elements[0]
        assert '</rect>' in builder.elements[0]

    def test_add_rect_minimum_width(self):
        """Test add_rect enforces minimum width."""
        builder = SVGBuilder(800, 600)
        builder.add_rect(10, 20, 0.1, 50, '#ff0000')
        assert 'width="0.50"' in builder.elements[0]  # Minimum width is 0.5

    def test_add_text(self):
        """Test add_text."""
        builder = SVGBuilder(800, 600)
        builder.add_text(100, 200, 'Test text', anchor='middle', font_size=12)
        assert len(builder.elements) == 1
        assert 'x="100.00"' in builder.elements[0]
        assert 'y="200.00"' in builder.elements[0]
        assert 'text-anchor="middle"' in builder.elements[0]
        assert 'font-size="12"' in builder.elements[0]
        assert 'Test text' in builder.elements[0]

    def test_add_line(self):
        """Test add_line."""
        builder = SVGBuilder(800, 600)
        builder.add_line(0, 0, 100, 100, stroke='#000', stroke_width=2)
        assert len(builder.elements) == 1
        assert 'x1="0.00"' in builder.elements[0]
        assert 'y1="0.00"' in builder.elements[0]
        assert 'x2="100.00"' in builder.elements[0]
        assert 'y2="100.00"' in builder.elements[0]
        assert 'stroke="#000"' in builder.elements[0]
        assert 'stroke-width="2"' in builder.elements[0]

    def test_add_x_axis(self):
        """Test add_x_axis."""
        builder = SVGBuilder(800, 600)
        margin = {'top': 60, 'right': 40, 'bottom': 40, 'left': 150}
        builder.add_x_axis(margin, 600, 10.0, 'hr', ticks=5)
        # Should have: 1 axis line + 6 tick lines + 6 tick labels + 1 axis label = 14 elements
        assert len(builder.elements) >= 14

    def test_escape_special_characters(self):
        """Test _escape method escapes XML special characters."""
        builder = SVGBuilder(800, 600)
        assert builder._escape('&') == '&amp;'
        assert builder._escape('<') == '&lt;'
        assert builder._escape('>') == '&gt;'
        assert builder._escape('"') == '&quot;'
        assert builder._escape("'") == '&#39;'
        assert (
            builder._escape('<test>&"value"</test>')
            == '&lt;test&gt;&amp;&quot;value&quot;&lt;/test&gt;'
        )

    def test_build_empty(self):
        """Test build with no elements."""
        builder = SVGBuilder(800, 600)
        svg = builder.build()
        assert svg.startswith('<svg')
        assert svg.endswith('</svg>')
        assert 'width="800"' in svg
        assert 'height="600"' in svg
        assert 'xmlns="http://www.w3.org/2000/svg"' in svg

    def test_build_with_elements(self):
        """Test build with multiple elements."""
        builder = SVGBuilder(800, 600)
        builder.add_title('Test Chart')
        builder.add_rect(10, 10, 100, 50, '#ff0000')
        builder.add_text(50, 100, 'Label')
        builder.add_line(0, 0, 100, 100)
        svg = builder.build()
        assert svg.startswith('<svg')
        assert svg.endswith('</svg>')
        assert 'Test Chart' in svg
        assert '<rect' in svg
        assert '<text' in svg
        assert '<line' in svg

    def test_build_includes_style(self):
        """Test build includes hover style."""
        builder = SVGBuilder(800, 600)
        svg = builder.build()
        assert '<style>rect:hover { opacity: 0.8; cursor: pointer; }</style>' in svg


class TestSVGBuilderPropertyBased:
    """Property-based tests for SVGBuilder using Hypothesis."""

    @given(
        width=st.integers(min_value=1, max_value=10000),
        height=st.integers(min_value=1, max_value=10000),
        title=st.text(min_size=0, max_size=100),
        num_rects=st.integers(min_value=0, max_value=20),
        num_texts=st.integers(min_value=0, max_value=20),
        num_lines=st.integers(min_value=0, max_value=20),
    )
    @settings(max_examples=100)
    def test_property_valid_svg_output(
        self,
        width: int,
        height: int,
        title: str,
        num_rects: int,
        num_texts: int,
        num_lines: int,
    ):
        """Property 6: Valid SVG Output.

        For any set of elements added to SVGBuilder, the generated output
        SHALL be a well-formed SVG document (starts with `<svg`, ends with
        `</svg>`, contains no unescaped special characters, and is valid XML).

        **Validates: Requirements 5.1, 5.7, 8.3**
        **Feature: run-analyzer-enhancement, Property 6: Valid SVG Output**
        """
        builder = SVGBuilder(width, height)

        # Add title if non-empty
        if title:
            builder.add_title(title)

        # Add random rectangles
        for i in range(num_rects):
            builder.add_rect(
                x=float(i * 10),
                y=float(i * 5),
                width=50.0,
                height=20.0,
                fill='#ff0000',
                tooltip=f'Rect {i}' if i % 2 == 0 else None,
            )

        # Add random text elements
        for i in range(num_texts):
            builder.add_text(
                x=float(i * 20),
                y=float(i * 10),
                text=f'Text {i}',
                anchor='start',
                font_size=10,
            )

        # Add random lines
        for i in range(num_lines):
            builder.add_line(
                x1=float(i * 5),
                y1=float(i * 5),
                x2=float(i * 10),
                y2=float(i * 10),
            )

        svg = builder.build()

        # Property: SVG starts with <svg
        assert svg.startswith('<svg'), 'SVG must start with <svg'

        # Property: SVG ends with </svg>
        assert svg.endswith('</svg>'), 'SVG must end with </svg>'

        # Property: SVG contains required attributes
        assert 'xmlns="http://www.w3.org/2000/svg"' in svg, 'SVG must have xmlns attribute'
        assert f'width="{width}"' in svg, 'SVG must have correct width'
        assert f'height="{height}"' in svg, 'SVG must have correct height'

        # Property: SVG is well-formed XML (can be parsed)
        try:
            ET.fromstring(svg)
        except ET.ParseError as e:
            pytest.fail(f'SVG is not well-formed XML: {e}')

    @given(text=st.text(min_size=0, max_size=200))
    @settings(max_examples=100)
    def test_property_escape_produces_valid_xml(self, text: str):
        """Property: Escaped text produces valid XML.

        For any input text, the escaped output should be safe for XML inclusion.

        **Validates: Requirements 8.3**
        **Feature: run-analyzer-enhancement, Property 6: Valid SVG Output (escape component)**
        """
        builder = SVGBuilder(100, 100)

        # Property: No unescaped special characters
        # After escaping, the text should not contain raw &, <, >, ", '
        # except as part of escape sequences
        # We verify by checking the escaped text can be used in XML

        # Create a minimal SVG with the escaped text
        builder.add_text(0, 0, text)  # add_text calls _escape internally
        svg = builder.build()

        # Property: The resulting SVG should be parseable XML
        try:
            ET.fromstring(svg)
        except ET.ParseError as e:
            pytest.fail(f'SVG with escaped text is not valid XML: {e}')

    @given(
        width=st.integers(min_value=100, max_value=2000),
        height=st.integers(min_value=100, max_value=2000),
        max_value=st.floats(min_value=0.1, max_value=1000.0, allow_nan=False),
        ticks=st.integers(min_value=1, max_value=20),
    )
    @settings(max_examples=100)
    def test_property_x_axis_produces_valid_svg(
        self,
        width: int,
        height: int,
        max_value: float,
        ticks: int,
    ):
        """Property: X-axis rendering produces valid SVG.

        For any valid axis parameters, the resulting SVG should be well-formed.

        **Validates: Requirements 8.2, 8.3**
        **Feature: run-analyzer-enhancement, Property 6: Valid SVG Output (axis component)**
        """
        builder = SVGBuilder(width, height)
        margin = {'top': 60, 'right': 40, 'bottom': 40, 'left': 150}
        chart_width = width - margin['left'] - margin['right']

        if chart_width > 0:
            builder.add_x_axis(margin, chart_width, max_value, 'hr', ticks=ticks)

        svg = builder.build()

        # Property: SVG is well-formed
        assert svg.startswith('<svg')
        assert svg.endswith('</svg>')

        # Property: SVG is valid XML
        try:
            ET.fromstring(svg)
        except ET.ParseError as e:
            pytest.fail(f'SVG with x-axis is not valid XML: {e}')
