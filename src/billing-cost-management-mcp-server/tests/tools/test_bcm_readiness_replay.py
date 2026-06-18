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

"""Replay recorded AWS responses through the real diagnose_readiness router.

Each fixture in ``tests/fixtures/bcm_readiness/*.json`` was captured from a real
account in a known state (see that directory's capture_fixtures.py and README.md).
Replaying them offline asserts that
the detection heuristics produce the expected verdict against *observed* AWS
behavior - closing the gap that hand-authored mocks cannot, since those encode
the same assumptions as the code under test.

If no fixtures have been captured yet, these tests skip (they are an additive
real-behavior gate, not a substitute for the unit suite).
"""

import glob
import json
import os
import pytest
from awslabs.billing_cost_management_mcp_server.tools import bcm_readiness_operations as ops
from botocore.exceptions import ClientError


# Absolute, normalized path to the fixtures dir (a sibling of this test's parent,
# under tests/fixtures/bcm_readiness) - resolved here so it is independent of the
# working directory the suite is run from.
_FIXTURES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'fixtures', 'bcm_readiness')
)


def _fixture_paths():
    """Return all captured fixture files (empty if none captured yet)."""
    return sorted(glob.glob(os.path.join(_FIXTURES_DIR, '*.json')))


class ReplayClient:
    """Fake boto3 client that replays a fixture's recorded calls in order.

    Each call to a method returns the next recorded response for that method, or
    re-raises the recorded ClientError - reproducing exactly what the real API
    returned when the fixture was captured.
    """

    def __init__(self, calls):
        """Group recorded calls by method name into FIFO queues."""
        self._queues = {}
        for entry in calls:
            self._queues.setdefault(entry['method'], []).append(entry)

    def __getattr__(self, method_name):
        """Return a callable replaying the next recorded result for the method."""

        def _replay(**kwargs):
            queue = self._queues.get(method_name)
            if not queue:
                raise AssertionError(f'No recorded call for {method_name!r} in fixture')
            # Use the last entry for any calls beyond what was recorded (e.g. a
            # single page replayed for a repeated paginating call).
            entry = queue.pop(0) if len(queue) > 1 else queue[0]
            if 'error' in entry:
                err = entry['error']
                raise ClientError(
                    {'Error': {'Code': err['code'], 'Message': err['message']}},
                    err['operation'],
                )
            return entry['response']

        return _replay


def _build_clients(fixture):
    """Reconstruct the client dict from a fixture's per-service call logs."""
    return {key: ReplayClient(calls) for key, calls in fixture['calls'].items()}


@pytest.mark.skipif(not _fixture_paths(), reason='No captured fixtures yet')
@pytest.mark.parametrize('path', _fixture_paths(), ids=lambda p: os.path.basename(p)[:-5])
def test_bcm_readiness_replay(path):
    """Replaying a recorded scenario reproduces its expected verdict."""
    with open(path) as handle:
        fixture = json.load(handle)

    clients = _build_clients(fixture)
    result = ops.diagnose_readiness(fixture['account_id'], fixture['intent'], clients)

    assert result['status'] == fixture['expected_status'], (
        f'{os.path.basename(path)}: expected {fixture["expected_status"]}, got {result["status"]}'
    )
    if fixture.get('expected_issue'):
        issue = (result.get('blocker') or result.get('pending_reason') or {}).get('issue')
        assert issue == fixture['expected_issue']
