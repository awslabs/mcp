# Cell Sizing

## Overview

Cell-based architectures benefit from capping the maximum size of a cell and using consistent cell sizes across different installations (AZs or Regions). Cell sizing involves balancing three opposing forces:

1. **Big enough** to fit the largest workloads
2. **Small enough** to test at full scale and operate efficiently
3. **Big enough** to gain economies of scale benefits

## Size Trade-offs

### Smaller Cells

#### Advantages
- **More cells needed** - Smaller cells require more replicas to handle total workload
- **Reduced scope of impact** - Cell outage affects smaller percentage of customers (10 cells = 10% impact per cell vs 100 cells = 1% impact per cell)
- **Less likely to hit scaling limitations** - Lower probability of reaching AWS service limits and quotas
- **Easier to test** - Cheaper and more practical to test at full cell capacity
- **Less idle resources** - Better resource utilization with smaller capacity

#### Disadvantages
- **More operational complexity** - More cells to manage and operate
- **Higher overhead** - More infrastructure overhead per unit of capacity

### Larger Cells

#### Advantages
- **Fewer cells needed** - Fewer replicas to manage and operate
- **Better capacity utilization** - Greater economy of scale in resources
- **Reduced splits** - Less likely to need to split individual client workloads across cells
- **Easier to operate** - Fewer total instances to manage

#### Disadvantages
- **Larger scope of impact** - Cell outage affects larger percentage of infrastructure and customers
- **More likely to reach scaling limitations** - Higher probability of hitting AWS service limits
- **Harder to test** - More expensive and complex to test at full scale

## Defining Scaling Dimensions

Cell sizing is closely related to your partition key and defines how much load a cell can support before needing to scale out.

### Key Considerations

#### Granular Scale Units
Consider the most granular and independent unit in your system:
- **Customer ID** - Most obvious choice but may have limitations
- **Resource ID** - May provide better distribution
- **Composite keys** - Combination of multiple factors

#### Large Customer Problem
If you define a cell can handle 10K TPS, but a single client grows beyond that:
- System becomes unable to scale-out
- Forced to scale-up (if possible) or unable to serve large customer
- Need dedicated cells or multiple cells per large customer

#### Multiple Dimensions
Define more than one scale unit dimension:
- **Transactions per second** - Request volume capacity
- **Customer count** - Number of tenants per cell
- **Data volume** - Storage capacity per cell
- **Bandwidth** - Network throughput capacity

### Scaling Dimension Examples

```
Cell Capacity Limits:
- 10,000 TPS
- 1,000 customers
- 100 GB storage
- 1 Gbps bandwidth
```

## Know and Respect Cell Limits

### Load Testing and Validation
- Determine limits through load testing and chaos engineering
- Test beyond normal capacity to understand breaking points
- Validate performance under stress conditions
- Document safe operating margins

### Load Shedding Implementation
- Use load shedding to avoid overload
- Implement at multiple layers (API Gateway, application level)
- Use algorithms like token bucket for rate limiting
- Monitor and alert on approaching limits

### AWS Service Integration
- **Amazon API Gateway** - Rate limiting at API and stage level
- **Application Load Balancer** - Request rate limiting
- **Custom implementation** - Token bucket algorithms

### Example: Token Bucket Algorithm
```python
class TokenBucket:
    def __init__(self, capacity, refill_rate):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()
    
    def consume(self, tokens=1):
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self):
        now = time.time()
        tokens_to_add = (now - self.last_refill) * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
```

## Cost Considerations

### Economic Factors
- Calculate cost per cell for different sizes
- Consider multi-tenancy vs dedicated tenancy pricing
- Factor in operational overhead costs
- Evaluate economies of scale benefits

### Revenue Opportunities
- **Dedicated cells** - Premium pricing for single-tenant cells
- **Enterprise features** - Higher-tier service offerings
- **SLA differentiation** - Different availability guarantees

### Cost Optimization
- Use Reserved Instances and Savings Plans
- Right-size instances based on actual usage
- Implement auto-scaling within cells
- Monitor and optimize resource utilization

## Capacity Planning

### Monitoring Requirements
- Track current capacity utilization per cell
- Monitor growth trends and patterns
- Alert on approaching capacity limits
- Plan for seasonal or event-driven spikes

### Scaling Triggers
- **Proactive scaling** - Based on growth projections
- **Reactive scaling** - Based on current utilization
- **Predictive scaling** - Using machine learning models
- **Manual scaling** - For planned events or migrations

### Capacity Buffers
As recommended in REL01-BP06: "Ensure sufficient gap exists between current quotas and maximum usage to accommodate failover."

- Maintain headroom for failover scenarios
- Account for uneven distribution across cells
- Plan for cell evacuation scenarios
- Consider burst capacity requirements

## Best Practices

### Consistent Sizing
- Use consistent cell sizes across environments
- Standardize resource allocation patterns
- Maintain uniform capacity limits
- Document sizing decisions and rationale

### Testing Strategy
- Regular load testing at cell limits
- Chaos engineering to validate failure modes
- Performance regression testing
- Capacity planning validation

### Monitoring and Alerting
- Real-time capacity utilization metrics
- Predictive alerting for capacity exhaustion
- Cell health and performance monitoring
- Cost tracking and optimization alerts