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
"""Knowledge base and analysis logic for cell-based architecture content.

This module contains the authoritative whitepaper section taxonomy
(``WHITEPAPER_SECTIONS``), a markdown knowledge loader for the bundled
``knowledge/`` tree, and the ``CellBasedArchitectureKnowledge`` facade used by
the MCP tool handlers in :mod:`server`.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from loguru import logger
from pydantic import BaseModel, Field

ComplexityLevel = Literal['beginner', 'intermediate', 'expert']


class WhitepaperSection(BaseModel):
    """Whitepaper section model."""

    title: str
    content: str
    subsections: List[str] = Field(default_factory=list)
    related_sections: List[str] = Field(default_factory=list)
    complexity_level: ComplexityLevel = 'intermediate'


@dataclass
class KnowledgeContent:
    """Represents a piece of knowledge content loaded from markdown."""

    file_path: str
    title: str
    content: str
    category: str
    subcategory: str
    tags: List[str]
    last_modified: datetime


class MarkdownKnowledgeLoader:
    """Load and manage markdown-based knowledge content from disk."""

    def __init__(self, knowledge_base_path: Optional[Union[str, Path]] = None) -> None:
        """Initialize the loader and discover knowledge files eagerly.

        Args:
            knowledge_base_path: Optional override for the root directory that
                contains the markdown knowledge tree. Defaults to the
                ``knowledge/`` folder shipped alongside this package.

        """
        if knowledge_base_path is None:
            current_dir = Path(__file__).parent
            self.knowledge_base_path = current_dir.parent.parent / 'knowledge'
        else:
            self.knowledge_base_path = Path(knowledge_base_path)

        self.content_cache: Dict[str, KnowledgeContent] = {}
        self.category_index: Dict[str, List[str]] = {}
        self.tag_index: Dict[str, List[str]] = {}

        self._load_all_content()

    def _load_all_content(self) -> None:
        """Load all markdown files recursively from the knowledge base."""
        if not self.knowledge_base_path.exists():
            return

        for md_file in self.knowledge_base_path.rglob('*.md'):
            try:
                content = self._load_markdown_file(md_file)
                if content:
                    rel = str(md_file.relative_to(self.knowledge_base_path))
                    self.content_cache[rel] = content
                    self._update_indexes(content)
            except Exception as exc:
                logger.error(f'Error loading {md_file}: {exc}')

    def _load_markdown_file(self, file_path: Path) -> Optional[KnowledgeContent]:
        """Load a single markdown file and return its ``KnowledgeContent``."""
        try:
            with open(file_path, 'r', encoding='utf-8') as fh:
                content = fh.read()

            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            title = title_match.group(1) if title_match else file_path.stem

            relative_path = file_path.relative_to(self.knowledge_base_path)
            path_parts = relative_path.parts
            category = path_parts[0] if len(path_parts) > 1 else 'general'
            subcategory = path_parts[1] if len(path_parts) > 2 else ''

            tags = self._extract_tags(content)
            last_modified = datetime.fromtimestamp(file_path.stat().st_mtime)

            return KnowledgeContent(
                file_path=str(relative_path),
                title=title,
                content=content,
                category=category,
                subcategory=subcategory,
                tags=tags,
                last_modified=last_modified,
            )
        except Exception as exc:
            logger.error(f'Error reading file {file_path}: {exc}')
            return None

    def _extract_tags(self, content: str) -> List[str]:
        """Extract explicit tag comments and derive implicit tags from content."""
        tags: List[str] = []

        tag_match = re.search(r'<!--\s*tags:\s*([^-]+)\s*-->', content, re.IGNORECASE)
        if tag_match:
            tags.extend(tag.strip() for tag in tag_match.group(1).split(','))

        content_lower = content.lower()
        if 'aws' in content_lower:
            tags.append('aws')
        if 'lambda' in content_lower:
            tags.append('lambda')
        if 'dynamodb' in content_lower:
            tags.append('dynamodb')
        if 'api gateway' in content_lower:
            tags.append('api-gateway')
        if 'monitoring' in content_lower:
            tags.append('monitoring')
        if 'security' in content_lower:
            tags.append('security')

        return list(set(tags))

    def _update_indexes(self, content: KnowledgeContent) -> None:
        """Update the category and tag indexes for a piece of content."""
        self.category_index.setdefault(content.category, []).append(content.file_path)
        for tag in content.tags:
            self.tag_index.setdefault(tag, []).append(content.file_path)

    def get_content_by_path(self, file_path: str) -> Optional[KnowledgeContent]:
        """Get content by its path relative to the knowledge base root."""
        return self.content_cache.get(file_path)

    def get_content_by_category(
        self,
        category: str,
        subcategory: Optional[str] = None,
    ) -> List[KnowledgeContent]:
        """Return all content in ``category``, optionally filtered by ``subcategory``."""
        results: List[KnowledgeContent] = []
        for content in self.content_cache.values():
            if content.category != category:
                continue
            if subcategory is None or content.subcategory == subcategory:
                results.append(content)
        return results

    def search_content(
        self,
        query: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[KnowledgeContent]:
        """Search content by query, optionally filtered by category and tags."""
        results: List[KnowledgeContent] = []
        query_lower = query.lower()

        for content in self.content_cache.values():
            if category and content.category != category:
                continue
            if tags and not any(tag in content.tags for tag in tags):
                continue
            if query_lower in content.title.lower() or query_lower in content.content.lower():
                results.append(content)
        return results

    def get_categories(self) -> List[str]:
        """Get all available categories."""
        return list(self.category_index.keys())

    def get_tags(self) -> List[str]:
        """Get all available tags."""
        return list(self.tag_index.keys())

    def get_content_summary(self) -> Dict[str, Any]:
        """Return a summary of knowledge base content."""
        return {
            'total_files': len(self.content_cache),
            'categories': {cat: len(files) for cat, files in self.category_index.items()},
            'tags': {tag: len(files) for tag, files in self.tag_index.items()},
            'last_updated': (
                max(c.last_modified for c in self.content_cache.values())
                if self.content_cache
                else None
            ),
        }

    def reload_content(self) -> None:
        """Reload all content from disk."""
        self.content_cache.clear()
        self.category_index.clear()
        self.tag_index.clear()
        self._load_all_content()


class CellBasedArchitectureKnowledge:
    """Main knowledge management class for cell-based architecture.

    Holds the authoritative whitepaper section taxonomy
    (:attr:`WHITEPAPER_SECTIONS`) and exposes the high-level operations used
    by the MCP tool handlers: concept explanation, stage guidance, design
    analysis, and validation.
    """

    WHITEPAPER_SECTIONS: Dict[str, Dict[str, Any]] = {
        'introduction': {
            'title': 'Introduction to Cell-Based Architecture',
            'content': (
                'Cell-based architecture is a resilience pattern that helps build more '
                'reliable distributed systems by isolating components into cells for better '
                'fault tolerance and scalability.'
            ),
            'complexity_level': 'beginner',
            'subsections': [],
            'related_sections': ['shared_responsibility', 'what_is_cell_based'],
        },
        'shared_responsibility': {
            'title': 'Shared Responsibility Model',
            'content': (
                'Understanding shared responsibility in cell-based architecture involves '
                'defining clear boundaries between what the platform provides and what '
                'applications must handle.'
            ),
            'complexity_level': 'beginner',
            'subsections': [],
            'related_sections': ['introduction'],
        },
        'what_is_cell_based': {
            'title': 'What is Cell-Based Architecture',
            'content': (
                'Cell-based architecture partitions applications into isolated cells, '
                'each containing all necessary components to serve a subset of customers '
                'or requests.'
            ),
            'complexity_level': 'beginner',
            'subsections': [],
            'related_sections': ['introduction'],
        },
        'why_use_cell_based': {
            'title': 'Why Use Cell-Based Architecture',
            'content': (
                'Cell-based architecture provides benefits including fault isolation, '
                'blast radius reduction, improved scalability, and better operational '
                'control.'
            ),
            'complexity_level': 'intermediate',
            'subsections': [],
            'related_sections': [],
        },
        'when_to_use': {
            'title': 'When to Use Cell-Based Architecture',
            'content': (
                'Cell-based architecture is most valuable for workloads where blast radius '
                'reduction, tenant isolation, or regional scaling is a first-class concern. '
                'Evaluate it for highly available services, multi-tenant SaaS platforms, '
                'and workloads with strict resilience SLOs.'
            ),
            'complexity_level': 'intermediate',
            'subsections': [],
            'related_sections': ['why_use_cell_based'],
        },
        'control_data_plane': {
            'title': 'Control Plane and Data Plane',
            'content': (
                'Cell-based architectures separate the control plane (which manages cells, '
                'routing, and configuration) from the data plane (which serves customer '
                'traffic). Keeping the data plane independent of the control plane is a '
                'key resilience property.'
            ),
            'complexity_level': 'expert',
            'subsections': [],
            'related_sections': ['cell_design', 'cell_routing'],
        },
        'cell_design': {
            'title': 'Cell Design',
            'content': (
                'Cell design involves creating isolated, self-contained units that include '
                'compute, storage, and networking resources with clear boundaries and '
                'minimal dependencies.'
            ),
            'complexity_level': 'expert',
            'subsections': [],
            'related_sections': [],
        },
        'cell_partition': {
            'title': 'Cell Partition',
            'content': (
                'Cell partitioning strategies involve dividing data and workloads across '
                'cells using techniques like customer-based, geographic, or feature-based '
                'partitioning.'
            ),
            'complexity_level': 'expert',
            'subsections': [],
            'related_sections': [],
        },
        'cell_routing': {
            'title': 'Cell Routing',
            'content': (
                'Cell routing directs requests to the correct cell using a thin, highly '
                'available routing layer. Keep routing logic simple and cache routing '
                'decisions where possible to minimize coupling to the control plane.'
            ),
            'complexity_level': 'expert',
            'subsections': [],
            'related_sections': ['control_data_plane', 'cell_partition'],
        },
        'cell_sizing': {
            'title': 'Cell Sizing',
            'content': (
                'Cell sizing balances blast radius, operational overhead, and cost. '
                'Smaller cells reduce blast radius but increase the number of cells to '
                'operate; larger cells are cheaper to run but expose more customers to a '
                'single failure domain.'
            ),
            'complexity_level': 'expert',
            'subsections': [],
            'related_sections': ['cell_partition', 'cell_placement'],
        },
        'cell_placement': {
            'title': 'Cell Placement',
            'content': (
                'Cell placement decides where cells run (Availability Zones, Regions, '
                'partitions) to meet resilience, latency, and data-residency requirements.'
            ),
            'complexity_level': 'expert',
            'subsections': [],
            'related_sections': ['cell_sizing'],
        },
        'cell_migration': {
            'title': 'Cell Migration',
            'content': (
                'Cell migration moves customers or tenants between cells to rebalance '
                'load, retire older cells, or respond to failures. Design migrations to be '
                'non-disruptive and resumable.'
            ),
            'complexity_level': 'expert',
            'subsections': [],
            'related_sections': ['cell_placement'],
        },
        'cell_deployment': {
            'title': 'Cell Deployment',
            'content': (
                'Cell deployment advocates wave-based rollouts: deploy to one canary cell, '
                'then to a small percentage, then broader waves. Automated rollback on '
                'elevated error rate or latency is recommended.'
            ),
            'complexity_level': 'expert',
            'subsections': [],
            'related_sections': ['cell_design'],
        },
        'cell_observability': {
            'title': 'Cell Observability',
            'content': (
                'Cell observability requires monitoring each cell independently while '
                'maintaining visibility into cross-cell interactions and overall system '
                'health.'
            ),
            'complexity_level': 'expert',
            'subsections': [],
            'related_sections': [],
        },
        'best_practices': {
            'title': 'Best Practices',
            'content': (
                'Implementation best practices include keeping cells independent, '
                'designing for failure, minimizing cross-cell dependencies, and '
                'implementing proper monitoring.'
            ),
            'complexity_level': 'intermediate',
            'subsections': [],
            'related_sections': [],
        },
        'faq': {
            'title': 'Frequently Asked Questions',
            'content': (
                'Common questions about cell-based architecture include how to size '
                'cells, when to adopt the pattern, how to migrate customers between '
                'cells, and how to keep routing simple and independent of the control '
                'plane.'
            ),
            'complexity_level': 'intermediate',
            'subsections': [],
            'related_sections': ['best_practices'],
        },
    }

    def __init__(self, knowledge_base_path: Optional[Union[str, Path]] = None) -> None:
        """Initialize the knowledge facade, eagerly loading markdown content."""
        self.loader = MarkdownKnowledgeLoader(knowledge_base_path)

    @classmethod
    def get_section(cls, section_name: str) -> Optional[WhitepaperSection]:
        """Get a whitepaper section by name, or ``None`` if unknown."""
        data = cls.WHITEPAPER_SECTIONS.get(section_name)
        if data:
            return WhitepaperSection(**data)
        return None

    @classmethod
    def get_sections_by_level(cls, level: ComplexityLevel) -> List[WhitepaperSection]:
        """Get all whitepaper sections at the given complexity level."""
        sections: List[WhitepaperSection] = []
        for data in cls.WHITEPAPER_SECTIONS.values():
            section = WhitepaperSection(**data)
            if section.complexity_level == level:
                sections.append(section)
        return sections

    @classmethod
    def get_related_sections(cls, section_name: str) -> List[WhitepaperSection]:
        """Get sections related to the given section."""
        if section_name not in cls.WHITEPAPER_SECTIONS:
            return []
        section_data = cls.WHITEPAPER_SECTIONS[section_name]
        related: List[WhitepaperSection] = []
        for related_name in section_data.get('related_sections', []):
            if related_name in cls.WHITEPAPER_SECTIONS:
                related.append(WhitepaperSection(**cls.WHITEPAPER_SECTIONS[related_name]))
        return related

    def get_concept_explanation(
        self,
        concept: str,
        detail_level: ComplexityLevel = 'intermediate',
        whitepaper_section: Optional[str] = None,
    ) -> str:
        """Return an explanation of a cell-based architecture concept.

        Args:
            concept: The concept to explain (e.g. "cell isolation").
            detail_level: ``beginner``, ``intermediate`` or ``expert``.
            whitepaper_section: Optional whitepaper section key to scope the answer.

        """
        if whitepaper_section and whitepaper_section in self.WHITEPAPER_SECTIONS:
            section = self.WHITEPAPER_SECTIONS[whitepaper_section]
            return (
                f'# {section["title"]}\n\n{section["content"]}\n\n'
                f'Concept: {concept} ({detail_level} level)'
            )

        if detail_level == 'beginner':
            return (
                f'# {concept.title()}\n\n'
                'Cell-based architecture concept explanation for beginners.\n\n'
                f'This concept relates to isolating components into cells for better fault '
                f'tolerance and scalability. {concept} is a key principle in building '
                'resilient distributed systems. Cell isolation ensures that failures in one '
                "cell don't cascade to other cells."
            )
        if detail_level == 'expert':
            return (
                f'# {concept.title()}\n\n'
                f'Advanced {concept} implementation details for experts.\n\n'
                'This concept involves sophisticated isolation mechanisms and advanced '
                'fault tolerance patterns in cell-based architectures. Expert-level '
                'implementation requires careful consideration of cell boundaries, routing '
                'strategies, and observability patterns.'
            )
        return (
            f'# {concept.title()}\n\n'
            'Cell-based architecture concept explanation for intermediate level.\n\n'
            'This concept relates to isolating components into cells for better fault '
            'tolerance and scalability. Cell isolation is achieved through dedicated '
            'resources and clear boundaries between cells.'
        )

    def get_implementation_guidance(
        self,
        stage: str,
        aws_services: Optional[List[str]] = None,
        experience_level: ComplexityLevel = 'intermediate',
    ) -> str:
        """Return stage-specific implementation guidance."""
        if aws_services is None:
            aws_services = []
        if not isinstance(aws_services, list):
            aws_services = []

        guidance = f'# {stage.title()} Stage Implementation Guidance\n\n'

        if stage == 'planning':
            guidance += (
                '## Planning Phase\n\n'
                '- Define cell boundaries\n'
                '- Identify isolation requirements\n'
                '- Plan for fault tolerance\n'
            )
        elif stage == 'design':
            guidance += (
                '## Design Phase\n\n'
                '- Create cell architecture diagrams\n'
                '- Define data partitioning strategy\n'
                '- Design routing mechanisms\n'
            )
        elif stage == 'implementation':
            guidance += (
                '## Implementation Phase\n\n'
                '- Set up cell infrastructure\n'
                '- Implement routing logic\n'
                '- Configure monitoring\n'
            )
        elif stage == 'monitoring':
            guidance += (
                '## Monitoring Phase\n\n'
                '- Set up cell-aware observability\n'
                '- Configure alerts and dashboards\n'
                '- Monitor cell health\n'
            )

        if aws_services:
            guidance += '\n## AWS Services Integration\n\n'
            for service in aws_services:
                guidance += f'- **{service.upper()}**: Cell-based configuration for {service}\n'

        guidance += f'\n*Guidance tailored for {experience_level} level.*\n'
        return guidance

    def analyze_architecture_design(
        self,
        architecture_description: str,
        focus_areas: Optional[List[str]] = None,
    ) -> str:
        """Analyze an architecture design against cell-based principles."""
        analysis_points: List[str] = []
        description_lower = architecture_description.lower()

        if 'shared database' in description_lower:
            anti_pattern_content = self.loader.search_content('anti-patterns')
            if anti_pattern_content:
                analysis_points.append(
                    '⚠️ Potential anti-pattern detected: Shared database across cells'
                )

        if 'single point of failure' in description_lower:
            analysis_points.append(
                '⚠️ Single point of failure mentioned - consider cell isolation principles'
            )

        if 'load balancer' in description_lower:
            routing_content = self.loader.search_content('cell routing')
            if routing_content:
                analysis_points.append('✅ Load balancing detected - ensure cell-aware routing')

        if focus_areas:
            for area in focus_areas:
                relevant_content = self.loader.search_content(area)
                if relevant_content:
                    analysis_points.append(
                        f'📋 Consider {area} best practices from knowledge base'
                    )

        if not analysis_points:
            analysis_points.append(
                'Architecture description provided. Consider reviewing cell-based '
                'architecture principles.'
            )

        return '\n'.join(analysis_points)

    def validate_architecture(
        self,
        design_document: str,
        validation_criteria: Optional[List[str]] = None,
    ) -> str:
        """Validate an architecture against cell-based principles."""
        validation_results: List[str] = []
        design_lower = design_document.lower()

        principles = [
            ('isolation', 'Cell isolation between components'),
            ('routing', 'Cell routing mechanism'),
            ('scaling', 'Horizontal scaling approach'),
            ('monitoring', 'Cell-aware monitoring'),
            ('deployment', 'Cell deployment strategy'),
        ]

        for principle, description in principles:
            if principle in design_lower:
                validation_results.append(f'✅ {description} - mentioned in design')
            else:
                validation_results.append(f'❌ {description} - not clearly addressed')

        if validation_criteria:
            for criterion in validation_criteria:
                if criterion.lower() in design_lower:
                    validation_results.append(f'✅ Validation criterion met: {criterion}')
                else:
                    validation_results.append(f'❌ Validation criterion not met: {criterion}')

        return '\n'.join(validation_results)

    def get_knowledge_summary(self) -> Dict[str, Any]:
        """Return a summary of available knowledge."""
        return self.loader.get_content_summary()

    def reload_knowledge(self) -> None:
        """Reload knowledge from disk."""
        self.loader.reload_content()
