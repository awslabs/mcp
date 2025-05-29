#!/bin/bash

# AWS Helper functions for ECS MCP Server LLM testing
# This file contains utility functions that can be sourced by test scripts

# Generate a random 5-letter ID for uniquely naming resources
# Usage: resource_id=$(generate_random_id)
generate_random_id() {
    cat /dev/urandom | tr -dc 'a-z' | fold -w 5 | head -n 1
}

# Wait for CloudFormation stack to reach a specific status
# Usage: wait_for_stack_status stack_name expected_status [max_wait_seconds]
wait_for_stack_status() {
    local stack_name=$1
    local expected_status=$2
    local max_wait_seconds=${3:-300}  # Default 5 minutes

    echo "Waiting for stack $stack_name to reach status $expected_status (timeout: ${max_wait_seconds}s)..."

    local start_time=$(date +%s)

    while true; do
        local current_time=$(date +%s)
        local elapsed_time=$((current_time - start_time))

        if [ $elapsed_time -gt $max_wait_seconds ]; then
            echo "⏱️ Timeout reached. Stack did not reach $expected_status within $max_wait_seconds seconds."
            return 1
        fi

        local status
        status=$(aws cloudformation describe-stacks --stack-name $stack_name --query 'Stacks[0].StackStatus' --output text 2>/dev/null)
        local exit_code=$?

        if [ $exit_code -ne 0 ]; then
            echo "Stack $stack_name does not exist or cannot be accessed."
            return 1
        fi

        echo "Current status: $status (elapsed time: ${elapsed_time}s)"

        if [[ "$status" == "$expected_status" ]]; then
            echo "✅ Stack reached $expected_status status."
            return 0
        fi

        # Special handling for failure states when not explicitly waiting for them
        if [[ "$expected_status" != *"FAIL"* && "$expected_status" != *"ROLLBACK"* ]]; then
            if [[ "$status" == *"FAIL"* || "$status" == *"ROLLBACK"* ]]; then
                echo "❌ Stack entered failure state $status while waiting for $expected_status."
                return 1
            fi
        fi

        sleep 10  # Check every 10 seconds
    done
}

# Wait for ECS service to reach stable state
# Usage: wait_for_service_stable cluster_name service_name [max_wait_seconds]
wait_for_service_stable() {
    local cluster_name=$1
    local service_name=$2
    local max_wait_seconds=${3:-300}  # Default 5 minutes

    echo "Waiting for service $service_name in cluster $cluster_name to reach stable state (timeout: ${max_wait_seconds}s)..."

    local start_time=$(date +%s)

    while true; do
        local current_time=$(date +%s)
        local elapsed_time=$((current_time - start_time))

        if [ $elapsed_time -gt $max_wait_seconds ]; then
            echo "⏱️ Timeout reached. Service did not stabilize within $max_wait_seconds seconds."
            return 1
        fi

        local service_data
        service_data=$(aws ecs describe-services --cluster $cluster_name --services $service_name 2>/dev/null)
        local exit_code=$?

        if [ $exit_code -ne 0 ]; then
            echo "Service $service_name in cluster $cluster_name does not exist or cannot be accessed."
            return 1
        fi

        local deployments_stable
        deployments_stable=$(echo "$service_data" | jq -r '.services[0].deployments | length == 1 and .[0].rolloutState == "COMPLETED"')

        local running_count
        running_count=$(echo "$service_data" | jq -r '.services[0].runningCount')

        local desired_count
        desired_count=$(echo "$service_data" | jq -r '.services[0].desiredCount')

        echo "Status: running $running_count / $desired_count tasks (elapsed time: ${elapsed_time}s)"

        if [ "$deployments_stable" == "true" ] && [ "$running_count" -eq "$desired_count" ]; then
            echo "✅ Service is stable with $running_count running tasks."
            return 0
        fi

        # Check for failed tasks
        local failed_tasks
        failed_tasks=$(aws ecs list-tasks --cluster $cluster_name --service-name $service_name --desired-status STOPPED --query 'length(taskArns)')

        if [ "$failed_tasks" -gt 0 ]; then
            echo "❌ Service has $failed_tasks failed tasks."
            return 1
        fi

        sleep 10  # Check every 10 seconds
    done
}

