# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FAILURE_CASES = {
    # DELETE ERRORS
    'S3_BUCKET_NOT_EMPTY': {
        'error_pattern': 'The bucket you tried to delete is not empty',
        'resource_type': 'AWS::S3::Bucket',
        'operation': 'DELETE',
        'error_code': 'BucketNotEmpty',
        'analysis': 'The error occurs when attempting to delete an Amazon S3 bucket that is not completely empty. This means the bucket still contains objects or other resources, and AWS S3 does not allow deleting non-empty buckets as a safety measure to prevent accidental data loss.',
        'resolution': """There are two approaches to solve this error:

Approach #1: Retry Delete from CloudFormation Console
1. In the CloudFormation console, choose "Retry delete"
2. When prompted to retain resources, select the S3 bucket you want to retain
3. Proceed with the stack deletion process

Approach #2: Manually Delete S3 objects
1. Open the Amazon S3 console
2. Navigate to the bucket that is causing the error
3. Delete all objects inside the bucket by selecting all objects and clicking "Delete"
4. Once the bucket is empty, go back to the CloudFormation console
5. Retry the DELETE operation on the CloudFormation stack""",
    },
    'SECURITY_GROUP_DEPENDENCY': {
        'error_pattern': 'resource.*has a dependent object',
        'resource_type': 'AWS::EC2::SecurityGroup',
        'operation': 'DELETE',
        'error_code': 'DependencyViolation',
        'analysis': 'The error occurs when attempting to delete an AWS EC2 Security Group that has associated resources or dependencies, such as running instances or network interfaces, still attached to it. AWS prevents the deletion of Security Groups that are actively in use to prevent potential service disruptions or security vulnerabilities.',
        'resolution': """There are two approaches to solve this error:

Approach #1: Retry Delete from CloudFormation Console
1. In the CloudFormation console, choose "Retry delete"
2. When prompted to retain resources, select the security group you want to retain
3. Proceed with the stack deletion process

Approach #2: Manually Disassociate Dependent Resources
1. Go to the Amazon EC2 console
2. In the left-hand navigation pane, click "Security Groups" under "NETWORK & SECURITY"
3. Select the security group with the ID mentioned in the error message
4. In the bottom pane, look for the "Resources" tab and identify any resources associated with this security group
5. If the resources are not managed by CloudFormation, you can proceed to disassociate or remove the dependencies between the security group and the associated resources
6. Once all dependencies are removed, return to the CloudFormation console
7. Select the stack that encountered the error and initiate the "Delete Stack" operation again

Warning: Manually disassociating or removing dependencies from resources managed by CloudFormation can lead to drift and an inconsistent state between your infrastructure and the CloudFormation template.""",
    },
    'SUBNET_DEPENDENCY': {
        'error_pattern': 'The subnet.*has dependencies and cannot be deleted',
        'resource_type': 'AWS::EC2::Subnet',
        'operation': 'DELETE',
        'error_code': 'DependencyViolation',
        'analysis': 'The error occurs when attempting to delete an AWS EC2 subnet that has dependencies, meaning other resources (such as EC2 instances, network interfaces, or route tables) are still associated with or relying on that subnet. The subnet cannot be deleted until these dependencies have been removed or disassociated.',
        'resolution': """There are two approaches to solve this error:

Approach #1: Retry Delete from CloudFormation Console
1. In the CloudFormation console, choose "Retry delete"
2. When prompted to retain resources, select the subnet you want to retain
3. Proceed with the stack deletion process

Approach #2: Manually Disassociate Dependent Resources
1. Go to the Amazon VPC console and navigate to the "Subnets" section
2. Locate the subnet with the ID mentioned in the error message
3. Identify and make a note of any resources (such as EC2 instances, Network Interfaces, or NAT Gateways) that are currently associated with or dependent on this subnet
4. If the resources are managed by CloudFormation, it's strongly recommended to manage the resource dependencies through CloudFormation
5. If the resources are not managed by CloudFormation, disassociate or remove the dependencies between the subnet and the associated resources
6. Once all dependencies have been removed, go back to the CloudFormation console
7. Initiate the DELETE operation again for the CloudFormation stack""",
    },
    'CONFIG_RULE_ACCESS_DENIED': {
        'error_pattern': 'An AWS service owns ServiceLinkedConfigRule.*You do not have permissions',
        'resource_type': 'AWS::Config::ConfigRule',
        'operation': 'DELETE',
        'error_code': 'AccessDeniedException',
        'analysis': 'The error indicates that you do not have the necessary permissions to perform the DELETE operation on the specified AWS::Config::ConfigRule resource. This occurs when an AWS service owns the ServiceLinkedConfigRule, and you are not authorized to delete or modify it.',
        'resolution': """It is never recommended to delete rules or the CloudFormation stack directly from the CloudFormation console for an AWS Config conformance pack, unless there is a drift between the stack and the pack.

Best practices to avoid such issues:
- Never delete the underlying CloudFormation stack for a conformance pack directly
- Instead, use the appropriate APIs to delete conformance packs:
  * For regular conformance packs, use the DeleteConformancePack API
  * For organizational conformance packs, use the DeleteOrganizationConformancePack API

Solution via AWS Management Console:
1. Open the AWS Management Console and navigate to the AWS Config service
2. In the AWS Config dashboard, click on "Rules" in the left-hand navigation pane
3. Locate the ConfigRule that is owned by the AWS service and click on its name
4. Take note of any dependencies associated with this rule
5. For each dependency, navigate to the respective service console and remove or disassociate the dependency from the ConfigRule
6. Once all dependencies have been removed, go back to the AWS CloudFormation console
7. Select the stack that contains the problematic ConfigRule
8. Click on the "Delete" button to initiate the deletion process for the stack""",
    },
    'IAM_ROLE_POLICY_ATTACHED': {
        'error_pattern': 'Cannot delete entity, must detach all policies first',
        'resource_type': 'AWS::IAM::Role',
        'operation': 'DELETE',
        'error_code': 'DeleteConflict',
        'analysis': 'The error occurs when attempting to delete an AWS IAM role that still has policies attached to it. Before deleting a role, all associated policies must be detached from the role first. This is a protective measure to prevent accidental deletion of roles with active policies.',
        'resolution': """Solution via AWS Management Console:
1. Go to the AWS Management Console and navigate to the IAM service
2. In the IAM console, select "Roles" from the left-hand navigation menu
3. Find the role that is causing the dependency violation error
4. Select the role and click on the "Permissions" tab
5. In the "Permissions" tab, scroll down to the "Permissions policies" section
6. Detach any inline policies or remove any managed policies that are associated with the role
7. Once all policies have been detached or removed, go back to the CloudFormation console
8. In the CloudFormation console, select the stack that contains the role resource
9. Click on the "Delete" button to delete the stack""",
    },
    'VPC_DEPENDENCY': {
        'error_pattern': 'The vpc.*has dependencies and cannot be deleted',
        'resource_type': 'AWS::EC2::VPC',
        'operation': 'DELETE',
        'error_code': 'DependencyViolation',
        'analysis': 'This error occurs when attempting to delete an Amazon VPC that has dependencies, meaning there are other AWS resources associated with or connected to the VPC. The VPC cannot be deleted until these dependencies are removed or disassociated from the VPC.',
        'resolution': """There are two approaches to solve this error:

Approach #1: Retry Delete from CloudFormation Console
1. In the CloudFormation console, choose "Retry delete"
2. When prompted to retain resources, select the VPC you want to retain
3. Proceed with the stack deletion process

Approach #2: Manually Disassociate Dependent Resources
1. Go to the Amazon VPC console
2. In the left navigation pane, choose "Your VPCs"
3. Select the VPC with the ID provided in the error message
4. In the details pane below, look for any resources that are associated with or dependent on this VPC, such as subnets, internet gateways, NAT gateways, or security groups
5. If the resources are not managed by CloudFormation, you can proceed to disassociate or remove the dependencies between the VPC and the associated resources
6. Once you have removed all dependencies, go back to the CloudFormation console
7. Select the stack that includes the VPC resource
8. Choose the "Delete" action to delete the stack""",
    },
    'LAMBDA_EDGE_REPLICATED': {
        'error_pattern': 'Lambda was unable to delete.*because it is a replicated function',
        'resource_type': 'AWS::Lambda::Function',
        'operation': 'DELETE',
        'analysis': 'This error occurs when attempting to delete an AWS Lambda@Edge function that has been replicated across multiple AWS regions and CloudFront edge locations. Lambda@Edge functions are designed to execute at CloudFront edge locations, and deleting a replicated function requires following a specific process to ensure proper cleanup across all replicas.',
        'resolution': """The safest way of solving this:

1. Identify the Lambda@Edge Function Resource
   - In the CloudFormation console or by reviewing the CloudFormation template, identify the resource that represents the Lambda@Edge function causing the deletion failure

2. Retain the Lambda@Edge Function Resource
   - In the CloudFormation console, when prompted to retain resources during stack deletion, select the Lambda@Edge function resource to retain
   - Proceed with the stack deletion process, allowing CloudFormation to delete all other resources except the retained Lambda@Edge function

3. Manually Delete the Lambda@Edge Function and its Replicas
   - After the stack deletion is complete, go to the AWS Lambda console
   - Locate the Lambda function specified in the error message
   - In the "Qualifiers" section, identify and expand any Lambda@Edge replicas associated with the function
   - For each replica, click the "Actions" dropdown and select "Delete"
   - Confirm the deletion of each replica when prompted
   - After deleting all replicas, delete the Lambda@Edge function""",
    },
    'CUSTOM_RESOURCE_NO_RESPONSE': {
        'error_pattern': 'See the details in CloudWatch Log Stream',
        'resource_type': 'AWS::CloudFormation::CustomResource',
        'operation': 'DELETE',
        'analysis': 'This error occurs when a custom resource fails to delete properly in an AWS CloudFormation stack. The error message indicates that the root cause and details of the failure are not provided, but can be found in the associated CloudWatch Log Stream.',
        'resolution': """Solution via AWS Management Console:
1. Go to the AWS CloudWatch service console
2. Navigate to the Log Groups section and find the log group associated with your CloudFormation stack
3. Open the log stream mentioned in the error message to view the detailed logs
4. Analyze the logs to identify any dependencies or resources that might be causing conflicts during the DELETE operation
5. If you identify any dependent resources, navigate to their respective service consoles (e.g., EC2 for instances, S3 for buckets, etc.) and remove or delete those dependencies
6. Once you have resolved the dependencies, go back to the CloudFormation console
7. Retry the DELETE operation on your CloudFormation stack""",
    },
    'ROUTE53_HOSTED_ZONE_NOT_EMPTY': {
        'error_pattern': 'The specified hosted zone.*non.*resource record sets and so cannot be deleted',
        'resource_type': 'AWS::Route53::HostedZone',
        'operation': 'DELETE',
        'analysis': 'This error occurs when attempting to delete an Amazon Route 53 hosted zone that contains non-empty resource record sets. Route 53 does not allow the deletion of a hosted zone until all associated resource record sets have been removed or transferred to another hosted zone.',
        'resolution': """Solution via AWS Management Console:
1. Open the Amazon Route 53 console
2. In the Navigation pane, select "Hosted Zones"
3. Select the Hosted Zone that is causing the dependency violation
4. In the details pane, scroll down to the "Records" section
5. Review the listed Records and identify any dependencies that need to be removed
6. Delete or modify the dependent Records as necessary except for NS/SOA records
7. Once all dependencies have been resolved, return to the CloudFormation console
8. Select the stack that encountered the error and try the DELETE operation again""",
    },
    'ECS_CLUSTER_SERVICES_ACTIVE': {
        'error_pattern': 'The Cluster cannot be deleted while Services are active',
        'resource_type': 'AWS::ECS::Cluster',
        'operation': 'DELETE',
        'analysis': 'This error occurs when attempting to delete an Amazon ECS cluster that still has active services running within it. Amazon ECS clusters cannot be deleted while they have active services, as this would disrupt the operation of those services and the tasks they are running.',
        'resolution': """There are two approaches to solve this error:

Approach #1:
If the ECS services were defined in the same CloudFormation template as the cluster, then this error should not arise if the services explicitly depend on the cluster (with a DependsOn condition). If not, their deletion order is undefined, and CloudFormation may try deleting the cluster before deleting the services.

To solve this error, retry deleting the stack, by which time the ECS Services may have already been deleted from the first try.

Approach #2:
If the services were created outside of the CloudFormation stack that created the ECS Cluster, you need to stop those services first:
1. Open the Amazon ECS console
2. In the navigation pane, choose "Clusters"
3. Select the cluster that is causing the dependency violation
4. In the "Services" tab, identify and stop any running services associated with the cluster
5. Once all services are stopped and no longer active, you can go back to the CloudFormation console
6. In the CloudFormation console, select the stack and initiate the DELETE stack operation again""",
    },
    'LOGS_DELETE_PERMISSION_DENIED': {
        'error_pattern': 'is not authorized to perform: logs:DeleteLogGroup',
        'resource_type': 'AWS::Logs::LogGroup',
        'operation': 'DELETE',
        'error_code': 'AccessDeniedException',
        'analysis': 'The error indicates that the specified IAM entity does not have the necessary permissions to perform the DeleteLogGroup action on the specified AWS CloudWatch Log Group resource. This means that the identity policy attached to the IAM entity does not grant the required authorization to delete the log group.',
        'resolution': """Solution via AWS Management Console:
1. Open the AWS Management Console and navigate to the Identity and Access Management (IAM) service
2. In the IAM console, select either "Users", "Roles" or "User Groups" as appropriate from the left-hand navigation menu
3. Find the role resource associated with the error message (the role that lacks the necessary permissions to delete the AWS::Logs::LogGroup resource)
4. Click on the role name to open the role details page
5. In the "Permissions" tab, click on the policy that should grant the required permissions (logs:DeleteLogGroup)
6. In the policy document, locate the "Statement" section and add a new statement granting the missing permission on the required resource(s)
7. Save the changes to the policy
8. Note that, in some cases, the policy may be managed by AWS, so it is not editable. In this case, add a new policy with the necessary permission
9. After updating the policy, the role should now have the necessary permissions to perform the logs:DeleteLogGroup action on the resource(s)
10. You can then return to the CloudFormation console and attempt the DELETE operation again, which should succeed
11. To avoid this error in future iterations, the change should be made in the CloudFormation template as well, not just in the console

If you do not have permissions to update policies, escalate to someone who does.""",
    },
    'LAMBDA_DELETE_PERMISSION_DENIED': {
        'error_pattern': 'is not authorized to perform: lambda:DeleteFunction',
        'resource_type': 'AWS::Lambda::Function',
        'operation': 'DELETE',
        'error_code': 'AccessDeniedException',
        'analysis': "The error indicates that the specified IAM entity does not have the necessary permissions to delete the Lambda function resource. The Lambda service has denied the request because the identity's policy does not explicitly allow the lambda:DeleteFunction action on the specified Lambda function resource.",
        'resolution': """Solution via AWS Management Console:
1. Open the AWS Management Console and navigate to the Identity and Access Management (IAM) service
2. In the IAM console, select either "Users", "Roles" or "User Groups" as appropriate from the left-hand navigation menu
3. Find the role resource associated with the error message (the role that lacks the necessary permissions to delete the AWS::Lambda::Function)
4. Click on the role name to open the role details page
5. In the "Permissions" tab, click on the policy that should grant the required permissions to delete Lambda functions
6. In the policy document, locate the "Statement" section and add a new statement granting the "lambda:DeleteFunction" permission on the required Lambda function resource(s)
7. Save the changes to the policy
8. Note that, in some cases, the policy may be managed by AWS, so it is not editable. In this case, add a new policy with the necessary "lambda:DeleteFunction" permission
9. After updating the policy, the role should now have the necessary permissions to perform the lambda:DeleteFunction action on the Lambda function resource(s)
10. You can then return to the CloudFormation console and attempt the DELETE operation again, which should succeed
11. To avoid this error in future iterations, the change should be made in the template as well, not just in the console""",
    },
    'IAM_ROLE_DELETE_POLICIES_FIRST': {
        'error_pattern': 'Cannot delete entity, must delete policies first',
        'resource_type': 'AWS::IAM::Role',
        'operation': 'DELETE',
        'error_code': 'DeleteConflict',
        'analysis': 'When attempting to delete an IAM role, AWS prevents the deletion if there are any policies attached to the role. The error message indicates that before proceeding with the deletion of the IAM role, all associated policies must be detached or removed first.',
        'resolution': """Solution via AWS Management Console:
1. Go to the AWS Management Console and navigate to the IAM service
2. In the left navigation pane, click "Roles"
3. Locate the role that is causing the dependency violation error
4. Click on the role name to open the role details page
5. In the "Permissions" tab, look for any inline policies or managed policies attached to the role
6. Remove all inline policies by clicking the "Remove" button next to each policy
7. Remove any managed policies attached to the role by clicking the "Detach" button next to each policy
8. Once all policies have been removed from the role, go back to the CloudFormation console
9. Select the stack that you were trying to delete
10. Click the "Delete" button to initiate the deletion process again""",
    },
    'CUSTOM_RESOURCE_TIMEOUT': {
        'error_pattern': 'CloudFormation did not receive a response from your Custom Resource.*requestId',
        'resource_type': 'AWS::CloudFormation::CustomResource',
        'operation': 'DELETE',
        'analysis': 'The error indicates that during a CloudFormation DELETE operation on a custom resource, the Lambda function or application responsible for handling the custom resource failed to respond to CloudFormation within the expected time frame. This failure to respond could be due to issues within the Lambda function or application code.',
        'resolution': """Lambda-based Custom Resource:
1. Open the AWS Lambda console and navigate to the Lambda function associated with the Custom Resource
2. Check the CloudWatch Logs for the Lambda function execution and look for any error messages or issues that may have caused the timeout
3. If the issue is related to the Lambda function code, update the function code to resolve the problem
4. After updating the Lambda function code, go back to the CloudFormation console
5. Attempt the DELETE operation again for the CloudFormation stack

SNS-based Custom Resource:
1. Verify SNS Topic Configuration: Ensure that your SNS topic is correctly configured and that the custom resource is subscribed to the topic
2. Check SNS Topic Access Policy: Make sure that the SNS topic has an appropriate access policy that allows CloudFormation to publish messages to the topic
3. Verify Custom Resource Code: Review the code that handles the custom resource operation and ensures that it is correctly publishing a response message to the SNS topic after the operation is complete
4. Check Logs: Check the logs of the component responsible for publishing the response message to the SNS topic
5. Increase CloudFormation Timeout: If your custom resource operation takes longer than the default CloudFormation timeout, you can increase the timeout value in your CloudFormation template
6. Update CloudFormation Stack: If you've made any changes to the SNS topic configuration, custom resource code, or CloudFormation template, you need to update your CloudFormation stack

Note: To streamline the development and testing cycle when dealing with failures in CloudFormation custom resources, leverage the ServiceTimeout property.""",
    },
    'SSM_DELETE_PERMISSION_DENIED': {
        'error_pattern': 'is not authorized to perform: ssm:DeleteParameter',
        'resource_type': 'AWS::SSM::Parameter',
        'operation': 'DELETE',
        'error_code': 'AccessDeniedException',
        'analysis': 'The error indicates that the specified IAM user, role, or group does not have the necessary permissions to delete an AWS Systems Manager (SSM) Parameter. The ssm:DeleteParameter action is being denied due to the lack of an appropriate IAM policy that grants the required permissions.',
        'resolution': """Solution via AWS Management Console:
1. Open the AWS Management Console and navigate to the Identity and Access Management (IAM) service
2. In the IAM console, select either "Users", "Roles" or "User Groups" as appropriate from the left-hand navigation menu
3. Find the role resource associated with the error message (the role that lacks the necessary permissions to perform ssm:DeleteParameter)
4. Click on the role name to open the role details page
5. In the "Permissions" tab, click on the policy that should grant the required ssm:DeleteParameter permission
6. In the policy document, locate the "Statement" section and add a new statement granting the missing ssm:DeleteParameter permission on the required resource(s)
7. Save the changes to the policy
8. Note that, in some cases, the policy may be managed by AWS, so it is not editable. In this case, add a new policy with the necessary ssm:DeleteParameter permission
9. After updating the policy, the role should now have the necessary permissions to perform the ssm:DeleteParameter action on the resource(s)
10. You can then return to the CloudFormation console and attempt the DELETE operation again, which should succeed
11. To avoid this error in future iterations, the change should be made in the template as well, not just in the console""",
    },
    'LAMBDA_REMOVE_PERMISSION_DENIED': {
        'error_pattern': 'is not authorized to perform: lambda:RemovePermission',
        'resource_type': 'AWS::Lambda::Permission',
        'operation': 'DELETE',
        'error_code': 'AccessDeniedException',
        'analysis': "This error occurs when an Identity (such as an IAM user, group, or role) attempts to remove a permission from an AWS Lambda function, but the Identity's policies do not grant the necessary lambda:RemovePermission permission on the specified Lambda function resource.",
        'resolution': """Solution via AWS Management Console:
1. Open the AWS Management Console and navigate to the Identity and Access Management (IAM) service
2. In the IAM console, select either "Users", "Roles" or "User Groups" as appropriate from the left-hand navigation menu
3. Find the resource associated with the error message (the resource that lacks the necessary permissions to perform lambda:RemovePermission)
4. Click on the resource name to open the details page
5. In the "Permissions" tab, click on the policy that should grant the required permissions to perform lambda:RemovePermission
6. In the policy document, locate the "Statement" section and add a new statement granting the lambda:RemovePermission permission on the required resource(s)
7. Save the changes to the policy
8. Note that, in some cases, the policy may be managed by AWS, so it is not editable. In this case, add a new policy with the necessary lambda:RemovePermission permission
9. After updating the policy, the role should now have the necessary permissions to perform the lambda:RemovePermission action on the resource(s)
10. You can then return to the CloudFormation console and attempt the DELETE operation again, which should succeed
11. To avoid this error in future iterations, the change should be made in the template as well, not just in the console""",
    },
    'TARGET_GROUP_IN_USE': {
        'error_pattern': 'Target group.*is currently in use by a listener or a rule',
        'resource_type': 'AWS::ElasticLoadBalancingV2::TargetGroup',
        'operation': 'DELETE',
        'analysis': 'This error occurs when attempting to delete an Elastic Load Balancing (ELB) target group that is currently in use by a listener or a rule. The target group cannot be deleted because it is associated with an active listener or rule configuration within the Elastic Load Balancing service.',
        'resolution': """Solution via AWS Management Console:
1. Go to the Amazon EC2 console and navigate to the "Load Balancers" section
2. Select the Elastic Load Balancer associated with the TargetGroup resource that triggered the error
3. Under the "Listeners" tab, identify any listeners that are currently using the TargetGroup resource
4. For each listener using the TargetGroup, either remove the TargetGroup from the listener or delete the listener entirely
5. Once all dependencies on the TargetGroup have been removed, return to the CloudFormation console
6. Initiate the DELETE operation again for the CloudFormation stack containing the TargetGroup resource""",
    },
    'LOAD_BALANCER_DELETION_PROTECTION': {
        'error_pattern': 'Load balancer.*cannot be deleted because deletion protection is enabled',
        'resource_type': 'AWS::ElasticLoadBalancingV2::LoadBalancer',
        'operation': 'DELETE',
        'analysis': 'The error indicates that the specified Elastic Load Balancing (ELB) load balancer cannot be deleted because deletion protection is enabled for that load balancer. Deletion protection is a safeguard feature that prevents accidental deletion of critical resources.',
        'resolution': """Solution via AWS Management Console:
1. Open the Amazon EC2 console at https://console.aws.amazon.com/ec2/
2. In the navigation pane, under "LOAD BALANCING", click "Load Balancers"
3. Select the Classic Load Balancer or Application Load Balancer whose ARN matches the one mentioned in the error message
4. From the "Actions" dropdown, select "Edit Attributes"
5. Scroll down to the "Deletion Protection" section and disable the "Deletion Protection" option
6. Click "Save" to apply the changes
7. Return to the CloudFormation console and retry the DELETE stack operation""",
    },
    'EC2_TERMINATION_PROTECTION': {
        'error_pattern': 'The instance.*may not be terminated.*disableApiTermination',
        'resource_type': 'AWS::EC2::Instance',
        'operation': 'DELETE',
        'analysis': 'This error occurs when attempting to terminate an Amazon EC2 instance that has the disableApiTermination attribute enabled, which prevents the instance from being terminated via the AWS Management Console, AWS CLI, or AWS SDKs. The disableApiTermination attribute is a protection mechanism that safeguards against accidental termination of instances.',
        'resolution': """Solution via AWS Management Console:
1. Open the Amazon EC2 console
2. Navigate to the "Instances" section
3. Select the instance with the ID mentioned in the error message
4. Right-click on the selected instance and choose "Instance Settings" > "Change Termination Protection"
5. In the "Termination protection" dialog box, toggle the "Termination protection" setting to "Disabled" and click "Save"
6. Return to the CloudFormation console
7. Retry the DELETE operation on the stack""",
    },
    'KMS_DELETE_ALIAS_ACCESS_DENIED': {
        'error_pattern': "Access denied for operation 'DeleteAlias'",
        'resource_type': 'AWS::KMS::Alias',
        'operation': 'DELETE',
        'error_code': 'AccessDeniedException',
        'analysis': 'This error occurs when you attempt to delete an AWS Key Management Service (KMS) alias, but you do not have the necessary permissions to perform this operation. The error indicates that your user account or role lacks the required access rights to remove the specified alias from the KMS service.',
        'resolution': """Solution via AWS Management Console:
1. Open the AWS Management Console and navigate to the AWS Key Management Service (KMS)
2. In the KMS console, select "Customer managed keys" from the left-hand navigation menu
3. Find the KMS key associated with the alias that triggered the error
4. Click on the key alias to open the key details page
5. In the "Key Users" section, check which IAM roles or users have access to use this key
6. Identify the IAM role or user that CloudFormation is using to perform the delete operation
7. If the IAM role or user does not have the "kms:DeleteAlias" permission on this KMS key, you need to add that permission
8. Open the IAM console and locate the IAM role or user identified in step 6
9. Edit the policy attached to the role or user to add the "kms:DeleteAlias" permission on the specific KMS key resource
10. Save the policy changes
11. After updating the policy, the IAM role or user should now have the necessary permissions to delete the KMS alias
12. You can then return to the CloudFormation console and attempt the DELETE operation again, which should succeed
13. To avoid this error in future iterations, the change should be made in the CloudFormation template as well, not just in the console""",
    },
    'S3_DELETE_ACCESS_DENIED': {
        'error_pattern': 'API: s3:DeleteBucket Access Denied',
        'resource_type': 'AWS::S3::Bucket',
        'operation': 'DELETE',
        'error_code': 'AccessDenied',
        'analysis': 'This error occurs when the S3 bucket policy denies the user or the IAM role executing the operation the necessary permissions to delete the specified Amazon S3 bucket. The resource type involved is an AWS::S3::Bucket, and the CloudFormation operation that triggered the error is DELETE.',
        'resolution': """There are two approaches to solve this error:

Approach #1: Retry Delete from CloudFormation Console
1. In the CloudFormation console, choose "Retry delete"
2. When prompted to retain resources, select the S3 bucket you want to retain
3. Proceed with the stack deletion process

Approach #2: Manually Delete S3 objects
1. Open the Amazon S3 console
2. From the S3 bucket list, identify the bucket that CloudFormation is attempting to delete
3. Open and edit the bucket policy to allow the Delete operation
4. Before deleting the bucket, you need to remove any dependencies or objects stored in the bucket. Select the problematic bucket and click on "Empty"
5. In the "Empty bucket" dialog, confirm that you want to permanently delete all objects in the bucket, then click "Empty"
6. Once the bucket is empty, you can proceed to delete it. Select the bucket again and click "Delete"
7. Confirm the deletion of the bucket in the dialog box
8. Return to the CloudFormation console and retry the DELETE operation""",
    },
    'CLOUDWATCH_ALARM_RATE_EXCEEDED': {
        'error_pattern': "Rate exceeded for operation 'DELETE'",
        'resource_type': 'AWS::CloudWatch::Alarm',
        'operation': 'DELETE',
        'analysis': 'This error occurs when you have exceeded the maximum allowed rate for deleting CloudWatch alarms. AWS imposes limits on the rate at which you can perform certain operations to protect the service from being overwhelmed by excessive requests.',
        'resolution': """Solution via AWS Management Console:

Wait and Retry:
- CloudFormation will automatically retry the deletion of the CloudWatch alarms after a certain period of time
- Wait for some time (e.g., 5-10 minutes) and then retry the stack deletion operation
- CloudFormation will attempt to delete the remaining CloudWatch alarms in batches to stay within the rate limits

If the Issue Persists, Increase the Deletion Delay:
1. If the rate exceeded error persists even after retrying, you can increase the delay between deletion attempts by modifying the CloudFormation service role's policy
2. Locate the CloudFormation service role in the IAM console
3. Edit the role's policy and add a statement to increase the deletion delay for CloudWatch alarms
4. After updating the CloudFormation service role's policy, retry the stack deletion process""",
    },
    'SQS_LAST_POLICY_DELETE': {
        'error_pattern': 'Last applied policy cannot be deleted',
        'resource_type': 'AWS::SQS::QueuePolicy',
        'operation': 'DELETE',
        'analysis': 'The error indicates that you are attempting to delete the last remaining resource policy associated with an AWS SQS queue. However, CloudFormation does not allow the deletion of the final policy directly applied to an SQS queue resource. To proceed, you must first delete any other policies that are currently applied to the queue before attempting to remove the last remaining policy.',
        'resolution': """Solution via AWS Management Console:
1. Go to the Amazon SQS console
2. Locate the queue that has the policy dependency issue
3. In the "Permissions" section, review the queue policies and remove any policies that are no longer needed or causing the dependency violation
4. Once you have removed the conflicting policies, go back to the CloudFormation console
5. Initiate the DELETE operation again for the CloudFormation stack""",
    },
    'CUSTOM_S3_AUTO_DELETE': {
        'error_pattern': 'CloudFormation did not receive a response from your Custom Resource',
        'resource_type': 'Custom::S3AutoDeleteObjects',
        'operation': 'DELETE',
        'analysis': 'This error indicates that AWS CloudFormation did not receive a response from a custom resource within the specified timeout period during a DELETE operation. The custom resource is a user-defined resource type, typically implemented using AWS Lambda functions or other external services.',
        'resolution': """Lambda-based Custom Resource:
1. Open the AWS Lambda console and navigate to the Lambda function associated with the Custom Resource
2. Check the logs for the specific requestId mentioned in the error message to identify any issues or exceptions in the Lambda function code
3. If the logs indicate an issue with the Lambda function code, update the code to resolve the problem
4. Once the code is updated, publish a new version of the Lambda function
5. Return to the CloudFormation console and attempt the DELETE operation again

SNS-based Custom Resource:
1. Verify SNS Topic Configuration: Ensure that your SNS topic is correctly configured and that the custom resource is subscribed to the topic
2. Check SNS Topic Access Policy: Make sure that the SNS topic has an appropriate access policy that allows CloudFormation to publish messages to the topic
3. Verify Custom Resource Code: Review the code that handles the custom resource operation and ensures that it is correctly publishing a response message to the SNS topic
4. Check Logs: Check the logs of the component responsible for publishing the response message to the SNS topic
5. Increase CloudFormation Timeout: If your custom resource operation takes longer than the default CloudFormation timeout, you can increase the timeout value in your CloudFormation template using the ServiceTimeout property
6. Update CloudFormation Stack: If you've made any changes, you need to update your CloudFormation stack

If you identify any dependent resources:
1. Identify the service resource that has a dependency on the custom resource causing the error
2. Navigate to the console of the service with the dependency and remove or detach the dependency on the resource
3. Return to the CloudFormation console and initiate the DELETE operation again""",
    },
    # CREATE/UPDATE ERRORS
    'SAGEMAKER_NOTEBOOK_LIMIT': {
        'error_pattern': 'Total number of notebook instances.*ResourceLimitExceeded',
        'resource_type': 'AWS::SageMaker::NotebookInstance',
        'operation': 'CREATE',
        'error_code': 'ResourceLimitExceeded',
        'analysis': 'The error message indicates that you have reached the account-level service limit for the total number of notebook instances in Amazon SageMaker. To resolve this issue, you need to request an increase for this service quota through the AWS Service Quotas console or by contacting AWS Support.',
        'resolution': """Solution via AWS Management Console:
1. Open the Amazon SageMaker console
2. Navigate to the "Notebook instances" section
3. Review the existing notebook instances and determine if you need to keep all of them or if you can stop or delete any unused instances
4. If you need to retain all the existing instances, go to the "Service quotas" section in the AWS Management Console
5. Click on the "AWS Services" link in the left navigation bar
6. Search for "Amazon Sagemaker" and click on it
7. Search for the "Total number of notebook instances" quota and click on "Request quota increase at account level"
8. Follow the instructions to request an increase in the quota limit for your AWS account
9. Once the quota increase is approved, you can return to the CloudFormation console and retry the CREATE operation""",
    },
    'ECS_CIRCUIT_BREAKER': {
        'error_pattern': 'ECS Deployment Circuit Breaker was triggered',
        'resource_type': 'AWS::ECS::Service',
        'operation': 'CREATE',
        'error_code': 'GeneralServiceException',
        'analysis': 'The ECS Deployment Circuit Breaker is a protective mechanism designed to prevent overwhelmed services and resource exhaustion during deployments. This error occurs when the circuit breaker is triggered due to a high rate of failures or issues during the deployment process of an Amazon ECS service.',
        'resolution': """Solution via AWS Management Console:
1. Go to the AWS CloudFormation console
2. Navigate to the stack that failed to create
3. In the stack events, look for the root cause of the failure related to the ECS service deployment
4. Common causes could be:
   - Insufficient ECS cluster capacity (CPU/memory) to run the desired task count
   - Application errors preventing the task from staying in RUNNING state
   - Network or security group issues preventing the tasks from being reachable
5. Based on the root cause identified, take appropriate action such as:
   - If insufficient cluster capacity, increase the capacity of the ECS cluster
   - If application errors, troubleshoot the application code/configuration
   - If network/security group issues, review the network and security group settings
6. Once the root cause is addressed, try updating the CloudFormation stack again to retry the ECS service creation""",
    },
    'LAMBDA_RUNTIME_DEPRECATED': {
        'error_pattern': 'The runtime parameter.*is no longer supported',
        'resource_type': 'AWS::Lambda::Function',
        'operation': 'UPDATE',
        'analysis': 'When updating or creating an AWS Lambda function, the error occurs because the specified runtime parameter is no longer supported. AWS Lambda no longer accepts the runtime parameter value that was provided, indicating that the runtime choice is outdated or deprecated.',
        'resolution': """Solution via AWS Management Console:
1. Modify your template to update the "Runtime" property in AWS::Lambda::Function (or AWS::Serverless::Function if using SAM)
2. After updating the Lambda function runtime, you should be able to successfully update the CloudFormation stack without encountering the error

To catch this and similar errors, we recommend the use of the cfn-lint CLI.""",
    },
    'IAM_POLICY_NOT_ATTACHABLE': {
        'error_pattern': 'Policy.*does not exist or is not attachable',
        'resource_type': 'AWS::IAM::Role',
        'operation': 'CREATE',
        'analysis': 'During the CREATE operation for an AWS::IAM::Role resource, this error occurs when the specified policy ARN provided as a parameter either does not exist or is not attachable to the IAM role being created. This indicates an issue with the policy ARN value itself or its compatibility with the IAM role resource.',
        'resolution': """Suggested steps:
1. In the CloudFormation console, identify the stack that is creating the IAM role
2. In the "Events" tab, make a note of the IAM policy ARN mentioned in the error message
3. Go to the AWS IAM console
4. In the navigation pane, choose "Policies"
5. Search for the IAM policy using the policy name. The policy name is the last part of the ARN you noted earlier
6. If the policy exists, then ensure that the policy ARN you have specified in the template matches the one from the console
7. If the policy doesn't exist, then proceed with creating a new one. A best practice is to apply least-privilege permissions
8. Modify the CloudFormation template and replace the IAM policy ARN with the newly created one
9. Return to the CloudFormation console and create a new stack with the updated template""",
    },
    'LAMBDA_UNZIPPED_SIZE_LIMIT': {
        'error_pattern': 'Unzipped size must be smaller than 262144000 bytes',
        'resource_type': 'AWS::Lambda::Function',
        'operation': 'UPDATE',
        'analysis': 'This error occurs when attempting to update an AWS Lambda function with a deployment package that exceeds the maximum allowed size of 262,144,000 bytes (approximately 250 MB). Lambda functions have a strict limit on the size of their deployment packages to ensure efficient execution and optimal performance.',
        'resolution': """Solution via AWS Management Console:
1. Go to the AWS Lambda console
2. Locate the Lambda function that is causing the issue
3. Click on the function name to open the function details
4. Scroll down to the "Code source" section and check the size of the deployment package
5. If the deployment package size exceeds the 262144000 bytes limit, you will need to optimize the package size
6. Consider the following steps to reduce the package size:
   - Remove any unnecessary dependencies or libraries from your project
   - Use code optimization techniques like minification or tree-shaking
   - Split your application code into multiple Lambda functions if possible
7. After optimizing the package size, update the deployment package in the CloudFormation template
8. Go back to the CloudFormation console and update the stack again

If the deployment package size exceeds the max limit, and you cannot reduce the package size, consider an alternate solution using lambda container image which supports max 10 GB image size.""",
    },
    'ECS_SERVICE_UNAVAILABLE': {
        'error_pattern': 'CreateCluster SDK error: Service Unavailable',
        'resource_type': 'AWS::ECS::Cluster',
        'operation': 'CREATE',
        'analysis': 'This error indicates that the AWS ECS (Elastic Container Service) encountered a temporary service unavailability issue while attempting to create a new cluster. The Service Unavailable message suggests that the service experienced a high load or an unexpected condition, preventing the creation of the cluster from completing successfully.',
        'resolution': """Solution via AWS Management Console:

Since the error is due to rate limiting, the recommended approach is to retry the CloudFormation operation after a short period of time:
1. Wait for a few minutes (typically 5-10 minutes) before attempting to create the ECS cluster again through CloudFormation
2. If the issue persists, you can try increasing the delay between retries or consider adjusting the deployment strategy to reduce the rate of requests

It's important to note that rate limiting errors are temporary and retrying the operation after a brief period should resolve the issue. If the problem persists, there may be other cleanup tasks required, such as deleting the stack ID previously created and trying again.""",
    },
    'LAMBDA_EMPTY_ZIP': {
        'error_pattern': 'Uploaded file must be a non.*empty zip',
        'resource_type': 'AWS::Lambda::Function',
        'operation': 'UPDATE',
        'analysis': 'This error occurs when attempting to update an AWS Lambda function with a deployment package that is either empty or not in the expected ZIP file format. The update operation requires a non-empty ZIP file containing the function code and dependencies to be provided as the deployment package.',
        'resolution': """Solution via AWS Management Console:
1. Go to the AWS Lambda console
2. Locate the Lambda function that caused the error during the CloudFormation UPDATE operation
3. In the "Code" section, click on the "Upload from" dropdown and select ".zip file"
4. Upload a non-empty and valid ZIP file containing your Lambda function code and dependencies
5. Save the changes to the Lambda function
6. Go back to the CloudFormation console and try the UPDATE operation again. Edit stack parameters if necessary""",
    },
    'LAMBDA_LAYER_NOT_EXIST': {
        'error_pattern': 'Layer version.*does not exist',
        'resource_type': 'AWS::Lambda::Function',
        'operation': 'UPDATE',
        'analysis': 'This error occurs when attempting to update an AWS Lambda function and the specified layer version ARN does not exist or is invalid. The layer version ARN is a unique identifier that references a specific version of an AWS Lambda layer, which is a package of libraries or data that can be used by multiple Lambda functions.',
        'resolution': """Solution via AWS Management Console:
1. Go to the AWS Lambda console
2. Locate the specific Lambda function resource that is causing the issue
3. Click on the "Layers" section for that Lambda function
4. Take note of the layer version ARN that you want to use is causing the issue by clicking the "Remove" or "Edit" button next to it
5. Save the changes to the Lambda function configuration
6. Use this layer version ARN in your template
7. Return to the CloudFormation console and try the UPDATE operation again for the stack""",
    },
    'ECS_SERVICE_TIMEOUT': {
        'error_pattern': 'Resource timed out',
        'resource_type': 'AWS::ECS::Service',
        'operation': 'CREATE',
        'analysis': 'During the creation of an Amazon ECS Service resource, the operation timed out before it could complete. This indicates that the process of creating the ECS Service took longer than the expected time limit, resulting in the operation being terminated prematurely.',
        'resolution': """Solution via AWS Management Console:
1. Go to the Amazon ECS console
2. Navigate to the "Clusters" section and select the cluster where the service is being created
3. Check the "Services" tab to see if the service is in a pending or provisioning state
4. If the service is stuck in a pending state, identify any dependencies that might be causing the timeout, such as:
   - Insufficient capacity in the cluster (lack of available container instances)
   - Network configuration issues (security groups, subnets, etc.)
   - IAM role or policy issues
   - Checking for container image availability
5. Resolve any identified dependencies by making necessary adjustments or configurations, not only in the console but also in the CloudFormation template when appropriate
6. After resolving the dependencies, return to the CloudFormation console
7. Retry the CREATE operation for the AWS::ECS::Service resource""",
    },
    'LAMBDA_S3_KEY_NOT_FOUND_UPDATE': {
        'error_pattern': 'Error occurred while GetObject.*S3 Error Code: NoSuchKey',
        'resource_type': 'AWS::Lambda::Function',
        'operation': 'UPDATE',
        'error_code': 'NoSuchKey',
        'analysis': 'This error occurs during an UPDATE operation on an AWS Lambda Function when the specified key or object does not exist in the configured Amazon S3 bucket. The Lambda function is likely attempting to retrieve or access a file or object from the S3 bucket, but the provided key or path is invalid or the object has been deleted or moved.',
        'resolution': """Solution via AWS Management Console:
1. Go to the Amazon S3 console
2. Navigate to the S3 bucket where the specified key or object is expected to exist
3. Check if the key or object is present in the bucket. If it's not there, you may need to update your CloudFormation template to reference the correct key or object name
4. If the key or object exists but is not accessible, review the bucket policies and object permissions to ensure that the AWS Lambda function has the necessary permissions to access the object
5. If the issue persists, check the CloudFormation template for any typos or misconfigurations related to the S3 bucket or object references""",
    },
    'LAMBDA_S3_KEY_NOT_FOUND_CREATE': {
        'error_pattern': 'Error occurred while GetObject.*S3 Error Code: NoSuchKey',
        'resource_type': 'AWS::Lambda::Function',
        'operation': 'CREATE',
        'error_code': 'NoSuchKey',
        'analysis': "This error occurs during the creation of an AWS Lambda function when the function's deployment package cannot be retrieved from the specified Amazon S3 bucket and key. The error message suggests that the deployment package file is either missing or the specified object key is incorrect.",
        'resolution': """Solution via AWS Management Console:
1. Go to the Amazon S3 console
2. Navigate to the S3 bucket where the specified key or object is expected to exist
3. Check if the key or object is present in the bucket. If it's not there, you may need to update your CloudFormation template to reference the correct key/object name or upload the correct deployment package to the S3 bucket location specified in your CloudFormation template
4. If the key or object exists but is not accessible, review the bucket policies and object permissions to ensure that the AWS Lambda function has the necessary permissions to access the object
5. If the issue persists, check the CloudFormation template for any typos or misconfigurations related to the S3 bucket or object references, ensuring that the object name does not start with "/"
6. Return to the CloudFormation console and execute the CREATE operation again with the updated template""",
    },
    'EIP_LIMIT_EXCEEDED': {
        'error_pattern': 'The maximum number of addresses has been reached',
        'resource_type': 'AWS::EC2::EIP',
        'operation': 'CREATE',
        'analysis': 'This error occurs when you have reached the maximum allowed number of Elastic IP addresses (EIPs) in your AWS account. EIPs are static IP addresses designed for dynamic cloud computing, and AWS imposes a limit on the number of EIPs that can be allocated within a single account to prevent resource exhaustion and potential abuse.',
        'resolution': """Solution via AWS Management Console:
1. Open the Amazon EC2 console and navigate to the "Elastic IPs" section
2. Review the list of allocated Elastic IP addresses and identify any that are not currently associated with an EC2 instance or a Network Interface
3. Release any unused Elastic IP addresses by selecting them and choosing the "Release Elastic IP" option
4. If you still need additional Elastic IP addresses, navigate to the "Service Quotas Dashboard" in the AWS Management Console
5. Locate the "EC2 Elastic IPs" limit and request an increase in the limit by clicking the "Request increase at account level" button
6. Provide the new limit in "Increase quota value" and click on "Request"
7. After the limit increase request is approved, you should be able to create additional Elastic IP addresses within the new limit
8. Return to the CloudFormation console and retry the CREATE operation for the AWS::EC2::EIP resource""",
    },
    'SUBNET_CIDR_CONFLICT': {
        'error_pattern': 'The CIDR.*conflicts with another subnet',
        'resource_type': 'AWS::EC2::Subnet',
        'operation': 'CREATE',
        'analysis': 'This error occurs when the CIDR block specified for an Amazon VPC subnet overlaps or conflicts with another existing subnet in the same VPC. Each subnet within a VPC must have a unique and non-overlapping CIDR block to ensure proper network isolation and routing.',
        'resolution': """Suggested steps:
1. Go to the CloudFormation console
2. Navigate to the stack that is experiencing the issue
3. In the "Events" tab, make a note of the "Logical ID" that belongs to the failed subnet
4. Make another note of the CIDR range mentioned in the error message
5. In the "Template" tab, locate the subnet resource using the "Logical ID" you noted earlier
6. Make a note of the "VpcId" property associated to the subnet resource
7. Go to the Amazon VPC console
8. Navigate to the "Your VPCs" section
9. Select the VPC ID and make a note of the VPC CIDR range
10. Navigate to the "Subnets" section
11. Identify the subnet(s) with the conflicting CIDR range mentioned in the error message and that belong to the same VPC
12. Modify the CloudFormation template to specify a non-overlapping CIDR range that falls within the VPC CIDR
13. Return to the CloudFormation console and create a new stack with the updated template""",
    },
    'LAMBDA_SECURITY_GROUP_NOT_FOUND': {
        'error_pattern': 'Error occurred while DescribeSecurityGroups.*InvalidGroup.NotFound',
        'resource_type': 'AWS::Lambda::Function',
        'operation': 'CREATE',
        'error_code': 'InvalidGroup.NotFound',
        'analysis': 'During the CREATE operation of an AWS Lambda Function resource, the AWS CloudFormation service encountered an error while attempting to describe security groups associated with the function. The specific error message indicates that the security group referenced in the CloudFormation template or configuration does not exist within the specified AWS account and region.',
        'resolution': """Suggested steps:
1. In the CloudFormation console, identify the stack that is creating the Lambda function resource
2. In the "Events" tab, make a note of the security group id mentioned in the error message
3. Go to the EC2 console and navigate to the Security Groups section
4. Check if the security group ID exists in the list of security groups. If it does not exist, proceed to the next step
5. Create a new security group. It is a best practice to authorize only the specific IP address ranges that need access to your lambda function
6. Modify the CloudFormation template and replace the security group ID with the newly created one
7. Return to the CloudFormation console and create a new stack with the updated template""",
    },
}


def match_failure_case(error_message, resource_type=None, operation=None):
    """Match an error message against known failure cases.

    Args:
        error_message: The error message from CloudFormation
        resource_type: Optional resource type (e.g., "AWS::S3::Bucket")
        operation: Optional operation type (e.g., "DELETE", "CREATE")

    Returns:
        dict: Matching failure case or None
    """
    import re

    for case_id, case_data in FAILURE_CASES.items():
        # Check error pattern match
        if re.search(case_data['error_pattern'], error_message, re.IGNORECASE):
            # Verify resource type if provided
            if resource_type and case_data['resource_type'] != resource_type:
                continue
            # Verify operation if provided
            if operation and case_data['operation'] != operation:
                continue

            return {'case_id': case_id, **case_data}

    return None
