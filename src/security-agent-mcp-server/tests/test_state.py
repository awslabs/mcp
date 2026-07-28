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
import pytest
from awslabs.security_agent_mcp_server.state import StateManager


class TestStateManager:
    """Tests for the StateManager class."""

    def test_get_config_empty(self, tmp_path, monkeypatch):
        """Returns empty dict when no config exists."""
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path)
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
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path)
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
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path)
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
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path)
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.CONFIG_FILE', tmp_path / 'config.json'
        )
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.SCANS_FILE', tmp_path / 'scans.json'
        )
        sm = StateManager()
        sm.save_scan(
            'scan-abc', {'scan_id': 'scan-abc', 'status': 'STARTED', 'started_at': '2026-01-01'}
        )
        scan = sm.get_scan('scan-abc')
        assert scan is not None
        assert scan['scan_id'] == 'scan-abc'
        assert scan['status'] == 'STARTED'

    def test_get_scan_latest(self, tmp_path, monkeypatch):
        """Returns most recent scan when no ID provided."""
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path)
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
        assert latest is not None
        assert latest['scan_id'] == 'scan-new'

    def test_list_scans(self, tmp_path, monkeypatch):
        """Lists scans in reverse chronological order."""
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path)
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
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path)
        cfg = tmp_path / 'config.json'
        scans = tmp_path / 'scans.json'
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.CONFIG_FILE', cfg)
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.SCANS_FILE', scans)
        sm = StateManager()
        sm.update_config(agent_space_id='as-123')
        sm.save_scan('scan-x', {'scan_id': 'scan-x', 'started_at': '2026-01-01'})
        sm.clear()
        assert sm.get_config() == {}

    def test_get_scan_when_none_exist(self, tmp_path, monkeypatch):
        """get_scan() with no ID and no scans returns None."""
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path)
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.CONFIG_FILE', tmp_path / 'config.json'
        )
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.SCANS_FILE', tmp_path / 'scans.json'
        )
        sm = StateManager()
        assert sm.get_scan() is None

    def test_save_scan_prunes_to_max(self, tmp_path, monkeypatch):
        """Saving more than MAX_SCANS prunes the oldest entries."""
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path)
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.CONFIG_FILE', tmp_path / 'config.json'
        )
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.SCANS_FILE', tmp_path / 'scans.json'
        )
        # Force MAX_SCANS down so we don't have to write 51 entries.
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.MAX_SCANS', 3)

        sm = StateManager()
        for i in range(5):
            sm.save_scan(
                f'scan-{i}',
                {'scan_id': f'scan-{i}', 'started_at': f'2026-01-0{i + 1}T00:00:00Z'},
            )

        scans = sm.list_scans()
        assert len(scans) == 3
        # Most recent 3 retained
        assert {s['scan_id'] for s in scans} == {'scan-2', 'scan-3', 'scan-4'}

    def test_code_review_id_round_trip(self, tmp_path, monkeypatch):
        """get_code_review_id returns what set_code_review_id stored."""
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path)
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.CONFIG_FILE', tmp_path / 'config.json'
        )
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.SCANS_FILE', tmp_path / 'scans.json'
        )
        sm = StateManager()
        sm.update_config(agent_space_id='as-1')

        sm.set_code_review_id('/abs/workspace', 'cr-abc')
        assert sm.get_code_review_id('/abs/workspace') == 'cr-abc'
        # Different workspace returns None
        assert sm.get_code_review_id('/other') is None

    def test_clear_config_keys_removes_keys(self, tmp_path, monkeypatch):
        """clear_config_keys deletes keys that update_config(None) silently ignores."""
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path)
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.CONFIG_FILE', tmp_path / 'config.json'
        )
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.SCANS_FILE', tmp_path / 'scans.json'
        )
        sm = StateManager()
        sm.update_config(agent_space_id='as-1', service_role='arn:role', s3_bucket='b')

        # update_config(None) is a no-op (this is the bug that motivated clear_config_keys).
        sm.update_config(agent_space_id=None)
        assert sm.get_config().get('agent_space_id') == 'as-1'

        # clear_config_keys actually removes it.
        sm.clear_config_keys('agent_space_id')
        cfg = sm.get_config()
        assert 'agent_space_id' not in cfg
        # Other keys preserved.
        assert cfg['service_role'] == 'arn:role'
        assert cfg['s3_bucket'] == 'b'

    def test_clear_config_keys_missing_is_noop(self, tmp_path, monkeypatch):
        """Clearing a key that isn't present is a safe no-op."""
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path)
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.CONFIG_FILE', tmp_path / 'config.json'
        )
        monkeypatch.setattr(
            'awslabs.security_agent_mcp_server.state.SCANS_FILE', tmp_path / 'scans.json'
        )
        sm = StateManager()
        sm.update_config(agent_space_id='as-1')

        sm.clear_config_keys('does_not_exist')
        assert sm.get_config()['agent_space_id'] == 'as-1'

    def test_corrupt_config_quarantined_and_recovered(self, tmp_path, monkeypatch):
        """A truncated/garbage config.json must NOT brick the server.

        It is quarantined, get_config returns {}, and the next write rebuilds clean state.
        """
        cfg = tmp_path / 'config.json'
        scans = tmp_path / 'scans.json'
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path)
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.CONFIG_FILE', cfg)
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.SCANS_FILE', scans)

        # Simulate a half-written file (crash mid-write).
        cfg.write_text('{"us-east-1": {"agent_space_id":')

        sm = StateManager()
        # Must NOT raise.
        assert sm.get_config() == {}

        # Quarantine file exists.
        quarantined = list(tmp_path.glob('config.json.corrupt-*'))
        assert len(quarantined) == 1, f'expected one quarantine file, got {quarantined}'

        # Subsequent write rebuilds a valid config.
        sm.update_config(agent_space_id='as-recovered')
        assert sm.get_config()['agent_space_id'] == 'as-recovered'
        # And the new config.json is valid JSON.
        json.loads(cfg.read_text())

    def test_corrupt_scans_quarantined_and_recovered(self, tmp_path, monkeypatch):
        """Same defensive behavior for scans.json."""
        cfg = tmp_path / 'config.json'
        scans = tmp_path / 'scans.json'
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path)
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.CONFIG_FILE', cfg)
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.SCANS_FILE', scans)

        scans.write_text('not even json{{{')

        sm = StateManager()
        # No crash.
        assert sm.list_scans() == []
        assert list(tmp_path.glob('scans.json.corrupt-*'))

        # Save still works.
        sm.save_scan('scan-1', {'scan_id': 'scan-1', 'started_at': '2026-01-01T00:00:00Z'})
        scan = sm.get_scan('scan-1')
        assert scan is not None
        assert scan['scan_id'] == 'scan-1'

    def test_atomic_write_no_partial_file_on_crash(self, tmp_path, monkeypatch):
        """If the write step fails partway, the existing valid file is preserved.

        Atomic replace semantics — no half-written state visible.
        """
        cfg = tmp_path / 'config.json'
        scans = tmp_path / 'scans.json'
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path)
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.CONFIG_FILE', cfg)
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.SCANS_FILE', scans)

        sm = StateManager()
        sm.update_config(agent_space_id='as-original')
        original_text = cfg.read_text()

        # Force os.replace to fail mid-write.
        import awslabs.security_agent_mcp_server.state as state_mod

        def _boom(*a, **kw):
            """Boom."""
            raise OSError('disk full')

        monkeypatch.setattr(state_mod.os, 'replace', _boom)

        with pytest.raises(OSError):
            sm.update_config(agent_space_id='as-new')

        # Original file intact.
        assert cfg.read_text() == original_text

    def test_unreadable_corrupt_file_quarantine_failure_does_not_crash(
        self, tmp_path, monkeypatch
    ):
        """If even renaming the corrupt file fails, _read_json_safely still returns {}.

        Rather than raising, the function falls through gracefully.
        """
        cfg = tmp_path / 'config.json'
        scans = tmp_path / 'scans.json'
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path)
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.CONFIG_FILE', cfg)
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.SCANS_FILE', scans)

        cfg.write_text('not json')

        # Force Path.rename to fail so the quarantine path is exercised.
        import pathlib

        original_rename = pathlib.Path.rename

        def _fail_rename(self, target):
            """Fail rename."""
            raise OSError('permission denied')

        monkeypatch.setattr(pathlib.Path, 'rename', _fail_rename)
        try:
            sm = StateManager()
            assert sm.get_config() == {}
        finally:
            monkeypatch.setattr(pathlib.Path, 'rename', original_rename)

    def test_concurrent_writers_no_lost_updates(self, tmp_path, monkeypatch):
        """Two threads writing different keys in parallel: both updates persist.

        No lost-update from interleaved read-modify-write. Regression for
        the Windows no-op-lock bug.
        """
        cfg = tmp_path / 'config.json'
        scans = tmp_path / 'scans.json'
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.STATE_DIR', tmp_path)
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.CONFIG_FILE', cfg)
        monkeypatch.setattr('awslabs.security_agent_mcp_server.state.SCANS_FILE', scans)

        import threading

        sm = StateManager()
        # Seed something so both writers do read-modify-write rather than create.
        sm.update_config(seed='ok')

        N = 20
        errors: list = []

        def writer_a():
            """Writer a."""
            try:
                for i in range(N):
                    sm.update_config(**{f'a{i}': str(i)})
            except Exception as e:
                errors.append(('a', e))

        def writer_b():
            """Writer b."""
            try:
                for i in range(N):
                    sm.update_config(**{f'b{i}': str(i)})
            except Exception as e:
                errors.append(('b', e))

        ta, tb = threading.Thread(target=writer_a), threading.Thread(target=writer_b)
        ta.start()
        tb.start()
        ta.join()
        tb.join()

        assert errors == [], f'thread errors: {errors}'

        final = sm.get_config()
        # All keys from both writers landed.
        for i in range(N):
            assert final[f'a{i}'] == str(i)
            assert final[f'b{i}'] == str(i)
        # Seed not stomped.
        assert final['seed'] == 'ok'
