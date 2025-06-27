#!/usr/bin/env python3
"""Script to fix front matter issues in markdown files"""

import glob
import re


def fix_frontmatter(file_path):
    """Fix front matter in a markdown file."""
    print(f'Checking {file_path}')

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if file starts with front matter
    if content.startswith('---'):
        lines = content.split('\n')

        # Find the end of front matter
        end_idx = -1
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == '---':
                end_idx = i
                break

        if end_idx > 0:
            # Extract front matter and content
            front_matter_lines = lines[1:end_idx]
            remaining_content = '\n'.join(lines[end_idx + 1 :])

            # Check for malformed front matter
            needs_fix = False
            fixed_lines = []

            for line in front_matter_lines:
                # Fix lines with extra spaces before ---
                if line.strip() == '---' and line != '---':
                    needs_fix = True
                    continue  # Skip malformed closing
                elif line.strip().startswith('title:'):
                    # Ensure title is properly formatted
                    title_match = re.match(r'\s*title:\s*(.+)', line)
                    if title_match:
                        title = title_match.group(1).strip()
                        # Remove quotes if present and re-add them properly
                        title = title.strip('"\'')
                        fixed_lines.append(f'title: "{title}"')
                        if line != f'title: "{title}"':
                            needs_fix = True
                    else:
                        fixed_lines.append(line)
                else:
                    fixed_lines.append(line)

            if needs_fix:
                # Reconstruct the file
                new_content = '---\n' + '\n'.join(fixed_lines) + '\n---\n\n' + remaining_content

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)

                print(f'  ✓ Fixed front matter in {file_path}')
            else:
                print(f'  ✓ Front matter OK in {file_path}')
        else:
            print(f'  ✗ Malformed front matter in {file_path} - no closing ---')
    else:
        print(f'  ✓ No front matter in {file_path}')


def main():
    """Main function to fix all markdown files."""
    # Fix all markdown files in docs
    md_files = glob.glob('docusaurus-site/docs/**/*.md', recursive=True)

    print(f'Found {len(md_files)} markdown files to check')

    for file_path in md_files:
        fix_frontmatter(file_path)

    print('Front matter fixing complete!')


if __name__ == '__main__':
    main()
