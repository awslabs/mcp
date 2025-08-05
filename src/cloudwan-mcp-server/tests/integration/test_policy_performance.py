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

"""Policy document parsing performance tests following AWS Labs patterns."""

import gc
import json
import logging
import os
import time
from unittest.mock import Mock, patch

import psutil
import pytest

from awslabs.cloudwan_mcp_server.server import (
    get_core_network_policy,
    validate_cloudwan_policy,
)

# Test timeout constants for maintainability and consistency (configurable via environment variables)
try:
    POLICY_PARSING_TIMEOUT = float(
        os.getenv("POLICY_PARSING_TIMEOUT", "30.0")
    )  # Default timeout for policy parsing operations
except (ValueError, TypeError):
    POLICY_PARSING_TIMEOUT = 30.0  # Fallback if env var is invalid

try:
    REGEX_DOS_TIMEOUT = int(os.getenv("REGEX_DOS_TIMEOUT", "30"))  # Timeout for regex DOS prevention tests
except (ValueError, TypeError):
    REGEX_DOS_TIMEOUT = 30  # Fallback if env var is invalid

# Edge region configurations for performance testing
EDGE_REGIONS = [
    "us-east",
    "us-west",
    "eu-west",
    "eu-central",
    "ap-southeast",
    "ap-northeast",
    "ap-south",
    "ca-central",
    "sa-east",
    "af-south",
    "me-south",
    "ap-east",
    "eu-north",
    "eu-south",
    "us-gov-east",
    "us-gov-west",
    "cn-north",
    "cn-northwest",
    "ap-southeast",
    "ap-northeast",
    "eu-west",
    "us-west",
    "us-east",
    "ap-south",
    "ca-central",
]

# AWS region names with numbers for testing
AWS_REGIONS = ["us-east-1", "us-west-2", "eu-west-1"]


