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

"""Shared header name for forwarding the caller bearer token through AgentCore Runtime.

AgentCore Runtime consumes the reserved ``Authorization`` header at its JWT authorizer and
does **not** forward it to the container, even when it is added to the runtime's request
header allowlist. The multi-tenant server, however, derives the per-request tenant identity by
reading the bearer token from ``Authorization``.

To bridge this, the harness sends the bearer token in *two* headers: ``Authorization`` (which
AgentCore's authorizer validates and then strips) and this non-reserved custom header (which
AgentCore forwards to the container because it is allow-listed). The container entrypoint maps
this header back onto ``Authorization`` before the server's ``IdentityMiddleware`` runs, so the
unmodified server sees the token exactly as it expects.

The name matches AgentCore's allowlist constraint ``[A-Za-z][A-Za-z0-9_-]{0,255}``.
"""

# The non-reserved header carrying the caller's ``Bearer <token>`` value through AgentCore.
TENANT_TOKEN_HEADER = 'X-Aho-Tenant-Token'

# Explicit-credentials headers (Option A workaround for accounts that block ``sts:TagSession``).
# The server's ``explicit`` inbound mechanism reads short-lived AWS credentials directly from
# these headers and uses them as-is -- no ``sts:AssumeRole`` and no session tagging -- so it
# works in accounts whose SCPs deny ``sts:TagSession``. The harness assumes each tenant role
# (untagged) and forwards the resulting credentials in these headers; AgentCore forwards them to
# the container because they are on the runtime's request-header allowlist. The names match the
# server's ``mechanisms/explicit.py`` header names.
EXPLICIT_ACCESS_KEY_ID_HEADER = 'X-Aws-Access-Key-Id'
EXPLICIT_SECRET_ACCESS_KEY_HEADER = 'X-Aws-Secret-Access-Key'  # noqa: S105  # pragma: allowlist secret
EXPLICIT_SESSION_TOKEN_HEADER = 'X-Aws-Session-Token'  # noqa: S105 - header name, not a secret

# All three explicit-credential header names, for the AgentCore request-header allowlist.
EXPLICIT_CREDENTIAL_HEADERS = (
    EXPLICIT_ACCESS_KEY_ID_HEADER,
    EXPLICIT_SECRET_ACCESS_KEY_HEADER,
    EXPLICIT_SESSION_TOKEN_HEADER,
)
