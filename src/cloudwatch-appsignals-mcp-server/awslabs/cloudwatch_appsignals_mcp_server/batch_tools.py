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

"""Batch processing tools for interactive audit workflows."""

from .aws_clients import appsignals_client
from .batch_processing_utils import (
    format_batch_result,
    get_batch_session,
    process_next_batch,
)
from loguru import logger
from pydantic import Field


async def continue_audit_batch(
    batch_session_id: str = Field(
        ..., description='Session ID from previous batch processing to continue'
    ),
) -> str:
    """Continue processing the next batch in an active audit session.

    **INTERACTIVE BATCH PROCESSING TOOL**
    Use this tool to continue processing the next batch of targets in an ongoing audit session.

    **WHEN TO USE:**
    - **When there are no findings from the last batch** - Services appear healthy, continue to next batch
    - **When customer wants to continue processing next batch**

    **RETURNS:**
    - Results from the next batch with progress information
    - Full JSON findings for MCP observation and service name extraction
    - Continuation instructions if more batches remain
    - Error message if session is invalid or expired
    """
    try:
        batch_result = process_next_batch(batch_session_id, appsignals_client)
        session = get_batch_session(batch_session_id)

        if batch_result.get('error'):
            return f'Error: {batch_result["error"]}'

        if not session:
            return 'Error: Session not found or expired'

        # Format and return batch result
        formatted_result = format_batch_result(batch_result, session)

        return formatted_result

    except Exception as e:
        logger.error(f'Error in continue_audit_batch: {e}', exc_info=True)
        return f'Error: {str(e)}'