# Check if a task has failed
# Usage: check_task_failed cluster_name task_arn
check_task_failed() {
    local cluster_name=$1
    local task_arn=$2

    local task_status
    task_status=$(aws ecs describe-tasks --cluster $cluster_name --tasks $task_arn --query 'tasks[0].lastStatus' --output text)

    if [ "$task_status" == "STOPPED" ]; then
        local stop_code
        stop_code=$(aws ecs describe-tasks --cluster $cluster_name --tasks $task_arn --query 'tasks[0].stoppedReason' --output text)
        echo "Task failed. Reason: $stop_code"
        return 0  # Failed
    else
        echo "Task status: $task_status"
        return 1  # Not failed
    fi
}

# Wait for ECS task to stop
# Usage: wait_for_task_stopped cluster_name task_arn [max_wait_seconds]
wait_for_task_stopped() {
    local cluster_name=$1
    local task_arn=$2
    local max_wait_seconds=${3:-300}  # Default 5 minutes

    echo "Waiting for task $task_arn in cluster $cluster_name to stop (timeout: ${max_wait_seconds}s)..."

    local start_time=$(date +%s)

    while true; do
        local current_time=$(date +%s)
        local elapsed_time=$((current_time - start_time))

        if [ $elapsed_time -gt $max_wait_seconds ]; then
            echo "⏱️ Timeout reached. Task did not stop within $max_wait_seconds seconds."
            return 1
        fi

        local task_status
        task_status=$(aws ecs describe-tasks --cluster $cluster_name --tasks $task_arn --query 'tasks[0].lastStatus' --output text 2>/dev/null)
        local exit_code=$?

        if [ $exit_code -ne 0 ]; then
            echo "Task $task_arn in cluster $cluster_name does not exist or cannot be accessed."
            return 1
        fi

        echo "Current status: $task_status (elapsed time: ${elapsed_time}s)"

        if [ "$task_status" == "STOPPED" ]; then
            local stop_reason
            stop_reason=$(aws ecs describe-tasks --cluster $cluster_name --tasks $task_arn --query 'tasks[0].stoppedReason' --output text)
            echo "✅ Task stopped. Reason: $stop_reason"
            return 0
        fi

        sleep 5  # Check every 5 seconds
    done
}

# Get public subnet ID from default VPC
# Usage: get_public_subnet_id
get_public_subnet_id() {
    aws ec2 describe-subnets \
      --filters "Name=vpc-id,Values=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text)" \
      --query "Subnets[0].SubnetId" --output text
}

# Get security group ID from default VPC
# Usage: get_default_security_group_id
get_default_security_group_id() {
    aws ec2 describe-security-groups \
      --filters "Name=vpc-id,Values=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text)" "Name=group-name,Values=default" \
      --query "SecurityGroups[0].GroupId" --output text
}

# Display task failure information
# Usage: display_task_failure_info cluster_name task_arn
display_task_failure_info() {
    local cluster_name=$1
    local task_arn=$2

    echo "Task failure information:"

    # Get container status
    aws ecs describe-tasks --cluster $cluster_name --tasks $task_arn \
      --query 'tasks[0].containers[].{name:name,reason:reason,exitCode:exitCode}' \
      --output table

    # Get last status and stopped reason
    aws ecs describe-tasks --cluster $cluster_name --tasks $task_arn \
      --query 'tasks[0].{lastStatus:lastStatus,stoppedReason:stoppedReason}' \
      --output table
}

# Check if CloudWatch logs contain error patterns
# Usage: check_logs_for_errors log_group_name log_stream_prefix [max_minutes]
check_logs_for_errors() {
    local log_group=$1
    local log_stream_prefix=$2
    local max_minutes=${3:-30}  # Default check logs from last 30 minutes

    echo "Checking CloudWatch logs for errors (group: $log_group, stream prefix: $log_stream_prefix)..."

    # Get the latest log stream
    local log_stream
    log_stream=$(aws logs describe-log-streams --log-group-name "$log_group" \
      --log-stream-name-prefix "$log_stream_prefix" --order-by LastEventTime \
      --descending --limit 1 --query 'logStreams[0].logStreamName' --output text)

    if [ "$log_stream" == "None" ]; then
        echo "No log stream found matching prefix $log_stream_prefix in group $log_group"
        return 1
    fi

    # Calculate timestamp for X minutes ago
    local start_time
    start_time=$(($(date +%s) - max_minutes * 60))
    start_time=$((start_time * 1000))  # Convert to milliseconds

    # Get logs and count errors
    local logs
    logs=$(aws logs get-log-events --log-group-name "$log_group" \
      --log-stream-name "$log_stream" --start-time "$start_time" \
      --query 'events[].message' --output text)

    echo "$logs" | grep -i error | wc -l
}
