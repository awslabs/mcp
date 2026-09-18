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

"""Every AWS resource the harness owns, and its lifecycle.

Two IAM roles, one provisioned cluster, one Serverless namespace and workgroup. Nothing is
looked up from an existing deployment: `up` creates whatever is missing, resumes a paused
cluster, seeds whichever warehouse is unseeded, and grants the server's own identity what it
needs. Every operation is idempotent, so a second run costs a few describe calls.

`pause` stops compute billing on the cluster. Serverless exposes no Pause, Resume, Suspend or
Stop operation and bills nothing while idle, so it is left alone. `down` deletes the lot.
"""

import json
import time
from botocore.exceptions import ClientError
from dataclasses import dataclass
from e2e_tests import denied_batch, tickit
from e2e_tests.config import DENIED_ACTION, Config


SAMPLE_DATA_BUCKET = 'redshift-downloads'

# Measured on ra3.large x2: create ~4 min, pause ~5.5 min, resume ~4 min. The ceiling is
# generous because these are control-plane operations behind a shared service.
_TRANSITION_TIMEOUT = 1800.0

# Control-plane transitions take minutes, so polling faster only adds API calls.
_POLL_SECONDS = 5.0

# IAM is eventually consistent, so a freshly created role is not immediately assumable.
_PROPAGATION_SECONDS = 12

_PURPOSE = 'redshift-mcp-server-e2e-harness'

# redshift takes Key/Value, redshift-serverless takes key/value.
_TAGS = [{'Key': 'purpose', 'Value': _PURPOSE}]
_TAGS_LOWER = [{'key': 'purpose', 'value': _PURPOSE}]

_REDSHIFT_TRUST = {
    'Version': '2012-10-17',
    'Statement': [
        {
            'Effect': 'Allow',
            'Principal': {
                'Service': ['redshift.amazonaws.com', 'redshift-serverless.amazonaws.com']
            },
            'Action': 'sts:AssumeRole',
        }
    ],
}

_S3_READ = {
    'Version': '2012-10-17',
    'Statement': [
        {
            'Effect': 'Allow',
            'Action': ['s3:GetObject', 's3:ListBucket'],
            'Resource': [
                f'arn:aws:s3:::{SAMPLE_DATA_BUCKET}',
                f'arn:aws:s3:::{SAMPLE_DATA_BUCKET}/*',
            ],
        }
    ],
}

# Everything the server needs, so that removing one action in a session policy is the only
# difference between a normal run and a no_batch run.
_REDSHIFT_FULL = {
    'Version': '2012-10-17',
    'Statement': [
        {
            'Effect': 'Allow',
            'Action': ['redshift-data:*', 'redshift:*', 'redshift-serverless:*'],
            'Resource': '*',
        }
    ],
}


class DeployError(RuntimeError):
    """A resource did not reach the state the harness needs."""


@dataclass(frozen=True)
class Warehouse:
    """A provisioned cluster or a Serverless workgroup, as the harness addresses it.

    The server under test reads the type from discovery and picks `ClusterIdentifier` or
    `WorkgroupName` itself. The harness has to make the same choice to seed and inspect, so it
    lives here rather than in every caller.
    """

    identifier: str
    kind: str
    database: str
    master_secret_arn: str | None = None

    @property
    def server_target(self) -> dict:
        """Addressing keys authenticating as the server under test does.

        Returns:
            Keyword arguments for a redshift-data call.
        """
        key = 'ClusterIdentifier' if self.kind == 'provisioned' else 'WorkgroupName'
        return {key: self.identifier, 'Database': self.database}

    @property
    def seed_target(self) -> dict:
        """Addressing keys authenticating as an identity that may create a schema.

        A fresh provisioned cluster grants an IAM identity nothing, not even `CREATE SCHEMA`,
        so seeding runs as the master user. Serverless needs no secret.

        Returns:
            Keyword arguments for a redshift-data call, carrying the master secret when the
            warehouse has one.
        """
        target = dict(self.server_target)
        if self.master_secret_arn:
            target['SecretArn'] = self.master_secret_arn
        return target


# --- IAM ---


