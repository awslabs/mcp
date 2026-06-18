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

"""Test fixtures shared across the package's pytest suite.

This module ensures the Amazon RDS global CA bundle is present on disk
before any test runs. The bundle is normally produced by hatch_build.py
during wheel build and ships inside the installed package; for local
test runs from a fresh checkout (where the package may be installed in
editable mode and the build hook produced the file at install time)
this is a no-op.

The check is here only to give a clean, actionable error message early
in collection if the file is missing -- otherwise tests that load the
bundle would fail with FileNotFoundError partway through the suite.
"""

import os


def _ensure_ca_bundle_present() -> None:
    r"""Fail collection early if the verified RDS CA bundle is missing.

    The bundle is produced by hatch_build.py during wheel build and is
    therefore present in any properly-installed copy of the package
    (editable or otherwise). Tests that load the bundle assume it exists.
    If the file is missing, the developer has either skipped the build
    hook (rare) or is running on a machine where the build hook could
    not reach the AWS truststore endpoint. In that case, run hatch_build
    once on a connected host:

        python hatch_build.py

    or fetch the bundle manually:

        curl -sSL https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem \\
            -o awslabs/mysql_mcp_server/connection/rds_global_bundle.pem
    """
    bundle_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'awslabs',
        'mysql_mcp_server',
        'connection',
        'rds_global_bundle.pem',
    )
    if os.path.exists(bundle_path):
        return

    raise RuntimeError(
        f'RDS CA bundle missing at {bundle_path}.\n\n'
        'The bundle is normally produced by hatch_build.py during package\n'
        'install. To produce it manually, run from the package root:\n\n'
        '    python hatch_build.py\n\n'
        'or download it directly with:\n\n'
        '    curl -sSL https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem \\\n'
        f'        -o {bundle_path}'
    )


_ensure_ca_bundle_present()
