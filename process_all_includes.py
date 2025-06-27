#!/usr/bin/env python3
"""
Script to process include-markdown statements in ALL markdown files
and replace them with actual content from the source files.
"""

import os
import re
import glob

def process_file(file_path):
    """Process a single markdown file to replace include statements."""
    print(f"Processing {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find include statements like {%include "../../src/server-name/README.md"%}
    include_pattern = r'\{\%include\s+"([^"]+)"\%\}'
    matches = re.findall(include_pattern, content)
    
    if not matches:
        print(f"  ✓ No includes found in {file_path}")
        return
    
    for match in matches:
        include_path = match
        # Convert relative path to absolute path from current working directory
        if include_path.startswith('../../'):
            # Remove the ../../ and use current directory
            actual_path = include_path[6:]  # Remove ../../
        else:
            actual_path = include_path
            
        print(f"  Found include: {include_path} -> {actual_path}")
        
        # Check if the file exists
        if os.path.exists(actual_path):
            try:
                with open(actual_path, 'r', encoding='utf-8') as include_file:
                    include_content = include_file.read()
                
                # Replace the include statement with the actual content
                include_statement = f'{{% include "{include_path}" %}}'
                content = content.replace(include_statement, include_content)
                print(f"  ✓ Replaced include statement with content from {actual_path}")
                
            except Exception as e:
                print(f"  ✗ Error reading {actual_path}: {e}")
        else:
            print(f"  ✗ File not found: {actual_path}")
    
    # Write the processed content back to the file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"  ✓ Processed {file_path}")

def main():
    """Main function to process all markdown files."""
    # Process all markdown files in docs recursively
    md_files = glob.glob('docusaurus-site/docs/**/*.md', recursive=True)
    
    print(f"Found {len(md_files)} markdown files to process")
    
    for file_path in md_files:
        process_file(file_path)
    
    print("Processing complete!")

if __name__ == '__main__':
    main()
