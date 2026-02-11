#!/usr/bin/env bash
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
set -euo pipefail

# loader.sh - Install and run Aurora DSQL Loader to load data from S3
#
# Usage: ./loader.sh [CLUSTER_ID] --source-uri S3_URI --table TABLE [OPTIONS]
#
# Examples:
#   ./loader.sh --source-uri s3://my-bucket/data.parquet --table analytics_data
#   ./loader.sh abc123def456 --source-uri s3://bucket/data.csv --table my_table --region us-west-2
#   ./loader.sh --source-uri s3://bucket/data.csv --table my_table --if-not-exists
#   ./loader.sh --source-uri s3://bucket/data.csv --table my_table --resume-job-id abc-123-def-456
#   ./loader.sh --install-only

CLUSTER_ID="${CLUSTER:-}"
REGION="${REGION:-${AWS_REGION:-us-east-1}}"
SOURCE_URI=""
TABLE=""
RESUME_JOB_ID=""
MANIFEST_DIR=""
IF_NOT_EXISTS=false
DRY_RUN=false
INSTALL_ONLY=false
LOADER_VERSION="latest"

# Installation directory
INSTALL_DIR="${HOME}/.local/bin"
LOADER_BIN="${INSTALL_DIR}/aurora-dsql-loader"

show_help() {
  cat << EOF
Usage: $0 [CLUSTER_ID] --source-uri S3_URI --table TABLE [OPTIONS]

Install and run Aurora DSQL Loader to load data from S3 into Aurora DSQL.

Arguments:
  CLUSTER_ID              Cluster identifier (default: \$CLUSTER env var)

Required Options:
  --source-uri URI        Source data URI (S3 path or local file)
  --table TABLE           Target table name

Options:
  --region REGION         AWS region (default: \$REGION or \$AWS_REGION or us-east-1)
  --resume-job-id ID      Resume a previously interrupted load job
  --manifest-dir DIR      Directory for load manifest storage
  --if-not-exists         Auto-create table if it doesn't exist
  --dry-run               Validate without loading data
  --install-only          Only install the loader, don't run it
  --version VERSION       Loader version to install (default: latest)
  -h, --help              Show this help message

Environment Variables:
  CLUSTER                 Default cluster identifier
  REGION                  Default AWS region
  AWS_REGION              Fallback AWS region

Examples:
  # Basic load from S3
  ./loader.sh --source-uri s3://my-bucket/data.parquet --table analytics_data

  # Load with auto-table creation
  ./loader.sh --source-uri s3://bucket/data.csv --table my_table --if-not-exists

  # Resume a failed load (requires manifest-dir from original load)
  ./loader.sh --source-uri s3://bucket/data.csv --table my_table --resume-job-id abc-123 --manifest-dir /path/to/manifest

  # Dry run to validate
  ./loader.sh --source-uri s3://bucket/data.csv --table my_table --dry-run

For more information, see: https://github.com/aws-samples/aurora-dsql-loader
EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --source-uri)
      SOURCE_URI="$2"
      shift 2
      ;;
    --table)
      TABLE="$2"
      shift 2
      ;;
    --region)
      REGION="$2"
      shift 2
      ;;
    --resume-job-id)
      RESUME_JOB_ID="$2"
      shift 2
      ;;
    --manifest-dir)
      MANIFEST_DIR="$2"
      shift 2
      ;;
    --if-not-exists)
      IF_NOT_EXISTS=true
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --install-only)
      INSTALL_ONLY=true
      shift
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    -*)
      echo "Unknown option: $1"
      echo "Use --help for usage information."
      exit 1
      ;;
    *)
      CLUSTER_ID="$1"
      shift
      ;;
  esac
done

# Detect OS and architecture for GitHub release asset naming
detect_platform() {
  local os arch
  os="$(uname -s)"
  arch="$(uname -m)"

  case "$os" in
    Linux)
      os="unknown-linux-gnu"
      ;;
    Darwin)
      os="apple-darwin"
      ;;
    *)
      echo "Error: Unsupported operating system: $os" >&2
      exit 1
      ;;
  esac

  case "$arch" in
    x86_64|amd64)
      arch="x86_64"
      ;;
    aarch64|arm64)
      arch="aarch64"
      ;;
    *)
      echo "Error: Unsupported architecture: $arch" >&2
      exit 1
      ;;
  esac

  echo "${arch}-${os}"
}

