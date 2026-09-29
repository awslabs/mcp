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

"""Redshift MCP Server constants."""

# System

# Access modes for the execute_query tool. Add new modes here and to ACCESS_MODES.
ACCESS_MODE_READ_ONLY = 'read-only'
ACCESS_MODE_READ_WRITE = 'read-write'
ACCESS_MODES = frozenset({ACCESS_MODE_READ_ONLY, ACCESS_MODE_READ_WRITE})
ACCESS_MODE_DEFAULT = ACCESS_MODE_READ_ONLY
# Skips the per-write confirmation prompt. Ignored in read-only mode.
UNSAFE_SKIP_WRITE_CONFIRMATION_DEFAULT = 'false'

CLIENT_CONNECT_TIMEOUT = 60
CLIENT_READ_TIMEOUT = 600
CLIENT_RETRIES = {'max_attempts': 5, 'mode': 'adaptive'}
CLIENT_USER_AGENT_NAME = 'awslabs/mcp/redshift-mcp-server'
LOG_LEVEL_DEFAULT = 'WARNING'
QUERY_TIMEOUT = 3600
QUERY_POLL_INTERVAL = 1
QUERY_LONG_POLL = 30

# How long an open transaction may sit idle before Redshift ends it, in seconds. Sent as the
# Data API's SessionKeepAliveSeconds, whose own ceiling is 86400.
SESSION_KEEPALIVE_DEFAULT = 600
SESSION_KEEPALIVE_MAX = 86400
# How many transactions one caller may hold open at once against one cluster and database.
MAX_OPEN_TRANSACTIONS_PER_TARGET_DEFAULT = 10
# How long to keep using the single-statement compatibility path after
# redshift-data:BatchExecuteStatement was denied, before trying the batch path again.
FALLBACK_NO_BATCH_REPROBE = 300

# The most rows one statement may return, unless MAX_RESULT_ROWS sets another. A larger result is
# refused rather than returned whole, which is more than an agent can read, or cut short, which
# reads as the whole.
MAX_RESULT_ROWS_DEFAULT = 1000

# How many pages of one result set to read before giving up on the paging ending. Not a limit on
# the result, which MAX_RESULT_ROWS is. This bounds the loop, which a service handing back a fresh
# token forever would otherwise never leave, and pages without rows never reach the row cap. Far
# above any real result, since reaching it discards everything read.
MAX_RESULT_PAGES = 10_000

# SQL guardrails

# Maximum SQL length accepted before parsing; longer input is rejected (fail closed).
MAX_SQL_LEN = 65_536

# How long the stored discovery answers every lookup, a cluster's absence included, before the
# control plane is asked again.
CLUSTER_RESOLVE_TTL = 300
