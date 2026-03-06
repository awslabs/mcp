---
name: diagram
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

## Common Workflows

### Workflow 1: AWS Architecture Diagram

**Goal:** Generate an AWS architecture diagram from a description.

**Steps:**
1. Load [dsl-guide.md](references/dsl-guide.md) for syntax reference
2. Load [aws-examples.md](examples/aws-examples.md) for patterns
3. Write a Python script using the `diagrams` DSL
4. Run via Bash: `mkdir -p generated-diagrams && python diagram.py`
5. Verify the PNG was created

**Critical rules:**
- ALWAYS set `show=False` in the `Diagram()` constructor
- ALWAYS set `filename="generated-diagrams/<name>"` (no `.png` extension)
- Use `with Cluster("name"):` to group related resources
- Use explicit imports: `from diagrams.aws.<service> import <Icon>`

### Workflow 2: Kubernetes Diagram

**Goal:** Generate a K8s architecture diagram.

**Steps:**
1. Load [dsl-guide.md](references/dsl-guide.md) for syntax
2. Load [general-examples.md](examples/general-examples.md) for K8s patterns
3. Write script using `diagrams.k8s.*` imports
4. Run via Bash

**Critical rules:**
- K8s imports: `from diagrams.k8s.compute import Pod, Deployment, StatefulSet`
- K8s networking: `from diagrams.k8s.network import Ingress, Service`
- Use `Cluster` for namespaces or logical groups

### Workflow 3: Sequence or Flow Diagram

**Goal:** Generate a process flow or interaction diagram.

**Steps:**
1. Load [general-examples.md](examples/general-examples.md) for flow/sequence patterns
2. Use `diagrams.programming.flowchart` for flow shapes (Decision, Action, InputOutput, etc.)
3. Run via Bash

### Workflow 4: Custom Styling

**Goal:** Customize colors, labels, and edge styles.

**Steps:**
1. Use `Edge(label="text", color="darkgreen", style="dashed")` for styled connections
2. Use `direction="TB"` or `direction="LR"` in `Diagram()` for layout direction
3. Use `Cluster` with nested `Cluster` for hierarchical grouping

**Edge styles:** `"solid"`, `"dashed"`, `"dotted"`, `"bold"`
**Common colors:** `"darkgreen"`, `"firebrick"`, `"brown"`, `"darkorange"`, `"black"`

---

## Best Practices

- **ALWAYS use `show=False`** -- prevents diagram from opening in a viewer
- **ALWAYS set `filename=`** -- save to `generated-diagrams/` subdirectory
- **MUST use explicit imports** -- `from diagrams.aws.compute import EC2`, not `import *`
- **SHOULD use `Cluster` for grouping** -- VPCs, subnets, service groups, namespaces
- **SHOULD set `direction=`** -- `"TB"` (top-to-bottom) or `"LR"` (left-to-right) for clarity
- **MUST create output directory** -- `mkdir -p generated-diagrams` before running
- **SHOULD use `Edge` for labeled connections** -- `>> Edge(label="HTTPS") >>` for clarity

---

## Additional Resources

- [diagrams documentation](https://diagrams.mingrammer.com/)
- [diagrams GitHub](https://github.com/mingrammer/diagrams)
- [GraphViz download](https://graphviz.org/download/)
- [Diagram node list](https://diagrams.mingrammer.com/docs/nodes/aws)
