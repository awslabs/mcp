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

"""Additional tests for prompt_utils module to improve coverage."""

import os
import tempfile
from unittest import mock

from awslabs.well_architected_security_mcp_server.util.prompt_utils import (
    get_all_template_names,
    get_prompt_template,
    get_template_metadata,
    load_prompt_templates,
)


def test_load_prompt_templates_with_missing_file():
    """Test loading prompt templates when file doesn't exist."""
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.util.prompt_utils._is_initialized", False
    ):
        result = load_prompt_templates("nonexistent_file.md")
        assert result == {}


def test_load_prompt_templates_with_valid_file():
    """Test loading prompt templates with a valid markdown file."""
    # Create a temporary markdown file with template content
    template_content = """# Prompt Templates

## Security Assessment
This template helps with security assessments.

```
Analyze the security configuration for {service} in {region}.
Focus on:
- Access controls
- Encryption settings
- Network security
```

## Compliance Check
This template helps with compliance checks.

```
Review compliance for {service} against {framework}.
Check:
- Policy adherence
- Configuration standards
```
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(template_content)
        temp_file = f.name

    try:
        # Reset the global state
        with mock.patch(
            "awslabs.well_architected_security_mcp_server.util.prompt_utils._is_initialized", False
        ):
            with mock.patch(
                "awslabs.well_architected_security_mcp_server.util.prompt_utils._prompt_templates",
                {},
            ):
                result = load_prompt_templates(temp_file)

                assert len(result) >= 2
                assert "security_assessment" in result
                assert "compliance_check" in result
                assert result["security_assessment"]["title"] == "Security Assessment"
                assert (
                    "Analyze the security configuration"
                    in result["security_assessment"]["content"]
                )
    finally:
        os.unlink(temp_file)


def test_get_prompt_template_existing():
    """Test getting an existing prompt template."""
    # Mock the templates
    mock_templates = {
        "test_template": {
            "name": "test_template",
            "title": "Test Template",
            "content": "Test content",
            "description": "Test description",
        }
    }

    with mock.patch(
        "awslabs.well_architected_security_mcp_server.util.prompt_utils._prompt_templates",
        mock_templates,
    ):
        with mock.patch(
            "awslabs.well_architected_security_mcp_server.util.prompt_utils._is_initialized", True
        ):
            result = get_prompt_template("test_template")

            assert result is not None
            assert result["name"] == "test_template"
            assert result["title"] == "Test Template"


def test_get_prompt_template_nonexistent():
    """Test getting a non-existent prompt template."""
    with mock.patch(
        "awslabs.well_architected_security_mcp_server.util.prompt_utils._prompt_templates", {}
    ):
        with mock.patch(
            "awslabs.well_architected_security_mcp_server.util.prompt_utils._is_initialized", True
        ):
            result = get_prompt_template("nonexistent_template")

            assert result is None


def test_get_all_template_names():
    """Test getting all template names."""
    mock_templates = {
        "template1": {"name": "template1"},
        "template2": {"name": "template2"},
        "template3": {"name": "template3"},
    }

    with mock.patch(
        "awslabs.well_architected_security_mcp_server.util.prompt_utils._prompt_templates",
        mock_templates,
    ):
        with mock.patch(
            "awslabs.well_architected_security_mcp_server.util.prompt_utils._is_initialized", True
        ):
            result = get_all_template_names()

            assert len(result) == 3
            assert "template1" in result
            assert "template2" in result
            assert "template3" in result


def test_get_template_metadata():
    """Test getting template metadata."""
    mock_templates = {
        "template1": {"name": "template1", "title": "Template 1", "description": "Description 1"},
        "template2": {"name": "template2", "title": "Template 2", "description": "Description 2"},
    }

    with mock.patch(
        "awslabs.well_architected_security_mcp_server.util.prompt_utils._prompt_templates",
        mock_templates,
    ):
        with mock.patch(
            "awslabs.well_architected_security_mcp_server.util.prompt_utils._is_initialized", True
        ):
            result = get_template_metadata()

            assert len(result) == 2
            assert result[0]["name"] in ["template1", "template2"]
            assert result[0]["title"] in ["Template 1", "Template 2"]
            assert result[0]["description"] in ["Description 1", "Description 2"]
