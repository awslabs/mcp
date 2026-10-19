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

"""YAML loader for EC2 Rescue Linux module definitions in ``mod.d/``."""

import hashlib
import os
import yaml
from awslabs.ec2rescue_for_linux_mcp_server.consts import MOD_MANIFEST_NAME
from awslabs.ec2rescue_for_linux_mcp_server.ec2rl import Ec2rlModule
from loguru import logger


# The ``mod.d/`` YAML files are vendored from upstream ec2rl. Upstream opens
# each with a ``--- !ec2rlcore.module.Module`` tag, which only PyYAML's
# unsafe loader can construct. We never need the Python object, only the
# mapping, so the tag is stripped as text below before ``yaml.safe_load`` —
# never widen this to an unsafe loader.
#
# For that reason the bundled files are NOT byte-identical to upstream: the
# tag is removed and whitespace outside block scalars is trimmed so they pass
# ``check-yaml`` and the repo's whitespace hooks. Script bodies inside
# ``content:`` block scalars are preserved exactly. When vendoring a new or
# updated module, apply the same normalization (strip the tag line, trim only
# lines outside ``|``/``>`` scalars), confirm ``yaml.safe_load`` of the result
# equals the pre-normalization document, then regenerate ``mod.d.sha256`` as
# shown in ``compute_mod_manifest``.
_EC2RL_MODULE_TAG = '!ec2rlcore.module.Module'
_HASH_CHUNK_SIZE = 65536


class ModuleManifestError(Exception):
    """Raised when the bundled mod.d/ does not match its checksum manifest."""


def _sha256_file(path: str) -> str:
    """Return the hex SHA-256 of a file, read in chunks."""
    digest = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(_HASH_CHUNK_SIZE), b''):
            digest.update(chunk)
    return digest.hexdigest()


def compute_mod_manifest(mod_dir: str) -> str:
    r"""Return the manifest text for every ``*.yaml`` in ``mod_dir``.

    Format is one ``<sha256>  <filename>`` line per YAML file, sorted by
    filename, so the manifest is deterministic and diffable.

    After a legitimate change to ``mod.d/``, regenerate the sibling
    ``mod.d.sha256`` (run from the package root) so load-time verification
    keeps passing::

        uv run python -c "from awslabs.ec2rescue_for_linux_mcp_server.yaml_loader \\
            import compute_mod_manifest as c; \\
            open('awslabs/ec2rescue_for_linux_mcp_server/mod.d.sha256','w')\\
            .write(c('awslabs/ec2rescue_for_linux_mcp_server/mod.d'))"
    """
    lines = []
    for filename in sorted(os.listdir(mod_dir)):
        if not filename.endswith('.yaml'):
            continue
        digest = _sha256_file(os.path.join(mod_dir, filename))
        lines.append(f'{digest}  {filename}')
    return '\n'.join(lines) + '\n'


def verify_mod_manifest(mod_dir: str) -> None:
    """Verify ``mod_dir`` against its sibling checksum manifest.

    Raises :class:`ModuleManifestError` if the manifest is missing or any
    YAML file has been added, removed, or changed. This is fail-closed: the
    server must not start on a mismatch.
    """
    manifest_path = os.path.join(os.path.dirname(mod_dir.rstrip('/')), MOD_MANIFEST_NAME)
    if not os.path.isfile(manifest_path):
        raise ModuleManifestError(f'Module checksum manifest not found: {manifest_path}')
    with open(manifest_path, 'r', encoding='utf-8') as f:
        expected = f.read()
    actual = compute_mod_manifest(mod_dir)
    if actual != expected:
        raise ModuleManifestError(
            f'Bundled module definitions do not match {MOD_MANIFEST_NAME}; '
            'the mod.d/ directory has been modified without regenerating the '
            'manifest.'
        )


def _parse_space_separated(value: object) -> list[str]:
    """Split a whitespace-separated string; non-strings become ``[]``."""
    if not isinstance(value, str):
        return []
    return [part for part in value.split() if part]


def _parse_package(value: object) -> str:
    """First valid identifier token from the YAML ``package:`` list, or ``''``.

    Entries look like ``- atop http://...`` or ``- !!str`` (empty).
    """
    if not isinstance(value, list):
        return ''
    for entry in value:
        if not isinstance(entry, str):
            continue
        stripped = entry.strip()
        if not stripped:
            continue
        first = stripped.split()[0]
        if first and all(c.isalnum() or c in '-_' for c in first):
            return first
    return ''


def _parse_bool(value: object) -> bool:
    """Coerce bool or ``"True"``/``"False"`` strings; anything else → False."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == 'true'
    return False


def _module_from_yaml_doc(doc: dict) -> Ec2rlModule | None:
    """Build an Ec2rlModule from a parsed YAML doc; returns None if invalid."""
    if not isinstance(doc, dict):
        return None
    name = doc.get('name')
    if not isinstance(name, str) or not name:
        return None

    constraint = doc.get('constraint') or {}
    if not isinstance(constraint, dict):
        constraint = {}

    try:
        return Ec2rlModule(
            name=name,
            log_subpath=f'mod_out/run/{name}.log',
            title=str(doc.get('title') or ''),
            helptext=str(doc.get('helptext') or ''),
            required_args=_parse_space_separated(constraint.get('required')),
            optional_args=_parse_space_separated(constraint.get('optional')),
            remediation=_parse_bool(doc.get('remediation')),
            constraint_class=str(constraint.get('class') or ''),
            domain=str(constraint.get('domain') or ''),
            package=_parse_package(doc.get('package')),
            software=str(constraint.get('software') or '').strip(),
            perfimpact=_parse_bool(constraint.get('perfimpact')),
        )
    except ValueError:
        # Ec2rlModule rejects unsafe fields (bad name, arg keys with shell
        # metacharacters, etc.). Treat that module as invalid rather than
        # letting one bad definition abort the whole load.
        return None


def load_modules_from_yaml_dir(
    mod_dir: str,
    include_remediation: bool = False,
    verify: bool = True,
) -> dict[str, Ec2rlModule]:
    """Load ``*.yaml`` from ``mod_dir``; skips remediation modules unless enabled.

    When ``verify`` is true, the directory is first checked against its
    checksum manifest and :class:`ModuleManifestError` is raised on a mismatch
    (fail-closed). The server always verifies; tests that build ad-hoc
    directories pass ``verify=False``.
    """
    if not os.path.isdir(mod_dir):
        logger.warning(f'Module directory does not exist: {mod_dir}')
        return {}

    if verify:
        verify_mod_manifest(mod_dir)

    modules: dict[str, Ec2rlModule] = {}
    for filename in sorted(os.listdir(mod_dir)):
        if not filename.endswith('.yaml'):
            continue
        path = os.path.join(mod_dir, filename)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            content = content.replace(_EC2RL_MODULE_TAG, '')
            doc = yaml.safe_load(content)
        except (OSError, yaml.YAMLError) as e:
            logger.warning(f'Skipping {filename}: failed to parse YAML: {e}')
            continue

        module = _module_from_yaml_doc(doc)
        if module is None:
            logger.warning(f'Skipping {filename}: missing or invalid module name')
            continue

        if module.remediation and not include_remediation:
            logger.debug(
                f'Skipping remediation module {module.name!r} (use --remediate to enable)'
            )
            continue

        modules[module.name] = module

    logger.info(
        f'Loaded {len(modules)} ec2rl modules from {mod_dir} '
        f'(include_remediation={include_remediation})'
    )
    return modules
