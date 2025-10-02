 You can choose the broker instance type that best supports your application. When choosing an instance type, it is important to consider factors that will affect broker performance:

- the number of clients and queues
- the volume of messages sent
- messages kept in memory
- redundant messages

Smaller broker instance types (m7g.medium) are recommended only for testing application performance. We recommend larger broker instance types (m7g.large and above) for production levels of clients and queues, high throughput, messages in memory, and redundant messages.

It is important to test your brokers to determine the appropriate instance type and size for your workload messaging requirements. Use the following sizing guidelines to determine the best appropriate instance type for your application.

> ⚠️ **Important:** You cannot downgrade a broker from an mq.m5 instance type to an mq.t3.micro instance type.

> ⚠️ **Important:** You cannot downgrade a broker from an mq.m7g instance type to an mq.t3.micro instance type.

## Sizing guidelines for m7g with quorum queues for single instance deployment

The following table shows the maximum limit values for each instance type for single instance brokers.

| Instance Type | Connections | Channels | Consumers per channel | Queues | Vhosts | Shovels |
|---------------|-------------|----------|----------------------|---------|---------|---------|
| mq.m7g.medium | 100 | 500 | 1,000 | 2,500 | 10 | 150 |
| mq.m7g.large | 5,000 | 15,000 | 1,000 | 20,000 | 1500 | 250 |
| mq.m7g.xlarge | 10,000 | 30,000 | 1,000 | 30,000 | 1,500 | 500 |
| mq.m7g.2xlarge | 20,000 | 60,000 | 1,000 | 40,000 | 1,500 | 1,000 |
| mq.m7g.4xlarge | 40,000 | 120,000 | 1,000 | 60,000 | 1,500 | 2,000 |
| mq.m7g.8xlarge | 80,000 | 240,000 | 1,000 | 80,000 | 1,500 | 4,000 |
| mq.m7g.12xlarge | 120,000 | 360,000 | 1,000 | 100,000 | 1,500 | 6,000 |
| mq.m7g.16xlarge | 160,000 | 480,000 | 1,000 | 120,000 | 1,500 | 8,000 |

## Sizing guidelines for m7g with quorum queues for cluster deployment

The following table shows the maximum limit values for each instance type for cluster brokers.

| Instance Type | Connections | Channels | Consumers per channel | Queues | Vhosts | Shovels |
|---------------|-------------|----------|----------------------|---------|---------|---------|
| mq.m7g.medium | 100 | 500 | 1,000 | 100 | 10 | 50 |
| mq.m7g.large | 5,000 | 15,000 | 1,000 | 10,000 | 1,500 | 150 |
| mq.m7g.xlarge | 10,000 | 30,000 | 1,000 | 15,000 | 1,500 | 300 |
| mq.m7g.2xlarge | 20,000 | 60,000 | 1,000 | 20,000 | 1,500 | 600 |
| mq.m7g.4xlarge | 40,000 | 120,000 | 1,000 | 30,000 | 1,500 | 1,200 |
| mq.m7g.8xlarge | 80,000 | 240,000 | 1,000 | 40,000 | 1,500 | 2,400 |
| mq.m7g.12xlarge | 120,000 | 360,000 | 1,000 | 50,000 | 1,500 | 3,600 |
| mq.m7g.16xlarge | 160,000 | 480,000 | 1,000 | 60,000 | 1,500 | 4,800 |

## Sizing guidelines for m5 with CMQ single instance deployment

The following table shows the maximum limit values for each instance type for single instance brokers.

| Instance Type | Connections | Channels | Consumers per channel | Queues | Vhosts | Shovels |
|---------------|-------------|----------|----------------------|---------|---------|---------|
| m5.large | 5,000 | 15,000 | 1,000 | 30,000 | 1500 | 250 |
| m5.xlarge | 10,000 | 30,000 | 1,000 | 60,000 | 1500 | 500 |
| m5.2xlarge | 20,000 | 60,000 | 1,000 | 120,000 | 1500 | 1,000 |
| m5.4xlarge | 40,000 | 120,000 | 1500 | 240,000 | 1,000 | 2,000 |


## Sizing guidelines for m5 with CMQ cluster deployment

The following table shows the maximum limit values for each instance type for cluster brokers.

| Instance Type | Queues | Consumers per channel | Shovels |
|---------------|--------|----------------------|---------|
| m5.large | 10,000 | 1,000 | 150 |
| m5.xlarge | 15,000 | 1,000 | 300 |
| m5.2xlarge | 20,000 | 1,000 | 600 |
| m5.4xlarge | 30,000 | 1,000 | 1200 |

The following connection and channel limits are applied per node:

| Instance Type | Connections | Channels |
|---------------|-------------|----------|
| m5.large | 5000 | 15,000 |
| m5.xlarge | 10,000 | 30,000 |
| m5.2xlarge | 20,000 | 60,000 |
| m5.4xlarge | 40,000 | 120,000 |

The exact limit values for a cluster broker may be lower than the indicated value depending on the number of available nodes and how RabbitMQ distributes resources among the available nodes. If you exceed the limit values, you can create a new connection to a different node and try again, or you can upgrade the instance size to increase the maximum limits
