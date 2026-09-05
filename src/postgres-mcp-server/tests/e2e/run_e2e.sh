#!/usr/bin/env bash
#
# Wrapper for the postgres-mcp-server e2e integration test.
#
# Refreshes AWS credentials with `ada` and then runs the e2e harness against a
# chosen matrix of endpoint types x auth methods. By default it enumerates all
# supported Aurora endpoints (express, serverless) and, for each, every auth
# method that endpoint supports.
#
#   endpoint types : express, serverless   (rds-instance: planned, not yet supported)
#   auth methods   : pg_wire_iam, pg_wire_secret, rds_api
#                    (filtered per endpoint: express -> pg_wire_iam only;
#                     serverless -> rds_api, pg_wire_iam, pg_wire_secret)
#
# Invalid endpoint/auth combinations (e.g. express + rds_api) are rejected by
# the harness before anything is provisioned.
#
# Usage:
#   tests/e2e/run_e2e.sh \
#       --account-id 123456789012 \
#       --role Admin \
#       --region us-west-2 \
#       --engine-version 17.5 \
#       [--endpoint-types express,serverless] \
#       [--auth-types pg_wire_iam,pg_wire_secret,rds_api] \
#       [--provider isengard] \
#       [--log-level INFO] \
#       [--database mcp_test_db] \
#       [--port 5432] \
#       [--log-file path.log] \
#       [--skip-cred-refresh]
#
# Anything after a literal `--` is passed straight through to the harness.
set -euo pipefail

usage() {
  # Print the leading comment header (stripping the leading "# "), stopping at
  # the first non-comment line.
  awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"
  exit "${1:-0}"
}

# --- defaults -------------------------------------------------------------
ACCOUNT_ID=""
ROLE=""
REGION=""
ENGINE_VERSION=""
ENDPOINT_TYPES="express,serverless"
AUTH_TYPES=""            # empty => harness default (all supported for each endpoint)
PROVIDER="isengard"
LOG_LEVEL="INFO"
DATABASE=""
PORT=""
LOG_FILE=""
SKIP_CRED_REFRESH="false"
PASSTHROUGH=()

# --- parse args -----------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --account-id)        ACCOUNT_ID="$2"; shift 2 ;;
    --role)              ROLE="$2"; shift 2 ;;
    --region)            REGION="$2"; shift 2 ;;
    --engine-version)    ENGINE_VERSION="$2"; shift 2 ;;
    --endpoint-types)    ENDPOINT_TYPES="$2"; shift 2 ;;
    --auth-types)        AUTH_TYPES="$2"; shift 2 ;;
    --provider)          PROVIDER="$2"; shift 2 ;;
    --log-level)         LOG_LEVEL="$2"; shift 2 ;;
    --database)          DATABASE="$2"; shift 2 ;;
    --port)              PORT="$2"; shift 2 ;;
    --log-file)          LOG_FILE="$2"; shift 2 ;;
    --skip-cred-refresh) SKIP_CRED_REFRESH="true"; shift ;;
    -h|--help)           usage 0 ;;
    --)                  shift; PASSTHROUGH+=("$@"); break ;;
    *) echo "ERROR: unknown argument: $1" >&2; usage 1 ;;
  esac
done

# --- validate -------------------------------------------------------------
missing=()
[[ -z "$REGION" ]] && missing+=("--region")
[[ -z "$ENGINE_VERSION" ]] && missing+=("--engine-version")
if [[ "$SKIP_CRED_REFRESH" != "true" ]]; then
  [[ -z "$ACCOUNT_ID" ]] && missing+=("--account-id")
  [[ -z "$ROLE" ]] && missing+=("--role")
fi
if [[ ${#missing[@]} -gt 0 ]]; then
  echo "ERROR: missing required argument(s): ${missing[*]}" >&2
  usage 1
fi

# Run from the package root (two levels up from tests/e2e) so `uv run` and the
# relative test path resolve regardless of the caller's working directory.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

if [[ -z "$LOG_FILE" ]]; then
  LOG_FILE="$REPO_ROOT/e2e-$(date +%Y%m%d-%H%M%S).log"
fi

# --- refresh credentials --------------------------------------------------
if [[ "$SKIP_CRED_REFRESH" == "true" ]]; then
  echo ">> Skipping credential refresh (--skip-cred-refresh)"
else
  if ! command -v ada >/dev/null 2>&1; then
    echo "ERROR: 'ada' not found on PATH; install it or pass --skip-cred-refresh" >&2
    exit 1
  fi
  echo ">> Refreshing AWS credentials via ada (account=$ACCOUNT_ID role=$ROLE provider=$PROVIDER)"
  ada credentials update \
    --account="$ACCOUNT_ID" \
    --provider="$PROVIDER" \
    --role="$ROLE" \
    --once
fi

# Fail fast if credentials aren't usable, with a clear message.
if ! aws sts get-caller-identity --region "$REGION" >/dev/null 2>&1; then
  echo "ERROR: AWS credentials are not valid (aws sts get-caller-identity failed)." >&2
  echo "       Refresh them (ada) or check --account-id/--role/--provider." >&2
  exit 1
fi

# --- build harness command ------------------------------------------------
cmd=(uv run python tests/e2e/e2e_integration_test.py
     --region "$REGION"
     --engine-version "$ENGINE_VERSION"
     --endpoint-types "$ENDPOINT_TYPES"
     --log-level "$LOG_LEVEL")
[[ -n "$AUTH_TYPES" ]] && cmd+=(--auth-types "$AUTH_TYPES")
[[ -n "$DATABASE" ]] && cmd+=(--database "$DATABASE")
[[ -n "$PORT" ]] && cmd+=(--port "$PORT")
if [[ ${#PASSTHROUGH[@]} -gt 0 ]]; then
  cmd+=("${PASSTHROUGH[@]}")
fi

echo ">> endpoint-types=$ENDPOINT_TYPES auth-types=${AUTH_TYPES:-<all supported>}"
echo ">> Running: ${cmd[*]}"
echo ">> Logging to: $LOG_FILE"

# Tee combined stdout+stderr to the log while preserving the harness exit code.
set +e
"${cmd[@]}" 2>&1 | tee "$LOG_FILE"
status=${PIPESTATUS[0]}
set -e

echo ">> e2e exited with status $status (log: $LOG_FILE)"
exit "$status"
