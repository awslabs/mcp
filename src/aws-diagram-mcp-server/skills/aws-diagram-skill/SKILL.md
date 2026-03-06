---
name: aws diagram
description: >
  Generate architecture diagrams using the Python diagrams DSL. Use when
  user requests architecture diagrams, system design visuals, or
  infrastructure diagrams for AWS, Kubernetes, or on-premises systems.
allowed-tools: Bash, Read, Write
---

# Architecture Diagram Skill

Generate professional architecture diagrams using the Python [diagrams](https://diagrams.mingrammer.com/) package. Supports AWS (29 service categories), Kubernetes, on-premises, GCP, SaaS, and more.

**Output:** PNG images saved to `generated-diagrams/` in the workspace.

---

## Reference Files

Load these files as needed for detailed guidance:

### [dsl-guide.md](references/dsl-guide.md)
**When:** ALWAYS load before writing diagram code
**Contains:** Full DSL reference -- imports, Diagram/Cluster/Edge syntax, provider import paths, all AWS service categories

### [icon-reference.md](references/icon-reference.md)
**When:** Load when you need to find the correct class name for a specific service or icon
**Contains:** Complete listing of all providers, services, and icon class names

### [aws-examples.md](examples/aws-examples.md)
**When:** Load when generating AWS architecture diagrams
**Contains:** 5 AWS examples -- basic, grouped workers, clustered services, event processing, Bedrock

### [general-examples.md](examples/general-examples.md)
**When:** Load when generating non-AWS diagrams (K8s, on-prem, sequence, flow, class, custom icons)
**Contains:** 7 examples -- sequence, flow, class, K8s, on-prem, colored edges, custom icons

---

## Prerequisites

Requires two dependencies installed locally:

1. **GraphViz** (system package -- provides the `dot` renderer):
   - macOS: `brew install graphviz`
   - Ubuntu/Debian: `sudo apt-get install graphviz`
   - Amazon Linux: `sudo yum install graphviz`
2. **Python `diagrams` package**: `pip install diagrams`

Run `scripts/setup.sh` to check and guide installation.

---

## Quick Start

### 1. Generate a simple diagram

```python
from diagrams import Diagram
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS
from diagrams.aws.network import ELB

with Diagram("Web Service", show=False, filename="generated-diagrams/web-service"):
    ELB("lb") >> EC2("web") >> RDS("db")
```

### 2. Run it

```bash
mkdir -p generated-diagrams
python diagram.py
# Output: generated-diagrams/web-service.png
```

---

## Best Practices

- **ALWAYS use `show=False`** -- prevents diagram from opening in a viewer
- **ALWAYS set `filename=`** -- save to `generated-diagrams/` subdirectory
- **MUST use explicit imports** -- `from diagrams.aws.compute import EC2`, not `import *`
- **SHOULD use `Cluster` for grouping** -- VPCs, subnets, service groups, namespaces
- **MUST create output directory** -- `mkdir -p generated-diagrams` before running
