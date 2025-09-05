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

"""Common utilities and helpers for the AWS API MCP server."""

from .cloudwatch_logger import CloudWatchLogSink
from .config import (
    DEFAULT_REGION,
    FASTMCP_LOG_LEVEL,
    CLOUDWATCH_LOG_GROUP_NAME,
    get_server_directory,
)
from .errors import AwsApiMcpError, Failure
from .helpers import as_json
from loguru import logger
from .models import (
    Context,
    Credentials,
    ProgramValidationRequest,
)
import sys


def initialize_logger():
    logger.remove()
    logger.add(sys.stderr, level=FASTMCP_LOG_LEVEL)

    # Add file sink
    log_dir = get_server_directory()
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / 'aws-api-mcp-server.log'
    logger.add(log_file, rotation='10 MB', retention='7 days')

    # Optional CloudWatch Logs sink
    try:
        if CLOUDWATCH_LOG_GROUP_NAME:
            cw_sink = CloudWatchLogSink(
                log_group_name=CLOUDWATCH_LOG_GROUP_NAME,
                region_name=str(DEFAULT_REGION),
            )
            # Forward all emitted log lines at the configured level to CloudWatch Logs
            logger.add(
                cw_sink,
                level=FASTMCP_LOG_LEVEL,
                enqueue=True,
                colorize=False,
                catch=True,
                backtrace=False,
                diagnose=False,
                format='{time:YYYY-MM-DDTHH:mm:ss.SSSZ} | {level} | {message}',
            )
    except Exception as _cw_err:
        logger.warning('CloudWatch Logs sink not initialized: {}', str(_cw_err))


__all__ = [
    'AwsApiMcpError',
    'Failure',
    'as_json',
    'logger',
    'Context',
    'Credentials',
    'ProgramValidationRequest',
]
