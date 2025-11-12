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
    """Handle Lambda function invocations from API Gateway."""
    print('Serving lambda request.')
    print(f'Event: {json.dumps(event)}')

    # Get the path from API Gateway event (works with HTTP API v2.0)
    path = event.get('rawPath', event.get('path', '/'))

    # Route requests
    if path == '/health':
        return health_check()
    elif path == '/api/buckets':
        return list_buckets()
    else:
        return {
            'statusCode': 404,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Not found'}),
        }


def health_check():
    """Health check endpoint."""
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'status': 'healthy', 'service': 'python-lambda'}),
    }


def list_buckets():
    """List S3 buckets endpoint."""
    result = s3.list_buckets()
    bucket_count = len(result.get('Buckets', []))
    response_body = f'(Python) Hello lambda - found {bucket_count} buckets.'

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'text/html'},
        'body': f'<html><body><h1>{response_body}</h1></body></html>',
    }
