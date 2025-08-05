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

"""Memory usage under load validation tests following AWS Labs patterns."""

import gc
import json
import os
import sys
import time
import tracemalloc
import weakref
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import psutil
import pytest
from botocore.exceptions import ClientError

from awslabs.cloudwan_mcp_server.server import (
    analyze_tgw_routes,
    discover_vpcs,
    get_core_network_policy,
    get_global_networks,
    list_core_networks,
    validate_ip_cidr,
)


class TestMemoryUsageMonitoring:
    """Test 99th percentile memory usage patterns."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_99th_percentile_memory_usage(self) -> None:
        """Test memory usage stays within 99th percentile limits under load."""
        memory_samples = []
        peak_memory = 0
        baseline_memory = 0

        def memory_intensive_mock(service, region=None):
            mock_client = Mock()

            def memory_consuming_operation(**kwargs):
                # Simulate memory-intensive AWS response processing
                large_dataset = []

                # Create large mock dataset (simulating AWS API response)
                for i in range(10000):  # 10K items
                    item = {
                        "CoreNetworkId": f"core-network-{i:08d}",
                        "GlobalNetworkId": f"global-network-{i:08d}",
                        "State": "AVAILABLE",
                        "Description": f"Memory test core network {i} with extensive metadata and configuration parameters",
                        "CreatedAt": datetime.now(UTC),
                        "Tags": [
                            {"Key": f"Tag{j}", "Value": f"Value{j}-{i}"}
                            for j in range(20)  # 20 tags per item
                        ],
                        "Metadata": {
                            "ExtensiveConfiguration": {
                                f"Config{k}": f"ConfigValue{k}-{i}-{k * i}"
                                for k in range(50)  # 50 config items per item
                            }
                        },
                    }
                    large_dataset.append(item)

                return {"CoreNetworks": large_dataset}

            mock_client.list_core_networks.side_effect = memory_consuming_operation
            return mock_client

        # Start memory monitoring
        tracemalloc.start()
        gc.collect()
        process = psutil.Process(os.getpid())
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client", side_effect=memory_intensive_mock):
            # Perform multiple operations and monitor memory
            operations_count = 100

            for operation_num in range(operations_count):
                # Execute memory-intensive operation
                result = await list_core_networks()
                parsed = json.loads(result)
                assert parsed["success"] is True

                # Sample memory usage
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_samples.append(current_memory - baseline_memory)
                peak_memory = max(peak_memory, current_memory - baseline_memory)

                # Force garbage collection periodically
                if operation_num % 10 == 0:
                    gc.collect()

                # Check for memory leaks (growth beyond reasonable bounds)
                if len(memory_samples) > 10:
                    recent_avg = sum(memory_samples[-10:]) / 10
                    if recent_avg > self.MEMORY_LEAK_THRESHOLD_MB:  # 1GB growth is concerning
                        pytest.fail(f"Potential memory leak: {recent_avg:.1f}MB average growth")

        # Calculate memory statistics
        memory_samples.sort()
        percentile_95 = memory_samples[int(0.95 * len(memory_samples))]
        percentile_99 = memory_samples[int(0.99 * len(memory_samples))]
        average_memory = sum(memory_samples) / len(memory_samples)

        # Stop memory monitoring
        current_traces, peak_traces = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Memory usage assertions
        assert percentile_99 < 500, f"99th percentile memory usage {percentile_99:.1f}MB too high"
        assert peak_memory < 800, f"Peak memory usage {peak_memory:.1f}MB too high"
        assert average_memory < 200, f"Average memory usage {average_memory:.1f}MB too high"

        # Verify memory is properly released
        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_retained = final_memory - baseline_memory
        assert memory_retained < 50, f"Too much memory retained after cleanup: {memory_retained:.1f}MB"

        print(
            f"Memory stats: Avg {average_memory:.1f}MB, 95th {percentile_95:.1f}MB, "
            f"99th {percentile_99:.1f}MB, Peak {peak_memory:.1f}MB"
        )

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self) -> None:
        """Test systematic memory leak detection across operations."""
        memory_baselines = {}
        leak_candidates = []
        operations_per_test = 50

        # Test operations that could have memory leaks
        test_operations = [
            ("list_core_networks", lambda: list_core_networks()),
            ("get_global_networks", lambda: get_global_networks()),
            ("discover_vpcs", lambda: discover_vpcs()),
            ("validate_ip_cidr", lambda: validate_ip_cidr("validate_ip", ip="10.0.0.1")),
        ]

        def create_mock_for_operation(op_name):
            def mock_factory(service, region=None):
                mock_client = Mock()

                # Different mock responses for different operations
                if "core_networks" in op_name:
                    mock_client.list_core_networks.return_value = {
                        "CoreNetworks": [
                            {
                                "CoreNetworkId": f"core-network-leak-test-{i}",
                                "State": "AVAILABLE",
                                "LargeData": "x" * 1000,  # 1KB per item
                            }
                            for i in range(100)
                        ]
                    }
                elif "global_networks" in op_name:
                    mock_client.describe_global_networks.return_value = {
                        "GlobalNetworks": [
                            {
                                "GlobalNetworkId": f"global-network-leak-test-{i}",
                                "State": "AVAILABLE",
                                "LargeData": "y" * 1000,
                            }
                            for i in range(100)
                        ]
                    }
                elif "vpcs" in op_name:
                    mock_client.describe_vpcs.return_value = {
                        "Vpcs": [
                            {"VpcId": f"vpc-leak-test-{i}", "State": "available", "LargeData": "z" * 1000}
                            for i in range(100)
                        ]
                    }

                return mock_client

            return mock_factory

        process = psutil.Process(os.getpid())

        for op_name, op_func in test_operations:
            with patch(
                "awslabs.cloudwan_mcp_server.server.get_aws_client", side_effect=create_mock_for_operation(op_name)
            ):
                gc.collect()
                initial_memory = process.memory_info().rss / 1024 / 1024
                memory_baselines[op_name] = initial_memory

                memory_progression = []

                # Execute operation multiple times
                for iteration in range(operations_per_test):
                    result = await op_func()
                    parsed = json.loads(result)
                    assert parsed["success"] is True

                    # Sample memory every 10 iterations
                    if iteration % 10 == 0:
                        current_memory = process.memory_info().rss / 1024 / 1024
                        memory_growth = current_memory - initial_memory
                        memory_progression.append(memory_growth)

                gc.collect()
                final_memory = process.memory_info().rss / 1024 / 1024
                total_growth = final_memory - initial_memory

                # Analyze memory progression for leaks
                if len(memory_progression) >= 3:
                    # Check for consistent upward trend (potential leak)
                    growth_trend = all(
                        memory_progression[i] >= memory_progression[i - 1] for i in range(1, len(memory_progression))
                    )

                    if growth_trend and total_growth > 20:  # 20MB growth threshold
                        leak_candidates.append(
                            {
                                "operation": op_name,
                                "total_growth": total_growth,
                                "progression": memory_progression,
                                "final_memory": final_memory,
                            }
                        )

        # Assert no significant memory leaks detected
        assert len(leak_candidates) == 0, (
            f"Memory leaks detected in operations: {[lc['operation'] for lc in leak_candidates]}"
        )

        # Verify memory returns to reasonable baseline
        final_system_memory = process.memory_info().rss / 1024 / 1024
        initial_system_memory = min(memory_baselines.values())
        system_growth = final_system_memory - initial_system_memory

        assert system_growth < 100, f"Overall system memory growth {system_growth:.1f}MB too high"

        print(
            f"Leak detection complete: {len(test_operations)} operations tested, {len(leak_candidates)} potential leaks"
        )

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_garbage_collection_pressure(self) -> None:
        """Test system behavior under garbage collection pressure."""
        gc.get_stats()
        gc_threshold_before = gc.get_threshold()

        # Configure aggressive GC for testing
        gc.set_threshold(100, 10, 10)  # More frequent GC

        try:
            gc_cycles = []
            memory_during_gc = []

            def gc_callback(phase, info) -> None:
                """Callback to monitor GC cycles."""
                if phase == "start":
                    process = psutil.Process(os.getpid())
                    current_memory = process.memory_info().rss / 1024 / 1024
                    gc_cycles.append(
                        {
                            "generation": info["generation"],
                            "collected": 0,
                            "memory_at_start": current_memory,
                            "start_time": time.time(),
                        }
                    )
                elif phase == "stop":
                    if gc_cycles:
                        gc_cycles[-1]["collected"] = info["collected"]
                        gc_cycles[-1]["end_time"] = time.time()
                        gc_cycles[-1]["duration"] = gc_cycles[-1]["end_time"] - gc_cycles[-1]["start_time"]

            # Enable GC debugging (if available)
            original_callbacks = gc.callbacks[:]
            gc.callbacks.append(gc_callback)

            def memory_pressure_mock(service, region=None):
                mock_client = Mock()

                def pressure_operation(**kwargs):
                    # Create many temporary objects to trigger GC
                    temporary_objects = []

                    for i in range(1000):  # Create 1000 temporary objects
                        temp_obj = {
                            "id": i,
                            "data": [f"item-{j}" for j in range(100)],  # 100 items each
                            "metadata": {f"key-{k}": f"value-{k}" for k in range(50)},
                            "large_string": "x" * 1000,  # 1KB string
                        }
                        temporary_objects.append(temp_obj)

                        # Periodically clear some objects to create garbage
                        if i % 100 == 0:
                            temporary_objects = temporary_objects[-50:]  # Keep only last 50

                    # Return response (temporary objects become garbage)
                    return {
                        "CoreNetworks": [
                            {"CoreNetworkId": f"core-network-gc-{i}", "State": "AVAILABLE"} for i in range(10)
                        ]
                    }

                mock_client.list_core_networks.side_effect = pressure_operation
                return mock_client

            with patch("awslabs.cloudwan_mcp_server.server.get_aws_client", side_effect=memory_pressure_mock):
                process = psutil.Process(os.getpid())
                start_memory = process.memory_info().rss / 1024 / 1024

                # Execute operations that create GC pressure
                operations_count = 20

                for i in range(operations_count):
                    result = await list_core_networks()
                    parsed = json.loads(result)
                    assert parsed["success"] is True

                    # Force some GC activity
                    if i % 5 == 0:
                        collected = gc.collect()
                        current_memory = process.memory_info().rss / 1024 / 1024
                        memory_during_gc.append(
                            {"iteration": i, "collected_objects": collected, "memory_mb": current_memory - start_memory}
                        )

                end_memory = process.memory_info().rss / 1024 / 1024
                memory_growth = end_memory - start_memory

            # Analyze GC behavior
            if gc_cycles:
                total_gc_time = sum(cycle.get("duration", 0) for cycle in gc_cycles)
                avg_gc_time = total_gc_time / len(gc_cycles) if gc_cycles else 0
                total_collected = sum(cycle.get("collected", 0) for cycle in gc_cycles)

                # GC should be working effectively
                assert avg_gc_time < 0.1, f"Average GC time {avg_gc_time:.4f}s too high"
                assert total_collected > 0, "GC should have collected objects"
                assert len(gc_cycles) > 0, "GC should have been triggered"

                print(
                    f"GC stats: {len(gc_cycles)} cycles, {total_collected} objects collected, "
                    f"{total_gc_time:.3f}s total GC time"
                )

            # Memory should be managed effectively under GC pressure
            assert memory_growth < 100, f"Memory growth under GC pressure: {memory_growth:.1f}MB"

        finally:
            # Restore original GC settings
            gc.set_threshold(*gc_threshold_before)
            gc.callbacks[:] = original_callbacks

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_large_object_heap_analysis(self) -> None:
        """Test large object heap analysis and management."""
        large_objects = []
        object_sizes = []
        heap_snapshots = []

        def large_object_mock(service, region=None):
            mock_client = Mock()

            def large_response_operation(**kwargs):
                # Create response with large objects
                large_policy = {
                    "version": "2021.12",
                    "core-network-configuration": {
                        "asn-ranges": ["64512-64555"],
                        "edge-locations": [{"location": "us-east-1"}],
                    },
                    "massive-segments": [
                        {
                            "name": f"segment-{i:06d}",
                            "description": "x" * 10000,  # 10KB description
                            "large-configuration": {
                                f"config-{j}": "y" * 1000  # 1KB per config * 100 configs = 100KB
                                for j in range(100)
                            },
                        }
                        for i in range(100)  # 100 segments * ~110KB = ~11MB per response
                    ],
                }

                return {"CoreNetworkPolicy": {"PolicyVersionId": "1", "PolicyDocument": json.dumps(large_policy)}}

            mock_client.get_core_network_policy.side_effect = large_response_operation
            return mock_client

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client", side_effect=large_object_mock):
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024

            # Create and process large objects
            for iteration in range(10):
                result = await get_core_network_policy("core-network-large-object-test")
                parsed = json.loads(result)
                assert parsed["success"] is True

                # Extract large object for analysis
                policy_doc = json.loads(parsed["policy_document"])
                large_objects.append(policy_doc)

                # Calculate object size
                obj_size = sys.getsizeof(json.dumps(policy_doc).encode("utf-8")) / 1024 / 1024  # MB
                object_sizes.append(obj_size)

                # Take heap snapshot
                current_memory = process.memory_info().rss / 1024 / 1024
                heap_snapshots.append(
                    {
                        "iteration": iteration,
                        "memory_mb": current_memory - initial_memory,
                        "object_count": len(large_objects),
                        "largest_object_mb": obj_size,
                    }
                )

                # Periodically clear old objects to test garbage collection
                if iteration % 3 == 0 and len(large_objects) > 3:
                    # Keep only recent objects
                    large_objects = large_objects[-3:]
                    gc.collect()

            # Final memory measurement
            gc.collect()
            final_memory = process.memory_info().rss / 1024 / 1024
            total_memory_growth = final_memory - initial_memory

            # Analyze object sizes
            avg_object_size = sum(object_sizes) / len(object_sizes)
            max_object_size = max(object_sizes)
            total_object_size = sum(object_sizes)

            # Large object heap assertions
            assert avg_object_size < 15, f"Average object size {avg_object_size:.1f}MB too large"
            assert max_object_size < 20, f"Largest object {max_object_size:.1f}MB too large"
            assert total_memory_growth < 200, f"Total memory growth {total_memory_growth:.1f}MB too high"

            # Verify memory management efficiency
            if heap_snapshots:
                memory_efficiency = total_object_size / total_memory_growth if total_memory_growth > 0 else 0
                assert memory_efficiency > 0.3, f"Memory efficiency {memory_efficiency:.2f} too low"

            print(
                f"Large objects: Avg {avg_object_size:.1f}MB, Max {max_object_size:.1f}MB, "
                f"Total growth {total_memory_growth:.1f}MB"
            )


class TestCircularReferenceDetection:
    """Test circular reference detection and cleanup."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_circular_reference_cleanup(self) -> None:
        """Test detection and cleanup of circular references."""
        circular_objects = []
        weakref_objects = []

        def circular_reference_mock(service, region=None):
            mock_client = Mock()

            def circular_response_operation(**kwargs):
                # Create objects with circular references
                parent_obj = {"id": len(circular_objects), "type": "parent", "children": []}

                # Create child objects that reference parent
                for i in range(10):
                    child_obj = {
                        "id": i,
                        "type": "child",
                        "parent": parent_obj,  # Circular reference
                        "data": "x" * 1000,  # 1KB data
                    }
                    parent_obj["children"].append(child_obj)

                # Create weak reference for monitoring
                weak_parent = weakref.ref(parent_obj)
                weakref_objects.append(weak_parent)
                circular_objects.append(parent_obj)

                return {
                    "CoreNetworks": [
                        {
                            "CoreNetworkId": f"core-network-circular-{parent_obj['id']}",
                            "State": "AVAILABLE",
                            "CircularData": parent_obj,
                        }
                    ]
                }

            mock_client.list_core_networks.side_effect = circular_response_operation
            return mock_client

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client", side_effect=circular_reference_mock):
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024

            # Create objects with circular references
            operations_count = 20

            for i in range(operations_count):
                result = await list_core_networks()
                parsed = json.loads(result)
                assert parsed["success"] is True

                # Periodically force cleanup
                if i % 5 == 0:
                    # Clear references and force GC
                    circular_objects.clear()
                    gc.collect()

                    # Check if weak references are cleaned up
                    alive_objects = sum(1 for weak_ref in weakref_objects if weak_ref() is not None)
                    dead_objects = len(weakref_objects) - alive_objects

                    print(f"Iteration {i}: {alive_objects} alive objects, {dead_objects} cleaned up")

            # Final cleanup test
            circular_objects.clear()
            gc.collect()

            final_memory = process.memory_info().rss / 1024 / 1024
            memory_growth = final_memory - initial_memory

            # Check weak references after final cleanup
            final_alive_objects = sum(1 for weak_ref in weakref_objects if weak_ref() is not None)
            cleanup_ratio = (len(weakref_objects) - final_alive_objects) / len(weakref_objects)

            # Circular reference cleanup assertions
            assert memory_growth < 50, f"Memory growth with circular references: {memory_growth:.1f}MB"
            assert cleanup_ratio > 0.8, f"Cleanup ratio {cleanup_ratio:.2f} too low"
            assert final_alive_objects <= operations_count * 0.1, f"Too many objects still alive: {final_alive_objects}"

            print(f"Circular reference cleanup: {cleanup_ratio:.2f} cleanup ratio, {memory_growth:.1f}MB memory growth")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_weakref_usage_patterns(self) -> None:
        """Test weak reference usage patterns for memory management."""
        strong_references = {}
        weak_references = {}
        callback_invocations = []

        def weakref_callback(weak_ref) -> None:
            """Callback when object is about to be garbage collected."""
            callback_invocations.append({"timestamp": time.time(), "weak_ref_id": id(weak_ref)})

        def weakref_aware_mock(service, region=None):
            mock_client = Mock()

            def weakref_operation(**kwargs):
                # Create object that will be managed with weak references
                large_data_object = {
                    "id": len(strong_references),
                    "large_data": "x" * 100000,  # 100KB object
                    "metadata": {"created_at": time.time(), "size_kb": 100},
                }

                # Store strong reference temporarily
                obj_id = f"obj-{len(strong_references):04d}"
                strong_references[obj_id] = large_data_object

                # Create weak reference with callback
                weak_ref = weakref.ref(large_data_object, weakref_callback)
                weak_references[obj_id] = weak_ref

                return {
                    "Routes": [
                        {
                            "DestinationCidrBlock": f"10.{len(strong_references)}.0.0/16",
                            "State": "active",
                            "LargeDataRef": obj_id,
                        }
                    ]
                }

            mock_client.search_transit_gateway_routes.side_effect = weakref_operation
            return mock_client

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client", side_effect=weakref_aware_mock):
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024

            # Create objects and manage with weak references
            for i in range(50):
                result = await analyze_tgw_routes(f"tgw-rtb-weakref-{i:03d}")
                parsed = json.loads(result)
                assert parsed["success"] is True

                # Periodically clear strong references (keep weak refs)
                if i % 10 == 0 and i > 0:
                    # Clear half of strong references
                    keys_to_remove = list(strong_references.keys())[: len(strong_references) // 2]
                    for key in keys_to_remove:
                        del strong_references[key]

                    # Force garbage collection
                    gc.collect()

                    # Verify weak references are cleaned up
                    alive_weak_refs = sum(1 for weak_ref in weak_references.values() if weak_ref() is not None)

                    print(f"Iteration {i}: {len(strong_references)} strong refs, {alive_weak_refs} alive weak refs")

            # Final cleanup
            strong_references.clear()
            gc.collect()

            final_memory = process.memory_info().rss / 1024 / 1024
            memory_growth = final_memory - initial_memory

            # Count final weak reference states
            final_alive_weak_refs = sum(1 for weak_ref in weak_references.values() if weak_ref() is not None)

            total_weak_refs = len(weak_references)
            cleanup_effectiveness = (total_weak_refs - final_alive_weak_refs) / total_weak_refs

            # Weak reference management assertions
            assert memory_growth < 150, f"Memory growth with weak refs: {memory_growth:.1f}MB"
            assert cleanup_effectiveness > 0.9, f"Weak ref cleanup effectiveness {cleanup_effectiveness:.2f}"
            assert len(callback_invocations) > 0, "Weak reference callbacks should be invoked"
            assert final_alive_weak_refs <= 5, f"Too many weak refs still alive: {final_alive_weak_refs}"

            print(
                f"Weak references: {cleanup_effectiveness:.2f} cleanup effectiveness, "
                f"{len(callback_invocations)} callbacks invoked"
            )


class TestMemoryFragmentation:
    """Test memory fragmentation patterns and mitigation."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_memory_fragmentation_patterns(self) -> None:
        """Test memory fragmentation with varied allocation patterns."""
        allocation_patterns = []
        fragmentation_metrics = []

        def fragmentation_mock(service, region=None):
            mock_client = Mock()

            def fragmented_allocation_operation(**kwargs):
                # Create varied allocation sizes to induce fragmentation
                allocations = []

                # Mix of small, medium, and large allocations
                allocation_sizes = [
                    ("small", 100),  # 100 bytes
                    ("medium", 10000),  # 10KB
                    ("large", 1000000),  # 1MB
                ]

                for alloc_type, size in allocation_sizes:
                    for i in range(10):  # 10 of each size
                        data = {
                            "type": alloc_type,
                            "id": i,
                            "data": "x" * size,
                            "metadata": {"allocation_time": time.time(), "size_bytes": size},
                        }
                        allocations.append(data)

                # Randomly delete some allocations to create holes
                import random

                seeded_random = random.Random(42)
                seeded_random.shuffle(allocations)
                allocations = allocations[: len(allocations) // 2]  # Keep only half

                allocation_patterns.append(allocations)

                return {
                    "GlobalNetworks": [
                        {
                            "GlobalNetworkId": f"global-network-frag-{len(allocation_patterns)}",
                            "State": "AVAILABLE",
                            "Allocations": len(allocations),
                        }
                    ]
                }

            mock_client.describe_global_networks.side_effect = fragmented_allocation_operation
            return mock_client

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client", side_effect=fragmentation_mock):
            process = psutil.Process(os.getpid())

            # Perform operations with fragmentation patterns
            for cycle in range(20):
                initial_memory = process.memory_info().rss / 1024 / 1024

                result = await get_global_networks()
                parsed = json.loads(result)
                assert parsed["success"] is True

                post_alloc_memory = process.memory_info().rss / 1024 / 1024
                memory_growth = post_alloc_memory - initial_memory

                # Force cleanup to observe fragmentation
                if cycle % 5 == 0:
                    allocation_patterns = allocation_patterns[-2:]  # Keep only recent patterns
                    gc.collect()

                    post_gc_memory = process.memory_info().rss / 1024 / 1024
                    memory_released = post_alloc_memory - post_gc_memory

                    fragmentation_ratio = memory_released / memory_growth if memory_growth > 0 else 0
                    fragmentation_metrics.append(
                        {
                            "cycle": cycle,
                            "growth_mb": memory_growth,
                            "released_mb": memory_released,
                            "fragmentation_ratio": fragmentation_ratio,
                        }
                    )

            # Analyze fragmentation
            if fragmentation_metrics:
                avg_fragmentation = sum(m["fragmentation_ratio"] for m in fragmentation_metrics) / len(
                    fragmentation_metrics
                )
                max_growth = max(m["growth_mb"] for m in fragmentation_metrics)
                total_released = sum(m["released_mb"] for m in fragmentation_metrics)

                # Fragmentation should be manageable
                assert avg_fragmentation > 0.3, f"Average fragmentation recovery {avg_fragmentation:.2f} too low"
                assert max_growth < 100, f"Max memory growth per cycle {max_growth:.1f}MB too high"
                assert total_released > 0, "Should be able to release fragmented memory"

                print(
                    f"Fragmentation: Avg recovery {avg_fragmentation:.2f}, "
                    f"Max growth {max_growth:.1f}MB, Total released {total_released:.1f}MB"
                )

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_rss_vs_vsz_monitoring(self) -> None:
        """Test RSS vs VSZ memory monitoring patterns."""
        memory_metrics = []

        def memory_monitoring_mock(service, region=None):
            mock_client = Mock()

            def monitored_operation(**kwargs):
                # Create data structure that affects RSS differently than VSZ
                large_sparse_data = {}

                # Create sparse data structure (affects VSZ more than RSS initially)
                for i in range(0, 100000, 1000):  # Sparse keys
                    large_sparse_data[i] = {
                        "data": "y" * 1000,  # 1KB actual data
                        "index": i,
                        "metadata": {"sparse": True},
                    }

                return {
                    "Vpcs": [
                        {
                            "VpcId": f"vpc-memory-monitor-{len(memory_metrics)}",
                            "State": "available",
                            "SparseData": len(large_sparse_data),
                        }
                    ]
                }

            mock_client.describe_vpcs.side_effect = monitored_operation
            return mock_client

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client", side_effect=memory_monitoring_mock):
            process = psutil.Process(os.getpid())

            for iteration in range(15):
                memory_info = process.memory_info()

                # Capture memory metrics before operation
                pre_rss = memory_info.rss / 1024 / 1024  # MB
                pre_vms = memory_info.vms / 1024 / 1024  # MB

                result = await discover_vpcs()
                parsed = json.loads(result)
                assert parsed["success"] is True

                # Capture memory metrics after operation
                post_memory_info = process.memory_info()
                post_rss = post_memory_info.rss / 1024 / 1024
                post_vms = post_memory_info.vms / 1024 / 1024

                rss_growth = post_rss - pre_rss
                vms_growth = post_vms - pre_vms
                rss_vms_ratio = post_rss / post_vms if post_vms > 0 else 0

                memory_metrics.append(
                    {
                        "iteration": iteration,
                        "rss_mb": post_rss,
                        "vms_mb": post_vms,
                        "rss_growth": rss_growth,
                        "vms_growth": vms_growth,
                        "rss_vms_ratio": rss_vms_ratio,
                    }
                )

                # Periodic cleanup
                if iteration % 5 == 0:
                    gc.collect()

            # Analyze RSS vs VSZ patterns
            avg_rss_growth = sum(m["rss_growth"] for m in memory_metrics) / len(memory_metrics)
            sum(m["vms_growth"] for m in memory_metrics) / len(memory_metrics)
            avg_ratio = sum(m["rss_vms_ratio"] for m in memory_metrics) / len(memory_metrics)

            final_rss = memory_metrics[-1]["rss_mb"] - memory_metrics[0]["rss_mb"]
            final_vms = memory_metrics[-1]["vms_mb"] - memory_metrics[0]["vms_mb"]

            # Memory monitoring assertions
            assert avg_rss_growth < 20, f"Average RSS growth {avg_rss_growth:.1f}MB per iteration too high"
            assert avg_ratio > 0.5, f"RSS/VMS ratio {avg_ratio:.2f} indicates potential memory issues"
            assert final_rss < 200, f"Final RSS growth {final_rss:.1f}MB too high"
            assert final_vms < 400, f"Final VMS growth {final_vms:.1f}MB too high"

            print(
                f"Memory monitoring: RSS growth {final_rss:.1f}MB, VMS growth {final_vms:.1f}MB, Ratio {avg_ratio:.2f}"
            )

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_swap_usage_patterns(self) -> None:
        """Test swap usage patterns under memory pressure."""
        swap_usage_samples = []
        memory_pressure_events = []

        def memory_pressure_mock(service, region=None):
            mock_client = Mock()

            def pressure_inducing_operation(**kwargs):
                # Create significant memory pressure
                pressure_data = []

                # Allocate large chunks of data
                for chunk in range(100):  # 100 chunks
                    chunk_data = {
                        "chunk_id": chunk,
                        "large_array": [f"data-{i}" * 100 for i in range(1000)],  # ~100KB per chunk
                        "metadata": {"chunk_size": "100KB", "pressure_level": "high"},
                    }
                    pressure_data.append(chunk_data)

                # Simulate memory-intensive processing
                processed_data = []
                for chunk in pressure_data:
                    processed_chunk = {
                        **chunk,
                        "processed": True,
                        "processing_data": chunk["large_array"] * 2,  # Double the data
                    }
                    processed_data.append(processed_chunk)

                return {
                    "CoreNetworks": [
                        {
                            "CoreNetworkId": f"core-network-pressure-{len(memory_pressure_events)}",
                            "State": "AVAILABLE",
                            "DataProcessed": len(processed_data),
                        }
                    ]
                }

            mock_client.list_core_networks.side_effect = pressure_inducing_operation
            return mock_client

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client", side_effect=memory_pressure_mock):
            # Monitor swap usage if available
            initial_swap = psutil.swap_memory()
            process = psutil.Process(os.getpid())

            for iteration in range(10):
                pre_memory = process.memory_info().rss / 1024 / 1024
                pre_swap = psutil.swap_memory()

                # Execute memory-intensive operation
                start_time = time.time()
                result = await list_core_networks()
                end_time = time.time()

                parsed = json.loads(result)
                assert parsed["success"] is True

                post_memory = process.memory_info().rss / 1024 / 1024
                post_swap = psutil.swap_memory()

                # Record memory pressure event
                memory_growth = post_memory - pre_memory
                swap_change = post_swap.used - pre_swap.used
                execution_time = end_time - start_time

                pressure_event = {
                    "iteration": iteration,
                    "memory_growth_mb": memory_growth,
                    "swap_change_bytes": swap_change,
                    "execution_time_s": execution_time,
                    "swap_pressure": swap_change > 0,
                }
                memory_pressure_events.append(pressure_event)

                swap_usage_samples.append(
                    {
                        "iteration": iteration,
                        "swap_used_mb": post_swap.used / 1024 / 1024,
                        "swap_percent": post_swap.percent,
                    }
                )

                # Cleanup to prevent excessive swap usage
                if iteration % 3 == 0:
                    gc.collect()

            # Analyze swap usage patterns
            max_swap_usage = max(s["swap_used_mb"] for s in swap_usage_samples)
            avg_execution_time = sum(e["execution_time_s"] for e in memory_pressure_events) / len(
                memory_pressure_events
            )
            swap_pressure_events = sum(1 for e in memory_pressure_events if e["swap_pressure"])

            # Swap usage should be reasonable
            assert max_swap_usage < 1000, f"Max swap usage {max_swap_usage:.1f}MB too high"
            assert avg_execution_time < 5.0, (
                f"Average execution time {avg_execution_time:.2f}s indicates swap thrashing"
            )
            assert swap_pressure_events <= len(memory_pressure_events) * 0.5, (
                f"Too many swap pressure events: {swap_pressure_events}"
            )

            final_swap = psutil.swap_memory()
            swap_growth = (final_swap.used - initial_swap.used) / 1024 / 1024  # MB

            assert swap_growth < 500, f"Total swap growth {swap_growth:.1f}MB too high"

            print(
                f"Swap usage: Max {max_swap_usage:.1f}MB, Growth {swap_growth:.1f}MB, "
                f"Pressure events {swap_pressure_events}"
            )


class TestMemoryBoundThrottling:
    """Test memory-bound throttling mechanisms."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_memory_bound_throttling_mechanism(self) -> None:
        """Test throttling mechanism based on memory usage bounds."""
        memory_threshold_mb = 200  # 200MB threshold
        throttle_events = []
        successful_operations = 0
        throttled_operations = 0

        def memory_aware_mock(service, region=None):
            nonlocal successful_operations, throttled_operations
            mock_client = Mock()

            def memory_bound_operation(**kwargs):
                nonlocal successful_operations, throttled_operations

                # Check current memory usage
                process = psutil.Process(os.getpid())
                current_memory = process.memory_info().rss / 1024 / 1024

                # Implement memory-based throttling
                if current_memory > memory_threshold_mb:
                    throttled_operations += 1
                    throttle_events.append(
                        {
                            "timestamp": time.time(),
                            "memory_mb": current_memory,
                            "threshold_mb": memory_threshold_mb,
                            "operation": "throttled",
                        }
                    )

                    # Simulate throttling delay
                    time.sleep(0.1)

                    # Force garbage collection before retry
                    gc.collect()

                    # Check memory again after GC
                    post_gc_memory = process.memory_info().rss / 1024 / 1024
                    if post_gc_memory > memory_threshold_mb:
                        raise ClientError(
                            {
                                "Error": {
                                    "Code": "MemoryPressureThrottling",
                                    "Message": f"Operation throttled due to memory pressure: {post_gc_memory:.1f}MB > {memory_threshold_mb}MB",
                                }
                            },
                            "MemoryBoundOperation",
                        )

                successful_operations += 1

                # Create memory-intensive response
                large_data = {
                    "operation_id": successful_operations,
                    "large_payload": "x" * 1000000,  # 1MB payload
                    "metadata": {"memory_at_execution": current_memory, "throttle_threshold": memory_threshold_mb},
                }

                return {
                    "CoreNetworkPolicy": {
                        "PolicyVersionId": str(successful_operations),
                        "PolicyDocument": json.dumps(large_data),
                    }
                }

            mock_client.get_core_network_policy.side_effect = memory_bound_operation
            return mock_client

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client", side_effect=memory_aware_mock):
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024

            # Execute operations that may trigger memory throttling
            operations_attempted = 50
            successful_results = []
            failed_results = []

            for i in range(operations_attempted):
                try:
                    result = await get_core_network_policy(f"core-network-throttle-{i:03d}")
                    parsed = json.loads(result)

                    if parsed["success"]:
                        successful_results.append(parsed)
                    else:
                        failed_results.append(parsed)

                except Exception as e:
                    failed_results.append({"error": str(e), "operation_num": i})

                # Periodic memory cleanup
                if i % 10 == 0:
                    gc.collect()

            final_memory = process.memory_info().rss / 1024 / 1024
            total_memory_growth = final_memory - initial_memory

            # Memory throttling analysis
            total_operations = successful_operations + throttled_operations
            throttled_operations / total_operations if total_operations > 0 else 0
            success_ratio = len(successful_results) / operations_attempted

            # Throttling mechanism assertions
            assert success_ratio > 0.6, f"Success ratio {success_ratio:.2f} too low under memory pressure"
            assert total_memory_growth < 300, f"Memory growth {total_memory_growth:.1f}MB despite throttling"
            assert len(throttle_events) > 0 or total_memory_growth < memory_threshold_mb, (
                "Throttling should activate under memory pressure"
            )

            if throttle_events:
                avg_throttle_memory = sum(e["memory_mb"] for e in throttle_events) / len(throttle_events)
                assert avg_throttle_memory >= memory_threshold_mb, (
                    f"Throttling activated below threshold: {avg_throttle_memory:.1f}MB"
                )

            print(
                f"Memory throttling: {successful_operations} successful, {throttled_operations} throttled, "
                f"{len(throttle_events)} throttle events, {total_memory_growth:.1f}MB growth"
            )
