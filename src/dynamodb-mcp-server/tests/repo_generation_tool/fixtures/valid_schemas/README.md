# DynamoDB Schema Design Examples

This directory contains comprehensive examples of both single-table and multi-table DynamoDB schema designs that demonstrate various access patterns, data organization strategies, and real-world application architectures.

## Overview

These examples showcase the schema formats supported by the DynamoDB MCP server code generation system. Each example represents a complete application domain demonstrating different approaches to DynamoDB data modeling - from single table designs optimized for co-location and performance, to multi-table designs optimized for domain separation and complex relationships.

## Schema Format

All examples use the `tables` array format with flexible partition and sort key templates:

```json
{
  "tables": [
    {
      "table_config": {
        "table_name": "TableName",
        "partition_key": "pk",
        "sort_key": "sk"
      },
      "entities": {
        "EntityName": {
          "pk_template": "{field}" | "TENANT#{tenant_id}#USER#{user_id}",
          "pk_params": ["field"] | ["tenant_id", "user_id"],
          "sk_template": "STATIC" | "TYPE#{field}#{timestamp}",
          "sk_params": [] | ["field", "timestamp"]
        }
      }
    }
  ]
}
```

## Single Table Design Examples

### 1. Social Media Application (`social_media_app/`)

**Domain**: Social networking and content sharing
**Table**: SocialMedia (Single Table)
**Key Features**:

- User-centric data partitioning with all user data co-located
- Hierarchical sort keys for posts, comments, likes, and follows
- Efficient timeline and feed generation
- Social interaction tracking and engagement metrics

**Partition Key Patterns**:

- Simple: `{user_id}` for user-centric data organization
- Hierarchical sort keys: `POST#{post_id}`, `COMMENT#{post_id}#{comment_id}`

**Use Cases**: User profiles, content publishing, social engagement, timeline feeds, follower management

### 2. Multi-Tenant E-Learning Platform (`elearning_platform/`)

**Domain**: Educational content delivery and progress tracking
**Table**: ELearningPlatform (Single Table)
**Key Features**:

- Complete tenant isolation with complex hierarchical partition keys
- Educational workflow support from enrollment to certification
- Detailed progress tracking and learning analytics
- Subscription-based tenant management with usage limits

**Partition Key Patterns**:

- Single tenant: `TENANT#{tenant_id}` for organization data
- Tenant + User: `TENANT#{tenant_id}#USER#{user_id}` for user-specific data
- Tenant + Course: `TENANT#{tenant_id}#COURSE#{course_id}` for course content
- Triple hierarchy: `TENANT#{tenant_id}#USER#{user_id}#COURSE#{course_id}` for progress tracking

**Use Cases**: Tenant management, course creation, user enrollment, progress tracking, certification, learning analytics

## Multi-Table Design Examples

### 3. E-commerce Application (`ecommerce_app/`)

**Domain**: Online retail and order management
**Tables**: UserTable, ProductTable, OrderTable (Multi-Table)
**Key Features**:

- User management with multiple addresses
- Product catalog with categories and reviews
- Order processing with item tracking
- Cross-table relationships between users, products, and orders

**Use Cases**: Product browsing, shopping cart, order history, inventory management

### 4. SaaS Project Management (`saas_app/`)

**Domain**: Multi-tenant project management platform
**Tables**: OrganizationTable, ProjectTable, TaskTable (Multi-Table)
**Key Features**:

- Multi-tenant organization structure
- Hierarchical project and task management
- Role-based access control
- Complex cross-project user assignments

**Use Cases**: Team collaboration, project tracking, task assignment, organizational management

### 5. Gaming Leaderboard Platform (`gaming_leaderboard/`)

**Domain**: Gaming leaderboards and achievement tracking
**Tables**: GameTable, LeaderboardTable, AchievementTable, TournamentTable (Multi-Table)
**Key Features**:

- Numeric sort keys for score-based ranking
- Player achievement tracking with point values
- Tournament management with ranking positions
- GSIs for cross-entity queries

**Use Cases**: Score submission, leaderboard queries, achievement tracking, tournament rankings

### 6. User Analytics Platform (`user_analytics/`)

