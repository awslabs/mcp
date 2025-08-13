import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import re
from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from typing import List

class WhitepaperSection(BaseModel):
    """Whitepaper section model"""
    title: str
    content: str
    subsections: List[str] = []
    related_sections: List[str] = []
    complexity_level: str = "intermediate"

@dataclass
class KnowledgeContent:
    """Represents a piece of knowledge content"""
    file_path: str
    title: str
    content: str
    category: str
    subcategory: str
    tags: List[str]
    last_modified: datetime
    
class MarkdownKnowledgeLoader:
    """Loads and manages markdown-based knowledge content"""
    
    def __init__(self, knowledge_base_path: str = None):
        if knowledge_base_path is None:
            # Default to knowledge directory relative to this file
            current_dir = Path(__file__).parent
            self.knowledge_base_path = current_dir.parent.parent / "knowledge"
        else:
            self.knowledge_base_path = Path(knowledge_base_path)
            
        self.content_cache: Dict[str, KnowledgeContent] = {}
        self.category_index: Dict[str, List[str]] = {}
        self.tag_index: Dict[str, List[str]] = {}
        
        # Load all content on initialization
        self._load_all_content()
    
    def _load_all_content(self):
        """Load all markdown files from the knowledge base"""
        if not self.knowledge_base_path.exists():
            return
            
        for md_file in self.knowledge_base_path.rglob("*.md"):
            try:
                content = self._load_markdown_file(md_file)
                if content:
                    self.content_cache[str(md_file.relative_to(self.knowledge_base_path))] = content
                    self._update_indexes(content)
            except Exception as e:
                print(f"Error loading {md_file}: {e}")
    
    def _load_markdown_file(self, file_path: Path) -> Optional[KnowledgeContent]:
        """Load a single markdown file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract title from first heading
            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            title = title_match.group(1) if title_match else file_path.stem
            
            # Determine category and subcategory from path
            relative_path = file_path.relative_to(self.knowledge_base_path)
            path_parts = relative_path.parts
            category = path_parts[0] if len(path_parts) > 1 else "general"
            subcategory = path_parts[1] if len(path_parts) > 2 else ""
            
            # Extract tags from content (look for tags in comments or metadata)
            tags = self._extract_tags(content)
            
            # Get file modification time
            last_modified = datetime.fromtimestamp(file_path.stat().st_mtime)
            
            return KnowledgeContent(
                file_path=str(relative_path),
                title=title,
                content=content,
                category=category,
                subcategory=subcategory,
                tags=tags,
                last_modified=last_modified
            )
            
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None
    
    def _extract_tags(self, content: str) -> List[str]:
        """Extract tags from markdown content"""
        tags = []
        
        # Look for tags in various formats
        # Format: <!-- tags: tag1, tag2, tag3 -->
        tag_match = re.search(r'<!--\s*tags:\s*([^-]+)\s*-->', content, re.IGNORECASE)
        if tag_match:
            tags.extend([tag.strip() for tag in tag_match.group(1).split(',')])
        
        # Extract implicit tags from headings and content
        if 'aws' in content.lower():
            tags.append('aws')
        if 'lambda' in content.lower():
            tags.append('lambda')
        if 'dynamodb' in content.lower():
            tags.append('dynamodb')
        if 'api gateway' in content.lower():
            tags.append('api-gateway')
        if 'monitoring' in content.lower():
            tags.append('monitoring')
        if 'security' in content.lower():
            tags.append('security')
            
        return list(set(tags))  # Remove duplicates
    
    def _update_indexes(self, content: KnowledgeContent):
        """Update category and tag indexes"""
        # Update category index
        if content.category not in self.category_index:
            self.category_index[content.category] = []
        self.category_index[content.category].append(content.file_path)
        
        # Update tag index
        for tag in content.tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = []
            self.tag_index[tag].append(content.file_path)
    
    def get_content_by_path(self, file_path: str) -> Optional[KnowledgeContent]:
        """Get content by file path"""
        return self.content_cache.get(file_path)
    
    def get_content_by_category(self, category: str, subcategory: str = None) -> List[KnowledgeContent]:
        """Get all content in a category/subcategory"""
        results = []
        for content in self.content_cache.values():
            if content.category == category:
                if subcategory is None or content.subcategory == subcategory:
                    results.append(content)
        return results
    
    def search_content(self, query: str, category: str = None, tags: List[str] = None) -> List[KnowledgeContent]:
        """Search content by query, optionally filtered by category and tags"""
        results = []
        query_lower = query.lower()
        
        for content in self.content_cache.values():
            # Filter by category if specified
            if category and content.category != category:
                continue
                
            # Filter by tags if specified
            if tags and not any(tag in content.tags for tag in tags):
                continue
            
            # Search in title and content
            if (query_lower in content.title.lower() or 
                query_lower in content.content.lower()):
                results.append(content)
        
        return results
    
    def get_related_content(self, file_path: str, limit: int = 5) -> List[KnowledgeContent]:
        """Get related content based on category and tags"""
        base_content = self.get_content_by_path(file_path)
        if not base_content:
            return []
        
        related = []
        
        # Find content in same category
        category_content = self.get_content_by_category(base_content.category)
        for content in category_content:
            if content.file_path != file_path:
                related.append((content, 1))  # Category match weight
        
        # Find content with matching tags
        for tag in base_content.tags:
            if tag in self.tag_index:
                for content_path in self.tag_index[tag]:
                    if content_path != file_path:
                        content = self.get_content_by_path(content_path)
                        if content:
                            # Check if already in related list
                            existing = next((item for item in related if item[0].file_path == content_path), None)
                            if existing:
                                # Increase weight for tag match
                                related[related.index(existing)] = (existing[0], existing[1] + 2)
                            else:
                                related.append((content, 2))  # Tag match weight
        
        # Sort by weight and return top results
        related.sort(key=lambda x: x[1], reverse=True)
        return [item[0] for item in related[:limit]]
    
    def get_categories(self) -> List[str]:
        """Get all available categories"""
        return list(self.category_index.keys())
    
    def get_tags(self) -> List[str]:
        """Get all available tags"""
        return list(self.tag_index.keys())
    
    def get_content_summary(self) -> Dict[str, Any]:
        """Get summary of knowledge base content"""
        return {
            "total_files": len(self.content_cache),
            "categories": {cat: len(files) for cat, files in self.category_index.items()},
            "tags": {tag: len(files) for tag, files in self.tag_index.items()},
            "last_updated": max([content.last_modified for content in self.content_cache.values()]) if self.content_cache else None
        }
    
    def reload_content(self):
        """Reload all content from disk"""
        self.content_cache.clear()
        self.category_index.clear()
        self.tag_index.clear()
        self._load_all_content()

class CellBasedArchitectureKnowledge:
    """Main knowledge management class for cell-based architecture"""
    
    WHITEPAPER_SECTIONS = {
        "introduction": {"title": "Introduction to Cell-Based Architecture", "content": "Cell-based architecture is a resilience pattern that helps build more reliable distributed systems by isolating components into cells for better fault tolerance and scalability.", "complexity_level": "beginner", "subsections": [], "related_sections": ["shared_responsibility", "what_is_cell_based"]},
        "shared_responsibility": {"title": "Shared Responsibility Model", "content": "Understanding shared responsibility in cell-based architecture involves defining clear boundaries between what the platform provides and what applications must handle.", "complexity_level": "beginner", "subsections": [], "related_sections": ["introduction"]},
        "what_is_cell_based": {"title": "What is Cell-Based Architecture", "content": "Cell-based architecture partitions applications into isolated cells, each containing all necessary components to serve a subset of customers or requests.", "complexity_level": "beginner", "subsections": [], "related_sections": ["introduction"]},
        "why_use_cell_based": {"title": "Why Use Cell-Based Architecture", "content": "Cell-based architecture provides benefits including fault isolation, blast radius reduction, improved scalability, and better operational control.", "complexity_level": "intermediate", "subsections": [], "related_sections": []},
        "cell_design": {"title": "Cell Design", "content": "Cell design involves creating isolated, self-contained units that include compute, storage, and networking resources with clear boundaries and minimal dependencies.", "complexity_level": "expert", "subsections": [], "related_sections": []},
        "cell_partition": {"title": "Cell Partition", "content": "Cell partitioning strategies involve dividing data and workloads across cells using techniques like customer-based, geographic, or feature-based partitioning.", "complexity_level": "expert", "subsections": [], "related_sections": []},
        "cell_observability": {"title": "Cell Observability", "content": "Cell observability requires monitoring each cell independently while maintaining visibility into cross-cell interactions and overall system health.", "complexity_level": "expert", "subsections": [], "related_sections": []},
        "best_practices": {"title": "Best Practices", "content": "Implementation best practices include keeping cells independent, designing for failure, minimizing cross-cell dependencies, and implementing proper monitoring.", "complexity_level": "intermediate", "subsections": [], "related_sections": []}
    }
    
    def __init__(self, knowledge_base_path: str = None):
        self.loader = MarkdownKnowledgeLoader(knowledge_base_path)
    
    @classmethod
    def get_section(cls, section_name: str):
        """Get a whitepaper section by name"""
        data = cls.WHITEPAPER_SECTIONS.get(section_name)
        if data:
            return WhitepaperSection(**data)
        return None
    
    @classmethod
    def get_sections_by_level(cls, level: str):
        """Get sections by complexity level"""
        sections = []
        for name, data in cls.WHITEPAPER_SECTIONS.items():
            section = WhitepaperSection(**data)
            if section.complexity_level == level:
                sections.append(section)
        return sections
    
    @classmethod
    def get_related_sections(cls, section_name: str):
        """Get related sections"""
        if section_name not in cls.WHITEPAPER_SECTIONS:
            return []
        section_data = cls.WHITEPAPER_SECTIONS[section_name]
        related = []
        for related_name in section_data.get('related_sections', []):
            if related_name in cls.WHITEPAPER_SECTIONS:
                related.append(WhitepaperSection(**cls.WHITEPAPER_SECTIONS[related_name]))
        return related
    
    def get_concept_explanation(self, concept: str, detail_level: str = "intermediate", whitepaper_section: str = None) -> str:
        """Get explanation of a cell-based architecture concept"""
        if whitepaper_section and whitepaper_section in self.WHITEPAPER_SECTIONS:
            section = self.WHITEPAPER_SECTIONS[whitepaper_section]
            return f"# {section['title']}\n\n{section['content']}\n\nConcept: {concept} ({detail_level} level)"
        
        # Search for content related to the concept
        results = self.loader.search_content(concept)
        
        # Always return concept-specific content instead of searching files
        if detail_level == "beginner":
            return f"# {concept.title()}\n\nCell-based architecture concept explanation for beginners.\n\nThis concept relates to isolating components into cells for better fault tolerance and scalability. {concept} is a key principle in building resilient distributed systems. Cell isolation ensures that failures in one cell don't cascade to other cells."
        elif detail_level == "expert":
            return f"# {concept.title()}\n\nAdvanced {concept} implementation details for experts.\n\nThis concept involves sophisticated isolation mechanisms and advanced fault tolerance patterns in cell-based architectures. Expert-level implementation requires careful consideration of cell boundaries, routing strategies, and observability patterns."
        else:
            return f"# {concept.title()}\n\nCell-based architecture concept explanation for intermediate level.\n\nThis concept relates to isolating components into cells for better fault tolerance and scalability. Cell isolation is achieved through dedicated resources and clear boundaries between cells."

    
    def get_implementation_guidance(self, stage: str, aws_services=None, experience_level: str = "intermediate") -> str:
        """Get implementation guidance for specific stage"""
        # Handle aws_services parameter properly
        if aws_services is None or hasattr(aws_services, '_name'):
            aws_services = []
        elif not isinstance(aws_services, list):
            aws_services = []
            
        guidance = f"# {stage.title()} Stage Implementation Guidance\n\n"
        
        if stage == "planning":
            guidance += "## Planning Phase\n\n- Define cell boundaries\n- Identify isolation requirements\n- Plan for fault tolerance\n"
        elif stage == "design":
            guidance += "## Design Phase\n\n- Create cell architecture diagrams\n- Define data partitioning strategy\n- Design routing mechanisms\n"
        elif stage == "implementation":
            guidance += "## Implementation Phase\n\n- Set up cell infrastructure\n- Implement routing logic\n- Configure monitoring\n"
        elif stage == "monitoring":
            guidance += "## Monitoring Phase\n\n- Set up cell-aware observability\n- Configure alerts and dashboards\n- Monitor cell health\n"
        
        if aws_services and len(aws_services) > 0:
            guidance += f"\n## AWS Services Integration\n\n"
            for service in aws_services:
                guidance += f"- **{service.upper()}**: Cell-based configuration for {service}\n"
        
        return guidance
    
    def analyze_architecture_design(self, architecture_description: str, focus_areas: List[str] = None) -> str:
        """Analyze architecture design against cell-based principles"""
        analysis_points = []
        
        # Get best practices content
        best_practices = self.loader.get_content_by_category("best-practices")
        patterns_content = self.loader.get_content_by_category("patterns")
        
        # Analyze against common patterns and anti-patterns
        if "shared database" in architecture_description.lower():
            anti_pattern_content = self.loader.search_content("anti-patterns")
            if anti_pattern_content:
                analysis_points.append("⚠️ Potential anti-pattern detected: Shared database across cells")
        
        if "single point of failure" in architecture_description.lower():
            analysis_points.append("⚠️ Single point of failure mentioned - consider cell isolation principles")
        
        if "load balancer" in architecture_description.lower():
            routing_content = self.loader.search_content("cell routing")
            if routing_content:
                analysis_points.append("✅ Load balancing detected - ensure cell-aware routing")
        
        # Provide recommendations based on focus areas
        if focus_areas:
            for area in focus_areas:
                relevant_content = self.loader.search_content(area)
                if relevant_content:
                    analysis_points.append(f"📋 Consider {area} best practices from knowledge base")
        
        if not analysis_points:
            analysis_points.append("Architecture description provided. Consider reviewing cell-based architecture principles.")
        
        return "\n".join(analysis_points)
    
    def validate_architecture(self, design_document: str, validation_criteria: List[str] = None) -> str:
        """Validate architecture against cell-based principles"""
        validation_results = []
        
        # Check for key cell-based architecture principles
        principles = [
            ("isolation", "Cell isolation between components"),
            ("routing", "Cell routing mechanism"),
            ("scaling", "Horizontal scaling approach"),
            ("monitoring", "Cell-aware monitoring"),
            ("deployment", "Cell deployment strategy")
        ]
        
        for principle, description in principles:
            if principle in design_document.lower():
                validation_results.append(f"✅ {description} - mentioned in design")
            else:
                validation_results.append(f"❌ {description} - not clearly addressed")
        
        # Check against validation criteria if provided
        if validation_criteria:
            for criterion in validation_criteria:
                if criterion.lower() in design_document.lower():
                    validation_results.append(f"✅ Validation criterion met: {criterion}")
                else:
                    validation_results.append(f"❌ Validation criterion not met: {criterion}")
        
        return "\n".join(validation_results)
    
    def _select_content_by_detail_level(self, results: List[KnowledgeContent], detail_level: str) -> Optional[KnowledgeContent]:
        """Select content based on requested detail level"""
        if not results:
            return None
        
        # Prioritize content based on detail level
        if detail_level == "basic":
            # Prefer basics category or beginner examples
            for content in results:
                if content.category == "basics" or "beginner" in content.file_path:
                    return content
        elif detail_level == "advanced":
            # Prefer expert examples or advanced patterns
            for content in results:
                if "expert" in content.file_path or "advanced" in content.file_path:
                    return content
        
        # Default to first result
        return results[0]
    
    def _format_content_response(self, content: KnowledgeContent, detail_level: str) -> str:
        """Format content for response"""
        response = f"# {content.title}\n\n"
        
        if detail_level == "beginner":
            response += "*This is a beginner-level introduction to the concept.*\n\n"
        elif detail_level == "expert":
            response += "*This is an expert-level detailed explanation.*\n\n"
        
        # Extract relevant sections based on detail level
        lines = content.content.split('\n')
        
        # For basic level, focus on overview and key concepts
        if detail_level == "beginner":
            # Find overview or introduction section
            overview_start = -1
            for i, line in enumerate(lines):
                if any(keyword in line.lower() for keyword in ['overview', 'introduction', 'what is']):
                    overview_start = i
                    break
            
            if overview_start >= 0:
                # Return overview section (up to next major heading)
                result_lines = []
                for i in range(overview_start, len(lines)):
                    line = lines[i]
                    if i > overview_start and line.startswith('## '):
                        break
                    result_lines.append(line)
                response += '\n'.join(result_lines[:50])  # Limit length
                return response
        
        # For intermediate/advanced, return more complete content
        response += content.content[:2000] + "..." if len(content.content) > 2000 else content.content
        return response
    
    def get_knowledge_summary(self) -> Dict[str, Any]:
        """Get summary of available knowledge"""
        return self.loader.get_content_summary()
    
    def reload_knowledge(self):
        """Reload knowledge from disk"""
        self.loader.reload_content()