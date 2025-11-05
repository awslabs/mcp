import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export interface LambdaApiGatewayStackProps extends cdk.StackProps {
  functionName: string;
  runtime: string;
  architecture: string;
}

export class LambdaApiGatewayStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: LambdaApiGatewayStackProps) {
    super(scope, id, props);

    const lambdaFunction = new lambda.Function(this, 'LambdaFunction', {
      functionName: props.functionName,
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'lambda_function.lambda_handler',
      code: lambda.Code.fromAsset('../sample-app/function.zip'),
      memorySize: 512,
      timeout: cdk.Duration.seconds(30),

      architecture: props.architecture === 'arm64' ? lambda.Architecture.ARM_64 : lambda.Architecture.X86_64,
    });

    lambdaFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['s3:ListAllMyBuckets'],
      resources: ['*'],
    }));

    const api = new apigateway.LambdaRestApi(this, `ApiGateway-Lambda-python-cdk-${Math.random().toString(36).substring(2, 10)}`, {
      handler: lambdaFunction,
      proxy: true,

    });

    new cdk.CfnOutput(this, 'PythonFunctionName', {
      value: lambdaFunction.functionName,
      description: 'Lambda Function Name',
    });
  }
}