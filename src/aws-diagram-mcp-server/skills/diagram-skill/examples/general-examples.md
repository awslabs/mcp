# General Diagram Examples

## 1. Sequence / Authentication Flow

Using flowchart shapes for process flows.

```python
from diagrams import Diagram
from diagrams.aws.general import User
from diagrams.programming.flowchart import Action, Decision, InputOutput

with Diagram("User Authentication Flow", show=False, filename="generated-diagrams/sequence"):
    user = User("User")
    login = InputOutput("Login Form")
    auth = Decision("Authenticated?")
    success = Action("Access Granted")
    failure = Action("Access Denied")

    user >> login >> auth
    auth >> success
    auth >> failure
```

## 2. Order Processing Flow

Decision trees and branching workflows.

```python
from diagrams import Diagram
from diagrams.programming.flowchart import Action, Decision, Delay, InputOutput, Predefined

with Diagram("Order Processing Flow", show=False, filename="generated-diagrams/flow"):
    start = Predefined("Start")
    order = InputOutput("Order Received")
    check = Decision("In Stock?")
    process = Action("Process Order")
    wait = Delay("Backorder")
    ship = Action("Ship Order")
    end = Predefined("End")

    start >> order >> check
    check >> process >> ship >> end
    check >> wait >> process
```

## 3. Class Diagram

Object relationship / inheritance diagram.

```python
from diagrams import Diagram
from diagrams.programming.language import Python

with Diagram("Simple Class Diagram", show=False, filename="generated-diagrams/class"):
    base = Python("BaseClass")
    child1 = Python("ChildClass1")
    child2 = Python("ChildClass2")

    base >> child1
    base >> child2
```

## 4. Kubernetes Exposed Pod

Ingress to service to pod replicas with HPA.

```python
from diagrams import Diagram
from diagrams.k8s.compute import Deployment, Pod, ReplicaSet
from diagrams.k8s.clusterconfig import HPA
from diagrams.k8s.network import Ingress, Service

with Diagram("Exposed Pod with 3 Replicas", show=False, filename="generated-diagrams/k8s-exposed"):
    net = Ingress("domain.com") >> Service("svc")
    net >> [Pod("pod1"),
            Pod("pod2"),
            Pod("pod3")] << ReplicaSet("rs") << Deployment("dp") << HPA("hpa")
```

## 5. Kubernetes Stateful Architecture

StatefulSet with PVCs and storage classes.

```python
from diagrams import Diagram, Cluster
from diagrams.k8s.compute import Pod, StatefulSet
from diagrams.k8s.network import Service
from diagrams.k8s.storage import PV, PVC, StorageClass

with Diagram("Stateful Architecture", show=False, filename="generated-diagrams/k8s-stateful"):
    with Cluster("Apps"):
        svc = Service("svc")
        sts = StatefulSet("sts")

        apps = []
        for _ in range(3):
            pod = Pod("pod")
            pvc = PVC("pvc")
            pod - sts - pvc
            apps.append(svc >> pod >> pvc)

    apps << PV("pv") << StorageClass("sc")
```

## 6. On-Premises Web Service (with colored edges)

Full on-prem stack with monitoring, logging, and styled edges.

```python
from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.analytics import Spark
from diagrams.onprem.compute import Server
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.logging import Fluentd
from diagrams.onprem.monitoring import Grafana, Prometheus
from diagrams.onprem.network import Nginx
from diagrams.onprem.queue import Kafka

with Diagram("Advanced Web Service with On-Premise (colored)", show=False, filename="generated-diagrams/onprem-colored"):
    ingress = Nginx("ingress")

    metrics = Prometheus("metric")
    metrics << Edge(color="firebrick", style="dashed") << Grafana("monitoring")

    with Cluster("Service Cluster"):
        grpcsvc = [
            Server("grpc1"),
            Server("grpc2"),
            Server("grpc3")]

    with Cluster("Sessions HA"):
        primary = Redis("session")
        primary - Edge(color="brown", style="dashed") - Redis("replica") << Edge(label="collect") << metrics
        grpcsvc >> Edge(color="brown") >> primary

    with Cluster("Database HA"):
        primary = PostgreSQL("users")
        primary - Edge(color="brown", style="dotted") - PostgreSQL("replica") << Edge(label="collect") << metrics
        grpcsvc >> Edge(color="black") >> primary

    aggregator = Fluentd("logging")
    aggregator >> Edge(label="parse") >> Kafka("stream") >> Edge(color="black", style="bold") >> Spark("analytics")

    ingress >> Edge(color="darkgreen") << grpcsvc >> Edge(color="darkorange") >> aggregator
```

## 7. Custom Icons

Using external images as diagram nodes.

```python
from diagrams import Diagram, Cluster
from diagrams.aws.database import Aurora
from diagrams.custom import Custom
from diagrams.k8s.compute import Pod
from urllib.request import urlretrieve

# Download an image to be used into a Custom Node class
rabbitmq_url = "https://jpadilla.github.io/rabbitmqapp/assets/img/icon.png"
rabbitmq_icon, _ = urlretrieve(rabbitmq_url, "rabbitmq.png")

with Diagram("Broker Consumers", show=False, filename="generated-diagrams/custom"):
    with Cluster("Consumers"):
        consumers = [
            Pod("worker"),
            Pod("worker"),
            Pod("worker")]

    queue = Custom("Message queue", rabbitmq_icon)

    queue >> consumers >> Aurora("Database")
```
