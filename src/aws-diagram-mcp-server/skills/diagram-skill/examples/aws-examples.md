# AWS Architecture Diagram Examples

## 1. Basic Web Service

Simple three-tier architecture.

```python
from diagrams import Diagram
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS
from diagrams.aws.network import ELB

with Diagram("Web Service Architecture", show=False, filename="generated-diagrams/aws-basic"):
    ELB("lb") >> EC2("web") >> RDS("userdb")
```

## 2. Grouped Workers

Load balancer distributing to multiple EC2 workers.

```python
from diagrams import Diagram
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS
from diagrams.aws.network import ELB

with Diagram("Grouped Workers", show=False, direction="TB", filename="generated-diagrams/aws-workers"):
    ELB("lb") >> [EC2("worker1"),
                  EC2("worker2"),
                  EC2("worker3"),
                  EC2("worker4"),
                  EC2("worker5")] >> RDS("events")
```

## 3. Clustered Web Services

DNS, load balancer, service cluster with DB replication and caching.

```python
from diagrams import Diagram, Cluster
from diagrams.aws.compute import ECS
from diagrams.aws.database import RDS, ElastiCache
from diagrams.aws.network import ELB, Route53

with Diagram("Clustered Web Services", show=False, filename="generated-diagrams/aws-clustered"):
    dns = Route53("dns")
    lb = ELB("lb")

    with Cluster("Services"):
        svc_group = [ECS("web1"),
                     ECS("web2"),
                     ECS("web3")]

    with Cluster("DB Cluster"):
        db_primary = RDS("userdb")
        db_primary - [RDS("userdb ro")]

    memcached = ElastiCache("memcached")

    dns >> lb >> svc_group
    svc_group >> db_primary
    svc_group >> memcached
```

## 4. Event Processing

EKS source, SQS queue, Lambda processors, S3 storage, Redshift analytics.

```python
from diagrams import Diagram, Cluster
from diagrams.aws.compute import ECS, EKS, Lambda
from diagrams.aws.analytics import Redshift
from diagrams.aws.integration import SQS
from diagrams.aws.storage import S3

with Diagram("Event Processing", show=False, filename="generated-diagrams/aws-events"):
    source = EKS("k8s source")

    with Cluster("Event Flows"):
        with Cluster("Event Workers"):
            workers = [ECS("worker1"),
                       ECS("worker2"),
                       ECS("worker3")]

        queue = SQS("event queue")

        with Cluster("Processing"):
            handlers = [Lambda("proc1"),
                        Lambda("proc2"),
                        Lambda("proc3")]

    store = S3("events store")
    dw = Redshift("analytics")

    source >> workers >> queue >> handlers
    handlers >> store
    handlers >> dw
```

## 5. S3 Image Processing with Bedrock

Serverless image processing pipeline using Bedrock.

```python
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.general import User
from diagrams.aws.ml import Bedrock
from diagrams.aws.storage import S3

with Diagram("S3 Image Processing with Bedrock", show=False, direction="LR", filename="generated-diagrams/aws-bedrock"):
    user = User("User")

    with Cluster("Amazon S3 Bucket"):
        input_folder = S3("Input Folder")
        output_folder = S3("Output Folder")

    lambda_function = Lambda("Image Processor Function")
    bedrock = Bedrock("Claude Sonnet 3.7")

    user >> Edge(label="Upload Image") >> input_folder
    input_folder >> Edge(label="Trigger") >> lambda_function
    lambda_function >> Edge(label="Process Image") >> bedrock
    bedrock >> Edge(label="Return Bounding Box") >> lambda_function
    lambda_function >> Edge(label="Upload Processed Image") >> output_folder
    output_folder >> Edge(label="Download Result") >> user
```
