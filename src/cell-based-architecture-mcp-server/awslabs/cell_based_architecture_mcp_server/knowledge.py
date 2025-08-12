import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import re
from datetime import datetime

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
    
    def __init__(self, knowledge_base_path: str = None):
        self.loader = MarkdownKnowledgeLoader(knowledge_base_path)
    
    def get_concept_explanation(self, concept: str, detail_level: str = "intermediate") -> str:
        """Get explanation of a cell-based architecture concept"""
        # Search for content related to the concept
        results = self.loader.search_content(concept)
        
        if not results:
            return f"No information found for concept: {concept}"
        
        # Select best match based on detail level
        best_match = self._select_content_by_detail_level(results, detail_level)
        
        if best_match:
            return self._format_content_response(best_match, detail_level)
        
        return f"No suitable content found for concept: {concept} at {detail_level} level"
    
    def get_implementation_guidance(self, stage: str, aws_services: List[str] = None) -> str:
        """Get implementation guidance for specific stage"""
        # Look for implementation content
        implementation_content = self.loader.get_content_by_category("implementation")
        
        # Filter by stage
        stage_content = []
        for content in implementation_content:
            if stage.lower() in content.title.lower() or stage.lower() in content.content.lower():
                stage_content.append(content)
        
        if not stage_content:
            return f"No implementation guidance found for stage: {stage}"
        
        # If AWS services specified, prioritize content mentioning those services
        if aws_services:
            service_content = []
            for content in stage_content:
                for service in aws_services:
                    if service.lower() in content.content.lower():
                        service_content.append(content)
                        break
            if service_content:
                stage_content = service_content
        
        # Return the most relevant content
        best_match = stage_content[0] if stage_content else None
        if best_match:
            return self._format_content_response(best_match, "intermediate")
        
        return f"No specific guidance found for stage: {stage}"
    
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
        # Extract relevant sections based on detail level
        lines = content.content.split('\n')
        
        # For basic level, focus on overview and key concepts
        if detail_level == "basic":
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
                return '\n'.join(result_lines[:50])  # Limit length
        
        # For intermediate/advanced, return more complete content
        return content.content[:2000] + "..." if len(content.content) > 2000 else content.content
    
    def get_knowledge_summary(self) -> Dict[str, Any]:
        """Get summary of available knowledge"""
        return self.loader.get_content_summary()
    
    def reload_knowledge(self):
        """Reload knowledge from disk"""
        self.loader.reload_content()