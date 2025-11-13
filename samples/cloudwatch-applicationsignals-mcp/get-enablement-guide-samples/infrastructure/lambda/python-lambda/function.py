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

import boto3
import json
import time
from datetime import datetime


s3 = boto3.client('s3')


def lambda_handler(event, context):
    """Self-contained Lambda function that generates internal traffic.

    Runs for ~10 minutes, calling application functions in a loop.
    """
    print('Starting self-contained traffic generation')

    duration = 600  # Run for 10 minutes (600 seconds)
    interval = 2  # Call every 2 seconds

    start_time = time.time()
    iteration = 0

    while (time.time() - start_time) < duration:
        iteration += 1
        timestamp = datetime.now().strftime('%H:%M:%S')

        print(f'[{timestamp}] Iteration {iteration}: Generating traffic...')

        # Call health check logic
        health_result = health_check()
        print(f'[{timestamp}] Health check: {health_result["status"]}')

        # Call buckets logic
        buckets_result = list_buckets()
        print(f'[{timestamp}] Buckets check: {buckets_result["bucket_count"]} buckets found')

        # Sleep between requests
        time.sleep(interval)

    elapsed = time.time() - start_time
    print(
        f'Traffic generation completed. Total iterations: {iteration}, Elapsed time: {elapsed:.2f}s'
    )

    return {
        'statusCode': 200,
        'body': json.dumps(
            {
                'message': 'Traffic generation completed',
                'iterations': iteration,
                'elapsed_seconds': elapsed,
            }
        ),
    }


def health_check():
    """Health check logic."""
    return {'status': 'healthy', 'service': 'python-lambda'}


def list_buckets():
    """List S3 buckets logic."""
    result = s3.list_buckets()
    bucket_count = len(result.get('Buckets', []))

    return {'bucket_count': bucket_count, 'message': f'Found {bucket_count} buckets'}
