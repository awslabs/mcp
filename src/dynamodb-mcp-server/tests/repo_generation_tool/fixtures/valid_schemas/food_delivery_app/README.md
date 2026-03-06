# Food Delivery Service Multi-Table Schema Example

This example demonstrates a food delivery / last-mile delivery service using multiple DynamoDB tables with filter expression support for server-side result filtering.

## Architecture Overview

The schema is designed around three main tables:
- **DeliveryTable**: Manages deliveries and delivery events
- **RestaurantTable**: Handles restaurant profiles
- **DriverTable**: Manages driver profiles (partition-key-only)

## Tables and Entities

### DeliveryTable
- **Delivery**: Core delivery records with customer, restaurant, driver, status, pricing, and items
- **DeliveryEvent**: Timestamped event log for delivery lifecycle tracking

### RestaurantTable
- **Restaurant**: Restaurant profiles with cuisine type, rating, and active status

### DriverTable
- **Driver**: Driver profiles with skills (tags), rating, delivery count, and availability (partition-key-only table)

## Key Features Demonstrated

### Filter Expression Patterns

This schema is the primary test fixture for DynamoDB filter expression support. It exercises all supported filter variants:

| Pattern | Filter Type | Example |
|---------|------------|---------|
| Comparison (`<>`, `>=`, `=`) | Status exclusion, minimum total, boolean match | `status <> "CANCELLED" AND total >= 50.00` |
| `between` | Fee range filtering | `delivery_fee BETWEEN 3.00 AND 10.00` |
| `in` | Multi-status matching | `status IN ("PENDING", "PREPARING", "EN_ROUTE")` |
| `attribute_exists` | Check for optional field presence | `attribute_exists(special_instructions)` |
| `attribute_not_exists` | Check for field absence | `attribute_not_exists(cancelled_at)` |
| `size` + comparison | Array length check | `size(items) > 3` |
| `size` + `between` | Array length range | `size(items) BETWEEN 2 AND 5` |
| `contains` | Array/string membership | `contains(tags, "express")` |
| `begins_with` | String prefix matching | `begins_with(name, "A")` |
| `AND` / `OR` | Logical combination | Multiple conditions combined |

### Query and Scan Operations
- **Query with filters**: Deliveries filtered by status, total, fee range, item count
- **Scan with filters**: Restaurants by cuisine keyword, drivers by skill tags and name prefix

### Mixed Key Designs
- **Composite keys**: DeliveryTable and RestaurantTable use PK + SK
- **Partition-key-only**: DriverTable uses PK only

### Field Type Coverage
- `string`, `decimal`, `integer`, `boolean`, `array` fields used in filter conditions
- Optional fields (`required: false`) for `attribute_exists` / `attribute_not_exists` testing

## Sample Use Cases

1. **Active Order Tracking**: Get non-cancelled deliveries above a minimum total
2. **Fee Analysis**: Find deliveries within a delivery fee range
3. **Status Filtering**: Get deliveries matching specific statuses (PENDING, PREPARING, EN_ROUTE)
4. **Special Instructions**: Find deliveries that have special instructions
5. **Large Orders**: Find deliveries with more than N items
6. **Driver Search**: Find available drivers with specific skills and experience
7. **Restaurant Discovery**: Scan for high-rated active restaurants by cuisine
8. **Event Filtering**: Get delivery events matching a type prefix
