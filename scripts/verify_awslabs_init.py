#!/usr/bin/env uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click>=8.1.8",
#     "tomlkit>=0.13.2"
# ]
# ///
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import click
import logging
import sys
from pathlib import Path


FILE_CONTENTS = """# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This file is part of the awslabs namespace.
# It is intentionally minimal to support PEP 420 namespace packages.
__path__ = __import__('pkgutil').extend_path(__path__, __name__)
"""


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    stream=sys.stderr,
)


@click.command()
@click.argument('directory', type=click.Path(exists=True, file_okay=False, dir_okay=True))
def main(directory: str) -> int:
    """Check if directory has awslabs subdirectory with correct __init__.py."""
    dir_path = Path(directory)
    awslabs_dir = dir_path / 'awslabs'
    click.echo(f'Looking {directory}')

    if not awslabs_dir.exists():
        click.echo(f'✓ No awslabs directory in {directory}')
        return 0

    init_file = awslabs_dir / '__init__.py'

    if not init_file.exists():
        click.echo(f'✗ Missing: {init_file}', err=True)
        return 1

    try:
        with open(init_file, 'r') as f:
            current_content = f.read()

        if current_content != FILE_CONTENTS:
            click.echo(f'✗ Mismatch: {init_file}', err=True)
            return 1

        click.echo(f'✓ OK: {init_file}')
        return 0
    except Exception as e:
        click.echo(f'✗ Error reading {init_file}: {e}', err=True)
        return 1


if __name__ == '__main__':
    main()
