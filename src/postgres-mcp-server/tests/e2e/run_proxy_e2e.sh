#!/usr/bin/env bash
#
# Wrapper for the RDS Proxy auto-detection e2e harness.
#
# Runs the proxy harness against RDS instances that ALREADY EXIST in your
# account. Unlike run_e2e.sh, this provisions nothing and deletes nothing, and
# every query it issues is a SELECT.
#
# What it needs from you:
#   --db-instance-identifier  a standalone RPG instance that IS fronted by a proxy
#   --no-proxy-instance       an instance with NO proxy (the control; recommended)
#
# Instances are named by DB instance IDENTIFIER (or ARN), and --database is the
# PostgreSQL database name inside the instance. --secret-arn is OPTIONAL: the
# server discovers the instance's MasterUserSecret on its own. Supply it only if
# the instance has no managed master password, or to also exercise the per-target
# secret override path.
#
# Credentials: this script does not acquire any. It uses whatever the standard AWS
# credential chain provides -- environment variables, an instance / task role, or
# shared config -- and fails fast if that yields nothing usable. Use --profile to
# select a named profile.
#
# (run_e2e.sh refreshes credentials itself because it provisions Aurora clusters
# into an account you may not be set up for yet. This harness targets
# pre-existing private infrastructure that you must already have a network path
# to, so by the time you can reach it you necessarily have credentials for it.
# Hence no credential handling here.)
#
# A read-only role is sufficient and preferred: the harness only calls describe_*
# RDS APIs, reads one Secrets Manager secret, and runs SELECTs.
#
# Network: RDS Proxy endpoints are normally private, so this generally has to run
# from inside the VPC -- an EC2 instance, an ECS task, or a laptop over VPN /
# Direct Connect with the proxy's security group allowing your egress. A 30s TLS
# handshake timeout in the harness usually means reachability, not a certificate
# problem.
#
# Usage:
#   tests/e2e/run_proxy_e2e.sh \
#       --region us-east-1 \
#       --db-instance-identifier my-proxied-instance \
#       [--no-proxy-instance my-bare-instance] \
#       [--database postgres] \
#       [--profile my-aws-profile] \
#       [--secret-arn arn:aws:secretsmanager:...]   # optional, see above \
#       [--auth-type pg_wire_secret|pg_wire_iam] \
#       [--sslmode verify-full] \
#       [--ca-bundle path|system] \
#       [--privilege-check off|warn|enforce] \
#       [--log-level INFO] \
#       [--log-file path.log]
#
# Anything after a literal `--` is passed straight through to the harness.
set -euo pipefail

usage() {
  awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"
  exit "${1:-0}"
}

# --- defaults -------------------------------------------------------------
REGION=""
DB_INSTANCE=""
NO_PROXY_INSTANCE=""
DATABASE=""
PROFILE=""
SECRET_ARN=""
AUTH_TYPE=""
SSLMODE=""
CA_BUNDLE=""
PRIVILEGE_CHECK=""
LOG_LEVEL="INFO"
LOG_FILE=""
PASSTHROUGH=()

# --- parse args -----------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --region)                  REGION="$2"; shift 2 ;;
    --db-instance-identifier)  DB_INSTANCE="$2"; shift 2 ;;
    --no-proxy-instance)       NO_PROXY_INSTANCE="$2"; shift 2 ;;
    --database)                DATABASE="$2"; shift 2 ;;
    --profile)                 PROFILE="$2"; shift 2 ;;
    --secret-arn)              SECRET_ARN="$2"; shift 2 ;;
    --auth-type)               AUTH_TYPE="$2"; shift 2 ;;
    --sslmode)                 SSLMODE="$2"; shift 2 ;;
    --ca-bundle)               CA_BUNDLE="$2"; shift 2 ;;
    --privilege-check)         PRIVILEGE_CHECK="$2"; shift 2 ;;
    --log-level)               LOG_LEVEL="$2"; shift 2 ;;
    --log-file)                LOG_FILE="$2"; shift 2 ;;
    -h|--help)                 usage 0 ;;
    --)                        shift; PASSTHROUGH+=("$@"); break ;;
    *) echo "ERROR: unknown argument: $1" >&2; usage 1 ;;
  esac
done

# --- validate -------------------------------------------------------------
missing=()
[[ -z "$REGION" ]] && missing+=("--region")
[[ -z "$DB_INSTANCE" ]] && missing+=("--db-instance-identifier")
if [[ ${#missing[@]} -gt 0 ]]; then
  echo "ERROR: missing required argument(s): ${missing[*]}" >&2
  usage 1
fi

if [[ -z "$NO_PROXY_INSTANCE" ]]; then
  echo ">> WARNING: no --no-proxy-instance given; the direct-connection fallback"
  echo ">>          will not be exercised."
fi

# Run from the package root so `uv run` and the relative test path resolve
# regardless of the caller's working directory.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

if [[ -z "$LOG_FILE" ]]; then
  LOG_FILE="$REPO_ROOT/proxy-e2e-$(date +%Y%m%d-%H%M%S).log"
fi

# --- credentials ----------------------------------------------------------
# Exported rather than passed as a flag, so boto3 inside the harness resolves it
# the same way the aws CLI preflight below does.
if [[ -n "$PROFILE" ]]; then
  export AWS_PROFILE="$PROFILE"
  echo ">> Using AWS profile: $AWS_PROFILE"
fi

# Fail fast with an actionable message rather than a boto3 traceback from inside
# the harness several seconds later.
if ! aws sts get-caller-identity --region "$REGION" >/dev/null 2>&1; then
  echo "ERROR: no usable AWS credentials for region $REGION" >&2
  echo "       (aws sts get-caller-identity failed)" >&2
  echo "       This script does not acquire credentials. Supply them through the" >&2
  echo "       standard chain: environment variables, an instance/task role, or a" >&2
  echo "       shared-config profile selected with --profile." >&2
  exit 1
fi

# --- build harness command ------------------------------------------------
cmd=(uv run --frozen python tests/e2e/proxy_e2e_test.py
     --region "$REGION"
     --db-instance-identifier "$DB_INSTANCE"
     --log-level "$LOG_LEVEL")
[[ -n "$NO_PROXY_INSTANCE" ]] && cmd+=(--no-proxy-instance "$NO_PROXY_INSTANCE")
[[ -n "$DATABASE" ]] && cmd+=(--database "$DATABASE")
[[ -n "$SECRET_ARN" ]] && cmd+=(--secret-arn "$SECRET_ARN")
[[ -n "$AUTH_TYPE" ]] && cmd+=(--auth-type "$AUTH_TYPE")
[[ -n "$SSLMODE" ]] && cmd+=(--sslmode "$SSLMODE")
[[ -n "$CA_BUNDLE" ]] && cmd+=(--ca-bundle "$CA_BUNDLE")
[[ -n "$PRIVILEGE_CHECK" ]] && cmd+=(--privilege-check "$PRIVILEGE_CHECK")
if [[ ${#PASSTHROUGH[@]} -gt 0 ]]; then
  cmd+=("${PASSTHROUGH[@]}")
fi

echo ">> proxied-instance=$DB_INSTANCE control=${NO_PROXY_INSTANCE:-<none>}"
echo ">> Running: ${cmd[*]}"
echo ">> Logging to: $LOG_FILE"

set +e
"${cmd[@]}" 2>&1 | tee "$LOG_FILE"
status=${PIPESTATUS[0]}
set -e

echo ">> proxy e2e exited with status $status (log: $LOG_FILE)"
exit "$status"