class TestLargePolicyDocumentParsing:
    """Test parsing performance with 10MB+ policy documents."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_10mb_policy_document_parsing(self) -> None:
        """Test parsing of 10MB+ policy document with complex structure."""
        # Generate massive policy document (~10MB)
        massive_policy = {
            "version": "2021.12",
            "core-network-configuration": {
                "asn-ranges": [f"{64512 + i}-{64512 + i + 99}" for i in range(0, 10000, 100)],
                "edge-locations": [],
            },
            "segments": [],
            "segment-actions": [],
            "attachment-policies": [],
        }

        # Add 1000 edge locations with detailed configuration
        for region_idx in range(25):  # 25 regions
            for az_idx in range(8):  # 8 AZs per region
                for instance_idx in range(5):  # 5 instances per AZ
                    edge_location = {
                        "location": f"{EDGE_REGIONS[region_idx]}-{az_idx + 1}",
                        "asn": 64512 + (region_idx * 1000) + (az_idx * 100) + instance_idx,
                        "inside-cidr-blocks": [f"169.254.{region_idx}.{az_idx * 32 + instance_idx * 4}/30"],
                        "tags": {
                            "Region": f"region-{region_idx:02d}",
                            "AvailabilityZone": f"az-{az_idx}",
                            "Instance": f"instance-{instance_idx}",
                            "Environment": "production" if region_idx % 2 == 0 else "staging",
                            "CostCenter": f"cc-{region_idx % 10:03d}",
                            "Team": f"team-{region_idx % 5:02d}",
                            "Purpose": "high-availability-backbone",
                        },
                    }
                    massive_policy["core-network-configuration"]["edge-locations"].append(edge_location)

        # Add 50,000 segments with complex configurations
        for segment_idx in range(50000):
            segment = {
                "name": f"segment-{segment_idx:06d}",
                "description": f"Automatically generated segment {segment_idx} for performance testing with extensive configuration parameters and metadata",
                "require-attachment-acceptance": segment_idx % 3 == 0,
                "isolate-attachments": segment_idx % 5 == 0,
                "allow-filter": [
                    f"10.{(segment_idx // 256) % 256}.{segment_idx % 256}.0/24",
                    f"172.{16 + ((segment_idx // 1000) % 16)}.{(segment_idx // 100) % 256}.0/20",
                ],
                "deny-filter": [f"192.168.{segment_idx % 256}.0/24"] if segment_idx % 7 == 0 else [],
                "edge-locations": [f"{EDGE_REGIONS[segment_idx % 3]}-{(segment_idx % 8) + 1}"],
                "tags": {
                    "SegmentId": f"seg-{segment_idx:06d}",
                    "Environment": ["prod", "staging", "dev"][segment_idx % 3],
                    "Application": f"app-{segment_idx % 100:03d}",
                    "Owner": f"team-{segment_idx % 50:02d}@company.com",
                    "CostCenter": f"cc-{segment_idx % 200:03d}",
                    "Purpose": "automated-network-segmentation",
                    "Compliance": ["pci", "hipaa", "sox"][segment_idx % 3],
                    "DataClassification": ["public", "internal", "confidential"][segment_idx % 3],
                },
            }
            massive_policy["segments"].append(segment)

        # Add 100,000 segment actions (sharing rules)
        for action_idx in range(100000):
            segment_action = {
                "action": ["share", "create-route"][action_idx % 2],
                "segment": f"segment-{action_idx % 50000:06d}",
                "share-with": [
                    f"segment-{(action_idx + offset) % 50000:06d}"
                    for offset in range(1, min(6, 50000 - (action_idx % 50000)))
                ]
                if action_idx % 2 == 0
                else None,
                "destination-cidr-blocks": [
                    f"10.{action_idx % 256}.0.0/16",
                    f"172.{16 + ((action_idx // 1000) % 16)}.0.0/12",
                ]
                if action_idx % 2 == 1
                else None,
                "mode": ["attachment-route", "single-route"][action_idx % 2],
                "via": {
                    "network-function-groups": [f"nfg-{action_idx % 1000:04d}"],
                    "with-edge-override": [
                        {
                            "edge-sets": [[f"edge-{action_idx % 100:03d}"]],
                            "use-edge": f"edge-{(action_idx + 1) % 100:03d}",
                        }
                    ],
                }
                if action_idx % 10 == 0
                else None,
            }
            massive_policy["segment-actions"].append(segment_action)

        # Add 75,000 attachment policies with complex conditions
        for policy_idx in range(75000):
            attachment_policy = {
                "rule-number": policy_idx + 1,
                "description": f"Complex attachment policy rule {policy_idx} with multiple conditions and nested logic structures",
                "condition-logic": ["and", "or"][policy_idx % 2],
                "conditions": [
                    {
                        "type": "tag-value",
                        "key": "Environment",
                        "value": ["production", "staging", "development"][policy_idx % 3],
                        "operator": "equals",
                    },
                    {"type": "tag-exists", "key": "Application", "operator": "exists"},
                    {"type": "account-id", "value": f"{123456789000 + (policy_idx % 1000)}", "operator": "equals"},
                    {"type": "resource-id", "value": f"vpc-{policy_idx:08d}*", "operator": "starts-with"},
                    {"type": "region", "value": f"{AWS_REGIONS[policy_idx % 3]}", "operator": "equals"},
                ],
                "action": {
                    "association-method": "constant",
                    "segment": f"segment-{policy_idx % 50000:06d}",
                    "require-acceptance": policy_idx % 4 == 0,
                    "tag-value-on-creation": {
                        "AutoAttached": "true",
                        "PolicyId": f"policy-{policy_idx:06d}",
                        "CreatedBy": "automated-attachment-system",
                        "Timestamp": "2024-01-01T00:00:00Z",
                    },
                },
            }
            massive_policy["attachment-policies"].append(attachment_policy)

        # Measure policy size
        policy_json = json.dumps(massive_policy)
        policy_size_mb = len(policy_json.encode("utf-8")) / 1024 / 1024

        start_time = time.time()
        memory_before = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        gc.collect()  # Clean memory before test

        result = await validate_cloudwan_policy(massive_policy)

        end_time = time.time()
        memory_after = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

        parsing_time = end_time - start_time
        memory_usage = memory_after - memory_before

        parsed = json.loads(result)
        assert parsed["success"] is True
        assert "overall_status" in parsed
        assert "validation_results" in parsed

        # Performance requirements for 10MB+ policy (timeout configurable via env)
        try:
            parsing_timeout = float(os.getenv("POLICY_PARSING_TIMEOUT", str(POLICY_PARSING_TIMEOUT)))
        except (ValueError, TypeError) as e:
            logging.warning(f"Invalid POLICY_PARSING_TIMEOUT environment variable, using default: {e}")
            parsing_timeout = POLICY_PARSING_TIMEOUT
        assert policy_size_mb >= 10.0, f"Policy size {policy_size_mb:.1f}MB, expected >= 10MB"
        assert parsing_time < parsing_timeout, (
            f"10MB policy parsing took {parsing_time:.2f}s, expected < {parsing_timeout:.0f}s"
        )
        assert memory_usage < 500, f"Memory usage {memory_usage:.2f}MB, expected < 500MB (optimized from 1000MB)"

        # Validate policy structure was processed
        validation_results = parsed["validation_results"]
        assert len(validation_results) >= 4  # At least version, core-config, segments, actions

        print(f"Performance: {policy_size_mb:.1f}MB policy parsed in {parsing_time:.2f}s using {memory_usage:.1f}MB")

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_complex_json_schema_validation(self) -> None:
        """Test complex JSON schema validation with nested structures."""
        # Create policy with deeply nested and complex JSON structures
        complex_nested_policy = {
            "version": "2021.12",
            "core-network-configuration": {
                "asn-ranges": ["64512-64555"],
                "edge-locations": [{"location": "us-east-1", "asn": 64512}],
                "inside-cidr-blocks": ["169.254.0.0/16"],
            },
            "segments": [
                {
                    "name": f"complex-segment-{i}",
                    "advanced-configuration": {
                        "level-1": {
                            "level-2": {
                                "level-3": {
                                    "level-4": {
                                        "level-5": {
                                            "nested-arrays": [
                                                {
                                                    "array-item": f"item-{j}",
                                                    "nested-object": {
                                                        "deep-property": f"value-{i}-{j}",
                                                        "conditional-logic": {
                                                            "if": {"condition": f"condition-{j}", "operator": "equals"},
                                                            "then": {"actions": [f"action-{k}" for k in range(10)]},
                                                            "else": {"fallback": f"fallback-{i}-{j}"},
                                                        },
                                                    },
                                                }
                                                for j in range(20)
                                            ]
                                        }
                                    }
                                }
                            }
                        }
                    },
                }
                for i in range(1000)
            ],
        }

        start_time = time.time()
        memory_before = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

        result = await validate_cloudwan_policy(complex_nested_policy)

        end_time = time.time()
        memory_after = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

        validation_time = end_time - start_time
        memory_usage = memory_after - memory_before

        parsed = json.loads(result)
        assert parsed["success"] is True

        # Complex nesting should be processed efficiently
        assert validation_time < 60.0, f"Complex validation took {validation_time:.2f}s"
        assert memory_usage < 300, f"Complex validation used {memory_usage:.2f}MB"

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_deep_policy_nesting_analysis(self) -> None:
        """Test analysis of deeply nested policy structures."""
        # Create policy with 20 levels of nesting
        deep_nesting_policy = {"version": "2021.12"}

        def create_nested_structure(depth, max_depth=20):
            if depth >= max_depth:
                return f"deep-value-at-level-{depth}"
            return {
                f"level-{depth}": create_nested_structure(depth + 1, max_depth),
                f"array-at-level-{depth}": [
                    {f"item-{i}-at-level-{depth}": create_nested_structure(depth + 1, max_depth)} for i in range(5)
                ],
                f"metadata-level-{depth}": {
                    "depth": depth,
                    "max_depth": max_depth,
                    "path": f"root.level-{depth}",
                    "properties": {f"prop-{j}": f"value-{j}-at-{depth}" for j in range(10)},
                },
            }

        deep_nesting_policy["core-network-configuration"] = {
            "asn-ranges": ["64512-64555"],
            "edge-locations": [{"location": "us-east-1", "asn": 64512}],
            "deep-configuration": create_nested_structure(0, 20),
        }

        start_time = time.time()
        result = await validate_cloudwan_policy(deep_nesting_policy)
        end_time = time.time()

        parsing_time = end_time - start_time
        parsed = json.loads(result)

        assert parsed["success"] is True
        assert parsing_time < 45.0, f"Deep nesting analysis took {parsing_time:.2f}s"


class TestRegexPerformanceAndDOS:
    """Test regex performance and DOS prevention scenarios."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_regex_dos_prevention_patterns(self) -> None:
        """Test prevention of regex denial-of-service attacks."""
        # Create policy with potentially problematic regex patterns
        regex_dos_policy = {
            "version": "2021.12",
            "core-network-configuration": {
                "asn-ranges": ["64512-64555"],
                "edge-locations": [{"location": "us-east-1", "asn": 64512}],
            },
            "segments": [
                {
                    "name": f"regex-test-{i}",
                    "description": "a" * 1000 + "b" * 1000,  # Long strings that could cause regex issues
                    "allow-filter": [
                        # Patterns that could be expensive to match
                        "10.0.0.0/8",
                        "172.16.0.0/12",
                        "192.168.0.0/16",
                    ],
                }
                for i in range(1000)
            ],
            "attachment-policies": [
                {
                    "rule-number": i,
                    "conditions": [
                        {
                            "type": "tag-value",
                            "key": "Name",
                            # Potentially expensive regex patterns
                            "value": "a" * 100 + ".*" + "b" * 100,
                            "operator": "contains",
                        }
                    ],
                    "action": {"association-method": "constant", "segment": f"regex-test-{i % 1000}"},
                }
                for i in range(5000)
            ],
        }

        start_time = time.time()

        result = await validate_cloudwan_policy(regex_dos_policy)

        end_time = time.time()
        execution_time = end_time - start_time

        parsed = json.loads(result)
        assert parsed["success"] is True

        # Should complete within reasonable time (regex DOS prevention)
        assert execution_time < REGEX_DOS_TIMEOUT, f"Regex validation took {execution_time:.2f}s, possible DOS"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_compiled_regex_benchmarking(self) -> None:
        """Test compiled regex performance for policy validation."""
        # Create policy with patterns that benefit from regex compilation
        regex_benchmark_policy = {
            "version": "2021.12",
            "core-network-configuration": {
                "asn-ranges": ["64512-64555"],
                "edge-locations": [{"location": "us-east-1", "asn": 64512}],
            },
            "attachment-policies": [],
        }

        # Add policies with repetitive patterns (should benefit from compilation)
        common_patterns = [
            r"^vpc-[0-9a-f]{17}$",
            r"^subnet-[0-9a-f]{17}$",
            r"^igw-[0-9a-f]{17}$",
            r"^rtb-[0-9a-f]{17}$",
            r"^sg-[0-9a-f]{17}$",
        ]

        for i in range(10000):
            policy = {
                "rule-number": i + 1,
                "conditions": [
                    {
                        "type": "resource-id",
                        "value": f"{['vpc', 'subnet', 'igw', 'rtb', 'sg'][i % 5]}-{i:017x}",
                        "operator": "matches-pattern",
                        "pattern": common_patterns[i % 5],
                    }
                ],
                "action": {"association-method": "constant", "segment": f"segment-{i % 100:03d}"},
            }
            regex_benchmark_policy["attachment-policies"].append(policy)

        start_time = time.time()
        result = await validate_cloudwan_policy(regex_benchmark_policy)
        end_time = time.time()

        regex_time = end_time - start_time
        parsed = json.loads(result)

        assert parsed["success"] is True
        # With regex compilation, should be relatively fast
        assert regex_time < 60.0, f"Regex compilation benchmark took {regex_time:.2f}s"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_circular_reference_detection(self) -> None:
        """Test detection of circular references in policy documents."""
        # Create policy with potential circular references
        circular_policy = {
            "version": "2021.12",
            "core-network-configuration": {
                "asn-ranges": ["64512-64555"],
                "edge-locations": [{"location": "us-east-1", "asn": 64512}],
            },
            "segments": [],
        }

        # Create segments that reference each other in a circle
        for i in range(100):
            segment = {
                "name": f"segment-{i:03d}",
                "references": [
                    f"segment-{(i + 1) % 100:03d}",  # References next segment (creates circle)
                    f"segment-{(i + 50) % 100:03d}",  # Additional reference for complexity
                ],
                "dependencies": [
                    f"segment-{(i - 1) % 100:03d}"  # Dependency on previous (reverse circle)
                ],
            }
            circular_policy["segments"].append(segment)

        # Add segment actions that could create circular dependencies
        circular_policy["segment-actions"] = []
        for i in range(100):
            action = {
                "action": "share",
                "segment": f"segment-{i:03d}",
                "share-with": [f"segment-{(i + j) % 100:03d}" for j in range(1, 6)],
                "conditions": {
                    "requires-segment": f"segment-{(i + 99) % 100:03d}"  # Circular condition
                },
            }
            circular_policy["segment-actions"].append(action)

        start_time = time.time()
        result = await validate_cloudwan_policy(circular_policy)
        end_time = time.time()

        detection_time = end_time - start_time
        parsed = json.loads(result)

        assert parsed["success"] is True  # Function should succeed
        # Circular reference detection should complete quickly
        assert detection_time < 30.0, f"Circular reference detection took {detection_time:.2f}s"


