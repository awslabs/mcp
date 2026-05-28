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

from datetime import datetime
from pathlib import Path

from awslabs.cell_based_architecture_mcp_server.knowledge import (
    CellBasedArchitectureKnowledge,
    KnowledgeContent,
    MarkdownKnowledgeLoader,
    WhitepaperSection,
)


class TestCellBasedArchitectureKnowledge:
    """Test CellBasedArchitectureKnowledge class."""

    def test_get_section_valid(self):
        """Test getting a valid section."""
        section = CellBasedArchitectureKnowledge.get_section('introduction')
        assert section is not None
        assert section.title == 'Introduction to Cell-Based Architecture'
        assert 'cell-based architecture' in section.content.lower()

    def test_get_section_invalid(self):
        """Test getting an invalid section."""
        section = CellBasedArchitectureKnowledge.get_section('nonexistent')
        assert section is None

    def test_get_sections_by_level_beginner(self):
        """Test getting beginner sections."""
        sections = CellBasedArchitectureKnowledge.get_sections_by_level('beginner')
        assert len(sections) > 0
        for section in sections:
            assert section.complexity_level == 'beginner'

    def test_get_sections_by_level_expert(self):
        """Test getting expert sections."""
        sections = CellBasedArchitectureKnowledge.get_sections_by_level('expert')
        assert len(sections) > 0
        for section in sections:
            assert section.complexity_level == 'expert'

    def test_get_related_sections(self):
        """Test getting related sections."""
        related = CellBasedArchitectureKnowledge.get_related_sections('introduction')
        assert len(related) > 0
        # Should include shared_responsibility and what_is_cell_based
        related_titles = [section.title for section in related]
        assert any('shared responsibility' in title.lower() for title in related_titles)

    def test_get_related_sections_invalid(self):
        """Test getting related sections for invalid section."""
        related = CellBasedArchitectureKnowledge.get_related_sections('nonexistent')
        assert related == []

    def test_all_sections_have_required_fields(self):
        """Test that all sections have required fields."""
        for (
            _section_name,
            section_data,
        ) in CellBasedArchitectureKnowledge.WHITEPAPER_SECTIONS.items():
            section = WhitepaperSection(**section_data)
            assert section.title
            assert section.content
            assert section.complexity_level in ['beginner', 'intermediate', 'expert']
            assert isinstance(section.subsections, list)
            assert isinstance(section.related_sections, list)

    def test_section_relationships_are_valid(self):
        """Test that section relationships reference valid sections."""
        for (
            section_name,
            section_data,
        ) in CellBasedArchitectureKnowledge.WHITEPAPER_SECTIONS.items():
            for related_name in section_data.get('related_sections', []):
                assert related_name in CellBasedArchitectureKnowledge.WHITEPAPER_SECTIONS, (
                    f'Section {section_name} references invalid related section {related_name}'
                )


class TestWhitepaperSection:
    """Test WhitepaperSection model."""

    def test_valid_section(self):
        """Test valid section creation."""
        section = WhitepaperSection(
            title='Test Section',
            content='Test content',
            subsections=['sub1', 'sub2'],
            related_sections=['related1'],
            complexity_level='intermediate',
        )
        assert section.title == 'Test Section'
        assert section.content == 'Test content'
        assert section.subsections == ['sub1', 'sub2']
        assert section.related_sections == ['related1']
        assert section.complexity_level == 'intermediate'

    def test_default_values(self):
        """Test default values."""
        section = WhitepaperSection(title='Test', content='Content')
        assert section.subsections == []
        assert section.related_sections == []
        assert section.complexity_level == 'intermediate'


