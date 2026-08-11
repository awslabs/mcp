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

"""Knowledge base loader: discover, parse, validate, and cache JSON entries."""

from __future__ import annotations

import asyncio
import json
from .canary_knowledge_base_model import KBEntry
from datetime import date
from loguru import logger
from pathlib import Path
from typing import Optional


class CanaryKnowledgeBaseLoader:
    """Singleton loader that reads JSON KB entries once and caches them."""

    _instance: Optional[CanaryKnowledgeBaseLoader] = None

    @classmethod
    async def get_instance(cls) -> CanaryKnowledgeBaseLoader:
        """Return the singleton instance, loading KB entries off the event loop on first call."""
        if cls._instance is None:
            cls._instance = cls()
            await asyncio.to_thread(cls._instance.load)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the loader with empty entries."""
        self._entries: dict[str, KBEntry] = {}
        self._loaded: bool = False

    def load(self) -> None:
        """Discover and load all JSON files from canary_knowledge_base/runtime/ and canary_knowledge_base/environment/."""
        if self._loaded:
            return

        entries_dir = Path(__file__).parent / 'canary_knowledge_base'
        subdirs = ['runtime', 'environment']

        for subdir in subdirs:
            dir_path = entries_dir / subdir
            if not dir_path.is_dir():
                logger.warning(f'Knowledge base directory not found: {dir_path}')
                continue

            for json_file in sorted(dir_path.glob('*.json')):
                entry = self._parse_and_validate(json_file)
                if entry is not None:
                    self._entries[entry.id] = entry

        logger.info(f'Knowledge base loaded: {len(self._entries)} entries')
        self._loaded = True

    def _parse_and_validate(self, file_path: Path) -> Optional[KBEntry]:
        """Parse a single JSON file, validate against schema, return KBEntry or None."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            if data is None:
                logger.warning(f'Empty JSON file skipped: {file_path}')
                return None
            return KBEntry(**data)
        except json.JSONDecodeError as e:
            logger.warning(f'Invalid JSON syntax in {file_path}: {e}')
            return None
        except Exception as e:
            logger.warning(f'Failed to validate KB entry {file_path}: {e}')
            return None

    def _is_deprecated(self, entry: KBEntry) -> bool:
        """Check if entry is deprecated and past its deprecation_date."""
        if not entry.deprecated:
            return False
        if entry.deprecation_date is None:
            return True
        return entry.deprecation_date <= date.today()

    def get_active_entries(self) -> list[KBEntry]:
        """Return all non-deprecated entries."""
        return [entry for entry in self._entries.values() if not self._is_deprecated(entry)]

    def get_entry_by_id(self, entry_id: str) -> Optional[KBEntry]:
        """Lookup a single entry by id."""
        return self._entries.get(entry_id)