def _ensure_role(iam, name: str, trust: dict, perms: dict, description: str) -> str:
    """Create or update one role and its inline policy.

    Args:
        iam: An IAM client.
        name: Role name.
        trust: Assume-role policy document.
        perms: Inline permissions policy document.
        description: Shown in the console, so an operator can tell what left it behind.

    Returns:
        The role ARN.
    """
    try:
        arn = iam.create_role(
            RoleName=name,
            AssumeRolePolicyDocument=json.dumps(trust),
            Description=description,
            Tags=_TAGS,
        )['Role']['Arn']
        created = True
    except ClientError as e:
        if e.response['Error']['Code'] != 'EntityAlreadyExists':
            raise
        arn = iam.get_role(RoleName=name)['Role']['Arn']
        created = False

    iam.put_role_policy(RoleName=name, PolicyName='harness', PolicyDocument=json.dumps(perms))

    if created:
        time.sleep(_PROPAGATION_SECONDS)

    return arn


def ensure_s3_read_role(iam, name: str) -> str:
    """Create the role Redshift assumes to read the sample-data bucket.

    Args:
        iam: An IAM client.
        name: Role name from the config.

    Returns:
        The role ARN, ready to pass to COPY and to attach to a warehouse.
    """
    return _ensure_role(
        iam,
        name,
        _REDSHIFT_TRUST,
        _S3_READ,
        f'Lets Redshift COPY sample data from s3://{SAMPLE_DATA_BUCKET} for the MCP e2e harness',
    )


def ensure_denied_batch_role(iam, sts, name: str) -> str:
    """Create the role the harness assumes to run the server without the batch action.

    Trusts the account, so any principal in it that may call AssumeRole can take it on.

    Args:
        iam: An IAM client.
        sts: An STS client, used to learn the account rather than hardcode it.
        name: Role name from the config.

    Returns:
        The role ARN.
    """
    account = sts.get_caller_identity()['Account']
    trust = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Principal': {'AWS': f'arn:aws:iam::{account}:root'},
                'Action': 'sts:AssumeRole',
            }
        ],
    }
    return _ensure_role(
        iam,
        name,
        trust,
        _REDSHIFT_FULL,
        f'Assumed with a session policy denying {DENIED_ACTION}, for the MCP e2e harness',
    )


def delete_role(iam, name: str) -> bool:
    """Delete one harness role and its inline policy.

    Args:
        iam: An IAM client.
        name: Role name.

    Returns:
        True if the role existed and was deleted.
    """
    try:
        iam.delete_role_policy(RoleName=name, PolicyName='harness')
    except ClientError as e:
        if e.response['Error']['Code'] != 'NoSuchEntity':
            raise

    try:
        iam.delete_role(RoleName=name)
    except ClientError as e:
        if e.response['Error']['Code'] != 'NoSuchEntity':
            raise
        return False

    return True


# --- Provisioned cluster ---


def describe_cluster(redshift, identifier: str) -> dict | None:
    """Return the cluster, or None when it does not exist.

    Args:
        redshift: A redshift client.
        identifier: Cluster identifier.

    Returns:
        The cluster description, or None.
    """
    try:
        return redshift.describe_clusters(ClusterIdentifier=identifier)['Clusters'][0]
    except ClientError as e:
        if e.response['Error']['Code'] == 'ClusterNotFound':
            return None
        raise


def _wait_for_cluster(redshift, identifier: str, status: str) -> dict:
    """Poll until the cluster reports the wanted status.

    Args:
        redshift: A redshift client.
        identifier: Cluster identifier.
        status: The status to wait for.

    Returns:
        The cluster description once it reports `status`.

    Raises:
        DeployError: If it disappears, or does not get there in time.
    """
    deadline = time.monotonic() + _TRANSITION_TIMEOUT

    while True:
        cluster = describe_cluster(redshift, identifier)
        if cluster is None:
            raise DeployError(f'cluster {identifier} disappeared while waiting for {status}')
        if cluster['ClusterStatus'] == status:
            return cluster
        if time.monotonic() >= deadline:
            raise DeployError(
                f'cluster {identifier} still {cluster["ClusterStatus"]} after '
                f'{_TRANSITION_TIMEOUT}s, wanted {status}'
            )
        time.sleep(_POLL_SECONDS)


def _wait_for_cluster_role(redshift, identifier: str, role_arn: str) -> dict:
    """Poll until an associated role reports `in-sync`.

    COPY fails with a permissions error until the association finishes, so this cannot be
    skipped.

    Args:
        redshift: A redshift client.
        identifier: Cluster identifier.
        role_arn: The role to wait for.

    Returns:
        The cluster description once the role is in-sync.

    Raises:
        DeployError: If it does not sync in time.
    """
    deadline = time.monotonic() + _TRANSITION_TIMEOUT

    while True:
        cluster = describe_cluster(redshift, identifier)
        if cluster is None:
            raise DeployError(f'cluster {identifier} disappeared while associating a role')
        statuses = {
            role['IamRoleArn']: role['ApplyStatus'] for role in cluster.get('IamRoles', [])
        }
        if statuses.get(role_arn) == 'in-sync' and cluster['ClusterStatus'] == 'available':
            return cluster
        if time.monotonic() >= deadline:
            raise DeployError(f'role {role_arn} not in-sync on {identifier}: {statuses}')
        time.sleep(_POLL_SECONDS)


