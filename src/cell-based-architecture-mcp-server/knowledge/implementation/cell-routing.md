# Cell Routing

## Overview

The router layer is a shared component between cells and cannot follow the same compartmentalization strategy as cells. It must remain simple, horizontally scalable, and avoid complex business logic to prevent multi-cell impacts.

## Design Principles

### Simplicity
- Be as simple as possible, but not simpler
- Minimize business logic in routing layer
- Focus solely on request dispatching

### Isolation
- Have request dispatching isolation between cells
- Continue operating normally in other cells even when one cell is unreachable
- Abstract underlying cellular implementation from clients

### Performance
- Fast and reliable request routing
- Computationally efficient partition mapping
- Use cryptographic hash functions and modular arithmetic

## Routing Approaches

### Using Amazon Route 53

Amazon Route 53 provides DNS-based routing with high availability and scalability.

#### Characteristics
- **DNS-based routing** - Uses DNS records for cell assignment
- **100% SLA** for data plane operations
- **Health checking** - Built-in health monitoring
- **Failover capabilities** - Automatic failover to healthy cells

#### Implementation
- Give each tenant a custom DNS record
- Configure DNS record to point to assigned cell
- Use Route 53 health checks for cell monitoring
- Combine with Route 53 Application Recovery Controller

#### Advantages
- Highly available and scalable
- Built-in health checking
- Automatic failover capabilities
- No custom routing infrastructure needed

#### Disadvantages
- DNS caching can delay routing changes
- Limited to DNS-based routing patterns
- May not suit all application architectures

### Using Amazon API Gateway

API Gateway provides serverless HTTP routing with extensive features.

#### Characteristics
- **Serverless regional service** - No infrastructure management
- **Native AWS integration** - Built-in service connections
- **Rich feature set** - Caching, throttling, rate limiting
- **DynamoDB integration** - Fast partition key lookups

#### Implementation
```
Client Request → API Gateway → DynamoDB Lookup → Target Cell
```

#### Features
- Caching support for routing decisions
- Throttling and rate limiting per cell
- Canary deployments for routing changes
- Usage plan configuration
- Built-in monitoring and logging

#### DynamoDB Integration
- Single-digit millisecond latency
- 99.99% SLA (99.999% with Global Tables)
- DynamoDB Accelerator (DAX) for microsecond performance
- Seamless scalability

#### Advantages
- Serverless operation
- Rich feature set
- Native AWS service integration
- High performance with DAX

#### Disadvantages
- Regional service dependency
- Cost considerations for high-volume routing
- API Gateway limits and quotas

### Using Compute Layer with S3

Custom compute layer with S3-based configuration provides maximum flexibility.

#### Architecture Components
- **Compute layer** - EC2, ECS, EKS, or Lambda
- **Configuration storage** - S3 bucket with cell mapping
- **Synchronization** - Process to update routing tables
- **In-memory mapping** - Fast lookup performance

#### Implementation Pattern
1. Control plane writes cell mapping to S3
2. Compute layer loads mapping into memory
3. S3 change notifications trigger mapping updates
4. Router processes requests using in-memory mapping

#### Advantages
- Maximum flexibility and control
- Can implement complex routing logic
- Cost-effective for high-volume scenarios
- Custom optimization opportunities

#### Disadvantages
- Requires custom implementation
- More operational complexity
- Need to handle synchronization carefully
- Scaling and availability considerations

## Non-HTTP Routing

### Event-Based Routing

For asynchronous APIs using messaging systems:

#### Implementation
- **Message broker** - Amazon SQS, Amazon MSK, or similar
- **Router consumer** - Processes messages and routes to cells
- **Cell-specific queues** - Separate queues per cell

#### Example: Payment Processing
```
Payment Request Queue → Cell Router → Cell-Specific Queue → Cell
```

#### Considerations
- Message ordering requirements
- Dead letter queue handling
- Backpressure management
- Monitoring and alerting

### Stream-Based Routing

For real-time data processing:

#### Implementation
- **Stream ingestion** - Amazon Kinesis or similar
- **Partition key extraction** - From stream records
- **Cell assignment** - Based on partition key
- **Cell-specific streams** - Route to appropriate cell stream

## Router Resilience

### Single Point of Failure Concerns

The cell router is the only component with shared state across all cells, making it a potential single point of failure.

### Mitigation Strategies

#### High Availability Design
- Deploy router across multiple AZs
- Use load balancing for router instances
- Implement health checks and automatic failover
- Design for graceful degradation

#### Scaling Considerations
- Router must scale infinitely
- Problems should be subset of non-cellularized application challenges
- Use horizontal scaling patterns
- Implement circuit breakers

#### Static Stability
- Router continues operating with cached state
- Graceful handling of cell unavailability
- No dependencies on control plane for routing
- Fallback mechanisms for configuration failures

## Configuration Management

### Mapping State Synchronization

Critical considerations for keeping router updated:

#### Push vs Pull Models
- **Push** - Control plane pushes updates to router
- **Pull** - Router polls for configuration changes
- **Hybrid** - Combination based on urgency and reliability needs

#### Consistency Requirements
- Eventually consistent is often acceptable
- Consider impact of stale routing information
- Implement override mechanisms for urgent changes
- Monitor configuration propagation delays

#### Caching Strategies
- Balance performance with consistency
- Implement cache invalidation mechanisms
- Consider TTL-based approaches
- Monitor cache hit rates and effectiveness

## Monitoring and Observability

### Key Metrics
- **Routing latency** - Time to make routing decisions
- **Cell distribution** - Even distribution across cells
- **Error rates** - Failed routing attempts
- **Configuration lag** - Time to propagate changes

### Alerting
- Router availability and performance
- Uneven cell distribution
- Configuration synchronization failures
- Cell health and reachability