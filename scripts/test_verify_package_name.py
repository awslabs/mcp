#!/usr/bin/env python3
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
"""Tests for verify_package_name.py's README reference filtering.

Regression coverage for https://github.com/awslabs/mcp/issues/2656.

The old filter matched on `ref.split('@')[0].lower() in ['asset', 'model',
'property', 'hierarchy']` (an exact-equality check on the whole prefix, not a
`startswith` check). That meant a compound name like `asset-manager@latest`
was never affected by the old exclusion (its prefix is `"asset-manager"`,
which is not in the list) -- the old code already detected it correctly. The
only real gap was a package literally named `asset`, `model`, `property`, or
`hierarchy` (exact match) that had a valid version, e.g. `asset@latest`,
which the old code silently hid.

The replacement drops the word list and instead matches the single known
code-sample false positive (`asset@invalid`, from the SiteWise README's
``create_asset("asset@invalid", "model-id")`` input-validation example) by
its exact literal value.
"""

import tempfile
import unittest
from pathlib import Path
from verify_package_name import find_package_references_in_readme


class TestFindPackageReferencesInReadme(unittest.TestCase):
    """Tests for find_package_references_in_readme."""

    def _refs(self, content: str):
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.md', delete=False, encoding='utf-8'
        ) as f:
            f.write(content)
            path = Path(f.name)
        try:
            return [ref for ref, _ in find_package_references_in_readme(path)]
        finally:
            path.unlink()

    def test_known_sitewise_false_positive_is_filtered(self):
        """The documented create_asset("asset@invalid", ...) sample is not a package ref."""
        content = 'create_asset("asset@invalid", "model-id")  # Fails: invalid characters\n'
        self.assertNotIn('asset@invalid', self._refs(content))

    def test_exact_word_package_with_valid_version_is_now_detected(self):
        """A package literally named one of the old hardcoded words must be detected.

        Discriminates old vs. new behavior: the old code excluded ANY
        `asset@<version>` reference by exact-prefix match, even with a
        legitimate version. This is the actual bug the old code had.
        """
        content = '"mcpServers": {"x": {"command": "uvx", "args": ["asset@latest"]}}\n'
        self.assertIn('asset@latest', self._refs(content))

    def test_exact_word_package_property_with_numeric_version_is_now_detected(self):
        """Same discrimination as above for another formerly-hardcoded word."""
        content = '"property@2" is referenced here\n'
        self.assertIn('property@2', self._refs(content))

    def test_compound_name_starting_with_hardcoded_word_was_always_detected(self):
        """Sanity check: compound names were never broken by the old exact-match list.

        This does NOT discriminate old vs. new (both detect it), but guards
        against a future regression that reintroduces prefix/startswith
        matching instead of exact matching.
        """
        content = '"mcpServers": {"x": {"command": "uvx", "args": ["asset-manager@latest"]}}\n'
        self.assertIn('asset-manager@latest', self._refs(content))


if __name__ == '__main__':
    unittest.main()
