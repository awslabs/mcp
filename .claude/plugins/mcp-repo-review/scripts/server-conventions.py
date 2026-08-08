#!/usr/bin/env python3
"""Convention checker for awslabs/mcp monorepo servers.

Validates that all src/*-mcp-server/ packages follow repo conventions:
- pyproject.toml structure (name, version, entry points, commitizen)
- Version sync between pyproject.toml and __init__.py
- License headers on .py files
- Entry point conventions (server.py with main())
"""

import glob
import os
import re
import sys

try:
    import tomllib
except ImportError:
    import tomli as tomllib

LICENSE_HEADER = "# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved."

REQUIRED_PYPROJECT_FIELDS = ["name", "version", "description", "readme", "requires-python", "license"]


def find_servers(repo_root: str) -> list[str]:
    pattern = os.path.join(repo_root, "src", "*-mcp-server")
    return sorted(glob.glob(pattern))


def check_pyproject(server_dir: str) -> list[str]:
    errors = []
    path = os.path.join(server_dir, "pyproject.toml")
    if not os.path.exists(path):
        return ["pyproject.toml missing"]

    with open(path, "rb") as f:
        data = tomllib.load(f)

    project = data.get("project", {})
    for field in REQUIRED_PYPROJECT_FIELDS:
        if field not in project:
            errors.append(f"pyproject.toml missing [project].{field}")

    name = project.get("name", "")
    if name and not name.startswith("awslabs."):
        errors.append(f"pyproject.toml name '{name}' must start with 'awslabs.'")

    scripts = project.get("scripts", {})
    if not scripts:
        errors.append("pyproject.toml missing [project.scripts] entry point")
    else:
        for entry_name, entry_path in scripts.items():
            if not entry_path.endswith(":main"):
                errors.append(f"entry point '{entry_name}' should end with ':main'")
            if "server:main" not in entry_path:
                errors.append(f"entry point '{entry_name}' should reference 'server:main'")

    commitizen = data.get("tool", {}).get("commitizen", {})
    if not commitizen:
        errors.append("pyproject.toml missing [tool.commitizen] config")

    return errors


def check_version_sync(server_dir: str) -> list[str]:
    errors = []
    pyproject_path = os.path.join(server_dir, "pyproject.toml")
    if not os.path.exists(pyproject_path):
        return []

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    pyproject_version = data.get("project", {}).get("version", "")

    awslabs_dir = os.path.join(server_dir, "awslabs")
    if not os.path.isdir(awslabs_dir):
        return []

    init_files = glob.glob(os.path.join(awslabs_dir, "*", "__init__.py"))
    for init_file in init_files:
        with open(init_file) as f:
            content = f.read()
        match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            init_version = match.group(1)
            if init_version != pyproject_version:
                errors.append(
                    f"version mismatch: pyproject.toml={pyproject_version} "
                    f"vs __init__.py={init_version}"
                )

    return errors


def check_license_headers(server_dir: str) -> list[str]:
    errors = []
    for py_file in glob.glob(os.path.join(server_dir, "awslabs", "**", "*.py"), recursive=True):
        with open(py_file) as f:
            first_line = f.readline().strip()
            if first_line and first_line.startswith("#!"):
                second_line = f.readline().strip()
            else:
                second_line = None
        rel = os.path.relpath(py_file, server_dir)
        if first_line and first_line.startswith("#!"):
            if second_line and second_line != LICENSE_HEADER:
                errors.append(f"{rel}: missing license header after shebang")
        elif first_line and first_line != LICENSE_HEADER:
            errors.append(f"{rel}: missing license header")

    return errors


def check_server(server_dir: str) -> dict:
    name = os.path.basename(server_dir)
    all_errors = []
    all_errors.extend(check_pyproject(server_dir))
    all_errors.extend(check_version_sync(server_dir))
    all_errors.extend(check_license_headers(server_dir))
    return {"name": name, "errors": all_errors}


def main():
    repo_root = sys.argv[1] if len(sys.argv) > 1 else "."
    servers = find_servers(repo_root)

    if not servers:
        print(f"No servers found under {repo_root}/src/*-mcp-server")
        sys.exit(1)

    results = [check_server(s) for s in servers]

    passed = [r for r in results if not r["errors"]]
    failed = [r for r in results if r["errors"]]

    print(f"=== Convention Check: {len(passed)} passed, {len(failed)} failed ===\n")

    if failed:
        for r in failed:
            print(f"FAIL: {r['name']}")
            for e in r["errors"]:
                print(f"  - {e}")
            print()

    if not failed:
        print("All servers follow conventions.")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
