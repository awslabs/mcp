# Common Cell-Based Architecture Patterns

## Overview

This document outlines proven patterns for implementing cell-based architectures, based on AWS service team experiences and customer implementations.

## Foundational Patterns

### Cell Zero Pattern
Start your cell-based architecture journey by treating your current stack as "cell zero."

#### Implementation
1. **Identify current stack** - Document existing architecture
2. **Add routing layer** - Implement cell router above current stack
3. **Gradual distribution** - Slowly distribute traffic according to cell partition strategy
4. **Incremental expansion** - Add new cells as needed

#### Benefits
- **Minimal initial disruption** - Existing system continues operating
- **Learning opportunity** - Gain experience with cell operations
- **Risk mitigation** - Gradual transition reduces risk
- **Validation** - Prove cell concept before full commitment

### Multi-Cell from Day One
Deploy multiple cells from the beginning, even if you could operate with one.

#### Implementation
```yaml
# Minimum recommended cell deployment
InitialCells:
  - CellId: cell-001
    Capacity: 1000 TPS
    Customers: 500
  - CellId: cell-002  
    Capacity: 1000 TPS
    Customers: 500
  - CellId: cell-003
    Capacity: 1000 TPS
    Customers: 0  # Spare capacity
```

#### Benefits
- **Operational experience** - Learn to manage multiple cells early
- **Failure isolation** - Immediate blast radius reduction
- **Scaling validation** - Prove scaling mechanisms work
- **Reduced surprises** - Identify multi-cell issues early

## Routing Patterns

### Hash-Based Routing
Simple, stateless routing using hash functions.

```python
import hashlib

def hash_based_routing(partition_key, cell_count):
    """Route based on hash of partition key"""
    hash_value = int(hashlib.md5(partition_key.encode()).hexdigest(), 16)
    return f"cell-{hash_value % cell_count:03d}"

# Example usage
customer_id = "customer-12345"
cell_id = hash_based_routing(customer_id, 10)
```

#### Use Cases
- **Stateless routing** - No routing table maintenance
- **Even distribution** - Good load distribution
- **Simple implementation** - Easy to implement and understand
- **High availability** - No single point of failure

#### Considerations
- **Migration complexity** - Changing cell count affects all customers
- **No override capability** - Cannot route specific customers to specific cells
- **Rebalancing required** - Adding/removing cells requires rebalancing

### Lookup-Based Routing
Explicit mapping table for partition key to cell assignment.

```python
import boto3

dynamodb = boto3.resource('dynamodb')
routing_table = dynamodb.Table('CellRouting')

def lookup_based_routing(partition_key):
    """Route based on explicit mapping table"""
    try:
        response = routing_table.get_item(
            Key={'PartitionKey': partition_key}
        )
        
        if 'Item' in response:
            return response['Item']['CellId']
        else:
            # New customer - assign to optimal cell
            return assign_to_optimal_cell(partition_key)
            
    except Exception as e:
        # Fallback to hash-based routing
        return hash_based_routing(partition_key, DEFAULT_CELL_COUNT)
```

#### Use Cases
- **Precise control** - Exact control over customer placement
- **Override capability** - Can route specific customers to specific cells
- **Migration support** - Easy to migrate customers between cells
- **Complex placement logic** - Support sophisticated placement algorithms

#### Considerations
- **State management** - Requires maintaining routing table
- **Performance overhead** - Lookup latency for each request
- **Availability dependency** - Routing depends on table availability
- **Storage costs** - Cost of storing routing information

### Hybrid Routing
Combination of hash-based and lookup-based routing.

```python
def hybrid_routing(partition_key, cell_count):
    """Try lookup first, fallback to hash-based"""
    # Check for explicit override
    override_cell = check_routing_override(partition_key)
    if override_cell:
        return override_cell
    
    # Check for explicit mapping
    mapped_cell = lookup_based_routing(partition_key)
    if mapped_cell:
        return mapped_cell
    
    # Fallback to hash-based routing
    return hash_based_routing(partition_key, cell_count)
```

## Data Patterns

### Table-per-Cell Pattern
Separate database tables for each cell.

```python
def get_cell_table_name(cell_id, base_table_name):
    """Generate cell-specific table name"""
    return f"{base_table_name}_{cell_id.replace('-', '_')}"

# Example usage
customer_table = get_cell_table_name("cell-001", "customers")
# Result: "customers_cell_001"
```

