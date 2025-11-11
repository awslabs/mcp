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
import os
import json
from botocore.exceptions import ClientError
from flask import Flask, Response


app = Flask(__name__)

PORT = int(os.environ.get('PORT', 5000))
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
s3_client = boto3.client('s3', region_name=AWS_REGION)


@app.route('/health')
def health():
    app.logger.info('Health check endpoint called')
    return Response(json.dumps({'status': 'healthy'}) + '\n', mimetype='application/json')


@app.route('/api/buckets')
def list_buckets():
    try:
        response = s3_client.list_buckets()
        buckets = [bucket['Name'] for bucket in response.get('Buckets', [])]
        app.logger.info(f'Successfully listed {len(buckets)} S3 buckets')
        return Response(json.dumps({'bucket_count': len(buckets), 'buckets': buckets}) + '\n', mimetype='application/json')
    except ClientError as e:
        app.logger.error(f'S3 client error: {str(e)}')
        return Response(json.dumps({'error': 'Failed to retrieve S3 buckets'}) + '\n', mimetype='application/json', status=500)


if __name__ == '__main__':
    print(f'Starting Flask application on port {PORT}')
    app.run(host='0.0.0.0', port=PORT)
