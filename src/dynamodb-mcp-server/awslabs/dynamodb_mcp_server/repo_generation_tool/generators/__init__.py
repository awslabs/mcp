"""Code generation logic and generators."""

from awslabs.dynamodb_mcp_server.repo_generation_tool.generators.access_pattern_mapper import (
    AccessPatternMapper,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.generators.base_generator import (
    BaseGenerator,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.generators.jinja2_generator import (
    Jinja2Generator,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.generators.sample_generators import (
    SampleValueGenerator,
)


def create_generator(
    generator_type: str, schema_path: str, language: str = 'python', **kwargs
) -> BaseGenerator:
    """Factory function to create generators"""
    if generator_type.lower() == 'jinja2':
        return Jinja2Generator(schema_path, language=language, **kwargs)
    else:
        raise ValueError(f"Unknown generator type: {generator_type}. Only 'jinja2' is supported")


__all__ = [
    'BaseGenerator',
    'Jinja2Generator',
    'AccessPatternMapper',
    'SampleValueGenerator',
    'create_generator',
]
