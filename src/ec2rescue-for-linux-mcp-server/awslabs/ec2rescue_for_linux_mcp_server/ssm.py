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

"""AWS Systems Manager operations for EC2Rescue for Linux MCP Server."""

import asyncio
import boto3
import shlex
import time
from awslabs.ec2rescue_for_linux_mcp_server.consts import (
    BOTO_CONFIG,
    SSM_AUTOMATION_POLL_DEADLINE_SECONDS,
    SSM_AUTOMATION_POLL_INTERVAL_SECONDS,
    SSM_DELIVERY_TIMEOUT_SECONDS,
    SSM_DOCUMENT_NAME,
    SSM_EXECUTION_TIMEOUT_SECONDS,
    SSM_INSTALL_DOCUMENT_NAME,
    SSM_POLL_DEADLINE_SECONDS,
    SSM_POLL_INTERVAL_SECONDS,
)
from loguru import logger


def _list_ssm_instances_sync(session: boto3.Session) -> list[dict]:
    """List EC2 instances registered with SSM (synchronous).

    Args:
        session: A configured boto3 Session.

    Returns:
        A list of dicts with keys: instance_id, name, platform,
        ping_status, ip_address, instance_type.
    """
    ssm = session.client('ssm', config=BOTO_CONFIG)

    ssm_instances: list[dict] = []
    paginator = ssm.get_paginator('describe_instance_information')
    for page in paginator.paginate():
        ssm_instances.extend(page['InstanceInformationList'])

    if not ssm_instances:
        logger.info('No SSM-managed instances found')
        return []

    ec2 = session.client('ec2', config=BOTO_CONFIG)
    ec2_instance_ids = [i['InstanceId'] for i in ssm_instances if i['InstanceId'].startswith('i-')]
    logger.info(f'Found {len(ssm_instances)} SSM-managed instances ({len(ec2_instance_ids)} EC2)')

    ec2_details: dict[str, dict] = {}
    if ec2_instance_ids:
        ec2_resp = ec2.describe_instances(InstanceIds=ec2_instance_ids)
        for reservation in ec2_resp['Reservations']:
            for inst in reservation['Instances']:
                name = next(
                    (t['Value'] for t in inst.get('Tags', []) if t['Key'] == 'Name'),
                    '',
                )
                ec2_details[inst['InstanceId']] = {
                    'name': name,
                    'instance_type': inst.get('InstanceType', ''),
                }

    result = []
    for ssm_inst in ssm_instances:
        iid = ssm_inst['InstanceId']
        ec2_info = ec2_details.get(iid, {})
        result.append(
            {
                'instance_id': iid,
                'name': ec2_info.get('name', ''),
                'platform': ssm_inst.get('PlatformType', ''),
                'ping_status': ssm_inst.get('PingStatus', ''),
                'ip_address': ssm_inst.get('IPAddress', ''),
                'instance_type': ec2_info.get('instance_type', ''),
            }
        )

    return result


_LOGIN_SHELL_PREFIXES = ('ec2rl ', 'which ')


def _unwrap_login_shell(wrapped: str) -> str | None:
    """Recover the original command from a ``bash -l -c '...'`` wrapping.

    Tokenizes ``wrapped`` with the standard shell lexer and returns the
    command argument only if it parses to exactly ``bash -l -c <command>``
    (four tokens). Any other shape -- extra tokens, an unbalanced quote, or a
    metacharacter that escaped the quoting -- yields ``None``, which signals
    that the wrapping did not contain the input as a single argument.

    Using :func:`shlex.split` rather than reversing the escaping by hand
    grounds the check in the same lexical rules a POSIX shell applies, so the
    round-trip guarantee does not rest on a bespoke unquoting routine.
    """
    try:
        tokens = shlex.split(wrapped)
    except ValueError:
        # Unbalanced quotes: the wrapping is not a well-formed single-quoted
        # argument.
        return None
    if len(tokens) == 4 and tokens[:3] == ['bash', '-l', '-c']:
        return tokens[3]
    return None


