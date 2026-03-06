# Diagrams DSL Reference

## Installation

```bash
# Python package
pip install diagrams

# GraphViz (required renderer)
# macOS:
brew install graphviz
# Ubuntu/Debian:
sudo apt-get install graphviz
# Amazon Linux:
sudo yum install graphviz
```

## Basic Structure

```python
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import EC2, Lambda
from diagrams.aws.database import RDS, DynamoDB
from diagrams.aws.network import ELB, CloudFront

with Diagram("My Architecture", show=False, filename="generated-diagrams/my-arch"):
    with Cluster("VPC"):
        lb = ELB("ALB")
        with Cluster("Private Subnet"):
            servers = [EC2("web1"), EC2("web2")]
        db = RDS("PostgreSQL")

    CloudFront("CDN") >> lb >> servers >> db
```

## Diagram Constructor

```python
Diagram(
    name="Diagram Title",     # Title shown on the diagram
    show=False,                # ALWAYS False -- don't open viewer
    filename="path/name",      # Output path (no .png extension)
    direction="TB",            # TB (top-bottom), LR (left-right), BT, RL
    outformat="png",           # png (default), jpg, svg, pdf
)
```

## Connections

```python
# Left to right flow
node1 >> node2 >> node3

# Right to left flow
node1 << node2

# Bidirectional
node1 - node2

# Fan out to multiple
node1 >> [node2, node3, node4]

# Labeled/styled edge
node1 >> Edge(label="HTTPS", color="darkgreen", style="dashed") >> node2
```

## Clusters (Grouping)

```python
with Cluster("VPC"):
    with Cluster("Public Subnet"):
        lb = ELB("ALB")
    with Cluster("Private Subnet"):
        app = EC2("App")
        db = RDS("DB")
```

## Edge Styles

| Parameter | Values |
|-----------|--------|
| `color` | `"darkgreen"`, `"firebrick"`, `"brown"`, `"darkorange"`, `"black"`, any CSS color |
| `style` | `"solid"`, `"dashed"`, `"dotted"`, `"bold"` |
| `label` | Any string |

## Provider Import Paths

| Provider | Import Pattern | Example |
|----------|---------------|---------|
| AWS | `diagrams.aws.<service>` | `from diagrams.aws.compute import EC2` |
| GCP | `diagrams.gcp.<service>` | `from diagrams.gcp.storage import GCS` |
| Kubernetes | `diagrams.k8s.<service>` | `from diagrams.k8s.compute import Pod` |
| On-premises | `diagrams.onprem.<service>` | `from diagrams.onprem.database import PostgreSQL` |
| SaaS | `diagrams.saas.<service>` | `from diagrams.saas.chat import Slack` |
| Elastic | `diagrams.elastic.<service>` | `from diagrams.elastic.elasticsearch import Elasticsearch` |
| Programming | `diagrams.programming.<service>` | `from diagrams.programming.language import Python` |
| Generic | `diagrams.generic.<service>` | `from diagrams.generic.compute import Rack` |
| Custom | `diagrams.custom.Custom` | `Custom("name", "icon.png")` |

## AWS Service Categories (29 total)

| Category | Import Path | Common Icons |
|----------|------------|--------------|
| `analytics` | `diagrams.aws.analytics` | Athena, EMR, Glue, Kinesis, Redshift, Quicksight |
| `compute` | `diagrams.aws.compute` | EC2, Lambda, ECS, EKS, Fargate, Batch |
| `cost` | `diagrams.aws.cost` | Budgets, CostExplorer |
| `database` | `diagrams.aws.database` | RDS, DynamoDB, ElastiCache, Aurora, Redshift |
| `devtools` | `diagrams.aws.devtools` | CodeBuild, CodeDeploy, CodePipeline |
| `general` | `diagrams.aws.general` | User, Users, Client, InternetGateway |
| `integration` | `diagrams.aws.integration` | SQS, SNS, StepFunctions, EventBridge, APIGateway |
| `iot` | `diagrams.aws.iot` | IotCore, IotAnalytics |
| `management` | `diagrams.aws.management` | CloudWatch, CloudFormation, SystemsManager |
| `ml` | `diagrams.aws.ml` | Sagemaker, Rekognition, Comprehend, Bedrock |
| `network` | `diagrams.aws.network` | VPC, ELB, CloudFront, Route53, APIGateway |
| `security` | `diagrams.aws.security` | IAM, Cognito, WAF, KMS, Shield |
| `storage` | `diagrams.aws.storage` | S3, EBS, EFS, FSx |

Other categories: `ar`, `blockchain`, `business`, `enablement`, `enduser`, `engagement`, `game`, `media`, `migration`, `mobile`, `quantum`, `robotics`, `satellite`.

## Kubernetes Service Categories

| Category | Import Path | Common Icons |
|----------|------------|--------------|
| `compute` | `diagrams.k8s.compute` | Pod, Deployment, StatefulSet, ReplicaSet, DaemonSet, Job |
| `network` | `diagrams.k8s.network` | Service, Ingress, NetworkPolicy |
| `storage` | `diagrams.k8s.storage` | PV, PVC, StorageClass |
| `controlplane` | `diagrams.k8s.controlplane` | APIServer, Scheduler, ControllerManager |
| `clusterconfig` | `diagrams.k8s.clusterconfig` | HPA, Namespace, Quota |
| `rbac` | `diagrams.k8s.rbac` | Role, RoleBinding, ClusterRole |
| `infra` | `diagrams.k8s.infra` | Node, Master |
| `group` | `diagrams.k8s.group` | NS |

## On-Premises Service Categories

| Category | Common Icons |
|----------|-------------|
| `compute` | Server |
| `database` | PostgreSQL, MySQL, MongoDB, Cassandra, InfluxDB |
| `container` | Docker |
| `ci` | Jenkins, GitlabCI, GithubActions |
| `cd` | ArgoCD, FluxCD |
| `monitoring` | Prometheus, Grafana, Datadog |
| `logging` | Fluentd, Loki |
| `queue` | Kafka, RabbitMQ, Celery |
| `network` | Nginx, HAProxy, Traefik |
| `inmemory` | Redis, Memcached |
| `search` | Elasticsearch |
| `vcs` | Git, Github, Gitlab |
| `iac` | Terraform, Ansible |
| `storage` | Ceph |

## Flowchart Shapes (for sequence/flow diagrams)

```python
from diagrams.programming.flowchart import (
    Action,          # Rectangle -- process step
    Decision,        # Diamond -- yes/no branch
    InputOutput,     # Parallelogram -- data input/output
    Predefined,      # Double-border rectangle -- predefined process
    Delay,           # Half-oval -- wait/delay
)
```

## Custom Nodes (external icons)

```python
from diagrams.custom import Custom

# Download an icon and use it
from urllib.request import urlretrieve
icon_path, _ = urlretrieve("https://example.com/icon.png", "icon.png")
custom_node = Custom("My Service", icon_path)
```

## Common Patterns

### Fan-out / Fan-in
```python
source >> [worker1, worker2, worker3] >> sink
```

### Bidirectional with Replica
```python
primary = RDS("primary")
primary - RDS("replica")  # bidirectional dash
```

### Nested Clusters
```python
with Cluster("VPC"):
    with Cluster("Public"):
        lb = ELB("ALB")
    with Cluster("Private"):
        app = [EC2("app1"), EC2("app2")]
    with Cluster("Data"):
        db = RDS("db")
    lb >> app >> db
```