**Domain**: User behavior tracking and analytics with GSI optimization
**Table**: UserAnalytics (Single Table with GSI)
**Key Features**:

- Comprehensive GSI (Global Secondary Index) implementation examples
- User behavior tracking with multiple query patterns
- Analytics-optimized data structures for reporting
- Demonstrates advanced GSI key design patterns

**GSI Patterns**:

- Status-based queries: `STATUS#{status}` partition key for filtering by user status
- Score-based analytics: `SCORE#{score}` partition key for leaderboard queries
- Time-based analysis: Sort keys with timestamps for chronological ordering

**Use Cases**: User analytics, behavior tracking, performance metrics, GSI query optimization, reporting dashboards

### 7. Deals Application (`deals_app/`)

**Domain**: Deal aggregation platform with partition-key-only tables and GSIs
**Tables**: Deals, Users, Brands, UserWatches (Multi-Table with Mixed Key Designs)
**Key Features**:

- **Partition-key-only tables**: Simple key-value lookups for Deals, Users, and Brands
- **Mixed key designs**: Composite keys where needed (UserWatches), partition-only where sufficient
- **GSIs with and without sort keys**: Demonstrates both sorted queries and simple grouping
- **Optimal for high-traffic reads**: Simple keys reduce latency and cost

**Key Design Patterns**:

- Partition-only: `{deal_id}`, `{user_id}`, `{brand_id}` for direct lookups
- Composite keys: `{user_id}` + `{watch_key}` for hierarchical data
- GSI with sort key: `{brand_id}` + `{created_at}` for sorted queries
- GSI without sort key: `{category_id}` for simple grouping

**Use Cases**: Deal browsing, user management, brand catalogs, notification fan-out, partition-key-only optimization

### 8. User Registration (`user_registration/`)

**Domain**: User registration with email uniqueness enforcement using cross-table transactions
**Tables**: Users, EmailLookup (Multi-Table with Atomic Transactions)
**Key Features**:

- **Cross-table atomic transactions**: TransactWriteItems and TransactGetItems for consistency
- **Email uniqueness enforcement**: Separate lookup table with atomic constraint checking
- **Partition-key-only tables**: Simple key-value lookups for both tables
- **Race-condition-free**: Atomic operations prevent duplicate emails
- **Referential integrity**: User and EmailLookup always in sync

**Transaction Patterns**:

- `register_user`: Atomic Put to both tables with existence checks
- `delete_user_with_email`: Atomic Delete from both tables
- `get_user_and_email`: TransactGet from both tables for consistency verification

**Key Design Patterns**:

- Partition-only: `USER#{user_id}`, `EMAIL#{email}` for direct lookups
- Condition expressions: `attribute_not_exists(pk)` for uniqueness enforcement
- TransactWrite: Atomic creates and deletes across tables
- TransactGet: Atomic reads for consistency verification

**Use Cases**: User registration, email uniqueness, account deletion, consistency verification, atomic multi-table operations

### 9. Food Delivery Service (`food_delivery_app/`)

**Domain**: Food delivery / last-mile delivery service with filter expression support
**Tables**: DeliveryTable, RestaurantTable, DriverTable (Multi-Table with Mixed Key Designs)
**Key Features**:

- **Filter expression support**: Primary test fixture for all DynamoDB filter expression variants
- **Comparison operators**: `=`, `<>`, `>=` for status exclusion, minimum totals, boolean matching
- **Range filters**: `between` for delivery fee ranges, `in` for multi-status matching
- **Function filters**: `contains`, `begins_with`, `attribute_exists`, `attribute_not_exists`, `size`
- **Logical operators**: `AND` and `OR` combinations of multiple filter conditions
- **Mixed key designs**: Composite keys (DeliveryTable, RestaurantTable) and partition-key-only (DriverTable)
- **Query and Scan filters**: Filter expressions on both Query and Scan operations

**Filter Expression Patterns**:

- Status exclusion: `status <> "CANCELLED" AND total >= 50.00`
- Fee range: `delivery_fee BETWEEN 3.00 AND 10.00`
- Multi-status: `status IN ("PENDING", "PREPARING", "EN_ROUTE")`
- Existence checks: `attribute_exists(special_instructions) AND attribute_not_exists(cancelled_at)`
- Array size: `size(items) > 3`, `size(items) BETWEEN 2 AND 5`
- Text matching: `contains(tags, "express")`, `begins_with(name, "A")`

