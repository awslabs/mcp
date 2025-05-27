# How to connect to an Amazon ElastiCache Memcached cache

Your Amazon ElastiCache instances are designed to be accessed through an Amazon EC2 instance. You can access your ElastiCache instance from an Amazon EC2 instance in the same Amazon VPC, or by using VPC peering, you can access your ElastiCache instance from an Amazon EC2 in a different Amazon VPC.

The following instructions will help you create an EC2 instance in the same VPC as your cache instance, and will guide you to configure the security groups required to access the cache from your desktop through an SSH tunnel.

## Launch and configure the EC2 instance

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

## Configure the Amazon ElastiCache Memcached Cache’s security groups

Complete the following steps:

1. Open the Amazon ElastiCache console.
2. In the navigation pane, choose Resources → Memcached caches.
3. Choose the name of the Amazon Memcached Cache. If you don't already have one, then create it.
4. Choose Connectivity & security.
5. From the Security section, choose the link under VPC security groups.
6. Select the security group, choose Actions, and then choose Edit inbound rules.
7. Choose Add rule, and then enter the following:
   - For Type, enter Custom TCP Rule
   - For Protocol, enter TCP
   - For Port Range, enter the port of your Amazon ElastiCache Memcached cache (11211).
   - For Source, enter the private IP address of your EC2 instance.
8. Choose Save.

This configuration for the security group allows traffic from the EC2 instance's private IP address. If the EC2 instance and the Amazon ElastiCache Memcached cache use the same VPC, then you don't need to modify the Amazon ElastiCache Memcached cache route table. If the VPC is different, then create a VPC peering connection to allow connections between those VPCs.
Note: If you use a more scalable solution, then review your configuration. For example, if you use the security group ID in a security group rule, then make sure that it doesn't restrict access to one instance. Instead, configure the rule to restrict access to any resource that uses the specific security group ID.

## Create an EC2 instance connect endpoint

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

## Connect to the ElastiCache Memcached cache from your local machine

**Note**: You must have access to the AWS CLI.

To connect from your local MCP Server to a private Amazon ElastiCache Memcached cache through an SSH tunnel, complete the following steps:
Linux or macOS
Run the following command to open a tunnel from local machine to the EC2 instance:

```
aws ec2-instance-connect open-tunnel --instance-id ec2-instance-ID --local-port 11211
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
* **LOCAL_PORT** with an unused port on your local machine (11211)
* **ELASTICACHE_ENDPOINT** with the endpoint of your ElastiCache Memcached cache
* **REMOTE_PORT** with the port that your Amazon ElastiCache Memcached cache uses (11211)

Use a third connection and run the following command to verify connection to your Amazon ElastiCache Memcached cache from your local machine:

```
telnet 127.0.0.1 LOCAL_PORT
```

**Note**: Replace the following values:
* **LOCAL_PORT** with the number of your local port (11211)
