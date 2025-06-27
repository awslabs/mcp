#!/usr/bin/env python3
"""Script to find and remove any remaining include statements that cause MDX errors"""

import glob
import re


def fix_file(file_path):
    """Fix remaining include statements in a markdown file."""
    print(f'Checking {file_path}')

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Find and remove any remaining include statements (both with and without spaces)
    include_pattern = r'\{\%\s*include\s+"[^"]+"\s*\%\}'
    matches = re.findall(include_pattern, content)

    if matches:
        print(f'  Found {len(matches)} include statements to remove')
        for match in matches:
            print(f'    Removing: {match}')
            content = content.replace(match, '')

        # Clean up any extra blank lines
        content = re.sub(r'\n\n\n+', '\n\n', content)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f'  ✓ Fixed {file_path}')
    else:
        print(f'  ✓ No include statements found in {file_path}')


def main():
    """Main function to fix all markdown files."""
    # Fix all markdown files in docs recursively
    md_files = glob.glob('docusaurus-site/docs/**/*.md', recursive=True)

    print(f'Found {len(md_files)} markdown files to check')

    for file_path in md_files:
        fix_file(file_path)

    print('Fixing complete!')


if __name__ == '__main__':
    main()