def ensure_cluster(redshift, config: Config, s3_read_role_arn: str) -> dict:
    """Bring the cluster to `available`, creating or resuming it as needed.

    Two nodes, not one: a single-node cluster differs in slice layout and concurrency enough
    that its results do not represent a real deployment.

    Args:
        redshift: A redshift client.
        config: The harness config.
        s3_read_role_arn: Role to associate, so COPY can read the sample-data bucket.

    Returns:
        The available cluster's description.

    Raises:
        DeployError: If it cannot be brought up.
    """
    cluster = describe_cluster(redshift, config.cluster_identifier)

    if cluster is None:
        redshift.create_cluster(
            ClusterIdentifier=config.cluster_identifier,
            NodeType=config.node_type,
            NumberOfNodes=config.number_of_nodes,
            ClusterType='multi-node',
            DBName=config.database,
            MasterUsername=config.master_username,
            # Managed by Secrets Manager rather than chosen here, so no secret reaches the
            # config and none has to be handled by the harness.
            ManageMasterPassword=True,
            PubliclyAccessible=False,
            ClusterSubnetGroupName=config.cluster_subnet_group_name,
            Encrypted=True,
            Tags=_TAGS,
        )
    elif cluster['ClusterStatus'] == 'paused':
        redshift.resume_cluster(ClusterIdentifier=config.cluster_identifier)

    cluster = _wait_for_cluster(redshift, config.cluster_identifier, 'available')

    associated = {role['IamRoleArn'] for role in cluster.get('IamRoles', [])}
    if s3_read_role_arn not in associated:
        redshift.modify_cluster_iam_roles(
            ClusterIdentifier=config.cluster_identifier, AddIamRoles=[s3_read_role_arn]
        )
        cluster = _wait_for_cluster_role(redshift, config.cluster_identifier, s3_read_role_arn)

    return cluster


def master_secret_arn(cluster: dict) -> str:
    """Return the ARN of the managed master password.

    Args:
        cluster: A cluster description.

    Returns:
        The Secrets Manager ARN the Data API authenticates the master user with.

    Raises:
        DeployError: If the cluster has no managed secret, which means it was not created by
            this harness.
    """
    arn = cluster.get('MasterPasswordSecretArn')
    if not arn:
        raise DeployError(
            f'cluster {cluster["ClusterIdentifier"]} has no managed master password, so the '
            'harness cannot seed it. Delete it and let the harness create it.'
        )
    return arn


def pause_cluster(redshift, identifier: str) -> bool:
    """Pause the cluster, so it bills storage only.

    Args:
        redshift: A redshift client.
        identifier: Cluster identifier.

    Returns:
        True if a pause was requested, False if it was not running.
    """
    cluster = describe_cluster(redshift, identifier)
    if cluster is None or cluster['ClusterStatus'] != 'available':
        return False

    redshift.pause_cluster(ClusterIdentifier=identifier)
    _wait_for_cluster(redshift, identifier, 'paused')
    return True


def destroy_cluster(redshift, identifier: str) -> bool:
    """Delete the cluster, taking no final snapshot.

    Args:
        redshift: A redshift client.
        identifier: Cluster identifier.

    Returns:
        True if the cluster existed and deletion was requested.
    """
    if describe_cluster(redshift, identifier) is None:
        return False

    # A paused cluster can be deleted directly. Skipping the final snapshot makes it
    # unrestorable, which is what we want for data reloadable from S3.
    redshift.delete_cluster(ClusterIdentifier=identifier, SkipFinalClusterSnapshot=True)
    return True


# --- Serverless namespace and workgroup ---


def describe_workgroup(serverless, name: str) -> dict | None:
    """Return the workgroup, or None when it does not exist.

    Args:
        serverless: A redshift-serverless client.
        name: Workgroup name.

    Returns:
        The workgroup, or None.
    """
    try:
        return serverless.get_workgroup(workgroupName=name)['workgroup']
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return None
        raise


