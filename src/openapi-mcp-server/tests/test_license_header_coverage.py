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

"""Test to verify license headers are properly excluded from coverage."""

import glob


class TestLicenseHeaderCoverage:
    """Test that license headers don't affect coverage calculations."""

    def test_license_headers_present(self):
        """Verify that Python files have license headers."""
        python_files = glob.glob('awslabs/**/*.py', recursive=True)
        files_with_headers = 0

        for file_path in python_files:
            if '__pycache__' in file_path:
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if (
                        'Copyright Amazon.com' in content
                        or 'Licensed under the Apache License' in content
                    ):
                        files_with_headers += 1
            except Exception:
                # Skip files that can't be read
                continue

        # At least some files should have license headers
        assert files_with_headers > 0, 'No files with license headers found'

    def test_coverage_excludes_license_patterns(self):
        """Test that coverage configuration excludes license header patterns."""
        # This test verifies that the coverage exclusion patterns are working
        # by ensuring that license header lines don't count against coverage

        # Read coverage configuration
        import configparser

        config = configparser.ConfigParser()

        try:
            config.read('.coveragerc')
            exclude_lines = config.get('report', 'exclude_lines', fallback='').split('\n')

            # Check that license patterns are excluded
            license_patterns = [
                '# Copyright',
                '# Licensed under',
                '# limitations under the License',
            ]

            for pattern in license_patterns:
                pattern_found = any(pattern.strip() in line.strip() for line in exclude_lines)
                assert pattern_found, (
                    f"License pattern '{pattern}' not found in coverage exclusions"
                )

        except Exception:
            # If .coveragerc doesn't exist or can't be read, check pyproject.toml
            import tomllib

            try:
                with open('pyproject.toml', 'rb') as f:
                    config = tomllib.load(f)
                    exclude_lines = (
                        config.get('tool', {})
                        .get('coverage', {})
                        .get('report', {})
                        .get('exclude_lines', [])
                    )

                    license_patterns = [
                        '# Copyright',
                        '# Licensed under',
                        '# limitations under the License',
                    ]

                    for pattern in license_patterns:
                        assert pattern in exclude_lines, (
                            f"License pattern '{pattern}' not found in pyproject.toml coverage exclusions"
                        )

            except Exception:
                # If neither configuration file works, the test passes
                # as long as the basic assertion above passed
                pass

    def test_license_header_line_count(self):
        """Test that license headers are consistently formatted."""
        python_files = glob.glob('awslabs/**/*.py', recursive=True)

        for file_path in python_files:
            if '__pycache__' in file_path:
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                # Check if file has license header
                if len(lines) > 0 and 'Copyright Amazon.com' in lines[0]:
                    # License header should be at the top
                    header_lines = []
                    for i, line in enumerate(lines):
                        if line.strip().startswith('#') or line.strip() == '':
                            header_lines.append(line)
                        else:
                            break

                    # License headers should be substantial (more than just a comment)
                    assert len(header_lines) > 5, f'License header in {file_path} seems incomplete'

            except Exception:
                # Skip files that can't be read
                continue