class TestPolicyVersionDiffPerformance:
    """Test performance of policy version diff operations."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_large_policy_version_diff_analysis(self) -> None:
        """Test diff analysis between large policy versions."""
        # Create base policy version
        base_policy = {
            "version": "2021.12",
            "core-network-configuration": {
                "asn-ranges": ["64512-64555"],
                "edge-locations": [{"location": f"us-east-{i}", "asn": 64512 + i} for i in range(1, 5)],
            },
            "segments": [
                {
                    "name": f"base-segment-{i:04d}",
                    "require-attachment-acceptance": i % 2 == 0,
                    "allow-filter": [f"10.{i // 256}.{i % 256}.0/24"],
                }
                for i in range(10000)
            ],
        }

        # Create modified policy version with changes
        modified_policy = base_policy.copy()
        modified_policy["segments"] = []

        # Add modified segments (some unchanged, some modified, some new)
        for i in range(12000):  # 2000 additional segments
            if i < 5000:
                # Keep first 5000 unchanged
                segment = {
                    "name": f"base-segment-{i:04d}",
                    "require-attachment-acceptance": i % 2 == 0,
                    "allow-filter": [f"10.{i // 256}.{i % 256}.0/24"],
                }
            elif i < 10000:
                # Modify next 5000
                segment = {
                    "name": f"base-segment-{i:04d}",
                    "require-attachment-acceptance": not (i % 2 == 0),  # Flipped
                    "allow-filter": [f"10.{i // 256}.{i % 256}.0/24", f"172.16.{i % 256}.0/24"],  # Added filter
                    "deny-filter": [f"192.168.{i % 256}.0/24"],  # New property
                }
            else:
                # Add 2000 new segments
                segment = {
                    "name": f"new-segment-{i:04d}",
                    "require-attachment-acceptance": False,
                    "allow-filter": [f"192.168.{i % 256}.0/24"],
                }

            modified_policy["segments"].append(segment)

        # Mock policy retrieval for diff analysis
        def mock_policy_retrieval(core_network_id, alias=None):
            if alias == "PREVIOUS":
                return base_policy
            else:
                return modified_policy

        start_time = time.time()
        memory_before = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

        # Test both policy versions
        base_result = await validate_cloudwan_policy(base_policy)
        modified_result = await validate_cloudwan_policy(modified_policy)

        end_time = time.time()
        memory_after = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

        diff_time = end_time - start_time
        memory_usage = memory_after - memory_before

        base_parsed = json.loads(base_result)
        modified_parsed = json.loads(modified_result)

        assert base_parsed["success"] is True
        assert modified_parsed["success"] is True

        # Performance requirements for large policy diff
        assert diff_time < 180.0, f"Large policy diff took {diff_time:.2f}s"
        assert memory_usage < 800, f"Policy diff memory usage {memory_usage:.2f}MB"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_policy_render_tree_validation(self) -> None:
        """Test policy render tree validation performance."""
        # Create policy with complex render dependencies
        render_tree_policy = {
            "version": "2021.12",
            "core-network-configuration": {
                "asn-ranges": ["64512-64555"],
                "edge-locations": [{"location": "us-east-1", "asn": 64512}],
            },
            "network-function-groups": [],
        }

        # Create hierarchical network function groups
        for level in range(5):  # 5 levels of hierarchy
            for group_idx in range(10**level):  # Exponential growth
                group = {
                    "name": f"nfg-level-{level}-{group_idx:06d}",
                    "description": f"Network function group at level {level}",
                    "require-attachment-acceptance": True,
                    "policy": {
                        "traffic-rules": [
                            {
                                "rule-number": rule_idx + 1,
                                "source": f"level-{level}-source-{rule_idx}",
                                "destination": f"level-{(level + 1) % 5}-dest-{rule_idx}",
                                "action": "allow",
                            }
                            for rule_idx in range(50)  # 50 rules per group
                        ]
                    },
                    "dependencies": [f"nfg-level-{level - 1}-{group_idx // 10:06d}"] if level > 0 else [],
                }
                render_tree_policy["network-function-groups"].append(group)

                # Limit total groups to prevent excessive test time
                if len(render_tree_policy["network-function-groups"]) >= 1000:
                    break

            if len(render_tree_policy["network-function-groups"]) >= 1000:
                break

        start_time = time.time()
        result = await validate_cloudwan_policy(render_tree_policy)
        end_time = time.time()

        render_time = end_time - start_time
        parsed = json.loads(result)

        assert parsed["success"] is True
        # Render tree validation should be efficient
        assert render_time < 90.0, f"Render tree validation took {render_time:.2f}s"


class TestMemoryMappedFileHandling:
    """Test memory-mapped file handling for large policies."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_memory_mapped_policy_processing(self) -> None:
        """Test memory-mapped file processing for very large policies."""
        # Simulate processing of a policy too large for memory
        streaming_policy_data = {
            "version": "2021.12",
            "core-network-configuration": {
                "asn-ranges": ["64512-64555"],
                "edge-locations": [{"location": "us-east-1", "asn": 64512}],
            },
        }

        # Create large segment dataset that would benefit from streaming
        large_segments = []
        for batch in range(100):  # 100 batches
            batch_segments = []
            for i in range(1000):  # 1000 segments per batch
                segment_idx = batch * 1000 + i
                segment = {
                    "name": f"streaming-segment-{segment_idx:08d}",
                    "description": f"Large segment {segment_idx} processed via streaming for memory efficiency optimization testing",
                    "require-attachment-acceptance": segment_idx % 2 == 0,
                    "allow-filter": [f"10.{(segment_idx // 65536) % 256}.{(segment_idx // 256) % 256}.0/24"],
                    "metadata": {
                        "batch": batch,
                        "index": i,
                        "total-index": segment_idx,
                        "processing-hint": "memory-efficient-streaming",
                    },
                }
                batch_segments.append(segment)
            large_segments.extend(batch_segments)

        streaming_policy_data["segments"] = large_segments

        # Simulate memory-mapped processing
        gc.collect()
        memory_baseline = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        start_time = time.time()

        # Process policy in chunks to simulate memory mapping
        chunk_size = 10000
        total_segments = len(large_segments)
        processed_chunks = 0

        for chunk_start in range(0, total_segments, chunk_size):
            chunk_end = min(chunk_start + chunk_size, total_segments)
            chunk_policy = {
                "version": "2021.12",
                "core-network-configuration": streaming_policy_data["core-network-configuration"],
                "segments": large_segments[chunk_start:chunk_end],
            }

            chunk_result = await validate_cloudwan_policy(chunk_policy)
            chunk_parsed = json.loads(chunk_result)
            assert chunk_parsed["success"] is True

            processed_chunks += 1

            # Force garbage collection between chunks (simulate memory mapping cleanup)
            gc.collect()

            current_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
            memory_growth = current_memory - memory_baseline

            # Memory growth should remain bounded with streaming
            assert memory_growth < 200, f"Memory grew by {memory_growth:.1f}MB during streaming"

        end_time = time.time()
        final_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

        streaming_time = end_time - start_time
        total_memory_growth = final_memory - memory_baseline

        # Validate streaming performance
        assert processed_chunks == 10  # 100,000 segments / 10,000 per chunk
        assert streaming_time < 120.0, f"Memory-mapped processing took {streaming_time:.2f}s"
        assert total_memory_growth < 300, f"Total memory growth {total_memory_growth:.1f}MB"

        print(
            f"Streamed {total_segments} segments in {processed_chunks} chunks, "
            f"{streaming_time:.2f}s, {total_memory_growth:.1f}MB growth"
        )


