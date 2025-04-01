#!/usr/bin/env uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click>=8.1.8",
#     "tomlkit>=0.13.2"
# ]
# ///
import datetime
import json
import logging
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, NewType, Protocol

import click
import tomlkit

# Configure logging to stderr
logging.basicConfig(
    level=logging.DEBUG, format="%(levelname)s: %(message)s", stream=sys.stderr
)

Version = NewType("Version", str)
Patch = NewType("Patch", str)
GitHash = NewType("GitHash", str)


class GitHashParamType(click.ParamType):
    name = "git_hash"

    def convert(
        self, value: Any, param: click.Parameter | None, ctx: click.Context | None
    ) -> GitHash | None:
        if value is None:
            return None

        if not (8 <= len(value) <= 40):
            self.fail(f"Git hash must be between 8 and 40 characters, got {len(value)}")

        if not re.match(r"^[0-9a-fA-F]+$", value):
            self.fail("Git hash must contain only hex digits (0-9, a-f)")

        try:
            # Verify hash exists in repo
            subprocess.run(
                ["git", "rev-parse", "--verify", value], check=True, capture_output=True
            )
        except subprocess.CalledProcessError:
            self.fail(f"Git hash {value} not found in repository")

        return GitHash(value.lower())


GIT_HASH = GitHashParamType()


class Package(Protocol):
    path: Path

    def package_name(self) -> str:
        ...

    def package_version(self) -> str:
        ...

    def update_version(self, patch: Patch) -> str:
        ...


@dataclass
class NpmPackage:
    path: Path

    def package_name(self) -> str:
        with open(self.path / "package.json", "r") as f:
            return json.load(f)["name"]

    def package_version(self) -> str:
        with open(self.path / "package.json", "r") as f:
            return json.load(f)["version"]

    def update_version(self, patch: Patch) -> str:
        with open(self.path / "package.json", "r+") as f:
            data = json.load(f)
            major, minor, _ = data["version"].split(".")
            version = ".".join([major, minor, patch])
            data["version"] = version
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()
            return version


@dataclass
class PyPiPackage:
    path: Path

    def package_name(self) -> str:
        with open(self.path / "pyproject.toml") as f:
            toml_data = tomlkit.parse(f.read())
            name = toml_data.get("project", {}).get("name")
            if not name:
                raise Exception("No name in pyproject.toml project section")
            return str(name)

    def package_version(self) -> str:
        with open(self.path / "pyproject.toml") as f:
            toml_data = tomlkit.parse(f.read())
            version = toml_data.get("project", {}).get("version")
            if not version:
                raise Exception("No version in pyproject.toml project section")
            return str(version)

    def update_version(self, patch: Patch) -> str:
        # Update version in pyproject.toml
        with open(self.path / "pyproject.toml") as f:
            data = tomlkit.parse(f.read())
            # Access the version safely from tomlkit document
            project_table = data.get("project")
            if project_table is None:
                raise Exception("No project section in pyproject.toml")

            version_str = str(project_table.get("version", ""))
            major, minor, _ = version_str.split(".")
            logging.debug(f"Major version: {major}")
            version = ".".join([major, minor, patch])

            # Update the version safely
            project_table["version"] = version

        with open(self.path / "pyproject.toml", "w") as f:
            f.write(tomlkit.dumps(data))
        return version


def has_changes(path: Path, git_hash: GitHash) -> bool:
    """Check if any files changed between current state and git hash"""
    try:
        logging.debug(f"Checking changes in {path} since {git_hash}")

        # Get the repository root directory
        repo_root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        try:
            # Get the relative path from repo root to package directory
            rel_path = path.relative_to(Path(repo_root))

            # Run git diff from repo root, but filter by package path
            output = subprocess.run(
                ["git", "diff", "--name-only", git_hash, "--", str(rel_path)],
                cwd=repo_root,  # Run from repo root
                check=True,
                capture_output=True,
                text=True,
            )

            logging.debug(f"Git command: git diff --name-only {git_hash} -- {rel_path}")
            logging.debug(f"Working directory: {repo_root}")

            changed_files = [Path(f) for f in output.stdout.splitlines()]
            logging.debug(f"Changed files: {changed_files}")

            relevant_files = [
                f
                for f in changed_files
                if f.suffix in [".py", ".ts", ".toml", ".lock", ".json"]
            ]
            logging.debug(f"Relevant files: {relevant_files}")

            return len(relevant_files) >= 1
        except ValueError:
            # Handle case where path is not relative to repo_root
            logging.debug(f"Path error: {path} is not inside repo root {repo_root}")
            logging.debug("Using absolute path as fallback")

            # Use absolute path as fallback
            output = subprocess.run(
                ["git", "diff", "--name-only", git_hash],
                check=True,
                capture_output=True,
                text=True,
            )

            # Filter to only include files under the specified path
            path_str = str(path).rstrip("/") + "/"
            changed_files = [
                Path(f) for f in output.stdout.splitlines() if f.startswith(path_str)
            ]

            relevant_files = [
                f
                for f in changed_files
                if f.suffix in [".py", ".ts", ".toml", ".lock", ".json"]
            ]
            return len(relevant_files) >= 1
    except subprocess.CalledProcessError as e:
        logging.error(f"Error executing git command: {e}")
        return False


