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

"""Tests for the review config loader."""

import json
import pytest
from awslabs.redshift_mcp_server.review.config_loader import (
    load_queries_config,
    load_recommendations_config,
    load_signals_config,
)
from pathlib import Path


CONFIG_DIR = Path(__file__).resolve().parent.parent / 'awslabs' / 'redshift_mcp_server' / 'config'


class TestLoadQueriesConfig:
    """Tests for load_queries_config."""

    def test_load_valid_queries(self):
        """Test loading the real queries.json config file."""
        result = load_queries_config(CONFIG_DIR / 'queries.json')
        assert isinstance(result, dict)
        assert 'NodeDetails' in result
        assert 'SQL' in result['NodeDetails']

    def test_load_queries_missing_file(self, tmp_path):
        """Test that a missing file raises ValueError."""
        with pytest.raises(ValueError, match='queries config file not found'):
            load_queries_config(tmp_path / 'nonexistent.json')

    def test_load_queries_malformed_json(self, tmp_path):
        """Test that malformed JSON raises ValueError."""
        bad_file = tmp_path / 'bad.json'
        bad_file.write_text('{invalid json}')
        with pytest.raises(ValueError, match='malformed JSON'):
            load_queries_config(bad_file)

    def test_load_queries_non_object(self, tmp_path):
        """Test that a non-object JSON raises ValueError."""
        bad_file = tmp_path / 'array.json'
        bad_file.write_text('["not", "an", "object"]')
        with pytest.raises(ValueError, match='must contain a JSON object'):
            load_queries_config(bad_file)


class TestLoadSignalsConfig:
    """Tests for load_signals_config."""

    def test_load_valid_signals(self):
        """Test loading the real signals.json config file."""
        result = load_signals_config(CONFIG_DIR / 'signals.json')
        assert isinstance(result, dict)
        assert 'NodeDetails' in result
        assert 'Signals' in result['NodeDetails']
        assert len(result['NodeDetails']['Signals']) > 0

    def test_load_signals_missing_file(self, tmp_path):
        """Test that a missing file raises ValueError."""
        with pytest.raises(ValueError, match='signals config file not found'):
            load_signals_config(tmp_path / 'nonexistent.json')

    def test_load_signals_malformed_json(self, tmp_path):
        """Test that malformed JSON raises ValueError."""
        bad_file = tmp_path / 'bad.json'
        bad_file.write_text('not json at all')
        with pytest.raises(ValueError, match='malformed JSON'):
            load_signals_config(bad_file)


class TestLoadRecommendationsConfig:
    """Tests for load_recommendations_config."""

    def test_load_valid_recommendations(self):
        """Test loading the real recommendations.json config file."""
        result = load_recommendations_config(CONFIG_DIR / 'recommendations.json')
        assert isinstance(result, dict)
        assert 'REC-001' in result
        rec = result['REC-001']
        assert 'text' in rec
        assert 'description' in rec
        assert 'effort' in rec
        assert 'documentation_links' in rec

    def test_load_recommendations_missing_file(self, tmp_path):
        """Test that a missing file raises ValueError."""
        with pytest.raises(ValueError, match='recommendations config file not found'):
            load_recommendations_config(tmp_path / 'nonexistent.json')

    def test_load_recommendations_malformed_json(self, tmp_path):
        """Test that malformed JSON raises ValueError."""
        bad_file = tmp_path / 'bad.json'
        bad_file.write_text('{key: no quotes}')
        with pytest.raises(ValueError, match='malformed JSON'):
            load_recommendations_config(bad_file)


class TestConfigLoaderWithSyntheticData:
    """Tests using synthetic config data to verify structure handling."""

    def test_queries_with_minimal_entry(self, tmp_path):
        """Test loading a minimal valid queries config."""
        config = {'TestQuery': {'SQL': 'SELECT 1'}}
        config_file = tmp_path / 'queries.json'
        config_file.write_text(json.dumps(config))
        result = load_queries_config(config_file)
        assert result['TestQuery']['SQL'] == 'SELECT 1'

    def test_signals_with_population_criteria(self, tmp_path):
        """Test loading signals config with PopulationCriteria."""
        config = {
            'TestSection': {
                'Signals': [
                    {
                        'Signal': 'test signal',
                        'Criteria': 'col > 10',
                        'PopulationCriteria': 'active = true',
                        'Recommendation': ['REC-001'],
                    }
                ]
            }
        }
        config_file = tmp_path / 'signals.json'
        config_file.write_text(json.dumps(config))
        result = load_signals_config(config_file)
        signal = result['TestSection']['Signals'][0]
        assert signal['Signal'] == 'test signal'
        assert signal['PopulationCriteria'] == 'active = true'

    def test_recommendations_with_all_fields(self, tmp_path):
        """Test loading recommendations config with all fields."""
        config = {
            'REC-TEST': {
                'text': 'Test recommendation',
                'description': 'A test description',
                'effort': 'Small',
                'documentation_links': ['https://example.com'],
            }
        }
        config_file = tmp_path / 'recommendations.json'
        config_file.write_text(json.dumps(config))
        result = load_recommendations_config(config_file)
        rec = result['REC-TEST']
        assert rec['text'] == 'Test recommendation'
        assert rec['effort'] == 'Small'
        assert rec['documentation_links'] == ['https://example.com']
