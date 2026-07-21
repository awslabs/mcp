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

"""Tests for the least-privilege post-connect guardrail (validate_connection).

The guardrail rejects (under the default 'enforce' policy) any connection
whose Postgres role is a superuser or a member of rds_superuser. It is
connection-agnostic: it only calls ``execute_query`` on the established
connection, so a single fake connection exercises the same contract that
both PsycopgPoolConnection and RDSDataAPIConnection satisfy.
"""

import pytest
from awslabs.postgres_mcp_server.connection.abstract_db_connection import AbstractDBConnection
from awslabs.postgres_mcp_server.server import (
    POSTGRES_PRIVILEGE_QUERY,
    PRIVILEGE_CHECK_ENFORCE,
    PRIVILEGE_CHECK_OFF,
    PRIVILEGE_CHECK_WARN,
    ConnectionValidationError,
    validate_connection,
)
from typing import Any, Dict, List, Optional
from unittest.mock import patch


def privilege_response(is_superuser: bool, is_rds_superuser: bool) -> dict:
    """Build an execute_query response matching the privilege query shape."""
    return {
        'columnMetadata': [{'name': 'is_superuser'}, {'name': 'is_rds_superuser'}],
        'records': [[{'booleanValue': is_superuser}, {'booleanValue': is_rds_superuser}]],
    }


