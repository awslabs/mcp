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

"""Tests for StateManager."""

import json

from awslabs.security_agent_mcp_server.state import StateManager


class TestStateManager:
    """Tests for the StateManager class."""

    def test_get_config_empty(self, tmp_path, monkeypatch):
        """Returns empty dict when no config exists."""
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path
        )
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.CONFIG_FILE', tmp_path / 'config.json'
        )
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.SCANS_FILE', tmp_path / 'scans.json'
        )
        sm = StateManager()
        assert sm.get_config() == {}

    def test_update_config(self, tmp_path, monkeypatch):
        """Updates config with key-value pairs."""
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path
        )
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.CONFIG_FILE', tmp_path / 'config.json'
        )
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.SCANS_FILE', tmp_path / 'scans.json'
        )
        sm = StateManager()
        sm.update_config(agent_space_id='as-123', s3_bucket='my-bucket')
        config = sm.get_config()
        assert config['agent_space_id'] == 'as-123'
        assert config['s3_bucket'] == 'my-bucket'

    def test_update_config_ignores_none(self, tmp_path, monkeypatch):
        """Does not store None values."""
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path
        )
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.CONFIG_FILE', tmp_path / 'config.json'
        )
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.SCANS_FILE', tmp_path / 'scans.json'
        )
        sm = StateManager()
        sm.update_config(agent_space_id='as-123', service_role=None)
        config = sm.get_config()
        assert 'agent_space_id' in config
        assert 'service_role' not in config

    def test_save_and_get_scan(self, tmp_path, monkeypatch):
        """Saves and retrieves scan data."""
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path
        )
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.CONFIG_FILE', tmp_path / 'config.json'
        )
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.SCANS_FILE', tmp_path / 'scans.json'
        )
        sm = StateManager()
        sm.save_scan('scan-abc', {'scan_id': 'scan-abc', 'status': 'STARTED', 'started_at': '2026-01-01'})
        scan = sm.get_scan('scan-abc')
        assert scan['scan_id'] == 'scan-abc'
        assert scan['status'] == 'STARTED'

    def test_get_scan_latest(self, tmp_path, monkeypatch):
        """Returns most recent scan when no ID provided."""
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path
        )
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.CONFIG_FILE', tmp_path / 'config.json'
        )
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.SCANS_FILE', tmp_path / 'scans.json'
        )
        sm = StateManager()
        sm.save_scan('scan-old', {'scan_id': 'scan-old', 'started_at': '2026-01-01'})
        sm.save_scan('scan-new', {'scan_id': 'scan-new', 'started_at': '2026-01-02'})
        latest = sm.get_scan()
        assert latest['scan_id'] == 'scan-new'

    def test_list_scans(self, tmp_path, monkeypatch):
        """Lists scans in reverse chronological order."""
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path
        )
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.CONFIG_FILE', tmp_path / 'config.json'
        )
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.SCANS_FILE', tmp_path / 'scans.json'
        )
        sm = StateManager()
        sm.save_scan('scan-a', {'scan_id': 'scan-a', 'started_at': '2026-01-01'})
        sm.save_scan('scan-b', {'scan_id': 'scan-b', 'started_at': '2026-01-03'})
        sm.save_scan('scan-c', {'scan_id': 'scan-c', 'started_at': '2026-01-02'})
        scans = sm.list_scans()
        assert scans[0]['scan_id'] == 'scan-b'
        assert scans[2]['scan_id'] == 'scan-a'

    def test_clear(self, tmp_path, monkeypatch):
        """Clears all state."""
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path
        )
        cfg = tmp_path / 'config.json'
        scans = tmp_path / 'scans.json'
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.CONFIG_FILE', cfg
        )
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.SCANS_FILE', scans
        )
        sm = StateManager()
        sm.update_config(agent_space_id='as-123')
        sm.save_scan('scan-x', {'scan_id': 'scan-x', 'started_at': '2026-01-01'})
        sm.clear()
        assert sm.get_config() == {}
