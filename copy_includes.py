#!/usr/bin/env python3
"""Script to copy include statements from original docs to Docusaurus server files."""

import glob
import os


def copy_includes():
    """Copy include statements from original docs to Docusaurus files."""
    # Get all original server files
    original_files = glob.glob('docs/servers/*.md')

    print(f'Found {len(original_files)} original server files')

    for original_file in original_files:
        # Get the filename
        filename = os.path.basename(original_file)
        docusaurus_file = f'docusaurus-site/docs/servers/{filename}'

        print(f'Processing {filename}')

        # Read original file
        try:
            with open(original_file, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except Exception as e:
            print(f'  ✗ Error reading {original_file}: {e}')
            continue

        # Read Docusaurus file
        try:
            with open(docusaurus_file, 'r', encoding='utf-8') as f:
                docusaurus_content = f.read()
        except Exception as e:
            print(f'  ✗ Error reading {docusaurus_file}: {e}')
            continue

        # Extract frontmatter from Docusaurus file
        lines = docusaurus_content.split('\n')
        frontmatter_end = -1
        in_frontmatter = False

        for i, line in enumerate(lines):
            if line.strip() == '---':
                if not in_frontmatter:
                    in_frontmatter = True
                else:
                    frontmatter_end = i
                    break

        if frontmatter_end == -1:
            print(f'  ✗ No frontmatter found in {docusaurus_file}')
            continue

        # Get frontmatter
        frontmatter = '\n'.join(lines[: frontmatter_end + 1])

        # Extract include statement from original file
        original_lines = original_content.split('\n')
        include_line = None

        for line in original_lines:
            if '{%include' in line or '{% include' in line:
                include_line = line
                break

        if not include_line:
            print(f'  ✗ No include statement found in {original_file}')
            continue

        # Combine frontmatter with include statement
        new_content = frontmatter + '\n\n' + include_line + '\n'

        # Write to Docusaurus file
        try:
            with open(docusaurus_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f'  ✓ Updated {docusaurus_file}')
        except Exception as e:
            print(f'  ✗ Error writing {docusaurus_file}: {e}')


if __name__ == '__main__':
    copy_includes()
    print('Include copying complete!')
