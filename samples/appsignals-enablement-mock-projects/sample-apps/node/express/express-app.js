'use strict';

const express = require('express');;
const { S3Client, ListBucketsCommand } = require('@aws-sdk/client-s3');
const logger = require('pino')()

const PORT = parseInt(process.env.SAMPLE_APP_PORT || '8080', 10);
const ADDRESS = process.env.SAMPLE_APP_ADDRESS || 'localhost';

const app = express();

// Generate logs in your endpoints
app.get('/', (req, res) => {
  healthCheck(res);
});

// Generate logs in your endpoints
app.get('/health', (req, res) => {
  healthCheck(res);
});

function healthCheck(res) {
  const msg = 'OK';
  logger.info(msg);
  res.send(msg);
}

app.get('/api/buckets', async (req, res) => {
  const s3Client = new S3Client({ region: 'us-east-1' });
  try {
    await s3Client.send(
      new ListBucketsCommand({}),
    ).then((data) => {
      logger.info(`Logging Buckets from ListBuckets Result:`);
      logger.info(data.Buckets);
    });
  } catch (e) {
    if (e instanceof Error) {
      logger.error(`Exception thrown when Listing Buckets: ${e.message}`);
    }
  } finally {
    const msg = 'done aws sdk s3 request'
    logger.info(msg);
    res.send(msg);
  }
});

app.listen(PORT, ADDRESS, () => {
  console.log(`Listening for requests on ${ADDRESS}:${PORT}`);
});