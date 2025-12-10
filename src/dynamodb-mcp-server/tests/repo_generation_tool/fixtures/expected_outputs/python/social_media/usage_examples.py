"""Generated usage examples for DynamoDB entities and repositories"""

from __future__ import annotations

import os
import sys
import time

# Import generated entities and repositories
from entities import Comment, Follow, Like, Post, UserProfile
from repositories import (
    CommentRepository,
    FollowRepository,
    LikeRepository,
    PostRepository,
    UserProfileRepository,
)


class UsageExamples:
    """Examples of using the generated entities and repositories"""

    def __init__(self):
        """Initialize repositories with default table names from schema."""
        # Initialize repositories with their respective table names
        # SocialMedia table repositories
        self.comment_repo = CommentRepository('SocialMedia')
        self.follow_repo = FollowRepository('SocialMedia')
        self.like_repo = LikeRepository('SocialMedia')
        self.post_repo = PostRepository('SocialMedia')
        self.userprofile_repo = UserProfileRepository('SocialMedia')

    def run_examples(self, include_additional_access_patterns: bool = False):
        """Run CRUD examples for all entities"""
        # Dictionary to store created entities for access pattern testing
        created_entities = {}

        print('Running Repository Examples')
        print('=' * 50)
        print('\n=== SocialMedia Table Operations ===')

        # Comment example
        print('\n--- Comment ---')

        # 1. CREATE - Create sample comment
        sample_comment = Comment(
            user_id='user_id123',
            post_id='post_id123',
            comment_id='comment_id123',
            username='sample_username',
            content='sample_content',
            timestamp=int(time.time()),
        )

        print('📝 Creating comment...')
        print(f'📝 PK: {sample_comment.pk()}, SK: {sample_comment.sk()}')

        created_comment = self.comment_repo.create_comment(sample_comment)
        print(f'✅ Created: {created_comment}')

        # Store created entity for access pattern testing
        created_entities['Comment'] = created_comment
        # 2. UPDATE - Update non-key field (username)
        print('\n🔄 Updating username field...')
        original_value = created_comment.username
        created_comment.username = 'username_updated'

        updated_comment = self.comment_repo.update_comment(created_comment)
        print(f'✅ Updated username: {original_value} → {updated_comment.username}')

        # Update stored entity with updated values
        created_entities['Comment'] = updated_comment

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving comment...')
        retrieved_comment = self.comment_repo.get_comment(
            created_comment.user_id, created_comment.post_id, created_comment.comment_id
        )

        if retrieved_comment:
            print(f'✅ Retrieved: {retrieved_comment}')
        else:
            print('❌ Failed to retrieve comment')

        print('🎯 Comment CRUD cycle completed successfully!')

        # Follow example
        print('\n--- Follow ---')

        # 1. CREATE - Create sample follow
        sample_follow = Follow(
            user_id='user_id123',
            follower_id='follower_id123',
            username='sample_username',
            timestamp=int(time.time()),
        )

        print('📝 Creating follow...')
        print(f'📝 PK: {sample_follow.pk()}, SK: {sample_follow.sk()}')

        created_follow = self.follow_repo.create_follow(sample_follow)
        print(f'✅ Created: {created_follow}')

        # Store created entity for access pattern testing
        created_entities['Follow'] = created_follow
        # 2. UPDATE - Update non-key field (username)
        print('\n🔄 Updating username field...')
        original_value = created_follow.username
        created_follow.username = 'username_updated'

        updated_follow = self.follow_repo.update_follow(created_follow)
        print(f'✅ Updated username: {original_value} → {updated_follow.username}')

        # Update stored entity with updated values
        created_entities['Follow'] = updated_follow

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving follow...')
        retrieved_follow = self.follow_repo.get_follow(
            created_follow.user_id, created_follow.follower_id
        )

        if retrieved_follow:
            print(f'✅ Retrieved: {retrieved_follow}')
        else:
            print('❌ Failed to retrieve follow')

        print('🎯 Follow CRUD cycle completed successfully!')

        # Like example
        print('\n--- Like ---')

        # 1. CREATE - Create sample like
        sample_like = Like(
            user_id='user_id123',
            post_id='post_id123',
            liker_user_id='liker_user_id123',
            username='sample_username',
            timestamp=int(time.time()),
        )

        print('📝 Creating like...')
        print(f'📝 PK: {sample_like.pk()}, SK: {sample_like.sk()}')

        created_like = self.like_repo.create_like(sample_like)
        print(f'✅ Created: {created_like}')

        # Store created entity for access pattern testing
        created_entities['Like'] = created_like
        # 2. UPDATE - Update non-key field (username)
        print('\n🔄 Updating username field...')
        original_value = created_like.username
        created_like.username = 'username_updated'

        updated_like = self.like_repo.update_like(created_like)
        print(f'✅ Updated username: {original_value} → {updated_like.username}')

        # Update stored entity with updated values
        created_entities['Like'] = updated_like

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving like...')
        retrieved_like = self.like_repo.get_like(
            created_like.user_id, created_like.post_id, created_like.liker_user_id
        )

        if retrieved_like:
            print(f'✅ Retrieved: {retrieved_like}')
        else:
            print('❌ Failed to retrieve like')

        print('🎯 Like CRUD cycle completed successfully!')

        # Post example
        print('\n--- Post ---')

        # 1. CREATE - Create sample post
        sample_post = Post(
            user_id='user_id123',
            post_id='post_id123',
            username='sample_username',
            content='sample_content',
            media_urls=['sample1', 'sample2'],
            timestamp=int(time.time()),
        )

        print('📝 Creating post...')
        print(f'📝 PK: {sample_post.pk()}, SK: {sample_post.sk()}')

        created_post = self.post_repo.create_post(sample_post)
        print(f'✅ Created: {created_post}')

        # Store created entity for access pattern testing
        created_entities['Post'] = created_post
        # 2. UPDATE - Update non-key field (username)
        print('\n🔄 Updating username field...')
        original_value = created_post.username
        created_post.username = 'username_updated'

        updated_post = self.post_repo.update_post(created_post)
        print(f'✅ Updated username: {original_value} → {updated_post.username}')

        # Update stored entity with updated values
        created_entities['Post'] = updated_post

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving post...')
        retrieved_post = self.post_repo.get_post(created_post.user_id, created_post.post_id)

        if retrieved_post:
            print(f'✅ Retrieved: {retrieved_post}')
        else:
            print('❌ Failed to retrieve post')

        print('🎯 Post CRUD cycle completed successfully!')

        # UserProfile example
        print('\n--- UserProfile ---')

        # 1. CREATE - Create sample userprofile
        sample_userprofile = UserProfile(
            user_id='user_id123',
            username='sample_username',
            email='sample_email',
            timestamp=int(time.time()),
        )

        print('📝 Creating userprofile...')
        print(f'📝 PK: {sample_userprofile.pk()}, SK: {sample_userprofile.sk()}')

        created_userprofile = self.userprofile_repo.create_user_profile(sample_userprofile)
        print(f'✅ Created: {created_userprofile}')

        # Store created entity for access pattern testing
        created_entities['UserProfile'] = created_userprofile
        # 2. UPDATE - Update non-key field (username)
        print('\n🔄 Updating username field...')
        original_value = created_userprofile.username
        created_userprofile.username = 'username_updated'

        updated_userprofile = self.userprofile_repo.update_user_profile(created_userprofile)
        print(f'✅ Updated username: {original_value} → {updated_userprofile.username}')

        # Update stored entity with updated values
        created_entities['UserProfile'] = updated_userprofile

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving userprofile...')
        retrieved_userprofile = self.userprofile_repo.get_user_profile(created_userprofile.user_id)

        if retrieved_userprofile:
            print(f'✅ Retrieved: {retrieved_userprofile}')
        else:
            print('❌ Failed to retrieve userprofile')

        print('🎯 UserProfile CRUD cycle completed successfully!')

        print('\n' + '=' * 50)
        print('🎉 Basic CRUD examples completed successfully!')

        # Additional Access Pattern Testing Section (before cleanup)
        if include_additional_access_patterns:
            self._test_additional_access_patterns(created_entities)

        # Cleanup - Delete all created entities
        print('\n' + '=' * 50)
        print('🗑️  Cleanup: Deleting all created entities')
        print('=' * 50)

        # Delete Comment
        if 'Comment' in created_entities:
            print('\n🗑️  Deleting comment...')
            deleted = self.comment_repo.delete_comment(
                created_entities['Comment'].user_id,
                created_entities['Comment'].post_id,
                created_entities['Comment'].comment_id,
            )

            if deleted:
                print('✅ Deleted comment successfully')
            else:
                print('❌ Failed to delete comment')

        # Delete Follow
        if 'Follow' in created_entities:
            print('\n🗑️  Deleting follow...')
            deleted = self.follow_repo.delete_follow(
                created_entities['Follow'].user_id, created_entities['Follow'].follower_id
            )

            if deleted:
                print('✅ Deleted follow successfully')
            else:
                print('❌ Failed to delete follow')

        # Delete Like
        if 'Like' in created_entities:
            print('\n🗑️  Deleting like...')
            deleted = self.like_repo.delete_like(
                created_entities['Like'].user_id,
                created_entities['Like'].post_id,
                created_entities['Like'].liker_user_id,
            )

            if deleted:
                print('✅ Deleted like successfully')
            else:
                print('❌ Failed to delete like')

        # Delete Post
        if 'Post' in created_entities:
            print('\n🗑️  Deleting post...')
            deleted = self.post_repo.delete_post(
                created_entities['Post'].user_id, created_entities['Post'].post_id
            )

            if deleted:
                print('✅ Deleted post successfully')
            else:
                print('❌ Failed to delete post')

        # Delete UserProfile
        if 'UserProfile' in created_entities:
            print('\n🗑️  Deleting userprofile...')
            deleted = self.userprofile_repo.delete_user_profile(
                created_entities['UserProfile'].user_id
            )

            if deleted:
                print('✅ Deleted userprofile successfully')
            else:
                print('❌ Failed to delete userprofile')

        print('\n💡 Requirements:')
        print("   - DynamoDB table 'SocialMedia' must exist")
        print('   - DynamoDB permissions: GetItem, PutItem, UpdateItem, DeleteItem')

    def _test_additional_access_patterns(self, created_entities: dict):
        """Test additional access patterns beyond basic CRUD (commented out by default for manual implementation)"""
        print('\n' + '=' * 60)
        print('🔍 Additional Access Pattern Testing (Commented Out)')
        print('=' * 60)
        print('💡 Uncomment the lines below after implementing the additional access patterns')
        print()

        # Comment
        # Access Pattern #5: Get comments for a specific post
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #5: Get comments for a specific post")
        #     print("   Using Main Table")
        #     user_id = created_entities["Comment"].user_id
        #     post_id = created_entities["Comment"].post_id
        #     self.comment_repo.get_post_comments(
        #         user_id,
        #         post_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #5: {e}")

        # Access Pattern #9: Add comment to post
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #9: Add comment to post")
        #     print("   Using Main Table")
        #     comment = created_entities["Comment"]
        #     self.comment_repo.add_comment(
        #         comment,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #9: {e}")

        # Access Pattern #16: Get comments for a post within comment_id range (Main Table Range Query)
        # Index: Main Table
        # Range Condition: between
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #16: Get comments for a post within comment_id range (Main Table Range Query)")
        #     print("   Using Main Table")
        #     print("   Range Condition: between")
        #     user_id = created_entities["Comment"].user_id
        #     start_comment_prefix = ""
        #     end_comment_prefix = ""
        #     self.comment_repo.get_comments_for_post_range(
        #         user_id,
        #         start_comment_prefix,
        #         end_comment_prefix,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #16: {e}")

        # Follow
        # Access Pattern #10: Follow a user
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #10: Follow a user")
        #     print("   Using Main Table")
        #     follow = created_entities["Follow"]
        #     self.follow_repo.follow_user(
        #         follow,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #10: {e}")

        # Access Pattern #11: Unfollow a user
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #11: Unfollow a user")
        #     print("   Using Main Table")
        #     user_id = created_entities["Follow"].user_id
        #     follower_id = created_entities["Follow"].follower_id
        #     self.follow_repo.unfollow_user(
        #         user_id,
        #         follower_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #11: {e}")

        # Access Pattern #13: Get user's followers list
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #13: Get user's followers list")
        #     print("   Using Main Table")
        #     target_user_id = ""
        #     self.follow_repo.get_user_followers(
        #         target_user_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #13: {e}")

        # Access Pattern #14: Get user's following list
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #14: Get user's following list")
        #     print("   Using Main Table")
        #     user_id = created_entities["Follow"].user_id
        #     self.follow_repo.get_user_following(
        #         user_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #14: {e}")

        # Like
        # Access Pattern #7: Like a post
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #7: Like a post")
        #     print("   Using Main Table")
        #     like = created_entities["Like"]
        #     self.like_repo.like_post(
        #         like,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #7: {e}")

        # Access Pattern #8: Unlike a post
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #8: Unlike a post")
        #     print("   Using Main Table")
        #     user_id = created_entities["Like"].user_id
        #     post_id = created_entities["Like"].post_id
        #     liker_user_id = created_entities["Like"].liker_user_id
        #     self.like_repo.unlike_post(
        #         user_id,
        #         post_id,
        #         liker_user_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #8: {e}")

        # Access Pattern #12: Get list of users who liked a specific post
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #12: Get list of users who liked a specific post")
        #     print("   Using Main Table")
        #     user_id = created_entities["Like"].user_id
        #     post_id = created_entities["Like"].post_id
        #     self.like_repo.get_post_likes(
        #         user_id,
        #         post_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #12: {e}")

        # Access Pattern #17: Get likes for a post after a specific prefix (Main Table Range Query)
        # Index: Main Table
        # Range Condition: >
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #17: Get likes for a post after a specific prefix (Main Table Range Query)")
        #     print("   Using Main Table")
        #     print("   Range Condition: >")
        #     user_id = created_entities["Like"].user_id
        #     like_prefix = ""
        #     self.like_repo.get_likes_after_prefix(
        #         user_id,
        #         like_prefix,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #17: {e}")

        # Post
        # Access Pattern #2: Create new post
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #2: Create new post")
        #     print("   Using Main Table")
        #     post = created_entities["Post"]
        #     self.post_repo.create_post(
        #         post,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #2: {e}")

        # Access Pattern #3: Delete post
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #3: Delete post")
        #     print("   Using Main Table")
        #     user_id = created_entities["Post"].user_id
        #     post_id = created_entities["Post"].post_id
        #     self.post_repo.delete_post(
        #         user_id,
        #         post_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #3: {e}")

        # Access Pattern #4: Get personalized feed - posts from followed users
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #4: Get personalized feed - posts from followed users")
        #     print("   Using Main Table")
        #     user_id = created_entities["Post"].user_id
        #     self.post_repo.get_user_posts(
        #         user_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #4: {e}")

        # Access Pattern #15: Get user posts by post_id prefix (Main Table Range Query)
        # Index: Main Table
        # Range Condition: begins_with
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #15: Get user posts by post_id prefix (Main Table Range Query)")
        #     print("   Using Main Table")
        #     print("   Range Condition: begins_with")
        #     user_id = created_entities["Post"].user_id
        #     post_id_prefix = ""
        #     self.post_repo.get_user_posts_by_prefix(
        #         user_id,
        #         post_id_prefix,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #15: {e}")

        # UserProfile
        # Access Pattern #1: User login/authentication - get user profile by user_id
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #1: User login/authentication - get user profile by user_id")
        #     print("   Using Main Table")
        #     user_id = created_entities["UserProfile"].user_id
        #     self.userprofile_repo.get_user_profile(
        #         user_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #1: {e}")

        # Access Pattern #6: View user profile and posts
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #6: View user profile and posts")
        #     print("   Using Main Table")
        #     user_id = created_entities["UserProfile"].user_id
        #     self.userprofile_repo.get_user_profile_and_posts(
        #         user_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #6: {e}")

        print('\n💡 Access Pattern Implementation Notes:')
        print('   - Main Table queries use partition key and sort key')
        print('   - GSI queries use different key structures and may have range conditions')
        print(
            '   - Range conditions (begins_with, between, >, <, >=, <=) require additional parameters'
        )
        print('   - Implement the access pattern methods in your repository classes')


def main():
    """Main function to run examples"""
    # Parse command line arguments
    include_additional_access_patterns = '--all' in sys.argv

    # Check if we're running against DynamoDB Local
    endpoint_url = os.getenv('AWS_ENDPOINT_URL_DYNAMODB')
    if endpoint_url:
        print(f'🔗 Using DynamoDB endpoint: {endpoint_url}')
        print(f'🌍 Using region: {os.getenv("AWS_DEFAULT_REGION", "us-east-1")}')
    else:
        print('🌐 Using AWS DynamoDB (no local endpoint specified)')

    print('📊 Using multiple tables:')
    print('   - SocialMedia')

    if include_additional_access_patterns:
        print('🔍 Including additional access pattern examples (commented out)')

    examples = UsageExamples()
    examples.run_examples(include_additional_access_patterns=include_additional_access_patterns)


if __name__ == '__main__':
    main()