class TestMarkdownKnowledgeLoader:
    """Tests for the markdown knowledge loader backing the knowledge facade."""

    @staticmethod
    def _build_tree(tmp_path: Path) -> Path:
        """Create a small but realistic knowledge tree on disk."""
        root = tmp_path / 'knowledge'
        (root / 'basics').mkdir(parents=True)
        (root / 'implementation').mkdir(parents=True)
        (root / 'aws-services').mkdir(parents=True)

        (root / 'basics' / 'intro.md').write_text(
            '<!-- tags: cell, isolation -->\n'
            '# Introduction\n\nCell-based architecture is a pattern about isolation.\n'
        )
        (root / 'implementation' / 'design.md').write_text(
            '# Cell Design\n\nLambda and DynamoDB are a good starting point.\n'
        )
        (root / 'aws-services' / 'api-gateway.md').write_text(
            '# API Gateway\n\n'
            'Use AWS API Gateway for routing cells. Security and monitoring apply.\n'
        )
        return root

    def test_loader_discovers_and_indexes_content(self, tmp_path):
        """Loader should index every markdown file by category and tag."""
        root = self._build_tree(tmp_path)
        loader = MarkdownKnowledgeLoader(root)

        # Three markdown files should be loaded.
        assert len(loader.content_cache) == 3
        # Categories should be exposed.
        assert set(loader.get_categories()) == {'basics', 'implementation', 'aws-services'}
        # Implicit + explicit tags are aggregated.
        tags = set(loader.get_tags())
        assert {'cell', 'isolation', 'aws', 'lambda', 'dynamodb', 'api-gateway'} <= tags

    def test_get_content_by_path_returns_expected_item(self, tmp_path):
        """Loader should return the exact piece of content for a known path."""
        root = self._build_tree(tmp_path)
        loader = MarkdownKnowledgeLoader(root)

        item = loader.get_content_by_path('basics/intro.md')
        assert item is not None
        assert item.title == 'Introduction'
        assert item.category == 'basics'
        assert loader.get_content_by_path('basics/does-not-exist.md') is None

    def test_get_content_by_category_filters(self, tmp_path):
        """``get_content_by_category`` filters by category (and optional subcategory)."""
        root = self._build_tree(tmp_path)
        loader = MarkdownKnowledgeLoader(root)

        items = loader.get_content_by_category('basics')
        assert len(items) == 1
        assert items[0].title == 'Introduction'
        # Non-existent category yields nothing.
        assert loader.get_content_by_category('does-not-exist') == []
        # Subcategory filter that doesn't match returns nothing.
        assert loader.get_content_by_category('basics', subcategory='nope') == []

    def test_search_content_matches_title_and_body(self, tmp_path):
        """``search_content`` searches both title and body, case-insensitively."""
        root = self._build_tree(tmp_path)
        loader = MarkdownKnowledgeLoader(root)

        # Title match.
        assert len(loader.search_content('Introduction')) == 1
        # Body match.
        assert len(loader.search_content('dynamodb')) == 1
        # No match.
        assert loader.search_content('no-such-word') == []

    def test_search_content_respects_category_and_tag_filters(self, tmp_path):
        """``search_content`` applies category and tag filters before matching."""
        root = self._build_tree(tmp_path)
        loader = MarkdownKnowledgeLoader(root)

        # Category filter excludes other categories even if text matches.
        assert loader.search_content('lambda', category='basics') == []
        assert len(loader.search_content('lambda', category='implementation')) == 1
        # Tag filter restricts to items with any of the tags.
        assert loader.search_content('api gateway', tags=['nonexistent']) == []
        assert len(loader.search_content('api gateway', tags=['api-gateway'])) == 1

    def test_summary_and_reload(self, tmp_path):
        """Summary exposes counts, and ``reload_content`` picks up new files."""
        root = self._build_tree(tmp_path)
        loader = MarkdownKnowledgeLoader(root)

        summary = loader.get_content_summary()
        assert summary['total_files'] == 3
        assert 'basics' in summary['categories']
        assert isinstance(summary['last_updated'], datetime)

        # Add a new file and reload.
        (root / 'basics' / 'extra.md').write_text('# Extra\n\nMore isolation content.\n')
        loader.reload_content()
        assert loader.get_content_summary()['total_files'] == 4

    def test_loader_with_missing_directory_returns_empty(self, tmp_path):
        """A loader pointed at a non-existent path returns an empty summary."""
        loader = MarkdownKnowledgeLoader(tmp_path / 'missing')
        assert loader.content_cache == {}
        assert loader.get_categories() == []
        assert loader.get_tags() == []
        summary = loader.get_content_summary()
        assert summary['total_files'] == 0
        assert summary['last_updated'] is None