**Use Cases**: Active order tracking, fee analysis, status filtering, driver search, restaurant discovery, large order detection

## Design Pattern Comparison

### Single Table Design Benefits

- **Cost efficiency**: Single table reduces operational costs and complexity
- **Data co-location**: Related data stored together for optimal performance
- **Atomic transactions**: All related operations can be performed atomically
- **Simplified infrastructure**: One table to manage, monitor, and scale

### Multi-Table Design Benefits

- **Domain separation**: Clear boundaries between different data types
- **Independent scaling**: Each table can be optimized for its specific access patterns
- **Flexible schema evolution**: Changes to one domain don't affect others
- **Specialized indexing**: GSIs can be tailored to specific entity requirements

## Key Patterns Demonstrated

### Single Table Patterns

- **Complex partition keys**: `TENANT#{tenant_id}#USER#{user_id}` for multi-level hierarchy
- **Hierarchical sort keys**: `POST#{post_id}`, `COMMENT#{post_id}#{comment_id}` for logical grouping
- **Type-based organization**: Entity type prefixes for efficient filtering
- **Chronological sorting**: Timestamps embedded in keys for natural ordering

### Multi-Table Patterns

- **Cross-table relationships**: Entity references in access pattern parameters
- **Denormalized data**: Strategic duplication for performance optimization
- **Consistent naming**: Unified conventions across all tables
- **Domain-specific optimization**: Each table optimized for its access patterns

### Advanced DynamoDB Techniques

- **Composite sort keys**: Enable complex sorting and filtering
- **Strategic denormalization**: Performance optimization through data duplication
- **GSI-ready design**: Sort key patterns optimized for Global Secondary Indexes
- **Time-series data**: Efficient storage and retrieval of chronological data
- **Range queries**: Date ranges, time slots, and filtered results

### GSI (Global Secondary Index) Patterns

- **Alternative partition keys**: Enable queries on non-primary key attributes
- **GSI key templates**: Template-based GSI key generation for flexible querying
- **Cross-entity queries**: GSI patterns that span multiple entity types
- **Analytics optimization**: GSI designs optimized for reporting and analytics
- **Query pattern alignment**: GSI structures that match common access patterns

## When to Choose Each Design

### Choose Single Table Design When:

- Related data is frequently accessed together
- You need atomic transactions across related entities
- Cost optimization is a primary concern
- Your access patterns are well-defined and stable
- You want simplified infrastructure management

### Choose Multi-Table Design When:

- You have distinct, independent data domains
- Different entities have vastly different access patterns
- You need to optimize for specific query types per entity
- Your application requires complex cross-entity analytics
- You want maximum flexibility for future schema changes

## Usage Instructions

1. **Choose an example** that matches your domain and access patterns
2. **Study the partition/sort key design** to understand data organization
3. **Review the access patterns** to see query optimization techniques
4. **Examine relationships** (single table hierarchy vs multi-table references)
5. **Consider your scale and cost requirements**
6. **Use as a template** for your own DynamoDB designs

## Code Generation

Each schema can be used with the DynamoDB MCP server code generation system:

```bash
uv run codegen.py --schema path/to/schema.json --language python --output ./generated
```

The generated code will include:

- Entity models with complex key builders (single table) or simple keys (multi-table)
- Repository classes optimized for the chosen design pattern
- Access pattern implementations
- Usage examples demonstrating the specific design approach

## Best Practices Demonstrated

1. **Partition key design**: Efficient data distribution and access patterns
2. **Sort key optimization**: Enables range queries and logical organization
3. **Access pattern alignment**: Designed for common query requirements
4. **Strategic denormalization**: Balances consistency with performance
5. **Scalability considerations**: Patterns that work at enterprise scale
6. **Cost optimization**: Efficient use of DynamoDB capacity and features

These examples serve as comprehensive references for building production-ready DynamoDB applications using either single table or multi-table design patterns, each optimized for different use cases and requirements.
