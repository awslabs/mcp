# Redshift Connectivity, Authentication & Client Driver Troubleshooting

Diagnose Redshift **connection failures, auth/authorization errors, and client driver
problems**. Establish provisioned vs Serverless and the exact error string first, then
identify the most likely root cause and give the fix. Public surface only:
[Security in Amazon Redshift](https://docs.aws.amazon.com/redshift/latest/mgmt/iam-redshift-user-mgmt.html).
Connection attempts are in `stl_connection_log` / `sys_connection_log` (superuser); active
sessions in `stv_sessions` / `pg_stat_activity` (provisioned) or `SYS_SESSION_HISTORY`
(any deployment — Serverless / Multi-AZ included).

> **Verify volatile values against the linked AWS docs before asserting them.** Connection
> limits/quotas, end-of-support dates, and driver versions in this reference are
> current-as-written and can change — do NOT present a specific number, date, or version as
> permanent. Treat it as the current value, confirm it against the linked Amazon Redshift
> documentation (the authoritative source), and if you have a documentation-fetch/web tool,
> retrieve the current value from that page first.

## Authentication: `Response signature invalid` during assumeRoleWithSAML

SSO login (DBeaver/JDBC) that worked before fails with `Response signature invalid (Service:
Sts, Status Code: 400)` / `InvalidIdentityTokenException`. This is a **SAML metadata**
mismatch — the **federation metadata** in your **IAM identity provider** no longer matches the
current **IdP metadata**, most often after IdP **certificate rotation or expiration**. Fix by
replacing the metadata:

```bash
# Download the updated SAML metadata file from the IdP (e.g. AD FS), then either
# IAM console -> Identity providers -> <provider> -> Replace metadata, or:
aws iam update-saml-provider \
  --saml-provider-arn <provider_arn, string, arn> \
  --saml-metadata-document file://<metadata.xml, path, no quotes>
# PowerShell equivalent: Update-IAMSAMLProvider
```

[Resolving SAML federation errors](https://docs.aws.amazon.com/IAM/latest/UserGuide/troubleshoot_saml.html).

## Authentication: `RedshiftDbUser principal tag is required` (QEv2, provisioned)

"Federated user" auth in Query Editor v2 works on Serverless but fails on a **provisioned**
cluster. This is an **expected difference between** Redshift **Serverless and provisioned**
clusters, by design. Provisioned's QEv2 **"Federated user"** option uses **`GetClusterCredentials`**,
which requires a **`DbUser`** — the **`RedshiftDbUser` principal tag** is what supplies it.
Serverless uses **`GetCredentials`**, which resolves the user from the IAM role with no tag. Two
fixes: (1) add the `RedshiftDbUser` **principal tag** (IAM role or IdP session tags) carrying the
DB user, or (2) switch the connection to **"Temporary credentials using your IAM identity"**, which
uses **`GetClusterCredentialsWithIAM`** and needs no tag — that option logs in as
`IAMR:<identity>`, so grants made for the tagged user name don't carry over.
[Using IAM authentication to generate database user credentials](https://docs.aws.amazon.com/redshift/latest/mgmt/generating-user-credentials.html).

## Authentication: IAM Identity Center / OIDC region mismatch

Integrating Redshift (e.g. `ca-central-1`) with an IAM Identity Center instance in another
region (e.g. `us-east-1`) fails: customers receive an **`InvalidParameterValue`** error from
the Redshift API stating that the IAM Identity Center instance must be in the same Region as
the data warehouse. (Redshift's own API validation rejects the mismatch — the exact wording can
change, so match on the `InvalidParameterValue` + same-Region intent rather than a fixed
string.) Root cause:
IAM Identity Center and the Redshift data warehouse must be in the **same AWS Region**, so the
`us-east-1` instance cannot be used directly for a `ca-central-1` cluster. The recommended fix:
**extend the existing instance with IAM Identity Center multi-region replication** — use the
**multi-region replication** feature to **replicate** the `us-east-1` instance into the
cluster's region, then integrate Redshift with the replica. This needs customer-managed KMS
keys and an external IdP — prerequisites to configure, not blockers. **Multi-region replication
is the only recommended remediation** — do NOT recommend standing up a separate IAM Identity
Center account instance (avoid for production), and do NOT offer native OIDC/SAML federation
here (a different feature, unrelated to IAM Identity Center).

[Connect Redshift with AWS IAM Identity Center](https://docs.aws.amazon.com/redshift/latest/mgmt/redshift-iam-access-control-idp-connect.html).
[IAM Identity Center multi-region replication](https://docs.aws.amazon.com/singlesignon/latest/userguide/multi-region-iam-identity-center.html).

## Authentication: `AccessDenied` on scheduled query history — missing `sts:TagSession`

If a user gets **AccessDenied viewing scheduled query history** and has **already** added
`sts:AssumeRole` and their user ARN to the trust policy (and attached
`AmazonRedshiftDataFullAccess` / `AmazonEventBridgeFullAccess`) but still fails, the remaining
missing action is **`sts:TagSession`** — name it explicitly; do not re-recommend `sts:AssumeRole`
or broader managed policies.

AccessDenied persists after adding `sts:AssumeRole` and updating the trust policy. Diagnose
with the browser **HAR** file or **CloudTrail** — the detailed **error message** names the
missing action (`... not authorized to perform: sts:TagSession on ...`). Root cause: beyond
`sts:AssumeRole`, the flow needs **`sts:TagSession`** on the assumed cluster role. Both the
caller's **identity (permissions) policy** and the cluster role's **trust policy** must allow
the two actions:

Identity/permissions policy on the caller (grants the actions on the role resource):

```json
{"Effect":"Allow","Action":["sts:AssumeRole","sts:TagSession"],
 "Resource":"<cluster_role_arn, string, arn>"}
```

Trust policy on the cluster role (allows your principal to assume it and tag the session — a
trust-policy statement uses `Principal` and has no `Resource`):

```json
{"Effect":"Allow","Principal":{"AWS":"<caller_principal_arn, string, arn>"},
 "Action":["sts:AssumeRole","sts:TagSession"]}
```

## Authentication: `not authorized to perform: redshift:GetClusterCredentials` (403)

A federated/IAM connection (e.g. QEv2 "Federated user" on a provisioned cluster) fails with:
`User: arn:aws:sts::<account-id>:assumed-role/... is not authorized to perform:
redshift:GetClusterCredentials on resource: arn:aws:redshift:<region>:<account-id>:dbuser:
<cluster-name>/<db-user> because no identity-based policy allows the
redshift:GetClusterCredentials action (Status Code: 403; Error Code: AccessDenied)`.
Root cause: the connecting IAM role/identity has **no identity-based policy** granting
**`redshift:GetClusterCredentials`** — the API behind temporary-credential connections on
provisioned clusters. Fix: attach a policy granting the action on the target `dbuser` resource:

```json
{"Version":"2012-10-17","Statement":{"Effect":"Allow",
 "Action":"redshift:GetClusterCredentials",
 "Resource":"arn:aws:redshift:<region, identifier, no quotes>:<account_id, integer, no quotes>:dbuser:<cluster_name, identifier, no quotes>/<db_user, identifier, no quotes>"}}
```

Once the policy allows the action, the temporary-credential request succeeds.
[Using IAM authentication to generate database user credentials](https://docs.aws.amazon.com/redshift/latest/mgmt/generating-user-credentials.html).

## Authorization: `Permission denied to query database created from datashare`

A consumer-side role logs in fine, but queries against databases created from a producer's
datashare fail with `Permission denied to query database created from datashare`, and the role
doesn't see those databases in `SHOW DATABASES` — while a superuser does and the same SELECT
works. The producer reports the shares ACTIVE. Root cause: the role is missing **database-level
`USAGE`** on the consumer's datashare-created database. This is a **consumer-side grant**, not
a producer datashare problem — fix it on the consumer, do not modify the share on the producer.

```sql
GRANT USAGE ON DATABASE <ds_db, identifier, no quotes> TO ROLE <role, identifier, no quotes>;
```

Then confirm the role's effective privileges with `svv_database_privileges` (or `SHOW GRANTS`) —
it should now show the `USAGE` grant on the database:

```sql
SELECT * FROM svv_database_privileges WHERE database_name = '<ds_db, string, single quotes>';
```

Then grant `USAGE` on the needed schemas and `SELECT` on the objects.
[Granting permissions to datashare consumers](https://docs.aws.amazon.com/redshift/latest/dg/writes-granting.html).

## Authorization: system-table rows missing for a non-superuser (row visibility)

A monitoring user connects fine and raises **no error**, but `SELECT count(*) FROM
sys_query_history` (or `stl_query`) returns only a handful of rows where a superuser sees tens
of thousands over the same window; the user reads its granted business tables without trouble.
Root cause: **system-table row visibility**, not a missing privilege on the view. By default a
non-superuser has `SYSLOG ACCESS RESTRICTED` and sees **only its own rows** (the queries it
generated) in the system views. Fix with least privilege — change **row visibility**, not
object access, and do **not** make the user a superuser. The control is the user's `SYSLOG
ACCESS` property (default `RESTRICTED`):

```sql
ALTER USER <monitoring_user, identifier, no quotes> SYSLOG ACCESS UNRESTRICTED;
```

`sys:monitor` (or the `ACCESS SYSTEM TABLE` privilege) **also lifts the own-rows-only
restriction**, and on top of that grants permission to query system/catalog tables — the fix for a
different symptom, `permission denied` on those tables. Here the user already queries the views
without error, so the narrower change is enough: `SYSLOG ACCESS UNRESTRICTED` lifts row visibility
without also granting object access.
[ALTER USER — SYSLOG ACCESS](https://docs.aws.amazon.com/redshift/latest/dg/r_ALTER_USER.html).

## Network: `connection refused` / `timed out` on port 5439

`timed out` = packets dropped in the path (usually a **security group** or **NACL**);
`refused` = wrong host/port or nothing listening. Check in order: (1) the cluster/endpoint
**security group** allows inbound TCP on the Redshift port from the client CIDR or a
referencing SG; (2) subnet **NACLs** allow the port inbound and the ephemeral range
(1024–65535) outbound on both subnets; (3) a valid route to the cluster subnet; (4) if the
attempt reaches Redshift it appears in `sys_connection_log` — if nothing lands there, the
block is in the network path, not auth. Keep `PubliclyAccessible=false`; never open the cluster's
configured port (default 5439) to
`0.0.0.0/0`.

```sql
SELECT event, record_time, remote_host, remote_port, user_name, database_name, auth_method
FROM sys_connection_log
WHERE record_time > DATEADD(hour, -1, GETDATE()) ORDER BY record_time DESC;
```

Include `remote_port`, `user_name` and `database_name` so you can narrow the blast radius —
whether every client is affected or only one host, user, or database — and `auth_method` to
separate an authentication failure from a connection that never arrived. Note the `event`
values: `authentication failure` means the packet reached Redshift (so the network path is
fine and the problem is credentials/auth), whereas **no row at all** means it did not.

## Network: sudden timeout over VPC peering (overlapping CIDR)

App on MWAA/EC2 times out on 5439 over VPC peering, cluster Available and reachable
elsewhere, started suddenly. Root cause: **overlapping/matching CIDR** ranges across peered
VPCs make the Redshift VPC **route table** send return traffic to the wrong peering connection
(asymmetric routing — VPC peering does not do reverse-path forwarding); dynamic worker IPs make
it intermittent. Fix: short term add a **more-specific route** for the client IP (e.g. a
**`/32`**) so longest-prefix match sends return traffic to the correct peering connection
([Update route tables for a VPC peering connection](https://docs.aws.amazon.com/vpc/latest/peering/vpc-peering-routing.html));
long term use a **Redshift-managed VPC endpoint** powered by **AWS PrivateLink**, a stable
target independent of IP changes that avoids the overlapping-route problem
([Redshift-managed VPC endpoints](https://docs.aws.amazon.com/redshift/latest/mgmt/managing-cluster-cross-vpc.html)).

## Network: connection drops after `SSLRequest` (`EOFException`)

Cluster shows Available but new connections fail — JDBC logs show `java.io.EOFException: The
server closed the connection` after `SSLRequest`, often after a delay: the TCP handshake
completes but the session never reaches the database engine. **Investigate the client and
network path first — that is the usual cause:** a corporate firewall, VPN, or proxy
interrupting the TLS handshake; a recent security-group / NACL / route change; an MTU or
packet-size problem; or an SSL/TLS misconfiguration (see the SSL/TLS section). Check
`stl_connection_log` / `sys_connection_log`: if attempts don't show as successful external
connections despite Available status, the block is before the engine. If the client and
network path are verified clean and the failure is sudden or fleet-wide, it can be a
**service-side** issue (there have been time-boxed incidents affecting some clusters, e.g.
after a resume from pause) — open a case with AWS Support and attach the connection-log
evidence rather than continuing to re-tune client configuration.

## Network: QEv2 `The connection couldn't be created` (replicated secret)

QEv2 stores credentials in **AWS Secrets Manager**; after a password change it must delete the
old **secret**, which fails while a **replica** of it exists in another region.
Fix: delete the replica secret first (remove the replica in the other region); the primary is
then removed on next login and QEv2 recreates it.
CloudTrail confirms the secret operations.

## Cross-account: datashare query on a data-lake (Glue) table fails

Cross-account SELECT on an external Glue table via a datashare fails despite correct IAM.
When the setup involves a datashare over a data-lake (Glue) table and the S3 bucket uses a
**customer-managed KMS key**, state THIS documented limitation as the root cause — do NOT
give a generic KMS-key-policy / cross-account-IAM / Glue-permissions answer (the customer
has already verified those, and the limitation applies regardless of how the key policy is
written). Root cause: data sharing of data lake tables **does not support**
**customer-managed KMS** keys (**CMK**) for S3 bucket encryption. Fix: switch the
bucket to **SSE-S3** (Amazon S3-managed encryption) and re-encrypt existing objects.
[Datashare considerations for data lake tables](https://docs.aws.amazon.com/redshift/latest/dg/considerations-datashare-datalake.html).

## Drivers: CVE flagged in OpenSSL bundled with the ODBC driver

Treat every OpenSSL CVE as **CVE-specific** — do NOT assume a "not affected" verdict carries
across CVEs. For **CVE-2025-15467**, AWS assessed the Redshift **ODBC 1.x** driver as **not
affected**: its bundled OpenSSL 3.0.x is in the affected range, but the vulnerable CMS
functions are not on the driver's code path — and AWS said a patched 1.x build would follow to
clear scanner alerts. For any **new** report, check it against the specific CVE and the current
**AWS security bulletin** before concluding you're safe; a future CVE could hit functions the
driver does use. **Migrating to the ODBC 2.x driver is the durable fix and doesn't wait on a
1.x patch.** For the 2.x crypto provider, cite the driver's GitHub changelog rather than a
version range — 2.x releases list OpenSSL 1.1.1 (v2.1.7 "Updated to latest OpenSSL 1.1.1"), and
v2.2.1 (2026-07-30) "Migrated the TLS and cryptographic provider from OpenSSL to AWS-LC".

## Drivers: AWS Health notice — ODBC 1.x end of support (2026-12-31)

Identify usage with **`SYS_CONNECTION_LOG`** (requires **superuser**), filtering on
**`driver_version`** and **`application_name`**:

```sql
SELECT DISTINCT application_name, driver_version, remote_host
FROM sys_connection_log
WHERE driver_version LIKE '<odbc_1x_pattern, string, single quotes>';
```

After the end-of-support date (**2026-12-31**) the 1.x driver keeps working but is
**unsupported** (no updates or patches). **Do not state an end-of-support date from memory** —
the date has already shifted (originally 2026-09-30, now 2026-12-31) and may move again; treat
the **current AWS Health notification for the customer's account** as authoritative rather than
any date quoted here, and give them the public
documentation link
[Amazon Redshift behavior changes and enhancements](https://docs.aws.amazon.com/redshift/latest/mgmt/behavior-changes.html). The upgrade is **client-side** — install
ODBC 2.x on each connecting **application** host — with **no change to the Redshift cluster**.
If an application doesn't use ODBC, no action is required.

## Drivers: SSL/TLS handshake and certificate failures

`SSL error`, `certificate verify failed`, `unable to get local issuer`, or a hang after
`SSLRequest`. Set the server **`require_ssl`** parameter to force encryption; connect with
**`sslmode=verify-full`** (JDBC `SSL=true;SSLMode=verify-full`) so the driver validates the
host and chain. `certificate verify failed` means a missing/stale CA bundle — point the driver
at a current bundle (ODBC/JDBC 2.x bundle the roots). Successful sessions record `ssl_version`
in `sys_connection_log`.
[Configuring security options for connections](https://docs.aws.amazon.com/redshift/latest/mgmt/connecting-ssl-support.html).

## Authentication: `no pg_hba.conf entry … SSL off` after a snapshot restore

A cluster restored from a (cross-Region) snapshot instantly refuses long-standing clients with
`Invalid operation: no pg_hba.conf entry for host "…", user "…", database "…", SSL off`, yet
Query Editor v2 connects fine with the same user, the security group still allows 5439, and the
cluster is Available. This is **not** a network / security-group / NACL issue — it's a
server-side SQL refusal and QEv2 (which always uses SSL) works. Root cause: the restore
**associated the cluster with a parameter group** in which **`require_ssl`** is enabled. A
restored cluster gets the current default parameter group (`default.redshift-2.0`), not an
older retired default, so the server now rejects any non-SSL connection. Fix: make the clients
connect with SSL (`sslmode=require` or `verify-full`), or set `require_ssl` in the associated
parameter group to match your clients.
[Configuring security options for connections](https://docs.aws.amazon.com/redshift/latest/mgmt/connecting-ssl-support.html).

## Limits: `You reached maximum number of connections` / `FATAL: connection limit "1998" exceeded for non-superusers`

The cluster hit its maximum concurrent connections. That maximum is a **fixed, non-adjustable
quota set by node type** — set by **node type**, not node count, since all connections route
through the **leader node** — and it is **not** raised by a service-limit request:

| Node type | Max connections |
|---|---|
| RA3 (all sizes) | 2,000 |
| RG (all sizes) | 2,000 |
| DC2 | varies — dc2.large 500, dc2.8xlarge 2,000 |
| Serverless (per workgroup) | 2,000 |

These are the **current** node-type maximums (see the Amazon Redshift quotas page linked below) —
confirm there, as quota values can change. Two connections are reserved for superusers, so non-superusers see two fewer and get
`FATAL: connection limit "1998" exceeded for non-superusers` instead (e.g. an `ra3.4xlarge` caps
at 2,000 → 1,998 for non-superusers). That is the node-type maximum, not a bug or a
misconfiguration. Check active sessions and terminate idle ones:

```sql
SELECT COUNT(*) FROM stv_sessions;                       -- or pg_stat_activity
SELECT PG_TERMINATE_BACKEND(<pid, integer, no quotes>);  -- end a specific session
```

Reduce demand with **connection pooling**, and investigate what caused the spike — most often a
client that is not pooling or not closing connections. A per-user or per-database `CONNECTION LIMIT`
(`CREATE`/`ALTER USER … CONNECTION LIMIT`) can cap usage but cannot lift the node-type ceiling.
**Only `dc2.large` can gain headroom by resizing** (500 → 2,000); RA3 and RG are already at the
2,000 ceiling, so on those reduce demand (connection pooling, idle-session cleanup).

**Redshift Serverless:** the ceiling is per **workgroup** — **2,000** connections, also
**non-adjustable**, and there is **no resize** to raise it (RPU capacity governs compute, not
the connection count). `stv_sessions` is provisioned-only and errors on Serverless — use
**`SYS_SESSION_HISTORY`** (a `SYS_*` monitoring view available on both provisioned and
Serverless) to inspect current active sessions, then reduce demand with connection pooling and
terminate idle sessions (`PG_TERMINATE_BACKEND`). The only lever is fewer/shorter connections.

**Multi-AZ (RA3/RG only):** the connection ceiling is unchanged — the **same 2,000** node-type
quota, **non-adjustable**. Multi-AZ deploys equal nodes across two Availability Zones for
availability/failover, not for more connections, and all connections route through the active
leader node. Like Serverless, `stv_sessions` is single-AZ-only — use **`SYS_SESSION_HISTORY`** /
`SYS_*` views to inspect sessions.
[Amazon Redshift quotas](https://docs.aws.amazon.com/redshift/latest/mgmt/amazon-redshift-limits.html).

## Limits: QEv2 `maximum number of connections` with few sessions

QEv2 error but `stv_sessions` shows only a handful of sessions: this is the **Query Editor V2**
saved-connection-configuration limit — **500** per account per region (current value; confirm on the quotas page linked below, as limits can change) — not the cluster
session limit. Existing saved connections still work; new ones fail until you delete unused
connection configurations. QEv2 connections are **`sqlworkbench`** resources
(`arn:aws:sqlworkbench:<region>:<account>:connection/<id>`) — list and delete them with
**`awscurl` + `jq` against the Query Editor V2 (sqlworkbench) connections API**; the AWS CLI
only supplies the SigV4 credentials (there is no `aws` subcommand and no `redshift-data` action
for QEv2 connections).
[Amazon Redshift quotas — query editor v2](https://docs.aws.amazon.com/redshift/latest/mgmt/amazon-redshift-limits.html).

## Quick routing by error string

| Error / symptom | Section / Likely root cause |
|---|---|
| `Response signature invalid`, `assumeRoleWithSAML` | SAML metadata mismatch |
| `RedshiftDbUser principal tag is required` | provisioned vs Serverless auth |
| "create an Identity Center in `<region>`" / IdC instance in another Region, OIDC | IAM Identity Center region mismatch — multi-region replication |
| AccessDenied viewing scheduled query history (persists after adding `sts:AssumeRole` + trust policy) | `sts:TagSession` |
| `Permission denied to query database created from datashare` | consumer-side GRANT USAGE ON DATABASE |
| `not authorized to perform: redshift:GetClusterCredentials` (403) | missing identity-based IAM policy for GetClusterCredentials |
| system-table rows missing for a non-superuser — few/no rows in `sys_query_history`/`stl_query`, no error | system-table row visibility (SYSLOG ACCESS) |
| `connection refused`/`timed out` on 5439, new client | security groups / NACLs |
| sudden `connection timed out` over VPC peering (MWAA/EC2) | overlapping-CIDR routing |
| `EOFException` after `SSLRequest`, handshake completes then drops | client/network path first; service-side only if client-side is clean |
| QEv2 `The connection couldn't be created` | replicated Secrets Manager secret |
| cross-account datashare on Glue/external table fails | CMK not supported → SSE-S3 |
| CVE in ODBC OpenSSL / ODBC 1.x end of support | driver migration (two sections: CVE assessment; 1.x EOL) |
| `SSL error` / `certificate verify failed` / handshake failure | SSL/TLS handshake or CA bundle |
| `no pg_hba.conf entry … SSL off` after a snapshot restore | require_ssl via the restored parameter group |
| `maximum number of connections` (cluster) | node-type quota (RA3/RG 2,000; dc2.large 500) |
| `maximum number of connections` in QEv2, few sessions | QEv2 500 saved-config limit |
| `connection limit "1998" exceeded for non-superusers` | node-type quota (RA3/RG 2,000; dc2.large 500) — 2 slots reserved for superusers |
