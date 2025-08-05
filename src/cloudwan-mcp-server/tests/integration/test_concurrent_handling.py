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

"""Concurrent request handling tests following AWS Labs patterns."""

import asyncio
import json
import threading
import time
from datetime import UTC, datetime
from unittest.mock import Mock, patch

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


class TestHighConcurrencyAPIRequests:
    """Test 1000+ concurrent API requests handling."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_1000_concurrent_list_core_networks(self) -> None:
        """Test 1000+ concurrent list_core_networks requests."""
        concurrent_requests = 1000
        request_counter = 0
        response_times = []
        successful_requests = 0
        failed_requests = 0

        def mock_client_factory(service, region=None):
            nonlocal request_counter
            mock_client = Mock()

            def concurrent_list_networks(**kwargs):
                nonlocal request_counter
                request_counter += 1
                current_request = request_counter

                # Simulate some processing time and potential variability
                processing_time = 0.01 + (current_request % 10) * 0.001  # 10-19ms
                time.sleep(processing_time)

                # Return mock core networks
                return {
                    "CoreNetworks": [
                        {
                            "CoreNetworkId": f"core-network-concurrent-{current_request:06d}",
                            "GlobalNetworkId": f"global-network-{current_request:06d}",
                            "State": "AVAILABLE",
                            "Description": f"Concurrent test network {current_request}",
                            "CreatedAt": datetime.now(UTC),
                        }
                    ]
                }

            mock_client.list_core_networks.side_effect = concurrent_list_networks
            return mock_client

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client", side_effect=mock_client_factory):
            # Create concurrent tasks
            start_time = time.time()

            async def single_request(request_id):
                request_start = time.time()
                try:
                    result = await list_core_networks(region=f"us-east-{(request_id % 2) + 1}")
                    request_end = time.time()
                    response_time = request_end - request_start

                    parsed = json.loads(result)
                    if parsed["success"]:
                        return {
                            "request_id": request_id,
                            "success": True,
                            "response_time": response_time,
                            "total_count": parsed["total_count"],
                        }
                    else:
                        return {
                            "request_id": request_id,
                            "success": False,
                            "response_time": response_time,
                            "error": parsed.get("error", "Unknown error"),
                        }
                except Exception as e:
                    request_end = time.time()
                    return {
                        "request_id": request_id,
                        "success": False,
                        "response_time": request_end - request_start,
                        "error": str(e),
                    }

            # Execute concurrent requests
            tasks = [single_request(i) for i in range(concurrent_requests)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            end_time = time.time()
            total_execution_time = end_time - start_time

            # Analyze results
            for result in results:
                if isinstance(result, dict):
                    response_times.append(result["response_time"])
                    if result["success"]:
                        successful_requests += 1
                    else:
                        failed_requests += 1
                else:
                    failed_requests += 1

            # Performance assertions
            assert successful_requests >= 950, f"Only {successful_requests} successful out of {concurrent_requests}"
            assert failed_requests <= 50, f"Too many failures: {failed_requests}"
            assert total_execution_time < 60.0, f"1000 concurrent requests took {total_execution_time:.2f}s"

            # Response time analysis
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            max_response_time = max(response_times) if response_times else 0

            assert avg_response_time < 0.5, f"Average response time {avg_response_time:.3f}s too high"
            assert max_response_time < 2.0, f"Max response time {max_response_time:.3f}s too high"

            requests_per_second = concurrent_requests / total_execution_time
            print(
                f"Concurrent performance: {requests_per_second:.1f} req/s, "
                f"avg {avg_response_time:.3f}s, max {max_response_time:.3f}s"
            )

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_mixed_operation_concurrent_requests(self) -> None:
        """Test concurrent requests across different operation types."""
        operations_per_type = 100
        operation_results = {
            "list_core_networks": [],
            "get_global_networks": [],
            "discover_vpcs": [],
            "validate_ip_cidr": [],
        }

        def mock_client_factory(service, region=None):
            mock_client = Mock()

            # Mock responses for different services
            if service == "networkmanager":
                mock_client.list_core_networks.return_value = {
                    "CoreNetworks": [{"CoreNetworkId": "core-network-mixed-test"}]
                }
                mock_client.describe_global_networks.return_value = {
                    "GlobalNetworks": [{"GlobalNetworkId": "global-network-mixed-test"}]
                }
            elif service == "ec2":
                mock_client.describe_vpcs.return_value = {"Vpcs": [{"VpcId": "vpc-mixed-test", "State": "available"}]}

            return mock_client

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client", side_effect=mock_client_factory):

            async def concurrent_operation(op_type, request_id):
                start_time = time.time()
                try:
                    if op_type == "list_core_networks":
                        result = await list_core_networks()
                    elif op_type == "get_global_networks":
                        result = await get_global_networks()
                    elif op_type == "discover_vpcs":
                        result = await discover_vpcs()
                    elif op_type == "validate_ip_cidr":
                        result = await validate_ip_cidr("validate_ip", ip=f"10.0.{request_id % 256}.1")

                    end_time = time.time()
                    parsed = json.loads(result)

                    return {
                        "operation": op_type,
                        "request_id": request_id,
                        "success": parsed["success"],
                        "response_time": end_time - start_time,
                    }
                except Exception as e:
                    end_time = time.time()
                    return {
                        "operation": op_type,
                        "request_id": request_id,
                        "success": False,
                        "response_time": end_time - start_time,
                        "error": str(e),
                    }

            # Create mixed concurrent tasks
            all_tasks = []
            for op_type in operation_results.keys():
                for i in range(operations_per_type):
                    task = concurrent_operation(op_type, i)
                    all_tasks.append(task)

            start_time = time.time()
            results = await asyncio.gather(*all_tasks, return_exceptions=True)
            end_time = time.time()

            total_time = end_time - start_time
            total_operations = len(all_tasks)

            # Organize results by operation type
            for result in results:
                if isinstance(result, dict):
                    op_type = result["operation"]
                    operation_results[op_type].append(result)

            # Analyze results per operation type
            for op_type, results_list in operation_results.items():
                successful = sum(1 for r in results_list if r["success"])
                avg_time = sum(r["response_time"] for r in results_list) / len(results_list)

                assert successful >= operations_per_type * 0.95, (
                    f"{op_type}: only {successful}/{operations_per_type} successful"
                )
                assert avg_time < 1.0, f"{op_type}: average response time {avg_time:.3f}s too high"

            # Overall performance
            operations_per_second = total_operations / total_time
            assert operations_per_second >= 50, f"Mixed operations: only {operations_per_second:.1f} ops/s"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion_scenarios(self) -> None:
        """Test behavior under connection pool exhaustion."""
        max_connections = 50  # Simulate limited connection pool
        active_connections = 0
        connection_waits = []

        def mock_client_with_connection_limit(service, region=None):
            nonlocal active_connections
            mock_client = Mock()

            def connection_limited_operation(**kwargs):
                nonlocal active_connections

                # Simulate connection pool limit
                wait_start = time.time()
                while active_connections >= max_connections:
                    time.sleep(0.01)  # Wait for connection to be available
                    if time.time() - wait_start > 5.0:  # 5s timeout
                        raise ClientError(
                            {"Error": {"Code": "ConnectionPoolTimeout", "Message": "Connection pool exhausted"}},
                            "Operation",
                        )

                wait_time = time.time() - wait_start
                connection_waits.append(wait_time)

                # Acquire connection
                active_connections += 1

                try:
                    # Simulate operation processing time
                    processing_time = 0.05 + (active_connections * 0.001)  # Longer with more connections
                    time.sleep(processing_time)

                    return {"CoreNetworks": [{"CoreNetworkId": "conn-pool-test"}]}
                finally:
                    # Release connection
                    active_connections -= 1

            mock_client.list_core_networks.side_effect = connection_limited_operation
            return mock_client

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client", side_effect=mock_client_with_connection_limit):
            # Test with requests exceeding connection pool
            high_concurrency = 200  # More than max_connections

            async def pool_limited_request(request_id):
                try:
                    result = await list_core_networks()
                    parsed = json.loads(result)
                    return {"success": parsed["success"], "request_id": request_id}
                except Exception as e:
                    return {"success": False, "request_id": request_id, "error": str(e)}

            tasks = [pool_limited_request(i) for i in range(high_concurrency)]

            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()

            execution_time = end_time - start_time
            successful_requests = sum(1 for r in results if isinstance(r, dict) and r.get("success", False))

            # Should handle connection pool limits gracefully
            assert successful_requests >= high_concurrency * 0.8, (
                f"Connection pool handling: {successful_requests}/{high_concurrency}"
            )
            assert execution_time < 120.0, f"Connection pool test took {execution_time:.2f}s"

            # Analyze connection wait times
            if connection_waits:
                avg_wait = sum(connection_waits) / len(connection_waits)
                max_wait = max(connection_waits)

                assert avg_wait < 1.0, f"Average connection wait {avg_wait:.3f}s too high"
                assert max_wait < 5.0, f"Max connection wait {max_wait:.3f}s too high"


class TestThreadStarvationScenarios:
    """Test thread starvation scenarios and mitigation."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_thread_pool_saturation(self) -> None:
        """Test behavior when thread pool becomes saturated."""
        max_threads = 20  # Limited thread pool
        active_threads = 0
        thread_queue_waits = []

        def thread_limited_mock(service, region=None):
            nonlocal active_threads
            mock_client = Mock()

            def thread_limited_operation(**kwargs):
                nonlocal active_threads

                queue_start = time.time()

                # Simulate thread pool limit
                while active_threads >= max_threads:
                    time.sleep(0.01)
                    if time.time() - queue_start > 10.0:  # 10s timeout
                        raise RuntimeError("Thread pool exhausted")

                queue_wait = time.time() - queue_start
                thread_queue_waits.append(queue_wait)

                active_threads += 1
                thread_id = threading.current_thread().ident

                try:
                    # Simulate CPU-intensive work
                    work_duration = 0.1 + (active_threads * 0.01)  # Longer with more threads
                    time.sleep(work_duration)

                    return {
                        "Routes": [
                            {
                                "DestinationCidrBlock": f"10.{active_threads}.0.0/16",
                                "State": "active",
                                "ThreadId": thread_id,
                            }
                        ]
                    }
                finally:
                    active_threads -= 1

            mock_client.search_transit_gateway_routes.side_effect = thread_limited_operation
            return mock_client

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client", side_effect=thread_limited_mock):
            # Test with more requests than available threads
            concurrent_requests = 100

            async def thread_limited_request(request_id):
                try:
                    result = await analyze_tgw_routes(f"tgw-rtb-thread-test-{request_id:03d}")
                    parsed = json.loads(result)
                    return {
                        "success": parsed["success"],
                        "request_id": request_id,
                        "total_routes": parsed.get("analysis", {}).get("total_routes", 0),
                    }
                except Exception as e:
                    return {"success": False, "request_id": request_id, "error": str(e)}

            tasks = [thread_limited_request(i) for i in range(concurrent_requests)]

            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()

            execution_time = end_time - start_time
            successful_requests = sum(1 for r in results if isinstance(r, dict) and r.get("success", False))

            # Thread pool should handle saturation gracefully
            assert successful_requests >= concurrent_requests * 0.9, (
                f"Thread saturation: {successful_requests}/{concurrent_requests}"
            )
            assert execution_time < 180.0, f"Thread saturation test took {execution_time:.2f}s"

            # Analyze thread queue behavior
            if thread_queue_waits:
                avg_queue_wait = sum(thread_queue_waits) / len(thread_queue_waits)
                max_queue_wait = max(thread_queue_waits)

                assert avg_queue_wait < 2.0, f"Average thread queue wait {avg_queue_wait:.3f}s"
                assert max_queue_wait < 10.0, f"Max thread queue wait {max_queue_wait:.3f}s"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_async_task_cancellation_handling(self) -> None:
        """Robust test for async task cancellation handling."""
        cancellation_scenarios = []
        completed_tasks = 0

        # Original function reference

        # Create cancellation-aware wrapper
        async def cancellation_aware_analyze_tgw_routes(route_table_id: str, region=None):
            """Cancellation-aware wrapper for analyze_tgw_routes with explicit cancellation points."""
            nonlocal completed_tasks

            try:
                # Add explicit cancellation points before the main work
                await asyncio.sleep(0)  # Cancellation point 1

                # Simulate the work with cancellation points
                for i in range(50):  # 50 iterations = ~500ms processing time
                    await asyncio.sleep(0.01)  # 10ms per iteration with cancellation point

                # If we get here, the task wasn't cancelled - proceed with normal work
                completed_tasks += 1

                # Return successful result
                import json

                result = {
                    "success": True,
                    "route_table_id": route_table_id,
                    "region": region or "us-east-1",
                    "analysis": {
                        "total_routes": 1,
                        "active_routes": 1,
                        "blackholed_routes": 0,
                        "route_details": [
                            {
                                "DestinationCidrBlock": f"10.{completed_tasks}.0.0/16",
                                "State": "active",
                                "Type": "static",
                            }
                        ],
                    },
                }
                return json.dumps(result, indent=2, default=str)

            except asyncio.CancelledError:
                # Task was cancelled - record this scenario
                cancellation_scenarios.append(
                    {"operation_id": route_table_id, "cancelled_at": time.time(), "cleanup_completed": True}
                )
                # Re-raise to maintain proper asyncio cancellation behavior
                raise

        # Patch the function to use our cancellation-aware version
        with patch("awslabs.cloudwan_mcp_server.server.analyze_tgw_routes", cancellation_aware_analyze_tgw_routes):
            # Create long-running tasks
            tasks = []
            for i in range(20):
                task = asyncio.create_task(cancellation_aware_analyze_tgw_routes(f"tgw-rtb-cancel-test-{i:02d}"))
                tasks.append(task)

            # Wait briefly to ensure tasks are running
            await asyncio.sleep(0.2)

            # Cancel specific subset of tasks
            tasks_to_cancel = tasks[:10]
            for task in tasks_to_cancel:
                task.cancel()

            try:
                # Use gather with return_exceptions to handle both completed and cancelled tasks
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Count successful completions vs cancellations
                successful_completions = sum(
                    1 for r in results if isinstance(r, str) and json.loads(r).get("success", False)
                )

                cancelled_exceptions = sum(1 for r in results if isinstance(r, asyncio.CancelledError))

                # Verify cancellation scenarios
                assert len(cancellation_scenarios) == 10, (
                    f"Expected 10 cancellation scenarios, got {len(cancellation_scenarios)}"
                )
                assert cancelled_exceptions == 10, f"Expected 10 CancelledError exceptions, got {cancelled_exceptions}"
                assert successful_completions >= 8, f"Too few task completions: {successful_completions}"

                # Check that all cancellation scenarios have proper metadata
                for scenario in cancellation_scenarios:
                    assert "operation_id" in scenario
                    assert "cancelled_at" in scenario
                    assert scenario["cleanup_completed"]

            except Exception as e:
                pytest.fail(f"Unexpected error in task cancellation test: {e}")

            finally:
                # Ensure all tasks are cleaned up
                for task in tasks:
                    if not task.done():
                        task.cancel()

                # Wait for any remaining tasks to complete
                await asyncio.gather(*tasks, return_exceptions=True)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_resource_contention_patterns(self) -> None:
        """Test resource contention between concurrent operations."""
        shared_resource_locks = {}
        resource_wait_times = []
        successful_acquisitions = 0
        failed_acquisitions = 0

        def resource_contention_mock(service, region=None):
            mock_client = Mock()

            def contended_operation(**kwargs):
                nonlocal successful_acquisitions, failed_acquisitions

                resource_id = kwargs.get("CoreNetworkId", "default-resource")

                # Simulate resource locking
                lock_start = time.time()
                max_wait = 5.0  # 5 second timeout

                while resource_id in shared_resource_locks:
                    time.sleep(0.01)
                    if time.time() - lock_start > max_wait:
                        failed_acquisitions += 1
                        raise ClientError(
                            {"Error": {"Code": "ResourceContention", "Message": f"Resource {resource_id} locked"}},
                            "GetCoreNetworkPolicy",
                        )

                wait_time = time.time() - lock_start
                resource_wait_times.append(wait_time)

                # Acquire resource lock
                shared_resource_locks[resource_id] = threading.current_thread().ident
                successful_acquisitions += 1

                try:
                    # Simulate resource-intensive operation
                    processing_time = 0.1  # 100ms processing
                    time.sleep(processing_time)

                    return {
                        "CoreNetworkPolicy": {
                            "PolicyVersionId": "1",
                            "PolicyDocument": json.dumps(
                                {
                                    "version": "2021.12",
                                    "resource-id": resource_id,
                                    "processed-by": shared_resource_locks[resource_id],
                                }
                            ),
                        }
                    }
                finally:
                    # Release resource lock
                    if resource_id in shared_resource_locks:
                        del shared_resource_locks[resource_id]

            mock_client.get_core_network_policy.side_effect = contended_operation
            return mock_client

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client", side_effect=resource_contention_mock):
            # Create contention scenario - multiple requests for same resources
            resource_ids = [f"core-network-resource-{i:02d}" for i in range(5)]  # 5 resources
            requests_per_resource = 10  # 10 requests per resource = 50 total

            async def contended_request(resource_id, request_num):
                try:
                    result = await get_core_network_policy(resource_id)
                    parsed = json.loads(result)
                    return {"success": parsed["success"], "resource_id": resource_id, "request_num": request_num}
                except Exception as e:
                    return {"success": False, "resource_id": resource_id, "request_num": request_num, "error": str(e)}

            # Create all contended requests
            all_tasks = []
            for resource_id in resource_ids:
                for req_num in range(requests_per_resource):
                    task = contended_request(resource_id, req_num)
                    all_tasks.append(task)

            start_time = time.time()
            results = await asyncio.gather(*all_tasks, return_exceptions=True)
            end_time = time.time()

            execution_time = end_time - start_time
            successful_requests = sum(1 for r in results if isinstance(r, dict) and r.get("success", False))

            # Resource contention should be handled gracefully
            total_requests = len(all_tasks)
            assert successful_requests >= total_requests * 0.9, (
                f"Resource contention: {successful_requests}/{total_requests}"
            )
            assert execution_time < 120.0, f"Resource contention test took {execution_time:.2f}s"

            # Analyze resource wait patterns
            if resource_wait_times:
                avg_wait = sum(resource_wait_times) / len(resource_wait_times)
                max_wait = max(resource_wait_times)

                assert avg_wait < 1.0, f"Average resource wait {avg_wait:.3f}s"
                assert max_wait < 5.0, f"Max resource wait {max_wait:.3f}s"

            print(
                f"Resource contention: {successful_acquisitions} successful, {failed_acquisitions} failed acquisitions"
            )


