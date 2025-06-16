#!/usr/bin/env python3
"""
Script to update version badges in README.md from VERSION file.
Run this script after updating the VERSION file.
"""

import re
from pathlib import Path


def update_readme_version():
    """Update version badge in README.md from VERSION file."""
    # Read version from VERSION file
    version_file = Path(__file__).parent.parent / "VERSION"
    if not version_file.exists():
        print("ERROR: VERSION file not found")
        return False

    version = version_file.read_text().strip()
    print(f"Found version: {version}")

    # Read README.md
    readme_file = Path(__file__).parent.parent / "README.md"
    if not readme_file.exists():
        print("ERROR: README.md not found")
        return False

    content = readme_file.read_text()

    # Update version badge
    old_pattern = r"\[\!\[Version\]\([^)]+\)\]"
    new_badge = f"[![Version](https://img.shields.io/badge/version-{version}-green.svg)](https://github.com/wangtianren/datazone-mcp-server/releases)"

    updated_content = re.sub(old_pattern, new_badge, content)

    if updated_content != content:
        readme_file.write_text(updated_content)
        print(f"Updated README.md version badge to {version}")
        return True
    else:
        print(f"README.md already has correct version {version}")
        return False


if __name__ == "__main__":
    update_readme_version()
