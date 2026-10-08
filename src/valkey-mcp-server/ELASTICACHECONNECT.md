# How to connect to an Amazon ElastiCache Valkey datastore

Amazon ElastiCache caches have one of two connection types:

* **VPC endpoint** (Node-based clusters, the default for serverless caches): You can access your ElastiCache for Valkey datastores from an Amazon EC2 instance in the same Amazon VPC, or by using VPC peering, you can access your ElastiCache for Valkey datastores from an Amazon EC2 in a different Amazon VPC. See [Connect to a cache in a VPC](#connect-to-a-cache-in-a-vpc).
* **Public endpoint** (ElastiCache Serverless for Valkey 9.0 or later, created with connection type `public`): the cache is reachable directly over the internet with IAM authentication and TLS 1.3. No EC2 instance, security group, or tunnel is needed. See [Connect to a serverless cache with a public endpoint](#connect-to-a-serverless-cache-with-a-public-endpoint).

## Connect to a cache in a VPC

Your Amazon ElastiCache for Valkey datastores are designed to be accessed through an Amazon EC2 instance. You can access your ElastiCache for Valkey datastores from an Amazon EC2 instance in the same Amazon VPC, or by using VPC peering, you can access your ElastiCache for Valkey datastores from an Amazon EC2 in a different Amazon VPC.

The following instructions will help you create an EC2 instance in the same VPC as your ElastiCache for Valkey datastore, and will guide you to configure the security groups required to access the cache from your desktop through an SSH tunnel.

### Launch and configure the EC2 instance

Complete the following steps:

1. Open the Amazon EC2 console, and then choose Launch instance.
2. Select an Amazon Machine Image (AMI).
3. Choose an instance type, and then choose Next: Configure Instance Details.
4. For Network, choose the VPC that the Amazon ElastiCache Valkey cache uses.
5. For Subnet, select the private subnet in the VPC
6. Choose Next: Add Storage, and then modify the storage as needed.
7. Choose Next: Add Tags, and then add tags as needed.
8. Choose Next: Configure Security Group.
9. Choose Add Rule, and then enter the following:
    * For Type, enter Custom TCP Rule
    * For Protocol, enter TCP
    * For Port Range, enter 22
    * For Source, enter the security group used by your Amazon EC2 connect endpoint.
10. Choose Review and Launch, and then choose Launch.

### Configure the Amazon ElastiCache Cache’s security groups

Complete the following steps:

1. Open the Amazon ElastiCache console.
2. In the navigation pane, choose Resources → Valkey caches.
3. Choose the name of the Amazon Valkey Cache. If you don't already have one, then create it.
4. Under Actions, select the option “Setup compute connection - new”
5. In the dropdown, select the EC2 instance you created above.
6. Click Setup.

This configuration for the security group allows traffic from the EC2 instance's private IP address. If the EC2 instance and the Amazon ElastiCache Valkey cache use the same VPC, then you don't need to modify the Amazon ElastiCache Valkey cache route table. If the VPC is different, then create a VPC peering connection to allow connections between those VPCs.
Note: If you use a more scalable solution, then review your configuration. For example, if you use the security group ID in a security group rule, then make sure that it doesn't restrict access to one instance. Instead, configure the rule to restrict access to any resource that uses the specific security group ID.

### Create an EC2 instance connect endpoint

1. Open the Amazon VPC console.
2. In the navigation pane, choose Endpoints.
3. Choose Create endpoint, and then specify the endpoint settings.
    * (Optional) For Name tag, enter a name for the endpoint.
    * For Service category, choose EC2 Instance Connect Endpoint.
    * For VPC, select the VPC that has the target instances.
    * (Optional) To preserve client IP addresses, expand Additional settings and select the check box. Otherwise, the default is to use the endpoint network interface as the client IP address.
    * For Security groups, select the security group you want to associate with the endpoint. Otherwise, the default is to use the default security group for the VPC.
    * For Subnet, select the subnet in which to create the endpoint.
    * (Optional) To add a tag, choose Add new tag and enter the tag key and the tag value.
4. Review your settings and then choose Create endpoint.
5. The initial status of the endpoint is Pending. To connect to an instance, you must wait until the endpoint status is Available. This can take up to a few minutes.

### Connect to the ElastiCache Valkey cache from your local machine

**Note**: You must have access to the AWS CLI.

To connect from your local MCP Server to a private Amazon ElastiCache Valkey cache through an SSH tunnel, complete the following steps:
Linux or macOS
Run the following command to open a tunnel from local machine to the EC2 instance:

```
aws ec2-instance-connect open-tunnel --instance-id ec2-instance-ID --local-port 6379
```

**Note**: Replace ec2-instance-ID with your EC2 instance ID.

Open a second connection and run the following command to create an SSH tunnel from your local host to your ElastiCache Valkey Cache through an EC2 instance:

```
ssh -i YOUR_EC2_KEY EC2_USER@EC2_HOST -p EC2_TUNNEL_PORT -L LOCAL_PORT:ELASTICACHE_ENDPOINT:REMOTE_PORT -N -f
```

**Note**: Replace the following values:
* **YOUR_EC2_KEY** with the path to your EC2 private key file
* **EC2_USER** with your EC2 instance username
* **EC2_HOST** with the hostname of your EC2 instance
* **EC2_TUNNEL_PORT** with the port you configured
* **LOCAL_PORT** with an unused port on your local machine (6379)
* **ELASTICACHE_ENDPOINT** with the endpoint of your ElastiCache Valkey cache
* **REMOTE_PORT** with the port that your Amazon ElastiCache Valkey cache uses (6379)

Use a third connection and run the following command to verify connection to your Amazon ElastiCache Valkey cache from your local machine:

```
valkey-cli -h 127.0.0.1 -p LOCAL_PORT
```

**Note**: Replace the following values:
* **LOCAL_PORT** with the number of your local port (6379)

## Connect to a serverless cache with a public endpoint

Every connection to a public endpoint cache requires **IAM authentication** and **TLS 1.3**. Static passwords are not supported: the cache must be associated with a user group in which every user uses IAM authentication (the system-managed `default.iam-user` / `default.iam-user-group` work out of the box), and the client authenticates by sending a short-lived IAM auth token as the password.

The MCP server handles this for you through Valkey GLIDE's built-in IAM support: it signs a short-lived IAM auth token with the AWS credentials available to the server. You do not generate or pass a token yourself.

### 1. Grant the `elasticache:Connect` permission

The IAM principal whose credentials the MCP server uses needs `elasticache:Connect` on **both** the cache ARN and the ElastiCache user ARN:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "elasticache:Connect",
            "Resource": [
                "arn:aws:elasticache:us-east-1:123456789012:serverlesscache:my-public-cache",
                "arn:aws:elasticache:us-east-1:123456789012:user:default.iam-user"
            ]
        }
    ]
}
```

The AWS managed policy `AdministratorAccess` already includes this permission for all resources.

### 2. Find the public endpoint address

Copy `Endpoint.Address` from the [ElastiCache console](https://console.aws.amazon.com/elasticache/) (Cache details, Endpoint) or from the CLI. Public endpoints look like `<cache-name>-<suffix>.public.serverless.<region-code>.cache.amazonaws.com`:

```
aws elasticache describe-serverless-caches --serverless-cache-name my-public-cache \
    --query "ServerlessCaches[0].Endpoint"
