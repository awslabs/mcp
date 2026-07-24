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

"""Credential-material scanning for the integration harness.

The scanner is registered with the exact secret values the harness knows (the STS
temporary credentials it observes and the bearer/JWT tokens it mints for test callers)
and reports a finding whenever any registered value appears verbatim in scanned text.
A finding carries only the material type and the location - never the offending value -
so findings and error messages can be logged and written to disk safely.
"""

import enum
import os
import pathlib
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass


class CredentialMaterialType(enum.Enum):
    """Categories of Credential_Material the harness must never leak."""

    SECRET_ACCESS_KEY = 'secret_access_key'  # pragma: allowlist secret
    SESSION_TOKEN = 'session_token'  # pragma: allowlist secret
    BEARER_TOKEN = 'bearer_token'  # pragma: allowlist secret


@dataclass(frozen=True)
class CredentialFinding:
    """A detected occurrence of registered Credential_Material.

    A finding intentionally records only the material type and the location where it was
    found. It NEVER carries the offending value, so it is safe to log, raise, or persist.
    """

    material_type: CredentialMaterialType
    location: str


class CredentialMaterialScanner:
    """Detects registered Credential_Material appearing verbatim in text.

    The scanner is constructed with a mapping of material type to the concrete secret
    values of that type. Empty or blank registered values are ignored so that an empty
    registration never matches all text.
    """

    def __init__(self, secrets: Mapping[CredentialMaterialType, Sequence[str]]) -> None:
        """Register the secret values to scan for, grouped by material type.

        Args:
            secrets: Mapping of each ``CredentialMaterialType`` to the concrete secret
                values of that type. Empty or blank values are ignored.
        """
        # Preserve (type, value) pairs, dropping empty/blank registrations up front so an
        # empty registration can never match. Order is preserved for deterministic output.
        self._registered: list[tuple[CredentialMaterialType, str]] = [
            (material_type, value)
            for material_type, values in secrets.items()
            for value in values
            if value and value.strip()
        ]

    def scan(self, text: str, location: str) -> list[CredentialFinding]:
        """Return one finding per registered value that appears verbatim in ``text``.

        Args:
            text: The text to scan (for example captured stdout or a response body).
            location: A human-readable name for where the text came from (for example
                ``'stdout'``, ``'response-body'``, or ``'inventory.json'``).

        Returns:
            A list with one ``CredentialFinding`` per registered value that occurs as a
            substring of ``text``. Empty when nothing is found.
        """
        return [
            CredentialFinding(material_type=material_type, location=location)
            for material_type, value in self._registered
            if value in text
        ]

    def assert_clean(self, text: str, location: str) -> None:
        """Raise ``AssertionError`` if any registered Credential_Material is present.

        The raised message names the material type(s) and the location but NEVER the
        offending value itself.

        Args:
            text: The text to scan.
            location: A human-readable name for where the text came from.

        Raises:
            AssertionError: If one or more registered values appear in ``text``. The
                message identifies the material type and location without the value.
        """
        findings = self.scan(text, location)
        if findings:
            types = ', '.join(sorted({finding.material_type.value for finding in findings}))
            raise AssertionError(
                f'Credential material detected at {location!r}: {types} (value redacted)'
            )


def safe_write(
    path: 'str | pathlib.Path',
    text: str,
    scanner: CredentialMaterialScanner,
) -> pathlib.Path:
    """Write ``text`` to ``path`` only after the scanner proves it clean.

    The text is scanned with ``scanner`` before any bytes touch disk. If any registered
    Credential_Material appears verbatim, ``scanner.assert_clean`` raises and nothing is
    written, so no on-disk artifact can ever contain the offending value. The raised
    message names the material type and location (the path) but NEVER the value itself.

    When the text is clean it is written atomically: the content is first written to a
    temporary file in the same directory and then moved into place with an atomic replace,
    so a reader never observes a partially written artifact.

    Args:
        path: Destination path for the artifact, as a ``str`` or ``pathlib.Path``.
        text: The content to persist (for example a captured-output file or report).
        scanner: The ``CredentialMaterialScanner`` registered with the harness's secrets.

    Returns:
        The resolved ``pathlib.Path`` that was written.

    Raises:
        AssertionError: If ``text`` contains any registered Credential_Material. The
            message identifies the material type and the path without the value.
    """
    target = pathlib.Path(path)
    # Scan before writing so a detected leak refuses the write entirely. The path is the
    # location, keeping the failure message type+location only (never the value).
    scanner.assert_clean(text, str(target))

    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)

    # Write to a temporary file in the same directory, then atomically replace the target
    # so no partial artifact is ever observable on disk.
    fd, tmp_name = tempfile.mkstemp(dir=parent, prefix=f'.{target.name}.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as tmp_file:
            tmp_file.write(text)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        os.replace(tmp_name, target)
    except BaseException:
        # Best-effort cleanup of the temp file if the replace never happened.
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise

    return target
