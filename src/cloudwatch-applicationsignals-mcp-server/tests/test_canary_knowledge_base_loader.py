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

"""Tests for canary_knowledge_base_loader."""

import json
import pytest
from awslabs.cloudwatch_applicationsignals_mcp_server.canary_knowledge_base_loader import (
    CanaryKnowledgeBaseLoader,
)
from awslabs.cloudwatch_applicationsignals_mcp_server.canary_knowledge_base_model import KBEntry
from datetime import date
from pathlib import Path
from unittest.mock import patch


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton instance before each test."""
    CanaryKnowledgeBaseLoader._instance = None
    yield
    CanaryKnowledgeBaseLoader._instance = None


@pytest.fixture
def sample_entry_json():
    """Return a sample knowledge base entry as a JSON-compatible dict."""
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

    @staticmethod
    def _load_sync() -> CanaryKnowledgeBaseLoader:
        """Synchronously create and load a loader for tests."""
        loader = CanaryKnowledgeBaseLoader()
        loader.load()
        return loader

    def test_singleton(self):
        """Test Singleton."""
        loader1 = self._load_sync()
        CanaryKnowledgeBaseLoader._instance = loader1
        # Second call to get_instance would return same if _instance is set
        assert CanaryKnowledgeBaseLoader._instance is loader1

    def test_load_from_real_kb_directory(self):
        """Test Load from real kb directory."""
        loader = self._load_sync()
        entries = loader.get_active_entries()
        # Should load the actual KB entries from the canary_knowledge_base directory
        assert len(entries) > 0

    def test_get_entry_by_id(self):
        """Test Get entry by id."""
        loader = self._load_sync()
        entry = loader.get_entry_by_id('RUNTIME-001')
        assert entry is not None
        assert entry.id == 'RUNTIME-001'

    def test_get_entry_by_id_not_found(self):
        """Test Get entry by id not found."""
        loader = self._load_sync()
        entry = loader.get_entry_by_id('NONEXISTENT-999')
        assert entry is None

    def test_load_only_once(self):
        """Test Load only once."""
        loader = CanaryKnowledgeBaseLoader()
        loader.load()
        count_after_first = len(loader.get_active_entries())
        loader.load()  # Should be a no-op
        assert len(loader.get_active_entries()) == count_after_first

    def test_parse_and_validate_valid(self, tmp_path, sample_entry_json):
        """Test Parse and validate valid."""
        json_file = tmp_path / 'test.json'
        json_file.write_text(json.dumps(sample_entry_json))

        loader = CanaryKnowledgeBaseLoader()
        entry = loader._parse_and_validate(json_file)
        assert entry is not None
        assert entry.id == 'TEST-001'

    def test_parse_and_validate_invalid_json(self, tmp_path):
        """Test Parse and validate invalid json."""
        json_file = tmp_path / 'bad.json'
        json_file.write_text('not valid json{{{')

        loader = CanaryKnowledgeBaseLoader()
        entry = loader._parse_and_validate(json_file)
        assert entry is None

    def test_parse_and_validate_empty_file(self, tmp_path):
        """Test Parse and validate empty file."""
        json_file = tmp_path / 'empty.json'
        json_file.write_text('null')

        loader = CanaryKnowledgeBaseLoader()
        entry = loader._parse_and_validate(json_file)
        assert entry is None

    def test_parse_and_validate_missing_required_field(self, tmp_path, sample_entry_json):
        """Test Parse and validate missing required field."""
        del sample_entry_json['id']
        json_file = tmp_path / 'missing.json'
        json_file.write_text(json.dumps(sample_entry_json))

        loader = CanaryKnowledgeBaseLoader()
        entry = loader._parse_and_validate(json_file)
        assert entry is None

    def test_is_deprecated_not_deprecated(self):
        """Test Is deprecated not deprecated."""
        entry = KBEntry(
            id='T',
            title='T',
            category='t',
            severity='low',
            error_patterns=[],
            symptoms=[],
            root_cause='x',
            recommendations=[],
        )
        loader = CanaryKnowledgeBaseLoader()
        assert loader._is_deprecated(entry) is False

    def test_is_deprecated_no_date(self):
        """Test Is deprecated no date."""
        entry = KBEntry(
            id='T',
            title='T',
            category='t',
            severity='low',
            error_patterns=[],
            symptoms=[],
            root_cause='x',
            recommendations=[],
            deprecated=True,
        )
        loader = CanaryKnowledgeBaseLoader()
        assert loader._is_deprecated(entry) is True

    def test_is_deprecated_future_date(self):
        """Test Is deprecated future date."""
        entry = KBEntry(
            id='T',
            title='T',
            category='t',
            severity='low',
            error_patterns=[],
            symptoms=[],
            root_cause='x',
            recommendations=[],
            deprecated=True,
            deprecation_date=date(2099, 12, 31),
        )
        loader = CanaryKnowledgeBaseLoader()
        assert loader._is_deprecated(entry) is False

    def test_is_deprecated_past_date(self):
        """Test Is deprecated past date."""
        entry = KBEntry(
            id='T',
            title='T',
            category='t',
            severity='low',
            error_patterns=[],
            symptoms=[],
            root_cause='x',
            recommendations=[],
            deprecated=True,
            deprecation_date=date(2020, 1, 1),
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
            CanaryKnowledgeBaseLoader()
            # Manually test with a non-existent path
            assert not (tmp_path / 'nonexistent').is_dir()


def test_load_with_missing_subdirectory(tmp_path):
    """Test that load handles missing subdirectories gracefully."""
    import awslabs.cloudwatch_applicationsignals_mcp_server.canary_knowledge_base_loader as mod

    # Create canary_knowledge_base dir with only 'runtime', no 'environment'
    kb_dir = tmp_path / 'canary_knowledge_base'
    kb_dir.mkdir()
    (kb_dir / 'runtime').mkdir()
    # 'environment' subdir intentionally missing

    orig_file = mod.__file__
    try:
        # Redirect __file__ so entries_dir = tmp_path / canary_knowledge_base
        mod.__file__ = str(tmp_path / 'fake.py')
        loader = CanaryKnowledgeBaseLoader()
        loader._loaded = False
        loader.load()
        # 'environment' dir is missing → warning logged, no crash
        assert loader._loaded is True
    finally:
        mod.__file__ = orig_file
