"""
Template Module

Exports template registry and renderer functionality.
"""

from .registry import (
    DeploymentTypes,
    Template,
    get_templates_path,
    get_template_for_deployment,
    discover_templates,
    list_templates,
    get_template_info
)

from .renderer import render_template

__all__ = [
    "DeploymentTypes",
    "Template",
    "get_templates_path",
    "get_template_for_deployment",
    "discover_templates",
    "list_templates",
    "get_template_info",
    "render_template"
]
