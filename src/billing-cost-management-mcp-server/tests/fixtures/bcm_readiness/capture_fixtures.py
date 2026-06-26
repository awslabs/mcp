#!/usr/bin/env python
r"""Capture real AWS API responses for a readiness scenario into a fixture.

Run this ONCE per account-state, against an account known to be in that state
(see README.md in this directory for the 2-account / scenario matrix). It wraps real
boto3 clients in a recording
proxy, runs the actual ``diagnose_readiness`` against them, and writes every
API call's response/error - plus the observed verdict - to a JSON fixture.

Those fixtures are then replayed offline by ``test_bcm_readiness_replay.py``, so the
unit tests assert against *recorded real responses* instead of hand-authored
fakes. This is what validates the CE-enablement / tag / COH heuristics against
real API behavior (README Open Question #1).

All calls made are READ-ONLY (get_caller_identity, simulate_principal_policy,
get_cost_and_usage, list_cost_allocation_tags, list_enrollment_statuses).

Usage (run from the package root with the project venv):

    python tests/fixtures/bcm_readiness/capture_fixtures.py \\
        --profile <aws-profile> \\
        --account-id <12-digit-id> \\
        --intent basic_cost_visibility \\
        --state ce_not_enabled \\
        --expect-status blocked \\
        --expect-issue cost_explorer_not_enabled

Writes: tests/fixtures/bcm_readiness/<state>.json (redacted by default).
"""

import argparse
import boto3
import json
import os
import re
from awslabs.billing_cost_management_mcp_server.tools import (
    bcm_readiness_operations as ops,
)
from botocore.exceptions import ClientError
from typing import Any, Dict, Optional


# Placeholder values used when redacting PII from fixtures.
_PLACEHOLDER_ACCOUNT = '123456789012'
_PLACEHOLDER_PRINCIPAL_ID = 'AROAEXAMPLEPRINCIPALID'

# AWS access-key-style principal IDs (e.g. AROA..., AIDA..., ASIA...).
_PRINCIPAL_ID_RE = re.compile(r'\b[A-Z0-9]{4}[A-Z0-9]{12,}\b')


def _redact(
    obj: Any,
    real_account: str,
    placeholder_account: str = _PLACEHOLDER_ACCOUNT,
    session_name: Optional[str] = None,
) -> Any:
    """Recursively scrub PII from a captured fixture in place.

    Replaces the real account id everywhere, the caller session name, and
    principal ids - while preserving JSON structure, ARN shapes, error codes,
    statuses, amounts, and every other verdict-driving value the replay needs.

    Args:
        obj: The fixture value to scrub (dict, list, or scalar).
        real_account: The real 12-digit account id to replace.
        placeholder_account: The value to replace it with.
        session_name: The caller session name to replace (e.g. ``user-Isengard``).

    Returns:
        The scrubbed value (same shape as the input).
    """
    if isinstance(obj, dict):
        return {
            k: _redact(v, real_account, placeholder_account, session_name) for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_redact(v, real_account, placeholder_account, session_name) for v in obj]
    if isinstance(obj, str):
        text = obj.replace(real_account, placeholder_account)
        if session_name:
            text = text.replace(session_name, 'test-session')
        text = _PRINCIPAL_ID_RE.sub(_PLACEHOLDER_PRINCIPAL_ID, text)
        return text
    return obj


# Fixtures live next to this script (and tests/tools/test_bcm_readiness_replay.py) so they travel
# with the PR and are auto-discovered by the replay test.
FIXTURES_DIR = os.path.dirname(__file__)

# boto3 service name per client key the tool expects.
SERVICE_NAMES = {
    'sts': 'sts',
    'iam': 'iam',
    'ce': 'ce',
    'coh': 'cost-optimization-hub',
}


