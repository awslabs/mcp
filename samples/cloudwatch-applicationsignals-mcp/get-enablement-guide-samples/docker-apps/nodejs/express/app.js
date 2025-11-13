// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

'use strict';

const express = require('express');
const { S3Client, ListBucketsCommand } = require('@aws-sdk/client-s3');
const logger = require('pino')();

const HOST = process.env.HOST || '0.0.0.0';
const PORT = parseInt(process.env.PORT || '8080', 10);

const app = express();

const s3Client = new S3Client({ region: process.env.AWS_REGION || 'us-east-1' });

app.get('/', (req, res) => {
  healthCheck(res);
});

app.get('/health', (req, res) => {
  healthCheck(res);
});

function healthCheck(res) {
  logger.info('Health check endpoint called');
  res.type('application/json').send(JSON.stringify({status: 'healthy'}) + '\n');
}

app.get('/api/buckets', async (req, res) => {
  try {
    const data = await s3Client.send(new ListBucketsCommand({}));
    const buckets = data.Buckets.map(bucket => bucket.Name);
    logger.info(`Successfully listed ${buckets.length} S3 buckets`);
    res.type('application/json').send(JSON.stringify({
      bucket_count: buckets.length,
      buckets: buckets
    }) + '\n');
  } catch (e) {
    if (e instanceof Error) {
      logger.error(`Exception thrown when Listing Buckets: ${e.message}`);
    }
    res.status(500).type('application/json').send(JSON.stringify({
      error: 'Failed to retrieve S3 buckets'
    }) + '\n');
  }
});

app.listen(PORT, HOST, () => {
  logger.info(`Listening for requests on ${HOST}:${PORT}`);
});