```

### 3. Configure the MCP server

Set these environment variables in your MCP client configuration (standard AWS credentials must also be available: environment variables, `AWS_PROFILE`, or an instance/container role):

```
VALKEY_HOST=my-public-cache-x2e9hv.public.serverless.use1.cache.amazonaws.com
VALKEY_PORT=6379
VALKEY_IAM_AUTH=true
VALKEY_USERNAME=default.iam-user      # the IAM-enabled ElastiCache user
VALKEY_CACHE_NAME=my-public-cache     # the cache name the token is signed for (lowercase)
AWS_REGION=us-east-1                  # region of the cache
VALKEY_CLUSTER_MODE=true              # matches the cluster-mode clients used in the ElastiCache docs
```

Notes:

* `VALKEY_CACHE_NAME` is the ElastiCache **cache name**, not the endpoint hostname in `VALKEY_HOST`. It must be lowercase.
* TLS is enabled automatically when `VALKEY_IAM_AUTH=true`; you do not need `VALKEY_USE_SSL`. GLIDE negotiates TLS 1.3 natively, so a TLS handshake failure usually means a proxy or TLS-inspecting device on the network path is downgrading or intercepting the connection.
* `VALKEY_PWD` is ignored when `VALKEY_IAM_AUTH=true`.
* IAM auth tokens are valid for 15 minutes (or until the temporary credentials that signed them expire, if sooner). Sessions expire after 12 hours and reconnect automatically. GLIDE handles both.
* Revoking the IAM principal's `elasticache:Connect` permission does not disconnect active sessions. To cut off access immediately, remove the user from the cache's user group.
* Account administrators can prevent public caches from being created with the `elasticache:ConnectionType` IAM condition key.

If the connection fails, see the Troubleshooting table in the [README](https://github.com/awslabs/mcp/blob/main/src/valkey-mcp-server/README.md#troubleshooting).
