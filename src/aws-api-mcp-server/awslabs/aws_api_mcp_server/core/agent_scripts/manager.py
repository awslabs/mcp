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

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import frontmatter
from loguru import logger

from ..common.config import CUSTOM_SCRIPTS_DIR
from .models import AgentScript, Template


class AgentScriptsManager:
    """
    Manager for agentic scripts with template support.
    
    Loads scripts and templates for LLM execution.
    """

    def __init__(
        self,
        scripts_dir: Path = None,
        custom_scripts_dir: Path = None,
    ):
        if scripts_dir is None:
            scripts_dir = Path(__file__).parent / 'registry'

        self.scripts_dir = scripts_dir
        self.scripts: Dict[str, AgentScript] = {}
        self.templates: Dict[str, Template] = {}
        self.index: Dict[str, Any] = {}

        # Caching for search operations
        self._search_results_cache: Dict[str, List[str]] = {}

        # Load all resources
        self._load_index()
        self._load_templates()
        self._load_scripts()

        # Load custom scripts if directory provided
        if custom_scripts_dir and custom_scripts_dir.exists():
            self._load_custom_scripts(custom_scripts_dir)

        logger.info(f'Loaded {len(self.scripts)} scripts, {len(self.templates)} templates')

    def _load_index(self):
        """Load the master index with script metadata."""
        index_path = self.scripts_dir / 'index.json'
        if index_path.exists():
            try:
                with open(index_path, 'r') as f:
                    self.index = json.load(f)
                logger.info(f"Loaded index with {len(self.index.get('scripts', {}))} script definitions")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f'Failed to load index.json: {e}')
                self.index = {}
        else:
            logger.info('No index.json found, using basic structure')
            self.index = {}

    def _load_templates(self):
        """Load configuration templates using class-based loading."""
        templates_dir = self.scripts_dir / 'templates'
        if not templates_dir.exists():
            logger.info('No templates directory found')
            return

        template_files = list(templates_dir.rglob('*.json'))
        logger.info(f'Found {len(template_files)} template files')

        for file_path in template_files:
            try:
                template = Template.load(file_path)
                self.templates[template.name] = template
            except Exception as e:
                logger.error(f'Failed to load template {file_path}: {e}')

    def _load_scripts(self):
        """Load all agentic scripts using class-based loading."""
        script_files = list(self.scripts_dir.rglob('*.script.md'))
        logger.info(f'Found {len(script_files)} script files')

        for file_path in script_files:
            try:
                script = AgentScript.load(file_path)
                self.scripts[script.name] = script
            except Exception as e:
                logger.error(f'Failed to load script {file_path}: {e}')

    def _load_custom_scripts(self, custom_dir: Path):
        """Load custom scripts from user-specified directory."""
        for file_path in custom_dir.glob('*.script.md'):
            try:
                script = AgentScript.load(file_path)
                
                if not script.metadata.get('description'):
                    logger.warning(f'Custom script {script.name} has no description, skipping')
                    continue
                
                self.scripts[script.name] = script
            except Exception as e:
                logger.error(f'Failed to load custom script {file_path}: {e}')

    def get_script(self, script_name: str) -> Optional[AgentScript]:
        """Get a script by name."""
        return self.scripts.get(script_name)

    def get_template(self, template_name: str) -> Optional[Template]:
        """Get a configuration template by name."""
        return self.templates.get(template_name)

    def get_template_content(self, template_name: str) -> Optional[str]:
        """Get template content as JSON string."""
        template = self.templates.get(template_name)
        if not template:
            return None
        return json.dumps(template.content, indent=2)

    def get_template_with_parameters(
        self, template_name: str, parameters: Dict[str, str]
    ) -> Optional[str]:
        """Get template with parameters replaced, returned as JSON string."""
        template = self.templates.get(template_name)
        if not template:
            return None

        return template.substitute_parameters(parameters)

    def _filter_by_complexity(self, candidates: set, complexity: str) -> set:
        """Filter scripts by complexity level."""
        return {
            name for name in candidates
            if self.index.get('scripts', {}).get(name, {}).get('complexity') == complexity
        }

    def _filter_by_aws_services(self, candidates: set, aws_services: List[str]) -> set:
        """Filter scripts by AWS services."""
        filtered = set()
        for name in candidates:
            script_services = self.index.get('scripts', {}).get(name, {}).get('aws_services', [])
            if any(service in script_services for service in aws_services):
                filtered.add(name)
        return filtered

    def _filter_by_tags(self, candidates: set, tags: List[str]) -> set:
        """Filter scripts by tags."""
        filtered = set()
        for name in candidates:
            script_tags = self.index.get('scripts', {}).get(name, {}).get('tags', [])
            if any(tag in script_tags for tag in tags):
                filtered.add(name)
        return filtered

    def _calculate_relevance_score(self, script_name: str, query: str) -> int:
        """Calculate relevance score for script against query."""
        script = self.scripts[script_name]
        script_metadata = self.index.get('scripts', {}).get(script_name, {})

        query_lower = query.lower()
        search_text = (
            f"{script_name} {script.description} "
            f"{' '.join(script_metadata.get('tags', []))} "
            f"{' '.join(script_metadata.get('aws_services', []))}"
        ).lower()

        score = 0
        for word in query_lower.split():
            if word in search_text:
                score += 1
        return score

    def search_scripts(
        self,
        query: str = None,
        tags: List[str] = None,
        aws_services: List[str] = None,
        complexity: str = None,
    ) -> List[str]:
        """
        Search scripts by various criteria with pre-filtering optimization.
        
        Returns:
            List of matching script names sorted by relevance
        """
        # Check cache
        cache_key = f'{query}|{tags}|{aws_services}|{complexity}'
        if cache_key in self._search_results_cache:
            logger.debug('Returning cached search results')
            return self._search_results_cache[cache_key]

        # Pre-filter candidates
        candidate_scripts = set(self.scripts.keys())

        if complexity:
            candidate_scripts = self._filter_by_complexity(candidate_scripts, complexity)
        if aws_services:
            candidate_scripts = self._filter_by_aws_services(candidate_scripts, aws_services)
        if tags:
            candidate_scripts = self._filter_by_tags(candidate_scripts, tags)

        # Calculate relevance scores
        matching_scripts = []
        for script_name in candidate_scripts:
            if query:
                score = self._calculate_relevance_score(script_name, query)
                if score == 0:
                    continue
                matching_scripts.append((score, script_name))
            else:
                matching_scripts.append((0, script_name))

        # Sort and return
        matching_scripts.sort(key=lambda x: x[0], reverse=True)
        result = [script_name for _, script_name in matching_scripts]

        self._search_results_cache[cache_key] = result
        return result

    def get_script_info(self, script_name: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive information about a script."""
        script = self.scripts.get(script_name)
        if not script:
            return None

        metadata = self.index.get('scripts', {}).get(script_name, {})

        return {
            'name': script_name,
            'description': script.description,
            'parameters': script.parameters,
            'estimated_time': metadata.get('estimated_time', 'Unknown'),
            'complexity': metadata.get('complexity', 'Unknown'),
            'tags': metadata.get('tags', []),
            'aws_services': metadata.get('aws_services', []),
            'path': str(script.path),
        }

    def list_scripts(self) -> List[str]:
        """Return list of available script names."""
        return list(self.scripts.keys())

    def list_templates(self) -> List[str]:
        """Return list of available template names."""
        return list(self.templates.keys())

    def clear_cache(self):
        """Clear all caches (useful for testing/reloading)."""
        self._search_results_cache.clear()
        logger.debug('Cleared search cache')

    def pretty_print_scripts(self) -> str:
        """Return a formatted string of available scripts for server integration."""
        if not self.scripts:
            return 'No agentic scripts available.'

        lines = []
        for script_name in sorted(self.scripts.keys()):
            info = self.get_script_info(script_name)
            if info:
                lines.append(f"{script_name} : {info['description']}")

        return '\n        '.join(lines)


# Global instance for server integration
custom_scripts_dir = (
    Path(CUSTOM_SCRIPTS_DIR) if CUSTOM_SCRIPTS_DIR and CUSTOM_SCRIPTS_DIR.strip() else None
)
AGENT_SCRIPTS_MANAGER = AgentScriptsManager(custom_scripts_dir=custom_scripts_dir)