class TestKnowledgeContent:
    """Sanity tests for the KnowledgeContent dataclass."""

    def test_dataclass_fields_roundtrip(self):
        """KnowledgeContent stores the values it is constructed with."""
        now = datetime.now()
        kc = KnowledgeContent(
            file_path='basics/intro.md',
            title='Intro',
            content='body',
            category='basics',
            subcategory='',
            tags=['aws'],
            last_modified=now,
        )
        assert kc.file_path == 'basics/intro.md'
        assert kc.category == 'basics'
        assert kc.tags == ['aws']
        assert kc.last_modified is now


class TestHighLevelOperations:
    """Tests for the high-level operations on CellBasedArchitectureKnowledge."""

    def test_get_concept_explanation_scoped_to_section(self):
        """A section-scoped concept query returns that section's content."""
        knowledge = CellBasedArchitectureKnowledge()
        response = knowledge.get_concept_explanation(
            'cell isolation',
            detail_level='intermediate',
            whitepaper_section='cell_design',
        )
        assert 'Cell Design' in response
        assert 'cell isolation' in response.lower()

    def test_get_concept_explanation_beginner(self):
        """Beginner-level explanation mentions the concept and basic framing."""
        knowledge = CellBasedArchitectureKnowledge()
        response = knowledge.get_concept_explanation('fault tolerance', 'beginner')
        assert 'Fault Tolerance' in response
        assert 'beginner' in response.lower()

    def test_get_concept_explanation_expert(self):
        """Expert-level explanation includes advanced framing."""
        knowledge = CellBasedArchitectureKnowledge()
        response = knowledge.get_concept_explanation('cell sizing', 'expert')
        assert 'Cell Sizing' in response
        assert 'expert' in response.lower() or 'advanced' in response.lower()

    def test_get_implementation_guidance_includes_services(self):
        """Guidance includes an AWS services block when services are provided."""
        knowledge = CellBasedArchitectureKnowledge()
        response = knowledge.get_implementation_guidance(
            'implementation',
            aws_services=['lambda', 'dynamodb'],
            experience_level='intermediate',
        )
        assert 'Implementation' in response
        assert 'LAMBDA' in response
        assert 'DYNAMODB' in response

    def test_get_implementation_guidance_without_services(self):
        """Guidance is still produced when no services are specified."""
        knowledge = CellBasedArchitectureKnowledge()
        response = knowledge.get_implementation_guidance(
            'planning',
            aws_services=None,
            experience_level='beginner',
        )
        assert 'Planning' in response
        assert 'AWS Services Integration' not in response

    def test_analyze_architecture_design_detects_anti_pattern(self):
        """Shared-database mentions are flagged as a possible anti-pattern."""
        knowledge = CellBasedArchitectureKnowledge()
        report = knowledge.analyze_architecture_design(
            'My system uses a shared database across all customers.',
            focus_areas=['isolation'],
        )
        assert 'anti-pattern' in report.lower() or 'shared database' in report.lower()

    def test_analyze_architecture_design_with_no_signals(self):
        """Empty-ish descriptions still produce a guidance line."""
        knowledge = CellBasedArchitectureKnowledge()
        report = knowledge.analyze_architecture_design('totally unrelated text')
        assert 'cell-based architecture principles' in report.lower()

    def test_validate_architecture_with_criteria(self):
        """Validation surfaces pass/fail markers and applies extra criteria."""
        knowledge = CellBasedArchitectureKnowledge()
        doc = 'System with isolation, routing and monitoring. Horizontal scaling.'
        report = knowledge.validate_architecture(
            doc,
            validation_criteria=['deployment', 'observability'],
        )
        # Both checkmark and cross should appear — we pass some and fail some.
        assert '✅' in report
        assert '❌' in report

    def test_knowledge_summary_and_reload(self):
        """Summary and reload methods are callable against the bundled knowledge."""
        knowledge = CellBasedArchitectureKnowledge()
        summary = knowledge.get_knowledge_summary()
        assert summary['total_files'] > 0
        # reload_knowledge should not raise against the bundled content.
        knowledge.reload_knowledge()
        assert knowledge.get_knowledge_summary()['total_files'] > 0
