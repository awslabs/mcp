# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Tests for the templates module."""

import pytest
from awslabs.code_doc_generation_mcp_server.utils.models import DocumentSection, DocumentSpec
from awslabs.code_doc_generation_mcp_server.utils.templates import (
    DOCUMENT_TEMPLATES,
    TEMPLATE_FILE_MAPPING,
    create_doc_from_template,
    get_template_for_file,
)
from unittest.mock import MagicMock


def test_get_template_for_file_direct_mapping():
    """Test get_template_for_file returns correct template for known files."""
    # Test standard mappings
    assert get_template_for_file('README.md') == 'README'
    assert get_template_for_file('API.md') == 'API'
    assert get_template_for_file('BACKEND.md') == 'BACKEND'
    assert get_template_for_file('FRONTEND.md') == 'FRONTEND'


def test_get_template_for_file_derived_mapping():
    """Test get_template_for_file derives template from filename correctly."""
    # Create a temporary test template
    original_templates = DOCUMENT_TEMPLATES.copy()
    try:
        # Add test template
        DOCUMENT_TEMPLATES['TEST_TEMPLATE'] = MagicMock()

        # Test with a filename that should be derived
        assert get_template_for_file('TEST_TEMPLATE.md') == 'TEST_TEMPLATE'
    finally:
        # Restore original templates
        globals()['DOCUMENT_TEMPLATES'] = original_templates


def test_get_template_for_file_unknown():
    """Test get_template_for_file raises ValueError for unknown files."""
    with pytest.raises(ValueError):
        get_template_for_file('UNKNOWN_FILE.md')


def test_template_file_mapping_consistency():
    """Test that TEMPLATE_FILE_MAPPING keys all map to valid templates."""
    for template_type in TEMPLATE_FILE_MAPPING.values():
        assert template_type in DOCUMENT_TEMPLATES, (
            f"Template type '{template_type}' not found in DOCUMENT_TEMPLATES"
        )


def test_create_doc_from_template():
    """Test create_doc_from_template creates correct DocumentSpec."""
    # Create a test for README template
    doc = create_doc_from_template('README', 'README.md')

    assert isinstance(doc, DocumentSpec)
    assert doc.name == 'README.md'
    assert doc.type == 'README'
    assert doc.template == 'README'
    # Ensure sections are copied from the template
    assert len(doc.sections) == len(DOCUMENT_TEMPLATES['README'].sections)

    # Verify first section
    assert doc.sections[0].title == DOCUMENT_TEMPLATES['README'].sections[0].title
    assert doc.sections[0].level == DOCUMENT_TEMPLATES['README'].sections[0].level


def test_create_doc_from_template_unknown():
    """Test create_doc_from_template raises ValueError for unknown templates."""
    with pytest.raises(ValueError):
        create_doc_from_template('NONEXISTENT_TEMPLATE', 'file.md')


def test_document_templates_structure():
    """Test that all document templates have the required structure."""
    for template_name, template in DOCUMENT_TEMPLATES.items():
        assert template.type == template_name
        assert isinstance(template.sections, list)
        assert len(template.sections) > 0

        # Check each section
        for section in template.sections:
            assert isinstance(section, DocumentSection)
            assert section.title
            assert section.level >= 1 and section.level <= 6
