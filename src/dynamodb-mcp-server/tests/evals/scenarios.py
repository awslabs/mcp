"""Test scenario definitions for DynamoDB data modeling evaluation."""

from typing import Any, Dict, List, Literal


BASIC_SCENARIOS = [
    {
        'name': 'Simple E-commerce Schema',
        'description': 'Basic e-commerce application with users, products, and orders',
        'user_input': 'I need to design a DynamoDB schema for an e-commerce application. I have users who can place orders for products. Each order can contain multiple products. I expect around 1000 users and 100 orders per day.',
        'complexity': 'beginner',
        'application_details': {
            'type': 'E-commerce platform',
            'domain': 'Online retail',
            'primary_function': 'Enable users to browse products, place orders, and manage their purchase history',
            'business_model': 'B2C retail with product catalog and order management',
        },
        'entities_and_relationships': {
            'entities': {
                'Users': 'Customer accounts with profile information, shipping addresses, and authentication data',
                'Products': 'Items available for purchase with details, pricing, inventory levels, and categories',
                'Orders': 'Purchase transactions containing order metadata, user information, and timestamps',
                'OrderItems': 'Individual line items within orders linking products with quantities and prices',
            },
            'relationships': [
                'Users → Orders (1:many) - Each user can place multiple orders over time',
                'Orders → OrderItems (1:many) - Each order contains one or more product line items',
                'Products → OrderItems (1:many) - Each product can appear in multiple different orders',
            ],
        },
        'access_patterns': {
            'read_patterns': [
                'Get user profile by user ID (very frequent)',
                "List user's order history(Last 6 Month) with pagination (frequent)",
                'Get complete order details with all items (frequent)',
                'Browse products by category with filtering (very frequent)',
                'Search products by name or keywords (frequent)',
                'Get individual product details and availability (very frequent)',
                'Check inventory levels for products (moderate)',
            ],
            'write_patterns': [
                'Create new user account during registration (moderate)',
                'Update user profile and shipping addresses (infrequent)',
                'Place new order with multiple items (frequent)',
                'Update order status during fulfillment (moderate)',
                'Update product inventory after purchases (frequent)',
                'Add new products to catalog (infrequent)',
                'Update product details and pricing (infrequent)',
            ],
        },
        'performance_and_scale': {
            'user_base': '1000 active users',
            'transaction_volume': '100 orders per day (~3000 per month)',
            'data_growth': '50 new products added monthly, growing product catalog',
            'read_write_ratio': '80% read, 20% write (typical e-commerce browsing pattern)',
            'performance_requirements': [
                'Product browsing and search: <5ms DynamoDB response time',
                'Order placement and checkout: <8ms DynamoDB response time',
                'User dashboard and order history: <3ms DynamoDB response time',
                'Inventory lookups: <2ms DynamoDB response time',
            ],
            'scalability_needs': 'Moderate growth expected, standard e-commerce traffic patterns with seasonal peaks',
            'regional_requirements': 'Single region deployment initially, potential multi-region expansion later',
        },
        'expected_elements': [
            'multi-table design',
            'access patterns',
            'primary key design',
            'relationships between entities',
            'basic cost considerations',
        ],
        'key_concepts_should_include': [
            'Users table',
            'Orders table',
            'Products table',
            'One-to-many relationships',
            'Query patterns',
        ],
    },
    {
        'name': 'High-Scale Social Media Platform',
        'description': 'Social media platform with posts, likes, comments at high scale',
        'user_input': "I'm building a social media platform where users can create posts, like posts, and comment on posts. I expect 100k+ users with some viral posts getting 10k+ interactions per minute. I need to handle both read-heavy and write-heavy patterns efficiently.",
        'complexity': 'advanced',
        'application_details': {
            'type': 'Social Media Platform',
            'domain': 'Social networking and content sharing',
            'primary_function': 'Enable users to create, share, and interact with posts through likes and comments',
            'business_model': 'Ad-supported social platform with viral content distribution',
        },
        'entities_and_relationships': {
            'entities': {
                'Users': 'User accounts with profiles, follower counts, and authentication data',
                'Posts': 'Content items with text, media, timestamps, and engagement metrics',
                'Likes': 'User engagement records linking users to posts with timestamps',
                'Comments': 'User-generated responses to posts with threading and moderation',
            },
            'relationships': [
                'Users → Posts (1:many) - Each user can create multiple posts',
                'Users → Likes (1:many) - Each user can like multiple posts',
                'Users → Comments (1:many) - Each user can comment on multiple posts',
                'Posts → Likes (1:many) - Each post can receive multiple likes',
                'Posts → Comments (1:many) - Each post can have multiple comments',
            ],
        },
        'access_patterns': {
            'read_patterns': [
                'Get user profile and follower count (frequent)',
                'Load user timeline/feed with recent posts (very frequent)',
                'Get post details with like/comment counts (very frequent)',
                'List comments for a post with pagination (frequent)',
                'Check if user liked a specific post (frequent)',
                'Get trending/viral posts by engagement metrics (moderate)',
                'Search posts by hashtags or keywords (moderate)',
            ],
            'write_patterns': [
                'Create new user account (moderate)',
                'Publish new post (frequent)',
                'Like/unlike posts (very frequent - up to 10k/minute for viral posts)',
                'Add comments to posts (frequent)',
                'Update user profile information (infrequent)',
                'Delete posts or comments (infrequent)',
                'Follow/unfollow other users (moderate)',
            ],
        },
        'performance_and_scale': {
            'user_base': '100k+ active users with high engagement',
            'transaction_volume': '10k+ interactions per minute for viral posts',
            'data_growth': 'Thousands of posts, millions of likes/comments daily',
            'read_write_ratio': '70% read, 30% write (high interaction platform)',
            'performance_requirements': [
                'Feed loading: <3ms DynamoDB response time',
                'Like/comment actions: <5ms DynamoDB response time',
                'Post publishing: <8ms DynamoDB response time',
                'Viral post handling: Must scale to 10k+ writes/minute',
            ],
            'scalability_needs': 'Extreme scalability required for viral content, hot partition mitigation essential',
            'regional_requirements': 'Global deployment with multi-region replication for performance',
        },
        'expected_elements': [
            'hot partition analysis',
            'write sharding strategies',
            'cost optimization',
            'performance considerations',
            'scaling strategies',
        ],
        'key_concepts_should_include': [
            'Hot partition mitigation',
            'Write sharding',
            'GSI design for scale',
            'Cost optimization',
            'Performance tuning',
        ],
    },
    {
        'name': 'Content Management System',
        'description': 'Blog/CMS with articles, authors, categories, and comments',
        'user_input': "I'm building a content management system for a blog. I have authors who write articles, articles belong to categories, and users can comment on articles. I need to display recent articles, articles by category, and author profiles. Expected traffic is 5000 page views per day with 50 new articles per month.",
        'complexity': 'beginner',
        'application_details': {
            'type': 'Content Management System',
            'domain': 'Digital publishing and blogging',
            'primary_function': 'Enable authors to publish articles, organize content by categories, and facilitate user engagement through comments',
            'business_model': 'Content-driven platform with potential ad revenue and subscription tiers',
        },
        'entities_and_relationships': {
            'entities': {
                'Authors': 'Content creators with profiles, bio information, and publishing permissions',
                'Articles': 'Published content with metadata, body text, publication dates, and SEO information',
                'Categories': 'Content organization tags with hierarchical structure and descriptions',
                'Comments': 'User-generated responses to articles with moderation status and threading',
            },
            'relationships': [
                'Authors → Articles (1:many) - Each author can write multiple articles',
                'Categories → Articles (many:many) - Articles can belong to multiple categories',
                'Articles → Comments (1:many) - Each article can have multiple comments',
                'Authors → Comments (1:many) - Authors can respond with comments',
            ],
        },
        'access_patterns': {
            'read_patterns': [
                'Display recent articles on homepage with pagination (very frequent)',
                'Get article details with author info and comments (very frequent)',
                'List articles by specific category (frequent)',
                'Show author profile with their published articles (moderate)',
                'Search articles by keywords or tags (moderate)',
                'Load comments for article with threading (frequent)',
                'Get popular/trending articles by view count (moderate)',
            ],
            'write_patterns': [
                'Publish new articles (moderate - 50/month)',
                'Update existing articles and drafts (moderate)',
                'Add new categories and organize content (infrequent)',
                'Submit user comments on articles (moderate)',
                'Moderate and approve comments (moderate)',
                'Update author profiles and bio information (infrequent)',
                'Track article view counts and analytics (frequent)',
            ],
        },
        'performance_and_scale': {
            'user_base': '5000+ daily readers, 20 active authors, moderate engagement',
            'transaction_volume': '5000 page views per day, ~50 new articles monthly',
            'data_growth': 'Steady content growth, accumulating article archive over time',
            'read_write_ratio': '85% read, 15% write (typical content consumption pattern)',
            'performance_requirements': [
                'Homepage loading: <3ms DynamoDB response time',
                'Article page display: <5ms DynamoDB response time',
                'Category browsing: <8ms DynamoDB response time',
                'Comment loading: <5ms DynamoDB response time',
            ],
            'scalability_needs': 'Moderate growth expected, seasonal traffic spikes during popular content releases',
            'regional_requirements': 'Single region sufficient, potential CDN integration for global readers',
        },
        'expected_elements': [
            'content modeling',
            'categorization strategy',
            'query patterns for content',
            'many-to-many relationships',
            'basic indexing needs',
        ],
        'key_concepts_should_include': [
            'Articles table',
            'Authors table',
            'Categories relationship',
            'GSI for filtering',
            'Query vs Scan patterns',
        ],
    },
]


def get_scenario_by_complexity(
    complexity: Literal['beginner', 'intermediate', 'advanced'],
) -> List[Dict[str, Any]]:
    """Get scenarios filtered by complexity level."""
    return [s for s in BASIC_SCENARIOS if s['complexity'] == complexity]


def get_scenario_by_name(name: str) -> Dict[str, Any]:
    """Get a specific scenario by name."""
    for scenario in BASIC_SCENARIOS:
        if scenario['name'] == name:
            return scenario
    raise ValueError(f"Scenario '{name}' not found")
