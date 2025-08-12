# Shared Responsibility Model for Resiliency

## Overview

In the Shared Responsibility Model for Resiliency, there are clear distinctions between AWS responsibility (Resiliency of the Cloud) and customer responsibility (Resiliency in the Cloud).

## AWS Responsibility: Resiliency OF the Cloud

AWS provides foundational isolation boundaries:
- **Availability Zones (AZs)** - Physically separated data centers
- **AWS Regions** - Geographic separation of infrastructure
- **Control planes** - Administrative and management functions
- **Data planes** - Core service functionality

## Customer Responsibility: Resiliency IN the Cloud

Cell-based architecture is part of your responsibility for Resiliency in the Cloud. This includes:
- **Workload architecture design**
- **Application-level fault isolation**
- **Data partitioning strategies**
- **Recovery mechanisms**

## Adding Cell-Based Isolation

Cell-based architecture allows you to add another level of fault isolation, going beyond the Availability Zones and Regions that AWS provides. This creates multiple layers of protection:

```
Region Level (AWS)
├── Availability Zone Level (AWS)
    ├── Cell Level (Customer)
        ├── Application Components (Customer)
```

## Operating Under Shared Model

Understanding how cell-based architecture operates under this shared model is important because:

1. **AWS handles infrastructure resilience** - You can rely on AZ and Region isolation
2. **You handle application resilience** - Cell design and implementation is your responsibility
3. **Combined protection** - Both layers work together for maximum resilience

## Benefits of Layered Approach

- **Multiple failure boundaries** - Failures can be contained at different levels
- **Reduced blast radius** - Impact is limited by the smallest affected boundary
- **Independent recovery** - Different layers can recover independently
- **Predictable behavior** - Well-defined responsibilities at each layer