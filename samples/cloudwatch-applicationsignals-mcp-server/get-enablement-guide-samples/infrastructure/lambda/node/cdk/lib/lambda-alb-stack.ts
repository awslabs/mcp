import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as elbv2_targets from 'aws-cdk-lib/aws-elasticloadbalancingv2-targets';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export interface LambdaAlbStackProps extends cdk.StackProps {
  functionName: string;
  runtime: string;
  architecture: string;
}

export class LambdaAlbStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: LambdaAlbStackProps) {
    super(scope, id, props);

    const lambdaFunction = new lambda.Function(this, 'LambdaFunction', {
      functionName: props.functionName,
      runtime: lambda.Runtime.NODEJS_20_X,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('../sample-app/build/function.zip'),
      memorySize: 512,
      timeout: cdk.Duration.seconds(30),
      architecture: props.architecture === 'arm64' ? lambda.Architecture.ARM_64 : lambda.Architecture.X86_64,
    });

    lambdaFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['s3:ListAllMyBuckets'],
      resources: ['*'],
    }));

    const vpc = new ec2.Vpc(this, 'VPC', {
      maxAzs: 2,
      natGateways: 0,
      subnetConfiguration: [
        {
          cidrMask: 24,
          name: 'Public',
          subnetType: ec2.SubnetType.PUBLIC,
        },
      ],
    });

    const alb = new elbv2.ApplicationLoadBalancer(this, 'ALB', {
      vpc,
      internetFacing: true,
      loadBalancerName: `nodejs-cdk-alb-${Math.random().toString(36).substring(2, 8)}`,
    });

    const listener = alb.addListener('Listener', {
      port: 80,
      protocol: elbv2.ApplicationProtocol.HTTP,
    });

    listener.addTargets('LambdaTarget', {
      targets: [new elbv2_targets.LambdaTarget(lambdaFunction)],
    });

    new cdk.CfnOutput(this, 'NodejsFunctionName', {
      value: lambdaFunction.functionName,
      description: 'Lambda Function Name',
    });

    new cdk.CfnOutput(this, 'ALBUrl', {
      value: `http://${alb.loadBalancerDnsName}`,
      description: 'ALB URL',
    });
  }
}