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
import logging
import os
from botocore.exceptions import ClientError
from django.http import HttpResponse


logger = logging.getLogger(__name__)

AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
s3_client = boto3.client('s3', region_name=AWS_REGION)


def health(request):
    """Health check endpoint that returns application status."""
    logger.info('Health check endpoint called')
    response_data = json.dumps({'status': 'healthy'}) + '\n'
    return HttpResponse(response_data, content_type='application/json')


def list_buckets(request):
    """List all S3 buckets and return count and names."""
    try:
        response = s3_client.list_buckets()
        buckets = [bucket['Name'] for bucket in response.get('Buckets', [])]
        logger.info(f'Successfully listed {len(buckets)} S3 buckets')
        response_data = json.dumps({'bucket_count': len(buckets), 'buckets': buckets}) + '\n'
        return HttpResponse(response_data, content_type='application/json')
    except ClientError as e:
        logger.error(f'S3 client error: {str(e)}')
        response_data = json.dumps({'error': 'Failed to retrieve S3 buckets'}) + '\n'
        return HttpResponse(response_data, content_type='application/json', status=500)
