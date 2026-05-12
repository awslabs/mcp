# Deals Application - Partition-Key-Only Schema Example

This example demonstrates a deal aggregation platform using **partition-key-only tables** and **mixed GSI designs** to optimize for high-traffic read operations and simple key-value lookups.

## Architecture Overview

The schema is designed around four tables with **mixed key designs**:
- **Deals**: Partition-key-only table for simple deal lookups
- **Users**: Partition-key-only table for user profile access
- **Brands**: Partition-key-only table for brand information
- **UserWatches**: Composite key table for user subscriptions

## Tables and Entities

### Deals (Partition Key Only)
- **Deal**: Core deal information with simple ID-based lookups
- **Key Design**: `deal_id` only - optimized for direct access
- **Use Case**: High-traffic deal browsing (5000 RPS reads)

### Users (Partition Key Only)
- **User**: User account information
- **Key Design**: `user_id` only - simple user lookups
- **Use Case**: User authentication and profile access

### Brands (Partition Key Only)
- **Brand**: Brand catalog and metadata
- **Key Design**: `brand_id` only - reference data access
- **Use Case**: Brand information lookups

### UserWatches (Composite Key)
- **UserWatch**: User subscriptions to brands and categories
- **Key Design**: `user_id` + `watch_key` - hierarchical data
- **Use Case**: Many-to-many relationships, notification fan-out

## Key Features Demonstrated

### Partition-Key-Only Tables
- **Simple lookups**: Direct GetItem operations with only partition key
- **Lower latency**: Faster access without sort key evaluation
- **Cost optimization**: Simpler keys reduce storage and transfer costs
- **Clear intent**: Schema structure matches actual access patterns

### Mixed Key Designs
- **Partition-only where sufficient**: Deals, Users, Brands use simple keys
- **Composite keys where needed**: UserWatches uses PK+SK for hierarchical data
- **Optimal for each use case**: Choose key design based on access patterns

### GSI Patterns

#### GSIs with Sort Keys (Sorted Queries)
- **DealsByBrand**: `brand_id` + `created_at` - chronologically sorted deals
- **DealsByCategory**: `category_id` + `created_at` - category browsing with sorting
- **WatchesByBrand**: `brand_id` + `user_id` - sorted list of brand watchers

#### GSIs without Sort Keys (Simple Grouping)
- **WatchesByCategory**: `category_id` only - partition-key-only GSI
- **Use Case**: Simple grouping without sorting requirements
- **Benefit**: Simpler GSI structure, lower write amplification costs

### Advanced DynamoDB Patterns
- **Sparse GSIs**: Only active deals included via status field
- **Range queries on GSIs**: Support for date-based filtering (`>=`)
- **Partition-key-only queries**: Efficient grouping without sort overhead
- **Event-driven architecture**: DynamoDB Streams for notification fan-out

## Sample Use Cases

1. **Deal Browsing**: Direct lookup by deal_id, browse by brand/category
2. **User Management**: Simple user profile access and authentication
3. **Brand Catalog**: Reference data for brand information
4. **Watch Subscriptions**: Users subscribe to brands and categories
5. **Notification Fan-out**: Query watchers for new deal notifications
6. **High-Traffic Reads**: Optimized for 5000 RPS with DAX caching
7. **Mixed Access Patterns**: Combine simple lookups with complex queries

## Partition-Key-Only Benefits

### Performance Optimization
- **Faster GetItem**: No sort key evaluation required
- **Lower latency**: Simpler key structure reduces processing time
- **Better caching**: Simpler keys improve DAX cache efficiency

### Cost Optimization
- **Reduced storage**: Smaller key sizes
- **Lower transfer costs**: Less data in keys
- **Simpler GSIs**: Partition-only GSIs have lower write costs

### Design Clarity
- **Intent clarity**: Schema clearly shows simple lookup patterns
- **Easier maintenance**: No artificial sort keys to manage
- **Better documentation**: Clear distinction between lookup and hierarchical data

## GSI Design Patterns

