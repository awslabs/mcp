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


s3 = boto3.client('s3')


def lambda_handler(event, context):
    """Lambda function that performs S3 bucket operations."""
    print('Starting Lambda execution')

    # Call buckets logic
    buckets_result = list_buckets()
    print(f'Buckets check: {buckets_result["bucket_count"]} buckets found')

    return {
        'statusCode': 200,
        'body': json.dumps(
            {
                'message': 'Execution completed',
                'buckets': buckets_result,
            }
        ),
    }


def list_buckets():
    """List S3 buckets logic."""
    result = s3.list_buckets()
    bucket_count = len(result.get('Buckets', []))

    return {'bucket_count': bucket_count, 'message': f'Found {bucket_count} buckets'}
