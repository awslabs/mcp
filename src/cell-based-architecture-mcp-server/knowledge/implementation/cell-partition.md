# Cell Partition

## Overview

Cell partition refers to the strategy used to map partition keys (like customer IDs) to specific cells. The choice of partitioning approach significantly impacts performance, scalability, and operational complexity.

## Full Mapping

Full mapping maintains an explicit mapping table that associates each partition key with its assigned cell.

### Characteristics
- **Explicit mapping** - Direct key-to-cell associations
- **Complete control** - Full control over partition placement
- **Flexibility** - Easy to implement custom placement logic
- **State overhead** - Requires storing mapping for every key

### Advantages
- Perfect control over partition placement
- Easy to implement special routing rules
- Supports complex placement strategies
- Natural support for override tables

### Disadvantages
- Higher memory usage for large key spaces
- Performance cost when cardinality is too high
- Longer cell router bootstrap time if map is kept in memory
- Scaling challenges with very large partition key spaces

### Use Cases
- Smaller partition key spaces
- Applications requiring precise control over placement
- Systems with complex routing requirements
- Scenarios where override capabilities are essential

## Prefix and Range-Based Mapping

Prefix and range-based mapping groups ranges of keys (or hashes of keys) to cells, reducing the cardinality of the mapping table.

### Characteristics
- **Range grouping** - Keys grouped into ranges assigned to cells
- **Reduced cardinality** - Fewer mapping entries than full mapping
- **Balanced complexity** - Middle ground between full mapping and algorithmic approaches
- **Flexible granularity** - Range size can be adjusted based on needs

### Advantages
- Reduces performance issues of full mapping
- Lower memory requirements than full mapping
- Maintains reasonable control over placement
- Supports hierarchical partitioning strategies

### Disadvantages
- More likely to have hot cells
- No control over which keys within each range have most traffic
- Range boundaries may not align with natural traffic patterns
- Requires careful range design

### Implementation Example
```
Range 000-199: Cell A
Range 200-399: Cell B  
Range 400-599: Cell C
Range 600-799: Cell D
Range 800-999: Cell E
```

## Naïve Modulo Mapping

Naïve modulo mapping uses modular arithmetic to map keys to cells, typically on a cryptographic hash of the key.

### Characteristics
- **Algorithmic mapping** - Uses hash(key) % cell_count
- **Zero state** - No mapping table required
- **Even distribution** - Very even distribution across cells
- **High churn** - Significant reassignment when cell count changes

### Advantages
- Simple to implement
- Avoids hot cells through even distribution
- Minimal state requirements
- Predictable performance characteristics

### Disadvantages
- Changing cell count requires rebalancing all cells
- High customer/tenant migration during scaling
- Difficult to implement override rules
- No control over specific key placement

### Implementation Example
```python
def get_cell(partition_key, cell_count):
    hash_value = hash(partition_key)
    return hash_value % cell_count
```

## Consistent Hashing

Consistent hashing maps keys to buckets (cells) with minimal churn when adding or removing buckets.

### Ring Consistent Hash
- Maps keys and cells to points on a circle
- Keys assigned to next clockwise cell
- Can suffer from uneven distribution
- Improved with virtual nodes

### Modern Algorithms
- **Fast, Minimal Memory Consistent Hash** (Lamping and Veach)
- **Multi-probe Consistent Hashing** (Appleton and O'Reilly)
- Better peak-to-average ratios
- Reduced state requirements

### Two-Step Process
1. **Logical buckets** - Fixed large number (tens of thousands)
2. **Physical mapping** - Logical buckets mapped to actual cells

### Advantages
- Minimal churn when adding/removing cells
- Simple to implement
- Good balance of distribution and stability
- Supports gradual migration

### Disadvantages
- Can suffer from uneven distribution
- More complex than naïve modulo
- May require tuning for optimal distribution
- Additional indirection layer

## Override Tables

Regardless of partition mapping approach, implement override tables to force specific keys to specific cells.

### Use Cases
- **Testing** - Route test traffic to specific cells
- **Quarantining** - Isolate problematic customers
- **Special routing** - Handle particularly heavy partition keys
- **Migration** - Temporary routing during cell transitions

### Implementation
- Checked before primary mapping algorithm
- Takes precedence over algorithmic assignment
- Should be kept small for performance
- Requires careful management and monitoring

## Choosing the Right Approach

### Consider Full Mapping When:
- Partition key space is manageable
- Precise control over placement is required
- Override capabilities are essential
- Performance of mapping lookup is acceptable

### Consider Range-Based When:
- Need balance between control and performance
- Partition keys have natural groupings
- Want to reduce mapping table size
- Can tolerate some hot cell risk

### Consider Modulo When:
- Even distribution is most important
- Simplicity is valued
- Cell count changes are infrequent
- Override capabilities not needed

### Consider Consistent Hashing When:
- Frequent cell additions/removals expected
- Want to minimize customer migration
- Can tolerate some distribution unevenness
- Need good balance of all factors