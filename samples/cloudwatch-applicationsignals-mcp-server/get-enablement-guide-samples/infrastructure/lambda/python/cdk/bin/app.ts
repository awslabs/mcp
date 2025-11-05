#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { LambdaApiGatewayStack } from '../lib/lambda-apigateway-stack';

const app = new cdk.App();

const functionName = `awslabs-sample-python-cdk-${Math.random().toString(36).substring(2, 10)}`;
const runtime = 'python3.12';
const architecture = 'x86_64';

new LambdaApiGatewayStack(app, 'LambdaApiGatewayStack-CDK-python', {
  functionName,
  runtime,
  architecture,
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});