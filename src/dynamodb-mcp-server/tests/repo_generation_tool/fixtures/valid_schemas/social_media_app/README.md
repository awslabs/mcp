# Social Media Single Table Design Example

This example demonstrates a comprehensive social media application using DynamoDB's **single table design** pattern with user-centric data organization and hierarchical access patterns.

## Architecture Overview

The schema is designed around a single DynamoDB table representing the social media ecosystem:

- **SocialMedia**: Manages all user profiles, posts, comments, likes, and follow relationships in one table

## Tables and Entities

### SocialMedia Table

- **UserProfile**: Core user profile information and authentication
- **Post**: User posts with content and media attachments
- **Comment**: Comments on posts with hierarchical organization
- **Like**: Post likes with user attribution and engagement tracking
- **Follow**: User following relationships for social connections

## Key Features Demonstrated

### Single Table Design Benefits

- **Cost efficiency**: One table reduces operational costs
- **Data co-location**: Related user data stored together for performance
- **Atomic transactions**: All user operations can be atomic
- **Simplified infrastructure**: Single table to manage and monitor

### Hierarchical Access Patterns

- **User-centric partitioning**: All data partitioned by user_id
- **Composite sort keys**: Enable range queries and natural sorting
- **Prefix matching**: Query related items by sort key prefixes
- **Timeline queries**: Efficient retrieval of user activity chronologically

### Complex Access Patterns

- **User authentication**: Get user profile by ID
- **Content creation**: Create posts, comments, and likes
- **Social interactions**: Follow/unfollow users, like/unlike posts
- **Feed generation**: Retrieve user posts and combined profile data
- **Engagement tracking**: Get post likes and comments

### Advanced DynamoDB Patterns

- **Hierarchical sort keys**: `POST#{post_id}`, `COMMENT#{post_id}#{comment_id}`
- **Strategic denormalization**: Username duplicated across entities for performance
- **Range query optimization**: Sort keys designed for efficient prefix queries
- **User activity aggregation**: All user data accessible in single query
- **Main table range queries**: Support for `begins_with`, `between`, and comparison operators on sort keys

## Sample Use Cases

1. **User Authentication**: Login and profile retrieval
2. **Content Publishing**: Create posts with media attachments
3. **Social Engagement**: Like posts, add comments, follow users
4. **User Timeline**: View user's posts and activity chronologically
5. **Feed Generation**: Combined profile and posts view
6. **Social Discovery**: Find followers and following relationships
7. **Range Queries**: Filter posts by prefix, comments by range, likes after a specific point

## Range Query Examples

This schema demonstrates main table range queries on sort keys:

### Post Range Queries
- **`get_user_posts_by_prefix`**: Uses `begins_with` to find posts matching a prefix pattern
  - Example: Find all posts with IDs starting with "2024-01"

### Comment Range Queries
- **`get_comments_for_post_range`**: Uses `between` to find comments within a range
  - Example: Get comments between specific comment IDs for pagination

### Like Range Queries
- **`get_likes_after_prefix`**: Uses `>` to find likes after a specific point
  - Example: Get likes added after a certain timestamp or user

These patterns enable efficient filtering and pagination without requiring additional GSIs.

## Cross-Table Entity References

The schema uses entity references within access patterns:

- `create_post`: References Post entity for content creation
- `add_comment`: References Comment entity for post interactions
- `like_post`: References Like entity for engagement tracking
- `follow_user`: References Follow entity for social connections

## Single Table Design Considerations

This design demonstrates key single table patterns:

- **User-centric partitioning**: All user data co-located by user_id
- **Hierarchical organization**: Sort keys create logical data hierarchy
- **Efficient range queries**: Prefix patterns enable flexible querying
- **Strategic denormalization**: Username duplication for query performance
- **Atomic operations**: Related items can be updated together
- **Natural sorting**: Timestamp-based ordering built into keys

This schema showcases how to build a scalable social media application using DynamoDB's single table design pattern while maintaining efficient query patterns and supporting complex social interactions within a unified data model.
