# AWS Provider Resources Listing

AWS Provider Version: 5.94.1

Last updated: April 08, 2025 16:51:28

Found 1492 resources and 601 data sources across 240 AWS service categories.

## Table of Contents
- [ACM (Certificate Manager)](#acm-certificate-manager)
- [ACM PCA (Certificate Manager Private Certificate Authority)](#acm-pca-certificate-manager-private-certificate-authority)
- [AMP (Managed Prometheus)](#amp-managed-prometheus)
- [API Gateway](#api-gateway)
- [API Gateway V2](#api-gateway-v2)
- [Account Management](#account-management)
- [Amazon Q Business](#amazon-q-business)
- [Amplify](#amplify)
- [App Mesh](#app-mesh)
- [App Runner](#app-runner)
- [AppConfig](#appconfig)
- [AppFabric](#appfabric)
- [AppFlow](#appflow)
- [AppIntegrations](#appintegrations)
- [AppStream 2.0](#appstream-2.0)
- [AppSync](#appsync)
- [Application Auto Scaling](#application-auto-scaling)
- [Athena](#athena)
- [Audit Manager](#audit-manager)
- [Auto Scaling](#auto-scaling)
- [Auto Scaling Plans](#auto-scaling-plans)
- [BCM Data Exports](#bcm-data-exports)
- [Backup](#backup)
- [Batch](#batch)
- [Bedrock](#bedrock)
- [Bedrock Agents](#bedrock-agents)
- [Billing](#billing)
- [CE (Cost Explorer)](#ce-cost-explorer)
- [Chatbot](#chatbot)
- [Chime](#chime)
- [Chime SDK Media Pipelines](#chime-sdk-media-pipelines)
- [Chime SDK Voice](#chime-sdk-voice)
- [Clean Rooms](#clean-rooms)
- [Cloud Control API](#cloud-control-api)
- [Cloud Map](#cloud-map)
- [Cloud9](#cloud9)
- [CloudFormation](#cloudformation)
- [CloudFront](#cloudfront)
- [CloudFront KeyValueStore](#cloudfront-keyvaluestore)
- [CloudHSM](#cloudhsm)
- [CloudSearch](#cloudsearch)
- [CloudTrail](#cloudtrail)
- [CloudWatch](#cloudwatch)
- [CloudWatch Application Insights](#cloudwatch-application-insights)
- [CloudWatch Evidently](#cloudwatch-evidently)
- [CloudWatch Internet Monitor](#cloudwatch-internet-monitor)
- [CloudWatch Logs](#cloudwatch-logs)
- [CloudWatch Network Monitor](#cloudwatch-network-monitor)
- [CloudWatch Observability Access Manager](#cloudwatch-observability-access-manager)
- [CloudWatch RUM](#cloudwatch-rum)
- [CloudWatch Synthetics](#cloudwatch-synthetics)
- [CodeArtifact](#codeartifact)
- [CodeBuild](#codebuild)
- [CodeCatalyst](#codecatalyst)
- [CodeCommit](#codecommit)
- [CodeConnections](#codeconnections)
- [CodeDeploy](#codedeploy)
- [CodeGuru Profiler](#codeguru-profiler)
- [CodeGuru Reviewer](#codeguru-reviewer)
- [CodePipeline](#codepipeline)
- [CodeStar Connections](#codestar-connections)
- [CodeStar Notifications](#codestar-notifications)
- [Cognito IDP (Identity Provider)](#cognito-idp-identity-provider)
- [Cognito Identity](#cognito-identity)
- [Comprehend](#comprehend)
- [Compute Optimizer](#compute-optimizer)
- [Config](#config)
- [Connect](#connect)
- [Connect Customer Profiles](#connect-customer-profiles)
- [Control Tower](#control-tower)
- [Cost Optimization Hub](#cost-optimization-hub)
- [Cost and Usage Report](#cost-and-usage-report)
- [DLM (Data Lifecycle Manager)](#dlm-data-lifecycle-manager)
- [DMS (Database Migration)](#dms-database-migration)
- [DRS (Elastic Disaster Recovery)](#drs-elastic-disaster-recovery)
- [Data Exchange](#data-exchange)
- [Data Pipeline](#data-pipeline)
- [DataSync](#datasync)
- [DataZone](#datazone)
- [Detective](#detective)
- [DevOps Guru](#devops-guru)
- [Device Farm](#device-farm)
- [Direct Connect](#direct-connect)
- [Directory Service](#directory-service)
- [DocumentDB](#documentdb)
- [DocumentDB Elastic](#documentdb-elastic)
- [DynamoDB](#dynamodb)
- [DynamoDB Accelerator (DAX)](#dynamodb-accelerator-dax)
- [EBS (EC2)](#ebs-ec2)
- [EC2 (Elastic Compute Cloud)](#ec2-elastic-compute-cloud)
- [EC2 Image Builder](#ec2-image-builder)
- [ECR (Elastic Container Registry)](#ecr-elastic-container-registry)
- [ECR Public](#ecr-public)
- [ECS (Elastic Container)](#ecs-elastic-container)
- [EFS (Elastic File System)](#efs-elastic-file-system)
- [EKS (Elastic Kubernetes)](#eks-elastic-kubernetes)
- [ELB (Elastic Load Balancing)](#elb-elastic-load-balancing)
- [ELB Classic](#elb-classic)
- [EMR](#emr)
- [EMR Containers](#emr-containers)
- [EMR Serverless](#emr-serverless)
- [ElastiCache](#elasticache)
- [Elastic Beanstalk](#elastic-beanstalk)
- [Elastic Transcoder](#elastic-transcoder)
- [Elasticsearch](#elasticsearch)
- [Elemental MediaConvert](#elemental-mediaconvert)
- [Elemental MediaLive](#elemental-medialive)
- [Elemental MediaPackage](#elemental-mediapackage)
- [Elemental MediaPackage Version 2](#elemental-mediapackage-version-2)
- [Elemental MediaStore](#elemental-mediastore)
- [End User Messaging SMS](#end-user-messaging-sms)
- [EventBridge](#eventbridge)
- [EventBridge Pipes](#eventbridge-pipes)
- [EventBridge Scheduler](#eventbridge-scheduler)
- [EventBridge Schemas](#eventbridge-schemas)
- [FIS (Fault Injection Simulator)](#fis-fault-injection-simulator)
- [FMS (Firewall Manager)](#fms-firewall-manager)
- [FSx](#fsx)
- [FinSpace](#finspace)
- [GameLift](#gamelift)
- [Global Accelerator](#global-accelerator)
- [Glue](#glue)
- [GuardDuty](#guardduty)
- [IAM (Identity & Access Management)](#iam-identity-&-access-management)
- [IAM Access Analyzer](#iam-access-analyzer)
- [IVS (Interactive Video)](#ivs-interactive-video)
- [IVS (Interactive Video) Chat](#ivs-interactive-video-chat)
- [Inspector](#inspector)
- [Inspector Classic](#inspector-classic)
- [IoT Core](#iot-core)
- [KMS (Key Management)](#kms-key-management)
- [Kendra](#kendra)
- [Keyspaces (for Apache Cassandra)](#keyspaces-for-apache-cassandra)
- [Kinesis](#kinesis)
- [Kinesis Analytics](#kinesis-analytics)
- [Kinesis Analytics V2](#kinesis-analytics-v2)
- [Kinesis Firehose](#kinesis-firehose)
- [Kinesis Video](#kinesis-video)
- [Lake Formation](#lake-formation)
- [Lambda](#lambda)
- [Lex Model Building](#lex-model-building)
- [Lex V2 Models](#lex-v2-models)
- [License Manager](#license-manager)
- [Lightsail](#lightsail)
- [Location](#location)
- [MQ](#mq)
- [MWAA (Managed Workflows for Apache Airflow)](#mwaa-managed-workflows-for-apache-airflow)
- [Macie](#macie)
- [Mainframe Modernization](#mainframe-modernization)
- [Managed Grafana](#managed-grafana)
- [Managed Streaming for Kafka](#managed-streaming-for-kafka)
- [Managed Streaming for Kafka Connect](#managed-streaming-for-kafka-connect)
- [MemoryDB](#memorydb)
- [Meta Data Sources](#meta-data-sources)
- [Neptune](#neptune)
- [Neptune Analytics](#neptune-analytics)
- [Network Firewall](#network-firewall)
- [Network Manager](#network-manager)
- [OpenSearch](#opensearch)
- [OpenSearch Ingestion](#opensearch-ingestion)
- [OpenSearch Serverless](#opensearch-serverless)
- [OpsWorks](#opsworks)
- [Organizations](#organizations)
- [Outposts](#outposts)
- [Outposts (EC2)](#outposts-ec2)
- [Payment Cryptography Control Plane](#payment-cryptography-control-plane)
- [Pinpoint](#pinpoint)
- [Polly](#polly)
- [Pricing Calculator](#pricing-calculator)
- [QLDB (Quantum Ledger Database)](#qldb-quantum-ledger-database)
- [QuickSight](#quicksight)
- [RAM (Resource Access Manager)](#ram-resource-access-manager)
- [RDS (Relational Database)](#rds-relational-database)
- [Recycle Bin (RBin)](#recycle-bin-rbin)
- [Redshift](#redshift)
- [Redshift Data](#redshift-data)
- [Redshift Serverless](#redshift-serverless)
- [Rekognition](#rekognition)
- [Resilience Hub](#resilience-hub)
- [Resource Explorer](#resource-explorer)
- [Resource Groups](#resource-groups)
- [Resource Groups Tagging](#resource-groups-tagging)
- [Roles Anywhere](#roles-anywhere)
- [Route 53](#route-53)
- [Route 53 Domains](#route-53-domains)
- [Route 53 Profiles](#route-53-profiles)
- [Route 53 Recovery Control Config](#route-53-recovery-control-config)
- [Route 53 Recovery Readiness](#route-53-recovery-readiness)
- [Route 53 Resolver](#route-53-resolver)
- [S3 (Simple Storage)](#s3-simple-storage)
- [S3 Control](#s3-control)
- [S3 Glacier](#s3-glacier)
- [S3 Tables](#s3-tables)
- [S3 on Outposts](#s3-on-outposts)
- [SDB (SimpleDB)](#sdb-simpledb)
- [SES (Simple Email)](#ses-simple-email)
- [SESv2 (Simple Email V2)](#sesv2-simple-email-v2)
- [SFN (Step Functions)](#sfn-step-functions)
- [SNS (Simple Notification)](#sns-simple-notification)
- [SQS (Simple Queue)](#sqs-simple-queue)
- [SSM (Systems Manager)](#ssm-systems-manager)
- [SSM Contacts](#ssm-contacts)
- [SSM Incident Manager Incidents](#ssm-incident-manager-incidents)
- [SSM Quick Setup](#ssm-quick-setup)
- [SSO Admin](#sso-admin)
- [SSO Identity Store](#sso-identity-store)
- [STS (Security Token)](#sts-security-token)
- [SWF (Simple Workflow)](#swf-simple-workflow)
- [SageMaker AI](#sagemaker-ai)
- [Secrets Manager](#secrets-manager)
- [Security Hub](#security-hub)
- [Security Lake](#security-lake)
- [Serverless Application Repository](#serverless-application-repository)
- [Service Catalog](#service-catalog)
- [Service Catalog AppRegistry](#service-catalog-appregistry)
- [Service Quotas](#service-quotas)
- [Shield](#shield)
- [Signer](#signer)
- [Storage Gateway](#storage-gateway)
- [Timestream Query](#timestream-query)
- [Timestream Write](#timestream-write)
- [Timestream for InfluxDB](#timestream-for-influxdb)
- [Transcribe](#transcribe)
- [Transfer Family](#transfer-family)
- [Transit Gateway](#transit-gateway)
- [VPC (Virtual Private Cloud)](#vpc-virtual-private-cloud)
- [VPC IPAM (IP Address Manager)](#vpc-ipam-ip-address-manager)
- [VPC Lattice](#vpc-lattice)
- [VPN (Client)](#vpn-client)
- [VPN (Site-to-Site)](#vpn-site-to-site)
- [Verified Access](#verified-access)
- [Verified Permissions](#verified-permissions)
- [WAF](#waf)
- [WAF Classic](#waf-classic)
- [WAF Classic Regional](#waf-classic-regional)
- [Wavelength](#wavelength)
- [Web Services Budgets](#web-services-budgets)
- [WorkLink](#worklink)
- [WorkSpaces](#workspaces)
- [X-Ray](#x-ray)

## ACM Certificate Manager

*2 resources and 1 data sources*

### Resources
- [aws_acm_certificate](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/acm_certificate)
- [aws_acm_certificate_validation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/acm_certificate_validation)

### Data Sources
- [aws_acm_certificate](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/acm_certificate)

## ACM PCA Certificate Manager Private Certificate Authority

*5 resources and 2 data sources*

### Resources
- [aws_acmpca_certificate](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/acmpca_certificate)
- [aws_acmpca_certificate_authority](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/acmpca_certificate_authority)
- [aws_acmpca_certificate_authority_certificate](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/acmpca_certificate_authority_certificate)
- [aws_acmpca_permission](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/acmpca_permission)
- [aws_acmpca_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/acmpca_policy)

### Data Sources
- [aws_acmpca_certificate](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/acmpca_certificate)
- [aws_acmpca_certificate_authority](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/acmpca_certificate_authority)

## AMP Managed Prometheus

*4 resources and 3 data sources*

### Resources
- [aws_prometheus_alert_manager_definition](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/prometheus_alert_manager_definition)
- [aws_prometheus_rule_group_namespace](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/prometheus_rule_group_namespace)
- [aws_prometheus_scraper](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/prometheus_scraper)
- [aws_prometheus_workspace](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/prometheus_workspace)

### Data Sources
- [aws_prometheus_default_scraper_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/prometheus_default_scraper_configuration)
- [aws_prometheus_workspace](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/prometheus_workspace)
- [aws_prometheus_workspaces](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/prometheus_workspaces)

## API Gateway

*26 resources and 10 data sources*

### Resources
- [aws_api_gateway_account](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_account)
- [aws_api_gateway_api_key](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_api_key)
- [aws_api_gateway_authorizer](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_authorizer)
- [aws_api_gateway_base_path_mapping](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_base_path_mapping)
- [aws_api_gateway_client_certificate](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_client_certificate)
- [aws_api_gateway_deployment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_deployment)
- [aws_api_gateway_documentation_part](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_documentation_part)
- [aws_api_gateway_documentation_version](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_documentation_version)
- [aws_api_gateway_domain_name](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_domain_name)
- [aws_api_gateway_domain_name_access_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_domain_name_access_association)
- [aws_api_gateway_gateway_response](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_gateway_response)
- [aws_api_gateway_integration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_integration)
- [aws_api_gateway_integration_response](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_integration_response)
- [aws_api_gateway_method](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_method)
- [aws_api_gateway_method_response](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_method_response)
- [aws_api_gateway_method_settings](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_method_settings)
- [aws_api_gateway_model](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_model)
- [aws_api_gateway_request_validator](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_request_validator)
- [aws_api_gateway_resource](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_resource)
- [aws_api_gateway_rest_api](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_rest_api)
- [aws_api_gateway_rest_api_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_rest_api_policy)
- [aws_api_gateway_rest_api_put](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_rest_api_put)
- [aws_api_gateway_stage](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_stage)
- [aws_api_gateway_usage_plan](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_usage_plan)
- [aws_api_gateway_usage_plan_key](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_usage_plan_key)
- [aws_api_gateway_vpc_link](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_vpc_link)

### Data Sources
- [aws_api_gateway_api_key](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/api_gateway_api_key)
- [aws_api_gateway_api_keys](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/api_gateway_api_keys)
- [aws_api_gateway_authorizer](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/api_gateway_authorizer)
- [aws_api_gateway_authorizers](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/api_gateway_authorizers)
- [aws_api_gateway_domain_name](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/api_gateway_domain_name)
- [aws_api_gateway_export](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/api_gateway_export)
- [aws_api_gateway_resource](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/api_gateway_resource)
- [aws_api_gateway_rest_api](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/api_gateway_rest_api)
- [aws_api_gateway_sdk](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/api_gateway_sdk)
- [aws_api_gateway_vpc_link](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/api_gateway_vpc_link)

## API Gateway V2

*12 resources and 4 data sources*

### Resources
- [aws_apigatewayv2_api](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apigatewayv2_api)
- [aws_apigatewayv2_api_mapping](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apigatewayv2_api_mapping)
- [aws_apigatewayv2_authorizer](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apigatewayv2_authorizer)
- [aws_apigatewayv2_deployment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apigatewayv2_deployment)
- [aws_apigatewayv2_domain_name](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apigatewayv2_domain_name)
- [aws_apigatewayv2_integration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apigatewayv2_integration)
- [aws_apigatewayv2_integration_response](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apigatewayv2_integration_response)
- [aws_apigatewayv2_model](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apigatewayv2_model)
- [aws_apigatewayv2_route](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apigatewayv2_route)
- [aws_apigatewayv2_route_response](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apigatewayv2_route_response)
- [aws_apigatewayv2_stage](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apigatewayv2_stage)
- [aws_apigatewayv2_vpc_link](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apigatewayv2_vpc_link)

### Data Sources
- [aws_apigatewayv2_api](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/apigatewayv2_api)
- [aws_apigatewayv2_apis](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/apigatewayv2_apis)
- [aws_apigatewayv2_export](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/apigatewayv2_export)
- [aws_apigatewayv2_vpc_link](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/apigatewayv2_vpc_link)

## Account Management

*3 resources and 0 data sources*

### Resources
- [aws_account_alternate_contact](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/account_alternate_contact)
- [aws_account_primary_contact](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/account_primary_contact)
- [aws_account_region](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/account_region)

## Amazon Q Business

*1 resources and 0 data sources*

### Resources
- [aws_qbusiness_application](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/qbusiness_application)

## Amplify

*5 resources and 0 data sources*

### Resources
- [aws_amplify_app](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/amplify_app)
- [aws_amplify_backend_environment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/amplify_backend_environment)
- [aws_amplify_branch](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/amplify_branch)
- [aws_amplify_domain_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/amplify_domain_association)
- [aws_amplify_webhook](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/amplify_webhook)

## App Mesh

*7 resources and 7 data sources*

### Resources
- [aws_appmesh_gateway_route](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appmesh_gateway_route)
- [aws_appmesh_mesh](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appmesh_mesh)
- [aws_appmesh_route](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appmesh_route)
- [aws_appmesh_virtual_gateway](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appmesh_virtual_gateway)
- [aws_appmesh_virtual_node](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appmesh_virtual_node)
- [aws_appmesh_virtual_router](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appmesh_virtual_router)
- [aws_appmesh_virtual_service](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appmesh_virtual_service)

### Data Sources
- [aws_appmesh_gateway_route](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/appmesh_gateway_route)
- [aws_appmesh_mesh](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/appmesh_mesh)
- [aws_appmesh_route](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/appmesh_route)
- [aws_appmesh_virtual_gateway](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/appmesh_virtual_gateway)
- [aws_appmesh_virtual_node](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/appmesh_virtual_node)
- [aws_appmesh_virtual_router](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/appmesh_virtual_router)
- [aws_appmesh_virtual_service](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/appmesh_virtual_service)

## App Runner

*9 resources and 1 data sources*

### Resources
- [aws_apprunner_auto_scaling_configuration_version](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apprunner_auto_scaling_configuration_version)
- [aws_apprunner_connection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apprunner_connection)
- [aws_apprunner_custom_domain_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apprunner_custom_domain_association)
- [aws_apprunner_default_auto_scaling_configuration_version](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apprunner_default_auto_scaling_configuration_version)
- [aws_apprunner_deployment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apprunner_deployment)
- [aws_apprunner_observability_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apprunner_observability_configuration)
- [aws_apprunner_service](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apprunner_service)
- [aws_apprunner_vpc_connector](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apprunner_vpc_connector)
- [aws_apprunner_vpc_ingress_connection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apprunner_vpc_ingress_connection)

### Data Sources
- [aws_apprunner_hosted_zone_id](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/apprunner_hosted_zone_id)

## AppConfig

*8 resources and 4 data sources*

### Resources
- [aws_appconfig_application](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appconfig_application)
- [aws_appconfig_configuration_profile](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appconfig_configuration_profile)
- [aws_appconfig_deployment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appconfig_deployment)
- [aws_appconfig_deployment_strategy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appconfig_deployment_strategy)
- [aws_appconfig_environment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appconfig_environment)
- [aws_appconfig_extension](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appconfig_extension)
- [aws_appconfig_extension_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appconfig_extension_association)
- [aws_appconfig_hosted_configuration_version](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appconfig_hosted_configuration_version)

### Data Sources
- [aws_appconfig_configuration_profile](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/appconfig_configuration_profile)
- [aws_appconfig_configuration_profiles](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/appconfig_configuration_profiles)
- [aws_appconfig_environment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/appconfig_environment)
- [aws_appconfig_environments](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/appconfig_environments)

## AppFabric

*5 resources and 0 data sources*

### Resources
- [aws_appfabric_app_authorization](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appfabric_app_authorization)
- [aws_appfabric_app_authorization_connection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appfabric_app_authorization_connection)
- [aws_appfabric_app_bundle](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appfabric_app_bundle)
- [aws_appfabric_ingestion](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appfabric_ingestion)
- [aws_appfabric_ingestion_destination](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appfabric_ingestion_destination)

## AppFlow

*2 resources and 0 data sources*

### Resources
- [aws_appflow_connector_profile](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appflow_connector_profile)
- [aws_appflow_flow](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appflow_flow)

## AppIntegrations

*2 resources and 1 data sources*

### Resources
- [aws_appintegrations_data_integration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appintegrations_data_integration)
- [aws_appintegrations_event_integration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appintegrations_event_integration)

### Data Sources
- [aws_appintegrations_event_integration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/appintegrations_event_integration)

## AppStream 2.0

*7 resources and 1 data sources*

### Resources
- [aws_appstream_directory_config](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appstream_directory_config)
- [aws_appstream_fleet](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appstream_fleet)
- [aws_appstream_fleet_stack_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appstream_fleet_stack_association)
- [aws_appstream_image_builder](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appstream_image_builder)
- [aws_appstream_stack](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appstream_stack)
- [aws_appstream_user](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appstream_user)
- [aws_appstream_user_stack_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appstream_user_stack_association)

### Data Sources
- [aws_appstream_image](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/appstream_image)

## AppSync

*10 resources and 0 data sources*

### Resources
- [aws_appsync_api_cache](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appsync_api_cache)
- [aws_appsync_api_key](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appsync_api_key)
- [aws_appsync_datasource](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appsync_datasource)
- [aws_appsync_domain_name](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appsync_domain_name)
- [aws_appsync_domain_name_api_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appsync_domain_name_api_association)
- [aws_appsync_function](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appsync_function)
- [aws_appsync_graphql_api](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appsync_graphql_api)
- [aws_appsync_resolver](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appsync_resolver)
- [aws_appsync_source_api_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appsync_source_api_association)
- [aws_appsync_type](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appsync_type)

## Application Auto Scaling

*3 resources and 0 data sources*

### Resources
- [aws_appautoscaling_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appautoscaling_policy)
- [aws_appautoscaling_scheduled_action](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appautoscaling_scheduled_action)
- [aws_appautoscaling_target](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/appautoscaling_target)

## Athena

*6 resources and 1 data sources*

### Resources
- [aws_athena_capacity_reservation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/athena_capacity_reservation)
- [aws_athena_data_catalog](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/athena_data_catalog)
- [aws_athena_database](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/athena_database)
- [aws_athena_named_query](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/athena_named_query)
- [aws_athena_prepared_statement](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/athena_prepared_statement)
- [aws_athena_workgroup](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/athena_workgroup)

### Data Sources
- [aws_athena_named_query](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/athena_named_query)

## Audit Manager

*8 resources and 2 data sources*

### Resources
- [aws_auditmanager_account_registration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/auditmanager_account_registration)
- [aws_auditmanager_assessment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/auditmanager_assessment)
- [aws_auditmanager_assessment_delegation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/auditmanager_assessment_delegation)
- [aws_auditmanager_assessment_report](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/auditmanager_assessment_report)
- [aws_auditmanager_control](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/auditmanager_control)
- [aws_auditmanager_framework](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/auditmanager_framework)
- [aws_auditmanager_framework_share](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/auditmanager_framework_share)
- [aws_auditmanager_organization_admin_account_registration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/auditmanager_organization_admin_account_registration)

### Data Sources
- [aws_auditmanager_control](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/auditmanager_control)
- [aws_auditmanager_framework](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/auditmanager_framework)

## Auto Scaling

*9 resources and 3 data sources*

### Resources
- [aws_autoscaling_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/autoscaling_attachment)
- [aws_autoscaling_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/autoscaling_group)
- [aws_autoscaling_group_tag](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/autoscaling_group_tag)
- [aws_autoscaling_lifecycle_hook](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/autoscaling_lifecycle_hook)
- [aws_autoscaling_notification](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/autoscaling_notification)
- [aws_autoscaling_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/autoscaling_policy)
- [aws_autoscaling_schedule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/autoscaling_schedule)
- [aws_autoscaling_traffic_source_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/autoscaling_traffic_source_attachment)
- [aws_launch_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/launch_configuration)

### Data Sources
- [aws_autoscaling_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/autoscaling_group)
- [aws_autoscaling_groups](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/autoscaling_groups)
- [aws_launch_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/launch_configuration)

## Auto Scaling Plans

*1 resources and 0 data sources*

### Resources
- [aws_autoscalingplans_scaling_plan](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/autoscalingplans_scaling_plan)

## BCM Data Exports

*1 resources and 0 data sources*

### Resources
- [aws_bcmdataexports_export](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bcmdataexports_export)

## Backup

*13 resources and 5 data sources*

### Resources
- [aws_backup_framework](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/backup_framework)
- [aws_backup_global_settings](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/backup_global_settings)
- [aws_backup_logically_air_gapped_vault](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/backup_logically_air_gapped_vault)
- [aws_backup_plan](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/backup_plan)
- [aws_backup_region_settings](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/backup_region_settings)
- [aws_backup_report_plan](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/backup_report_plan)
- [aws_backup_restore_testing_plan](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/backup_restore_testing_plan)
- [aws_backup_restore_testing_selection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/backup_restore_testing_selection)
- [aws_backup_selection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/backup_selection)
- [aws_backup_vault](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/backup_vault)
- [aws_backup_vault_lock_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/backup_vault_lock_configuration)
- [aws_backup_vault_notifications](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/backup_vault_notifications)
- [aws_backup_vault_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/backup_vault_policy)

### Data Sources
- [aws_backup_framework](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/backup_framework)
- [aws_backup_plan](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/backup_plan)
- [aws_backup_report_plan](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/backup_report_plan)
- [aws_backup_selection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/backup_selection)
- [aws_backup_vault](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/backup_vault)

## Batch

*4 resources and 4 data sources*

### Resources
- [aws_batch_compute_environment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/batch_compute_environment)
- [aws_batch_job_definition](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/batch_job_definition)
- [aws_batch_job_queue](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/batch_job_queue)
- [aws_batch_scheduling_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/batch_scheduling_policy)

### Data Sources
- [aws_batch_compute_environment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/batch_compute_environment)
- [aws_batch_job_definition](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/batch_job_definition)
- [aws_batch_job_queue](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/batch_job_queue)
- [aws_batch_scheduling_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/batch_scheduling_policy)

## Bedrock

*6 resources and 6 data sources*

### Resources
- [aws_bedrock_custom_model](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrock_custom_model)
- [aws_bedrock_guardrail](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrock_guardrail)
- [aws_bedrock_guardrail_version](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrock_guardrail_version)
- [aws_bedrock_inference_profile](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrock_inference_profile)
- [aws_bedrock_model_invocation_logging_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrock_model_invocation_logging_configuration)
- [aws_bedrock_provisioned_model_throughput](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrock_provisioned_model_throughput)

### Data Sources
- [aws_bedrock_custom_model](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/bedrock_custom_model)
- [aws_bedrock_custom_models](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/bedrock_custom_models)
- [aws_bedrock_foundation_model](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/bedrock_foundation_model)
- [aws_bedrock_foundation_models](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/bedrock_foundation_models)
- [aws_bedrock_inference_profile](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/bedrock_inference_profile)
- [aws_bedrock_inference_profiles](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/bedrock_inference_profiles)

## Bedrock Agents

*7 resources and 1 data sources*

### Resources
- [aws_bedrockagent_agent](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrockagent_agent)
- [aws_bedrockagent_agent_action_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrockagent_agent_action_group)
- [aws_bedrockagent_agent_alias](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrockagent_agent_alias)
- [aws_bedrockagent_agent_collaborator](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrockagent_agent_collaborator)
- [aws_bedrockagent_agent_knowledge_base_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrockagent_agent_knowledge_base_association)
- [aws_bedrockagent_data_source](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrockagent_data_source)
- [aws_bedrockagent_knowledge_base](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrockagent_knowledge_base)

### Data Sources
- [aws_bedrockagent_agent_versions](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/bedrockagent_agent_versions)

## Billing

*0 resources and 1 data sources*


### Data Sources
- [aws_billing_service_account](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/billing_service_account)

## CE Cost Explorer

*4 resources and 2 data sources*

### Resources
- [aws_ce_anomaly_monitor](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ce_anomaly_monitor)
- [aws_ce_anomaly_subscription](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ce_anomaly_subscription)
- [aws_ce_cost_allocation_tag](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ce_cost_allocation_tag)
- [aws_ce_cost_category](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ce_cost_category)

### Data Sources
- [aws_ce_cost_category](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ce_cost_category)
- [aws_ce_tags](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ce_tags)

## Chatbot

*2 resources and 1 data sources*

### Resources
- [aws_chatbot_slack_channel_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/chatbot_slack_channel_configuration)
- [aws_chatbot_teams_channel_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/chatbot_teams_channel_configuration)

### Data Sources
- [aws_chatbot_slack_workspace](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/chatbot_slack_workspace)

## Chime

*7 resources and 0 data sources*

### Resources
- [aws_chime_voice_connector](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/chime_voice_connector)
- [aws_chime_voice_connector_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/chime_voice_connector_group)
- [aws_chime_voice_connector_logging](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/chime_voice_connector_logging)
- [aws_chime_voice_connector_origination](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/chime_voice_connector_origination)
- [aws_chime_voice_connector_streaming](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/chime_voice_connector_streaming)
- [aws_chime_voice_connector_termination](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/chime_voice_connector_termination)
- [aws_chime_voice_connector_termination_credentials](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/chime_voice_connector_termination_credentials)

## Chime SDK Media Pipelines

*1 resources and 0 data sources*

### Resources
- [aws_chimesdkmediapipelines_media_insights_pipeline_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/chimesdkmediapipelines_media_insights_pipeline_configuration)

## Chime SDK Voice

*4 resources and 0 data sources*

### Resources
- [aws_chimesdkvoice_global_settings](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/chimesdkvoice_global_settings)
- [aws_chimesdkvoice_sip_media_application](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/chimesdkvoice_sip_media_application)
- [aws_chimesdkvoice_sip_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/chimesdkvoice_sip_rule)
- [aws_chimesdkvoice_voice_profile_domain](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/chimesdkvoice_voice_profile_domain)

## Clean Rooms

*3 resources and 0 data sources*

### Resources
- [aws_cleanrooms_collaboration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cleanrooms_collaboration)
- [aws_cleanrooms_configured_table](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cleanrooms_configured_table)
- [aws_cleanrooms_membership](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cleanrooms_membership)

## Cloud Control API

*1 resources and 1 data sources*

### Resources
- [aws_cloudcontrolapi_resource](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudcontrolapi_resource)

### Data Sources
- [aws_cloudcontrolapi_resource](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cloudcontrolapi_resource)

## Cloud Map

*5 resources and 3 data sources*

### Resources
- [aws_service_discovery_http_namespace](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/service_discovery_http_namespace)
- [aws_service_discovery_instance](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/service_discovery_instance)
- [aws_service_discovery_private_dns_namespace](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/service_discovery_private_dns_namespace)
- [aws_service_discovery_public_dns_namespace](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/service_discovery_public_dns_namespace)
- [aws_service_discovery_service](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/service_discovery_service)

### Data Sources
- [aws_service_discovery_dns_namespace](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/service_discovery_dns_namespace)
- [aws_service_discovery_http_namespace](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/service_discovery_http_namespace)
- [aws_service_discovery_service](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/service_discovery_service)

## Cloud9

*2 resources and 0 data sources*

### Resources
- [aws_cloud9_environment_ec2](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloud9_environment_ec2)
- [aws_cloud9_environment_membership](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloud9_environment_membership)

## CloudFormation

*5 resources and 3 data sources*

### Resources
- [aws_cloudformation_stack](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudformation_stack)
- [aws_cloudformation_stack_instances](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudformation_stack_instances)
- [aws_cloudformation_stack_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudformation_stack_set)
- [aws_cloudformation_stack_set_instance](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudformation_stack_set_instance)
- [aws_cloudformation_type](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudformation_type)

### Data Sources
- [aws_cloudformation_export](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cloudformation_export)
- [aws_cloudformation_stack](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cloudformation_stack)
- [aws_cloudformation_type](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cloudformation_type)

## CloudFront

*16 resources and 10 data sources*

### Resources
- [aws_cloudfront_cache_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfront_cache_policy)
- [aws_cloudfront_continuous_deployment_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfront_continuous_deployment_policy)
- [aws_cloudfront_distribution](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfront_distribution)
- [aws_cloudfront_field_level_encryption_config](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfront_field_level_encryption_config)
- [aws_cloudfront_field_level_encryption_profile](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfront_field_level_encryption_profile)
- [aws_cloudfront_function](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfront_function)
- [aws_cloudfront_key_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfront_key_group)
- [aws_cloudfront_key_value_store](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfront_key_value_store)
- [aws_cloudfront_monitoring_subscription](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfront_monitoring_subscription)
- [aws_cloudfront_origin_access_control](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfront_origin_access_control)
- [aws_cloudfront_origin_access_identity](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfront_origin_access_identity)
- [aws_cloudfront_origin_request_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfront_origin_request_policy)
- [aws_cloudfront_public_key](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfront_public_key)
- [aws_cloudfront_realtime_log_config](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfront_realtime_log_config)
- [aws_cloudfront_response_headers_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfront_response_headers_policy)
- [aws_cloudfront_vpc_origin](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfront_vpc_origin)

### Data Sources
- [aws_cloudfront_cache_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cloudfront_cache_policy)
- [aws_cloudfront_distribution](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cloudfront_distribution)
- [aws_cloudfront_function](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cloudfront_function)
- [aws_cloudfront_log_delivery_canonical_user_id](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cloudfront_log_delivery_canonical_user_id)
- [aws_cloudfront_origin_access_control](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cloudfront_origin_access_control)
- [aws_cloudfront_origin_access_identities](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cloudfront_origin_access_identities)
- [aws_cloudfront_origin_access_identity](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cloudfront_origin_access_identity)
- [aws_cloudfront_origin_request_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cloudfront_origin_request_policy)
- [aws_cloudfront_realtime_log_config](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cloudfront_realtime_log_config)
- [aws_cloudfront_response_headers_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cloudfront_response_headers_policy)

## CloudFront KeyValueStore

*1 resources and 0 data sources*

### Resources
- [aws_cloudfrontkeyvaluestore_key](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfrontkeyvaluestore_key)

## CloudHSM

*2 resources and 1 data sources*

### Resources
- [aws_cloudhsm_v2_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudhsm_v2_cluster)
- [aws_cloudhsm_v2_hsm](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudhsm_v2_hsm)

### Data Sources
- [aws_cloudhsm_v2_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cloudhsm_v2_cluster)

## CloudSearch

*2 resources and 0 data sources*

### Resources
- [aws_cloudsearch_domain](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudsearch_domain)
- [aws_cloudsearch_domain_service_access_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudsearch_domain_service_access_policy)

## CloudTrail

*3 resources and 1 data sources*

### Resources
- [aws_cloudtrail](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudtrail)
- [aws_cloudtrail_event_data_store](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudtrail_event_data_store)
- [aws_cloudtrail_organization_delegated_admin_account](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudtrail_organization_delegated_admin_account)

### Data Sources
- [aws_cloudtrail_service_account](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cloudtrail_service_account)

## CloudWatch

*6 resources and 1 data sources*

### Resources
- [aws_cloudwatch_composite_alarm](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_composite_alarm)
- [aws_cloudwatch_contributor_insight_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_contributor_insight_rule)
- [aws_cloudwatch_contributor_managed_insight_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_contributor_managed_insight_rule)
- [aws_cloudwatch_dashboard](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_dashboard)
- [aws_cloudwatch_metric_alarm](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_metric_alarm)
- [aws_cloudwatch_metric_stream](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_metric_stream)

### Data Sources
- [aws_cloudwatch_contributor_managed_insight_rules](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cloudwatch_contributor_managed_insight_rules)

## CloudWatch Application Insights

*1 resources and 0 data sources*

### Resources
- [aws_applicationinsights_application](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/applicationinsights_application)

## CloudWatch Evidently

*4 resources and 0 data sources*

### Resources
- [aws_evidently_feature](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/evidently_feature)
- [aws_evidently_launch](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/evidently_launch)
- [aws_evidently_project](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/evidently_project)
- [aws_evidently_segment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/evidently_segment)

## CloudWatch Internet Monitor

*1 resources and 0 data sources*

### Resources
- [aws_internetmonitor_monitor](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/internetmonitor_monitor)

## CloudWatch Logs

*16 resources and 3 data sources*

### Resources
- [aws_cloudwatch_log_account_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_account_policy)
- [aws_cloudwatch_log_anomaly_detector](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_anomaly_detector)
- [aws_cloudwatch_log_data_protection_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_data_protection_policy)
- [aws_cloudwatch_log_delivery](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_delivery)
- [aws_cloudwatch_log_delivery_destination](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_delivery_destination)
- [aws_cloudwatch_log_delivery_destination_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_delivery_destination_policy)
- [aws_cloudwatch_log_delivery_source](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_delivery_source)
- [aws_cloudwatch_log_destination](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_destination)
- [aws_cloudwatch_log_destination_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_destination_policy)
- [aws_cloudwatch_log_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_group)
- [aws_cloudwatch_log_index_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_index_policy)
- [aws_cloudwatch_log_metric_filter](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_metric_filter)
- [aws_cloudwatch_log_resource_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_resource_policy)
- [aws_cloudwatch_log_stream](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_stream)
- [aws_cloudwatch_log_subscription_filter](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_subscription_filter)
- [aws_cloudwatch_query_definition](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_query_definition)

### Data Sources
- [aws_cloudwatch_log_data_protection_policy_document](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cloudwatch_log_data_protection_policy_document)
- [aws_cloudwatch_log_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cloudwatch_log_group)
- [aws_cloudwatch_log_groups](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cloudwatch_log_groups)

## CloudWatch Network Monitor

*2 resources and 0 data sources*

### Resources
- [aws_networkmonitor_monitor](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/networkmonitor_monitor)
- [aws_networkmonitor_probe](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/networkmonitor_probe)

## CloudWatch Observability Access Manager

*3 resources and 4 data sources*

### Resources
- [aws_oam_link](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/oam_link)
- [aws_oam_sink](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/oam_sink)
- [aws_oam_sink_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/oam_sink_policy)

### Data Sources
- [aws_oam_link](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/oam_link)
- [aws_oam_links](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/oam_links)
- [aws_oam_sink](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/oam_sink)
- [aws_oam_sinks](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/oam_sinks)

## CloudWatch RUM

*2 resources and 0 data sources*

### Resources
- [aws_rum_app_monitor](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/rum_app_monitor)
- [aws_rum_metrics_destination](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/rum_metrics_destination)

## CloudWatch Synthetics

*3 resources and 2 data sources*

### Resources
- [aws_synthetics_canary](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/synthetics_canary)
- [aws_synthetics_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/synthetics_group)
- [aws_synthetics_group_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/synthetics_group_association)

### Data Sources
- [aws_synthetics_runtime_version](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/synthetics_runtime_version)
- [aws_synthetics_runtime_versions](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/synthetics_runtime_versions)

## CodeArtifact

*4 resources and 2 data sources*

### Resources
- [aws_codeartifact_domain](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codeartifact_domain)
- [aws_codeartifact_domain_permissions_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codeartifact_domain_permissions_policy)
- [aws_codeartifact_repository](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codeartifact_repository)
- [aws_codeartifact_repository_permissions_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codeartifact_repository_permissions_policy)

### Data Sources
- [aws_codeartifact_authorization_token](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/codeartifact_authorization_token)
- [aws_codeartifact_repository_endpoint](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/codeartifact_repository_endpoint)

## CodeBuild

*6 resources and 1 data sources*

### Resources
- [aws_codebuild_fleet](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codebuild_fleet)
- [aws_codebuild_project](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codebuild_project)
- [aws_codebuild_report_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codebuild_report_group)
- [aws_codebuild_resource_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codebuild_resource_policy)
- [aws_codebuild_source_credential](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codebuild_source_credential)
- [aws_codebuild_webhook](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codebuild_webhook)

### Data Sources
- [aws_codebuild_fleet](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/codebuild_fleet)

## CodeCatalyst

*3 resources and 1 data sources*

### Resources
- [aws_codecatalyst_dev_environment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codecatalyst_dev_environment)
- [aws_codecatalyst_project](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codecatalyst_project)
- [aws_codecatalyst_source_repository](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codecatalyst_source_repository)

### Data Sources
- [aws_codecatalyst_dev_environment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/codecatalyst_dev_environment)

## CodeCommit

*4 resources and 2 data sources*

### Resources
- [aws_codecommit_approval_rule_template](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codecommit_approval_rule_template)
- [aws_codecommit_approval_rule_template_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codecommit_approval_rule_template_association)
- [aws_codecommit_repository](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codecommit_repository)
- [aws_codecommit_trigger](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codecommit_trigger)

### Data Sources
- [aws_codecommit_approval_rule_template](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/codecommit_approval_rule_template)
- [aws_codecommit_repository](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/codecommit_repository)

## CodeConnections

*2 resources and 0 data sources*

### Resources
- [aws_codeconnections_connection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codeconnections_connection)
- [aws_codeconnections_host](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codeconnections_host)

## CodeDeploy

*3 resources and 0 data sources*

### Resources
- [aws_codedeploy_app](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codedeploy_app)
- [aws_codedeploy_deployment_config](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codedeploy_deployment_config)
- [aws_codedeploy_deployment_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codedeploy_deployment_group)

## CodeGuru Profiler

*1 resources and 1 data sources*

### Resources
- [aws_codeguruprofiler_profiling_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codeguruprofiler_profiling_group)

### Data Sources
- [aws_codeguruprofiler_profiling_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/codeguruprofiler_profiling_group)

## CodeGuru Reviewer

*1 resources and 0 data sources*

### Resources
- [aws_codegurureviewer_repository_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codegurureviewer_repository_association)

## CodePipeline

*3 resources and 0 data sources*

### Resources
- [aws_codepipeline](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codepipeline)
- [aws_codepipeline_custom_action_type](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codepipeline_custom_action_type)
- [aws_codepipeline_webhook](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codepipeline_webhook)

## CodeStar Connections

*2 resources and 1 data sources*

### Resources
- [aws_codestarconnections_connection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codestarconnections_connection)
- [aws_codestarconnections_host](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codestarconnections_host)

### Data Sources
- [aws_codestarconnections_connection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/codestarconnections_connection)

## CodeStar Notifications

*1 resources and 0 data sources*

### Resources
- [aws_codestarnotifications_notification_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/codestarnotifications_notification_rule)

## Cognito IDP Identity Provider

*11 resources and 7 data sources*

### Resources
- [aws_cognito_identity_provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_identity_provider)
- [aws_cognito_managed_user_pool_client](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_managed_user_pool_client)
- [aws_cognito_resource_server](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_resource_server)
- [aws_cognito_risk_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_risk_configuration)
- [aws_cognito_user](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_user)
- [aws_cognito_user_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_user_group)
- [aws_cognito_user_in_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_user_in_group)
- [aws_cognito_user_pool](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_user_pool)
- [aws_cognito_user_pool_client](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_user_pool_client)
- [aws_cognito_user_pool_domain](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_user_pool_domain)
- [aws_cognito_user_pool_ui_customization](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_user_pool_ui_customization)

### Data Sources
- [aws_cognito_user_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cognito_user_group)
- [aws_cognito_user_groups](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cognito_user_groups)
- [aws_cognito_user_pool](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cognito_user_pool)
- [aws_cognito_user_pool_client](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cognito_user_pool_client)
- [aws_cognito_user_pool_clients](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cognito_user_pool_clients)
- [aws_cognito_user_pool_signing_certificate](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cognito_user_pool_signing_certificate)
- [aws_cognito_user_pools](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cognito_user_pools)

## Cognito Identity

*3 resources and 1 data sources*

### Resources
- [aws_cognito_identity_pool](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_identity_pool)
- [aws_cognito_identity_pool_provider_principal_tag](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_identity_pool_provider_principal_tag)
- [aws_cognito_identity_pool_roles_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_identity_pool_roles_attachment)

### Data Sources
- [aws_cognito_identity_pool](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cognito_identity_pool)

## Comprehend

*2 resources and 0 data sources*

### Resources
- [aws_comprehend_document_classifier](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/comprehend_document_classifier)
- [aws_comprehend_entity_recognizer](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/comprehend_entity_recognizer)

## Compute Optimizer

*2 resources and 0 data sources*

### Resources
- [aws_computeoptimizer_enrollment_status](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/computeoptimizer_enrollment_status)
- [aws_computeoptimizer_recommendation_preferences](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/computeoptimizer_recommendation_preferences)

## Config

*13 resources and 0 data sources*

### Resources
- [aws_config_aggregate_authorization](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/config_aggregate_authorization)
- [aws_config_config_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/config_config_rule)
- [aws_config_configuration_aggregator](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/config_configuration_aggregator)
- [aws_config_configuration_recorder](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/config_configuration_recorder)
- [aws_config_configuration_recorder_status](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/config_configuration_recorder_status)
- [aws_config_conformance_pack](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/config_conformance_pack)
- [aws_config_delivery_channel](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/config_delivery_channel)
- [aws_config_organization_conformance_pack](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/config_organization_conformance_pack)
- [aws_config_organization_custom_policy_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/config_organization_custom_policy_rule)
- [aws_config_organization_custom_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/config_organization_custom_rule)
- [aws_config_organization_managed_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/config_organization_managed_rule)
- [aws_config_remediation_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/config_remediation_configuration)
- [aws_config_retention_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/config_retention_configuration)

## Connect

*16 resources and 16 data sources*

### Resources
- [aws_connect_bot_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/connect_bot_association)
- [aws_connect_contact_flow](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/connect_contact_flow)
- [aws_connect_contact_flow_module](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/connect_contact_flow_module)
- [aws_connect_hours_of_operation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/connect_hours_of_operation)
- [aws_connect_instance](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/connect_instance)
- [aws_connect_instance_storage_config](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/connect_instance_storage_config)
- [aws_connect_lambda_function_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/connect_lambda_function_association)
- [aws_connect_phone_number](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/connect_phone_number)
- [aws_connect_queue](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/connect_queue)
- [aws_connect_quick_connect](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/connect_quick_connect)
- [aws_connect_routing_profile](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/connect_routing_profile)
- [aws_connect_security_profile](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/connect_security_profile)
- [aws_connect_user](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/connect_user)
- [aws_connect_user_hierarchy_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/connect_user_hierarchy_group)
- [aws_connect_user_hierarchy_structure](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/connect_user_hierarchy_structure)
- [aws_connect_vocabulary](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/connect_vocabulary)

### Data Sources
- [aws_connect_bot_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/connect_bot_association)
- [aws_connect_contact_flow](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/connect_contact_flow)
- [aws_connect_contact_flow_module](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/connect_contact_flow_module)
- [aws_connect_hours_of_operation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/connect_hours_of_operation)
- [aws_connect_instance](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/connect_instance)
- [aws_connect_instance_storage_config](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/connect_instance_storage_config)
- [aws_connect_lambda_function_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/connect_lambda_function_association)
- [aws_connect_prompt](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/connect_prompt)
- [aws_connect_queue](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/connect_queue)
- [aws_connect_quick_connect](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/connect_quick_connect)
- [aws_connect_routing_profile](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/connect_routing_profile)
- [aws_connect_security_profile](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/connect_security_profile)
- [aws_connect_user](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/connect_user)
- [aws_connect_user_hierarchy_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/connect_user_hierarchy_group)
- [aws_connect_user_hierarchy_structure](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/connect_user_hierarchy_structure)
- [aws_connect_vocabulary](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/connect_vocabulary)

## Connect Customer Profiles

*2 resources and 0 data sources*

### Resources
- [aws_customerprofiles_domain](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/customerprofiles_domain)
- [aws_customerprofiles_profile](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/customerprofiles_profile)

## Control Tower

*2 resources and 1 data sources*

### Resources
- [aws_controltower_control](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/controltower_control)
- [aws_controltower_landing_zone](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/controltower_landing_zone)

### Data Sources
- [aws_controltower_controls](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/controltower_controls)

## Cost Optimization Hub

*2 resources and 0 data sources*

### Resources
- [aws_costoptimizationhub_enrollment_status](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/costoptimizationhub_enrollment_status)
- [aws_costoptimizationhub_preferences](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/costoptimizationhub_preferences)

## Cost and Usage Report

*1 resources and 1 data sources*

### Resources
- [aws_cur_report_definition](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cur_report_definition)

### Data Sources
- [aws_cur_report_definition](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cur_report_definition)

## DLM Data Lifecycle Manager

*1 resources and 0 data sources*

### Resources
- [aws_dlm_lifecycle_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dlm_lifecycle_policy)

## DMS Database Migration

*8 resources and 5 data sources*

### Resources
- [aws_dms_certificate](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dms_certificate)
- [aws_dms_endpoint](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dms_endpoint)
- [aws_dms_event_subscription](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dms_event_subscription)
- [aws_dms_replication_config](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dms_replication_config)
- [aws_dms_replication_instance](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dms_replication_instance)
- [aws_dms_replication_subnet_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dms_replication_subnet_group)
- [aws_dms_replication_task](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dms_replication_task)
- [aws_dms_s3_endpoint](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dms_s3_endpoint)

### Data Sources
- [aws_dms_certificate](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/dms_certificate)
- [aws_dms_endpoint](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/dms_endpoint)
- [aws_dms_replication_instance](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/dms_replication_instance)
- [aws_dms_replication_subnet_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/dms_replication_subnet_group)
- [aws_dms_replication_task](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/dms_replication_task)

## DRS Elastic Disaster Recovery

*1 resources and 0 data sources*

### Resources
- [aws_drs_replication_configuration_template](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/drs_replication_configuration_template)

## Data Exchange

*3 resources and 0 data sources*

### Resources
- [aws_dataexchange_data_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dataexchange_data_set)
- [aws_dataexchange_event_action](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dataexchange_event_action)
- [aws_dataexchange_revision](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dataexchange_revision)

## Data Pipeline

*2 resources and 2 data sources*

### Resources
- [aws_datapipeline_pipeline](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/datapipeline_pipeline)
- [aws_datapipeline_pipeline_definition](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/datapipeline_pipeline_definition)

### Data Sources
- [aws_datapipeline_pipeline](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/datapipeline_pipeline)
- [aws_datapipeline_pipeline_definition](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/datapipeline_pipeline_definition)

## DataSync

*13 resources and 0 data sources*

### Resources
- [aws_datasync_agent](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/datasync_agent)
- [aws_datasync_location_azure_blob](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/datasync_location_azure_blob)
- [aws_datasync_location_efs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/datasync_location_efs)
- [aws_datasync_location_fsx_lustre_file_system](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/datasync_location_fsx_lustre_file_system)
- [aws_datasync_location_fsx_ontap_file_system](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/datasync_location_fsx_ontap_file_system)
- [aws_datasync_location_fsx_openzfs_file_system](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/datasync_location_fsx_openzfs_file_system)
- [aws_datasync_location_fsx_windows_file_system](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/datasync_location_fsx_windows_file_system)
- [aws_datasync_location_hdfs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/datasync_location_hdfs)
- [aws_datasync_location_nfs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/datasync_location_nfs)
- [aws_datasync_location_object_storage](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/datasync_location_object_storage)
- [aws_datasync_location_s3](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/datasync_location_s3)
- [aws_datasync_location_smb](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/datasync_location_smb)
- [aws_datasync_task](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/datasync_task)

## DataZone

*10 resources and 2 data sources*

### Resources
- [aws_datazone_asset_type](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/datazone_asset_type)
- [aws_datazone_domain](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/datazone_domain)
- [aws_datazone_environment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/datazone_environment)
- [aws_datazone_environment_blueprint_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/datazone_environment_blueprint_configuration)
- [aws_datazone_environment_profile](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/datazone_environment_profile)
- [aws_datazone_form_type](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/datazone_form_type)
- [aws_datazone_glossary](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/datazone_glossary)
- [aws_datazone_glossary_term](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/datazone_glossary_term)
- [aws_datazone_project](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/datazone_project)
- [aws_datazone_user_profile](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/datazone_user_profile)

### Data Sources
- [aws_datazone_domain](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/datazone_domain)
- [aws_datazone_environment_blueprint](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/datazone_environment_blueprint)

## Detective

*5 resources and 0 data sources*

### Resources
- [aws_detective_graph](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/detective_graph)
- [aws_detective_invitation_accepter](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/detective_invitation_accepter)
- [aws_detective_member](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/detective_member)
- [aws_detective_organization_admin_account](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/detective_organization_admin_account)
- [aws_detective_organization_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/detective_organization_configuration)

## DevOps Guru

*4 resources and 2 data sources*

### Resources
- [aws_devopsguru_event_sources_config](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/devopsguru_event_sources_config)
- [aws_devopsguru_notification_channel](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/devopsguru_notification_channel)
- [aws_devopsguru_resource_collection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/devopsguru_resource_collection)
- [aws_devopsguru_service_integration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/devopsguru_service_integration)

### Data Sources
- [aws_devopsguru_notification_channel](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/devopsguru_notification_channel)
- [aws_devopsguru_resource_collection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/devopsguru_resource_collection)

## Device Farm

*6 resources and 0 data sources*

### Resources
- [aws_devicefarm_device_pool](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/devicefarm_device_pool)
- [aws_devicefarm_instance_profile](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/devicefarm_instance_profile)
- [aws_devicefarm_network_profile](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/devicefarm_network_profile)
- [aws_devicefarm_project](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/devicefarm_project)
- [aws_devicefarm_test_grid_project](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/devicefarm_test_grid_project)
- [aws_devicefarm_upload](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/devicefarm_upload)

## Direct Connect

*19 resources and 5 data sources*

### Resources
- [aws_dx_bgp_peer](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dx_bgp_peer)
- [aws_dx_connection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dx_connection)
- [aws_dx_connection_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dx_connection_association)
- [aws_dx_connection_confirmation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dx_connection_confirmation)
- [aws_dx_gateway](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dx_gateway)
- [aws_dx_gateway_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dx_gateway_association)
- [aws_dx_gateway_association_proposal](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dx_gateway_association_proposal)
- [aws_dx_hosted_connection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dx_hosted_connection)
- [aws_dx_hosted_private_virtual_interface](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dx_hosted_private_virtual_interface)
- [aws_dx_hosted_private_virtual_interface_accepter](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dx_hosted_private_virtual_interface_accepter)
- [aws_dx_hosted_public_virtual_interface](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dx_hosted_public_virtual_interface)
- [aws_dx_hosted_public_virtual_interface_accepter](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dx_hosted_public_virtual_interface_accepter)
- [aws_dx_hosted_transit_virtual_interface](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dx_hosted_transit_virtual_interface)
- [aws_dx_hosted_transit_virtual_interface_accepter](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dx_hosted_transit_virtual_interface_accepter)
- [aws_dx_lag](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dx_lag)
- [aws_dx_macsec_key_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dx_macsec_key_association)
- [aws_dx_private_virtual_interface](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dx_private_virtual_interface)
- [aws_dx_public_virtual_interface](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dx_public_virtual_interface)
- [aws_dx_transit_virtual_interface](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dx_transit_virtual_interface)

### Data Sources
- [aws_dx_connection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/dx_connection)
- [aws_dx_gateway](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/dx_gateway)
- [aws_dx_location](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/dx_location)
- [aws_dx_locations](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/dx_locations)
- [aws_dx_router_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/dx_router_configuration)

## Directory Service

*8 resources and 1 data sources*

### Resources
- [aws_directory_service_conditional_forwarder](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/directory_service_conditional_forwarder)
- [aws_directory_service_directory](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/directory_service_directory)
- [aws_directory_service_log_subscription](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/directory_service_log_subscription)
- [aws_directory_service_radius_settings](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/directory_service_radius_settings)
- [aws_directory_service_region](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/directory_service_region)
- [aws_directory_service_shared_directory](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/directory_service_shared_directory)
- [aws_directory_service_shared_directory_accepter](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/directory_service_shared_directory_accepter)
- [aws_directory_service_trust](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/directory_service_trust)

### Data Sources
- [aws_directory_service_directory](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/directory_service_directory)

## DocumentDB

*7 resources and 2 data sources*

### Resources
- [aws_docdb_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/docdb_cluster)
- [aws_docdb_cluster_instance](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/docdb_cluster_instance)
- [aws_docdb_cluster_parameter_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/docdb_cluster_parameter_group)
- [aws_docdb_cluster_snapshot](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/docdb_cluster_snapshot)
- [aws_docdb_event_subscription](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/docdb_event_subscription)
- [aws_docdb_global_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/docdb_global_cluster)
- [aws_docdb_subnet_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/docdb_subnet_group)

### Data Sources
- [aws_docdb_engine_version](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/docdb_engine_version)
- [aws_docdb_orderable_db_instance](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/docdb_orderable_db_instance)

## DocumentDB Elastic

*1 resources and 0 data sources*

### Resources
- [aws_docdbelastic_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/docdbelastic_cluster)

## DynamoDB

*9 resources and 2 data sources*

### Resources
- [aws_dynamodb_contributor_insights](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dynamodb_contributor_insights)
- [aws_dynamodb_global_table](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dynamodb_global_table)
- [aws_dynamodb_kinesis_streaming_destination](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dynamodb_kinesis_streaming_destination)
- [aws_dynamodb_resource_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dynamodb_resource_policy)
- [aws_dynamodb_table](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dynamodb_table)
- [aws_dynamodb_table_export](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dynamodb_table_export)
- [aws_dynamodb_table_item](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dynamodb_table_item)
- [aws_dynamodb_table_replica](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dynamodb_table_replica)
- [aws_dynamodb_tag](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dynamodb_tag)

### Data Sources
- [aws_dynamodb_table](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/dynamodb_table)
- [aws_dynamodb_table_item](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/dynamodb_table_item)

## DynamoDB Accelerator DAX

*3 resources and 0 data sources*

### Resources
- [aws_dax_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dax_cluster)
- [aws_dax_parameter_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dax_parameter_group)
- [aws_dax_subnet_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dax_subnet_group)

## EBS EC2

*10 resources and 6 data sources*

### Resources
- [aws_ebs_default_kms_key](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ebs_default_kms_key)
- [aws_ebs_encryption_by_default](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ebs_encryption_by_default)
- [aws_ebs_fast_snapshot_restore](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ebs_fast_snapshot_restore)
- [aws_ebs_snapshot](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ebs_snapshot)
- [aws_ebs_snapshot_block_public_access](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ebs_snapshot_block_public_access)
- [aws_ebs_snapshot_copy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ebs_snapshot_copy)
- [aws_ebs_snapshot_import](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ebs_snapshot_import)
- [aws_ebs_volume](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ebs_volume)
- [aws_snapshot_create_volume_permission](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/snapshot_create_volume_permission)
- [aws_volume_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/volume_attachment)

### Data Sources
- [aws_ebs_default_kms_key](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ebs_default_kms_key)
- [aws_ebs_encryption_by_default](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ebs_encryption_by_default)
- [aws_ebs_snapshot](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ebs_snapshot)
- [aws_ebs_snapshot_ids](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ebs_snapshot_ids)
- [aws_ebs_volume](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ebs_volume)
- [aws_ebs_volumes](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ebs_volumes)

## EC2 Elastic Compute Cloud

*25 resources and 21 data sources*

### Resources
- [aws_ami](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ami)
- [aws_ami_copy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ami_copy)
- [aws_ami_from_instance](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ami_from_instance)
- [aws_ami_launch_permission](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ami_launch_permission)
- [aws_ec2_availability_zone_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_availability_zone_group)
- [aws_ec2_capacity_block_reservation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_capacity_block_reservation)
- [aws_ec2_capacity_reservation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_capacity_reservation)
- [aws_ec2_fleet](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_fleet)
- [aws_ec2_host](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_host)
- [aws_ec2_image_block_public_access](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_image_block_public_access)
- [aws_ec2_instance_connect_endpoint](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_instance_connect_endpoint)
- [aws_ec2_instance_metadata_defaults](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_instance_metadata_defaults)
- [aws_ec2_instance_state](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_instance_state)
- [aws_ec2_serial_console_access](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_serial_console_access)
- [aws_ec2_tag](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_tag)
- [aws_eip](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eip)
- [aws_eip_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eip_association)
- [aws_eip_domain_name](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eip_domain_name)
- [aws_instance](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/instance)
- [aws_key_pair](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/key_pair)
- [aws_launch_template](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/launch_template)
- [aws_placement_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/placement_group)
- [aws_spot_datafeed_subscription](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/spot_datafeed_subscription)
- [aws_spot_fleet_request](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/spot_fleet_request)
- [aws_spot_instance_request](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/spot_instance_request)

### Data Sources
- [aws_ami](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ami)
- [aws_ami_ids](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ami_ids)
- [aws_availability_zone](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/availability_zone)
- [aws_availability_zones](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/availability_zones)
- [aws_ec2_capacity_block_offering](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_capacity_block_offering)
- [aws_ec2_host](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_host)
- [aws_ec2_instance_type](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_instance_type)
- [aws_ec2_instance_type_offering](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_instance_type_offering)
- [aws_ec2_instance_type_offerings](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_instance_type_offerings)
- [aws_ec2_instance_types](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_instance_types)
- [aws_ec2_public_ipv4_pool](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_public_ipv4_pool)
- [aws_ec2_public_ipv4_pools](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_public_ipv4_pools)
- [aws_ec2_serial_console_access](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_serial_console_access)
- [aws_ec2_spot_price](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_spot_price)
- [aws_eip](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/eip)
- [aws_eips](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/eips)
- [aws_instance](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/instance)
- [aws_instances](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/instances)
- [aws_key_pair](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/key_pair)
- [aws_launch_template](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/launch_template)
- [aws_spot_datafeed_subscription](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/spot_datafeed_subscription)

## EC2 Image Builder

*9 resources and 13 data sources*

### Resources
- [aws_imagebuilder_component](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/imagebuilder_component)
- [aws_imagebuilder_container_recipe](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/imagebuilder_container_recipe)
- [aws_imagebuilder_distribution_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/imagebuilder_distribution_configuration)
- [aws_imagebuilder_image](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/imagebuilder_image)
- [aws_imagebuilder_image_pipeline](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/imagebuilder_image_pipeline)
- [aws_imagebuilder_image_recipe](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/imagebuilder_image_recipe)
- [aws_imagebuilder_infrastructure_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/imagebuilder_infrastructure_configuration)
- [aws_imagebuilder_lifecycle_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/imagebuilder_lifecycle_policy)
- [aws_imagebuilder_workflow](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/imagebuilder_workflow)

### Data Sources
- [aws_imagebuilder_component](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/imagebuilder_component)
- [aws_imagebuilder_components](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/imagebuilder_components)
- [aws_imagebuilder_container_recipe](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/imagebuilder_container_recipe)
- [aws_imagebuilder_container_recipes](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/imagebuilder_container_recipes)
- [aws_imagebuilder_distribution_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/imagebuilder_distribution_configuration)
- [aws_imagebuilder_distribution_configurations](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/imagebuilder_distribution_configurations)
- [aws_imagebuilder_image](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/imagebuilder_image)
- [aws_imagebuilder_image_pipeline](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/imagebuilder_image_pipeline)
- [aws_imagebuilder_image_pipelines](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/imagebuilder_image_pipelines)
- [aws_imagebuilder_image_recipe](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/imagebuilder_image_recipe)
- [aws_imagebuilder_image_recipes](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/imagebuilder_image_recipes)
- [aws_imagebuilder_infrastructure_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/imagebuilder_infrastructure_configuration)
- [aws_imagebuilder_infrastructure_configurations](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/imagebuilder_infrastructure_configurations)

## ECR Elastic Container Registry

*9 resources and 7 data sources*

### Resources
- [aws_ecr_account_setting](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ecr_account_setting)
- [aws_ecr_lifecycle_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ecr_lifecycle_policy)
- [aws_ecr_pull_through_cache_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ecr_pull_through_cache_rule)
- [aws_ecr_registry_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ecr_registry_policy)
- [aws_ecr_registry_scanning_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ecr_registry_scanning_configuration)
- [aws_ecr_replication_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ecr_replication_configuration)
- [aws_ecr_repository](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ecr_repository)
- [aws_ecr_repository_creation_template](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ecr_repository_creation_template)
- [aws_ecr_repository_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ecr_repository_policy)

### Data Sources
- [aws_ecr_authorization_token](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ecr_authorization_token)
- [aws_ecr_image](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ecr_image)
- [aws_ecr_lifecycle_policy_document](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ecr_lifecycle_policy_document)
- [aws_ecr_pull_through_cache_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ecr_pull_through_cache_rule)
- [aws_ecr_repositories](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ecr_repositories)
- [aws_ecr_repository](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ecr_repository)
- [aws_ecr_repository_creation_template](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ecr_repository_creation_template)

## ECR Public

*2 resources and 1 data sources*

### Resources
- [aws_ecrpublic_repository](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ecrpublic_repository)
- [aws_ecrpublic_repository_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ecrpublic_repository_policy)

### Data Sources
- [aws_ecrpublic_authorization_token](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ecrpublic_authorization_token)

## ECS Elastic Container

*8 resources and 6 data sources*

### Resources
- [aws_ecs_account_setting_default](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ecs_account_setting_default)
- [aws_ecs_capacity_provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ecs_capacity_provider)
- [aws_ecs_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ecs_cluster)
- [aws_ecs_cluster_capacity_providers](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ecs_cluster_capacity_providers)
- [aws_ecs_service](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ecs_service)
- [aws_ecs_tag](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ecs_tag)
- [aws_ecs_task_definition](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ecs_task_definition)
- [aws_ecs_task_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ecs_task_set)

### Data Sources
- [aws_ecs_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ecs_cluster)
- [aws_ecs_clusters](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ecs_clusters)
- [aws_ecs_container_definition](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ecs_container_definition)
- [aws_ecs_service](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ecs_service)
- [aws_ecs_task_definition](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ecs_task_definition)
- [aws_ecs_task_execution](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ecs_task_execution)

## EFS Elastic File System

*6 resources and 4 data sources*

### Resources
- [aws_efs_access_point](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/efs_access_point)
- [aws_efs_backup_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/efs_backup_policy)
- [aws_efs_file_system](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/efs_file_system)
- [aws_efs_file_system_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/efs_file_system_policy)
- [aws_efs_mount_target](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/efs_mount_target)
- [aws_efs_replication_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/efs_replication_configuration)

### Data Sources
- [aws_efs_access_point](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/efs_access_point)
- [aws_efs_access_points](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/efs_access_points)
- [aws_efs_file_system](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/efs_file_system)
- [aws_efs_mount_target](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/efs_mount_target)

## EKS Elastic Kubernetes

*8 resources and 9 data sources*

### Resources
- [aws_eks_access_entry](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_access_entry)
- [aws_eks_access_policy_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_access_policy_association)
- [aws_eks_addon](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_addon)
- [aws_eks_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_cluster)
- [aws_eks_fargate_profile](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_fargate_profile)
- [aws_eks_identity_provider_config](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_identity_provider_config)
- [aws_eks_node_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_node_group)
- [aws_eks_pod_identity_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_pod_identity_association)

### Data Sources
- [aws_eks_access_entry](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/eks_access_entry)
- [aws_eks_addon](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/eks_addon)
- [aws_eks_addon_version](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/eks_addon_version)
- [aws_eks_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/eks_cluster)
- [aws_eks_cluster_auth](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/eks_cluster_auth)
- [aws_eks_cluster_versions](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/eks_cluster_versions)
- [aws_eks_clusters](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/eks_clusters)
- [aws_eks_node_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/eks_node_group)
- [aws_eks_node_groups](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/eks_node_groups)

## ELB Elastic Load Balancing

*8 resources and 7 data sources*

### Resources
- [aws_lb](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lb)
- [aws_lb_listener](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lb_listener)
- [aws_lb_listener_certificate](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lb_listener_certificate)
- [aws_lb_listener_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lb_listener_rule)
- [aws_lb_target_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lb_target_group)
- [aws_lb_target_group_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lb_target_group_attachment)
- [aws_lb_trust_store](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lb_trust_store)
- [aws_lb_trust_store_revocation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lb_trust_store_revocation)

### Data Sources
- [aws_lb](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/lb)
- [aws_lb_hosted_zone_id](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/lb_hosted_zone_id)
- [aws_lb_listener](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/lb_listener)
- [aws_lb_listener_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/lb_listener_rule)
- [aws_lb_target_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/lb_target_group)
- [aws_lb_trust_store](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/lb_trust_store)
- [aws_lbs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/lbs)

## ELB Classic

*9 resources and 3 data sources*

### Resources
- [aws_app_cookie_stickiness_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/app_cookie_stickiness_policy)
- [aws_elb](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/elb)
- [aws_elb_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/elb_attachment)
- [aws_lb_cookie_stickiness_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lb_cookie_stickiness_policy)
- [aws_lb_ssl_negotiation_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lb_ssl_negotiation_policy)
- [aws_load_balancer_backend_server_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/load_balancer_backend_server_policy)
- [aws_load_balancer_listener_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/load_balancer_listener_policy)
- [aws_load_balancer_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/load_balancer_policy)
- [aws_proxy_protocol_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/proxy_protocol_policy)

### Data Sources
- [aws_elb](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/elb)
- [aws_elb_hosted_zone_id](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/elb_hosted_zone_id)
- [aws_elb_service_account](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/elb_service_account)

## EMR

*8 resources and 2 data sources*

### Resources
- [aws_emr_block_public_access_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/emr_block_public_access_configuration)
- [aws_emr_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/emr_cluster)
- [aws_emr_instance_fleet](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/emr_instance_fleet)
- [aws_emr_instance_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/emr_instance_group)
- [aws_emr_managed_scaling_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/emr_managed_scaling_policy)
- [aws_emr_security_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/emr_security_configuration)
- [aws_emr_studio](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/emr_studio)
- [aws_emr_studio_session_mapping](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/emr_studio_session_mapping)

### Data Sources
- [aws_emr_release_labels](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/emr_release_labels)
- [aws_emr_supported_instance_types](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/emr_supported_instance_types)

## EMR Containers

*2 resources and 1 data sources*

### Resources
- [aws_emrcontainers_job_template](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/emrcontainers_job_template)
- [aws_emrcontainers_virtual_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/emrcontainers_virtual_cluster)

### Data Sources
- [aws_emrcontainers_virtual_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/emrcontainers_virtual_cluster)

## EMR Serverless

*1 resources and 0 data sources*

### Resources
- [aws_emrserverless_application](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/emrserverless_application)

## ElastiCache

*10 resources and 6 data sources*

### Resources
- [aws_elasticache_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/elasticache_cluster)
- [aws_elasticache_global_replication_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/elasticache_global_replication_group)
- [aws_elasticache_parameter_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/elasticache_parameter_group)
- [aws_elasticache_replication_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/elasticache_replication_group)
- [aws_elasticache_reserved_cache_node](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/elasticache_reserved_cache_node)
- [aws_elasticache_serverless_cache](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/elasticache_serverless_cache)
- [aws_elasticache_subnet_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/elasticache_subnet_group)
- [aws_elasticache_user](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/elasticache_user)
- [aws_elasticache_user_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/elasticache_user_group)
- [aws_elasticache_user_group_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/elasticache_user_group_association)

### Data Sources
- [aws_elasticache_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/elasticache_cluster)
- [aws_elasticache_replication_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/elasticache_replication_group)
- [aws_elasticache_reserved_cache_node_offering](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/elasticache_reserved_cache_node_offering)
- [aws_elasticache_serverless_cache](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/elasticache_serverless_cache)
- [aws_elasticache_subnet_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/elasticache_subnet_group)
- [aws_elasticache_user](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/elasticache_user)

## Elastic Beanstalk

*4 resources and 3 data sources*

### Resources
- [aws_elastic_beanstalk_application](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/elastic_beanstalk_application)
- [aws_elastic_beanstalk_application_version](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/elastic_beanstalk_application_version)
- [aws_elastic_beanstalk_configuration_template](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/elastic_beanstalk_configuration_template)
- [aws_elastic_beanstalk_environment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/elastic_beanstalk_environment)

### Data Sources
- [aws_elastic_beanstalk_application](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/elastic_beanstalk_application)
- [aws_elastic_beanstalk_hosted_zone](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/elastic_beanstalk_hosted_zone)
- [aws_elastic_beanstalk_solution_stack](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/elastic_beanstalk_solution_stack)

## Elastic Transcoder

*2 resources and 0 data sources*

### Resources
- [aws_elastictranscoder_pipeline](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/elastictranscoder_pipeline)
- [aws_elastictranscoder_preset](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/elastictranscoder_preset)

## Elasticsearch

*4 resources and 1 data sources*

### Resources
- [aws_elasticsearch_domain](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/elasticsearch_domain)
- [aws_elasticsearch_domain_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/elasticsearch_domain_policy)
- [aws_elasticsearch_domain_saml_options](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/elasticsearch_domain_saml_options)
- [aws_elasticsearch_vpc_endpoint](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/elasticsearch_vpc_endpoint)

### Data Sources
- [aws_elasticsearch_domain](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/elasticsearch_domain)

## Elemental MediaConvert

*1 resources and 1 data sources*

### Resources
- [aws_media_convert_queue](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/media_convert_queue)

### Data Sources
- [aws_media_convert_queue](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/media_convert_queue)

## Elemental MediaLive

*5 resources and 1 data sources*

### Resources
- [aws_medialive_channel](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/medialive_channel)
- [aws_medialive_input](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/medialive_input)
- [aws_medialive_input_security_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/medialive_input_security_group)
- [aws_medialive_multiplex](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/medialive_multiplex)
- [aws_medialive_multiplex_program](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/medialive_multiplex_program)

### Data Sources
- [aws_medialive_input](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/medialive_input)

## Elemental MediaPackage

*1 resources and 0 data sources*

### Resources
- [aws_media_package_channel](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/media_package_channel)

## Elemental MediaPackage Version 2

*1 resources and 0 data sources*

### Resources
- [aws_media_packagev2_channel_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/media_packagev2_channel_group)

## Elemental MediaStore

*2 resources and 0 data sources*

### Resources
- [aws_media_store_container](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/media_store_container)
- [aws_media_store_container_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/media_store_container_policy)

## End User Messaging SMS

*3 resources and 0 data sources*

### Resources
- [aws_pinpointsmsvoicev2_configuration_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/pinpointsmsvoicev2_configuration_set)
- [aws_pinpointsmsvoicev2_opt_out_list](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/pinpointsmsvoicev2_opt_out_list)
- [aws_pinpointsmsvoicev2_phone_number](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/pinpointsmsvoicev2_phone_number)

## EventBridge

*9 resources and 4 data sources*

### Resources
- [aws_cloudwatch_event_api_destination](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_event_api_destination)
- [aws_cloudwatch_event_archive](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_event_archive)
- [aws_cloudwatch_event_bus](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_event_bus)
- [aws_cloudwatch_event_bus_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_event_bus_policy)
- [aws_cloudwatch_event_connection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_event_connection)
- [aws_cloudwatch_event_endpoint](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_event_endpoint)
- [aws_cloudwatch_event_permission](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_event_permission)
- [aws_cloudwatch_event_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_event_rule)
- [aws_cloudwatch_event_target](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_event_target)

### Data Sources
- [aws_cloudwatch_event_bus](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cloudwatch_event_bus)
- [aws_cloudwatch_event_buses](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cloudwatch_event_buses)
- [aws_cloudwatch_event_connection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cloudwatch_event_connection)
- [aws_cloudwatch_event_source](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cloudwatch_event_source)

## EventBridge Pipes

*1 resources and 0 data sources*

### Resources
- [aws_pipes_pipe](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/pipes_pipe)

## EventBridge Scheduler

*2 resources and 0 data sources*

### Resources
- [aws_scheduler_schedule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/scheduler_schedule)
- [aws_scheduler_schedule_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/scheduler_schedule_group)

## EventBridge Schemas

*4 resources and 0 data sources*

### Resources
- [aws_schemas_discoverer](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/schemas_discoverer)
- [aws_schemas_registry](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/schemas_registry)
- [aws_schemas_registry_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/schemas_registry_policy)
- [aws_schemas_schema](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/schemas_schema)

## FIS Fault Injection Simulator

*1 resources and 0 data sources*

### Resources
- [aws_fis_experiment_template](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/fis_experiment_template)

## FMS Firewall Manager

*3 resources and 0 data sources*

### Resources
- [aws_fms_admin_account](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/fms_admin_account)
- [aws_fms_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/fms_policy)
- [aws_fms_resource_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/fms_resource_set)

## FSx

*11 resources and 5 data sources*

### Resources
- [aws_fsx_backup](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/fsx_backup)
- [aws_fsx_data_repository_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/fsx_data_repository_association)
- [aws_fsx_file_cache](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/fsx_file_cache)
- [aws_fsx_lustre_file_system](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/fsx_lustre_file_system)
- [aws_fsx_ontap_file_system](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/fsx_ontap_file_system)
- [aws_fsx_ontap_storage_virtual_machine](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/fsx_ontap_storage_virtual_machine)
- [aws_fsx_ontap_volume](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/fsx_ontap_volume)
- [aws_fsx_openzfs_file_system](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/fsx_openzfs_file_system)
- [aws_fsx_openzfs_snapshot](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/fsx_openzfs_snapshot)
- [aws_fsx_openzfs_volume](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/fsx_openzfs_volume)
- [aws_fsx_windows_file_system](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/fsx_windows_file_system)

### Data Sources
- [aws_fsx_ontap_file_system](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/fsx_ontap_file_system)
- [aws_fsx_ontap_storage_virtual_machine](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/fsx_ontap_storage_virtual_machine)
- [aws_fsx_ontap_storage_virtual_machines](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/fsx_ontap_storage_virtual_machines)
- [aws_fsx_openzfs_snapshot](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/fsx_openzfs_snapshot)
- [aws_fsx_windows_file_system](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/fsx_windows_file_system)

## FinSpace

*7 resources and 0 data sources*

### Resources
- [aws_finspace_kx_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/finspace_kx_cluster)
- [aws_finspace_kx_database](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/finspace_kx_database)
- [aws_finspace_kx_dataview](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/finspace_kx_dataview)
- [aws_finspace_kx_environment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/finspace_kx_environment)
- [aws_finspace_kx_scaling_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/finspace_kx_scaling_group)
- [aws_finspace_kx_user](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/finspace_kx_user)
- [aws_finspace_kx_volume](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/finspace_kx_volume)

## GameLift

*6 resources and 0 data sources*

### Resources
- [aws_gamelift_alias](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/gamelift_alias)
- [aws_gamelift_build](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/gamelift_build)
- [aws_gamelift_fleet](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/gamelift_fleet)
- [aws_gamelift_game_server_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/gamelift_game_server_group)
- [aws_gamelift_game_session_queue](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/gamelift_game_session_queue)
- [aws_gamelift_script](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/gamelift_script)

## Global Accelerator

*7 resources and 2 data sources*

### Resources
- [aws_globalaccelerator_accelerator](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/globalaccelerator_accelerator)
- [aws_globalaccelerator_cross_account_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/globalaccelerator_cross_account_attachment)
- [aws_globalaccelerator_custom_routing_accelerator](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/globalaccelerator_custom_routing_accelerator)
- [aws_globalaccelerator_custom_routing_endpoint_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/globalaccelerator_custom_routing_endpoint_group)
- [aws_globalaccelerator_custom_routing_listener](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/globalaccelerator_custom_routing_listener)
- [aws_globalaccelerator_endpoint_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/globalaccelerator_endpoint_group)
- [aws_globalaccelerator_listener](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/globalaccelerator_listener)

### Data Sources
- [aws_globalaccelerator_accelerator](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/globalaccelerator_accelerator)
- [aws_globalaccelerator_custom_routing_accelerator](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/globalaccelerator_custom_routing_accelerator)

## Glue

*20 resources and 5 data sources*

### Resources
- [aws_glue_catalog_database](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/glue_catalog_database)
- [aws_glue_catalog_table](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/glue_catalog_table)
- [aws_glue_catalog_table_optimizer](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/glue_catalog_table_optimizer)
- [aws_glue_classifier](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/glue_classifier)
- [aws_glue_connection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/glue_connection)
- [aws_glue_crawler](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/glue_crawler)
- [aws_glue_data_catalog_encryption_settings](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/glue_data_catalog_encryption_settings)
- [aws_glue_data_quality_ruleset](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/glue_data_quality_ruleset)
- [aws_glue_dev_endpoint](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/glue_dev_endpoint)
- [aws_glue_job](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/glue_job)
- [aws_glue_ml_transform](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/glue_ml_transform)
- [aws_glue_partition](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/glue_partition)
- [aws_glue_partition_index](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/glue_partition_index)
- [aws_glue_registry](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/glue_registry)
- [aws_glue_resource_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/glue_resource_policy)
- [aws_glue_schema](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/glue_schema)
- [aws_glue_security_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/glue_security_configuration)
- [aws_glue_trigger](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/glue_trigger)
- [aws_glue_user_defined_function](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/glue_user_defined_function)
- [aws_glue_workflow](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/glue_workflow)

### Data Sources
- [aws_glue_catalog_table](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/glue_catalog_table)
- [aws_glue_connection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/glue_connection)
- [aws_glue_data_catalog_encryption_settings](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/glue_data_catalog_encryption_settings)
- [aws_glue_registry](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/glue_registry)
- [aws_glue_script](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/glue_script)

## GuardDuty

*13 resources and 2 data sources*

### Resources
- [aws_guardduty_detector](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/guardduty_detector)
- [aws_guardduty_detector_feature](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/guardduty_detector_feature)
- [aws_guardduty_filter](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/guardduty_filter)
- [aws_guardduty_invite_accepter](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/guardduty_invite_accepter)
- [aws_guardduty_ipset](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/guardduty_ipset)
- [aws_guardduty_malware_protection_plan](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/guardduty_malware_protection_plan)
- [aws_guardduty_member](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/guardduty_member)
- [aws_guardduty_member_detector_feature](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/guardduty_member_detector_feature)
- [aws_guardduty_organization_admin_account](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/guardduty_organization_admin_account)
- [aws_guardduty_organization_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/guardduty_organization_configuration)
- [aws_guardduty_organization_configuration_feature](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/guardduty_organization_configuration_feature)
- [aws_guardduty_publishing_destination](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/guardduty_publishing_destination)
- [aws_guardduty_threatintelset](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/guardduty_threatintelset)

### Data Sources
- [aws_guardduty_detector](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/guardduty_detector)
- [aws_guardduty_finding_ids](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/guardduty_finding_ids)

## IAM Identity & Access Management

*34 resources and 17 data sources*

### Resources
- [aws_iam_access_key](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_access_key)
- [aws_iam_account_alias](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_account_alias)
- [aws_iam_account_password_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_account_password_policy)
- [aws_iam_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_group)
- [aws_iam_group_membership](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_group_membership)
- [aws_iam_group_policies_exclusive](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_group_policies_exclusive)
- [aws_iam_group_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_group_policy)
- [aws_iam_group_policy_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_group_policy_attachment)
- [aws_iam_group_policy_attachments_exclusive](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_group_policy_attachments_exclusive)
- [aws_iam_instance_profile](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_instance_profile)
- [aws_iam_openid_connect_provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_openid_connect_provider)
- [aws_iam_organizations_features](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_organizations_features)
- [aws_iam_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_policy)
- [aws_iam_policy_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_policy_attachment)
- [aws_iam_role](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role)
- [aws_iam_role_policies_exclusive](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policies_exclusive)
- [aws_iam_role_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy)
- [aws_iam_role_policy_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy_attachment)
- [aws_iam_role_policy_attachments_exclusive](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy_attachments_exclusive)
- [aws_iam_saml_provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_saml_provider)
- [aws_iam_security_token_service_preferences](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_security_token_service_preferences)
- [aws_iam_server_certificate](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_server_certificate)
- [aws_iam_service_linked_role](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_service_linked_role)
- [aws_iam_service_specific_credential](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_service_specific_credential)
- [aws_iam_signing_certificate](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_signing_certificate)
- [aws_iam_user](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_user)
- [aws_iam_user_group_membership](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_user_group_membership)
- [aws_iam_user_login_profile](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_user_login_profile)
- [aws_iam_user_policies_exclusive](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_user_policies_exclusive)
- [aws_iam_user_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_user_policy)
- [aws_iam_user_policy_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_user_policy_attachment)
- [aws_iam_user_policy_attachments_exclusive](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_user_policy_attachments_exclusive)
- [aws_iam_user_ssh_key](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_user_ssh_key)
- [aws_iam_virtual_mfa_device](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_virtual_mfa_device)

### Data Sources
- [aws_iam_access_keys](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_access_keys)
- [aws_iam_account_alias](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_account_alias)
- [aws_iam_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_group)
- [aws_iam_instance_profile](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_instance_profile)
- [aws_iam_instance_profiles](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_instance_profiles)
- [aws_iam_openid_connect_provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_openid_connect_provider)
- [aws_iam_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy)
- [aws_iam_policy_document](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document)
- [aws_iam_principal_policy_simulation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_principal_policy_simulation)
- [aws_iam_role](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_role)
- [aws_iam_roles](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_roles)
- [aws_iam_saml_provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_saml_provider)
- [aws_iam_server_certificate](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_server_certificate)
- [aws_iam_session_context](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_session_context)
- [aws_iam_user](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_user)
- [aws_iam_user_ssh_key](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_user_ssh_key)
- [aws_iam_users](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_users)

## IAM Access Analyzer

*2 resources and 0 data sources*

### Resources
- [aws_accessanalyzer_analyzer](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/accessanalyzer_analyzer)
- [aws_accessanalyzer_archive_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/accessanalyzer_archive_rule)

## IVS Interactive Video

*3 resources and 1 data sources*

### Resources
- [aws_ivs_channel](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ivs_channel)
- [aws_ivs_playback_key_pair](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ivs_playback_key_pair)
- [aws_ivs_recording_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ivs_recording_configuration)

### Data Sources
- [aws_ivs_stream_key](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ivs_stream_key)

## IVS Interactive Video Chat

*2 resources and 0 data sources*

### Resources
- [aws_ivschat_logging_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ivschat_logging_configuration)
- [aws_ivschat_room](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ivschat_room)

## Inspector

*4 resources and 0 data sources*

### Resources
- [aws_inspector2_delegated_admin_account](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/inspector2_delegated_admin_account)
- [aws_inspector2_enabler](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/inspector2_enabler)
- [aws_inspector2_member_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/inspector2_member_association)
- [aws_inspector2_organization_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/inspector2_organization_configuration)

## Inspector Classic

*3 resources and 1 data sources*

### Resources
- [aws_inspector_assessment_target](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/inspector_assessment_target)
- [aws_inspector_assessment_template](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/inspector_assessment_template)
- [aws_inspector_resource_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/inspector_resource_group)

### Data Sources
- [aws_inspector_rules_packages](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/inspector_rules_packages)

## IoT Core

*19 resources and 2 data sources*

### Resources
- [aws_iot_authorizer](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iot_authorizer)
- [aws_iot_billing_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iot_billing_group)
- [aws_iot_ca_certificate](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iot_ca_certificate)
- [aws_iot_certificate](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iot_certificate)
- [aws_iot_domain_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iot_domain_configuration)
- [aws_iot_event_configurations](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iot_event_configurations)
- [aws_iot_indexing_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iot_indexing_configuration)
- [aws_iot_logging_options](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iot_logging_options)
- [aws_iot_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iot_policy)
- [aws_iot_policy_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iot_policy_attachment)
- [aws_iot_provisioning_template](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iot_provisioning_template)
- [aws_iot_role_alias](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iot_role_alias)
- [aws_iot_thing](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iot_thing)
- [aws_iot_thing_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iot_thing_group)
- [aws_iot_thing_group_membership](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iot_thing_group_membership)
- [aws_iot_thing_principal_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iot_thing_principal_attachment)
- [aws_iot_thing_type](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iot_thing_type)
- [aws_iot_topic_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iot_topic_rule)
- [aws_iot_topic_rule_destination](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iot_topic_rule_destination)

### Data Sources
- [aws_iot_endpoint](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iot_endpoint)
- [aws_iot_registration_code](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iot_registration_code)

## KMS Key Management

*9 resources and 7 data sources*

### Resources
- [aws_kms_alias](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kms_alias)
- [aws_kms_ciphertext](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kms_ciphertext)
- [aws_kms_custom_key_store](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kms_custom_key_store)
- [aws_kms_external_key](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kms_external_key)
- [aws_kms_grant](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kms_grant)
- [aws_kms_key](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kms_key)
- [aws_kms_key_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kms_key_policy)
- [aws_kms_replica_external_key](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kms_replica_external_key)
- [aws_kms_replica_key](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kms_replica_key)

### Data Sources
- [aws_kms_alias](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/kms_alias)
- [aws_kms_ciphertext](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/kms_ciphertext)
- [aws_kms_custom_key_store](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/kms_custom_key_store)
- [aws_kms_key](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/kms_key)
- [aws_kms_public_key](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/kms_public_key)
- [aws_kms_secret](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/kms_secret)
- [aws_kms_secrets](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/kms_secrets)

## Kendra

*6 resources and 5 data sources*

### Resources
- [aws_kendra_data_source](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kendra_data_source)
- [aws_kendra_experience](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kendra_experience)
- [aws_kendra_faq](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kendra_faq)
- [aws_kendra_index](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kendra_index)
- [aws_kendra_query_suggestions_block_list](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kendra_query_suggestions_block_list)
- [aws_kendra_thesaurus](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kendra_thesaurus)

### Data Sources
- [aws_kendra_experience](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/kendra_experience)
- [aws_kendra_faq](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/kendra_faq)
- [aws_kendra_index](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/kendra_index)
- [aws_kendra_query_suggestions_block_list](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/kendra_query_suggestions_block_list)
- [aws_kendra_thesaurus](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/kendra_thesaurus)

## Keyspaces for Apache Cassandra

*2 resources and 0 data sources*

### Resources
- [aws_keyspaces_keyspace](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/keyspaces_keyspace)
- [aws_keyspaces_table](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/keyspaces_table)

## Kinesis

*3 resources and 2 data sources*

### Resources
- [aws_kinesis_resource_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kinesis_resource_policy)
- [aws_kinesis_stream](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kinesis_stream)
- [aws_kinesis_stream_consumer](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kinesis_stream_consumer)

### Data Sources
- [aws_kinesis_stream](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/kinesis_stream)
- [aws_kinesis_stream_consumer](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/kinesis_stream_consumer)

## Kinesis Analytics

*1 resources and 0 data sources*

### Resources
- [aws_kinesis_analytics_application](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kinesis_analytics_application)

## Kinesis Analytics V2

*2 resources and 0 data sources*

### Resources
- [aws_kinesisanalyticsv2_application](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kinesisanalyticsv2_application)
- [aws_kinesisanalyticsv2_application_snapshot](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kinesisanalyticsv2_application_snapshot)

## Kinesis Firehose

*1 resources and 1 data sources*

### Resources
- [aws_kinesis_firehose_delivery_stream](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kinesis_firehose_delivery_stream)

### Data Sources
- [aws_kinesis_firehose_delivery_stream](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/kinesis_firehose_delivery_stream)

## Kinesis Video

*1 resources and 0 data sources*

### Resources
- [aws_kinesis_video_stream](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kinesis_video_stream)

## Lake Formation

*8 resources and 3 data sources*

### Resources
- [aws_lakeformation_data_cells_filter](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lakeformation_data_cells_filter)
- [aws_lakeformation_data_lake_settings](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lakeformation_data_lake_settings)
- [aws_lakeformation_lf_tag](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lakeformation_lf_tag)
- [aws_lakeformation_opt_in](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lakeformation_opt_in)
- [aws_lakeformation_permissions](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lakeformation_permissions)
- [aws_lakeformation_resource](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lakeformation_resource)
- [aws_lakeformation_resource_lf_tag](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lakeformation_resource_lf_tag)
- [aws_lakeformation_resource_lf_tags](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lakeformation_resource_lf_tags)

### Data Sources
- [aws_lakeformation_data_lake_settings](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/lakeformation_data_lake_settings)
- [aws_lakeformation_permissions](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/lakeformation_permissions)
- [aws_lakeformation_resource](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/lakeformation_resource)

## Lambda

*13 resources and 7 data sources*

### Resources
- [aws_lambda_alias](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_alias)
- [aws_lambda_code_signing_config](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_code_signing_config)
- [aws_lambda_event_source_mapping](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_event_source_mapping)
- [aws_lambda_function](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_function)
- [aws_lambda_function_event_invoke_config](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_function_event_invoke_config)
- [aws_lambda_function_recursion_config](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_function_recursion_config)
- [aws_lambda_function_url](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_function_url)
- [aws_lambda_invocation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_invocation)
- [aws_lambda_layer_version](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_layer_version)
- [aws_lambda_layer_version_permission](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_layer_version_permission)
- [aws_lambda_permission](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_permission)
- [aws_lambda_provisioned_concurrency_config](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_provisioned_concurrency_config)
- [aws_lambda_runtime_management_config](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_runtime_management_config)

### Data Sources
- [aws_lambda_alias](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/lambda_alias)
- [aws_lambda_code_signing_config](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/lambda_code_signing_config)
- [aws_lambda_function](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/lambda_function)
- [aws_lambda_function_url](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/lambda_function_url)
- [aws_lambda_functions](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/lambda_functions)
- [aws_lambda_invocation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/lambda_invocation)
- [aws_lambda_layer_version](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/lambda_layer_version)

## Lex Model Building

*4 resources and 4 data sources*

### Resources
- [aws_lex_bot](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lex_bot)
- [aws_lex_bot_alias](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lex_bot_alias)
- [aws_lex_intent](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lex_intent)
- [aws_lex_slot_type](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lex_slot_type)

### Data Sources
- [aws_lex_bot](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/lex_bot)
- [aws_lex_bot_alias](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/lex_bot_alias)
- [aws_lex_intent](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/lex_intent)
- [aws_lex_slot_type](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/lex_slot_type)

## Lex V2 Models

*6 resources and 0 data sources*

### Resources
- [aws_lexv2models_bot](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lexv2models_bot)
- [aws_lexv2models_bot_locale](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lexv2models_bot_locale)
- [aws_lexv2models_bot_version](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lexv2models_bot_version)
- [aws_lexv2models_intent](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lexv2models_intent)
- [aws_lexv2models_slot](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lexv2models_slot)
- [aws_lexv2models_slot_type](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lexv2models_slot_type)

## License Manager

*4 resources and 3 data sources*

### Resources
- [aws_licensemanager_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/licensemanager_association)
- [aws_licensemanager_grant](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/licensemanager_grant)
- [aws_licensemanager_grant_accepter](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/licensemanager_grant_accepter)
- [aws_licensemanager_license_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/licensemanager_license_configuration)

### Data Sources
- [aws_licensemanager_grants](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/licensemanager_grants)
- [aws_licensemanager_received_license](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/licensemanager_received_license)
- [aws_licensemanager_received_licenses](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/licensemanager_received_licenses)

## Lightsail

*23 resources and 0 data sources*

### Resources
- [aws_lightsail_bucket](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lightsail_bucket)
- [aws_lightsail_bucket_access_key](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lightsail_bucket_access_key)
- [aws_lightsail_bucket_resource_access](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lightsail_bucket_resource_access)
- [aws_lightsail_certificate](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lightsail_certificate)
- [aws_lightsail_container_service](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lightsail_container_service)
- [aws_lightsail_container_service_deployment_version](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lightsail_container_service_deployment_version)
- [aws_lightsail_database](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lightsail_database)
- [aws_lightsail_disk](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lightsail_disk)
- [aws_lightsail_disk_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lightsail_disk_attachment)
- [aws_lightsail_distribution](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lightsail_distribution)
- [aws_lightsail_domain](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lightsail_domain)
- [aws_lightsail_domain_entry](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lightsail_domain_entry)
- [aws_lightsail_instance](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lightsail_instance)
- [aws_lightsail_instance_public_ports](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lightsail_instance_public_ports)
- [aws_lightsail_key_pair](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lightsail_key_pair)
- [aws_lightsail_lb](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lightsail_lb)
- [aws_lightsail_lb_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lightsail_lb_attachment)
- [aws_lightsail_lb_certificate](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lightsail_lb_certificate)
- [aws_lightsail_lb_certificate_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lightsail_lb_certificate_attachment)
- [aws_lightsail_lb_https_redirection_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lightsail_lb_https_redirection_policy)
- [aws_lightsail_lb_stickiness_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lightsail_lb_stickiness_policy)
- [aws_lightsail_static_ip](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lightsail_static_ip)
- [aws_lightsail_static_ip_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lightsail_static_ip_attachment)

## Location

*6 resources and 7 data sources*

### Resources
- [aws_location_geofence_collection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/location_geofence_collection)
- [aws_location_map](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/location_map)
- [aws_location_place_index](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/location_place_index)
- [aws_location_route_calculator](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/location_route_calculator)
- [aws_location_tracker](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/location_tracker)
- [aws_location_tracker_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/location_tracker_association)

### Data Sources
- [aws_location_geofence_collection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/location_geofence_collection)
- [aws_location_map](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/location_map)
- [aws_location_place_index](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/location_place_index)
- [aws_location_route_calculator](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/location_route_calculator)
- [aws_location_tracker](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/location_tracker)
- [aws_location_tracker_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/location_tracker_association)
- [aws_location_tracker_associations](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/location_tracker_associations)

## MQ

*2 resources and 3 data sources*

### Resources
- [aws_mq_broker](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/mq_broker)
- [aws_mq_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/mq_configuration)

### Data Sources
- [aws_mq_broker](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/mq_broker)
- [aws_mq_broker_engine_types](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/mq_broker_engine_types)
- [aws_mq_broker_instance_type_offerings](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/mq_broker_instance_type_offerings)

## MWAA Managed Workflows for Apache Airflow

*1 resources and 0 data sources*

### Resources
- [aws_mwaa_environment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/mwaa_environment)

## Macie

*9 resources and 0 data sources*

### Resources
- [aws_macie2_account](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/macie2_account)
- [aws_macie2_classification_export_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/macie2_classification_export_configuration)
- [aws_macie2_classification_job](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/macie2_classification_job)
- [aws_macie2_custom_data_identifier](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/macie2_custom_data_identifier)
- [aws_macie2_findings_filter](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/macie2_findings_filter)
- [aws_macie2_invitation_accepter](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/macie2_invitation_accepter)
- [aws_macie2_member](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/macie2_member)
- [aws_macie2_organization_admin_account](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/macie2_organization_admin_account)
- [aws_macie2_organization_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/macie2_organization_configuration)

## Mainframe Modernization

*3 resources and 0 data sources*

### Resources
- [aws_m2_application](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/m2_application)
- [aws_m2_deployment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/m2_deployment)
- [aws_m2_environment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/m2_environment)

## Managed Grafana

*7 resources and 1 data sources*

### Resources
- [aws_grafana_license_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/grafana_license_association)
- [aws_grafana_role_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/grafana_role_association)
- [aws_grafana_workspace](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/grafana_workspace)
- [aws_grafana_workspace_api_key](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/grafana_workspace_api_key)
- [aws_grafana_workspace_saml_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/grafana_workspace_saml_configuration)
- [aws_grafana_workspace_service_account](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/grafana_workspace_service_account)
- [aws_grafana_workspace_service_account_token](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/grafana_workspace_service_account_token)

### Data Sources
- [aws_grafana_workspace](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/grafana_workspace)

## Managed Streaming for Kafka

*8 resources and 6 data sources*

### Resources
- [aws_msk_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/msk_cluster)
- [aws_msk_cluster_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/msk_cluster_policy)
- [aws_msk_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/msk_configuration)
- [aws_msk_replicator](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/msk_replicator)
- [aws_msk_scram_secret_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/msk_scram_secret_association)
- [aws_msk_serverless_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/msk_serverless_cluster)
- [aws_msk_single_scram_secret_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/msk_single_scram_secret_association)
- [aws_msk_vpc_connection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/msk_vpc_connection)

### Data Sources
- [aws_msk_bootstrap_brokers](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/msk_bootstrap_brokers)
- [aws_msk_broker_nodes](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/msk_broker_nodes)
- [aws_msk_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/msk_cluster)
- [aws_msk_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/msk_configuration)
- [aws_msk_kafka_version](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/msk_kafka_version)
- [aws_msk_vpc_connection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/msk_vpc_connection)

## Managed Streaming for Kafka Connect

*3 resources and 3 data sources*

### Resources
- [aws_mskconnect_connector](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/mskconnect_connector)
- [aws_mskconnect_custom_plugin](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/mskconnect_custom_plugin)
- [aws_mskconnect_worker_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/mskconnect_worker_configuration)

### Data Sources
- [aws_mskconnect_connector](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/mskconnect_connector)
- [aws_mskconnect_custom_plugin](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/mskconnect_custom_plugin)
- [aws_mskconnect_worker_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/mskconnect_worker_configuration)

## MemoryDB

*7 resources and 6 data sources*

### Resources
- [aws_memorydb_acl](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/memorydb_acl)
- [aws_memorydb_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/memorydb_cluster)
- [aws_memorydb_multi_region_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/memorydb_multi_region_cluster)
- [aws_memorydb_parameter_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/memorydb_parameter_group)
- [aws_memorydb_snapshot](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/memorydb_snapshot)
- [aws_memorydb_subnet_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/memorydb_subnet_group)
- [aws_memorydb_user](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/memorydb_user)

### Data Sources
- [aws_memorydb_acl](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/memorydb_acl)
- [aws_memorydb_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/memorydb_cluster)
- [aws_memorydb_parameter_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/memorydb_parameter_group)
- [aws_memorydb_snapshot](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/memorydb_snapshot)
- [aws_memorydb_subnet_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/memorydb_subnet_group)
- [aws_memorydb_user](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/memorydb_user)

## Meta Data Sources

*0 resources and 8 data sources*


### Data Sources
- [aws_arn](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/arn)
- [aws_default_tags](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/default_tags)
- [aws_ip_ranges](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ip_ranges)
- [aws_partition](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/partition)
- [aws_region](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/region)
- [aws_regions](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/regions)
- [aws_service](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/service)
- [aws_service_principal](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/service_principal)

## Neptune

*9 resources and 2 data sources*

### Resources
- [aws_neptune_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/neptune_cluster)
- [aws_neptune_cluster_endpoint](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/neptune_cluster_endpoint)
- [aws_neptune_cluster_instance](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/neptune_cluster_instance)
- [aws_neptune_cluster_parameter_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/neptune_cluster_parameter_group)
- [aws_neptune_cluster_snapshot](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/neptune_cluster_snapshot)
- [aws_neptune_event_subscription](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/neptune_event_subscription)
- [aws_neptune_global_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/neptune_global_cluster)
- [aws_neptune_parameter_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/neptune_parameter_group)
- [aws_neptune_subnet_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/neptune_subnet_group)

### Data Sources
- [aws_neptune_engine_version](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/neptune_engine_version)
- [aws_neptune_orderable_db_instance](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/neptune_orderable_db_instance)

## Neptune Analytics

*1 resources and 0 data sources*

### Resources
- [aws_neptunegraph_graph](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/neptunegraph_graph)

## Network Firewall

*6 resources and 3 data sources*

### Resources
- [aws_networkfirewall_firewall](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/networkfirewall_firewall)
- [aws_networkfirewall_firewall_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/networkfirewall_firewall_policy)
- [aws_networkfirewall_logging_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/networkfirewall_logging_configuration)
- [aws_networkfirewall_resource_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/networkfirewall_resource_policy)
- [aws_networkfirewall_rule_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/networkfirewall_rule_group)
- [aws_networkfirewall_tls_inspection_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/networkfirewall_tls_inspection_configuration)

### Data Sources
- [aws_networkfirewall_firewall](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/networkfirewall_firewall)
- [aws_networkfirewall_firewall_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/networkfirewall_firewall_policy)
- [aws_networkfirewall_resource_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/networkfirewall_resource_policy)

## Network Manager

*19 resources and 11 data sources*

### Resources
- [aws_networkmanager_attachment_accepter](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/networkmanager_attachment_accepter)
- [aws_networkmanager_connect_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/networkmanager_connect_attachment)
- [aws_networkmanager_connect_peer](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/networkmanager_connect_peer)
- [aws_networkmanager_connection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/networkmanager_connection)
- [aws_networkmanager_core_network](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/networkmanager_core_network)
- [aws_networkmanager_core_network_policy_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/networkmanager_core_network_policy_attachment)
- [aws_networkmanager_customer_gateway_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/networkmanager_customer_gateway_association)
- [aws_networkmanager_device](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/networkmanager_device)
- [aws_networkmanager_dx_gateway_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/networkmanager_dx_gateway_attachment)
- [aws_networkmanager_global_network](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/networkmanager_global_network)
- [aws_networkmanager_link](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/networkmanager_link)
- [aws_networkmanager_link_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/networkmanager_link_association)
- [aws_networkmanager_site](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/networkmanager_site)
- [aws_networkmanager_site_to_site_vpn_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/networkmanager_site_to_site_vpn_attachment)
- [aws_networkmanager_transit_gateway_connect_peer_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/networkmanager_transit_gateway_connect_peer_association)
- [aws_networkmanager_transit_gateway_peering](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/networkmanager_transit_gateway_peering)
- [aws_networkmanager_transit_gateway_registration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/networkmanager_transit_gateway_registration)
- [aws_networkmanager_transit_gateway_route_table_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/networkmanager_transit_gateway_route_table_attachment)
- [aws_networkmanager_vpc_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/networkmanager_vpc_attachment)

### Data Sources
- [aws_networkmanager_connection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/networkmanager_connection)
- [aws_networkmanager_connections](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/networkmanager_connections)
- [aws_networkmanager_core_network_policy_document](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/networkmanager_core_network_policy_document)
- [aws_networkmanager_device](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/networkmanager_device)
- [aws_networkmanager_devices](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/networkmanager_devices)
- [aws_networkmanager_global_network](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/networkmanager_global_network)
- [aws_networkmanager_global_networks](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/networkmanager_global_networks)
- [aws_networkmanager_link](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/networkmanager_link)
- [aws_networkmanager_links](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/networkmanager_links)
- [aws_networkmanager_site](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/networkmanager_site)
- [aws_networkmanager_sites](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/networkmanager_sites)

## OpenSearch

*9 resources and 1 data sources*

### Resources
- [aws_opensearch_authorize_vpc_endpoint_access](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opensearch_authorize_vpc_endpoint_access)
- [aws_opensearch_domain](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opensearch_domain)
- [aws_opensearch_domain_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opensearch_domain_policy)
- [aws_opensearch_domain_saml_options](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opensearch_domain_saml_options)
- [aws_opensearch_inbound_connection_accepter](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opensearch_inbound_connection_accepter)
- [aws_opensearch_outbound_connection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opensearch_outbound_connection)
- [aws_opensearch_package](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opensearch_package)
- [aws_opensearch_package_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opensearch_package_association)
- [aws_opensearch_vpc_endpoint](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opensearch_vpc_endpoint)

### Data Sources
- [aws_opensearch_domain](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/opensearch_domain)

## OpenSearch Ingestion

*1 resources and 0 data sources*

### Resources
- [aws_osis_pipeline](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/osis_pipeline)

## OpenSearch Serverless

*6 resources and 6 data sources*

### Resources
- [aws_opensearchserverless_access_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opensearchserverless_access_policy)
- [aws_opensearchserverless_collection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opensearchserverless_collection)
- [aws_opensearchserverless_lifecycle_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opensearchserverless_lifecycle_policy)
- [aws_opensearchserverless_security_config](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opensearchserverless_security_config)
- [aws_opensearchserverless_security_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opensearchserverless_security_policy)
- [aws_opensearchserverless_vpc_endpoint](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opensearchserverless_vpc_endpoint)

### Data Sources
- [aws_opensearchserverless_access_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/opensearchserverless_access_policy)
- [aws_opensearchserverless_collection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/opensearchserverless_collection)
- [aws_opensearchserverless_lifecycle_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/opensearchserverless_lifecycle_policy)
- [aws_opensearchserverless_security_config](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/opensearchserverless_security_config)
- [aws_opensearchserverless_security_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/opensearchserverless_security_policy)
- [aws_opensearchserverless_vpc_endpoint](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/opensearchserverless_vpc_endpoint)

## OpsWorks

*17 resources and 0 data sources*

### Resources
- [aws_opsworks_application](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opsworks_application)
- [aws_opsworks_custom_layer](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opsworks_custom_layer)
- [aws_opsworks_ecs_cluster_layer](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opsworks_ecs_cluster_layer)
- [aws_opsworks_ganglia_layer](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opsworks_ganglia_layer)
- [aws_opsworks_haproxy_layer](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opsworks_haproxy_layer)
- [aws_opsworks_instance](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opsworks_instance)
- [aws_opsworks_java_app_layer](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opsworks_java_app_layer)
- [aws_opsworks_memcached_layer](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opsworks_memcached_layer)
- [aws_opsworks_mysql_layer](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opsworks_mysql_layer)
- [aws_opsworks_nodejs_app_layer](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opsworks_nodejs_app_layer)
- [aws_opsworks_permission](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opsworks_permission)
- [aws_opsworks_php_app_layer](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opsworks_php_app_layer)
- [aws_opsworks_rails_app_layer](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opsworks_rails_app_layer)
- [aws_opsworks_rds_db_instance](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opsworks_rds_db_instance)
- [aws_opsworks_stack](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opsworks_stack)
- [aws_opsworks_static_web_layer](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opsworks_static_web_layer)
- [aws_opsworks_user_profile](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/opsworks_user_profile)

## Organizations

*7 resources and 12 data sources*

### Resources
- [aws_organizations_account](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/organizations_account)
- [aws_organizations_delegated_administrator](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/organizations_delegated_administrator)
- [aws_organizations_organization](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/organizations_organization)
- [aws_organizations_organizational_unit](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/organizations_organizational_unit)
- [aws_organizations_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/organizations_policy)
- [aws_organizations_policy_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/organizations_policy_attachment)
- [aws_organizations_resource_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/organizations_resource_policy)

### Data Sources
- [aws_organizations_delegated_administrators](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/organizations_delegated_administrators)
- [aws_organizations_delegated_services](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/organizations_delegated_services)
- [aws_organizations_organization](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/organizations_organization)
- [aws_organizations_organizational_unit](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/organizations_organizational_unit)
- [aws_organizations_organizational_unit_child_accounts](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/organizations_organizational_unit_child_accounts)
- [aws_organizations_organizational_unit_descendant_accounts](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/organizations_organizational_unit_descendant_accounts)
- [aws_organizations_organizational_unit_descendant_organizational_units](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/organizations_organizational_unit_descendant_organizational_units)
- [aws_organizations_organizational_units](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/organizations_organizational_units)
- [aws_organizations_policies](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/organizations_policies)
- [aws_organizations_policies_for_target](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/organizations_policies_for_target)
- [aws_organizations_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/organizations_policy)
- [aws_organizations_resource_tags](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/organizations_resource_tags)

## Outposts

*0 resources and 8 data sources*


### Data Sources
- [aws_outposts_asset](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/outposts_asset)
- [aws_outposts_assets](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/outposts_assets)
- [aws_outposts_outpost](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/outposts_outpost)
- [aws_outposts_outpost_instance_type](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/outposts_outpost_instance_type)
- [aws_outposts_outpost_instance_types](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/outposts_outpost_instance_types)
- [aws_outposts_outposts](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/outposts_outposts)
- [aws_outposts_site](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/outposts_site)
- [aws_outposts_sites](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/outposts_sites)

## Outposts EC2

*2 resources and 9 data sources*

### Resources
- [aws_ec2_local_gateway_route](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_local_gateway_route)
- [aws_ec2_local_gateway_route_table_vpc_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_local_gateway_route_table_vpc_association)

### Data Sources
- [aws_ec2_coip_pool](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_coip_pool)
- [aws_ec2_coip_pools](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_coip_pools)
- [aws_ec2_local_gateway](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_local_gateway)
- [aws_ec2_local_gateway_route_table](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_local_gateway_route_table)
- [aws_ec2_local_gateway_route_tables](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_local_gateway_route_tables)
- [aws_ec2_local_gateway_virtual_interface](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_local_gateway_virtual_interface)
- [aws_ec2_local_gateway_virtual_interface_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_local_gateway_virtual_interface_group)
- [aws_ec2_local_gateway_virtual_interface_groups](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_local_gateway_virtual_interface_groups)
- [aws_ec2_local_gateways](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_local_gateways)

## Payment Cryptography Control Plane

*2 resources and 0 data sources*

### Resources
- [aws_paymentcryptography_key](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/paymentcryptography_key)
- [aws_paymentcryptography_key_alias](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/paymentcryptography_key_alias)

## Pinpoint

*12 resources and 0 data sources*

### Resources
- [aws_pinpoint_adm_channel](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/pinpoint_adm_channel)
- [aws_pinpoint_apns_channel](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/pinpoint_apns_channel)
- [aws_pinpoint_apns_sandbox_channel](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/pinpoint_apns_sandbox_channel)
- [aws_pinpoint_apns_voip_channel](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/pinpoint_apns_voip_channel)
- [aws_pinpoint_apns_voip_sandbox_channel](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/pinpoint_apns_voip_sandbox_channel)
- [aws_pinpoint_app](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/pinpoint_app)
- [aws_pinpoint_baidu_channel](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/pinpoint_baidu_channel)
- [aws_pinpoint_email_channel](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/pinpoint_email_channel)
- [aws_pinpoint_email_template](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/pinpoint_email_template)
- [aws_pinpoint_event_stream](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/pinpoint_event_stream)
- [aws_pinpoint_gcm_channel](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/pinpoint_gcm_channel)
- [aws_pinpoint_sms_channel](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/pinpoint_sms_channel)

## Polly

*0 resources and 1 data sources*


### Data Sources
- [aws_polly_voices](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/polly_voices)

## Pricing Calculator

*0 resources and 1 data sources*


### Data Sources
- [aws_pricing_product](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/pricing_product)

## QLDB Quantum Ledger Database

*2 resources and 1 data sources*

### Resources
- [aws_qldb_ledger](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/qldb_ledger)
- [aws_qldb_stream](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/qldb_stream)

### Data Sources
- [aws_qldb_ledger](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/qldb_ledger)

## QuickSight

*19 resources and 5 data sources*

### Resources
- [aws_quicksight_account_subscription](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/quicksight_account_subscription)
- [aws_quicksight_analysis](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/quicksight_analysis)
- [aws_quicksight_dashboard](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/quicksight_dashboard)
- [aws_quicksight_data_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/quicksight_data_set)
- [aws_quicksight_data_source](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/quicksight_data_source)
- [aws_quicksight_folder](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/quicksight_folder)
- [aws_quicksight_folder_membership](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/quicksight_folder_membership)
- [aws_quicksight_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/quicksight_group)
- [aws_quicksight_group_membership](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/quicksight_group_membership)
- [aws_quicksight_iam_policy_assignment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/quicksight_iam_policy_assignment)
- [aws_quicksight_ingestion](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/quicksight_ingestion)
- [aws_quicksight_namespace](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/quicksight_namespace)
- [aws_quicksight_refresh_schedule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/quicksight_refresh_schedule)
- [aws_quicksight_role_membership](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/quicksight_role_membership)
- [aws_quicksight_template](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/quicksight_template)
- [aws_quicksight_template_alias](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/quicksight_template_alias)
- [aws_quicksight_theme](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/quicksight_theme)
- [aws_quicksight_user](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/quicksight_user)
- [aws_quicksight_vpc_connection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/quicksight_vpc_connection)

### Data Sources
- [aws_quicksight_analysis](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/quicksight_analysis)
- [aws_quicksight_data_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/quicksight_data_set)
- [aws_quicksight_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/quicksight_group)
- [aws_quicksight_theme](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/quicksight_theme)
- [aws_quicksight_user](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/quicksight_user)

## RAM Resource Access Manager

*5 resources and 1 data sources*

### Resources
- [aws_ram_principal_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ram_principal_association)
- [aws_ram_resource_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ram_resource_association)
- [aws_ram_resource_share](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ram_resource_share)
- [aws_ram_resource_share_accepter](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ram_resource_share_accepter)
- [aws_ram_sharing_with_organization](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ram_sharing_with_organization)

### Data Sources
- [aws_ram_resource_share](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ram_resource_share)

## RDS Relational Database

*29 resources and 15 data sources*

### Resources
- [aws_db_cluster_snapshot](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/db_cluster_snapshot)
- [aws_db_event_subscription](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/db_event_subscription)
- [aws_db_instance](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/db_instance)
- [aws_db_instance_automated_backups_replication](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/db_instance_automated_backups_replication)
- [aws_db_instance_role_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/db_instance_role_association)
- [aws_db_option_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/db_option_group)
- [aws_db_parameter_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/db_parameter_group)
- [aws_db_proxy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/db_proxy)
- [aws_db_proxy_default_target_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/db_proxy_default_target_group)
- [aws_db_proxy_endpoint](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/db_proxy_endpoint)
- [aws_db_proxy_target](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/db_proxy_target)
- [aws_db_snapshot](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/db_snapshot)
- [aws_db_snapshot_copy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/db_snapshot_copy)
- [aws_db_subnet_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/db_subnet_group)
- [aws_rds_certificate](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/rds_certificate)
- [aws_rds_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/rds_cluster)
- [aws_rds_cluster_activity_stream](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/rds_cluster_activity_stream)
- [aws_rds_cluster_endpoint](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/rds_cluster_endpoint)
- [aws_rds_cluster_instance](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/rds_cluster_instance)
- [aws_rds_cluster_parameter_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/rds_cluster_parameter_group)
- [aws_rds_cluster_role_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/rds_cluster_role_association)
- [aws_rds_cluster_snapshot_copy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/rds_cluster_snapshot_copy)
- [aws_rds_custom_db_engine_version](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/rds_custom_db_engine_version)
- [aws_rds_export_task](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/rds_export_task)
- [aws_rds_global_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/rds_global_cluster)
- [aws_rds_instance_state](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/rds_instance_state)
- [aws_rds_integration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/rds_integration)
- [aws_rds_reserved_instance](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/rds_reserved_instance)
- [aws_rds_shard_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/rds_shard_group)

### Data Sources
- [aws_db_cluster_snapshot](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/db_cluster_snapshot)
- [aws_db_event_categories](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/db_event_categories)
- [aws_db_instance](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/db_instance)
- [aws_db_instances](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/db_instances)
- [aws_db_parameter_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/db_parameter_group)
- [aws_db_proxy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/db_proxy)
- [aws_db_snapshot](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/db_snapshot)
- [aws_db_subnet_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/db_subnet_group)
- [aws_rds_certificate](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/rds_certificate)
- [aws_rds_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/rds_cluster)
- [aws_rds_cluster_parameter_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/rds_cluster_parameter_group)
- [aws_rds_clusters](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/rds_clusters)
- [aws_rds_engine_version](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/rds_engine_version)
- [aws_rds_orderable_db_instance](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/rds_orderable_db_instance)
- [aws_rds_reserved_instance_offering](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/rds_reserved_instance_offering)

## Recycle Bin RBin

*1 resources and 0 data sources*

### Resources
- [aws_rbin_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/rbin_rule)

## Redshift

*22 resources and 7 data sources*

### Resources
- [aws_redshift_authentication_profile](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshift_authentication_profile)
- [aws_redshift_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshift_cluster)
- [aws_redshift_cluster_iam_roles](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshift_cluster_iam_roles)
- [aws_redshift_cluster_snapshot](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshift_cluster_snapshot)
- [aws_redshift_data_share_authorization](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshift_data_share_authorization)
- [aws_redshift_data_share_consumer_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshift_data_share_consumer_association)
- [aws_redshift_endpoint_access](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshift_endpoint_access)
- [aws_redshift_endpoint_authorization](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshift_endpoint_authorization)
- [aws_redshift_event_subscription](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshift_event_subscription)
- [aws_redshift_hsm_client_certificate](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshift_hsm_client_certificate)
- [aws_redshift_hsm_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshift_hsm_configuration)
- [aws_redshift_logging](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshift_logging)
- [aws_redshift_parameter_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshift_parameter_group)
- [aws_redshift_partner](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshift_partner)
- [aws_redshift_resource_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshift_resource_policy)
- [aws_redshift_scheduled_action](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshift_scheduled_action)
- [aws_redshift_snapshot_copy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshift_snapshot_copy)
- [aws_redshift_snapshot_copy_grant](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshift_snapshot_copy_grant)
- [aws_redshift_snapshot_schedule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshift_snapshot_schedule)
- [aws_redshift_snapshot_schedule_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshift_snapshot_schedule_association)
- [aws_redshift_subnet_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshift_subnet_group)
- [aws_redshift_usage_limit](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshift_usage_limit)

### Data Sources
- [aws_redshift_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/redshift_cluster)
- [aws_redshift_cluster_credentials](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/redshift_cluster_credentials)
- [aws_redshift_data_shares](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/redshift_data_shares)
- [aws_redshift_orderable_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/redshift_orderable_cluster)
- [aws_redshift_producer_data_shares](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/redshift_producer_data_shares)
- [aws_redshift_service_account](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/redshift_service_account)
- [aws_redshift_subnet_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/redshift_subnet_group)

## Redshift Data

*1 resources and 0 data sources*

### Resources
- [aws_redshiftdata_statement](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshiftdata_statement)

## Redshift Serverless

*7 resources and 3 data sources*

### Resources
- [aws_redshiftserverless_custom_domain_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshiftserverless_custom_domain_association)
- [aws_redshiftserverless_endpoint_access](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshiftserverless_endpoint_access)
- [aws_redshiftserverless_namespace](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshiftserverless_namespace)
- [aws_redshiftserverless_resource_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshiftserverless_resource_policy)
- [aws_redshiftserverless_snapshot](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshiftserverless_snapshot)
- [aws_redshiftserverless_usage_limit](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshiftserverless_usage_limit)
- [aws_redshiftserverless_workgroup](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/redshiftserverless_workgroup)

### Data Sources
- [aws_redshiftserverless_credentials](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/redshiftserverless_credentials)
- [aws_redshiftserverless_namespace](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/redshiftserverless_namespace)
- [aws_redshiftserverless_workgroup](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/redshiftserverless_workgroup)

## Rekognition

*3 resources and 0 data sources*

### Resources
- [aws_rekognition_collection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/rekognition_collection)
- [aws_rekognition_project](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/rekognition_project)
- [aws_rekognition_stream_processor](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/rekognition_stream_processor)

## Resilience Hub

*1 resources and 0 data sources*

### Resources
- [aws_resiliencehub_resiliency_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/resiliencehub_resiliency_policy)

## Resource Explorer

*2 resources and 1 data sources*

### Resources
- [aws_resourceexplorer2_index](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/resourceexplorer2_index)
- [aws_resourceexplorer2_view](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/resourceexplorer2_view)

### Data Sources
- [aws_resourceexplorer2_search](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/resourceexplorer2_search)

## Resource Groups

*2 resources and 0 data sources*

### Resources
- [aws_resourcegroups_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/resourcegroups_group)
- [aws_resourcegroups_resource](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/resourcegroups_resource)

## Resource Groups Tagging

*0 resources and 1 data sources*


### Data Sources
- [aws_resourcegroupstaggingapi_resources](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/resourcegroupstaggingapi_resources)

## Roles Anywhere

*2 resources and 0 data sources*

### Resources
- [aws_rolesanywhere_profile](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/rolesanywhere_profile)
- [aws_rolesanywhere_trust_anchor](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/rolesanywhere_trust_anchor)

## Route 53

*14 resources and 5 data sources*

### Resources
- [aws_route53_cidr_collection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_cidr_collection)
- [aws_route53_cidr_location](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_cidr_location)
- [aws_route53_delegation_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_delegation_set)
- [aws_route53_health_check](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_health_check)
- [aws_route53_hosted_zone_dnssec](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_hosted_zone_dnssec)
- [aws_route53_key_signing_key](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_key_signing_key)
- [aws_route53_query_log](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_query_log)
- [aws_route53_record](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_record)
- [aws_route53_records_exclusive](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_records_exclusive)
- [aws_route53_traffic_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_traffic_policy)
- [aws_route53_traffic_policy_instance](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_traffic_policy_instance)
- [aws_route53_vpc_association_authorization](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_vpc_association_authorization)
- [aws_route53_zone](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_zone)
- [aws_route53_zone_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_zone_association)

### Data Sources
- [aws_route53_delegation_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/route53_delegation_set)
- [aws_route53_records](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/route53_records)
- [aws_route53_traffic_policy_document](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/route53_traffic_policy_document)
- [aws_route53_zone](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/route53_zone)
- [aws_route53_zones](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/route53_zones)

## Route 53 Domains

*3 resources and 0 data sources*

### Resources
- [aws_route53domains_delegation_signer_record](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53domains_delegation_signer_record)
- [aws_route53domains_domain](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53domains_domain)
- [aws_route53domains_registered_domain](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53domains_registered_domain)

## Route 53 Profiles

*3 resources and 1 data sources*

### Resources
- [aws_route53profiles_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53profiles_association)
- [aws_route53profiles_profile](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53profiles_profile)
- [aws_route53profiles_resource_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53profiles_resource_association)

### Data Sources
- [aws_route53profiles_profiles](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/route53profiles_profiles)

## Route 53 Recovery Control Config

*4 resources and 0 data sources*

### Resources
- [aws_route53recoverycontrolconfig_cluster](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53recoverycontrolconfig_cluster)
- [aws_route53recoverycontrolconfig_control_panel](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53recoverycontrolconfig_control_panel)
- [aws_route53recoverycontrolconfig_routing_control](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53recoverycontrolconfig_routing_control)
- [aws_route53recoverycontrolconfig_safety_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53recoverycontrolconfig_safety_rule)

## Route 53 Recovery Readiness

*4 resources and 0 data sources*

### Resources
- [aws_route53recoveryreadiness_cell](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53recoveryreadiness_cell)
- [aws_route53recoveryreadiness_readiness_check](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53recoveryreadiness_readiness_check)
- [aws_route53recoveryreadiness_recovery_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53recoveryreadiness_recovery_group)
- [aws_route53recoveryreadiness_resource_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53recoveryreadiness_resource_set)

## Route 53 Resolver

*12 resources and 9 data sources*

### Resources
- [aws_route53_resolver_config](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_resolver_config)
- [aws_route53_resolver_dnssec_config](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_resolver_dnssec_config)
- [aws_route53_resolver_endpoint](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_resolver_endpoint)
- [aws_route53_resolver_firewall_config](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_resolver_firewall_config)
- [aws_route53_resolver_firewall_domain_list](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_resolver_firewall_domain_list)
- [aws_route53_resolver_firewall_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_resolver_firewall_rule)
- [aws_route53_resolver_firewall_rule_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_resolver_firewall_rule_group)
- [aws_route53_resolver_firewall_rule_group_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_resolver_firewall_rule_group_association)
- [aws_route53_resolver_query_log_config](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_resolver_query_log_config)
- [aws_route53_resolver_query_log_config_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_resolver_query_log_config_association)
- [aws_route53_resolver_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_resolver_rule)
- [aws_route53_resolver_rule_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route53_resolver_rule_association)

### Data Sources
- [aws_route53_resolver_endpoint](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/route53_resolver_endpoint)
- [aws_route53_resolver_firewall_config](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/route53_resolver_firewall_config)
- [aws_route53_resolver_firewall_domain_list](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/route53_resolver_firewall_domain_list)
- [aws_route53_resolver_firewall_rule_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/route53_resolver_firewall_rule_group)
- [aws_route53_resolver_firewall_rule_group_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/route53_resolver_firewall_rule_group_association)
- [aws_route53_resolver_firewall_rules](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/route53_resolver_firewall_rules)
- [aws_route53_resolver_query_log_config](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/route53_resolver_query_log_config)
- [aws_route53_resolver_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/route53_resolver_rule)
- [aws_route53_resolver_rules](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/route53_resolver_rules)

## S3 Simple Storage

*24 resources and 8 data sources*

### Resources
- [aws_s3_bucket](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket)
- [aws_s3_bucket_accelerate_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_accelerate_configuration)
- [aws_s3_bucket_acl](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_acl)
- [aws_s3_bucket_analytics_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_analytics_configuration)
- [aws_s3_bucket_cors_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_cors_configuration)
- [aws_s3_bucket_intelligent_tiering_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_intelligent_tiering_configuration)
- [aws_s3_bucket_inventory](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_inventory)
- [aws_s3_bucket_lifecycle_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_lifecycle_configuration)
- [aws_s3_bucket_logging](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_logging)
- [aws_s3_bucket_metric](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_metric)
- [aws_s3_bucket_notification](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_notification)
- [aws_s3_bucket_object](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_object)
- [aws_s3_bucket_object_lock_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_object_lock_configuration)
- [aws_s3_bucket_ownership_controls](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_ownership_controls)
- [aws_s3_bucket_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_policy)
- [aws_s3_bucket_public_access_block](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_public_access_block)
- [aws_s3_bucket_replication_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_replication_configuration)
- [aws_s3_bucket_request_payment_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_request_payment_configuration)
- [aws_s3_bucket_server_side_encryption_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_server_side_encryption_configuration)
- [aws_s3_bucket_versioning](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_versioning)
- [aws_s3_bucket_website_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_website_configuration)
- [aws_s3_directory_bucket](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_directory_bucket)
- [aws_s3_object](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_object)
- [aws_s3_object_copy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_object_copy)

### Data Sources
- [aws_canonical_user_id](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/canonical_user_id)
- [aws_s3_bucket](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/s3_bucket)
- [aws_s3_bucket_object](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/s3_bucket_object)
- [aws_s3_bucket_objects](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/s3_bucket_objects)
- [aws_s3_bucket_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/s3_bucket_policy)
- [aws_s3_directory_buckets](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/s3_directory_buckets)
- [aws_s3_object](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/s3_object)
- [aws_s3_objects](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/s3_objects)

## S3 Control

*15 resources and 2 data sources*

### Resources
- [aws_s3_access_point](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_access_point)
- [aws_s3_account_public_access_block](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_account_public_access_block)
- [aws_s3control_access_grant](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3control_access_grant)
- [aws_s3control_access_grants_instance](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3control_access_grants_instance)
- [aws_s3control_access_grants_instance_resource_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3control_access_grants_instance_resource_policy)
- [aws_s3control_access_grants_location](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3control_access_grants_location)
- [aws_s3control_access_point_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3control_access_point_policy)
- [aws_s3control_bucket](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3control_bucket)
- [aws_s3control_bucket_lifecycle_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3control_bucket_lifecycle_configuration)
- [aws_s3control_bucket_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3control_bucket_policy)
- [aws_s3control_multi_region_access_point](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3control_multi_region_access_point)
- [aws_s3control_multi_region_access_point_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3control_multi_region_access_point_policy)
- [aws_s3control_object_lambda_access_point](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3control_object_lambda_access_point)
- [aws_s3control_object_lambda_access_point_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3control_object_lambda_access_point_policy)
- [aws_s3control_storage_lens_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3control_storage_lens_configuration)

### Data Sources
- [aws_s3_account_public_access_block](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/s3_account_public_access_block)
- [aws_s3control_multi_region_access_point](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/s3control_multi_region_access_point)

## S3 Glacier

*2 resources and 0 data sources*

### Resources
- [aws_glacier_vault](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/glacier_vault)
- [aws_glacier_vault_lock](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/glacier_vault_lock)

## S3 Tables

*5 resources and 0 data sources*

### Resources
- [aws_s3tables_namespace](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3tables_namespace)
- [aws_s3tables_table](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3tables_table)
- [aws_s3tables_table_bucket](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3tables_table_bucket)
- [aws_s3tables_table_bucket_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3tables_table_bucket_policy)
- [aws_s3tables_table_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3tables_table_policy)

## S3 on Outposts

*1 resources and 0 data sources*

### Resources
- [aws_s3outposts_endpoint](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3outposts_endpoint)

## SDB SimpleDB

*1 resources and 0 data sources*

### Resources
- [aws_simpledb_domain](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/simpledb_domain)

## SES Simple Email

*14 resources and 3 data sources*

### Resources
- [aws_ses_active_receipt_rule_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ses_active_receipt_rule_set)
- [aws_ses_configuration_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ses_configuration_set)
- [aws_ses_domain_dkim](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ses_domain_dkim)
- [aws_ses_domain_identity](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ses_domain_identity)
- [aws_ses_domain_identity_verification](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ses_domain_identity_verification)
- [aws_ses_domain_mail_from](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ses_domain_mail_from)
- [aws_ses_email_identity](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ses_email_identity)
- [aws_ses_event_destination](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ses_event_destination)
- [aws_ses_identity_notification_topic](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ses_identity_notification_topic)
- [aws_ses_identity_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ses_identity_policy)
- [aws_ses_receipt_filter](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ses_receipt_filter)
- [aws_ses_receipt_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ses_receipt_rule)
- [aws_ses_receipt_rule_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ses_receipt_rule_set)
- [aws_ses_template](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ses_template)

### Data Sources
- [aws_ses_active_receipt_rule_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ses_active_receipt_rule_set)
- [aws_ses_domain_identity](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ses_domain_identity)
- [aws_ses_email_identity](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ses_email_identity)

## SESv2 Simple Email V2

*11 resources and 4 data sources*

### Resources
- [aws_sesv2_account_suppression_attributes](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sesv2_account_suppression_attributes)
- [aws_sesv2_account_vdm_attributes](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sesv2_account_vdm_attributes)
- [aws_sesv2_configuration_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sesv2_configuration_set)
- [aws_sesv2_configuration_set_event_destination](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sesv2_configuration_set_event_destination)
- [aws_sesv2_contact_list](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sesv2_contact_list)
- [aws_sesv2_dedicated_ip_assignment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sesv2_dedicated_ip_assignment)
- [aws_sesv2_dedicated_ip_pool](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sesv2_dedicated_ip_pool)
- [aws_sesv2_email_identity](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sesv2_email_identity)
- [aws_sesv2_email_identity_feedback_attributes](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sesv2_email_identity_feedback_attributes)
- [aws_sesv2_email_identity_mail_from_attributes](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sesv2_email_identity_mail_from_attributes)
- [aws_sesv2_email_identity_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sesv2_email_identity_policy)

### Data Sources
- [aws_sesv2_configuration_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/sesv2_configuration_set)
- [aws_sesv2_dedicated_ip_pool](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/sesv2_dedicated_ip_pool)
- [aws_sesv2_email_identity](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/sesv2_email_identity)
- [aws_sesv2_email_identity_mail_from_attributes](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/sesv2_email_identity_mail_from_attributes)

## SFN Step Functions

*3 resources and 4 data sources*

### Resources
- [aws_sfn_activity](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sfn_activity)
- [aws_sfn_alias](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sfn_alias)
- [aws_sfn_state_machine](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sfn_state_machine)

### Data Sources
- [aws_sfn_activity](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/sfn_activity)
- [aws_sfn_alias](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/sfn_alias)
- [aws_sfn_state_machine](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/sfn_state_machine)
- [aws_sfn_state_machine_versions](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/sfn_state_machine_versions)

## SNS Simple Notification

*6 resources and 1 data sources*

### Resources
- [aws_sns_platform_application](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sns_platform_application)
- [aws_sns_sms_preferences](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sns_sms_preferences)
- [aws_sns_topic](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sns_topic)
- [aws_sns_topic_data_protection_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sns_topic_data_protection_policy)
- [aws_sns_topic_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sns_topic_policy)
- [aws_sns_topic_subscription](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sns_topic_subscription)

### Data Sources
- [aws_sns_topic](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/sns_topic)

## SQS Simple Queue

*4 resources and 2 data sources*

### Resources
- [aws_sqs_queue](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sqs_queue)
- [aws_sqs_queue_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sqs_queue_policy)
- [aws_sqs_queue_redrive_allow_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sqs_queue_redrive_allow_policy)
- [aws_sqs_queue_redrive_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sqs_queue_redrive_policy)

### Data Sources
- [aws_sqs_queue](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/sqs_queue)
- [aws_sqs_queues](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/sqs_queues)

## SSM Systems Manager

*12 resources and 7 data sources*

### Resources
- [aws_ssm_activation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssm_activation)
- [aws_ssm_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssm_association)
- [aws_ssm_default_patch_baseline](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssm_default_patch_baseline)
- [aws_ssm_document](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssm_document)
- [aws_ssm_maintenance_window](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssm_maintenance_window)
- [aws_ssm_maintenance_window_target](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssm_maintenance_window_target)
- [aws_ssm_maintenance_window_task](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssm_maintenance_window_task)
- [aws_ssm_parameter](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssm_parameter)
- [aws_ssm_patch_baseline](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssm_patch_baseline)
- [aws_ssm_patch_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssm_patch_group)
- [aws_ssm_resource_data_sync](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssm_resource_data_sync)
- [aws_ssm_service_setting](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssm_service_setting)

### Data Sources
- [aws_ssm_document](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ssm_document)
- [aws_ssm_instances](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ssm_instances)
- [aws_ssm_maintenance_windows](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ssm_maintenance_windows)
- [aws_ssm_parameter](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ssm_parameter)
- [aws_ssm_parameters_by_path](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ssm_parameters_by_path)
- [aws_ssm_patch_baseline](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ssm_patch_baseline)
- [aws_ssm_patch_baselines](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ssm_patch_baselines)

## SSM Contacts

*4 resources and 4 data sources*

### Resources
- [aws_ssmcontacts_contact](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssmcontacts_contact)
- [aws_ssmcontacts_contact_channel](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssmcontacts_contact_channel)
- [aws_ssmcontacts_plan](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssmcontacts_plan)
- [aws_ssmcontacts_rotation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssmcontacts_rotation)

### Data Sources
- [aws_ssmcontacts_contact](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ssmcontacts_contact)
- [aws_ssmcontacts_contact_channel](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ssmcontacts_contact_channel)
- [aws_ssmcontacts_plan](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ssmcontacts_plan)
- [aws_ssmcontacts_rotation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ssmcontacts_rotation)

## SSM Incident Manager Incidents

*2 resources and 2 data sources*

### Resources
- [aws_ssmincidents_replication_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssmincidents_replication_set)
- [aws_ssmincidents_response_plan](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssmincidents_response_plan)

### Data Sources
- [aws_ssmincidents_replication_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ssmincidents_replication_set)
- [aws_ssmincidents_response_plan](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ssmincidents_response_plan)

## SSM Quick Setup

*1 resources and 0 data sources*

### Resources
- [aws_ssmquicksetup_configuration_manager](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssmquicksetup_configuration_manager)

## SSO Admin

*12 resources and 7 data sources*

### Resources
- [aws_ssoadmin_account_assignment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssoadmin_account_assignment)
- [aws_ssoadmin_application](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssoadmin_application)
- [aws_ssoadmin_application_access_scope](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssoadmin_application_access_scope)
- [aws_ssoadmin_application_assignment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssoadmin_application_assignment)
- [aws_ssoadmin_application_assignment_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssoadmin_application_assignment_configuration)
- [aws_ssoadmin_customer_managed_policy_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssoadmin_customer_managed_policy_attachment)
- [aws_ssoadmin_instance_access_control_attributes](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssoadmin_instance_access_control_attributes)
- [aws_ssoadmin_managed_policy_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssoadmin_managed_policy_attachment)
- [aws_ssoadmin_permission_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssoadmin_permission_set)
- [aws_ssoadmin_permission_set_inline_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssoadmin_permission_set_inline_policy)
- [aws_ssoadmin_permissions_boundary_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssoadmin_permissions_boundary_attachment)
- [aws_ssoadmin_trusted_token_issuer](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssoadmin_trusted_token_issuer)

### Data Sources
- [aws_ssoadmin_application](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ssoadmin_application)
- [aws_ssoadmin_application_assignments](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ssoadmin_application_assignments)
- [aws_ssoadmin_application_providers](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ssoadmin_application_providers)
- [aws_ssoadmin_instances](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ssoadmin_instances)
- [aws_ssoadmin_permission_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ssoadmin_permission_set)
- [aws_ssoadmin_permission_sets](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ssoadmin_permission_sets)
- [aws_ssoadmin_principal_application_assignments](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ssoadmin_principal_application_assignments)

## SSO Identity Store

*3 resources and 5 data sources*

### Resources
- [aws_identitystore_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/identitystore_group)
- [aws_identitystore_group_membership](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/identitystore_group_membership)
- [aws_identitystore_user](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/identitystore_user)

### Data Sources
- [aws_identitystore_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/identitystore_group)
- [aws_identitystore_group_memberships](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/identitystore_group_memberships)
- [aws_identitystore_groups](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/identitystore_groups)
- [aws_identitystore_user](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/identitystore_user)
- [aws_identitystore_users](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/identitystore_users)

## STS Security Token

*0 resources and 1 data sources*


### Data Sources
- [aws_caller_identity](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/caller_identity)

## SWF Simple Workflow

*1 resources and 0 data sources*

### Resources
- [aws_swf_domain](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/swf_domain)

## SageMaker AI

*30 resources and 1 data sources*

### Resources
- [aws_sagemaker_app](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_app)
- [aws_sagemaker_app_image_config](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_app_image_config)
- [aws_sagemaker_code_repository](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_code_repository)
- [aws_sagemaker_data_quality_job_definition](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_data_quality_job_definition)
- [aws_sagemaker_device](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_device)
- [aws_sagemaker_device_fleet](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_device_fleet)
- [aws_sagemaker_domain](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_domain)
- [aws_sagemaker_endpoint](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_endpoint)
- [aws_sagemaker_endpoint_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_endpoint_configuration)
- [aws_sagemaker_feature_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_feature_group)
- [aws_sagemaker_flow_definition](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_flow_definition)
- [aws_sagemaker_hub](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_hub)
- [aws_sagemaker_human_task_ui](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_human_task_ui)
- [aws_sagemaker_image](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_image)
- [aws_sagemaker_image_version](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_image_version)
- [aws_sagemaker_mlflow_tracking_server](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_mlflow_tracking_server)
- [aws_sagemaker_model](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_model)
- [aws_sagemaker_model_package_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_model_package_group)
- [aws_sagemaker_model_package_group_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_model_package_group_policy)
- [aws_sagemaker_monitoring_schedule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_monitoring_schedule)
- [aws_sagemaker_notebook_instance](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_notebook_instance)
- [aws_sagemaker_notebook_instance_lifecycle_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_notebook_instance_lifecycle_configuration)
- [aws_sagemaker_pipeline](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_pipeline)
- [aws_sagemaker_project](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_project)
- [aws_sagemaker_servicecatalog_portfolio_status](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_servicecatalog_portfolio_status)
- [aws_sagemaker_space](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_space)
- [aws_sagemaker_studio_lifecycle_config](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_studio_lifecycle_config)
- [aws_sagemaker_user_profile](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_user_profile)
- [aws_sagemaker_workforce](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_workforce)
- [aws_sagemaker_workteam](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sagemaker_workteam)

### Data Sources
- [aws_sagemaker_prebuilt_ecr_image](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/sagemaker_prebuilt_ecr_image)

## Secrets Manager

*4 resources and 6 data sources*

### Resources
- [aws_secretsmanager_secret](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/secretsmanager_secret)
- [aws_secretsmanager_secret_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/secretsmanager_secret_policy)
- [aws_secretsmanager_secret_rotation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/secretsmanager_secret_rotation)
- [aws_secretsmanager_secret_version](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/secretsmanager_secret_version)

### Data Sources
- [aws_secretsmanager_random_password](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/secretsmanager_random_password)
- [aws_secretsmanager_secret](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/secretsmanager_secret)
- [aws_secretsmanager_secret_rotation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/secretsmanager_secret_rotation)
- [aws_secretsmanager_secret_version](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/secretsmanager_secret_version)
- [aws_secretsmanager_secret_versions](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/secretsmanager_secret_versions)
- [aws_secretsmanager_secrets](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/secretsmanager_secrets)

## Security Hub

*15 resources and 1 data sources*

### Resources
- [aws_securityhub_account](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/securityhub_account)
- [aws_securityhub_action_target](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/securityhub_action_target)
- [aws_securityhub_automation_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/securityhub_automation_rule)
- [aws_securityhub_configuration_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/securityhub_configuration_policy)
- [aws_securityhub_configuration_policy_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/securityhub_configuration_policy_association)
- [aws_securityhub_finding_aggregator](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/securityhub_finding_aggregator)
- [aws_securityhub_insight](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/securityhub_insight)
- [aws_securityhub_invite_accepter](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/securityhub_invite_accepter)
- [aws_securityhub_member](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/securityhub_member)
- [aws_securityhub_organization_admin_account](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/securityhub_organization_admin_account)
- [aws_securityhub_organization_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/securityhub_organization_configuration)
- [aws_securityhub_product_subscription](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/securityhub_product_subscription)
- [aws_securityhub_standards_control](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/securityhub_standards_control)
- [aws_securityhub_standards_control_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/securityhub_standards_control_association)
- [aws_securityhub_standards_subscription](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/securityhub_standards_subscription)

### Data Sources
- [aws_securityhub_standards_control_associations](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/securityhub_standards_control_associations)

## Security Lake

*5 resources and 0 data sources*

### Resources
- [aws_securitylake_aws_log_source](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/securitylake_aws_log_source)
- [aws_securitylake_custom_log_source](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/securitylake_custom_log_source)
- [aws_securitylake_data_lake](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/securitylake_data_lake)
- [aws_securitylake_subscriber](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/securitylake_subscriber)
- [aws_securitylake_subscriber_notification](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/securitylake_subscriber_notification)

## Serverless Application Repository

*1 resources and 1 data sources*

### Resources
- [aws_serverlessapplicationrepository_cloudformation_stack](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/serverlessapplicationrepository_cloudformation_stack)

### Data Sources
- [aws_serverlessapplicationrepository_application](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/serverlessapplicationrepository_application)

## Service Catalog

*13 resources and 6 data sources*

### Resources
- [aws_servicecatalog_budget_resource_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/servicecatalog_budget_resource_association)
- [aws_servicecatalog_constraint](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/servicecatalog_constraint)
- [aws_servicecatalog_organizations_access](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/servicecatalog_organizations_access)
- [aws_servicecatalog_portfolio](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/servicecatalog_portfolio)
- [aws_servicecatalog_portfolio_share](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/servicecatalog_portfolio_share)
- [aws_servicecatalog_principal_portfolio_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/servicecatalog_principal_portfolio_association)
- [aws_servicecatalog_product](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/servicecatalog_product)
- [aws_servicecatalog_product_portfolio_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/servicecatalog_product_portfolio_association)
- [aws_servicecatalog_provisioned_product](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/servicecatalog_provisioned_product)
- [aws_servicecatalog_provisioning_artifact](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/servicecatalog_provisioning_artifact)
- [aws_servicecatalog_service_action](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/servicecatalog_service_action)
- [aws_servicecatalog_tag_option](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/servicecatalog_tag_option)
- [aws_servicecatalog_tag_option_resource_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/servicecatalog_tag_option_resource_association)

### Data Sources
- [aws_servicecatalog_constraint](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/servicecatalog_constraint)
- [aws_servicecatalog_launch_paths](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/servicecatalog_launch_paths)
- [aws_servicecatalog_portfolio](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/servicecatalog_portfolio)
- [aws_servicecatalog_portfolio_constraints](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/servicecatalog_portfolio_constraints)
- [aws_servicecatalog_product](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/servicecatalog_product)
- [aws_servicecatalog_provisioning_artifacts](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/servicecatalog_provisioning_artifacts)

## Service Catalog AppRegistry

*3 resources and 3 data sources*

### Resources
- [aws_servicecatalogappregistry_application](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/servicecatalogappregistry_application)
- [aws_servicecatalogappregistry_attribute_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/servicecatalogappregistry_attribute_group)
- [aws_servicecatalogappregistry_attribute_group_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/servicecatalogappregistry_attribute_group_association)

### Data Sources
- [aws_servicecatalogappregistry_application](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/servicecatalogappregistry_application)
- [aws_servicecatalogappregistry_attribute_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/servicecatalogappregistry_attribute_group)
- [aws_servicecatalogappregistry_attribute_group_associations](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/servicecatalogappregistry_attribute_group_associations)

## Service Quotas

*3 resources and 3 data sources*

### Resources
- [aws_servicequotas_service_quota](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/servicequotas_service_quota)
- [aws_servicequotas_template](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/servicequotas_template)
- [aws_servicequotas_template_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/servicequotas_template_association)

### Data Sources
- [aws_servicequotas_service](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/servicequotas_service)
- [aws_servicequotas_service_quota](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/servicequotas_service_quota)
- [aws_servicequotas_templates](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/servicequotas_templates)

## Shield

*8 resources and 1 data sources*

### Resources
- [aws_shield_application_layer_automatic_response](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/shield_application_layer_automatic_response)
- [aws_shield_drt_access_log_bucket_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/shield_drt_access_log_bucket_association)
- [aws_shield_drt_access_role_arn_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/shield_drt_access_role_arn_association)
- [aws_shield_proactive_engagement](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/shield_proactive_engagement)
- [aws_shield_protection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/shield_protection)
- [aws_shield_protection_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/shield_protection_group)
- [aws_shield_protection_health_check_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/shield_protection_health_check_association)
- [aws_shield_subscription](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/shield_subscription)

### Data Sources
- [aws_shield_protection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/shield_protection)

## Signer

*3 resources and 2 data sources*

### Resources
- [aws_signer_signing_job](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/signer_signing_job)
- [aws_signer_signing_profile](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/signer_signing_profile)
- [aws_signer_signing_profile_permission](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/signer_signing_profile_permission)

### Data Sources
- [aws_signer_signing_job](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/signer_signing_job)
- [aws_signer_signing_profile](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/signer_signing_profile)

## Storage Gateway

*10 resources and 1 data sources*

### Resources
- [aws_storagegateway_cache](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/storagegateway_cache)
- [aws_storagegateway_cached_iscsi_volume](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/storagegateway_cached_iscsi_volume)
- [aws_storagegateway_file_system_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/storagegateway_file_system_association)
- [aws_storagegateway_gateway](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/storagegateway_gateway)
- [aws_storagegateway_nfs_file_share](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/storagegateway_nfs_file_share)
- [aws_storagegateway_smb_file_share](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/storagegateway_smb_file_share)
- [aws_storagegateway_stored_iscsi_volume](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/storagegateway_stored_iscsi_volume)
- [aws_storagegateway_tape_pool](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/storagegateway_tape_pool)
- [aws_storagegateway_upload_buffer](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/storagegateway_upload_buffer)
- [aws_storagegateway_working_storage](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/storagegateway_working_storage)

### Data Sources
- [aws_storagegateway_local_disk](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/storagegateway_local_disk)

## Timestream Query

*1 resources and 0 data sources*

### Resources
- [aws_timestreamquery_scheduled_query](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/timestreamquery_scheduled_query)

## Timestream Write

*2 resources and 2 data sources*

### Resources
- [aws_timestreamwrite_database](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/timestreamwrite_database)
- [aws_timestreamwrite_table](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/timestreamwrite_table)

### Data Sources
- [aws_timestreamwrite_database](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/timestreamwrite_database)
- [aws_timestreamwrite_table](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/timestreamwrite_table)

## Timestream for InfluxDB

*1 resources and 0 data sources*

### Resources
- [aws_timestreaminfluxdb_db_instance](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/timestreaminfluxdb_db_instance)

## Transcribe

*4 resources and 0 data sources*

### Resources
- [aws_transcribe_language_model](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/transcribe_language_model)
- [aws_transcribe_medical_vocabulary](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/transcribe_medical_vocabulary)
- [aws_transcribe_vocabulary](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/transcribe_vocabulary)
- [aws_transcribe_vocabulary_filter](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/transcribe_vocabulary_filter)

## Transfer Family

*10 resources and 2 data sources*

### Resources
- [aws_transfer_access](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/transfer_access)
- [aws_transfer_agreement](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/transfer_agreement)
- [aws_transfer_certificate](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/transfer_certificate)
- [aws_transfer_connector](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/transfer_connector)
- [aws_transfer_profile](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/transfer_profile)
- [aws_transfer_server](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/transfer_server)
- [aws_transfer_ssh_key](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/transfer_ssh_key)
- [aws_transfer_tag](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/transfer_tag)
- [aws_transfer_user](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/transfer_user)
- [aws_transfer_workflow](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/transfer_workflow)

### Data Sources
- [aws_transfer_connector](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/transfer_connector)
- [aws_transfer_server](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/transfer_server)

## Transit Gateway

*20 resources and 17 data sources*

### Resources
- [aws_ec2_transit_gateway](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_transit_gateway)
- [aws_ec2_transit_gateway_connect](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_transit_gateway_connect)
- [aws_ec2_transit_gateway_connect_peer](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_transit_gateway_connect_peer)
- [aws_ec2_transit_gateway_default_route_table_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_transit_gateway_default_route_table_association)
- [aws_ec2_transit_gateway_default_route_table_propagation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_transit_gateway_default_route_table_propagation)
- [aws_ec2_transit_gateway_multicast_domain](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_transit_gateway_multicast_domain)
- [aws_ec2_transit_gateway_multicast_domain_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_transit_gateway_multicast_domain_association)
- [aws_ec2_transit_gateway_multicast_group_member](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_transit_gateway_multicast_group_member)
- [aws_ec2_transit_gateway_multicast_group_source](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_transit_gateway_multicast_group_source)
- [aws_ec2_transit_gateway_peering_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_transit_gateway_peering_attachment)
- [aws_ec2_transit_gateway_peering_attachment_accepter](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_transit_gateway_peering_attachment_accepter)
- [aws_ec2_transit_gateway_policy_table](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_transit_gateway_policy_table)
- [aws_ec2_transit_gateway_policy_table_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_transit_gateway_policy_table_association)
- [aws_ec2_transit_gateway_prefix_list_reference](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_transit_gateway_prefix_list_reference)
- [aws_ec2_transit_gateway_route](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_transit_gateway_route)
- [aws_ec2_transit_gateway_route_table](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_transit_gateway_route_table)
- [aws_ec2_transit_gateway_route_table_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_transit_gateway_route_table_association)
- [aws_ec2_transit_gateway_route_table_propagation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_transit_gateway_route_table_propagation)
- [aws_ec2_transit_gateway_vpc_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_transit_gateway_vpc_attachment)
- [aws_ec2_transit_gateway_vpc_attachment_accepter](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_transit_gateway_vpc_attachment_accepter)

### Data Sources
- [aws_ec2_transit_gateway](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_transit_gateway)
- [aws_ec2_transit_gateway_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_transit_gateway_attachment)
- [aws_ec2_transit_gateway_attachments](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_transit_gateway_attachments)
- [aws_ec2_transit_gateway_connect](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_transit_gateway_connect)
- [aws_ec2_transit_gateway_connect_peer](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_transit_gateway_connect_peer)
- [aws_ec2_transit_gateway_dx_gateway_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_transit_gateway_dx_gateway_attachment)
- [aws_ec2_transit_gateway_multicast_domain](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_transit_gateway_multicast_domain)
- [aws_ec2_transit_gateway_peering_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_transit_gateway_peering_attachment)
- [aws_ec2_transit_gateway_peering_attachments](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_transit_gateway_peering_attachments)
- [aws_ec2_transit_gateway_route_table](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_transit_gateway_route_table)
- [aws_ec2_transit_gateway_route_table_associations](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_transit_gateway_route_table_associations)
- [aws_ec2_transit_gateway_route_table_propagations](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_transit_gateway_route_table_propagations)
- [aws_ec2_transit_gateway_route_table_routes](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_transit_gateway_route_table_routes)
- [aws_ec2_transit_gateway_route_tables](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_transit_gateway_route_tables)
- [aws_ec2_transit_gateway_vpc_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_transit_gateway_vpc_attachment)
- [aws_ec2_transit_gateway_vpc_attachments](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_transit_gateway_vpc_attachments)
- [aws_ec2_transit_gateway_vpn_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_transit_gateway_vpn_attachment)

## VPC Virtual Private Cloud

*59 resources and 27 data sources*

### Resources
- [aws_default_network_acl](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/default_network_acl)
- [aws_default_route_table](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/default_route_table)
- [aws_default_security_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/default_security_group)
- [aws_default_subnet](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/default_subnet)
- [aws_default_vpc](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/default_vpc)
- [aws_default_vpc_dhcp_options](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/default_vpc_dhcp_options)
- [aws_ec2_managed_prefix_list](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_managed_prefix_list)
- [aws_ec2_managed_prefix_list_entry](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_managed_prefix_list_entry)
- [aws_ec2_network_insights_analysis](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_network_insights_analysis)
- [aws_ec2_network_insights_path](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_network_insights_path)
- [aws_ec2_subnet_cidr_reservation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_subnet_cidr_reservation)
- [aws_ec2_traffic_mirror_filter](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_traffic_mirror_filter)
- [aws_ec2_traffic_mirror_filter_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_traffic_mirror_filter_rule)
- [aws_ec2_traffic_mirror_session](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_traffic_mirror_session)
- [aws_ec2_traffic_mirror_target](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_traffic_mirror_target)
- [aws_egress_only_internet_gateway](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/egress_only_internet_gateway)
- [aws_flow_log](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/flow_log)
- [aws_internet_gateway](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/internet_gateway)
- [aws_internet_gateway_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/internet_gateway_attachment)
- [aws_main_route_table_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/main_route_table_association)
- [aws_nat_gateway](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/nat_gateway)
- [aws_network_acl](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/network_acl)
- [aws_network_acl_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/network_acl_association)
- [aws_network_acl_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/network_acl_rule)
- [aws_network_interface](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/network_interface)
- [aws_network_interface_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/network_interface_attachment)
- [aws_network_interface_permission](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/network_interface_permission)
- [aws_network_interface_sg_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/network_interface_sg_attachment)
- [aws_route](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route)
- [aws_route_table](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route_table)
- [aws_route_table_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route_table_association)
- [aws_security_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/security_group)
- [aws_security_group_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/security_group_rule)
- [aws_subnet](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/subnet)
- [aws_vpc](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc)
- [aws_vpc_block_public_access_exclusion](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_block_public_access_exclusion)
- [aws_vpc_block_public_access_options](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_block_public_access_options)
- [aws_vpc_dhcp_options](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_dhcp_options)
- [aws_vpc_dhcp_options_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_dhcp_options_association)
- [aws_vpc_endpoint](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_endpoint)
- [aws_vpc_endpoint_connection_accepter](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_endpoint_connection_accepter)
- [aws_vpc_endpoint_connection_notification](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_endpoint_connection_notification)
- [aws_vpc_endpoint_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_endpoint_policy)
- [aws_vpc_endpoint_private_dns](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_endpoint_private_dns)
- [aws_vpc_endpoint_route_table_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_endpoint_route_table_association)
- [aws_vpc_endpoint_security_group_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_endpoint_security_group_association)
- [aws_vpc_endpoint_service](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_endpoint_service)
- [aws_vpc_endpoint_service_allowed_principal](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_endpoint_service_allowed_principal)
- [aws_vpc_endpoint_service_private_dns_verification](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_endpoint_service_private_dns_verification)
- [aws_vpc_endpoint_subnet_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_endpoint_subnet_association)
- [aws_vpc_ipv4_cidr_block_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_ipv4_cidr_block_association)
- [aws_vpc_ipv6_cidr_block_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_ipv6_cidr_block_association)
- [aws_vpc_network_performance_metric_subscription](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_network_performance_metric_subscription)
- [aws_vpc_peering_connection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_peering_connection)
- [aws_vpc_peering_connection_accepter](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_peering_connection_accepter)
- [aws_vpc_peering_connection_options](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_peering_connection_options)
- [aws_vpc_security_group_egress_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_security_group_egress_rule)
- [aws_vpc_security_group_ingress_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_security_group_ingress_rule)
- [aws_vpc_security_group_vpc_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_security_group_vpc_association)

### Data Sources
- [aws_ec2_managed_prefix_list](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_managed_prefix_list)
- [aws_ec2_managed_prefix_lists](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_managed_prefix_lists)
- [aws_ec2_network_insights_analysis](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_network_insights_analysis)
- [aws_ec2_network_insights_path](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_network_insights_path)
- [aws_internet_gateway](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/internet_gateway)
- [aws_nat_gateway](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/nat_gateway)
- [aws_nat_gateways](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/nat_gateways)
- [aws_network_acls](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/network_acls)
- [aws_network_interface](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/network_interface)
- [aws_network_interfaces](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/network_interfaces)
- [aws_prefix_list](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/prefix_list)
- [aws_route](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/route)
- [aws_route_table](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/route_table)
- [aws_route_tables](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/route_tables)
- [aws_security_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/security_group)
- [aws_security_groups](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/security_groups)
- [aws_subnet](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/subnet)
- [aws_subnets](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/subnets)
- [aws_vpc](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/vpc)
- [aws_vpc_dhcp_options](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/vpc_dhcp_options)
- [aws_vpc_endpoint](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/vpc_endpoint)
- [aws_vpc_endpoint_service](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/vpc_endpoint_service)
- [aws_vpc_peering_connection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/vpc_peering_connection)
- [aws_vpc_peering_connections](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/vpc_peering_connections)
- [aws_vpc_security_group_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/vpc_security_group_rule)
- [aws_vpc_security_group_rules](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/vpc_security_group_rules)
- [aws_vpcs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/vpcs)

## VPC IPAM IP Address Manager

*9 resources and 6 data sources*

### Resources
- [aws_vpc_ipam](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_ipam)
- [aws_vpc_ipam_organization_admin_account](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_ipam_organization_admin_account)
- [aws_vpc_ipam_pool](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_ipam_pool)
- [aws_vpc_ipam_pool_cidr](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_ipam_pool_cidr)
- [aws_vpc_ipam_pool_cidr_allocation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_ipam_pool_cidr_allocation)
- [aws_vpc_ipam_preview_next_cidr](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_ipam_preview_next_cidr)
- [aws_vpc_ipam_resource_discovery](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_ipam_resource_discovery)
- [aws_vpc_ipam_resource_discovery_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_ipam_resource_discovery_association)
- [aws_vpc_ipam_scope](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc_ipam_scope)

### Data Sources
- [aws_vpc_ipam](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/vpc_ipam)
- [aws_vpc_ipam_pool](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/vpc_ipam_pool)
- [aws_vpc_ipam_pool_cidrs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/vpc_ipam_pool_cidrs)
- [aws_vpc_ipam_pools](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/vpc_ipam_pools)
- [aws_vpc_ipam_preview_next_cidr](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/vpc_ipam_preview_next_cidr)
- [aws_vpc_ipams](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/vpc_ipams)

## VPC Lattice

*14 resources and 5 data sources*

### Resources
- [aws_vpclattice_access_log_subscription](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpclattice_access_log_subscription)
- [aws_vpclattice_auth_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpclattice_auth_policy)
- [aws_vpclattice_listener](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpclattice_listener)
- [aws_vpclattice_listener_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpclattice_listener_rule)
- [aws_vpclattice_resource_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpclattice_resource_configuration)
- [aws_vpclattice_resource_gateway](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpclattice_resource_gateway)
- [aws_vpclattice_resource_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpclattice_resource_policy)
- [aws_vpclattice_service](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpclattice_service)
- [aws_vpclattice_service_network](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpclattice_service_network)
- [aws_vpclattice_service_network_resource_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpclattice_service_network_resource_association)
- [aws_vpclattice_service_network_service_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpclattice_service_network_service_association)
- [aws_vpclattice_service_network_vpc_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpclattice_service_network_vpc_association)
- [aws_vpclattice_target_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpclattice_target_group)
- [aws_vpclattice_target_group_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpclattice_target_group_attachment)

### Data Sources
- [aws_vpclattice_auth_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/vpclattice_auth_policy)
- [aws_vpclattice_listener](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/vpclattice_listener)
- [aws_vpclattice_resource_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/vpclattice_resource_policy)
- [aws_vpclattice_service](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/vpclattice_service)
- [aws_vpclattice_service_network](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/vpclattice_service_network)

## VPN Client

*4 resources and 1 data sources*

### Resources
- [aws_ec2_client_vpn_authorization_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_client_vpn_authorization_rule)
- [aws_ec2_client_vpn_endpoint](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_client_vpn_endpoint)
- [aws_ec2_client_vpn_network_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_client_vpn_network_association)
- [aws_ec2_client_vpn_route](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_client_vpn_route)

### Data Sources
- [aws_ec2_client_vpn_endpoint](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ec2_client_vpn_endpoint)

## VPN Site-to-Site

*6 resources and 2 data sources*

### Resources
- [aws_customer_gateway](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/customer_gateway)
- [aws_vpn_connection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpn_connection)
- [aws_vpn_connection_route](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpn_connection_route)
- [aws_vpn_gateway](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpn_gateway)
- [aws_vpn_gateway_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpn_gateway_attachment)
- [aws_vpn_gateway_route_propagation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpn_gateway_route_propagation)

### Data Sources
- [aws_customer_gateway](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/customer_gateway)
- [aws_vpn_gateway](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/vpn_gateway)

## Verified Access

*6 resources and 0 data sources*

### Resources
- [aws_verifiedaccess_endpoint](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/verifiedaccess_endpoint)
- [aws_verifiedaccess_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/verifiedaccess_group)
- [aws_verifiedaccess_instance](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/verifiedaccess_instance)
- [aws_verifiedaccess_instance_logging_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/verifiedaccess_instance_logging_configuration)
- [aws_verifiedaccess_instance_trust_provider_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/verifiedaccess_instance_trust_provider_attachment)
- [aws_verifiedaccess_trust_provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/verifiedaccess_trust_provider)

## Verified Permissions

*5 resources and 1 data sources*

### Resources
- [aws_verifiedpermissions_identity_source](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/verifiedpermissions_identity_source)
- [aws_verifiedpermissions_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/verifiedpermissions_policy)
- [aws_verifiedpermissions_policy_store](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/verifiedpermissions_policy_store)
- [aws_verifiedpermissions_policy_template](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/verifiedpermissions_policy_template)
- [aws_verifiedpermissions_schema](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/verifiedpermissions_schema)

### Data Sources
- [aws_verifiedpermissions_policy_store](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/verifiedpermissions_policy_store)

## WAF

*6 resources and 4 data sources*

### Resources
- [aws_wafv2_ip_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/wafv2_ip_set)
- [aws_wafv2_regex_pattern_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/wafv2_regex_pattern_set)
- [aws_wafv2_rule_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/wafv2_rule_group)
- [aws_wafv2_web_acl](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/wafv2_web_acl)
- [aws_wafv2_web_acl_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/wafv2_web_acl_association)
- [aws_wafv2_web_acl_logging_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/wafv2_web_acl_logging_configuration)

### Data Sources
- [aws_wafv2_ip_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/wafv2_ip_set)
- [aws_wafv2_regex_pattern_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/wafv2_regex_pattern_set)
- [aws_wafv2_rule_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/wafv2_rule_group)
- [aws_wafv2_web_acl](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/wafv2_web_acl)

## WAF Classic

*12 resources and 5 data sources*

### Resources
- [aws_waf_byte_match_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/waf_byte_match_set)
- [aws_waf_geo_match_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/waf_geo_match_set)
- [aws_waf_ipset](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/waf_ipset)
- [aws_waf_rate_based_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/waf_rate_based_rule)
- [aws_waf_regex_match_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/waf_regex_match_set)
- [aws_waf_regex_pattern_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/waf_regex_pattern_set)
- [aws_waf_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/waf_rule)
- [aws_waf_rule_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/waf_rule_group)
- [aws_waf_size_constraint_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/waf_size_constraint_set)
- [aws_waf_sql_injection_match_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/waf_sql_injection_match_set)
- [aws_waf_web_acl](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/waf_web_acl)
- [aws_waf_xss_match_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/waf_xss_match_set)

### Data Sources
- [aws_waf_ipset](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/waf_ipset)
- [aws_waf_rate_based_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/waf_rate_based_rule)
- [aws_waf_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/waf_rule)
- [aws_waf_subscribed_rule_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/waf_subscribed_rule_group)
- [aws_waf_web_acl](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/waf_web_acl)

## WAF Classic Regional

*13 resources and 5 data sources*

### Resources
- [aws_wafregional_byte_match_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/wafregional_byte_match_set)
- [aws_wafregional_geo_match_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/wafregional_geo_match_set)
- [aws_wafregional_ipset](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/wafregional_ipset)
- [aws_wafregional_rate_based_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/wafregional_rate_based_rule)
- [aws_wafregional_regex_match_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/wafregional_regex_match_set)
- [aws_wafregional_regex_pattern_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/wafregional_regex_pattern_set)
- [aws_wafregional_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/wafregional_rule)
- [aws_wafregional_rule_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/wafregional_rule_group)
- [aws_wafregional_size_constraint_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/wafregional_size_constraint_set)
- [aws_wafregional_sql_injection_match_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/wafregional_sql_injection_match_set)
- [aws_wafregional_web_acl](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/wafregional_web_acl)
- [aws_wafregional_web_acl_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/wafregional_web_acl_association)
- [aws_wafregional_xss_match_set](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/wafregional_xss_match_set)

### Data Sources
- [aws_wafregional_ipset](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/wafregional_ipset)
- [aws_wafregional_rate_based_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/wafregional_rate_based_rule)
- [aws_wafregional_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/wafregional_rule)
- [aws_wafregional_subscribed_rule_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/wafregional_subscribed_rule_group)
- [aws_wafregional_web_acl](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/wafregional_web_acl)

## Wavelength

*1 resources and 0 data sources*

### Resources
- [aws_ec2_carrier_gateway](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ec2_carrier_gateway)

## Web Services Budgets

*2 resources and 1 data sources*

### Resources
- [aws_budgets_budget](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/budgets_budget)
- [aws_budgets_budget_action](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/budgets_budget_action)

### Data Sources
- [aws_budgets_budget](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/budgets_budget)

## WorkLink

*2 resources and 0 data sources*

### Resources
- [aws_worklink_fleet](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/worklink_fleet)
- [aws_worklink_website_certificate_authority_association](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/worklink_website_certificate_authority_association)

## WorkSpaces

*4 resources and 4 data sources*

### Resources
- [aws_workspaces_connection_alias](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/workspaces_connection_alias)
- [aws_workspaces_directory](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/workspaces_directory)
- [aws_workspaces_ip_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/workspaces_ip_group)
- [aws_workspaces_workspace](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/workspaces_workspace)

### Data Sources
- [aws_workspaces_bundle](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/workspaces_bundle)
- [aws_workspaces_directory](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/workspaces_directory)
- [aws_workspaces_image](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/workspaces_image)
- [aws_workspaces_workspace](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/workspaces_workspace)

## X-Ray

*4 resources and 0 data sources*

### Resources
- [aws_xray_encryption_config](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/xray_encryption_config)
- [aws_xray_group](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/xray_group)
- [aws_xray_resource_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/xray_resource_policy)
- [aws_xray_sampling_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/xray_sampling_rule)

---
*This document was generated automatically by the AWS Provider Resources Generator script.*
*Generation time: 184.69 seconds*