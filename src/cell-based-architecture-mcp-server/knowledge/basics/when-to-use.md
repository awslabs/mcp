# When to Use Cell-Based Architecture?

## Ideal Use Cases

Cell-based architecture is beneficial for workloads with these characteristics:

### Critical Applications
- Applications where any downtime can have huge negative impact on customers
- FSI customers with workloads critical to economic stability
- Ultra-scale systems that are too big/critical to fail

### Strict Recovery Requirements
- Less than 5 seconds of Recovery Point Objective (RPO)
- Less than 30 seconds of Recovery Time Objective (RTO)

### Multi-Tenant Requirements
- Multi-tenant services where some tenants require fully dedicated tenancy
- Customers willing to pay for dedicated single-tenant cells

## Key Question

"Is it better for 100% of customers to experience a 5% failure rate, or 5% of customers to experience a 100% failure rate?"

Cell-based architecture chooses the latter approach.

## When NOT to Use

Cell-based architecture will not be a good choice for all workloads. Consider the disadvantages:

### Increased Complexity
- Increase in architecture complexity due to redundancy of infrastructure and components
- Requires specialized operational tools and practices to operate multiple replicas (cells)
- Necessity to invest in a cell routing layer

### Higher Costs
- High cost of infrastructure and services
- Utilization-based fee structures like Amazon EC2 Reserved Instances (RIs) and Savings Plans help close this delta

### Operational Overhead
- Need to manage tens, hundreds, or thousands of instances of your workload
- Requires automation and sophisticated deployment pipelines
- Complex observability and monitoring requirements

## Decision Framework

Consider cell-based architecture when:
1. **Scale requirements** exceed single-instance capabilities
2. **Availability requirements** are extremely high
3. **Customer impact** of outages is severe (financial, reputational)
4. **Regulatory requirements** demand fault isolation
5. **Growth trajectory** suggests need for horizontal scaling

Avoid cell-based architecture when:
1. **Simplicity** is more important than extreme resilience
2. **Cost constraints** are primary concern
3. **Team expertise** is limited for complex distributed systems
4. **Workload characteristics** don't align with partitioning strategies