def _wrap_login_shell(command: str) -> str:
    """Wrap commands that need the full user PATH in ``bash -l -c '...'``.

    SSM's ``AWS-RunShellScript`` runs a non-login shell with a minimal
    PATH. Commands like ``ec2rl`` and ``which`` need ``/etc/profile.d/``
    sourced to find binaries in non-standard locations (e.g.
    ``/usr/share/bcc/tools/``).

    The wrapped result is re-parsed before it is returned: tokenizing it must
    yield exactly ``bash -l -c <command>``. If it does not, the single-quote
    escaping failed to contain the input (a shell injection would otherwise
    reach the instance), so this raises ``ValueError`` rather than returning a
    command that was never re-validated.
    """
    if not any(command.startswith(prefix) for prefix in _LOGIN_SHELL_PREFIXES):
        return command

    escaped = command.replace("'", "'\\''")
    wrapped = f"bash -l -c '{escaped}'"

    # Re-validate the wrapping by reversing it. This closes the gap where the
    # validated command is re-quoted after validation and the result is never
    # checked again.
    if _unwrap_login_shell(wrapped) != command:
        raise ValueError(f'Login-shell wrapping failed to round-trip: {command!r}')

    return wrapped


def _run_ssm_command_sync(
    session: boto3.Session,
    instance_id: str,
    command: str,
    delivery_timeout_seconds: int = SSM_DELIVERY_TIMEOUT_SECONDS,
    execution_timeout_seconds: int = SSM_EXECUTION_TIMEOUT_SECONDS,
    poll_deadline_seconds: int = SSM_POLL_DEADLINE_SECONDS,
    poll_interval: float = SSM_POLL_INTERVAL_SECONDS,
) -> dict:
    """Execute a shell command on an EC2 instance via SSM SendCommand (synchronous).

    Args:
        session: A configured boto3 Session.
        instance_id: The EC2 instance ID to run the command on.
        command: The shell command to execute.
        delivery_timeout_seconds: How long SSM waits for the agent to pick
            up the command (the SendCommand ``TimeoutSeconds`` parameter).
        execution_timeout_seconds: How long the agent is allowed to run
            the command (forwarded as the AWS-RunShellScript document's
            ``executionTimeout`` parameter).
        poll_deadline_seconds: Client-side ceiling on how long to poll
            get_command_invocation before giving up.
        poll_interval: Time between status polls in seconds.

    Returns:
        A dict with keys: status, stdout, stderr, exit_code.
    """
    ssm = session.client('ssm', config=BOTO_CONFIG)

    shell_command = _wrap_login_shell(command)
    logger.info(f'Sending SSM command to {instance_id}: {shell_command}')
    resp = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName=SSM_DOCUMENT_NAME,
        Parameters={
            'commands': [shell_command],
            'executionTimeout': [str(execution_timeout_seconds)],
        },
        TimeoutSeconds=delivery_timeout_seconds,
    )
    command_id = resp['Command']['CommandId']
    logger.info(f'SSM command sent, CommandId: {command_id}')

    deadline = time.monotonic() + poll_deadline_seconds
    while time.monotonic() < deadline:
        try:
            invocation = ssm.get_command_invocation(
                CommandId=command_id,
                InstanceId=instance_id,
            )
        except ssm.exceptions.InvocationDoesNotExist:
            logger.debug(f'Command {command_id} invocation not yet available, retrying...')
            time.sleep(poll_interval)
            continue

        if invocation['Status'] in ('Success', 'Failed', 'Cancelled', 'TimedOut'):
            logger.info(f'Command {command_id} completed with status: {invocation["Status"]}')
            return {
                'status': invocation['Status'],
                'stdout': invocation.get('StandardOutputContent', ''),
                'stderr': invocation.get('StandardErrorContent', ''),
                'exit_code': invocation.get('ResponseCode', -1),
            }

        time.sleep(poll_interval)

    logger.warning(f'Command {command_id} polling gave up after {poll_deadline_seconds}s')
    return {
        'status': 'TimedOut',
        'stdout': '',
        'stderr': 'Command timed out waiting for result',
        'exit_code': -1,
    }


