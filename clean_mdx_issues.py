#!/usr/bin/env python3
"""Script to clean up MDX parsing issues in markdown files"""

import glob
import re


def clean_file(file_path):
    """Clean MDX issues in a markdown file."""
    print(f'Cleaning {file_path}')

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Fix common MDX issues
    # 1. Replace angle brackets in text that might be interpreted as JSX
    content = re.sub(r'<([^>]*?)>', r'`<\1>`', content)

    # 2. Fix any remaining curly braces that might be interpreted as JSX expressions
    content = re.sub(r'\{([^}]*?)\}', r'`{\1}`', content)

    # 3. Escape any remaining problematic characters
    content = content.replace('{{', '\\{\\{')
    content = content.replace('}}', '\\}\\}')

    # 4. Fix any malformed front matter
    lines = content.split('\n')
    if lines and lines[0].strip() == '---':
        # Find the end of front matter
        end_idx = -1
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == '---':
                end_idx = i
                break

        if end_idx > 0:
            # Clean front matter
            front_matter_lines = lines[1:end_idx]
            cleaned_front_matter = []

            for line in front_matter_lines:
                # Ensure proper YAML formatting
                if ':' in line and not line.strip().startswith('#'):
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    if value and not (value.startswith('"') and value.endswith('"')):
                        value = f'"{value}"'
                    cleaned_front_matter.append(f'{key}: {value}')
                else:
                    cleaned_front_matter.append(line)

            # Reconstruct content
            remaining_content = '\n'.join(lines[end_idx + 1 :])
            content = '---\n' + '\n'.join(cleaned_front_matter) + '\n---\n\n' + remaining_content

    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'  ✓ Cleaned {file_path}')
    else:
        print(f'  ✓ No changes needed for {file_path}')


def main():
    """Main function to clean all markdown files."""
    # Clean all markdown files in docs recursively
    md_files = glob.glob('docusaurus-site/docs/**/*.md', recursive=True)

    print(f'Found {len(md_files)} markdown files to clean')

    for file_path in md_files:
        clean_file(file_path)

    print('Cleaning complete!')


if __name__ == '__main__':
    main()
