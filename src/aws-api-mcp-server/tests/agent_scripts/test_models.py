"""Tests for agent script models."""

import json
import pytest
import tempfile
from pathlib import Path

from awslabs.aws_api_mcp_server.core.agent_scripts.models import (
    AgentScript,
    ScriptIndex,
    Template,
)


class TestTemplate:
    """Tests for Template class."""

    def test_template_load(self):
        """Test Template.load() from JSON file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            template_path = Path(temp_dir) / 'test-template.json'
            template_data = {
                '_description': 'Test template',
                '_parameters': ['param1', 'param2'],
                'key1': 'value1',
                'key2': '{param1}'
            }
            
            with open(template_path, 'w') as f:
                json.dump(template_data, f)
            
            template = Template.load(template_path)
            
            assert template.name == 'test-template'
            assert template.description == 'Test template'
            assert '_description' not in template.content
            assert 'key1' in template.content
            assert template.content['key1'] == 'value1'

    def test_template_substitute_parameters(self):
        """Test Template.substitute_parameters()."""
        with tempfile.TemporaryDirectory() as temp_dir:
            template_path = Path(temp_dir) / 'test.json'
            template_data = {
                'bucket': '{bucket_name}',
                'account': '{account_id}',
                'nested': {
                    'value': '{param1}'
                }
            }
            
            with open(template_path, 'w') as f:
                json.dump(template_data, f)
            
            template = Template.load(template_path)
            result = template.substitute_parameters({
                'bucket_name': 'my-bucket',
                'account_id': '123456',
                'param1': 'test-value'
            })
            
            assert isinstance(result, str)
            assert 'my-bucket' in result
            assert '123456' in result
            assert 'test-value' in result
            assert '{bucket_name}' not in result


class TestScriptIndex:
    """Tests for ScriptIndex class."""

    def test_script_index_from_dict(self):
        """Test ScriptIndex.from_dict()."""
        data = {
            'version': '2.0',
            'scripts': {'test': {'main': 'test.script.md'}},
            'templates': {'t1': {'file': 't1.json'}},
            'metadata': {'total': 1}
        }
        
        index = ScriptIndex.from_dict(data)
        
        assert index.version == '2.0'
        assert 'test' in index.scripts
        assert 't1' in index.templates
        assert index.metadata['total'] == 1

    def test_script_index_defaults(self):
        """Test ScriptIndex with missing fields."""
        data = {}
        index = ScriptIndex.from_dict(data)
        
        assert index.version == '1.0'
        assert index.scripts == {}
        assert index.templates == {}
        assert index.metadata == {}


class TestAgentScript:
    """Tests for AgentScript class."""

    def test_agent_script_load_legacy_format(self):
        """Test AgentScript.load() with legacy flat format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / 'my-script.script.md'
            script_path.write_text("""---
description: Test script
---
# Script content
""")
            
            script = AgentScript.load(script_path)
            
            assert script.name == 'my-script'
            assert script.description == 'Test script'
            assert script.content.strip() == '# Script content'

    def test_agent_script_load_modular_format(self):
        """Test AgentScript.load() with modular main.script.md format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            script_dir = Path(temp_dir) / 'my-module'
            script_dir.mkdir()
            script_path = script_dir / 'main.script.md'
            script_path.write_text("""---
description: Modular script
---
# Modular content
""")
            
            script = AgentScript.load(script_path)
            
            assert script.name == 'my-module'
            assert script.description == 'Modular script'

    def test_agent_script_yaml_parameters(self):
        """Test AgentScript.load() with YAML parameters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / 'test.script.md'
            script_path.write_text("""---
description: Test
parameters:
  param1:
    required: true
    description: "First param"
  param2:
    required: false
    default: "value"
---
# Content
""")
            
            script = AgentScript.load(script_path)
            
            assert 'param1' in script.parameters
            assert script.parameters['param1']['required'] is True
            assert 'param2' in script.parameters
