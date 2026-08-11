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
import os
import time
from contextlib import contextmanager
from filelock import FileLock
from loguru import logger
from pathlib import Path
from typing import Optional


STATE_DIR = Path.home() / '.securityagent'
CONFIG_FILE = STATE_DIR / 'config.json'
SCANS_FILE = STATE_DIR / 'scans.json'
MAX_SCANS = 50


def _atomic_write_json(path: Path, payload: dict, mode: int = 0o600) -> None:
    """Write JSON atomically: serialize to a sibling tmp file, fsync, then rename.

    Either the new contents are visible or the old contents are; never partial.
    Mitigates corruption from crashes / OOM / out-of-disk mid-write.
    """
    tmp = path.with_suffix(path.suffix + '.tmp')
    data = json.dumps(payload, indent=2)
    with open(tmp, 'w') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.chmod(tmp, mode)
    os.replace(tmp, path)


def _read_json_safely(path: Path) -> dict:
    """Read JSON, quarantining the file if it's corrupt and returning {} instead.

    A corrupt file should not brick every tool call; instead, rename it to
    `<path>.corrupt-<unix-ts>` so the user can recover it manually, log a
    warning, and let the next write rebuild a clean file.
    """
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        quarantine = path.with_suffix(path.suffix + f'.corrupt-{int(time.time())}')
        try:
            path.rename(quarantine)
        except OSError:
            # If we can't rename, at least don't crash. Next write will overwrite.
            quarantine = None
        logger.warning(
            f'Corrupt state file at {path}: {e}. '
            f'Quarantined to {quarantine}; starting from empty state.'
            if quarantine
            else f'Corrupt state file at {path}: {e}. Starting from empty state.'
        )
        return {}


@contextmanager
def _file_lock():
    """Cross-platform exclusive file lock for state read-modify-write cycles.

    Uses `filelock`, which is `fcntl` on POSIX and `msvcrt` on Windows under the
    hood. Serializes concurrent writers from separate MCP processes against the
    same `~/.securityagent/`.
    """
    STATE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = STATE_DIR / '.lock'
    with FileLock(str(lock_path)):
        yield


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
        """Update config for the current region. None values are ignored.

        Use clear_config_keys() to explicitly remove keys.
        """
        with _file_lock():
            all_config = self._load_config()
            region_config = all_config.get(self._region, {})
            region_config.update({k: v for k, v in kwargs.items() if v is not None})
            all_config[self._region] = region_config
            _atomic_write_json(CONFIG_FILE, all_config)

    def clear_config_keys(self, *keys: str) -> None:
        """Remove the given keys from the current region's config (no-op if absent)."""
        with _file_lock():
            all_config = self._load_config()
            region_config = all_config.get(self._region, {})
            changed = False
            for k in keys:
                if k in region_config:
                    del region_config[k]
                    changed = True
            if changed:
                all_config[self._region] = region_config
                _atomic_write_json(CONFIG_FILE, all_config)

    def _load_config(self) -> dict:
        """Load full config file. Quarantines + recovers from corruption."""
        return _read_json_safely(CONFIG_FILE)

    def _load_scans(self) -> dict:
        return _read_json_safely(SCANS_FILE)

    def _save_scans(self, scans: dict) -> None:
        _atomic_write_json(SCANS_FILE, scans)

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