class FakeConnection(AbstractDBConnection):
    """Minimal stand-in for a data-plane connection.

    Records the SQL passed to execute_query and returns a preset response,
    or raises a preset exception. Mirrors the {'columnMetadata','records'}
    contract that both concrete connection classes return. Subclasses
    AbstractDBConnection so it satisfies validate_connection's parameter type.
    """

    def __init__(
        self,
        response: Optional[Dict[str, Any]] = None,
        exc: Optional[Exception] = None,
    ):
        """Store the preset response/exception and init the query log."""
        super().__init__(readonly=True)
        # Coerce None to {} so the return type matches the base contract;
        # tests that omit a response always set exc and raise before returning.
        self.response: Dict[str, Any] = response if response is not None else {}
        self.exc = exc
        self.queries: List[str] = []

    async def execute_query(
        self, sql: str, parameters: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Record the SQL and return the preset response or raise the preset error."""
        self.queries.append(sql)
        if self.exc is not None:
            raise self.exc
        return self.response

    async def close(self) -> None:
        """No-op close; nothing to release for the fake connection."""
        pass

    async def check_connection_health(self) -> bool:
        """Report healthy; unused by the guardrail tests."""
        return True


class TestValidateConnectionEnforce:
    """Default 'enforce' policy: reject superuser / rds_superuser, fail-closed."""

    @pytest.mark.asyncio
    async def test_superuser_rejected(self):
        """A superuser role is rejected and the privilege query is used."""
        conn = FakeConnection(response=privilege_response(True, False))
        with pytest.raises(ConnectionValidationError) as exc:
            await validate_connection(conn, PRIVILEGE_CHECK_ENFORCE)
        assert 'superuser' in str(exc.value).lower()
        # The privilege query (not a bare SELECT 1) was used.
        assert conn.queries == [POSTGRES_PRIVILEGE_QUERY]

    @pytest.mark.asyncio
    async def test_rds_superuser_rejected(self):
        """A member of rds_superuser is rejected."""
        conn = FakeConnection(response=privilege_response(False, True))
        with pytest.raises(ConnectionValidationError) as exc:
            await validate_connection(conn, PRIVILEGE_CHECK_ENFORCE)
        assert 'rds_superuser' in str(exc.value)

    @pytest.mark.asyncio
    async def test_both_flags_rejected(self):
        """A role that is both superuser and rds_superuser is rejected."""
        conn = FakeConnection(response=privilege_response(True, True))
        with pytest.raises(ConnectionValidationError):
            await validate_connection(conn, PRIVILEGE_CHECK_ENFORCE)

    @pytest.mark.asyncio
    async def test_least_privilege_role_allowed(self):
        """A non-superuser role passes without raising."""
        conn = FakeConnection(response=privilege_response(False, False))
        # Must not raise.
        await validate_connection(conn, PRIVILEGE_CHECK_ENFORCE)
        assert conn.queries == [POSTGRES_PRIVILEGE_QUERY]

    @pytest.mark.asyncio
    async def test_query_error_fails_closed(self):
        """If the privilege query errors, enforce rejects (fail-closed)."""
        conn = FakeConnection(exc=RuntimeError('connection reset'))
        with pytest.raises(ConnectionValidationError) as exc:
            await validate_connection(conn, PRIVILEGE_CHECK_ENFORCE)
        assert 'fail-closed' in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_empty_result_fails_closed(self):
        """An empty privilege result means unverifiable -> enforce rejects."""
        conn = FakeConnection(response={'columnMetadata': [], 'records': []})
        with pytest.raises(ConnectionValidationError):
            await validate_connection(conn, PRIVILEGE_CHECK_ENFORCE)

    @pytest.mark.asyncio
    async def test_missing_expected_columns_fails_closed(self):
        """A row lacking the expected columns is unverifiable -> enforce rejects.

        Guards against silently passing a role we could not actually inspect
        (e.g. if the query result shape changed unexpectedly).
        """
        conn = FakeConnection(
            response={
                'columnMetadata': [{'name': 'something_else'}],
                'records': [[{'booleanValue': False}]],
            }
        )
        with pytest.raises(ConnectionValidationError):
            await validate_connection(conn, PRIVILEGE_CHECK_ENFORCE)


class TestValidateConnectionWarn:
    """'warn' policy: log but never raise."""

    @pytest.mark.asyncio
    async def test_superuser_warns_but_allows(self):
        """Under warn, a superuser logs a warning but is allowed."""
        conn = FakeConnection(response=privilege_response(True, False))
        with patch('awslabs.postgres_mcp_server.server.logger.warning') as mock_warn:
            await validate_connection(conn, PRIVILEGE_CHECK_WARN)
        mock_warn.assert_called_once()
        assert 'over-privileged' in mock_warn.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_query_error_warns_but_allows(self):
        """Under warn, an unverifiable check logs a warning but is allowed."""
        conn = FakeConnection(exc=RuntimeError('boom'))
        with patch('awslabs.postgres_mcp_server.server.logger.warning') as mock_warn:
            await validate_connection(conn, PRIVILEGE_CHECK_WARN)
        mock_warn.assert_called_once()

    @pytest.mark.asyncio
    async def test_unverifiable_shape_warns_but_allows(self):
        """Under warn, an unexpected result shape logs a warning but is allowed."""
        conn = FakeConnection(response={'columnMetadata': [], 'records': []})
        with patch('awslabs.postgres_mcp_server.server.logger.warning') as mock_warn:
            await validate_connection(conn, PRIVILEGE_CHECK_WARN)
        mock_warn.assert_called_once()
        assert 'unexpected result shape' in mock_warn.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_clean_role_no_warning(self):
        """A non-superuser role produces no warning under warn."""
        conn = FakeConnection(response=privilege_response(False, False))
        with patch('awslabs.postgres_mcp_server.server.logger.warning') as mock_warn:
            await validate_connection(conn, PRIVILEGE_CHECK_WARN)
        mock_warn.assert_not_called()


class TestValidateConnectionOff:
    """'off' policy: connectivity only, no privilege query."""

    @pytest.mark.asyncio
    async def test_off_runs_select_1_only(self):
        """Under off, only SELECT 1 runs; the privilege query is skipped."""
        # Even a would-be superuser response is irrelevant: off never asks.
        conn = FakeConnection(response=privilege_response(True, True))
        await validate_connection(conn, PRIVILEGE_CHECK_OFF)
        assert conn.queries == ['SELECT 1']
        assert POSTGRES_PRIVILEGE_QUERY not in conn.queries

    @pytest.mark.asyncio
    async def test_off_connectivity_failure_propagates(self):
        """Under off, a failed connectivity check still propagates."""
        conn = FakeConnection(exc=RuntimeError('cannot connect'))
        with pytest.raises(RuntimeError):
            await validate_connection(conn, PRIVILEGE_CHECK_OFF)


class TestPrivilegeQueryShape:
    """The privilege query targets the intended catalog signals."""

    def test_query_checks_superuser_and_rds_superuser(self):
        """The privilege query references rolsuper, rds_superuser, current_user, EXISTS."""
        q = POSTGRES_PRIVILEGE_QUERY.lower()
        assert 'rolsuper' in q
        assert 'rds_superuser' in q
        assert 'current_user' in q
        # Uses EXISTS so a missing rds_superuser role does not error.
        assert 'exists' in q
