# Remote-Deployment Integration Test Harness

This directory (`integration/`) is the **Integration_Test_Harness** for the AWS HealthOmics
MCP Server. It proves, against **live AWS resources**, that the server's `streamable-http`
transport works end-to-end behind two representative fronting layers and that the opt-in
multi-tenant credential-resolution path works when backed by a real DynamoDB role registry.

It delivers two deployments:

- **`agentcore`** — the server is hosted on Amazon Bedrock AgentCore Runtime
  (`server_protocol: MCP`, `streamable-http` on container port `8000`, the fixed port AgentCore
  routes MCP traffic to). AgentCore is the sole ingress and terminates inbound authentication at
  its boundary.
- **`apigateway`** — Amazon API Gateway fronts the server. The server binds to `127.0.0.1`;
  the gateway authenticates callers and forwards only authenticated requests through a private
  (VPC-link) integration.

The harness is **opt-in and skipped by default** (see [Opt-In Signal](#opt-in-signal)). The
project's default `uv run pytest` invocation stays fully offline: it constructs no AWS client,
resolves no credentials, and opens no network connection to AWS.

> **Placeholder convention.** Every value you must substitute is written in
> `<UPPER_SNAKE>` form — for example `<REGION>`, `<ACCOUNT_ID>`, `<TENANT_A_ROLE_ARN>`,
> `<EXTERNAL_ID>`, `<ENDPOINT>`, `<BEARER_TOKEN>`. Replace the entire token, including the
> angle brackets, with a real value before running a command.

---

## Table of contents

- [Known limitations](#known-limitations)
- [Prerequisites](#prerequisites)
  - [IAM actions](#iam-actions)
  - [Tools and minimum versions](#tools-and-minimum-versions)
  - [Account configuration](#account-configuration)
  - [Environment variables](#environment-variables)
- [Opt-In Signal](#opt-in-signal)
- [AgentCore deployment](#agentcore-deployment)
  - [AgentCore provision](#agentcore-provision)
  - [AgentCore run (tests)](#agentcore-run-tests)
  - [AgentCore teardown](#agentcore-teardown)
- [API Gateway deployment](#api-gateway-deployment)
  - [API Gateway provision](#api-gateway-provision)
  - [API Gateway run (tests)](#api-gateway-run-tests)
  - [API Gateway teardown](#api-gateway-teardown)
- [Registry_Record](#registry_record)
- [Tenant_Role trust relationship](#tenant_role-trust-relationship)

---

## Known limitations

**The target account must permit `sts:TagSession`.** The server's multi-tenant `jwt`
mechanism attaches an ABAC session tag identifying the caller (`Tags=[{caller: <sub>}]`) on
*every* `sts:AssumeRole` call, and this is not configurable. Provisioning grants
`sts:TagSession` in both the execution-role policy and each Tenant_Role trust policy, but if a
Service Control Policy (SCP) or permission boundary on the account denies `sts:TagSession`
org-wide, the tagged assume fails with `AccessDenied` and every tool request is rejected with
HTTP 401. This has been observed on locked-down accounts (for example some Isengard accounts).

Symptom: provisioning reports **complete** and the AgentCore runtime reaches `READY`, but the
transport and isolation tests fail with `Received error (401) from runtime`, and the runtime's
CloudWatch logs show:

```
JWT-to-STS exchange failed for inbound request: ClientError
```

with the underlying STS error being `AccessDenied ... not authorized to perform: sts:TagSession`.

To confirm whether an account blocks it, run (no harness required):

```bash
aws sts assume-role --role-arn <ANY_ASSUMABLE_ROLE_ARN> \
  --role-session-name check --tags Key=caller,Value=check
```

If that returns `AccessDenied` on `sts:TagSession` while the same call without `--tags`
succeeds, the account forbids session tagging. Run the harness in an account whose SCPs permit
`sts:TagSession`, or have the guardrail relaxed.

**Workaround for `sts:TagSession`-restricted accounts: `--inbound explicit`.** The AgentCore
deployment accepts `--inbound explicit`, which runs the server with its `explicit` inbound
mechanism instead of `jwt`. In this mode the harness assumes each Tenant_Role **without**
session tags (which succeeds even where `sts:TagSession` is denied) and forwards the resulting
short-lived credentials to the server via `X-Aws-*` headers; the server uses them directly, so
no `AssumeRole`/tagging happens inside the server. AgentCore still authenticates the caller at
its JWT authorizer, and the cross-tenant isolation guarantee still holds (each tenant's calls
run under its own assumed-role identity). Trade-off: this validates transport + isolation via
the `explicit` path, **not** the `jwt` registry→assume exchange — use it to run end-to-end in a
restricted account, and the default `jwt` mode (Option C: an account permitting
`sts:TagSession`) for full-fidelity coverage.

```bash
python -m integration.deploy.cli e2e \
  --deployment agentcore \
  --region <REGION> \
  --inbound explicit \
  --teardown
```

---

## Prerequisites

You need an AWS account, credentials on the default boto3 chain (environment,
`~/.aws/config`, SSO, or an instance/role profile), and the tools and permissions below.

### IAM actions

The identity that runs `provision` / `teardown` and the integration tests needs the following
IAM actions, each scoped to the indicated resource. Scope down to the specific resource ARNs
your run uses; the harness's default names are `aho-mcp-itest-registry` (registry table),
`aho-mcp-itest` (ECR repository and AgentCore runtime), and `aho-mcp-itest-registry-apigw`
(REST API).

| IAM action(s) | Resource scope | Why |
|---|---|---|
| `dynamodb:CreateTable`, `dynamodb:DescribeTable`, `dynamodb:PutItem`, `dynamodb:DeleteTable` | The registry table ARN `arn:aws:dynamodb:<REGION>:<ACCOUNT_ID>:table/aho-mcp-itest-registry` | Create the role-registry table, wait for it to become active, write the Tenant_A/Tenant_B records, and delete it on teardown |
| `ecr:CreateRepository`, `ecr:DescribeRepositories`, `ecr:GetAuthorizationToken`, `ecr:BatchCheckLayerAvailability`, `ecr:InitiateLayerUpload`, `ecr:UploadLayerPart`, `ecr:CompleteLayerUpload`, `ecr:PutImage`, `ecr:DeleteRepository` | The repository ARN `arn:aws:ecr:<REGION>:<ACCOUNT_ID>:repository/aho-mcp-itest` (`ecr:GetAuthorizationToken` requires `*`) | Create the ECR repository, authenticate the Docker client, push the harness image, and force-delete the repository on teardown (**agentcore** only) |
| `bedrock-agentcore:CreateAgentRuntime`, `bedrock-agentcore:DeleteAgentRuntime` (and the AgentCore control-plane describe actions) | The AgentCore runtime ARN `arn:aws:bedrock-agentcore:<REGION>:<ACCOUNT_ID>:runtime/aho-mcp-itest` | Create and delete the AgentCore Runtime hosting the server (**agentcore** only) |
| `apigateway:POST`, `apigateway:GET`, `apigateway:PUT`, `apigateway:DELETE` | The API Gateway resource ARNs under `arn:aws:apigateway:<REGION>::/restapis*` and `.../vpclinks*` | Create the REST API, authorizer, method, private VPC-link integration, deployment, and delete them on teardown (**apigateway** only) |
| `iam:CreateRole`, `iam:PutRolePolicy`, `iam:GetRole`, `iam:ListRolePolicies`, `iam:DeleteRolePolicy`, `iam:DeleteRole` | The role ARNs `arn:aws:iam::<ACCOUNT_ID>:role/aho-mcp-itest-*` | Auto-create and delete the two Tenant_Roles and the AgentCore execution role (**agentcore** only) |
| `iam:PassRole` | The auto-created execution role ARN `arn:aws:iam::<ACCOUNT_ID>:role/aho-mcp-itest-exec` | Pass the execution role to AgentCore Runtime at create time (**agentcore** only) |
| `cognito-idp:CreateUserPool`, `cognito-idp:CreateUserPoolClient`, `cognito-idp:AdminCreateUser`, `cognito-idp:AdminSetUserPassword`, `cognito-idp:AdminGetUser`, `cognito-idp:AdminInitiateAuth`, `cognito-idp:DeleteUserPool` | `*` (Cognito user pool ARNs are only known after creation) | Auto-create the identity provider, mint the per-tenant bearer tokens, and delete the pool on teardown (**agentcore** only) |
| `sts:AssumeRole` (and `sts:TagSession` in `jwt` mode) | Each auto-created Tenant_Role ARN (`arn:aws:iam::<ACCOUNT_ID>:role/aho-mcp-itest-tenant-a`, `...-tenant-b`) | In `jwt` mode the deployed server assumes each tenant's mapped role (tagged, with that tenant's `ExternalId`); in `--inbound explicit` mode the harness/operator assumes each Tenant_Role **untagged** to mint the forwarded credentials |
| `sts:GetCallerIdentity` | `*` | Resolve the deployment account id at provision time and report the assumed-role identity in the `WhoAmI` isolation tool |

For the **agentcore** deployment the Tenant_Roles, their trust and permission policies, and the
execution role are all created for you (see the [Tenant_Role trust
relationship](#tenant_role-trust-relationship) for the exact trust policy the harness attaches).
For the **apigateway** deployment you still supply pre-existing Tenant_Role ARNs via `--tenant`,
and those roles must grant whatever HealthOmics permissions the tools under test exercise.

### Tools and minimum versions

| Tool | Minimum version | Used for |
|---|---|---|
| `python` | 3.10+ | Running the CLI (`python -m integration.deploy.cli`) and the tests |
| `uv` | 0.4+ | Dependency management and running the suite (`uv run pytest`, `uv sync`) |
| `docker` | 24+ | Building and pushing the harness container image (**agentcore** only) |
| `aws` CLI | 2.15+ | Verifying account configuration and inspecting/provisioning supporting resources |

Install the project's dependencies first:

```bash
uv sync
```

### Account configuration

- **Region.** Choose a single target region `<REGION>` (for example `us-east-1`) that offers
  Amazon Bedrock AgentCore Runtime, Amazon ECR, Amazon Cognito, Amazon API Gateway, and Amazon
  DynamoDB. Pass it to every command with `--region <REGION>`.
- **Credentials.** Provide credentials on the default boto3 chain for the account
  `<ACCOUNT_ID>` where resources are created. No harness code takes credentials as arguments.
- **`sts:TagSession` must be permitted.** The account's SCPs / permission boundaries must not
  deny `sts:TagSession` (see [Known limitations](#known-limitations)); the multi-tenant path
  fails closed with HTTP 401 otherwise.
- **Tenant roles (agentcore).** Nothing to do — the two Tenant_Roles, the execution role, and
  the Cognito identity provider are auto-created by `provision`/`e2e` and removed by
  `teardown`.
- **Tenant roles (apigateway).** Create the per-tenant IAM roles in advance
  (`<TENANT_A_ROLE_ARN>`, `<TENANT_B_ROLE_ARN>`) with the
  [trust relationship](#tenant_role-trust-relationship) below.
- **API Gateway supporting resources (apigateway only).** The loopback-bound server's private
  target, the network-load-balancer target ARN(s) the VPC link fronts, and the authorizer
  Lambda's invoke ARN are operator-provisioned and supplied through the environment variables
  below; the harness cannot fabricate them.

### Environment variables

The harness and its tests read the following environment variables. None carries a value the
harness invents; each is either the opt-in switch, a provisioning input, or a live-run input.

**Opt-in switch**

| Variable | Meaning |
|---|---|
| `RUN_REMOTE_INTEGRATION_TESTS` | The [Opt_In_Signal](#opt-in-signal). Truthy (`true`/`1`/`yes`/`on`/`enabled`, case-insensitive) enables the integration tests; absent/blank/other keeps them skipped |

**Provisioning inputs (read by the deploy CLI / deployment modules)**

| Variable | Deployment | Meaning |
|---|---|---|
| `AHO_ITEST_TENANTS` | apigateway | Optional fallback for `--tenant` (apigateway only; agentcore auto-provisions its tenants). Multiple tenant specs separated by `;`, each `identity,role_arn,external_id[,account_id]` |
| `AHO_ITEST_APIGW_SERVER_TARGET` | apigateway | The loopback-bound server's private target the VPC-link integration fronts (a resource identifier, not a secret) |
| `AHO_ITEST_APIGW_VPC_LINK_TARGET_ARNS` | apigateway | Comma-separated network-load-balancer ARN(s) the API Gateway VPC link targets |
| `AHO_ITEST_APIGW_AUTHORIZER_URI` | apigateway | The invoke ARN/URI of the API Gateway custom (TOKEN) authorizer Lambda |

**Live-run inputs (read by the integration tests)**

For the **agentcore** deployment the `e2e` command sets all of these automatically from the
freshly provisioned resources and minted tokens, so you only set them by hand when running
`uv run pytest` directly against an existing deployment (or for the apigateway deployment).

| Variable | Used by | Meaning |
|---|---|---|
| `AHO_ITEST_AGENTCORE_ENDPOINT` | AgentCore transport test | The AgentCore MCP endpoint to invoke the server through |
| `AHO_ITEST_APIGATEWAY_ENDPOINT` | API Gateway transport test | The API Gateway invoke endpoint (`https://<API_ID>.execute-api.<REGION>.amazonaws.com/itest/mcp`) |
| `AHO_ITEST_ENDPOINT` | Cross-tenant isolation test | The deployment endpoint used for the interleaved multi-tenant calls |
| `AHO_ITEST_BEARER_TOKEN` | transport tests + credential scan | A valid caller bearer/JWT token (Credential_Material; scanned for leaks) |
| `AHO_ITEST_TENANT_A_TOKEN` | isolation test | Tenant_A's bearer/JWT token (Credential_Material) |
| `AHO_ITEST_TENANT_B_TOKEN` | isolation test | Tenant_B's bearer/JWT token (Credential_Material) |
| `AHO_ITEST_TENANT_A_EXPECTED_ARN` | isolation test | The exact assumed-role ARN `WhoAmI` should return for Tenant_A (`arn:aws:sts::<ACCOUNT_ID>:assumed-role/<ROLE_NAME>/<SESSION>`) |
| `AHO_ITEST_TENANT_B_EXPECTED_ARN` | isolation test | The exact assumed-role ARN `WhoAmI` should return for Tenant_B |
| `AHO_ITEST_DIRECT_TARGET` | direct-access-refused test | The direct (bypass) `host:port` or URL that must **not** be reachable off the fronting layer |
| `AHO_ITEST_CAPTURED_OUTPUT_PATH` | credential-safety test | Path to the file holding the run's full-duration captured stdout+stderr |
| `AHO_ITEST_ARTIFACT_DIR` | credential-safety test | Directory of harness-written artifacts (captured output, logs, reports, inventory) to scan |
| `AHO_ITEST_KNOWN_SECRET_ACCESS_KEY` | credential-safety test | A known STS secret access key value to search for verbatim (Credential_Material) |
| `AHO_ITEST_KNOWN_SESSION_TOKEN` | credential-safety test | A known STS session token value to search for verbatim (Credential_Material) |

**Server-facing variables (injected into the deployed server by the harness — you do not set these)**

`MCP_TRANSPORT=streamable-http`, `MCP_HOST` (`0.0.0.0` for AgentCore's container / `127.0.0.1`
for API Gateway), `MCP_PORT` (`8000` for AgentCore — the fixed MCP container port), `MCP_PATH=/mcp`,
`MCP_MULTI_TENANT=true`, `MCP_INBOUND_AUTH` (`jwt` by default, or `explicit` with
`--inbound explicit`), `MCP_JWT_ROLE_REGISTRY=dynamodb://<TABLE_NAME>`, and `AWS_REGION` /
`AWS_DEFAULT_REGION` (so the server's role-registry DynamoDB client resolves a region inside the
container).

For the **agentcore** deployment the harness's container entrypoint additionally adapts the
*unmodified* server for AgentCore Runtime (no server-package changes): it runs the server
stateless (`stateless_http`), relaxes the SDK's loopback-only DNS-rebinding Host allow-list
(AgentCore is the sole, authenticated ingress and forwards a non-loopback `Host`), and — because
AgentCore strips the reserved `Authorization` header — forwards the caller's token via an
allow-listed non-reserved header (`jwt` mode) or the `X-Aws-*` credential headers (`explicit`
mode), mapping them back for the server.

---

## Opt-In Signal

The Opt_In_Signal is the environment variable **`RUN_REMOTE_INTEGRATION_TESTS`**. It is the
master switch that lets the integration tests under `integration/tests/` run against live AWS.
With it absent, every integration test is skipped at collection time with a reason naming this
variable, and no AWS client is ever built.

**Enable** the integration suite:

```bash
export RUN_REMOTE_INTEGRATION_TESTS=true
```

Recognized truthy values are `true`, `1`, `yes`, `on`, and `enabled` (case-insensitive, with
surrounding whitespace trimmed).

**Disable** the integration suite (return to the offline default):

```bash
unset RUN_REMOTE_INTEGRATION_TESTS
```

**Default offline behavior.** With `RUN_REMOTE_INTEGRATION_TESTS` unset, the project's default
invocation stays offline and contributes zero passed/failed integration results:

```bash
uv run pytest
```

Every test under `integration/tests/` reports `skipped`. The harness's own offline unit and
property tests (under `integration/harness_tests/`) still run because they never touch AWS.

---

## AgentCore deployment

Hosts the server on Amazon Bedrock AgentCore Runtime. **The AgentCore deployment is
zero-setup**: provisioning creates *everything* it needs and teardown deletes it, so no
tenant roles, identity provider, or bearer tokens need to be prepared by hand. Provisioning:

1. Creates two **Tenant_Roles** (Tenant_A / Tenant_B) with an account-root + `ExternalId`
   trust policy and a read-only HealthOmics permission policy.
2. Creates the AgentCore **execution role** the container runs as (scoped to assume the
   Tenant_Roles, read the role registry, pull the image, and write logs).
3. Creates an Amazon **Cognito** user pool + app client + one user per tenant, and mints each
   tenant's bearer token. The user pool is the OIDC provider the AgentCore JWT authorizer
   trusts; each user's `sub` becomes that tenant's registry identity.
4. Creates the **DynamoDB role registry** mapping each `sub` to its Tenant_Role.
5. Builds/pushes the container image (`integration/deploy/image/Dockerfile`, `streamable-http`
   on port `8000`) and creates the **AgentCore Runtime**, wired with the execution role and a
   `customJWTAuthorizer` pinned to the Cognito discovery URL + app-client id.

Provisioning reports **complete** once the AgentCore endpoint reference is emitted.

### AgentCore end-to-end (recommended)

The simplest path is the one-shot `e2e` command: it provisions, wires the freshly minted
tokens and expected ARNs into the environment, runs the AgentCore integration tests, and
(with `--teardown`) deletes everything afterwards — all in one process:

```bash
python -m integration.deploy.cli e2e \
  --deployment agentcore \
  --region <REGION> \
  --teardown
```

By default it runs the AgentCore transport and cross-tenant isolation tests; pass repeatable
`--test <PYTEST_PATH>` options to choose others. The `e2e` command sets
`RUN_REMOTE_INTEGRATION_TESTS` and every `AHO_ITEST_*` input for the test run itself, so you do
not export anything by hand. The minted tokens are held in memory only and are never written
to disk.

### AgentCore provision

To provision without immediately running the tests (for example to inspect the deployment):

```bash
python -m integration.deploy.cli provision \
  --deployment agentcore \
  --region <REGION> \
  --table-name aho-mcp-itest-registry \
  --inventory-path ./agentcore-inventory.json
```

Notes:
- `--deployment` and `--region` are required. `--table-name` defaults to
  `aho-mcp-itest-registry` and `--inventory-path` defaults to `./agentcore-inventory.json`.
- No `--tenant` inputs are needed: the two tenants (Tenant_A / Tenant_B), their roles, and
  their Cognito users/tokens are all created automatically.
- Because the minted bearer tokens are short-lived and held only in memory, run the tests via
  the `e2e` command above (which mints tokens as part of the same run) rather than exporting
  them from a standalone `provision`.

### AgentCore run (tests)

`e2e` runs the tests for you. If you want to run `uv run pytest` directly against an existing
deployment, export the endpoint and a freshly minted bearer token yourself (the transport test
needs only the first two; the isolation test also needs the per-tenant tokens and expected
ARNs):

```bash
export RUN_REMOTE_INTEGRATION_TESTS=true
export AHO_ITEST_AGENTCORE_ENDPOINT="<AGENTCORE_ENDPOINT>"
export AHO_ITEST_ENDPOINT="<AGENTCORE_ENDPOINT>"
export AHO_ITEST_BEARER_TOKEN="<BEARER_TOKEN>"
export AHO_ITEST_TENANT_A_TOKEN="<TENANT_A_BEARER_TOKEN>"
export AHO_ITEST_TENANT_B_TOKEN="<TENANT_B_BEARER_TOKEN>"
export AHO_ITEST_TENANT_A_EXPECTED_ARN="arn:aws:sts::<ACCOUNT_ID>:assumed-role/aho-mcp-itest-tenant-a/<SESSION>"
export AHO_ITEST_TENANT_B_EXPECTED_ARN="arn:aws:sts::<ACCOUNT_ID>:assumed-role/aho-mcp-itest-tenant-b/<SESSION>"

uv run pytest integration/tests/test_agentcore_transport.py integration/tests/test_cross_tenant_isolation.py -v
```

### AgentCore teardown

```bash
python -m integration.deploy.cli teardown \
  --deployment agentcore \
  --region <REGION> \
  --inventory-path ./agentcore-inventory.json
```

Teardown deletes every resource recorded in the inventory (the two Tenant_Roles, the execution
role, the Cognito user pool, the registry table, the ECR repository, and the AgentCore
Runtime). It is idempotent: re-running after the resources are gone reports success, and if any
resource cannot be deleted it exits non-zero and names the undeleted resources.

---

## API Gateway deployment

Fronts the loopback-bound server (`127.0.0.1`) with Amazon API Gateway. Provisioning creates the
DynamoDB role registry with the Tenant_A/Tenant_B records, records the loopback-bound server
target and its VPC link, and creates the REST API with a custom (TOKEN) authorizer and a private
`VPC_LINK` `HTTP_PROXY` integration. Provisioning reports **complete** once the API Gateway
invoke endpoint is emitted.

### API Gateway provision

The three live-only inputs (server target, VPC-link target ARNs, authorizer URI) are supplied
through the environment because the harness cannot fabricate the operator-provisioned compute
and network resources:

```bash
export AHO_ITEST_APIGW_SERVER_TARGET="<SERVER_PRIVATE_TARGET>"
export AHO_ITEST_APIGW_VPC_LINK_TARGET_ARNS="<NLB_TARGET_ARN>"          # comma-separated for multiple
export AHO_ITEST_APIGW_AUTHORIZER_URI="<AUTHORIZER_INVOKE_ARN>"

python -m integration.deploy.cli provision \
  --deployment apigateway \
  --region <REGION> \
  --tenant "<TENANT_A_IDENTITY>,<TENANT_A_ROLE_ARN>,<TENANT_A_EXTERNAL_ID>" \
  --tenant "<TENANT_B_IDENTITY>,<TENANT_B_ROLE_ARN>,<TENANT_B_EXTERNAL_ID>" \
  --table-name aho-mcp-itest-registry \
  --inventory-path ./apigateway-inventory.json
```

The REST API is named `<TABLE_NAME>-apigw` (default `aho-mcp-itest-registry-apigw`) and is
deployed to the `itest` stage, so the emitted endpoint has the form
`https://<API_ID>.execute-api.<REGION>.amazonaws.com/itest/mcp`.

### API Gateway run (tests)

```bash
export RUN_REMOTE_INTEGRATION_TESTS=true
export AHO_ITEST_APIGATEWAY_ENDPOINT="https://<API_ID>.execute-api.<REGION>.amazonaws.com/itest/mcp"
export AHO_ITEST_ENDPOINT="https://<API_ID>.execute-api.<REGION>.amazonaws.com/itest/mcp"
export AHO_ITEST_BEARER_TOKEN="<BEARER_TOKEN>"
export AHO_ITEST_TENANT_A_TOKEN="<TENANT_A_BEARER_TOKEN>"
export AHO_ITEST_TENANT_B_TOKEN="<TENANT_B_BEARER_TOKEN>"
export AHO_ITEST_TENANT_A_EXPECTED_ARN="arn:aws:sts::<ACCOUNT_ID>:assumed-role/<TENANT_A_ROLE_NAME>/<SESSION>"
export AHO_ITEST_TENANT_B_EXPECTED_ARN="arn:aws:sts::<ACCOUNT_ID>:assumed-role/<TENANT_B_ROLE_NAME>/<SESSION>"
export AHO_ITEST_DIRECT_TARGET="127.0.0.1:8000"

uv run pytest integration/tests/test_apigateway_transport.py integration/tests/test_cross_tenant_isolation.py -v
```

### API Gateway teardown

```bash
python -m integration.deploy.cli teardown \
  --deployment apigateway \
  --region <REGION> \
  --inventory-path ./apigateway-inventory.json
```

Teardown deletes every recorded resource (registry table, REST API, and VPC link; the
loopback-bound server compute is operator-managed and has no harness-created cloud resource). It
is idempotent and names any undeleted resources on failure.

---

## Registry_Record

The harness writes one **Registry_Record** per tenant into the DynamoDB role registry; the
server's `RegistryRoleResolver` reads it by the partition key. The table's partition key
attribute is named `identity` (the resolver's default), so no server-side schema override is
needed. Each item has the shape `{ identity, role_arn, external_id, account_id?, enabled? }`:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `identity` | String (partition key) | Yes | The Authenticated_Identity — the JWT `sub` claim value that identifies the tenant and keys the registry lookup |
| `role_arn` | String | Yes | The ARN of the Tenant_Role the server assumes (via `sts:AssumeRole`) to run this tenant's tool calls |
| `external_id` | String | Yes | The non-empty `sts:ExternalId` passed unmodified on the AssumeRole call for this tenant (≤ 1224 chars) |
| `account_id` | String | No | The owning account id, informational only |
| `enabled` | Boolean | No | Defaults to enabled; when present and non-truthy the record is disabled and requests for this identity are rejected with HTTP 401 |

Across all records, `role_arn` values are pairwise distinct and `external_id` values are
non-empty and pairwise distinct (the builder fails closed otherwise), and each `identity`
(partition key) is unique so no tenant's record overwrites another's.

---

## Tenant_Role trust relationship

For the **agentcore** deployment you do not write this policy: `provision`/`e2e` create each
Tenant_Role with a trust policy that trusts the deployment **account root**
(`arn:<PARTITION>:iam::<ACCOUNT_ID>:root`) guarded by the tenant's generated `sts:ExternalId`,
and the execution role is separately scoped to assume only those role ARNs. The reference
policy below documents the shape (and is what you attach yourself for the **apigateway**
deployment, whose Tenant_Roles you supply).

Each **Tenant_Role** named in a Registry_Record must trust the harness/server's calling
identity so the server can assume it per request. The cross-account trust relationship states:

- **Trusted principal:** the account/role under which the deployed server calls AssumeRole —
  the AgentCore Runtime execution role or the loopback-bound server's execution role/account
  (`<HARNESS_ACCOUNT_ID>` / `<HARNESS_ROLE_ARN>`).
- **Action:** `sts:AssumeRole` **and** `sts:TagSession`, guarded by an `sts:ExternalId`
  condition that must equal the tenant's `external_id` from its Registry_Record. `sts:TagSession`
  is required because the server attaches an ABAC session tag identifying the caller on the
  assume-role call; without it STS denies the tagged assume with an AccessDenied error.

Attach a trust policy to each Tenant_Role like the following (substitute the trusted principal
and the tenant's external id):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "<HARNESS_ROLE_ARN>"
      },
      "Action": ["sts:AssumeRole", "sts:TagSession"],
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "<TENANT_EXTERNAL_ID>"
        }
      }
    }
  ]
}
```

Because the trusted principal may live in a different account (`<HARNESS_ACCOUNT_ID>`) from the
Tenant_Role (`<ACCOUNT_ID>`), this is a cross-account trust: the server (in the harness account)
assumes each Tenant_Role (in the tenant's account) with the matching `ExternalId`.