async def list_ssm_instances(session: boto3.Session) -> list[dict]:
    """List EC2 instances registered with SSM.

    Args:
        session: A configured boto3 Session.

    Returns:
        A list of dicts with keys: instance_id, name, platform,
        ping_status, ip_address, instance_type.
    """
    return await asyncio.to_thread(_list_ssm_instances_sync, session)


async def run_ssm_command(
    session: boto3.Session,
    instance_id: str,
    command: str,
    delivery_timeout_seconds: int = SSM_DELIVERY_TIMEOUT_SECONDS,
    execution_timeout_seconds: int = SSM_EXECUTION_TIMEOUT_SECONDS,
    poll_deadline_seconds: int = SSM_POLL_DEADLINE_SECONDS,
    poll_interval: float = SSM_POLL_INTERVAL_SECONDS,
) -> dict:
    """Execute a shell command on an EC2 instance via SSM SendCommand.

    See :func:`_run_ssm_command_sync` for the meaning of the timeout
    parameters.

    Returns:
        A dict with keys: status, stdout, stderr, exit_code.
    """
    return await asyncio.to_thread(
        _run_ssm_command_sync,
        session,
        instance_id,
        command,
        delivery_timeout_seconds,
        execution_timeout_seconds,
        poll_deadline_seconds,
        poll_interval,
    )


def _run_install_ec2_rescue_sync(
    session: boto3.Session,
    instance_id: str,
    poll_deadline_seconds: float = SSM_AUTOMATION_POLL_DEADLINE_SECONDS,
    poll_interval: float = SSM_AUTOMATION_POLL_INTERVAL_SECONDS,
) -> dict:
    """Run AWSSupport-InstallEC2Rescue automation on an instance (synchronous).

    Returns:
        A dict with keys: status, automation_execution_id, outputs, failure_message.
    """
    ssm = session.client('ssm', config=BOTO_CONFIG)

    logger.info(f'Starting automation {SSM_INSTALL_DOCUMENT_NAME} on {instance_id}')
    resp = ssm.start_automation_execution(
        DocumentName=SSM_INSTALL_DOCUMENT_NAME,
        Parameters={'InstanceId': [instance_id]},
    )
    execution_id = resp['AutomationExecutionId']
    logger.info(f'Automation started, ExecutionId: {execution_id}')

    deadline = time.monotonic() + poll_deadline_seconds
    while time.monotonic() < deadline:
        execution = ssm.describe_automation_executions(
            Filters=[{'Key': 'ExecutionId', 'Values': [execution_id]}]
        )
        records = execution.get('AutomationExecutionMetadataList', [])
        if not records:
            time.sleep(poll_interval)
            continue

        status = records[0].get('AutomationExecutionStatus', '')
        if status in ('Success', 'Failed', 'Cancelled', 'TimedOut'):
            logger.info(f'Automation {execution_id} completed with status: {status}')
            outputs = records[0].get('Outputs', {})
            failure = records[0].get('FailureMessage', '')
            return {
                'status': status,
                'automation_execution_id': execution_id,
                'outputs': outputs,
                'failure_message': failure,
            }

        time.sleep(poll_interval)

    logger.warning(f'Automation {execution_id} polling gave up after {poll_deadline_seconds}s')
    return {
        'status': 'TimedOut',
        'automation_execution_id': execution_id,
        'outputs': {},
        'failure_message': (f'Client-side poll deadline ({poll_deadline_seconds}s) exceeded.'),
    }


async def run_install_ec2_rescue(
    session: boto3.Session,
    instance_id: str,
) -> dict:
    """Run AWSSupport-InstallEC2Rescue automation on an instance.

    Returns:
        A dict with keys: status, automation_execution_id, outputs, failure_message.
    """
    return await asyncio.to_thread(
        _run_install_ec2_rescue_sync,
        session,
        instance_id,
    )