def describe_namespace(serverless, name: str) -> dict | None:
    """Return the namespace, or None when it does not exist.

    Args:
        serverless: A redshift-serverless client.
        name: Namespace name.

    Returns:
        The namespace, or None.
    """
    try:
        return serverless.get_namespace(namespaceName=name)['namespace']
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return None
        raise


def _wait_for_workgroup(serverless, name: str, status: str) -> dict:
    """Poll until the workgroup reports the wanted status.

    Args:
        serverless: A redshift-serverless client.
        name: Workgroup name.
        status: The status to wait for.

    Returns:
        The workgroup once it reports `status`.

    Raises:
        DeployError: If it disappears, or does not get there in time.
    """
    deadline = time.monotonic() + _TRANSITION_TIMEOUT

    while True:
        workgroup = describe_workgroup(serverless, name)
        if workgroup is None:
            raise DeployError(f'workgroup {name} disappeared while waiting for {status}')
        if workgroup['status'] == status:
            return workgroup
        if time.monotonic() >= deadline:
            raise DeployError(
                f'workgroup {name} still {workgroup["status"]} after {_TRANSITION_TIMEOUT}s, '
                f'wanted {status}'
            )
        time.sleep(_POLL_SECONDS)


def ensure_workgroup(serverless, config: Config, s3_read_role_arn: str) -> dict:
    """Bring the namespace and workgroup up, creating whichever is missing.

    The sample-data role is attached at namespace creation, which is why Serverless needs no
    equivalent of the cluster's role-association wait.

    Args:
        serverless: A redshift-serverless client.
        config: The harness config.
        s3_read_role_arn: Role attached to the namespace, so COPY can read the sample data.

    Returns:
        The available workgroup.

    Raises:
        DeployError: If it cannot be brought up.
    """
    if describe_namespace(serverless, config.namespace_name) is None:
        serverless.create_namespace(
            namespaceName=config.namespace_name,
            dbName=config.database,
            iamRoles=[s3_read_role_arn],
            defaultIamRoleArn=s3_read_role_arn,
            manageAdminPassword=True,
            tags=_TAGS_LOWER,
        )

    if describe_workgroup(serverless, config.workgroup_name) is None:
        serverless.create_workgroup(
            workgroupName=config.workgroup_name,
            namespaceName=config.namespace_name,
            baseCapacity=config.base_capacity,
            publiclyAccessible=False,
            tags=_TAGS_LOWER,
        )

    return _wait_for_workgroup(serverless, config.workgroup_name, 'AVAILABLE')


def destroy_workgroup(serverless, config: Config) -> bool:
    """Delete the workgroup and then its namespace.

    Order matters: a namespace holding a workgroup cannot be deleted.

    Args:
        serverless: A redshift-serverless client.
        config: The harness config.

    Returns:
        True if either resource existed and deletion was requested.

    Raises:
        DeployError: If the workgroup does not finish deleting in time.
    """
    deleted = False

    if describe_workgroup(serverless, config.workgroup_name) is not None:
        serverless.delete_workgroup(workgroupName=config.workgroup_name)
        deadline = time.monotonic() + _TRANSITION_TIMEOUT
        while describe_workgroup(serverless, config.workgroup_name) is not None:
            if time.monotonic() >= deadline:
                raise DeployError(f'workgroup {config.workgroup_name} did not delete')
            time.sleep(_POLL_SECONDS)
        deleted = True

    if describe_namespace(serverless, config.namespace_name) is not None:
        # Naming no final snapshot skips it, which is what we want for data reloadable from S3.
        serverless.delete_namespace(namespaceName=config.namespace_name)
        deleted = True

    return deleted


# --- Commands ---


def clients(session) -> dict:
    """Build the clients every command needs.

    Args:
        session: A boto3 session for the configured profile and region.

    Returns:
        A dict of boto3 clients keyed by service.
    """
    return {
        'redshift': session.client('redshift'),
        'serverless': session.client('redshift-serverless'),
        'data': session.client('redshift-data'),
        'iam': session.client('iam'),
        'sts': session.client('sts'),
    }


