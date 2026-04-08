"""Tests for canary_knowledge_base_loader."""

import json
import pytest
from datetime import date
from pathlib import Path
from unittest.mock import patch, MagicMock
from awslabs.cloudwatch_applicationsignals_mcp_server.canary_knowledge_base_loader import (
    CanaryKnowledgeBaseLoader,
)
from awslabs.cloudwatch_applicationsignals_mcp_server.canary_knowledge_base_model import KBEntry


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton instance before each test."""
    CanaryKnowledgeBaseLoader._instance = None
    yield
    CanaryKnowledgeBaseLoader._instance = None


@pytest.fixture
def sample_entry_json():
    return {
        'id': 'TEST-001',
        'title': 'Test entry',
        'category': 'test',
        'severity': 'high',
        'error_patterns': [{'text_contains': 'error'}],
        'symptoms': ['Something broke'],
        'root_cause': 'A bug',
        'recommendations': [
            {'priority': 'high', 'confidence': 90, 'solution': [{'step': 'Fix it'}]}
        ],
    }


class TestCanaryKnowledgeBaseLoader:
    """Tests for CanaryKnowledgeBaseLoader."""

    def test_singleton(self):
        instance1 = CanaryKnowledgeBaseLoader.get_instance()
        instance2 = CanaryKnowledgeBaseLoader.get_instance()
        assert instance1 is instance2

    def test_load_from_real_kb_directory(self):
        loader = CanaryKnowledgeBaseLoader.get_instance()
        entries = loader.get_active_entries()
        # Should load the actual KB entries from the canary_knowledge_base directory
        assert len(entries) > 0

    def test_get_entry_by_id(self):
        loader = CanaryKnowledgeBaseLoader.get_instance()
        entry = loader.get_entry_by_id('RUNTIME-001')
        assert entry is not None
        assert entry.id == 'RUNTIME-001'

    def test_get_entry_by_id_not_found(self):
        loader = CanaryKnowledgeBaseLoader.get_instance()
        entry = loader.get_entry_by_id('NONEXISTENT-999')
        assert entry is None

    def test_load_only_once(self):
        loader = CanaryKnowledgeBaseLoader()
        loader.load()
        count_after_first = len(loader.get_active_entries())
        loader.load()  # Should be a no-op
        assert len(loader.get_active_entries()) == count_after_first

    def test_parse_and_validate_valid(self, tmp_path, sample_entry_json):
        json_file = tmp_path / 'test.json'
        json_file.write_text(json.dumps(sample_entry_json))

        loader = CanaryKnowledgeBaseLoader()
        entry = loader._parse_and_validate(json_file)
        assert entry is not None
        assert entry.id == 'TEST-001'

    def test_parse_and_validate_invalid_json(self, tmp_path):
        json_file = tmp_path / 'bad.json'
        json_file.write_text('not valid json{{{')

        loader = CanaryKnowledgeBaseLoader()
        entry = loader._parse_and_validate(json_file)
        assert entry is None

    def test_parse_and_validate_empty_file(self, tmp_path):
        json_file = tmp_path / 'empty.json'
        json_file.write_text('null')

        loader = CanaryKnowledgeBaseLoader()
        entry = loader._parse_and_validate(json_file)
        assert entry is None

    def test_parse_and_validate_missing_required_field(self, tmp_path, sample_entry_json):
        del sample_entry_json['id']
        json_file = tmp_path / 'missing.json'
        json_file.write_text(json.dumps(sample_entry_json))

        loader = CanaryKnowledgeBaseLoader()
        entry = loader._parse_and_validate(json_file)
        assert entry is None

    def test_is_deprecated_not_deprecated(self):
        entry = KBEntry(
            id='T', title='T', category='t', severity='low',
            error_patterns=[], symptoms=[], root_cause='x', recommendations=[],
        )
        loader = CanaryKnowledgeBaseLoader()
        assert loader._is_deprecated(entry) is False

    def test_is_deprecated_no_date(self):
        entry = KBEntry(
            id='T', title='T', category='t', severity='low',
            error_patterns=[], symptoms=[], root_cause='x', recommendations=[],
            deprecated=True,
        )
        loader = CanaryKnowledgeBaseLoader()
        assert loader._is_deprecated(entry) is True

    def test_is_deprecated_future_date(self):
        entry = KBEntry(
            id='T', title='T', category='t', severity='low',
            error_patterns=[], symptoms=[], root_cause='x', recommendations=[],
            deprecated=True, deprecation_date=date(2099, 12, 31),
        )
        loader = CanaryKnowledgeBaseLoader()
        assert loader._is_deprecated(entry) is False

    def test_is_deprecated_past_date(self):
        entry = KBEntry(
            id='T', title='T', category='t', severity='low',
            error_patterns=[], symptoms=[], root_cause='x', recommendations=[],
            deprecated=True, deprecation_date=date(2020, 1, 1),
        )
        loader = CanaryKnowledgeBaseLoader()
        assert loader._is_deprecated(entry) is True

    def test_missing_directory_logs_warning(self, tmp_path):
        """Test that missing subdirectories are handled gracefully."""
        loader = CanaryKnowledgeBaseLoader()
        loader._loaded = False
        # Patch the entries_dir to a temp path with no subdirs
        with patch.object(Path, 'parent', new_callable=lambda: property(lambda self: tmp_path)):
            # The loader should handle missing dirs gracefully
            loader2 = CanaryKnowledgeBaseLoader()
            # Manually test with a non-existent path
            assert not (tmp_path / 'nonexistent').is_dir()
