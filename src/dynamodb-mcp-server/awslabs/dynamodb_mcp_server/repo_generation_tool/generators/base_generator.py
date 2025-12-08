"""Base generator abstract class and core interfaces"""

from abc import ABC, abstractmethod
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.language_config import (
    LanguageConfigLoader,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_loader import SchemaLoader
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.type_mappings import TypeMapper
from typing import Any


class BaseGenerator(ABC):
    """Base class for code generators"""

    def __init__(
        self, schema_path: str, language: str = 'python', allow_absolute_paths: bool = True
    ):
        """Initialize code generator.

        Args:
            schema_path: Path to schema file
            language: Target programming language
            allow_absolute_paths: If False, restricts to relative paths (safer for MCP/LLM usage)
        """
        self.schema_loader = SchemaLoader(schema_path, allow_absolute_paths=allow_absolute_paths)
        self.language = language
        self.language_config = LanguageConfigLoader.load(language)
        self.type_mapper = TypeMapper(language)

    @property
    def schema(self) -> dict[str, Any]:
        """Get the loaded schema."""
        return self.schema_loader.schema

    @abstractmethod
    def generate_entity(self, entity_name: str, entity_config: dict[str, Any]) -> str:
        """Generate entity code"""
        pass

    @abstractmethod
    def generate_repository(self, entity_name: str, entity_config: dict[str, Any]) -> str:
        """Generate repository code"""
        pass

    @abstractmethod
    def generate_all(self, output_dir: str, generate_usage_examples: bool = False) -> None:
        """Generate all code artifacts"""
        pass

    def generate_usage_examples(
        self,
        access_pattern_mapping: dict[str, Any],
        all_entities: dict[str, Any],
        all_tables: list[dict[str, Any]],
    ) -> str:
        """Generate usage examples code - to be implemented by subclasses"""
        return '# Usage examples not implemented for this generator'
