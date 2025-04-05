#!/usr/bin/env python3
from aws_cdk import (
    App,
    Stack,
    CfnOutput,
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_iam as iam,
)
from constructs import Construct

class ExampleStack(Stack):
    """Example CDK stack demonstrating various AWS resources and their relationships"""
    
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create a VPC
        vpc = ec2.Vpc(
            self, "MainVPC",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                ),
                ec2.SubnetConfiguration(
                    name="private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                ),
            ]
        )

        # Create a security group for Lambda
        lambda_security_group = ec2.SecurityGroup(
            self, "LambdaSecurityGroup",
            vpc=vpc,
            description="Security group for Lambda functions",
            allow_all_outbound=True,
        )

        # Create a DynamoDB table
        table = dynamodb.Table(
            self, "ItemsTable",
            partition_key=dynamodb.Attribute(
                name="id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Create an S3 bucket
        bucket = s3.Bucket(
            self, "DataBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # Create a Lambda function
        api_function = lambda_.Function(
            self, "ApiFunction",
            runtime=lambda_.Runtime.NODEJS_18_X,
            handler="index.handler",
            code=lambda_.Code.from_inline("""
                exports.handler = async function(event, context) {
                  return {
                    statusCode: 200,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: 'Hello from Lambda!' })
                  };
                };
            """),
            vpc=vpc,
            security_groups=[lambda_security_group],
            environment={
                "TABLE_NAME": table.table_name,
                "BUCKET_NAME": bucket.bucket_name,
            },
        )

        # Grant permissions
        table.grant_read_write_data(api_function)
        bucket.grant_read_write(api_function)

        # Create a REST API
        api = apigateway.RestApi(
            self, "ItemsApi",
            description="API for managing items",
            deploy_options=apigateway.StageOptions(
                stage_name="prod",
            ),
        )

        # Add a resource and method to the API
        items = api.root.add_resource("items")
        items.add_method("GET", apigateway.LambdaIntegration(api_function))
        items.add_method("POST", apigateway.LambdaIntegration(api_function))

        # Create a processor Lambda function
        processor_function = lambda_.Function(
            self, "ProcessorFunction",
            runtime=lambda_.Runtime.NODEJS_18_X,
            handler="index.handler",
            code=lambda_.Code.from_inline("""
                exports.handler = async function(event, context) {
                  console.log('Processing data...');
                  return { success: true };
                };
            """),
            vpc=vpc,
            security_groups=[lambda_security_group],
        )

        # Grant permissions
        table.grant_read_data(processor_function)
        bucket.grant_read(processor_function)

        # Create IAM role for custom resource
        custom_resource_role = iam.Role(
            self, "CustomResourceRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )

        # Add outputs
        CfnOutput(
            self, "ApiEndpoint",
            value=api.url,
            description="API Gateway endpoint URL",
        )

        CfnOutput(
            self, "BucketName",
            value=bucket.bucket_name,
            description="S3 bucket name",
        )


# Create the CDK app and stack
app = App()
ExampleStack(app, "ExampleStack")
app.synth()