def gen_version() -> Version:
    """Generate release version based on current time"""
    now = datetime.datetime.now(datetime.UTC)
    return Version(f"{now.year}.{now.month}.{gen_patch()}")


def gen_patch() -> Patch:
    """Generate version based on current UTC timestamp"""
    now = datetime.datetime.now(datetime.UTC)
    # return Patch(f"{int(now.timestamp())}")
    return Patch(f"{now.day:02d}{now.hour:02d}{now.minute:02d}")


def find_changed_packages(directory: Path, git_hash: GitHash) -> Iterator[Package]:
    # Debug info
    logging.debug(f"Searching for changed packages in {directory} since {git_hash}")

    # List all PyPI packages
    for path in directory.glob("*/pyproject.toml"):
        logging.debug(f"Found PyPI package at {path.parent}")
        # Check if it has relevant changes
        if has_changes(path.parent, git_hash):
            yield PyPiPackage(path.parent)

    # List all NPM packages
    for path in directory.glob("*/package.json"):
        logging.debug(f"Found NPM package at {path.parent}")
        # Check if it has relevant changes
        if has_changes(path.parent, git_hash):
            yield NpmPackage(path.parent)


@click.group()
def cli():
    pass


@cli.command("update-packages")
@click.option(
    "--directory", type=click.Path(exists=True, path_type=Path), default=Path.cwd()
)
@click.argument("git_hash", type=GIT_HASH)
def update_packages(directory: Path, git_hash: GitHash) -> int:
    # Detect package type
    path = directory.resolve(strict=True)
    patch = gen_patch()

    for package in find_changed_packages(path, git_hash):
        name = package.package_name()
        version = package.update_version(patch)

        click.echo(f"{name}@{version}")

    return 0


@cli.command("generate-notes")
@click.option(
    "--directory", type=click.Path(exists=True, path_type=Path), default=Path.cwd()
)
@click.argument("git_hash", type=GIT_HASH)
def generate_notes(directory: Path, git_hash: GitHash) -> int:
    # Detect package type
    path = directory.resolve(strict=True)
    release = gen_version()

    click.echo(f"# Release: {release}")
    click.echo("")
    click.echo("## Updated packages")
    for package in find_changed_packages(path, git_hash):
        name = package.package_name()
        version = package.package_version()
        click.echo(f"- {name}@{version}")
    click.echo("")

    return 0


@cli.command("generate-version")
def generate_version() -> int:
    # Detect package type
    click.echo(gen_version())
    return 0


@cli.command("generate-matrix")
@click.option(
    "--directory", type=click.Path(exists=True, path_type=Path), default=Path.cwd()
)
@click.option("--npm", is_flag=True, default=False)
@click.option("--pypi", is_flag=True, default=False)
@click.argument("git_hash", type=GIT_HASH)
def generate_matrix(directory: Path, git_hash: GitHash, pypi: bool, npm: bool) -> int:
    # Detect package type
    path = directory.resolve(strict=True)

    changes = []
    for package in find_changed_packages(path, git_hash):
        pkg = package.path.relative_to(path)
        if npm and isinstance(package, NpmPackage):
            changes.append(str(pkg))
        if pypi and isinstance(package, PyPiPackage):
            changes.append(str(pkg))

    click.echo(json.dumps(changes))
    return 0


if __name__ == "__main__":
    sys.exit(cli())
