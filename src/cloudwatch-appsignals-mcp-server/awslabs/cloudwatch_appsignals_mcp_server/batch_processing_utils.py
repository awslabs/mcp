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

"""Utilities for interactive batch processing of audit operations."""

import json
import uuid
from datetime import datetime, timezone
from loguru import logger
from typing import Any, Dict, List, Optional


# Global storage for batch sessions (in production, this would be in a database)
_batch_sessions: Dict[str, Dict[str, Any]] = {}


def create_batch_session(
    targets: List[Dict[str, Any]],
    input_obj: Dict[str, Any],
    region: str,
    banner: str,
    batch_size: int = 10,
    auto_complete: Optional[bool] = None,
) -> str:
    """Create a new batch processing session.

    Args:
        targets: List of all targets to process
        input_obj: Base input object for API calls
        region: AWS region
        banner: Banner text for display
        batch_size: Number of targets per batch
        auto_complete: If True, process all batches automatically. If False, use interactive mode.
                      If None, auto-decide based on target count.

    Returns:
        Session ID for tracking the batch processing
    """
    session_id = str(uuid.uuid4())

    # Auto-decide batch processing mode if not specified
    if auto_complete is None:
        auto_complete = len(targets) <= batch_size  # Auto-complete for small lists

    # Create batches
    batches = []
    for i in range(0, len(targets), batch_size):
        batch = targets[i : i + batch_size]
        batches.append(batch)

    now = datetime.now(timezone.utc).isoformat()
    session = {
        'session_id': session_id,
        'created_at': now,
        'last_activity': now,
        'targets': targets,
        'input_obj': input_obj,
        'batches': batches,
        'current_batch_index': 0,
        'processed_batches': [],
        'failed_batches': [],
        'all_findings': [],
        'auto_complete': auto_complete,
        'status': 'created',
    }

    _batch_sessions[session_id] = session
    logger.info(f'Created batch session {session_id} with {len(batches)} batches')

    return session_id


def get_batch_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get batch session by ID."""
    return _batch_sessions.get(session_id)


def update_batch_session_activity(session_id: str) -> None:
    """Update last activity timestamp for session."""
    if session_id in _batch_sessions:
        _batch_sessions[session_id]['last_activity'] = datetime.now(timezone.utc).isoformat()


def _create_batch_metadata(
    session: Dict[str, Any], current_batch: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Create common batch metadata."""
    current_index = session['current_batch_index']
    return {
        'batch_index': current_index + 1,
        'total_batches': len(session['batches']),
        'targets_in_batch': len(current_batch),
        'targets': current_batch,
    }


def _build_api_input(
    session: Dict[str, Any], current_batch: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Build API input object for the current batch."""
    batch_input = {
        'StartTime': datetime.fromtimestamp(session['input_obj']['StartTime'], tz=timezone.utc),
        'EndTime': datetime.fromtimestamp(session['input_obj']['EndTime'], tz=timezone.utc),
        'AuditTargets': current_batch,
    }
    if 'Auditors' in session['input_obj']:
        batch_input['Auditors'] = session['input_obj']['Auditors']
    return batch_input


def _update_session_after_batch(session: Dict[str, Any], batch_result: Dict[str, Any]) -> None:
    """Update session state after processing a batch."""
    session['current_batch_index'] += 1

    if batch_result['status'] == 'success':
        session['processed_batches'].append(batch_result)
        session['all_findings'].extend(batch_result.get('findings', []))
    else:
        session['failed_batches'].append(batch_result)

    # Update overall session status
    session['status'] = (
        'completed' if session['current_batch_index'] >= len(session['batches']) else 'in_progress'
    )


def process_next_batch(session_id: str, appsignals_client) -> Dict[str, Any]:
    """Process the next batch in the session.

    Returns:
        Dictionary with batch results and session status
    """
    session = get_batch_session(session_id)
    if not session:
        return {'error': 'Session not found or expired'}

    update_batch_session_activity(session_id)

    current_index = session['current_batch_index']
    batches = session['batches']

    if current_index >= len(batches):
        return {'error': 'No more batches to process', 'status': 'completed'}

    current_batch = batches[current_index]
    batch_metadata = _create_batch_metadata(session, current_batch)

    try:
        # Build and execute API call
        batch_input = _build_api_input(session, current_batch)
        response = appsignals_client.list_audit_findings(**batch_input)

        # Create success result
        batch_findings = response.get('AuditFindings', [])
        batch_result = {
            **batch_metadata,
            'findings_count': len(batch_findings),
            'findings': batch_findings,
            'status': 'success',
        }

    except Exception as e:
        # Create error result
        batch_result = {**batch_metadata, 'error': str(e), 'status': 'failed'}

    # Update session state and return result
    _update_session_after_batch(session, batch_result)
    return batch_result


def cleanup_batch_sessions() -> None:
    """Clean up all batch sessions from memory."""
    global _batch_sessions

    initial_count = len(_batch_sessions)
    _batch_sessions.clear()
    logger.info(f'Cleaned up all {initial_count} batch sessions')


def format_batch_result(batch_result: Dict[str, Any], session: Dict[str, Any]) -> str:
    """Format batch processing result for user display with essential information only."""
    batch_index = batch_result['batch_index']
    total_batches = batch_result['total_batches']

    if batch_result.get('error'):
        return f'❌ Batch {batch_index}/{total_batches} failed: {batch_result["error"]}'

    findings_count = len(batch_result.get('findings', []))

    if findings_count == 0:
        status = f'✅ Batch {batch_index}/{total_batches}: {batch_result["targets_in_batch"]} services healthy'
        if batch_index < total_batches:
            status += f" | Continue: continue_audit_batch('{session['session_id']}')"
        return status

    # Keep full JSON for MCP observation when findings exist
    findings_json = json.dumps(batch_result['findings'], indent=2, default=str)
    return f'⚠️ Batch {batch_index}/{total_batches}: {findings_count} findings\n```\n{findings_json}\n```'
