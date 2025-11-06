#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { LambdaAlbStack } from '../lib/lambda-alb-stack';

const app = new cdk.App();

const functionName = `awslabs-sample-java-cdk-${Math.random().toString(36).substring(2, 10)}`;
const runtime = 'java17';
const architecture = 'x86_64';

new LambdaAlbStack(app, 'LambdaAlbStack-CDK-java', {
  functionName,
  runtime,
  architecture,
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: 'us-east-1',
  },
});