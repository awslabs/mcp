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
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';

export interface AppConfig {
  appName: string;
  imageName: string;
  language: string;
  port: number;
  healthCheckPath: string;
  serviceName: string;
}

export class ECSAppStack extends cdk.Stack {
  constructor(scope: Construct, id: string, config: AppConfig, props?: cdk.StackProps) {
    super(scope, id, props);

    // Construct ECR image URI using convention
    const ecrImageUri = `${this.account}.dkr.ecr.${this.region}.amazonaws.com/${config.imageName}:latest`;

    // Use default VPC
    const vpc = ec2.Vpc.fromLookup(this, 'DefaultVPC', {
      isDefault: true,
    });

    // Create ECS cluster with container insights enabled
    const cluster = new ecs.Cluster(this, 'Cluster', {
      vpc,
      clusterName: `${config.appName}-cluster`,
      containerInsights: true,
    });

    // IAM task execution role for ECS tasks
    const taskExecutionRole = new iam.Role(this, 'TaskExecutionRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonECSTaskExecutionRolePolicy'),
      ],
    });

    // IAM task role for basic ECS tasks
    const taskRole = new iam.Role(this, 'TaskRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonS3ReadOnlyAccess'),
      ],
    });

    // Create CloudWatch log group for the application
    const logGroup = new logs.LogGroup(this, 'LogGroup', {
      logGroupName: `/ecs/${config.appName}`,
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // Create CloudWatch log group for curl sidecar
    const curlLogGroup = new logs.LogGroup(this, `${config.appName}CurlLogGroup`, {
      logGroupName: `/ecs/${config.appName}-curl`,
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // Task definition
    const taskDefinition = new ecs.FargateTaskDefinition(this, 'TaskDefinition', {
      memoryLimitMiB: 1024,
      cpu: 512,
      executionRole: taskExecutionRole,
      taskRole: taskRole,
    });

    // Add volume for tmp directory
    taskDefinition.addVolume({
      name: 'tmp',
    });

    // Add application container
    const appContainer = taskDefinition.addContainer('Application', {
      image: ecs.ContainerImage.fromRegistry(ecrImageUri),
      essential: true,
      memoryReservationMiB: 512,
      readonlyRootFilesystem: true,
      environment: {
        PORT: config.port.toString(),
      },
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'app',
        logGroup: logGroup,
      }),
    });

    // Add port mapping for application
    appContainer.addPortMappings({
      containerPort: config.port,
      protocol: ecs.Protocol.TCP,
    });

    // Add mount point for tmp volume
    appContainer.addMountPoints({
      sourceVolume: 'tmp',
      containerPath: '/tmp',
      readOnly: false,
    });

    // Add curl sidecar container
    const curlContainer = taskDefinition.addContainer('CurlSidecar', {
      image: ecs.ContainerImage.fromRegistry('curlimages/curl:8.1.2'),
      essential: false,
      memoryReservationMiB: 128,
      command: [
        'sh', '-c',
        `echo 'Starting curl sidecar...'; sleep 30; while true; do echo "$(date): Curling localhost:${config.port}/api/buckets"; curl -f localhost:${config.port}/api/buckets || echo 'Curl failed'; sleep 60; done`
      ],
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'curl',
        logGroup: curlLogGroup,
      }),
    });

    // Add dependency so curl waits for app to start
    curlContainer.addContainerDependencies({
      container: appContainer,
      condition: ecs.ContainerDependencyCondition.START,
    });

    // Create security group for ECS service with minimal permissions
    const securityGroup = new ec2.SecurityGroup(this, 'EcsSecurityGroup', {
      vpc,
      description: 'Security group for ECS service - allows limited outbound access',
      allowAllOutbound: false,
    });

    // Add outbound rules for ECS operations
    securityGroup.addEgressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(443),
      'HTTPS for ECR and AWS APIs'
    );

    securityGroup.addEgressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(80),
      'HTTP for package downloads'
    );

    securityGroup.addEgressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.udp(53),
      'DNS UDP'
    );

    securityGroup.addEgressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(53),
      'DNS TCP'
    );

    // Determine subnet configuration - prefer private subnets if available
    const privateSubnets = vpc.privateSubnets;
    const publicSubnets = vpc.publicSubnets;

    const usePrivateSubnets = privateSubnets.length > 0;
    const subnets = usePrivateSubnets ? privateSubnets : publicSubnets;

    // Create ECS service without load balancer
    const service = new ecs.FargateService(this, 'Service', {
      cluster,
      taskDefinition,
      serviceName: config.appName,
      desiredCount: 2,
      assignPublicIp: !usePrivateSubnets, // Only assign public IP if using public subnets
      vpcSubnets: {
        subnets: subnets,
      },
      securityGroups: [securityGroup],
    });

    // Outputs
    new cdk.CfnOutput(this, 'ClusterName', {
      value: cluster.clusterName,
      description: 'ECS Cluster Name',
    });

    new cdk.CfnOutput(this, 'ServiceName', {
      value: service.serviceName,
      description: 'ECS Service Name',
    });

    new cdk.CfnOutput(this, 'ECRImageURI', {
      value: ecrImageUri,
      description: 'ECR image URI used',
    });

    new cdk.CfnOutput(this, 'Language', {
      value: config.language,
      description: 'Application language',
    });

    new cdk.CfnOutput(this, 'AppLogGroup', {
      value: logGroup.logGroupName,
      description: 'Application CloudWatch Log Group',
    });

    new cdk.CfnOutput(this, 'CurlLogGroup', {
      value: curlLogGroup.logGroupName,
      description: 'Curl Sidecar CloudWatch Log Group',
    });

    new cdk.CfnOutput(this, 'SubnetType', {
      value: usePrivateSubnets ? 'Private' : 'Public',
      description: 'Type of subnets used for ECS tasks',
    });
  }
}
