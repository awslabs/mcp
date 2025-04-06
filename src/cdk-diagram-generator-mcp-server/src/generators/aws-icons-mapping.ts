/**
 * AWS Icons Mapping
 * 
 * This file contains a mapping of AWS resource types to their corresponding Draw.io icon names.
 * The icons are from the AWS4 library in Draw.io.
 * 
 * Reference: https://www.diagrams.net/doc/faq/aws-icons
 */

// Map of AWS resource types to Draw.io icon names
export const AWS_ICONS_MAPPING: Record<string, string> = {
  // Compute
  'AWS::Lambda::Function': 'lambda',
  'AWS::EC2::Instance': 'instance',
  'AWS::EC2::LaunchTemplate': 'ami',
  'AWS::AutoScaling::AutoScalingGroup': 'auto_scaling2',
  'AWS::Batch::ComputeEnvironment': 'batch',
  'AWS::Batch::JobDefinition': 'batch',
  'AWS::Batch::JobQueue': 'batch',
  'AWS::ECS::Cluster': 'ecs',
  'AWS::ECS::Service': 'ecs',
  'AWS::ECS::TaskDefinition': 'ecs',
  'AWS::EKS::Cluster': 'eks',
  'AWS::ElasticBeanstalk::Application': 'elastic_beanstalk',
  'AWS::ElasticBeanstalk::Environment': 'elastic_beanstalk',
  'AWS::Lambda::LayerVersion': 'lambda',
  'AWS::Lambda::EventSourceMapping': 'lambda',
  'AWS::Lightsail::Instance': 'lightsail',
  
  // Containers
  'AWS::ECS::CapacityProvider': 'ecs',
  'AWS::ECS::TaskSet': 'ecs',
  'AWS::App::Runner::Service': 'app_runner',
  'AWS::ECR::Repository': 'ecr',
  'AWS::ECR::RegistryPolicy': 'ecr',
  'AWS::EKS::Nodegroup': 'eks',
  'AWS::EKS::FargateProfile': 'fargate',
  
  // Storage
  'AWS::S3::Bucket': 's3',
  'AWS::S3::BucketPolicy': 's3',
  'AWS::EFS::FileSystem': 'efs',
  'AWS::EFS::MountTarget': 'efs',
  'AWS::FSx::FileSystem': 'fsx',
  'AWS::FSx::Volume': 'fsx',
  'AWS::DynamoDB::Table': 'dynamodb',
  'AWS::DynamoDB::GlobalTable': 'dynamodb',
  'AWS::ElastiCache::CacheCluster': 'elasticache',
  'AWS::ElastiCache::ReplicationGroup': 'elasticache',
  'AWS::RDS::DBInstance': 'rds',
  'AWS::RDS::DBCluster': 'rds',
  'AWS::RDS::DBSubnetGroup': 'rds',
  'AWS::Redshift::Cluster': 'redshift',
  'AWS::Neptune::DBCluster': 'neptune',
  'AWS::Neptune::DBInstance': 'neptune',
  'AWS::DocumentDB::DBCluster': 'documentdb_with_mongodb_compatibility',
  'AWS::DocumentDB::DBInstance': 'documentdb_with_mongodb_compatibility',
  'AWS::Timestream::Database': 'timestream',
  'AWS::Timestream::Table': 'timestream',
  'AWS::QLDB::Ledger': 'quantum_ledger_database',
  
  // Database
  'AWS::RDS::DBParameterGroup': 'rds',
  'AWS::RDS::DBClusterParameterGroup': 'rds',
  'AWS::RDS::OptionGroup': 'rds',
  'AWS::RDS::EventSubscription': 'rds',
  'AWS::Redshift::ClusterParameterGroup': 'redshift',
  'AWS::Redshift::ClusterSubnetGroup': 'redshift',
  
  // Networking & Content Delivery
  'AWS::EC2::VPC': 'vpc',
  'AWS::EC2::Subnet': 'subnet',
  'AWS::EC2::RouteTable': 'route_table',
  'AWS::EC2::SecurityGroup': 'security_group',
  'AWS::EC2::NatGateway': 'nat_gateway',
  'AWS::EC2::InternetGateway': 'internet_gateway',
  'AWS::EC2::VPCEndpoint': 'endpoint',
  'AWS::EC2::VPCPeeringConnection': 'peering',
  'AWS::EC2::TransitGateway': 'transit_gateway',
  'AWS::EC2::CustomerGateway': 'customer_gateway',
  'AWS::EC2::VPNGateway': 'vpn_gateway',
  'AWS::EC2::VPNConnection': 'vpn_connection',
  'AWS::ElasticLoadBalancing::LoadBalancer': 'classic_load_balancer',
  'AWS::ElasticLoadBalancingV2::LoadBalancer': 'application_load_balancer',
  'AWS::ElasticLoadBalancingV2::TargetGroup': 'elastic_load_balancing',
  'AWS::ElasticLoadBalancingV2::Listener': 'elastic_load_balancing',
  'AWS::ApiGateway::RestApi': 'api_gateway',
  'AWS::ApiGateway::Resource': 'api_gateway',
  'AWS::ApiGateway::Method': 'api_gateway',
  'AWS::ApiGateway::Stage': 'api_gateway',
  'AWS::ApiGateway::Deployment': 'api_gateway',
  'AWS::ApiGatewayV2::Api': 'apigateway',
  'AWS::ApiGatewayV2::Route': 'apigateway',
  'AWS::ApiGatewayV2::Integration': 'apigateway',
  'AWS::CloudFront::Distribution': 'cloudfront',
  'AWS::CloudFront::OriginAccessIdentity': 'cloudfront',
  'AWS::Route53::HostedZone': 'route_53',
  'AWS::Route53::RecordSet': 'route_53',
  'AWS::Route53::RecordSetGroup': 'route_53',
  'AWS::Route53::HealthCheck': 'route_53',
  'AWS::GlobalAccelerator::Accelerator': 'global_accelerator',
  'AWS::GlobalAccelerator::EndpointGroup': 'global_accelerator',
  'AWS::GlobalAccelerator::Listener': 'global_accelerator',
  'AWS::AppMesh::Mesh': 'app_mesh',
  'AWS::AppMesh::VirtualNode': 'app_mesh',
  'AWS::AppMesh::VirtualService': 'app_mesh',
  'AWS::AppMesh::VirtualRouter': 'app_mesh',
  'AWS::AppMesh::Route': 'app_mesh',
  'AWS::AppMesh::GatewayRoute': 'app_mesh',
  'AWS::AppMesh::VirtualGateway': 'app_mesh',
  
  // Management & Governance
  'AWS::CloudWatch::Alarm': 'cloudwatch',
  'AWS::CloudWatch::Dashboard': 'cloudwatch',
  'AWS::CloudWatch::MetricFilter': 'cloudwatch',
  'AWS::CloudTrail::Trail': 'cloudtrail',
  'AWS::Config::ConfigRule': 'config',
  'AWS::Config::ConfigurationRecorder': 'config',
  'AWS::Config::DeliveryChannel': 'config',
  'AWS::AutoScaling::ScalingPolicy': 'auto_scaling2',
  'AWS::AutoScaling::ScheduledAction': 'auto_scaling2',
  'AWS::SSM::Parameter': 'systems_manager',
  'AWS::SSM::Document': 'systems_manager',
  'AWS::SSM::MaintenanceWindow': 'systems_manager',
  'AWS::SSM::PatchBaseline': 'systems_manager',
  'AWS::CloudFormation::Stack': 'cloudformation',
  'AWS::CloudFormation::StackSet': 'cloudformation',
  'AWS::ServiceCatalog::Portfolio': 'service_catalog',
  'AWS::ServiceCatalog::Product': 'service_catalog',
  'AWS::OpsWorks::Stack': 'opsworks',
  'AWS::OpsWorks::Layer': 'opsworks',
  'AWS::OpsWorks::Instance': 'opsworks',
  'AWS::OpsWorks::App': 'opsworks',
  
  // Security, Identity, & Compliance
  'AWS::IAM::Role': 'role',
  'AWS::IAM::Policy': 'policy',
  'AWS::IAM::ManagedPolicy': 'permissions',
  'AWS::IAM::User': 'user',
  'AWS::IAM::Group': 'users',
  'AWS::IAM::InstanceProfile': 'role',
  'AWS::Cognito::UserPool': 'cognito',
  'AWS::Cognito::UserPoolClient': 'cognito',
  'AWS::Cognito::IdentityPool': 'cognito',
  'AWS::KMS::Key': 'kms',
  'AWS::KMS::Alias': 'kms',
  'AWS::SecretsManager::Secret': 'secrets_manager',
  'AWS::SecretsManager::SecretTargetAttachment': 'secrets_manager',
  'AWS::WAF::WebACL': 'waf',
  'AWS::WAF::Rule': 'waf',
  'AWS::WAF::RuleGroup': 'waf',
  'AWS::WAFv2::WebACL': 'waf',
  'AWS::WAFv2::RuleGroup': 'waf',
  'AWS::WAFv2::IPSet': 'waf',
  'AWS::WAFv2::RegexPatternSet': 'waf',
  'AWS::Shield::Protection': 'shield',
  'AWS::GuardDuty::Detector': 'guardduty',
  'AWS::GuardDuty::Filter': 'guardduty',
  'AWS::GuardDuty::IPSet': 'guardduty',
  'AWS::GuardDuty::ThreatIntelSet': 'guardduty',
  'AWS::Inspector::AssessmentTarget': 'inspector',
  'AWS::Inspector::AssessmentTemplate': 'inspector',
  'AWS::Inspector::ResourceGroup': 'inspector',
  'AWS::Macie::FindingsFilter': 'macie',
  'AWS::Macie::CustomDataIdentifier': 'macie',
  
  // Application Integration
  'AWS::SNS::Topic': 'sns',
  'AWS::SNS::Subscription': 'sns',
  'AWS::SQS::Queue': 'sqs',
  'AWS::SQS::QueuePolicy': 'sqs',
  'AWS::StepFunctions::StateMachine': 'step_functions',
  'AWS::StepFunctions::Activity': 'step_functions',
  'AWS::EventBridge::Rule': 'eventbridge',
  'AWS::Events::Rule': 'eventbridge',
  'AWS::Events::EventBus': 'eventbridge',
  'AWS::MQ::Broker': 'mq',
  'AWS::MQ::Configuration': 'mq',
  'AWS::AppSync::GraphQLApi': 'appsync',
  'AWS::AppSync::DataSource': 'appsync',
  'AWS::AppSync::Resolver': 'appsync',
  'AWS::AppSync::FunctionConfiguration': 'appsync',
  
  // Analytics
  'AWS::Athena::WorkGroup': 'athena',
  'AWS::Athena::DataCatalog': 'athena',
  'AWS::EMR::Cluster': 'emr',
  'AWS::EMR::Step': 'emr',
  'AWS::EMR::InstanceFleet': 'emr',
  'AWS::EMR::InstanceGroup': 'emr',
  'AWS::Kinesis::Stream': 'kinesis',
  'AWS::Kinesis::StreamConsumer': 'kinesis',
  'AWS::KinesisAnalytics::Application': 'kinesis_data_analytics',
  'AWS::KinesisAnalyticsV2::Application': 'kinesis_data_analytics',
  'AWS::KinesisFirehose::DeliveryStream': 'kinesis_data_firehose',
  'AWS::Glue::Database': 'glue',
  'AWS::Glue::Table': 'glue',
  'AWS::Glue::Crawler': 'glue',
  'AWS::Glue::Job': 'glue',
  'AWS::Glue::Trigger': 'glue',
  'AWS::Glue::Workflow': 'glue',
  'AWS::MSK::Cluster': 'managed_streaming_for_kafka',
  'AWS::MSK::Configuration': 'managed_streaming_for_kafka',
  'AWS::QuickSight::Dashboard': 'quicksight',
  'AWS::QuickSight::DataSource': 'quicksight',
  'AWS::QuickSight::DataSet': 'quicksight',
  'AWS::QuickSight::Analysis': 'quicksight',
  'AWS::QuickSight::Template': 'quicksight',
  'AWS::DataBrew::Dataset': 'data_exchange',
  'AWS::DataBrew::Job': 'data_exchange',
  'AWS::DataBrew::Project': 'data_exchange',
  'AWS::DataBrew::Recipe': 'data_exchange',
  'AWS::DataBrew::Schedule': 'data_exchange',
  
  // Machine Learning
  'AWS::SageMaker::Model': 'sagemaker',
  'AWS::SageMaker::EndpointConfig': 'sagemaker',
  'AWS::SageMaker::Endpoint': 'sagemaker',
  'AWS::SageMaker::NotebookInstance': 'sagemaker',
  'AWS::SageMaker::NotebookInstanceLifecycleConfig': 'sagemaker',
  'AWS::SageMaker::Workteam': 'sagemaker',
  'AWS::Comprehend::DocumentClassifier': 'comprehend',
  'AWS::Comprehend::EntityRecognizer': 'comprehend',
  'AWS::Forecast::Dataset': 'forecast',
  'AWS::Forecast::DatasetGroup': 'forecast',
  'AWS::Forecast::Predictor': 'forecast',
  'AWS::Forecast::ForecastModel': 'forecast',
  'AWS::Lex::Bot': 'lex',
  'AWS::Lex::BotAlias': 'lex',
  'AWS::Polly::Lexicon': 'polly',
  'AWS::Rekognition::Collection': 'rekognition',
  'AWS::Rekognition::StreamProcessor': 'rekognition',
  'AWS::Textract::DocumentAnalysis': 'textract',
  'AWS::Textract::DocumentExtraction': 'textract',
  'AWS::Translate::TranslationJob': 'translate',
  'AWS::Bedrock::Model': 'bedrock',
  'AWS::Bedrock::ModelInvocation': 'bedrock',
  'AWS::Bedrock::KnowledgeBase': 'bedrock',
  
  // Developer Tools
  'AWS::CodeBuild::Project': 'codebuild',
  'AWS::CodeBuild::ReportGroup': 'codebuild',
  'AWS::CodeBuild::SourceCredential': 'codebuild',
  'AWS::CodeCommit::Repository': 'codecommit',
  'AWS::CodeDeploy::Application': 'codedeploy',
  'AWS::CodeDeploy::DeploymentGroup': 'codedeploy',
  'AWS::CodeDeploy::DeploymentConfig': 'codedeploy',
  'AWS::CodePipeline::Pipeline': 'codepipeline',
  'AWS::CodePipeline::Webhook': 'codepipeline',
  'AWS::CodeStar::Project': 'codestar',
  'AWS::CodeStarConnections::Connection': 'codestar',
  'AWS::XRay::Group': 'xray',
  'AWS::XRay::SamplingRule': 'xray',
  'AWS::Cloud9::EnvironmentEC2': 'cloud9',
  
  // IoT
  'AWS::IoT::Thing': 'iot_core',
  'AWS::IoT::Policy': 'iot_core',
  'AWS::IoT::Certificate': 'iot_core',
  'AWS::IoT::TopicRule': 'iot_core',
  'AWS::IoT::RoleAlias': 'iot_core',
  'AWS::IoT::ProvisioningTemplate': 'iot_core',
  'AWS::IoT::BillingGroup': 'iot_core',
  'AWS::IoT::ThingGroup': 'iot_core',
  'AWS::IoT::ThingType': 'iot_core',
  'AWS::IoT1Click::Device': 'iot_1click',
  'AWS::IoT1Click::Placement': 'iot_1click',
  'AWS::IoT1Click::Project': 'iot_1click',
  'AWS::IoTAnalytics::Channel': 'iot_analytics',
  'AWS::IoTAnalytics::Dataset': 'iot_analytics',
  'AWS::IoTAnalytics::Datastore': 'iot_analytics',
  'AWS::IoTAnalytics::Pipeline': 'iot_analytics',
  'AWS::IoTEvents::DetectorModel': 'iot_events',
  'AWS::IoTEvents::Input': 'iot_events',
  'AWS::IoTEvents::AlarmModel': 'iot_events',
  'AWS::IoTSiteWise::Asset': 'iot_sitewise',
  'AWS::IoTSiteWise::AssetModel': 'iot_sitewise',
  'AWS::IoTSiteWise::Gateway': 'iot_sitewise',
  'AWS::IoTThingsGraph::FlowTemplate': 'iot_things_graph',
  'AWS::Greengrass::Group': 'greengrass',
  'AWS::Greengrass::CoreDefinition': 'greengrass',
  'AWS::Greengrass::DeviceDefinition': 'greengrass',
  'AWS::Greengrass::FunctionDefinition': 'greengrass',
  'AWS::Greengrass::LoggerDefinition': 'greengrass',
  'AWS::Greengrass::ResourceDefinition': 'greengrass',
  'AWS::Greengrass::SubscriptionDefinition': 'greengrass',
  
  // Mobile
  'AWS::Amplify::App': 'amplify',
  'AWS::Amplify::Branch': 'amplify',
  'AWS::Amplify::Domain': 'amplify',
  'AWS::DeviceFarm::Project': 'device_farm',
  'AWS::DeviceFarm::DevicePool': 'device_farm',
  'AWS::DeviceFarm::TestGridProject': 'device_farm',
  'AWS::Pinpoint::App': 'pinpoint',
  'AWS::Pinpoint::Campaign': 'pinpoint',
  'AWS::Pinpoint::EmailTemplate': 'pinpoint',
  'AWS::Pinpoint::PushTemplate': 'pinpoint',
  'AWS::Pinpoint::SmsTemplate': 'pinpoint',
  'AWS::Pinpoint::Segment': 'pinpoint',
  
  // AR & VR
  'AWS::Sumerian::Scene': 'sumerian',
  
  // Cost Management
  'AWS::Budgets::Budget': 'budgets',
  'AWS::CostExplorer::CostCategory': 'cost_explorer',
  
  // Customer Engagement
  'AWS::Connect::Instance': 'connect',
  'AWS::Connect::ContactFlow': 'connect',
  'AWS::Connect::HoursOfOperation': 'connect',
  'AWS::Connect::PhoneNumber': 'connect',
  'AWS::Connect::Queue': 'connect',
  'AWS::Connect::QuickConnect': 'connect',
  'AWS::Connect::User': 'connect',
  'AWS::SES::ConfigurationSet': 'simple_email_service',
  'AWS::SES::ContactList': 'simple_email_service',
  'AWS::SES::ReceiptFilter': 'simple_email_service',
  'AWS::SES::ReceiptRule': 'simple_email_service',
  'AWS::SES::ReceiptRuleSet': 'simple_email_service',
  'AWS::SES::Template': 'simple_email_service',
  
  // Business Applications
  'AWS::WorkMail::Group': 'workmail',
  'AWS::WorkMail::User': 'workmail',
  'AWS::WorkMail::Resource': 'workmail',
  'AWS::Chime::AppInstance': 'chime',
  'AWS::Chime::AppInstanceUser': 'chime',
  'AWS::Chime::Channel': 'chime',
  'AWS::Chime::ChannelMembership': 'chime',
  
  // End User Computing
  'AWS::WorkSpaces::Workspace': 'workspaces',
  'AWS::WorkSpaces::ConnectionAlias': 'workspaces',
  'AWS::WorkSpaces::WorkspaceDirectory': 'workspaces',
  'AWS::WorkSpaces::WorkspaceImage': 'workspaces',
  'AWS::AppStream::DirectoryConfig': 'appstream',
  'AWS::AppStream::Fleet': 'appstream',
  'AWS::AppStream::ImageBuilder': 'appstream',
  'AWS::AppStream::Stack': 'appstream',
  'AWS::AppStream::StackFleetAssociation': 'appstream',
  'AWS::AppStream::StackUserAssociation': 'appstream',
  'AWS::AppStream::User': 'appstream',
  
  // Quantum Technologies
  'AWS::Braket::QuantumTask': 'braket',
  
  // Blockchain
  'AWS::ManagedBlockchain::Member': 'managed_blockchain',
  'AWS::ManagedBlockchain::Node': 'managed_blockchain',
  
  // Satellite
  'AWS::GroundStation::Config': 'ground_station',
  'AWS::GroundStation::DataflowEndpointGroup': 'ground_station',
  'AWS::GroundStation::MissionProfile': 'ground_station',
  
  // Robotics
  'AWS::RoboMaker::RobotApplication': 'robomaker',
  'AWS::RoboMaker::RobotApplicationVersion': 'robomaker',
  'AWS::RoboMaker::SimulationApplication': 'robomaker',
  'AWS::RoboMaker::SimulationApplicationVersion': 'robomaker',
  
  
  // Default icon for unknown resource types
  'default': 'aws_cloud'
};

