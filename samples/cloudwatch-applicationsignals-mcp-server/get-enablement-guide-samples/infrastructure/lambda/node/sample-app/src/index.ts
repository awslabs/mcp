import {
  APIGatewayProxyEvent,
  APIGatewayProxyResult,
  Context,
} from 'aws-lambda';

import { S3 } from '@aws-sdk/client-s3';

const s3 = new S3();

exports.handler = async (_event: APIGatewayProxyEvent, _context: Context) => {
  console.info('Serving lambda request.');

  const result = await s3.listBuckets();

  const response: APIGatewayProxyResult = {
    statusCode: 200,
    headers: {
      'Content-Type': 'text/html'
    },
    body: `<html><body><h1>Hello lambda - found ${result.Buckets?.length || 0} buckets.</h1></body></html>`,
  };
  return response;
};
