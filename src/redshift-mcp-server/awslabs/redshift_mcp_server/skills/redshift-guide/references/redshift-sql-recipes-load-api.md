# Redshift Recipes: COPY & Data API (Working Code)

Procedural patterns agents must SHOW as working code, not describe as rules.

## Recipe: COPY with error handling

```bash
#!/bin/bash
# Load CSV from S3. Tolerates bad rows, diagnoses failures via Data API.
export AWS_SDK_UA_APP_ID="aws#skill#redshift-guide#1.0"
WORKGROUP="<workgroup_name, string, no quotes>"
DB="<database, string, no quotes>"
TABLE="<schema.table, identifier, no quotes>"
ROLE_ARN="<iam_role_arn, string, no quotes>"
S3_PATH="<s3_uri, string, no quotes>"

# These values are interpolated straight into the SQL text. Set them yourself, or
# validate them (allowlist the identifier, verify the s3:// URI) before use — a table
# name or path taken from user input is a SQL-injection vector here. The Data API's
# --parameters option binds values, but not identifiers, so it does not cover $TABLE.
#
# --wait-time-seconds (1-30) is long polling: the call returns as soon as the
# statement finishes, so a short load needs no polling at all. A COPY can exceed
# 30s, so still loop — but each iteration waits up to 30s instead of sleeping
# blindly, which cuts calls against a TPS-limited quota.
STMT_ID=$(aws redshift-data execute-statement \
  --workgroup-name "$WORKGROUP" --database "$DB" --wait-time-seconds 30 \
  --sql "COPY $TABLE FROM '$S3_PATH' IAM_ROLE '$ROLE_ARN' CSV IGNOREHEADER 1 MAXERROR 100 DATEFORMAT 'auto' TIMEFORMAT 'auto';" \
  --query 'Id' --output text)

DEADLINE=$(( SECONDS + 900 ))   # always bound the loop
while :; do
  STATUS=$(aws redshift-data describe-statement --id "$STMT_ID" \
    --wait-time-seconds 30 --query 'Status' --output text)
  case "$STATUS" in FINISHED|FAILED|ABORTED) break ;; esac
  if (( SECONDS >= DEADLINE )); then echo "COPY still $STATUS after 900s"; exit 1; fi
done

if [[ "$STATUS" != "FINISHED" ]]; then
  echo "COPY failed: $STATUS"
  aws redshift-data describe-statement --id "$STMT_ID" --query 'Error' --output text
  # Row-level diagnostics. The diagnostic SELECT is short, so one long-polled
  # execute-statement is enough — no sleep before fetching results.
  ERR_ID=$(aws redshift-data execute-statement --workgroup-name "$WORKGROUP" --database "$DB" \
    --wait-time-seconds 30 \
    --sql "SELECT file_name, line_number, column_name, error_message FROM sys_load_error_detail ORDER BY start_time DESC LIMIT 20;" \
    --query 'Id' --output text)
  aws redshift-data get-statement-result --id "$ERR_ID"
  exit 1
fi
echo "COPY succeeded: $STMT_ID"
```

- `MAXERROR 100` fails the load once errors reach 100.
- `sys_load_error_detail` for diagnostics (all deployment types).
- `IAM_ROLE` is the **namespace role** (attached to the namespace), not the caller.

## Recipe: Data API poll loop (Python)

