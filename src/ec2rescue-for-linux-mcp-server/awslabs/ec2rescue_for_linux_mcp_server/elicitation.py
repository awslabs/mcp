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

"""MCP elicitation schemas and the perfimpact consent gate."""

from __future__ import annotations

from awslabs.ec2rescue_for_linux_mcp_server.ec2rl import Ec2rlModule
from awslabs.ec2rescue_for_linux_mcp_server.responses import ModuleResponse
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import BaseModel, Field


class _ReadAllElicitation(BaseModel):
    """Schema for the read-all elicitation prompt to the user."""

    read_all: bool = Field(
        description=(
            'True reads every file under <output_dir>/gathered_out/<module>/ '
            'and returns their contents. False (the safe default; also on '
            'cancel) does NOT end the request — the server returns the file '
            'listing in `available_files`, and you then re-invoke the tool '
            'with `gathered_files=[...]` to read the specific files you want '
            '(use this to avoid binary files).'
        ),
    )


class _FetchAllConfirmation(BaseModel):
    """Schema for confirming a full (unfiltered) fetch when grep_keys is omitted."""

    confirm: bool = Field(
        description=(
            'The output of this module can be very large. Set true to '
            'fetch all output without filtering; false to abort and '
            're-invoke with specific grep_keys.'
        ),
    )


class _LargeOutputConfirmation(BaseModel):
    """Schema for confirming execution of a module with potentially large output."""

    confirm: bool = Field(
        description=(
            'This module produces potentially very large output that may '
            'consume significant context. Set true to proceed; false to '
            'abort and consider an alternative module or approach.'
        ),
    )


# Operator permission for perfimpact modules, set by main() from
# --allow-perfimpact. Denied by default (fail-closed): a runtime elicitation
# prompt is no safeguard because agentic MCP clients auto-answer it, so
# permission is a startup flag an agent cannot grant itself.
_ALLOW_PERFIMPACT: bool = False

# Operator permission to install EC2 Rescue, set by main() from
# --allow-install. Denied by default (fail-closed), and a startup flag for the
# same reason as _ALLOW_PERFIMPACT above.
_ALLOW_INSTALL: bool = False


def _perfimpact_consent_gate(
    instance_id: str,
    module: Ec2rlModule,
) -> str | None:
    """Gate a perfimpact module run on the ``--allow-perfimpact`` flag.

    Callers must check ``module.perfimpact`` first. Returns None when
    permitted, else an Aborted JSON envelope. See ``_ALLOW_PERFIMPACT`` for
    why this is a startup flag rather than a runtime prompt.
    """
    if _ALLOW_PERFIMPACT:
        logger.info(f'Module {module.name!r} is perfimpact; permitted by --allow-perfimpact.')
        return None

    logger.info(
        f'Module {module.name!r} is perfimpact but --allow-perfimpact was '
        'not set; denying (fail-closed).'
    )
    return ModuleResponse(
        instance_id=instance_id,
        module=module.name,
        status='Aborted',
        reason='perfimpact_not_permitted',
        message=(
            'This module may impact running processes (packet capture, '
            'syscall tracing, CPU profiling) and is disabled by default. '
            'An operator must restart the server with --allow-perfimpact to '
            'enable it. This is deliberately a startup flag, not a runtime '
            'consent prompt, because agentic MCP clients auto-answer '
            'elicitation without a human in the loop.'
        ),
    ).as_json()


async def _fetch_all_elicitation_gate(
    ctx: Context,
    instance_id: str,
    module: Ec2rlModule,
    key_description: str,
) -> bool:
    """Ask the user whether to fetch all output when grep_keys was omitted.

    Returns True when the user explicitly confirmed (proceed with full
    fetch). Returns False on decline, cancel, or elicitation failure —
    the caller should return an Aborted response prompting the user to
    specify keys.
    """
    message = (
        f"Module '{module.name}' output can be very large when "
        f'`grep_keys` is not specified. For targeted results, re-invoke '
        f'with `grep_keys=["<key1>", ...]` (each key: {key_description}). '
        f'Confirm to fetch ALL output anyway.'
    )
    try:
        elicit_result = await ctx.elicit(message=message, schema=_FetchAllConfirmation)
    except Exception as e:
        logger.info(
            f'Elicitation unavailable for fetch-all gate on {module.name!r}: '
            f'{e!r}; denying full fetch.'
        )
        return False

    if (
        elicit_result.action == 'accept'
        and elicit_result.data is not None
        and elicit_result.data.confirm
    ):
        logger.info(f'User confirmed fetching all output for {module.name!r} on {instance_id}.')
        return True

    logger.info(
        f'User declined full fetch for {module.name!r} on {instance_id} '
        f'(action={elicit_result.action!r}).'
    )
    return False


async def _large_output_elicitation_gate(
    ctx: Context,
    instance_id: str,
    module: Ec2rlModule,
    warning_message: str,
) -> str | None:
    """Gate modules with potentially large output on user confirmation.

    Returns None when the run may proceed (user confirmed). Returns an
    Aborted JSON envelope when the user declined, cancelled, or
    elicitation is unavailable.
    """
    try:
        elicit_result = await ctx.elicit(message=warning_message, schema=_LargeOutputConfirmation)
    except Exception as e:
        logger.info(
            f'Elicitation unavailable for large-output gate on {module.name!r}: {e!r}; aborting.'
        )
        return ModuleResponse(
            instance_id=instance_id,
            module=module.name,
            status='Aborted',
            reason='large_output_not_confirmed',
            hint=warning_message,
        ).as_json()

    if (
        elicit_result.action == 'accept'
        and elicit_result.data is not None
        and elicit_result.data.confirm
    ):
        logger.info(f'User confirmed large-output module {module.name!r} on {instance_id}.')
        return None

    logger.info(
        f'User declined large-output module {module.name!r} on '
        f'{instance_id} (action={elicit_result.action!r}).'
    )
    return ModuleResponse(
        instance_id=instance_id,
        module=module.name,
        status='Aborted',
        reason='large_output_not_confirmed',
        hint=warning_message,
    ).as_json()


def _install_gate(
    instance_id: str,
) -> str | None:
    """Gate the install tool on the ``--allow-install`` flag.

    Returns None when permitted, else an Aborted JSON envelope.
    """
    if _ALLOW_INSTALL:
        logger.info(f'install_ec2rescue_linux on {instance_id}: permitted by --allow-install.')
        return None

    logger.info(
        f'install_ec2rescue_linux on {instance_id} but --allow-install was '
        'not set; denying (fail-closed).'
    )
    return ModuleResponse(
        instance_id=instance_id,
        module='install_ec2rescue_linux',
        status='Aborted',
        reason='install_not_permitted',
        message=(
            'Installing EC2 Rescue downloads and installs software on the '
            'instance and is disabled by default. An operator must restart '
            'the server with --allow-install to enable it.'
        ),
    ).as_json()
