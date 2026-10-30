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

"""Tests for loading ec2rl module definitions from YAML."""

import os
import pytest
from awslabs.ec2rescue_for_linux_mcp_server.consts import MOD_MANIFEST_NAME
from awslabs.ec2rescue_for_linux_mcp_server.yaml_loader import (
    ModuleManifestError,
    _module_from_yaml_doc,
    compute_mod_manifest,
    load_modules_from_yaml_dir,
    verify_mod_manifest,
)


class TestModuleFromYamlDoc:
    """A single bad definition must not build an unsafe module or crash."""

    def test_unsafe_arg_key_yields_none(self):
        """A module whose optional key has metacharacters is dropped (None)."""
        doc = {'name': 'evil', 'constraint': {'optional': 'x;id'}}
        assert _module_from_yaml_doc(doc) is None

    def test_leading_hyphen_arg_key_yields_none(self):
        """A leading-hyphen arg key is dropped rather than built."""
        doc = {'name': 'evil', 'constraint': {'required': '-flag'}}
        assert _module_from_yaml_doc(doc) is None

    def test_valid_doc_builds_module(self):
        """A well-formed definition builds a module with parsed arg keys."""
        doc = {
            'name': 'top',
            'constraint': {'optional': 'times since'},
        }
        module = _module_from_yaml_doc(doc)
        assert module is not None
        assert module.name == 'top'
        assert module.optional_args == ['times', 'since']

    def test_untrusted_helptext_is_sanitized(self):
        """The doc's helptext is sanitized when the module is built."""
        doc = {
            'name': 'top',
            'helptext': 'x' * 5000 + '\x00',
        }
        module = _module_from_yaml_doc(doc)
        assert module is not None
        assert len(module.helptext) <= 500
        assert '\x00' not in module.helptext


def _write_mod_dir(tmp_path, files: dict[str, str]) -> str:
    """Create a mod.d directory with the given {filename: content} and return it."""
    mod_dir = tmp_path / 'mod.d'
    mod_dir.mkdir()
    for name, content in files.items():
        (mod_dir / name).write_text(content)
    return str(mod_dir)


def _write_manifest(tmp_path, mod_dir: str) -> None:
    """Write a correct manifest as a sibling of mod_dir."""
    (tmp_path / MOD_MANIFEST_NAME).write_text(compute_mod_manifest(mod_dir))


class TestModManifest:
    """The bundled mod.d/ is verified against a checksum manifest (fail-closed)."""

    def test_matching_manifest_passes(self, tmp_path):
        """A directory that matches its manifest verifies without error."""
        mod_dir = _write_mod_dir(tmp_path, {'a.yaml': 'name: a\n', 'b.yaml': 'name: b\n'})
        _write_manifest(tmp_path, mod_dir)
        verify_mod_manifest(mod_dir)  # does not raise

    def test_modified_file_is_detected(self, tmp_path):
        """Changing a file after the manifest is written is rejected."""
        mod_dir = _write_mod_dir(tmp_path, {'a.yaml': 'name: a\n'})
        _write_manifest(tmp_path, mod_dir)
        (tmp_path / 'mod.d' / 'a.yaml').write_text('name: a\n# tampered\n')
        with pytest.raises(ModuleManifestError):
            verify_mod_manifest(mod_dir)

    def test_added_file_is_detected(self, tmp_path):
        """Adding a file not in the manifest is rejected."""
        mod_dir = _write_mod_dir(tmp_path, {'a.yaml': 'name: a\n'})
        _write_manifest(tmp_path, mod_dir)
        (tmp_path / 'mod.d' / 'evil.yaml').write_text('name: evil\n')
        with pytest.raises(ModuleManifestError):
            verify_mod_manifest(mod_dir)

    def test_removed_file_is_detected(self, tmp_path):
        """Removing a file listed in the manifest is rejected."""
        mod_dir = _write_mod_dir(tmp_path, {'a.yaml': 'name: a\n', 'b.yaml': 'name: b\n'})
        _write_manifest(tmp_path, mod_dir)
        os.remove(os.path.join(mod_dir, 'b.yaml'))
        with pytest.raises(ModuleManifestError):
            verify_mod_manifest(mod_dir)

    def test_missing_manifest_is_rejected(self, tmp_path):
        """A directory with no manifest at all is rejected (fail-closed)."""
        mod_dir = _write_mod_dir(tmp_path, {'a.yaml': 'name: a\n'})
        with pytest.raises(ModuleManifestError):
            verify_mod_manifest(mod_dir)

    def test_load_verifies_by_default(self, tmp_path):
        """load_modules_from_yaml_dir verifies the manifest by default."""
        mod_dir = _write_mod_dir(tmp_path, {'a.yaml': 'name: a\n'})
        # No manifest written -> load must fail closed.
        with pytest.raises(ModuleManifestError):
            load_modules_from_yaml_dir(mod_dir)

    def test_load_can_skip_verification(self, tmp_path):
        """verify=False lets ad-hoc directories load without a manifest."""
        mod_dir = _write_mod_dir(tmp_path, {'a.yaml': 'name: a\n'})
        modules = load_modules_from_yaml_dir(mod_dir, verify=False)
        assert 'a' in modules

    def test_manifest_is_deterministic(self, tmp_path):
        """compute_mod_manifest is stable and sorted by filename."""
        mod_dir = _write_mod_dir(tmp_path, {'b.yaml': 'name: b\n', 'a.yaml': 'name: a\n'})
        manifest = compute_mod_manifest(mod_dir)
        filenames = [line.split('  ', 1)[1] for line in manifest.splitlines()]
        assert filenames == ['a.yaml', 'b.yaml']


class TestBundledManifestIsCurrent:
    """The committed manifest must match the shipped mod.d/ (guards releases)."""

    def test_bundled_mod_dir_matches_manifest(self):
        """The real bundled mod.d/ verifies against its committed manifest."""
        from awslabs.ec2rescue_for_linux_mcp_server.server import _default_mod_dir

        verify_mod_manifest(_default_mod_dir())  # does not raise
