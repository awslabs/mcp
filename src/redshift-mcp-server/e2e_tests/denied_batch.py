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

"""Credentials denied one action, which is the only way to reach the no_batch fallback.

The server chooses its compatibility path from an `AccessDeniedException` on
`redshift-data:BatchExecuteStatement`, so no amount of configuration reaches that code. The
denial has to be real.

A session policy on `sts:AssumeRole` removes exactly that action and allows everything else,
so a server started with these credentials differs from a normally started one in one respect
only. Measured against the Data API: a denied batch action answers `AccessDeniedException`,
while denied cluster credentials answer `ValidationException` on both call shapes, so the
server's discriminator does not confuse the two.
"""

import boto3
import json
from botocore.exceptions import ClientError
from e2e_tests.config import DENIED_ACTION


# The longest session a role assumed with default settings grants. A harness run is minutes,
# but the agent decides its own pace, so the ceiling matters more than the floor here.
_SESSION_SECONDS = 3600

_SESSION_POLICY = {
    'Version': '2012-10-17',
    'Statement': [
        {'Effect': 'Allow', 'Action': '*', 'Resource': '*'},
        {'Effect': 'Deny', 'Action': DENIED_ACTION, 'Resource': '*'},
    ],
}


class DenialError(RuntimeError):
    """The credentials are not denied what the harness needs them denied."""


def environment(sts, role_arn: str, region: str) -> dict[str, str]:
    """Return environment variables that authenticate without the batch action.

    Handed to the generated agent as one MCP server's `env`, so the agent can reach the
    fallback through an ordinary tool call rather than a shell wrapper. `AWS_PROFILE` must be
    absent from that environment, or it wins over these.

    Args:
        sts: An STS client authenticated normally.
        role_arn: The harness's denied-batch role.
        region: Region to pin, so the server does not fall back to a different one.

    Returns:
        AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN and AWS_REGION.
    """
    credentials = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName='mcp-e2e-no-batch',
        Policy=json.dumps(_SESSION_POLICY),
        DurationSeconds=_SESSION_SECONDS,
    )['Credentials']

    return {
        'AWS_ACCESS_KEY_ID': credentials['AccessKeyId'],
        'AWS_SECRET_ACCESS_KEY': credentials['SecretAccessKey'],
        'AWS_SESSION_TOKEN': credentials['SessionToken'],
        'AWS_REGION': region,
    }


def client(env: dict[str, str]):
    """Return a redshift-data client authenticating the way the denied server does.

    The harness needs one to ask the warehouse what identity these credentials arrive as, which
    is what the grants have to name.

    Args:
        env: The environment from `environment`.

    Returns:
        A redshift-data client.
    """
    return boto3.Session(
        aws_access_key_id=env['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=env['AWS_SECRET_ACCESS_KEY'],
        aws_session_token=env['AWS_SESSION_TOKEN'],
        region_name=env['AWS_REGION'],
    ).client('redshift-data')


def verify(env: dict[str, str], target: dict) -> None:
    """Fail loudly if the credentials are not actually denied the batch action.

    Guards against a silently passing run: were the session policy to stop applying, every
    no_batch scenario would exercise the main path while still reporting success.

    The target must exist. The Data API resolves it before it authorizes, so a made-up
    identifier answers `ValidationException` whatever the caller is allowed, which tells us
    nothing about the denial.

    Args:
        env: The environment from `environment`.
        target: Addressing keys for a warehouse that is up, from `Warehouse.server_target`.

    Raises:
        DenialError: If the batch action is permitted, or the single-statement action the
            fallback needs is denied too.
    """
    data = client(env)

    try:
        data.batch_execute_statement(Sqls=['SELECT 1'], **target)
    except ClientError as e:
        code = e.response['Error']['Code']
        if code != 'AccessDeniedException':
            raise DenialError(
                f'expected AccessDeniedException for {DENIED_ACTION}, got {code}'
            ) from e
    else:
        raise DenialError(f'{DENIED_ACTION} was permitted; the session policy is not applying')

    # The fallback submits one statement at a time, so it needs this action to survive. A
    # denial here would leave it nothing to fall back to.
    try:
        data.execute_statement(Sql='SELECT 1', **target)
    except ClientError as e:
        if e.response['Error']['Code'] == 'AccessDeniedException':
            raise DenialError(
                'redshift-data:ExecuteStatement is denied too, so the fallback has no path'
            ) from e
