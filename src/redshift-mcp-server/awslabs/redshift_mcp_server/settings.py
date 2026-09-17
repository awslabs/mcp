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

"""Settings the operator sets through the environment, bounded and resolved once."""

import functools
import os
from awslabs.redshift_mcp_server.consts import (
    ACCESS_MODE_DEFAULT,
    ACCESS_MODE_READ_WRITE,
    ACCESS_MODES,
    MAX_OPEN_TRANSACTIONS_PER_TARGET_DEFAULT,
    SESSION_KEEPALIVE_DEFAULT,
    SESSION_KEEPALIVE_MAX,
    UNSAFE_SKIP_WRITE_CONFIRMATION_DEFAULT,
)
from loguru import logger


def _resolve_int_env(
    name: str, default: int, *, minimum: int = 1, maximum: int | None = None
) -> int:
    """Read an integer setting from the environment, bounded.

    Falls back on the default for anything unusable rather than failing to start, since a
    mistyped timeout should not take the server down.

    Args:
        name: The environment variable to read.
        default: The value to use when it is unset or unusable.
        minimum: The smallest accepted value.
        maximum: The largest accepted value, unbounded when None.

    Returns:
        The configured value, or the default.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default

    try:
        value = int(raw.strip())
    except ValueError:
        logger.warning(f'{name}={raw!r} is not an integer, using {default}')
        return default

    if value < minimum or (maximum is not None and value > maximum):
        bound = f'{minimum} to {maximum}' if maximum is not None else f'{minimum} or more'
        logger.warning(f'{name}={value} is outside the accepted {bound}, using {default}')
        return default

    return value


# Resolved on first use, not at import: this module is imported while the server is still
# running its own import block, before it has pointed the logger at LOG_FILE, so a warning
# raised here at import time would go to stderr and miss the file the operator is watching.
# No setting can change while the server runs, so resolving once is still right.
@functools.cache
def session_keepalive() -> int:
    """How long an open transaction may sit idle, in seconds.

    Returns:
        The configured idle timeout.
    """
    return _resolve_int_env(
        'SESSION_KEEPALIVE', SESSION_KEEPALIVE_DEFAULT, maximum=SESSION_KEEPALIVE_MAX
    )


@functools.cache
def max_open_transactions_per_target() -> int:
    """How many transactions one caller may hold open per cluster and database.

    Returns:
        The configured cap.
    """
    return _resolve_int_env(
        'MAX_OPEN_TRANSACTIONS_PER_TARGET', MAX_OPEN_TRANSACTIONS_PER_TARGET_DEFAULT
    )


# Not cached, unlike the two above: the server calls each of these once and binds the result
# to a module constant, and it does so after pointing the logger at LOG_FILE, so the warnings
# raised here reach the file the operator is watching.
def resolve_access_mode() -> str:
    """Resolve the access mode from the environment, failing closed to read-only.

    Anything other than a supported mode falls back to `ACCESS_MODE_DEFAULT`, so a
    typo cannot silently grant write access.

    Returns:
        The resolved mode, always one of `ACCESS_MODES`.
    """
    mode = os.environ.get('ACCESS_MODE', ACCESS_MODE_DEFAULT).strip().lower()

    if mode not in ACCESS_MODES:
        logger.warning(
            f'ACCESS_MODE={mode!r} is not a supported mode '
            f'({", ".join(sorted(ACCESS_MODES))}); falling back to {ACCESS_MODE_DEFAULT}.'
        )
        return ACCESS_MODE_DEFAULT

    if mode == ACCESS_MODE_READ_WRITE:
        logger.warning(
            f'ACCESS_MODE={ACCESS_MODE_READ_WRITE}: the execute_query tool can modify and '
            'delete data. Restrict the database user to the least privilege the workload needs.'
        )

    return mode


def resolve_skip_write_confirmation(access_mode: str) -> bool:
    """Resolve whether to skip the per-write confirmation prompt.

    Args:
        access_mode: The resolved access mode, used to report a no-op setting.

    Returns:
        True when `UNSAFE_SKIP_WRITE_CONFIRMATION` is `true`, else False.
    """
    value = (
        os.environ.get('UNSAFE_SKIP_WRITE_CONFIRMATION', UNSAFE_SKIP_WRITE_CONFIRMATION_DEFAULT)
        .strip()
        .lower()
    )

    if value not in {'true', 'false'}:
        logger.warning(
            f'UNSAFE_SKIP_WRITE_CONFIRMATION={value!r} is not "true" or "false"; '
            'keeping the confirmation prompt.'
        )
        return False

    if value == 'false':
        return False

    if access_mode != ACCESS_MODE_READ_WRITE:
        logger.warning(f'UNSAFE_SKIP_WRITE_CONFIRMATION=true has no effect in {access_mode} mode.')
        return False

    logger.warning(
        'UNSAFE_SKIP_WRITE_CONFIRMATION=true: writes execute without asking for '
        'confirmation. The database user privileges are the only remaining control.'
    )
    return True