// Map of AWS service names to Draw.io icon names (for simpler resource types)
export const AWS_SERVICE_ICONS: Record<string, string> = {
  // Compute
  'lambda': 'lambda',
  'ec2': 'instance',
  'batch': 'batch',
  'ecs': 'ecs',
  'eks': 'eks',
  'elasticbeanstalk': 'elastic_beanstalk',
  'lightsail': 'lightsail',
  
  // Containers
  'ecr': 'ecr',
  'fargate': 'fargate',
  
  // Storage
  's3': 's3',
  'efs': 'efs',
  'fsx': 'fsx',
  'dynamodb': 'dynamodb',
  'elasticache': 'elasticache',
  'rds': 'rds',
  'redshift': 'redshift',
  'neptune': 'neptune',
  'documentdb': 'documentdb_with_mongodb_compatibility',
  'timestream': 'timestream',
  'qldb': 'quantum_ledger_database',
  
  // Networking & Content Delivery
  'vpc': 'vpc',
  'subnet': 'subnet',
  'routetable': 'route_table',
  'securitygroup': 'security_group',
  'natgateway': 'nat_gateway',
  'internetgateway': 'internet_gateway',
  'elb': 'classic_load_balancer',
  'alb': 'application_load_balancer',
  'nlb': 'network_load_balancer',
  'apigateway': 'api_gateway',
  'cloudfront': 'cloudfront',
  'route53': 'route_53',
  'globalaccelerator': 'global_accelerator',
  'appmesh': 'app_mesh',
  
  // Management & Governance
  'cloudwatch': 'cloudwatch',
  'cloudtrail': 'cloudtrail',
  'config': 'config',
  'autoscaling': 'auto_scaling2',
  'ssm': 'systems_manager',
  'cloudformation': 'cloudformation',
  'servicecatalog': 'service_catalog',
  'opsworks': 'opsworks',
  
  // Security, Identity, & Compliance
  'iam': 'iam',
  'role': 'role',
  'policy': 'policy',
  'user': 'user',
  'cognito': 'cognito',
  'kms': 'kms',
  'secretsmanager': 'secrets_manager',
  'waf': 'waf',
  'shield': 'shield',
  'guardduty': 'guardduty',
  'inspector': 'inspector',
  'macie': 'macie',
  
  // Application Integration
  'sns': 'sns',
  'sqs': 'sqs',
  'stepfunctions': 'step_functions',
  'eventbridge': 'eventbridge',
  'mq': 'mq',
  'appsync': 'appsync',
  
  // Analytics
  'athena': 'athena',
  'emr': 'emr',
  'kinesis': 'kinesis',
  'kinesisanalytics': 'kinesis_data_analytics',
  'kinesisfirehose': 'kinesis_data_firehose',
  'glue': 'glue',
  'msk': 'managed_streaming_for_kafka',
  'quicksight': 'quicksight',
  'databrew': 'data_exchange',
  
  // Machine Learning
  'sagemaker': 'sagemaker',
  'comprehend': 'comprehend',
  'forecast': 'forecast',
  'lex': 'lex',
  'polly': 'polly',
  'rekognition': 'rekognition',
  'textract': 'textract',
  'translate': 'translate',
  'bedrock': 'bedrock',
  
  // Developer Tools
  'codebuild': 'codebuild',
  'codecommit': 'codecommit',
  'codedeploy': 'codedeploy',
  'codepipeline': 'codepipeline',
  'codestar': 'codestar',
  'xray': 'xray',
  'cloud9': 'cloud9',
  
  // IoT
  'iot': 'iot_core',
  'iot1click': 'iot_1click',
  'iotanalytics': 'iot_analytics',
  'iotevents': 'iot_events',
  'iotsitewise': 'iot_sitewise',
  'iotthingsgraph': 'iot_things_graph',
  'greengrass': 'greengrass',
  
  // Mobile
  'amplify': 'amplify',
  'devicefarm': 'device_farm',
  'pinpoint': 'pinpoint',
  
  // AR & VR
  'sumerian': 'sumerian',
  
  // Cost Management
  'budgets': 'budgets',
  'costexplorer': 'cost_explorer',
  
  // Customer Engagement
  'connect': 'connect',
  'ses': 'simple_email_service',
  
  // Business Applications
  'workmail': 'workmail',
  'chime': 'chime',
  
  // End User Computing
  'workspaces': 'workspaces',
  'appstream': 'appstream',
  
  // Quantum Technologies
  'braket': 'braket',
  
  // Blockchain
  'managedblockchain': 'managed_blockchain',
  
  // Satellite
  'groundstation': 'ground_station',
  
  // Robotics
  'robomaker': 'robomaker',
  
  // Default icon for unknown services
  'default': 'aws_cloud'
};

/**
 * Get the Draw.io icon name for an AWS resource type
 * 
 * @param resourceType The AWS resource type (e.g., 'AWS::Lambda::Function')
 * @returns The Draw.io icon name (e.g., 'lambda')
 */
export function getIconForResourceType(resourceType: string): string {
  // Try to get the icon from the resource type mapping
  if (AWS_ICONS_MAPPING[resourceType]) {
    return AWS_ICONS_MAPPING[resourceType];
  }
  
  // If not found, try to extract the service name and get the icon from the service mapping
  const serviceName = resourceType.split('::')[1]?.toLowerCase();
  if (serviceName && AWS_SERVICE_ICONS[serviceName]) {
    return AWS_SERVICE_ICONS[serviceName];
  }
  
  // If still not found, return the default icon
  return AWS_SERVICE_ICONS.default;
}

/**
 * Get the Draw.io icon name for a simple resource type
 * 
 * @param resourceType The simple resource type (e.g., 'lambda', 'dynamodb')
 * @returns The Draw.io icon name (e.g., 'lambda', 'dynamodb')
 */
export function getIconForSimpleResourceType(resourceType: string): string {
  return AWS_SERVICE_ICONS[resourceType.toLowerCase()] || AWS_SERVICE_ICONS.default;
}
