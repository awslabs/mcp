# User Analytics GSI Schema

This comprehensive schema demonstrates advanced GSI functionality for user analytics with multiple GSI patterns and range query types.

## Features Demonstrated

- **Multiple GSIs**: Four different GSIs covering various analytics dimensions
- **All Range Conditions**: `>=`, `begins_with`, and `between` range queries
- **Hierarchical Keys**: Country/City hierarchy in LocationIndex
- **Numeric Range Queries**: Session count ranges in EngagementIndex
- **Date Range Queries**: Signup date ranges in AgeGroupIndex
- **Status Tracking**: Time-based status queries
- **Complex Templates**: Multi-parameter templates with prefixes

## GSI Structure

### StatusIndex
- **Purpose**: Query users by activity status and time
- **PK**: `STATUS#{status}` (e.g., "active", "inactive")
- **SK**: `{last_active}` (timestamp for chronological ordering)

### LocationIndex
- **Purpose**: Geographic user queries
- **PK**: `COUNTRY#{country}`
- **SK**: `CITY#{city}` (enables city-level and prefix queries)

### EngagementIndex
- **Purpose**: Query users by engagement level and session activity
- **PK**: `ENGAGEMENT#{engagement_level}` (e.g., "high", "medium", "low")
- **SK**: `{session_count}` (numeric for range queries)

### AgeGroupIndex
- **Purpose**: Demographic analysis with temporal filtering
- **PK**: `AGE_GROUP#{age_group}` (e.g., "18-25", "26-35", "36-50")
- **SK**: `{signup_date}` (date for chronological and range queries)

## Access Patterns

1. **get_user_profile**: Main table GetItem
2. **get_active_users**: StatusIndex simple Query
3. **get_recent_active_users**: StatusIndex range Query with `>=` condition
4. **get_users_by_location**: LocationIndex exact Query
5. **get_users_by_country_prefix**: LocationIndex range Query with `begins_with` condition
6. **get_users_by_engagement_level**: EngagementIndex simple Query
7. **get_highly_engaged_users_by_session_range**: EngagementIndex range Query with `between` condition
8. **get_users_by_age_group**: AgeGroupIndex simple Query
9. **get_recent_signups_by_age_group**: AgeGroupIndex range Query with `>=` condition
10. **get_users_signup_date_range**: AgeGroupIndex range Query with `between` condition
