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

import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as apigatewayv2 from 'aws-cdk-lib/aws-apigatewayv2';
import { HttpLambdaIntegration } from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import { Construct } from 'constructs';
import * as path from 'path';

export interface LambdaConfig {
  functionName: string;
  runtime: string;
  handler: string;
  artifactPath: string;
  timeout: number;
  memorySize: number;
}

export class LambdaStack extends cdk.Stack {
  constructor(scope: Construct, id: string, config: LambdaConfig, props?: cdk.StackProps) {
    super(scope, id, props);

    // Map runtime string to Lambda Runtime object
    const runtimeMap: { [key: string]: lambda.Runtime } = {
      'python3.13': lambda.Runtime.PYTHON_3_13,
    };

    const lambdaRuntime = runtimeMap[config.runtime];
    if (!lambdaRuntime) {
      throw new Error(`Unsupported runtime: ${config.runtime}`);
    }

    // Resolve artifact path
    const artifactPath = path.resolve(__dirname, '..', config.artifactPath);

    // IAM role for Lambda
    const lambdaRole = new iam.Role(this, 'LambdaRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonS3ReadOnlyAccess'),
      ],
    });

    // Lambda function
    const lambdaFunction = new lambda.Function(this, 'Function', {
      functionName: config.functionName,
      runtime: lambdaRuntime,
      handler: config.handler,
      code: lambda.Code.fromAsset(artifactPath),
      role: lambdaRole,
      timeout: cdk.Duration.seconds(config.timeout),
      memorySize: config.memorySize,
    });

    // API Gateway HTTP API
    const httpApi = new apigatewayv2.HttpApi(this, 'HttpApi', {
      apiName: `${config.functionName}-api`,
    });

    const integration = new HttpLambdaIntegration('LambdaIntegration', lambdaFunction);

    httpApi.addRoutes({
      path: '/{proxy+}',
      methods: [apigatewayv2.HttpMethod.ANY],
      integration: integration,
    });

    // Also add root path
    httpApi.addRoutes({
      path: '/',
      methods: [apigatewayv2.HttpMethod.ANY],
      integration: integration,
    });

    // Outputs
    new cdk.CfnOutput(this, 'ApiUrl', {
      value: httpApi.url || '',
      description: 'API Gateway URL',
    });

    new cdk.CfnOutput(this, 'HealthUrl', {
      value: `${httpApi.url}health`,
      description: 'Health endpoint URL',
    });

    new cdk.CfnOutput(this, 'BucketsUrl', {
      value: `${httpApi.url}api/buckets`,
      description: 'Buckets API endpoint URL',
    });

    // Lambda function outputs
    new cdk.CfnOutput(this, 'FunctionName', {
      value: lambdaFunction.functionName,
      description: 'Lambda function name',
    });

    new cdk.CfnOutput(this, 'FunctionArn', {
      value: lambdaFunction.functionArn,
      description: 'Lambda function ARN',
    });
  }
}