# Install the loader if not present
install_loader() {
  if [[ -x "$LOADER_BIN" ]]; then
    echo "Aurora DSQL Loader already installed at $LOADER_BIN" >&2
    "$LOADER_BIN" --help 2>/dev/null || true
    return 0
  fi

  echo "Installing Aurora DSQL Loader..." >&2

  # Create install directory
  mkdir -p "$INSTALL_DIR"

  local platform release_url download_url
  platform="$(detect_platform)"

  # Get the download URL from GitHub releases
  if [[ "$LOADER_VERSION" == "latest" ]]; then
    release_url="https://api.github.com/repos/aws-samples/aurora-dsql-loader/releases/latest"
  else
    release_url="https://api.github.com/repos/aws-samples/aurora-dsql-loader/releases/tags/${LOADER_VERSION}"
  fi

  echo "Fetching release information from GitHub..." >&2

  # Extract the download URL for the appropriate platform
  download_url=$(curl -sL "$release_url" | grep -o "https://[^\"]*aurora-dsql-loader-${platform}[^\"]*" | head -1)

  if [[ -z "$download_url" ]]; then
    echo "Error: Could not find download URL for platform: $platform" >&2
    echo "You may need to build from source. See: https://github.com/aws-samples/aurora-dsql-loader" >&2
    exit 1
  fi

  echo "Downloading from: $download_url" >&2

  # Download and install
  local temp_file
  temp_file=$(mktemp)
  trap "rm -f '$temp_file'" EXIT

  if ! curl -sL "$download_url" -o "$temp_file"; then
    echo "Error: Failed to download loader" >&2
    exit 1
  fi

  # Check if it's a tar.gz or direct binary
  if file "$temp_file" | grep -q "gzip"; then
    tar -xzf "$temp_file" -C "$INSTALL_DIR"
    # Find and rename the binary if needed
    if [[ ! -f "$LOADER_BIN" ]]; then
      local extracted_bin
      extracted_bin=$(find "$INSTALL_DIR" -name "aurora-dsql-loader*" -type f -executable 2>/dev/null | head -1)
      if [[ -n "$extracted_bin" && "$extracted_bin" != "$LOADER_BIN" ]]; then
        mv "$extracted_bin" "$LOADER_BIN"
      fi
    fi
  else
    mv "$temp_file" "$LOADER_BIN"
    trap - EXIT
  fi

  chmod +x "$LOADER_BIN"

  echo "Aurora DSQL Loader installed successfully at $LOADER_BIN" >&2
  "$LOADER_BIN" --version 2>/dev/null || true

  # Check if install dir is in PATH
  if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo "" >&2
    echo "Note: $INSTALL_DIR is not in your PATH." >&2
    echo "Add it with: export PATH=\"\$PATH:$INSTALL_DIR\"" >&2
  fi
}

# Main execution
main() {
  # Always ensure loader is installed
  install_loader

  if [[ "$INSTALL_ONLY" == "true" ]]; then
    exit 0
  fi

  # Validate required parameters for load operation
  if [[ -z "$SOURCE_URI" ]]; then
    echo "Error: --source-uri is required" >&2
    echo "Use --help for usage information." >&2
    exit 1
  fi

  if [[ -z "$TABLE" ]]; then
    echo "Error: --table is required" >&2
    echo "Use --help for usage information." >&2
    exit 1
  fi

  if [[ -z "$CLUSTER_ID" ]]; then
    echo "Error: CLUSTER_ID is required. Set \$CLUSTER env var or pass as argument." >&2
    echo "" >&2
    echo "Usage: $0 CLUSTER_ID --source-uri URI --table TABLE [options]" >&2
    echo "   or: export CLUSTER=abc123 && $0 --source-uri URI --table TABLE [options]" >&2
    exit 1
  fi

  # Build endpoint
  local endpoint="${CLUSTER_ID}.dsql.${REGION}.on.aws"

  echo "Loading data into Aurora DSQL..." >&2
  echo "  Endpoint:   $endpoint" >&2
  echo "  Source:     $SOURCE_URI" >&2
  echo "  Table:      $TABLE" >&2
  [[ -n "$RESUME_JOB_ID" ]] && echo "  Resume Job: $RESUME_JOB_ID" >&2
  [[ -n "$MANIFEST_DIR" ]] && echo "  Manifest:   $MANIFEST_DIR" >&2
  [[ "$IF_NOT_EXISTS" == "true" ]] && echo "  Auto-create table if not exists" >&2
  [[ "$DRY_RUN" == "true" ]] && echo "  DRY RUN MODE" >&2
  echo "" >&2

  # Build the command
  local cmd=("$LOADER_BIN" "load")
  cmd+=("--endpoint" "$endpoint")
  cmd+=("--source-uri" "$SOURCE_URI")
  cmd+=("--table" "$TABLE")

  if [[ -n "$RESUME_JOB_ID" ]]; then
    cmd+=("--resume-job-id" "$RESUME_JOB_ID")
  fi

  if [[ -n "$MANIFEST_DIR" ]]; then
    cmd+=("--manifest-dir" "$MANIFEST_DIR")
  fi

  if [[ "$IF_NOT_EXISTS" == "true" ]]; then
    cmd+=("--if-not-exists")
  fi

  if [[ "$DRY_RUN" == "true" ]]; then
    cmd+=("--dry-run")
  fi

  # Execute the loader
  "${cmd[@]}"
}

main
