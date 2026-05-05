# E-commerce Multi-Table Schema Example

This example demonstrates a comprehensive e-commerce application using multiple DynamoDB tables with complex access patterns and cross-table relationships.

## Architecture Overview

The schema is designed around three main tables:
- **UserTable**: Manages user profiles and addresses
- **ProductTable**: Handles products, categories, and reviews
- **OrderTable**: Manages orders, order items, and user order history

## Tables and Entities

### UserTable
- **User**: Core user profile information
- **UserAddress**: Multiple addresses per user (shipping, billing, etc.)

### ProductTable
- **Product**: Product catalog with inventory management
- **ProductCategory**: Category-based product indexing for browsing
- **ProductReview**: Customer reviews with ratings and comments

### OrderTable
- **Order**: Order details with shipping and payment information
- **OrderItem**: Individual items within orders
- **UserOrderHistory**: User's order history sorted by date

## Key Features Demonstrated

### Cross-Table Relationships
- Orders reference Users and Products across tables
- Reviews link Products with Users
- Order history maintains relationships between Users and Orders

### Complex Access Patterns
- **Category browsing**: Query products by category
- **User order history**: Retrieve orders sorted by date
- **Product reviews**: Get all reviews for a product
- **Inventory management**: Update stock quantities

### Advanced DynamoDB Patterns
- **Composite sort keys**: Enable range queries and sorting
- **GSI-ready design**: Sort keys designed for Global Secondary Indexes
- **Denormalization**: Product info duplicated in OrderItems for performance
- **Time-based sorting**: Orders and reviews sorted by timestamp
- **Main table range queries**: Support for date-based filtering (`>=`, `between`) and prefix matching (`begins_with`) on sort keys

## Sample Use Cases

1. **Product Catalog**: Browse products by category, view details and reviews
2. **Shopping Cart**: Add products to cart, create orders with multiple items
3. **Order Management**: Track order status, view order history
4. **User Management**: Manage multiple addresses, update profiles
5. **Inventory Tracking**: Update stock levels, track product availability
6. **Date-Based Queries**: Filter orders by date range, find recent orders
7. **Pagination**: Navigate through products and reviews efficiently

## Range Query Examples

This schema demonstrates main table range queries across multiple tables:

### UserOrderHistory Range Queries
- **`get_user_orders_after_date`**: Uses `>=` to find orders after a specific date
  - Example: Get all orders placed since last month
- **`get_user_orders_in_date_range`**: Uses `between` to find orders within a date range
  - Example: Get orders from Q1 2024 for reporting

### ProductReview Range Queries
- **`get_product_reviews_by_id_prefix`**: Uses `begins_with` to find reviews matching a prefix
  - Example: Find reviews with IDs starting with a specific pattern

### ProductCategory Range Queries
- **`get_category_products_after_id`**: Uses `>` to find products after a specific ID
  - Example: Pagination through category products

These patterns enable efficient date-based filtering, pagination, and time-range queries without requiring additional GSIs.

## Cross-Table Entity References

The schema includes several access patterns that demonstrate cross-table entity references:
- `create_product_review`: References both Product and User entities
- `create_order`: References User entity for order creation
- `add_order_item`: References Product entity when adding items
- `add_order_to_user_history`: References both User and Order entities

This design showcases how to maintain data consistency and relationships across multiple DynamoDB tables while optimizing for common e-commerce query patterns.
