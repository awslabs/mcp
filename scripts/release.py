#!/usr/bin/env uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click>=8.1.8",
#     "tomlkit>=0.13.2"
# ]
# ///
import sys
import re
import click
from pathlib import Path
import json
import tomlkit
import datetime
import subprocess
from dataclasses import dataclass
from typing import Any, Iterator, NewType, Protocol


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

    def package_name(self) -> str: ...

    def package_version(self) -> str: ...

    def update_version(self, patch: Patch) -> str: ...


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
            major, minor, _ = data["project"]["version"].split(".")
            print(f"DEBUG: {major}")
            version = ".".join([major, minor, patch])
            data["project"]["version"] = version

        with open(self.path / "pyproject.toml", "w") as f:
            f.write(tomlkit.dumps(data))
        return version

def has_changes(path: Path, git_hash: GitHash) -> bool:
    """Check if any files changed between current state and git hash"""
    try:
        output = subprocess.run(
            ["git", "diff", "--name-only", git_hash, "--", "."],
            cwd=path,
            check=True,
            capture_output=True,
            text=True,
        )

        changed_files = [Path(f) for f in output.stdout.splitlines()]
        relevant_files = [f for f in changed_files if f.suffix in [".py", ".ts"]]
        return len(relevant_files) >= 1
    except subprocess.CalledProcessError:
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
    for path in directory.glob("*/package.json"):
        if has_changes(path.parent, git_hash):
            yield NpmPackage(path.parent)
    for path in directory.glob("*/pyproject.toml"):
        if has_changes(path.parent, git_hash):
            yield PyPiPackage(path.parent)


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