```python
import time, boto3
from botocore.config import Config

# WaitTimeSeconds (1-30) = long polling: the call returns as soon as the statement
# finishes instead of returning immediately and forcing you to poll. Prefer it —
# fewer calls against a TPS-limited quota, lower latency on short statements. It
# does NOT replace the loop: on expiry the statement may still be running, so
# anything that can exceed 30s still needs a bounded loop.
WAIT = 30

def execute_and_wait(sql, workgroup, database="dev", timeout_s=300):
    # `sql` is sent as-is. Do not build it from unsanitized input: the Data API's
    # Parameters option binds values, not identifiers, so a table or column name
    # taken from user input is a SQL-injection vector. Allowlist identifiers.
    # Region comes from the environment (AWS_REGION / AWS_DEFAULT_REGION) or your
    # profile — set it there rather than pinning one here.
    client = boto3.client("redshift-data", config=Config(user_agent_appid="aws#skill#redshift-guide#1.0"))
    # One call submits AND waits up to WAIT seconds for completion.
    desc = client.execute_statement(
        WorkgroupName=workgroup, Database=database, Sql=sql, WaitTimeSeconds=WAIT
    )
    stmt_id = desc["Id"]

    deadline = time.monotonic() + timeout_s
    while desc["Status"] not in ("FINISHED", "FAILED", "ABORTED"):
        if time.monotonic() >= deadline:
            raise TimeoutError(f"{stmt_id} still {desc['Status']} after {timeout_s}s")
        desc = client.describe_statement(Id=stmt_id, WaitTimeSeconds=WAIT)

    if desc["Status"] != "FINISHED":
        raise RuntimeError(f"{stmt_id} {desc['Status']}: {desc.get('Error', '')}")
    if not desc.get("HasResultSet"):
        return []

    rows, kwargs = [], {"Id": stmt_id}
    while True:
        r = client.get_statement_result(**kwargs)
        cols = [c["name"] for c in r["ColumnMetadata"]]
        rows.extend([[None if "isNull" in f else list(f.values())[0] for f in rec] for rec in r["Records"]])
        if "NextToken" not in r:
            break
        kwargs["NextToken"] = r["NextToken"]
    return [dict(zip(cols, row)) for row in rows]
```

`GetStatementResult` also accepts `WaitTimeSeconds`, but its expiry behaviour differs
from the others: instead of reporting an in-progress status it raises
`ResourceNotFoundException` — meaning "no results YET", not "results gone". Treating it
as a failure reports a false error on a still-running query, so catch and retry:

```python
def wait_for_result(client, stmt_id, timeout_s=300):
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            return client.get_statement_result(Id=stmt_id, WaitTimeSeconds=WAIT)
        except client.exceptions.ResourceNotFoundException:
            if time.monotonic() >= deadline:
                raise TimeoutError(f"{stmt_id}: no results after {timeout_s}s")
```

- Target: **Serverless** = `WorkgroupName`, **Provisioned** = `ClusterIdentifier`; plus `Database` either way. Auth is independent of that choice — e.g. temporary credentials (add `DbUser` to connect to a cluster as a database user), Secrets Manager (`SecretArn`), or IAM Identity Center. On the CLI these are `--workgroup-name` / `--cluster-identifier`, `--database`, and `--db-user` or `--secret-arn`.
  `DbUser` issues temporary credentials via `GetClusterCredentials` rather than using a
  stored password. Rotate the secret when using `SecretArn`.
- Log the API calls: `redshift-data:*` actions land in CloudTrail, and cluster-side
  activity needs Redshift audit logging (`useractivitylog`, `connectionlog`, `userlog`)
  enabled separately — CloudTrail alone does not record the SQL that ran.
- `GetStatementResult` returns a result set to anyone who can call it with the statement
  ID, so avoid selecting PII or secret columns into a result set you do not need.
  `sys_load_error_detail` exposes rejected rows in `raw_line`/`err_reason`.
- Throttle = HTTP **400** (not 429). ExecuteStatement TPS is quota-limited — check the Data API quotas page.
- Calls are async by default; **`WaitTimeSeconds` (1-30) turns
  any call into a long poll** that returns when the statement finishes or the wait
  expires, whichever is first. Prefer it over blind sleeping, but keep a bounded loop
  for work that can exceed 30s. Supported on `ExecuteStatement`,
  `BatchExecuteStatement`, `DescribeStatement`, `GetStatementResult`, and
  `GetStatementResultV2`.
- **Expiry behaviour differs by operation** (verified live): `ExecuteStatement` /
  `DescribeStatement` return the current in-progress status, but `GetStatementResult`
  raises **`ResourceNotFoundException`** (`Query does not have result. Please check
  query status with DescribeStatement.`). That means "no results yet", NOT "results
  gone" — catch and retry rather than reporting a failure.
- `BatchExecuteStatement` + `WaitTimeSeconds` holds until **every** sub-statement
  completes, returning the batch parent id and overall status. To wait on one
  sub-statement, long-poll `DescribeStatement`/`GetStatementResult` with that
  sub-statement's id — it returns as soon as that one finishes, without waiting for the
  rest of the batch.