### When to Use Sort Keys in GSIs
- **Sorted results needed**: DealsByBrand sorts by `created_at`
- **Range queries required**: Filter deals after a specific date
- **Pagination with order**: Maintain consistent ordering

### When to Omit Sort Keys in GSIs
- **Simple grouping**: WatchesByCategory just groups by category
- **No sorting needed**: Order doesn't matter for the use case
- **Cost optimization**: Reduce write amplification

## Range Query Examples

This schema demonstrates GSI range queries:

### DealsByBrand Range Query
- **`get_recent_deals_by_brand`**: Uses `>=` on GSI sort key
  - Example: Get deals for a brand created after a specific date
  - GSI: DealsByBrand with `brand_id` + `created_at`
  - Benefit: Efficient date-based filtering on sorted GSI

## Access Pattern Mapping

### Partition-Key-Only Patterns
1. **Get deal by ID** (Pattern #1): Direct GetItem on Deals table
2. **Get user by ID** (Pattern #6): Direct GetItem on Users table
3. **Get brand by ID** (Pattern #8): Direct GetItem on Brands table

### GSI Query Patterns
3. **Browse deals by brand** (Pattern #3): Query DealsByBrand GSI
4. **Browse deals by category** (Pattern #4): Query DealsByCategory GSI
5. **Recent deals by brand** (Pattern #5): Range query on DealsByBrand GSI
11. **Get brand watchers** (Pattern #11): Query WatchesByBrand GSI
12. **Get category watchers** (Pattern #12): Query WatchesByCategory GSI (partition-only)

### Composite Key Patterns
10. **Get user watches** (Pattern #10): Query UserWatches by user_id

## Integration Patterns

### DynamoDB Streams Integration
- **Notification fan-out**: New deals trigger Lambda to query watchers
- **Async processing**: Streams feed notification delivery pipeline
- **Event-driven**: Decouple deal creation from notification delivery

### DAX Caching Strategy
- **High-traffic optimization**: 5000 RPS reads with sub-millisecond latency
- **Simple key caching**: Partition-only keys cache efficiently
- **Cost reduction**: 85% reduction in DynamoDB read costs

### OpenSearch Integration
- **Full-text search**: DynamoDB Streams → Lambda → OpenSearch
- **Search patterns**: Handle pattern #11 (search deals) via OpenSearch
- **Complementary services**: Use right tool for each access pattern

## Design Philosophy

This schema demonstrates the principle of **choosing the right key design for each use case**:

- **Simple lookups** → Partition key only (Deals, Users, Brands)
- **Hierarchical data** → Composite keys (UserWatches)
- **Sorted queries** → GSIs with sort keys (DealsByBrand, DealsByCategory)
- **Simple grouping** → GSIs without sort keys (WatchesByCategory)

By mixing key designs based on actual requirements, the schema achieves optimal performance, cost, and maintainability.

## Comparison with Composite Key Design

### Traditional Approach (All Composite Keys)
```json
{
  "table_config": {
    "partition_key": "pk",
    "sort_key": "sk"
  },
  "pk_template": "DEAL#{deal_id}",
  "sk_template": "METADATA"  // Artificial sort key
}
```

### Optimized Approach (Partition Key Only)
```json
{
  "table_config": {
    "partition_key": "deal_id"
  },
  "pk_template": "{deal_id}"  // No artificial sort key needed
}
```

**Benefits**: Simpler, faster, cheaper, and clearer intent.

## When to Use This Pattern

Choose partition-key-only tables when:
- ✅ Access pattern is simple key-value lookup
- ✅ No hierarchical data or one-to-many relationships
- ✅ High-traffic reads benefit from simplicity
- ✅ Cost optimization is important
- ✅ Schema clarity improves maintainability

Use composite keys when:
- ✅ Hierarchical data structure (user → watches)
- ✅ One-to-many relationships
- ✅ Range queries on main table sort key
- ✅ Multiple items per partition

This schema showcases both patterns working together in a real-world application.
