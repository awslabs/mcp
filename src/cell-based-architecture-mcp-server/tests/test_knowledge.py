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
"""Tests for knowledge base functionality."""

import pytest

from awslabs.cell_based_architecture_mcp_server.knowledge import (
    CellBasedArchitectureKnowledge,
    WhitepaperSection,
)


class TestCellBasedArchitectureKnowledge:
    """Test CellBasedArchitectureKnowledge class."""

    def test_get_section_valid(self):
        """Test getting a valid section."""
        section = CellBasedArchitectureKnowledge.get_section("introduction")
        assert section is not None
        assert section.title == "Introduction to Cell-Based Architecture"
        assert "cell-based architecture" in section.content.lower()

    def test_get_section_invalid(self):
        """Test getting an invalid section."""
        section = CellBasedArchitectureKnowledge.get_section("nonexistent")
        assert section is None

    def test_get_sections_by_level_beginner(self):
        """Test getting beginner sections."""
        sections = CellBasedArchitectureKnowledge.get_sections_by_level("beginner")
        assert len(sections) > 0
        for section in sections:
            assert section.complexity_level == "beginner"

    def test_get_sections_by_level_expert(self):
        """Test getting expert sections."""
        sections = CellBasedArchitectureKnowledge.get_sections_by_level("expert")
        assert len(sections) > 0
        for section in sections:
            assert section.complexity_level == "expert"

    def test_get_related_sections(self):
        """Test getting related sections."""
        related = CellBasedArchitectureKnowledge.get_related_sections("introduction")
        assert len(related) > 0
        # Should include shared_responsibility and what_is_cell_based
        related_titles = [section.title for section in related]
        assert any("shared responsibility" in title.lower() for title in related_titles)

    def test_get_related_sections_invalid(self):
        """Test getting related sections for invalid section."""
        related = CellBasedArchitectureKnowledge.get_related_sections("nonexistent")
        assert related == []

    def test_all_sections_have_required_fields(self):
        """Test that all sections have required fields."""
        for section_name, section_data in CellBasedArchitectureKnowledge.WHITEPAPER_SECTIONS.items():
            section = WhitepaperSection(**section_data)
            assert section.title
            assert section.content
            assert section.complexity_level in ["beginner", "intermediate", "expert"]
            assert isinstance(section.subsections, list)
            assert isinstance(section.related_sections, list)

    def test_section_relationships_are_valid(self):
        """Test that section relationships reference valid sections."""
        for section_name, section_data in CellBasedArchitectureKnowledge.WHITEPAPER_SECTIONS.items():
            for related_name in section_data.get('related_sections', []):
                assert related_name in CellBasedArchitectureKnowledge.WHITEPAPER_SECTIONS, \
                    f"Section {section_name} references invalid related section {related_name}"


class TestWhitepaperSection:
    """Test WhitepaperSection model."""

    def test_valid_section(self):
        """Test valid section creation."""
        section = WhitepaperSection(
            title="Test Section",
            content="Test content",
            subsections=["sub1", "sub2"],
            related_sections=["related1"],
            complexity_level="intermediate"
        )
        assert section.title == "Test Section"
        assert section.content == "Test content"
        assert section.subsections == ["sub1", "sub2"]
        assert section.related_sections == ["related1"]
        assert section.complexity_level == "intermediate"

    def test_default_values(self):
        """Test default values."""
        section = WhitepaperSection(
            title="Test",
            content="Content"
        )
        assert section.subsections == []
        assert section.related_sections == []
        assert section.complexity_level == "intermediate"