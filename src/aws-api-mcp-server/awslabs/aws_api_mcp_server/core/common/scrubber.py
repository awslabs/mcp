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

from typing import Any


BLOCKED_KEYWORDS = frozenset(
    [
        ('security', 'token'),
        ('secret',),
        ('session', 'token'),
        ('password',),
        ('credentials',),
    ]
)


class SensitiveDataScrubber:
    """Scrubber for removing sensitive credential information from JSON data."""

    def scrub_creds(self, json_node: Any) -> Any:
        """Recursively scrub credentials from JSON data."""
        if isinstance(json_node, dict):
            result = {}
            for key, nested_node in json_node.items():
                if self._contains_combinations(key):
                    result[key] = '*****************'
                else:
                    result[key] = self.scrub_creds(nested_node)

            return result
        elif isinstance(json_node, list):
            return [self.scrub_creds(item) for item in json_node]
        else:
            return json_node

    def _contains_combination(self, text: str, combination: tuple[str, ...]) -> bool:
        """Check if text contains all words in a combination (case-insensitive)."""
        return all(word.lower() in text.lower() for word in combination)

    def _contains_combinations(self, text: str) -> bool:
        """Check if text contains any of the blocked combinations."""
        return any(
            self._contains_combination(text, combination) for combination in BLOCKED_KEYWORDS
        )


sensitive_data_scrubber = SensitiveDataScrubber()