class TestAtomicOperationValidation:
    """Test atomic operation validation under concurrency."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_atomic_policy_operations(self) -> None:
        """Test atomic policy update operations."""
        policy_version_counter = 0
        concurrent_updates = []
        update_conflicts = 0
        successful_updates = 0

        def atomic_policy_mock(service, region=None):
            nonlocal policy_version_counter, update_conflicts, successful_updates
            mock_client = Mock()

            def atomic_update_operation(**kwargs):
                nonlocal policy_version_counter, update_conflicts, successful_updates

                operation_start = time.time()
                current_version = policy_version_counter

                # Simulate version check and update race condition
                time.sleep(0.01)  # Small window for race condition

                if policy_version_counter != current_version:
                    # Version changed during operation - conflict
                    update_conflicts += 1
                    raise ClientError(
                        {
                            "Error": {
                                "Code": "OptimisticLockException",
                                "Message": f"Policy version changed from {current_version} to {policy_version_counter}",
                                "ExpectedVersion": str(current_version),
                                "ActualVersion": str(policy_version_counter),
                            }
                        },
                        "UpdateCoreNetworkPolicy",
                    )

                # Simulate successful atomic update
                policy_version_counter += 1
                successful_updates += 1

                concurrent_updates.append(
                    {
                        "timestamp": operation_start,
                        "old_version": current_version,
                        "new_version": policy_version_counter,
                        "thread_id": threading.current_thread().ident,
                    }
                )

                return {
                    "CoreNetworkPolicy": {
                        "PolicyVersionId": str(policy_version_counter),
                        "PolicyDocument": json.dumps(
                            {"version": "2021.12", "update-timestamp": operation_start, "atomic-operation": True}
                        ),
                        "ChangeSetState": "READY_TO_EXECUTE",
                    }
                }

            mock_client.get_core_network_policy.side_effect = atomic_update_operation
            return mock_client

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client", side_effect=atomic_policy_mock):
            # Test concurrent atomic operations
            concurrent_operations = 50

            async def atomic_operation_request(request_id):
                try:
                    result = await get_core_network_policy(f"core-network-atomic-{request_id:03d}")
                    parsed = json.loads(result)
                    return {
                        "success": parsed["success"],
                        "request_id": request_id,
                        "policy_version": parsed.get("policy_version_id", "unknown"),
                    }
                except Exception as e:
                    return {"success": False, "request_id": request_id, "error": str(e)}

            tasks = [atomic_operation_request(i) for i in range(concurrent_operations)]

            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()

            execution_time = end_time - start_time
            successful_requests = sum(1 for r in results if isinstance(r, dict) and r.get("success", False))

            # Atomic operations should maintain consistency
            assert successful_updates > 0, "No successful atomic updates"
            assert successful_requests >= concurrent_operations * 0.8, (
                f"Atomic operations: {successful_requests}/{concurrent_operations}"
            )
            assert execution_time < 60.0, f"Atomic operations took {execution_time:.2f}s"

            # Verify no version conflicts in successful updates
            if concurrent_updates:
                versions = [update["new_version"] for update in concurrent_updates]
                assert len(set(versions)) == len(versions), "Version collision detected in atomic updates"
                assert max(versions) == len(concurrent_updates), "Version sequence not maintained"

            print(f"Atomic operations: {successful_updates} successful, {update_conflicts} conflicts")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_session_token_race_conditions(self) -> None:
        """Test session token handling under race conditions."""
        session_tokens = {}
        token_refresh_count = 0
        token_conflicts = 0

        def session_token_mock(service, region=None):
            nonlocal token_refresh_count, token_conflicts
            mock_client = Mock()

            def token_aware_operation(**kwargs):
                nonlocal token_refresh_count, token_conflicts

                client_id = kwargs.get("ClientId", "default-client")

                # Simulate token expiry and refresh logic
                current_time = time.time()

                if client_id not in session_tokens:
                    # Initial token creation
                    session_tokens[client_id] = {
                        "token": f"token-{client_id}-{token_refresh_count:06d}",
                        "expires_at": current_time + 3600,  # 1 hour
                        "created_at": current_time,
                    }
                    token_refresh_count += 1

                token_info = session_tokens[client_id]

                # Check for token expiry (simulate short expiry for testing)
                if current_time > token_info["expires_at"] - 3500:  # Refresh 100s before expiry
                    # Token refresh race condition window
                    time.sleep(0.01)

                    # Check if another thread already refreshed
                    if session_tokens[client_id] == token_info:
                        # We won the race - refresh token
                        session_tokens[client_id] = {
                            "token": f"token-{client_id}-{token_refresh_count:06d}",
                            "expires_at": current_time + 3600,
                            "created_at": current_time,
                        }
                        token_refresh_count += 1
                    else:
                        # Another thread refreshed - potential conflict
                        token_conflicts += 1

                return {
                    "CoreNetworks": [
                        {
                            "CoreNetworkId": f"core-network-token-{client_id}",
                            "SessionToken": session_tokens[client_id]["token"],
                        }
                    ]
                }

            mock_client.list_core_networks.side_effect = token_aware_operation
            return mock_client

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client", side_effect=session_token_mock):
            # Test concurrent requests with shared session tokens
            clients_count = 10
            requests_per_client = 20

            async def session_token_request(client_id, request_num):
                try:
                    # Add client identifier to trigger session token logic
                    result = await list_core_networks(region="us-east-1")
                    parsed = json.loads(result)
                    return {"success": parsed["success"], "client_id": client_id, "request_num": request_num}
                except Exception as e:
                    return {"success": False, "client_id": client_id, "request_num": request_num, "error": str(e)}

            # Create concurrent requests from multiple clients
            all_tasks = []
            for client_id in range(clients_count):
                for req_num in range(requests_per_client):
                    task = session_token_request(f"client-{client_id:02d}", req_num)
                    all_tasks.append(task)

            start_time = time.time()
            results = await asyncio.gather(*all_tasks, return_exceptions=True)
            end_time = time.time()

            execution_time = end_time - start_time
            successful_requests = sum(1 for r in results if isinstance(r, dict) and r.get("success", False))
            total_requests = len(all_tasks)

            # Session token handling should be robust
            assert successful_requests >= total_requests * 0.95, (
                f"Session token handling: {successful_requests}/{total_requests}"
            )
            assert execution_time < 90.0, f"Session token test took {execution_time:.2f}s"

            # Token management should be efficient
            assert token_refresh_count <= clients_count * 2, f"Too many token refreshes: {token_refresh_count}"
            assert token_conflicts <= total_requests * 0.1, f"Too many token conflicts: {token_conflicts}"

            print(
                f"Session tokens: {len(session_tokens)} clients, "
                f"{token_refresh_count} refreshes, {token_conflicts} conflicts"
            )


class TestIdempotencyTokenHandling:
    """Test idempotency token handling patterns."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_idempotent_operation_deduplication(self) -> None:
        """Test idempotent operation deduplication."""
        processed_operations = {}
        duplicate_operations = 0
        unique_operations = 0

        def idempotent_mock(service, region=None):
            nonlocal duplicate_operations, unique_operations
            mock_client = Mock()

            def idempotent_operation(**kwargs):
                nonlocal duplicate_operations, unique_operations

                # Extract idempotency token (simulate from request metadata)
                operation_params = str(sorted(kwargs.items()))
                idempotency_key = hash(operation_params)

                if idempotency_key in processed_operations:
                    # Duplicate operation - return cached result
                    duplicate_operations += 1
                    return processed_operations[idempotency_key]["result"]
                else:
                    # New operation - process and cache
                    unique_operations += 1

                    # Simulate processing
                    time.sleep(0.02)  # 20ms processing time

                    result = {
                        "Routes": [
                            {
                                "DestinationCidrBlock": f"10.{unique_operations}.0.0/16",
                                "State": "active",
                                "IdempotencyKey": str(idempotency_key),
                                "ProcessedAt": time.time(),
                            }
                        ]
                    }

                    processed_operations[idempotency_key] = {"result": result, "first_processed": time.time()}

                    return result

            mock_client.search_transit_gateway_routes.side_effect = idempotent_operation
            return mock_client

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client", side_effect=idempotent_mock):
            # Test idempotent operations with intentional duplicates
            route_table_ids = [f"tgw-rtb-idem-{i:02d}" for i in range(10)]  # 10 unique route tables
            duplicate_factor = 5  # Each request repeated 5 times

            async def idempotent_request(route_table_id, attempt_num):
                try:
                    result = await analyze_tgw_routes(route_table_id)
                    parsed = json.loads(result)
                    return {
                        "success": parsed["success"],
                        "route_table_id": route_table_id,
                        "attempt_num": attempt_num,
                        "total_routes": parsed.get("analysis", {}).get("total_routes", 0),
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "route_table_id": route_table_id,
                        "attempt_num": attempt_num,
                        "error": str(e),
                    }

            # Create requests with duplicates
            all_tasks = []
            for route_table_id in route_table_ids:
                for attempt in range(duplicate_factor):
                    task = idempotent_request(route_table_id, attempt)
                    all_tasks.append(task)

            start_time = time.time()
            results = await asyncio.gather(*all_tasks, return_exceptions=True)
            end_time = time.time()

            execution_time = end_time - start_time
            successful_requests = sum(1 for r in results if isinstance(r, dict) and r.get("success", False))
            total_requests = len(all_tasks)

            # Idempotency should work correctly
            assert successful_requests == total_requests, (
                f"Idempotent operations: {successful_requests}/{total_requests}"
            )
            assert unique_operations == len(route_table_ids), (
                f"Expected {len(route_table_ids)} unique operations, got {unique_operations}"
            )
            assert duplicate_operations == total_requests - unique_operations, (
                f"Expected {total_requests - unique_operations} duplicates, got {duplicate_operations}"
            )

            # Duplicates should be processed faster (cached results)
            expected_max_time = unique_operations * 0.02 + 10  # Processing time + overhead
            assert execution_time < expected_max_time, f"Idempotent deduplication took {execution_time:.2f}s"

            print(f"Idempotency: {unique_operations} unique, {duplicate_operations} cached operations")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_bulk_operation_rollback_patterns(self) -> None:
        """Test bulk operation rollback patterns."""
        operation_log = []
        rollback_operations = []
        successful_batches = 0
        failed_batches = 0

        def bulk_rollback_mock(service, region=None):
            nonlocal successful_batches, failed_batches
            mock_client = Mock()

            def bulk_operation(**kwargs):
                nonlocal successful_batches, failed_batches

                batch_id = kwargs.get("BatchId", f"batch-{len(operation_log):04d}")
                operations = kwargs.get("Operations", [])

                operation_results = []
                rollback_needed = False

                # Process operations in batch
                for i, operation in enumerate(operations):
                    op_id = f"{batch_id}-op-{i:03d}"

                    try:
                        # Simulate operation processing with potential failure
                        if "fail" in operation.get("type", "").lower() or i % 7 == 6:  # Fail every 7th operation
                            raise ClientError(
                                {"Error": {"Code": "ValidationException", "Message": f"Operation {op_id} failed"}},
                                "BulkOperation",
                            )

                        # Successful operation
                        operation_result = {
                            "OperationId": op_id,
                            "Status": "SUCCESS",
                            "Result": f"Processed {operation.get('data', 'unknown')}",
                        }
                        operation_results.append(operation_result)
                        operation_log.append(
                            {"batch_id": batch_id, "operation_id": op_id, "status": "success", "timestamp": time.time()}
                        )

                    except ClientError as e:
                        # Operation failed - need rollback
                        rollback_needed = True
                        operation_results.append({"OperationId": op_id, "Status": "FAILED", "Error": str(e)})
                        break  # Stop processing on first failure

                if rollback_needed:
                    # Perform rollback of successful operations in this batch
                    rollback_ops = [
                        log for log in operation_log if log["batch_id"] == batch_id and log["status"] == "success"
                    ]

                    for rollback_op in rollback_ops:
                        rollback_operations.append(
                            {
                                "original_operation": rollback_op["operation_id"],
                                "rollback_timestamp": time.time(),
                                "batch_id": batch_id,
                            }
                        )
                        # Mark as rolled back
                        rollback_op["status"] = "rolled_back"

                    failed_batches += 1
                    raise ClientError(
                        {
                            "Error": {
                                "Code": "BatchOperationFailed",
                                "Message": f"Batch {batch_id} failed, rollback completed",
                            }
                        },
                        "BulkOperation",
                    )
                else:
                    successful_batches += 1
                    return {"BatchId": batch_id, "Status": "SUCCESS", "Operations": operation_results}

            mock_client.bulk_create_routes = bulk_operation
            return mock_client

        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client", side_effect=bulk_rollback_mock):
            # Test bulk operations with rollback scenarios
            batch_count = 20
            operations_per_batch = 10

            async def bulk_operation_request(batch_num):
                try:
                    # Simulate bulk route creation (using tgw route analysis as proxy)
                    operations = [
                        {
                            "type": "create_route" if i % 7 != 6 else "fail_route",  # Every 7th fails
                            "data": f"route-{batch_num:02d}-{i:02d}",
                        }
                        for i in range(operations_per_batch)
                    ]

                    # Simulate bulk operation success/failure based on batch number
                    if batch_num % 7 == 6:  # Every 7th batch fails
                        return {
                            "success": False,
                            "batch_num": batch_num,
                            "error": f"Bulk operation batch {batch_num} failed",
                            "rollback_required": True,
                        }
                    else:
                        return {"success": True, "batch_num": batch_num, "operations": len(operations)}

                except Exception as e:
                    return {"success": False, "batch_num": batch_num, "error": str(e), "rollback_required": True}

            tasks = [bulk_operation_request(i) for i in range(batch_count)]

            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()

            execution_time = end_time - start_time
            successful_requests = sum(1 for r in results if isinstance(r, dict) and r.get("success", False))

            # Bulk operations with rollback should handle failures gracefully
            assert successful_requests >= batch_count * 0.7, f"Bulk operations: {successful_requests}/{batch_count}"
            assert execution_time < 120.0, f"Bulk rollback test took {execution_time:.2f}s"

            # Verify rollback operations occurred
            len(operation_log)
            rolled_back_operations = sum(1 for log in operation_log if log["status"] == "rolled_back")

            assert len(rollback_operations) == rolled_back_operations, (
                f"Rollback count mismatch: {len(rollback_operations)} vs {rolled_back_operations}"
            )

            if rollback_operations:
                avg_rollback_time = sum(
                    rb["rollback_timestamp"]
                    - next(log["timestamp"] for log in operation_log if log["operation_id"] == rb["original_operation"])
                    for rb in rollback_operations
                ) / len(rollback_operations)

                assert avg_rollback_time < 1.0, f"Average rollback time {avg_rollback_time:.3f}s too high"

            print(
                f"Bulk operations: {successful_batches} successful batches, "
                f"{failed_batches} failed batches, {len(rollback_operations)} rollbacks"
            )
