#!/usr/bin/env python3
"""
Script to verify that README files correctly reference package names from pyproject.toml files.

This script extracts the package name from a pyproject.toml file and checks if the README.md
file in the same directory correctly references this package name in installation instructions.
"""

import argparse
import base64
import json
import re
import sys
import urllib.parse
from pathlib import Path
from typing import List, Tuple

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        print("Error: tomllib (Python 3.11+) or tomli package is required", file=sys.stderr)
        sys.exit(1)


def extract_package_name(pyproject_path: Path) -> str:
    """Extract the package name from pyproject.toml file."""
    try:
        with open(pyproject_path, 'rb') as f:
            data = tomllib.load(f)
        return data['project']['name']
    except (FileNotFoundError, KeyError) as e:
        raise ValueError(f"Failed to extract package name from {pyproject_path}: {e}")
    except Exception as e:
        # Handle both tomllib.TOMLDecodeError and tomli.TOMLDecodeError
        if "TOML" in str(type(e).__name__):
            raise ValueError(f"Failed to parse TOML file {pyproject_path}: {e}")
        else:
            raise ValueError(f"Failed to extract package name from {pyproject_path}: {e}")


def extract_package_from_base64_config(config_b64: str) -> List[str]:
    """Extract package names from Base64 encoded or URL-encoded JSON config."""
    try:
        # First, try to URL decode in case it's URL-encoded
        try:
            config_b64 = urllib.parse.unquote(config_b64)
        except Exception:
            pass  # If URL decoding fails, use original string
        
        # Try to parse as JSON directly first (for URL-encoded JSON)
        try:
            config = json.loads(config_b64)
        except json.JSONDecodeError:
            # If not JSON, try Base64 decoding
            config_json = base64.b64decode(config_b64).decode('utf-8')
            config = json.loads(config_json)
        
        # Look for package names in the config
        package_names = []
        
        # Check command field
        if 'command' in config and config['command'] in ['uvx', 'uv']:
            if 'args' in config and config['args']:
                for arg in config['args']:
                    if '@' in arg and '.' in arg:
                        package_names.append(arg)
        
        return package_names
    except Exception:
        # If we can't decode, return empty list
        return []


def find_package_references_in_readme(readme_path: Path, verbose: bool = False) -> List[str]:
    """Find all package name references in the README file."""
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        return []
    
    # More specific patterns for package references in installation instructions
    patterns = [
        # uvx/uv tool run patterns with @version
        r'uvx\s+([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+)',
        r'uv\s+tool\s+run\s+--from\s+([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+)',
        # JSON configuration patterns with @version
        r'"([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+)"',
        # Package names in JSON config (without version)
        r'"([a-zA-Z0-9._-]+)"\s*:\s*{[^}]*"command"\s*:\s*"uvx"',
        # Docker image patterns
        r'docker\s+run[^"]*"([a-zA-Z0-9._/-]+)"',
        # Cursor installation links (name parameter in URL)
        r'cursor\.com/en/install-mcp\?name=([a-zA-Z0-9._-]+)',
        # VS Code installation links (name parameter in URL)
        r'vscode\.dev/redirect/mcp/install\?name=([^&]+)',
        # Base64 encoded config in URLs (contains package names) - handled separately
        # r'config=([^&\s]+)',  # Moved to separate handling
    ]
    
    references = []
    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
        references.extend(matches)
    
    # Handle Base64/URL-encoded configs specially
    config_patterns = re.findall(r'config=([^&\s)]+)', content, re.IGNORECASE)
    for config_str in config_patterns:
        config_packages = extract_package_from_base64_config(config_str)
        references.extend(config_packages)
        # Remove the original config string from references if it was added by regex
        if config_str in references:
            references.remove(config_str)
    
    # Filter out common false positives
    filtered_references = []
    for ref in references:
        # Skip very short references (likely false positives)
        if len(ref) < 3:
            continue
        # Skip common non-package words
        if ref.lower() in ['-e', '--', 'pip', 'uv', 'uvx', 'docker', 'run', 'install', 'mcpservers', 'command', 'args', 'env']:
            continue
        # Skip if it looks like a command line flag
        if ref.startswith('-'):
            continue
        # Skip if it's clearly a JSON key (camelCase)
        if ref.islower() and len(ref) > 5 and any(c.isupper() for c in ref):
            continue
        # Skip if it doesn't contain dots (package names usually have dots)
        if '.' not in ref and '@' not in ref:
            continue
        filtered_references.append(ref)
    
    return filtered_references


def verify_package_name_consistency(package_name: str, references: List[str]) -> Tuple[bool, List[str]]:
    """Verify that package references match the actual package name."""
    # Extract just the package name part (without version)
    base_package_name = package_name.split('@')[0] if '@' in package_name else package_name
    
    issues = []
    
    for ref in references:
        # Extract package name from reference (remove version if present)
        ref_package = ref.split('@')[0] if '@' in ref else ref
        
        if ref_package != base_package_name:
            issues.append(f"Package name mismatch: found '{ref_package}' but expected '{base_package_name}'")
    
    return len(issues) == 0, issues


def main():
    """Main function to verify package name consistency."""
    parser = argparse.ArgumentParser(
        description="Verify that README files correctly reference package names from pyproject.toml"
    )
    parser.add_argument(
        "package_dir",
        help="Path to the package directory (e.g., src/amazon-neptune-mcp-server)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    package_dir = Path(args.package_dir)
    pyproject_path = package_dir / "pyproject.toml"
    readme_path = package_dir / "README.md"
    
    if not package_dir.exists():
        print(f"Error: Package directory '{package_dir}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    if not pyproject_path.exists():
        print(f"Error: pyproject.toml not found in '{package_dir}'", file=sys.stderr)
        sys.exit(1)
    
    if not readme_path.exists():
        print(f"Warning: README.md not found in '{package_dir}'", file=sys.stderr)
        sys.exit(0)
    
    try:
        # Extract package name from pyproject.toml
        package_name = extract_package_name(pyproject_path)
        if args.verbose:
            print(f"Package name from pyproject.toml: {package_name}")
        
        # Find package references in README
        references = find_package_references_in_readme(readme_path, args.verbose)
        if args.verbose:
            print(f"Found {len(references)} package references in README")
            for ref in references:
                print(f"  - {ref}")
        
        # Verify consistency
        is_consistent, issues = verify_package_name_consistency(package_name, references)
        
        if is_consistent:
            print(f"✅ Package name verification passed for {package_name}")
            if args.verbose:
                print("All package references in README match the package name from pyproject.toml")
        else:
            print(f"❌ Package name verification failed for {package_name}")
            for issue in issues:
                print(f"  - {issue}")
            sys.exit(1)
            
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
