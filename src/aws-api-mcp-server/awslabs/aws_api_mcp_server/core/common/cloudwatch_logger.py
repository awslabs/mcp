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

import boto3
import threading
import time
from ..aws.credentials import get_local_credentials
from ..common.config import AWS_API_MCP_PROFILE_NAME
from botocore.exceptions import ClientError
from loguru import logger
from typing import Optional


class CloudWatchLogSink:
    """File-like sink that forwards log lines to CloudWatch Logs.

    Notes:
    - Uses a dedicated log stream per process/host.
    - Maintains and refreshes the sequence token on InvalidSequenceToken errors.
    - Thread-safe via an internal lock.
    """

    def __init__(self, log_group_name: str, region_name: str):
        """Initialize the CloudWatchLogSink."""
        self.log_group_name = log_group_name
        self.region_name = region_name
        self.lock = threading.Lock()
        self.sequence_token: Optional[str] = None

        credentials = get_local_credentials(profile=AWS_API_MCP_PROFILE_NAME)

        self.client = boto3.client(
            'logs',
            region_name=region_name,
            aws_access_key_id=credentials.access_key_id,
            aws_secret_access_key=credentials.secret_access_key,
            aws_session_token=credentials.session_token,
        )

        self.log_stream_name = f'aws-api-mcp-server-{str(int(time.time()))}'

        self._ensure_log_group_exists()
        self._ensure_log_stream_exists()
        self._refresh_sequence_token()

    def write(self, message: str):
        """Write a log message to CloudWatch Logs."""
        if not message:
            return

        # CloudWatch Logs requires event timestamps in milliseconds
        timestamp_ms = int(time.time() * 1000)
        log_event = {'timestamp': timestamp_ms, 'message': message.rstrip('\n')}

        with self.lock:
            self._put_log_events([log_event])

    def _ensure_log_group_exists(self):
        """Ensure the log group exists."""
        try:
            self.client.create_log_group(logGroupName=self.log_group_name)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code in {'ResourceAlreadyExistsException'}:
                logger.info(f'Existing log group {self.log_group_name} was found.')
                return
            if error_code in {'AccessDeniedException'}:
                logger.warning(
                    f'Failed to create log group {self.log_group_name} due to lack of permissions: {error_code}'
                )
                return
            raise

    def _ensure_log_stream_exists(self):
        """Ensure the log stream exists."""
        try:
            self.client.create_log_stream(
                logGroupName=self.log_group_name, logStreamName=self.log_stream_name
            )
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code in {'ResourceAlreadyExistsException'}:
                logger.debug(f'Existing log stream {self.log_stream_name} was found.')
                return
            if error_code in {'AccessDeniedException'}:
                logger.warning(
                    f'Failed to create log stream {self.log_stream_name} due to lack of permissions: {error_code}'
                )
                return
            raise

    def _refresh_sequence_token(self):
        """Refresh the sequence token."""
        try:
            resp = self.client.describe_log_streams(
                logGroupName=self.log_group_name,
                logStreamNamePrefix=self.log_stream_name,
                limit=1,
            )
            streams = resp.get('logStreams', [])
            if streams and streams[0].get('uploadSequenceToken'):
                self.sequence_token = streams[0]['uploadSequenceToken']
        except ClientError:
            # Leave sequence token as None; first put may set it
            self.sequence_token = None

    def _put_log_events(self, events):
        """Put log events."""
        kwargs = {
            'logGroupName': self.log_group_name,
            'logStreamName': self.log_stream_name,
            'logEvents': events,
        }
        if self.sequence_token is not None:
            kwargs['sequenceToken'] = self.sequence_token

        try:
            response = self.client.put_log_events(**kwargs)
            self.sequence_token = response.get('nextSequenceToken')
            return
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code in {'InvalidSequenceTokenException'}:
                # Refresh token and retry once
                self._refresh_sequence_token()
                if self.sequence_token is not None:
                    kwargs['sequenceToken'] = self.sequence_token
                elif 'sequenceToken' in kwargs:
                    kwargs.pop('sequenceToken', None)
                response = self.client.put_log_events(**kwargs)
                self.sequence_token = response.get('nextSequenceToken')
                return
            if error_code in {'DataAlreadyAcceptedException'}:
                # Update token and drop duplicate
                self._refresh_sequence_token()
                return
            raise

    def flush(self):  # for compatibility with file-like interface
        """Flush the log events."""
        return
