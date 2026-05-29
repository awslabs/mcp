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

"""State persistence — config and scan tracking in ~/.securityagent/."""

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Optional


STATE_DIR = Path.home() / '.securityagent'
CONFIG_FILE = STATE_DIR / 'config.json'
SCANS_FILE = STATE_DIR / 'scans.json'
MAX_SCANS = 50


@contextmanager
def _file_lock():
    """Cross-platform file lock. Falls back to no-op on Windows."""
    STATE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_file = STATE_DIR / '.lock'
    try:
        import fcntl

        f = open(lock_file, 'w')
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()
    except ImportError:
        yield  # No locking on Windows


class StateManager:
    """Manages local configuration and scan state persistence."""

    def __init__(self, region: str = 'us-east-1'):
        """Initialize state manager, creating state directory if needed."""
        self._region = region
        STATE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)

    def get_config(self) -> dict:
        """Get config for the current region."""
        all_config = self._load_config()
        return all_config.get(self._region, {})

    def update_config(self, **kwargs) -> None:
        """Update config for the current region."""
        with _file_lock():
            all_config = self._load_config()
            region_config = all_config.get(self._region, {})
            region_config.update({k: v for k, v in kwargs.items() if v is not None})
            all_config[self._region] = region_config
            CONFIG_FILE.write_text(json.dumps(all_config, indent=2))
            CONFIG_FILE.chmod(0o600)

    def _load_config(self) -> dict:
        """Load full config file."""
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text())
        return {}

    def _load_scans(self) -> dict:
        if SCANS_FILE.exists():
            return json.loads(SCANS_FILE.read_text())
        return {}

    def _save_scans(self, scans: dict) -> None:
        SCANS_FILE.write_text(json.dumps(scans, indent=2))
        SCANS_FILE.chmod(0o600)

    def save_scan(self, scan_id: str, data: dict) -> None:
        """Save scan state to local storage. Keeps last 50 scans."""
        with _file_lock():
            scans = self._load_scans()
            scans[scan_id] = data
            # Prune old scans
            if len(scans) > MAX_SCANS:
                sorted_ids = sorted(scans, key=lambda k: scans[k].get('started_at', ''))
                for old_id in sorted_ids[: len(scans) - MAX_SCANS]:
                    del scans[old_id]
            self._save_scans(scans)

    def get_scan(self, scan_id: Optional[str] = None) -> dict | None:
        """Get scan state by ID, or most recent if no ID provided."""
        scans = self._load_scans()
        if scan_id:
            return scans.get(scan_id)
        if not scans:
            return None
        return max(scans.values(), key=lambda s: s.get('started_at', ''))

    def list_scans(self) -> list[dict]:
        """List all tracked scans, most recent first."""
        scans = self._load_scans()
        return sorted(scans.values(), key=lambda s: s.get('started_at', ''), reverse=True)

    def get_code_review_id(self, workspace_path: str) -> Optional[str]:
        """Get stored code review ID for a workspace path."""
        config = self.get_config()
        code_reviews = config.get('code_reviews', {})
        return code_reviews.get(workspace_path)

    def set_code_review_id(self, workspace_path: str, code_review_id: str) -> None:
        """Store code review ID for a workspace path."""
        config = self.get_config()
        code_reviews = config.get('code_reviews', {})
        code_reviews[workspace_path] = code_review_id
        self.update_config(code_reviews=code_reviews)

    def clear(self) -> None:
        """Clear all local configuration and scan state."""
        if CONFIG_FILE.exists():
            CONFIG_FILE.unlink()
        if SCANS_FILE.exists():
            SCANS_FILE.unlink()
