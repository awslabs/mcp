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

Regression coverage for https://github.com/awslabs/mcp/issues/2656: the script
used to hardcode a list of "safe" prefixes (asset/model/property/hierarchy) to
skip when filtering `word@something` false positives, which would have hidden
a real package reference such as ``asset-manager@latest`` had one ever been
added. The replacement filters on whether the text after ``@`` looks like a
version identifier instead of matching a fixed word list.
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

    def test_code_example_with_invalid_placeholder_is_filtered(self):
        """Doc code examples like create_asset("asset@invalid", ...) are not package refs."""
        content = 'create_asset("asset@invalid", "model-id")  # Fails: invalid characters\n'
        self.assertNotIn('asset@invalid', self._refs(content))

    def test_previously_hardcoded_prefixes_no_longer_hide_real_packages(self):
        """A real package starting with a formerly-hardcoded prefix must be detected."""
        content = '"mcpServers": {"x": {"command": "uvx", "args": ["asset-manager@latest"]}}\n'
        self.assertIn('asset-manager@latest', self._refs(content))

    def test_bare_numeric_version_is_kept(self):
        """A short numeric version tag (no dot) is still recognized as a package ref."""
        content = '"model-toolkit@2" is referenced here\n'
        self.assertIn('model-toolkit@2', self._refs(content))

    def test_non_version_suffix_is_filtered_regardless_of_prefix(self):
        """Any word@non-version token is filtered, not just the old hardcoded words."""
        content = 'create_model("model@bad-input")\n'
        self.assertNotIn('model@bad-input', self._refs(content))


if __name__ == '__main__':
    unittest.main()
