#!/bin/bash -eu
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

# OSS-Fuzz build script for AWS MCP Servers
# This script compiles fuzz targets with coverage instrumentation
# and copies them to the $OUT directory for OSS-Fuzz execution.
#
# Environment variables set by OSS-Fuzz:
#   $SRC - Source code directory
#   $OUT - Output directory for fuzz targets
#   $WORK - Working directory for build artifacts
#   $LIB_FUZZING_ENGINE - Path to the fuzzing engine library

set -o errexit
set -o nounset
set -o pipefail

# Navigate to the fuzzing directory
cd "$SRC/mcp/fuzzing"

# Configure sanitizer environment variables
export ASAN_OPTIONS="detect_leaks=0:symbolize=1:detect_stack_use_after_return=1"
export UBSAN_OPTIONS="print_stacktrace=1:halt_on_error=1"

# Function to compile a fuzz target
compile_fuzz_target() {
    local target_path="$1"
    local target_name
    target_name=$(basename "$target_path" .py)

    echo "Compiling fuzz target: $target_name"

    # Compile the fuzz target with coverage instrumentation
    # Using the OSS-Fuzz Python compilation approach
    compile_python_fuzzer "$target_path"

    # Copy the compiled target to $OUT
    cp "$target_path" "$OUT/$target_name"
    chmod +x "$OUT/$target_name"
}

# Function to package seed corpus
package_corpus() {
    local target_name="$1"
    local corpus_dir="$SRC/mcp/fuzzing/corpus/$target_name"

    if [ -d "$corpus_dir" ]; then
        echo "Packaging corpus for: $target_name"
        zip -j "$OUT/${target_name}_seed_corpus.zip" "$corpus_dir"/* 2>/dev/null || true
    fi
}

# Function to copy dictionary
copy_dictionary() {
    local target_name="$1"
    local dict_name="$2"
    local dict_path="$SRC/mcp/fuzzing/dictionaries/$dict_name"

    if [ -f "$dict_path" ]; then
        echo "Copying dictionary for: $target_name"
        cp "$dict_path" "$OUT/$target_name.dict"
    fi
}

# Compile all fuzz targets in the targets directory
echo "=== Building AWS MCP Servers Fuzz Targets ==="

# Find and compile all fuzz target files
for target_dir in "$SRC/mcp/fuzzing/targets"/*/; do
    if [ -d "$target_dir" ]; then
        target_category=$(basename "$target_dir")
        echo "Processing target category: $target_category"

        for target_file in "$target_dir"fuzz_*.py; do
            if [ -f "$target_file" ]; then
                target_name=$(basename "$target_file" .py)

                # Compile the fuzz target
                compile_fuzz_target "$target_file"

                # Package the seed corpus if it exists
                package_corpus "$target_category"

                # Copy dictionary based on target category
                case "$target_category" in
                    postgres|mysql)
                        copy_dictionary "$target_name" "sql.dict"
                        ;;
                    openapi)
                        copy_dictionary "$target_name" "openapi.dict"
                        ;;
                    dynamodb)
                        copy_dictionary "$target_name" "json.dict"
                        ;;
                    neptune)
                        copy_dictionary "$target_name" "gremlin.dict"
                        copy_dictionary "$target_name" "sparql.dict"
                        ;;
                    aws_api)
                        copy_dictionary "$target_name" "aws_cli.dict"
                        ;;
                    core)
                        copy_dictionary "$target_name" "yaml.dict"
                        copy_dictionary "$target_name" "toml.dict"
                        ;;
                esac
            fi
        done
    fi
done

# Copy the harness base module for runtime imports
cp "$SRC/mcp/fuzzing/harness_base.py" "$OUT/" 2>/dev/null || true
cp "$SRC/mcp/fuzzing/classifier.py" "$OUT/" 2>/dev/null || true

echo "=== Build Complete ==="
echo "Fuzz targets built and copied to: $OUT"