#### Benefits
- **Complete isolation** - No shared state between cells
- **Independent scaling** - Each table scales independently
- **Blast radius containment** - Issues affect only one cell
- **Simplified backup/restore** - Cell-level data operations

#### Considerations
- **Management overhead** - More tables to manage
- **Cross-cell queries** - Complex to query across cells
- **Schema evolution** - Need to update multiple tables
- **Cost implications** - Multiple table instances

### Shared Database with Cell Partitioning
Single database with cell-aware partitioning.

```sql
-- Add cell_id to all tables
CREATE TABLE customers (
    customer_id VARCHAR(50),
    cell_id VARCHAR(20),
    name VARCHAR(100),
    email VARCHAR(100),
    PRIMARY KEY (customer_id, cell_id)
);

-- Create cell-specific indexes
CREATE INDEX idx_customers_cell ON customers(cell_id);
```

#### Benefits
- **Simplified management** - Single database to manage
- **Cross-cell queries** - Easier to query across cells
- **Schema consistency** - Single schema to maintain
- **Cost efficiency** - Shared infrastructure costs

#### Considerations
- **Blast radius** - Database issues affect all cells
- **Scaling limitations** - Single database scaling limits
- **Isolation concerns** - Less isolation between cells
- **Performance impact** - Cross-cell queries can impact performance

## Deployment Patterns

### Canary Cell Pattern
Designate specific cells for testing new deployments.

```yaml
# Deployment configuration
DeploymentStrategy:
  Phases:
    - Name: Canary
      Cells: ["cell-canary-001"]
      TrafficPercentage: 1
      Duration: 30m
      
    - Name: Wave1
      Cells: ["cell-001", "cell-002"]
      TrafficPercentage: 20
      Duration: 1h
      
    - Name: Wave2
      Cells: ["cell-003", "cell-004", "cell-005"]
      TrafficPercentage: 50
      Duration: 2h
      
    - Name: Production
      Cells: ["*"]
      TrafficPercentage: 100
```

#### Implementation
```python
def deploy_to_canary_cells(deployment_artifact):
    """Deploy to canary cells first"""
    canary_cells = get_canary_cells()
    
    for cell_id in canary_cells:
        deploy_to_cell(cell_id, deployment_artifact)
        
        # Monitor canary cell health
        if not monitor_cell_health(cell_id, duration=30):
            rollback_cell_deployment(cell_id)
            raise Exception(f"Canary deployment failed in {cell_id}")
    
    return True
```

### Blue-Green Cell Pattern
Maintain parallel cell environments for zero-downtime deployments.

```python
def blue_green_cell_deployment(cell_id, new_version):
    """Deploy using blue-green pattern per cell"""
    
    # Create green environment
    green_cell_id = f"{cell_id}-green"
    create_cell_environment(green_cell_id, new_version)
    
    # Validate green environment
    if validate_cell_health(green_cell_id):
        # Switch traffic to green
        update_routing(cell_id, green_cell_id)
        
        # Monitor for issues
        if monitor_traffic_switch(green_cell_id, duration=10):
            # Success - cleanup blue environment
            cleanup_cell_environment(cell_id)
            rename_cell(green_cell_id, cell_id)
        else:
            # Rollback to blue
            update_routing(green_cell_id, cell_id)
            cleanup_cell_environment(green_cell_id)
    else:
        cleanup_cell_environment(green_cell_id)
        raise Exception("Green environment validation failed")
```

## Scaling Patterns

### Horizontal Cell Scaling
Add more cells to handle increased load.

```python
def horizontal_cell_scaling():
    """Monitor and scale cells horizontally"""
    system_load = get_system_load_metrics()
    
    if system_load.average_utilization > SCALE_OUT_THRESHOLD:
        # Calculate number of new cells needed
        current_cells = len(get_active_cells())
        target_cells = calculate_target_cell_count(system_load)
        new_cells_needed = target_cells - current_cells
        
        for i in range(new_cells_needed):
            new_cell_id = generate_cell_id()
            create_new_cell(new_cell_id)
            
            # Gradually migrate customers to new cell
            migrate_customers_to_cell(new_cell_id, target_count=100)
```

### Vertical Cell Scaling
Increase capacity within existing cells.

```python
def vertical_cell_scaling(cell_id):
    """Scale cell capacity vertically"""
    current_capacity = get_cell_capacity(cell_id)
    utilization = get_cell_utilization(cell_id)
    
    if utilization > SCALE_UP_THRESHOLD:
        # Increase cell capacity
        new_capacity = min(current_capacity * 1.5, MAX_CELL_CAPACITY)
        scale_cell_resources(cell_id, new_capacity)
        
        # Update cell capacity tracking
        update_cell_capacity_metadata(cell_id, new_capacity)
```