def up(session, config: Config, log=print) -> dict[str, Warehouse]:
    """Bring both warehouses to a state an agent can be pointed at.

    Args:
        session: A boto3 session for the configured profile and region.
        config: The harness config.
        log: Where to report progress.

    Returns:
        Both warehouses, seeded and granted, keyed by kind.
    """
    aws = clients(session)

    s3_role = ensure_s3_read_role(aws['iam'], config.s3_read_role_name)
    denied_role = ensure_denied_batch_role(aws['iam'], aws['sts'], config.denied_batch_role_name)
    log(f'iam        {s3_role}')

    cluster = ensure_cluster(aws['redshift'], config, s3_role)
    log(f'cluster    {config.cluster_identifier} {cluster["ClusterStatus"]}')

    workgroup = ensure_workgroup(aws['serverless'], config, s3_role)
    log(f'workgroup  {config.workgroup_name} {workgroup["status"]}')

    warehouses = {
        'provisioned': Warehouse(
            identifier=config.cluster_identifier,
            kind='provisioned',
            database=config.database,
            master_secret_arn=master_secret_arn(cluster),
        ),
        'serverless': Warehouse(
            identifier=config.workgroup_name, kind='serverless', database=config.database
        ),
    }

    # The denied-batch server arrives as a different database identity, so it needs the same
    # grants. Without them a no_batch scenario can only read the catalogue, and "reads still
    # work" goes unproven on the tables a user actually has.
    denied_data = denied_batch.client(
        denied_batch.environment(aws['sts'], denied_role, config.region)
    )

    for warehouse in warehouses.values():
        if tickit.is_seeded(aws['data'], warehouse.seed_target, config.schema):
            log(f'seed       {warehouse.identifier} already loaded')
        else:
            counts = tickit.seed(
                aws['data'], warehouse.seed_target, config.schema, s3_role, config.region
            )
            log(f'seed       {warehouse.identifier} loaded {sum(counts.values())} rows')

        for data in (aws['data'], denied_data):
            identity = tickit.current_identity(data, warehouse.server_target)
            tickit.grant_read(
                aws['data'], warehouse.seed_target, config.schema, config.database, identity
            )
            log(f'grant      {warehouse.identifier} -> {identity}')

    return warehouses


def status(session, config: Config, log=print) -> None:
    """Report what exists, without changing anything.

    Args:
        session: A boto3 session for the configured profile and region.
        config: The harness config.
        log: Where to report.
    """
    aws = clients(session)

    cluster = describe_cluster(aws['redshift'], config.cluster_identifier)
    log(
        f'cluster    {config.cluster_identifier} '
        f'{cluster["ClusterStatus"] if cluster else "absent"}'
    )

    workgroup = describe_workgroup(aws['serverless'], config.workgroup_name)
    log(f'workgroup  {config.workgroup_name} {workgroup["status"] if workgroup else "absent"}')

    namespace = describe_namespace(aws['serverless'], config.namespace_name)
    log(f'namespace  {config.namespace_name} {namespace["status"] if namespace else "absent"}')

    for name in (config.s3_read_role_name, config.denied_batch_role_name):
        try:
            aws['iam'].get_role(RoleName=name)
            log(f'iam        {name} present')
        except aws['iam'].exceptions.NoSuchEntityException:
            log(f'iam        {name} absent')


def pause(session, config: Config, log=print) -> None:
    """Stop compute billing on the provisioned cluster.

    Args:
        session: A boto3 session for the configured profile and region.
        config: The harness config.
        log: Where to report.
    """
    aws = clients(session)

    if pause_cluster(aws['redshift'], config.cluster_identifier):
        log(f'cluster    {config.cluster_identifier} paused')
    else:
        log(f'cluster    {config.cluster_identifier} not running, nothing to pause')

    log(f'workgroup  {config.workgroup_name} left alone, Serverless has no pause')


def down(session, config: Config, log=print) -> None:
    """Delete every resource the harness owns.

    Args:
        session: A boto3 session for the configured profile and region.
        config: The harness config.
        log: Where to report.
    """
    aws = clients(session)

    cluster_gone = destroy_cluster(aws['redshift'], config.cluster_identifier)
    log(f'cluster    {config.cluster_identifier} {"deleting" if cluster_gone else "absent"}')

    serverless_gone = destroy_workgroup(aws['serverless'], config)
    log(f'serverless {config.workgroup_name} {"deleting" if serverless_gone else "absent"}')

    for name in (config.s3_read_role_name, config.denied_batch_role_name):
        log(f'iam        {name} {"deleted" if delete_role(aws["iam"], name) else "absent"}')


def teardown(session, config: Config, log=print) -> None:
    """Apply whichever end-of-run lifecycle the config asks for.

    Args:
        session: A boto3 session for the configured profile and region.
        config: The harness config.
        log: Where to report.
    """
    if config.destroy_after_run:
        down(session, config, log)
    elif config.pause_after_run:
        pause(session, config, log)
    else:
        log('lifecycle  left running, both pause_after_run and destroy_after_run are false')