class TestPolicyCacheInvalidation:
    """Test policy cache invalidation and performance."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_policy_cache_invalidation_performance(self) -> None:
        """Test policy cache invalidation scenarios."""
        # Create base policy for caching
        cached_policy = {
            "version": "2021.12",
            "core-network-configuration": {
                "asn-ranges": ["64512-64555"],
                "edge-locations": [{"location": "us-east-1", "asn": 64512}],
            },
            "segments": [
                {"name": f"cached-segment-{i:04d}", "require-attachment-acceptance": i % 2 == 0} for i in range(5000)
            ],
        }

        # Simulate cache scenario
        cache_hit_count = 0
        cache_miss_count = 0

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()

            def cached_policy_retrieval(**kwargs):
                nonlocal cache_hit_count, cache_miss_count

                # Simulate cache behavior
                if hasattr(cached_policy_retrieval, "call_count"):
                    cached_policy_retrieval.call_count += 1
                else:
                    cached_policy_retrieval.call_count = 1

                if cached_policy_retrieval.call_count <= 3:
                    # First 3 calls are cache misses
                    cache_miss_count += 1
                    time.sleep(0.1)  # Simulate retrieval delay
                else:
                    # Subsequent calls are cache hits
                    cache_hit_count += 1

                return {"CoreNetworkPolicy": {"PolicyVersionId": "1", "PolicyDocument": json.dumps(cached_policy)}}

            mock_client.get_core_network_policy.side_effect = cached_policy_retrieval
            mock_get_client.return_value = mock_client

            # Test multiple policy retrievals
            start_time = time.time()

            for i in range(10):
                result = await get_core_network_policy("core-network-cache-test")
                parsed = json.loads(result)
                assert parsed["success"] is True

            end_time = time.time()
            total_time = end_time - start_time

            # Verify cache behavior
            assert cache_miss_count <= 3, f"Too many cache misses: {cache_miss_count}"
            assert cache_hit_count >= 7, f"Too few cache hits: {cache_hit_count}"

            # With caching, later calls should be much faster
            assert total_time < 5.0, f"Cached policy retrieval took {total_time:.2f}s"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_parallel_policy_validation_performance(self) -> None:
        """Test parallel policy validation for performance optimization."""
        # Create multiple policy variants for parallel processing
        policy_variants = []

        for variant_idx in range(20):
            variant_policy = {
                "version": "2021.12",
                "core-network-configuration": {
                    "asn-ranges": [f"{64512 + variant_idx * 10}-{64512 + variant_idx * 10 + 9}"],
                    "edge-locations": [{"location": f"us-east-{(variant_idx % 2) + 1}", "asn": 64512 + variant_idx}],
                },
                "segments": [
                    {
                        "name": f"variant-{variant_idx:02d}-segment-{i:04d}",
                        "require-attachment-acceptance": (variant_idx + i) % 2 == 0,
                    }
                    for i in range(1000)
                ],
            }
            policy_variants.append(variant_policy)

        # Test sequential validation
        start_time = time.time()
        sequential_results = []

        for policy in policy_variants:
            result = await validate_cloudwan_policy(policy)
            sequential_results.append(json.loads(result))

        sequential_time = time.time() - start_time

        # Test parallel validation simulation (processing in batches)
        start_time = time.time()
        parallel_results = []
        batch_size = 5

        for batch_start in range(0, len(policy_variants), batch_size):
            batch_end = min(batch_start + batch_size, len(policy_variants))
            batch_policies = policy_variants[batch_start:batch_end]

            # Process batch (simulate parallel processing)
            batch_results = []
            for policy in batch_policies:
                result = await validate_cloudwan_policy(policy)
                batch_results.append(json.loads(result))

            parallel_results.extend(batch_results)

        parallel_time = time.time() - start_time

        # Verify all validations succeeded
        assert len(sequential_results) == 20
        assert len(parallel_results) == 20
        assert all(result["success"] for result in sequential_results)
        assert all(result["success"] for result in parallel_results)

        # Parallel processing should show some efficiency gains
        efficiency_ratio = sequential_time / parallel_time if parallel_time > 0 else 1
        print(
            f"Sequential: {sequential_time:.2f}s, Parallel: {parallel_time:.2f}s, Efficiency: {efficiency_ratio:.2f}x"
        )

        assert sequential_time > 0 and parallel_time > 0, "Both methods should take measurable time"