class RecordingClient:
    """Proxy that delegates to a real boto3 client and records every call.

    Each invoked method is logged as an ordered entry with its response, or the
    error code/operation if it raised a ClientError (so the heuristic-triggering
    exceptions are captured faithfully).
    """

    def __init__(self, real_client, log):
        """Store the real client and the shared call log for its service."""
        self._real = real_client
        self._log = log

    def __getattr__(self, method_name):
        """Return a wrapper that calls the real method and records the result."""
        real_method = getattr(self._real, method_name)

        def _recorded(**kwargs):
            entry = {'method': method_name, 'kwargs': kwargs}
            try:
                response = real_method(**kwargs)
            except ClientError as error:
                err = error.response.get('Error', {})
                entry['error'] = {
                    'code': err.get('Code', ''),
                    'message': err.get('Message', ''),
                    'operation': method_name,
                }
                self._log.append(entry)
                raise
            # Drop ResponseMetadata noise; keep the meaningful payload.
            entry['response'] = {k: v for k, v in response.items() if k != 'ResponseMetadata'}
            self._log.append(entry)
            return response

        return _recorded


def main():  # noqa: D103
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--account-id', required=True)
    parser.add_argument(
        '--intent',
        required=True,
        choices=[ops.INTENT_BASIC, ops.INTENT_TAG, ops.INTENT_OPTIMIZATION],
    )
    parser.add_argument('--state', required=True, help='Short slug, used as the fixture filename.')
    parser.add_argument('--region', default='us-east-1')
    parser.add_argument('--expect-status', choices=['ready', 'blocked', 'pending'])
    parser.add_argument('--expect-issue', default=None)
    parser.add_argument(
        '--no-redact',
        action='store_true',
        help='Keep real account id / ARNs / principal ids (default: redact for PR safety).',
    )
    args = parser.parse_args()

    session = boto3.Session(profile_name=args.profile, region_name=args.region)

    # Build recording proxies only for the clients this intent needs.
    needed = set()
    for check in ops.INTENT_CHECKS[args.intent]:
        needed.update(
            {
                'iam': {'sts', 'iam'},
                'cost_explorer': {'ce'},
                'tags': {'ce'},
                'cost_optimization_hub': {'coh'},
            }[check]
        )

    logs = {key: [] for key in needed}
    clients = {
        key: RecordingClient(session.client(SERVICE_NAMES[key]), logs[key]) for key in needed
    }

    observed_status = None
    observed_issue = None
    raised = None
    try:
        result = ops.diagnose_readiness(args.account_id, args.intent, clients)
        observed_status = result['status']
        observed_issue = (result.get('blocker') or result.get('pending_reason') or {}).get('issue')
    except Exception as exc:  # noqa: BLE001 - record whatever happened
        raised = f'{type(exc).__name__}: {exc}'

    fixture: Dict[str, Any] = {
        'state': args.state,
        'account_id': args.account_id,
        'intent': args.intent,
        'expected_status': args.expect_status or observed_status,
        'expected_issue': args.expect_issue if args.expect_issue is not None else observed_issue,
        'observed_status': observed_status,
        'observed_issue': observed_issue,
        'observed_exception': raised,
        'calls': logs,
    }

    if not args.no_redact:
        # Derive the caller session name from any recorded assumed-role ARN so it
        # too can be scrubbed (e.g. ".../Role/<session>" -> "test-session").
        session_name = None
        caller = next(
            (c for c in logs.get('sts', []) if c['method'] == 'get_caller_identity'), None
        )
        arn = (caller or {}).get('response', {}).get('Arn', '')
        if ':assumed-role/' in arn:
            session_name = arn.rsplit('/', 1)[-1] or None
        fixture = _redact(fixture, args.account_id, session_name=session_name)
        fixture['account_id'] = _PLACEHOLDER_ACCOUNT

    os.makedirs(FIXTURES_DIR, exist_ok=True)
    path = os.path.join(FIXTURES_DIR, f'{args.state}.json')
    # Match the repo's pretty-format-json pre-commit hook (sort_keys + trailing
    # newline) so freshly captured fixtures pass CI without a reformat pass.
    with open(path, 'w') as handle:
        json.dump(fixture, handle, indent=2, sort_keys=True, default=str)
        handle.write('\n')

    print(f'Wrote {path}')
    print(f'  observed: status={observed_status} issue={observed_issue} exception={raised}')
    if args.expect_status and args.expect_status != observed_status:
        print(
            f'  WARNING: expected status {args.expect_status!r} but observed '
            f'{observed_status!r} - account may not be in the {args.state!r} state.'
        )


if __name__ == '__main__':
    main()