## Migration Patterns

### Gradual Customer Migration
Move customers between cells gradually to minimize impact.

```python
def gradual_customer_migration(source_cell, target_cell, migration_rate=10):
    """Migrate customers gradually between cells"""
    customers_to_migrate = get_customers_for_migration(source_cell)
    
    for batch in batch_customers(customers_to_migrate, migration_rate):
        for customer_id in batch:
            # Migrate customer data
            migrate_customer_data(customer_id, source_cell, target_cell)
            
            # Update routing
            update_customer_routing(customer_id, target_cell)
            
            # Validate migration
            if not validate_customer_migration(customer_id, target_cell):
                rollback_customer_migration(customer_id, source_cell)
        
        # Wait between batches
        time.sleep(MIGRATION_BATCH_DELAY)
```

### Hot Customer Isolation
Move high-traffic customers to dedicated cells.

```python
def isolate_hot_customers():
    """Identify and isolate high-traffic customers"""
    hot_customers = identify_hot_customers(threshold=HIGH_TRAFFIC_THRESHOLD)
    
    for customer_id in hot_customers:
        current_cell = get_customer_cell(customer_id)
        
        # Create dedicated cell for hot customer
        dedicated_cell = create_dedicated_cell(customer_id)
        
        # Migrate customer to dedicated cell
        migrate_customer_data(customer_id, current_cell, dedicated_cell)
        update_customer_routing(customer_id, dedicated_cell)
        
        # Monitor dedicated cell performance
        monitor_dedicated_cell(dedicated_cell, customer_id)
```

## Monitoring Patterns

### Cell Health Scoring
Implement comprehensive cell health scoring.

```python
def calculate_cell_health_score(cell_id):
    """Calculate comprehensive health score for cell"""
    metrics = get_cell_metrics(cell_id)
    
    # Weight different metrics
    weights = {
        'availability': 0.3,
        'response_time': 0.25,
        'error_rate': 0.25,
        'capacity_utilization': 0.2
    }
    
    scores = {
        'availability': min(metrics.availability / 99.9, 1.0),
        'response_time': max(0, 1.0 - (metrics.avg_response_time / 1000)),
        'error_rate': max(0, 1.0 - (metrics.error_rate / 5.0)),
        'capacity_utilization': 1.0 - abs(metrics.utilization - 0.7) / 0.3
    }
    
    health_score = sum(scores[metric] * weights[metric] for metric in weights)
    return min(max(health_score, 0.0), 1.0)
```

### Cross-Cell Comparison
Compare performance across cells to identify outliers.

```python
def identify_outlier_cells():
    """Identify cells performing significantly different from others"""
    cells = get_active_cells()
    cell_metrics = {}
    
    for cell_id in cells:
        cell_metrics[cell_id] = get_cell_performance_metrics(cell_id)
    
    # Calculate system averages
    avg_response_time = statistics.mean([m.response_time for m in cell_metrics.values()])
    avg_error_rate = statistics.mean([m.error_rate for m in cell_metrics.values()])
    
    outliers = []
    for cell_id, metrics in cell_metrics.items():
        if (metrics.response_time > avg_response_time * 1.5 or 
            metrics.error_rate > avg_error_rate * 2.0):
            outliers.append({
                'cell_id': cell_id,
                'response_time_ratio': metrics.response_time / avg_response_time,
                'error_rate_ratio': metrics.error_rate / avg_error_rate
            })
    
    return outliers
```

## Best Practices

### Pattern Selection Guidelines
- **Start simple** - Begin with basic patterns and evolve
- **Consider trade-offs** - Each pattern has benefits and costs
- **Match requirements** - Choose patterns that fit your specific needs
- **Plan for evolution** - Design patterns that can evolve over time

### Implementation Principles
- **Gradual adoption** - Implement patterns incrementally
- **Comprehensive testing** - Test patterns thoroughly before production
- **Monitoring integration** - Ensure patterns are observable
- **Documentation** - Document pattern decisions and rationale

### Operational Excellence
- **Automation** - Automate pattern implementation where possible
- **Standardization** - Use consistent patterns across cells
- **Training** - Ensure team understands chosen patterns
- **Continuous improvement** - Regularly review and improve patterns