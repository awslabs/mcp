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

"""Local per-task spend ledger.

A single JSON file, by design: the server is self-contained, makes no
network calls, and needs no account. The path can be overridden with the
AGENT_COST_LEDGER_PATH environment variable (used by the tests).
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path


_LOCK = threading.Lock()


def ledger_path() -> Path:
    """Return the ledger file path, honoring AGENT_COST_LEDGER_PATH."""
    override = os.environ.get('AGENT_COST_LEDGER_PATH')
    if override:
        return Path(override)
    return Path.home() / '.agent-cost-mcp-server' / 'ledger.json'


class Ledger:
    """Append-only store of priced per-task spend entries."""

    def __init__(self, path: Path | None = None) -> None:
        """Open the ledger at the given path or the default location."""
        self._path = path or ledger_path()

    def _load(self) -> list[dict]:
        if not self._path.exists():
            return []
        return json.loads(self._path.read_text() or '[]')

    def _save(self, entries: list[dict]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix('.tmp')
        tmp.write_text(json.dumps(entries, indent=2))
        tmp.replace(self._path)

    def record(
        self,
        task_id: str,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
    ) -> dict:
        """Append one priced spend entry and return it."""
        entry = {
            'task_id': task_id,
            'model_id': model_id,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'cost_usd': round(cost_usd, 6),
            'recorded_at': datetime.now(timezone.utc).isoformat(),
        }
        with _LOCK:
            entries = self._load()
            entries.append(entry)
            self._save(entries)
        return entry

    def status(self, task_id: str, budget_usd: float) -> dict:
        """Summarize a task's recorded spend against a budget."""
        if budget_usd < 0:
            raise ValueError('budget_usd must be non-negative')
        entries = [e for e in self._load() if e['task_id'] == task_id]
        spent = round(sum(e['cost_usd'] for e in entries), 6)
        return {
            'task_id': task_id,
            'spent_usd': spent,
            'budget_usd': budget_usd,
            'remaining_usd': round(budget_usd - spent, 6),
            'over_budget': spent > budget_usd,
            'calls': len(entries),
            'models_used': sorted({e['model_id'] for e in entries}),
        }
