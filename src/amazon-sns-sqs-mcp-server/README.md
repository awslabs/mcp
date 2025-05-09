## Setup the MCP server
- Provision a user on your AWS account IAM.
- Attach **ONLY** `AmazonSNSFullAccess` and `AmazonSQSFullAccess` on the new user.
- Use `aws configure` on your environment to configure the credential (You need the access ID and access key that generated in previous steps)

## Features
This MCP server provides tools to:
- Create, list, and manage Amazon SNS topics
- Create, list, and manage Amazon SNS subscriptions
- Create, list, and manage Amazon SQS queues
- Send and receive messages using SNS and SQS
