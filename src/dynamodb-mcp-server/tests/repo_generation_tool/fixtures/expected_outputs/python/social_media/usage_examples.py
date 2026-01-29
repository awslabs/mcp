"""Generated usage examples for DynamoDB entities and repositories"""

from __future__ import annotations

import os
import sys

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
        try:
            self.comment_repo = CommentRepository('SocialMedia')
            print("✅ Initialized CommentRepository for table 'SocialMedia'")
        except Exception as e:
            print(f'❌ Failed to initialize CommentRepository: {e}')
            self.comment_repo = None
        try:
            self.follow_repo = FollowRepository('SocialMedia')
            print("✅ Initialized FollowRepository for table 'SocialMedia'")
        except Exception as e:
            print(f'❌ Failed to initialize FollowRepository: {e}')
            self.follow_repo = None
        try:
            self.like_repo = LikeRepository('SocialMedia')
            print("✅ Initialized LikeRepository for table 'SocialMedia'")
        except Exception as e:
            print(f'❌ Failed to initialize LikeRepository: {e}')
            self.like_repo = None
        try:
            self.post_repo = PostRepository('SocialMedia')
            print("✅ Initialized PostRepository for table 'SocialMedia'")
        except Exception as e:
            print(f'❌ Failed to initialize PostRepository: {e}')
            self.post_repo = None
        try:
            self.userprofile_repo = UserProfileRepository('SocialMedia')
            print("✅ Initialized UserProfileRepository for table 'SocialMedia'")
        except Exception as e:
            print(f'❌ Failed to initialize UserProfileRepository: {e}')
            self.userprofile_repo = None

    def run_examples(self, include_additional_access_patterns: bool = False):
        """Run CRUD examples for all entities"""
        # Dictionary to store created entities for access pattern testing
        created_entities = {}

        # Step 0: Cleanup any leftover entities from previous runs (makes tests idempotent)
        print('🧹 Pre-test Cleanup: Removing any leftover entities from previous runs')
        print('=' * 50)
        # Try to delete Comment (user_id, post_id, comment_id)
        try:
            sample_comment = Comment(
                user_id='user-12345',
                post_id='post-67890',
                comment_id='comment-11111',
                username='techexplorer',
                content='Great post! Thanks for sharing this insightful content.',
                timestamp=1705751400,
            )
            self.comment_repo.delete_comment(
                sample_comment.user_id, sample_comment.post_id, sample_comment.comment_id
            )
            print('   🗑️  Deleted leftover comment (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete Follow (user_id, follower_id)
        try:
            sample_follow = Follow(
                user_id='user-12345',
                follower_id='user-67890',
                username='techexplorer',
                timestamp=1705579200,
            )
            self.follow_repo.delete_follow(sample_follow.user_id, sample_follow.follower_id)
            print('   🗑️  Deleted leftover follow (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete Like (user_id, post_id, liker_user_id)
        try:
            sample_like = Like(
                user_id='user-12345',
                post_id='post-67890',
                liker_user_id='user-67890',
                username='follower_user',
                timestamp=1705748700,
            )
            self.like_repo.delete_like(
                sample_like.user_id, sample_like.post_id, sample_like.liker_user_id
            )
            print('   🗑️  Deleted leftover like (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete Post (user_id, post_id)
        try:
            sample_post = Post(
                user_id='user-12345',
                post_id='post-67890',
                username='techexplorer',
                content='Just finished reading an amazing book about technology trends. Highly recommend it to anyone interested in the future of AI!',
                media_urls=['https://example.com/images/book-cover.jpg'],
                timestamp=1705741200,
            )
            self.post_repo.delete_post(sample_post.user_id, sample_post.post_id)
            print('   🗑️  Deleted leftover post (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete UserProfile (user_id)
        try:
            sample_userprofile = UserProfile(
                user_id='user-12345',
                username='techexplorer',
                email='techexplorer@example.com',
                timestamp=1704067200,
            )
            self.userprofile_repo.delete_user_profile(sample_userprofile.user_id)
            print('   🗑️  Deleted leftover userprofile (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        print('✅ Pre-test cleanup completed\n')

        print('Running Repository Examples')
        print('=' * 50)
        print('\n=== SocialMedia Table Operations ===')

        # Comment example
        print('\n--- Comment ---')

        # 1. CREATE - Create sample comment
        sample_comment = Comment(
            user_id='user-12345',
            post_id='post-67890',
            comment_id='comment-11111',
            username='techexplorer',
            content='Great post! Thanks for sharing this insightful content.',
            timestamp=1705751400,
        )

        print('📝 Creating comment...')
        print(f'📝 PK: {sample_comment.pk()}, SK: {sample_comment.sk()}')

        try:
            created_comment = self.comment_repo.create_comment(sample_comment)
            print(f'✅ Created: {created_comment}')
            # Store created entity for access pattern testing
            created_entities['Comment'] = created_comment
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  comment already exists, retrieving existing entity...')
                try:
                    existing_comment = self.comment_repo.get_comment(
                        sample_comment.user_id, sample_comment.post_id, sample_comment.comment_id
                    )

                    if existing_comment:
                        print(f'✅ Retrieved existing: {existing_comment}')
                        # Store existing entity for access pattern testing
                        created_entities['Comment'] = existing_comment
                    else:
                        print('❌ Failed to retrieve existing comment')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing comment: {get_error}')
            else:
                print(f'❌ Failed to create comment: {e}')
        # 2. UPDATE - Update non-key field (content)
        if 'Comment' in created_entities:
            print('\n🔄 Updating content field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['Comment']
                refreshed_entity = self.comment_repo.get_comment(
                    entity_for_refresh.user_id,
                    entity_for_refresh.post_id,
                    entity_for_refresh.comment_id,
                )

                if refreshed_entity:
                    original_value = refreshed_entity.content
                    refreshed_entity.content = 'Great post! Thanks for sharing this very insightful content. Really helpful!'

                    updated_comment = self.comment_repo.update_comment(refreshed_entity)
                    print(f'✅ Updated content: {original_value} → {updated_comment.content}')

                    # Update stored entity with updated values
                    created_entities['Comment'] = updated_comment
                else:
                    print('❌ Could not refresh comment for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(f'⚠️  comment was modified by another process (optimistic locking): {e}')
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update comment: {e}')

        # 3. GET - Retrieve and print the entity
        if 'Comment' in created_entities:
            print('\n🔍 Retrieving comment...')
            try:
                entity_for_get = created_entities['Comment']
                retrieved_comment = self.comment_repo.get_comment(
                    entity_for_get.user_id, entity_for_get.post_id, entity_for_get.comment_id
                )

                if retrieved_comment:
                    print(f'✅ Retrieved: {retrieved_comment}')
                else:
                    print('❌ Failed to retrieve comment')
            except Exception as e:
                print(f'❌ Failed to retrieve comment: {e}')

        print('🎯 Comment CRUD cycle completed!')

        # Follow example
        print('\n--- Follow ---')

        # 1. CREATE - Create sample follow
        sample_follow = Follow(
            user_id='user-12345',
            follower_id='user-67890',
            username='techexplorer',
            timestamp=1705579200,
        )

        print('📝 Creating follow...')
        print(f'📝 PK: {sample_follow.pk()}, SK: {sample_follow.sk()}')

        try:
            created_follow = self.follow_repo.create_follow(sample_follow)
            print(f'✅ Created: {created_follow}')
            # Store created entity for access pattern testing
            created_entities['Follow'] = created_follow
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  follow already exists, retrieving existing entity...')
                try:
                    existing_follow = self.follow_repo.get_follow(
                        sample_follow.user_id, sample_follow.follower_id
                    )

                    if existing_follow:
                        print(f'✅ Retrieved existing: {existing_follow}')
                        # Store existing entity for access pattern testing
                        created_entities['Follow'] = existing_follow
                    else:
                        print('❌ Failed to retrieve existing follow')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing follow: {get_error}')
            else:
                print(f'❌ Failed to create follow: {e}')
        # 2. UPDATE - Update non-key field (timestamp)
        if 'Follow' in created_entities:
            print('\n🔄 Updating timestamp field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['Follow']
                refreshed_entity = self.follow_repo.get_follow(
                    entity_for_refresh.user_id, entity_for_refresh.follower_id
                )

                if refreshed_entity:
                    original_value = refreshed_entity.timestamp
                    refreshed_entity.timestamp = 1705665600

                    updated_follow = self.follow_repo.update_follow(refreshed_entity)
                    print(f'✅ Updated timestamp: {original_value} → {updated_follow.timestamp}')

                    # Update stored entity with updated values
                    created_entities['Follow'] = updated_follow
                else:
                    print('❌ Could not refresh follow for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(f'⚠️  follow was modified by another process (optimistic locking): {e}')
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update follow: {e}')

        # 3. GET - Retrieve and print the entity
        if 'Follow' in created_entities:
            print('\n🔍 Retrieving follow...')
            try:
                entity_for_get = created_entities['Follow']
                retrieved_follow = self.follow_repo.get_follow(
                    entity_for_get.user_id, entity_for_get.follower_id
                )

                if retrieved_follow:
                    print(f'✅ Retrieved: {retrieved_follow}')
                else:
                    print('❌ Failed to retrieve follow')
            except Exception as e:
                print(f'❌ Failed to retrieve follow: {e}')

        print('🎯 Follow CRUD cycle completed!')

        # Like example
        print('\n--- Like ---')

        # 1. CREATE - Create sample like
        sample_like = Like(
            user_id='user-12345',
            post_id='post-67890',
            liker_user_id='user-67890',
            username='follower_user',
            timestamp=1705748700,
        )

        print('📝 Creating like...')
        print(f'📝 PK: {sample_like.pk()}, SK: {sample_like.sk()}')

        try:
            created_like = self.like_repo.create_like(sample_like)
            print(f'✅ Created: {created_like}')
            # Store created entity for access pattern testing
            created_entities['Like'] = created_like
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  like already exists, retrieving existing entity...')
                try:
                    existing_like = self.like_repo.get_like(
                        sample_like.user_id, sample_like.post_id, sample_like.liker_user_id
                    )

                    if existing_like:
                        print(f'✅ Retrieved existing: {existing_like}')
                        # Store existing entity for access pattern testing
                        created_entities['Like'] = existing_like
                    else:
                        print('❌ Failed to retrieve existing like')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing like: {get_error}')
            else:
                print(f'❌ Failed to create like: {e}')
        # 2. UPDATE - Update non-key field (timestamp)
        if 'Like' in created_entities:
            print('\n🔄 Updating timestamp field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['Like']
                refreshed_entity = self.like_repo.get_like(
                    entity_for_refresh.user_id,
                    entity_for_refresh.post_id,
                    entity_for_refresh.liker_user_id,
                )

                if refreshed_entity:
                    original_value = refreshed_entity.timestamp
                    refreshed_entity.timestamp = 1705835100

                    updated_like = self.like_repo.update_like(refreshed_entity)
                    print(f'✅ Updated timestamp: {original_value} → {updated_like.timestamp}')

                    # Update stored entity with updated values
                    created_entities['Like'] = updated_like
                else:
                    print('❌ Could not refresh like for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(f'⚠️  like was modified by another process (optimistic locking): {e}')
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update like: {e}')

        # 3. GET - Retrieve and print the entity
        if 'Like' in created_entities:
            print('\n🔍 Retrieving like...')
            try:
                entity_for_get = created_entities['Like']
                retrieved_like = self.like_repo.get_like(
                    entity_for_get.user_id, entity_for_get.post_id, entity_for_get.liker_user_id
                )

                if retrieved_like:
                    print(f'✅ Retrieved: {retrieved_like}')
                else:
                    print('❌ Failed to retrieve like')
            except Exception as e:
                print(f'❌ Failed to retrieve like: {e}')

        print('🎯 Like CRUD cycle completed!')

        # Post example
        print('\n--- Post ---')

        # 1. CREATE - Create sample post
        sample_post = Post(
            user_id='user-12345',
            post_id='post-67890',
            username='techexplorer',
            content='Just finished reading an amazing book about technology trends. Highly recommend it to anyone interested in the future of AI!',
            media_urls=['https://example.com/images/book-cover.jpg'],
            timestamp=1705741200,
        )

        print('📝 Creating post...')
        print(f'📝 PK: {sample_post.pk()}, SK: {sample_post.sk()}')

        try:
            created_post = self.post_repo.create_post(sample_post)
            print(f'✅ Created: {created_post}')
            # Store created entity for access pattern testing
            created_entities['Post'] = created_post
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  post already exists, retrieving existing entity...')
                try:
                    existing_post = self.post_repo.get_post(
                        sample_post.user_id, sample_post.post_id
                    )

                    if existing_post:
                        print(f'✅ Retrieved existing: {existing_post}')
                        # Store existing entity for access pattern testing
                        created_entities['Post'] = existing_post
                    else:
                        print('❌ Failed to retrieve existing post')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing post: {get_error}')
            else:
                print(f'❌ Failed to create post: {e}')
        # 2. UPDATE - Update non-key field (content)
        if 'Post' in created_entities:
            print('\n🔄 Updating content field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['Post']
                refreshed_entity = self.post_repo.get_post(
                    entity_for_refresh.user_id, entity_for_refresh.post_id
                )

                if refreshed_entity:
                    original_value = refreshed_entity.content
                    refreshed_entity.content = 'Just finished reading an amazing book about technology trends. Highly recommend it to anyone interested in the future of AI and machine learning!'

                    updated_post = self.post_repo.update_post(refreshed_entity)
                    print(f'✅ Updated content: {original_value} → {updated_post.content}')

                    # Update stored entity with updated values
                    created_entities['Post'] = updated_post
                else:
                    print('❌ Could not refresh post for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(f'⚠️  post was modified by another process (optimistic locking): {e}')
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update post: {e}')

        # 3. GET - Retrieve and print the entity
        if 'Post' in created_entities:
            print('\n🔍 Retrieving post...')
            try:
                entity_for_get = created_entities['Post']
                retrieved_post = self.post_repo.get_post(
                    entity_for_get.user_id, entity_for_get.post_id
                )

                if retrieved_post:
                    print(f'✅ Retrieved: {retrieved_post}')
                else:
                    print('❌ Failed to retrieve post')
            except Exception as e:
                print(f'❌ Failed to retrieve post: {e}')

        print('🎯 Post CRUD cycle completed!')

        # UserProfile example
        print('\n--- UserProfile ---')

        # 1. CREATE - Create sample userprofile
        sample_userprofile = UserProfile(
            user_id='user-12345',
            username='techexplorer',
            email='techexplorer@example.com',
            timestamp=1704067200,
        )

        print('📝 Creating userprofile...')
        print(f'📝 PK: {sample_userprofile.pk()}, SK: {sample_userprofile.sk()}')

        try:
            created_userprofile = self.userprofile_repo.create_user_profile(sample_userprofile)
            print(f'✅ Created: {created_userprofile}')
            # Store created entity for access pattern testing
            created_entities['UserProfile'] = created_userprofile
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  userprofile already exists, retrieving existing entity...')
                try:
                    existing_userprofile = self.userprofile_repo.get_user_profile(
                        sample_userprofile.user_id
                    )

                    if existing_userprofile:
                        print(f'✅ Retrieved existing: {existing_userprofile}')
                        # Store existing entity for access pattern testing
                        created_entities['UserProfile'] = existing_userprofile
                    else:
                        print('❌ Failed to retrieve existing userprofile')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing userprofile: {get_error}')
            else:
                print(f'❌ Failed to create userprofile: {e}')
        # 2. UPDATE - Update non-key field (username)
        if 'UserProfile' in created_entities:
            print('\n🔄 Updating username field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['UserProfile']
                refreshed_entity = self.userprofile_repo.get_user_profile(
                    entity_for_refresh.user_id
                )

                if refreshed_entity:
                    original_value = refreshed_entity.username
                    refreshed_entity.username = 'techexplorer_ai'

                    updated_userprofile = self.userprofile_repo.update_user_profile(
                        refreshed_entity
                    )
                    print(
                        f'✅ Updated username: {original_value} → {updated_userprofile.username}'
                    )

                    # Update stored entity with updated values
                    created_entities['UserProfile'] = updated_userprofile
                else:
                    print('❌ Could not refresh userprofile for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  userprofile was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update userprofile: {e}')

        # 3. GET - Retrieve and print the entity
        if 'UserProfile' in created_entities:
            print('\n🔍 Retrieving userprofile...')
            try:
                entity_for_get = created_entities['UserProfile']
                retrieved_userprofile = self.userprofile_repo.get_user_profile(
                    entity_for_get.user_id
                )

                if retrieved_userprofile:
                    print(f'✅ Retrieved: {retrieved_userprofile}')
                else:
                    print('❌ Failed to retrieve userprofile')
            except Exception as e:
                print(f'❌ Failed to retrieve userprofile: {e}')

        print('🎯 UserProfile CRUD cycle completed!')

        print('\n' + '=' * 50)
        print('🎉 Basic CRUD examples completed!')

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
            try:
                deleted = self.comment_repo.delete_comment(
                    created_entities['Comment'].user_id,
                    created_entities['Comment'].post_id,
                    created_entities['Comment'].comment_id,
                )

                if deleted:
                    print('✅ Deleted comment successfully')
                else:
                    print('❌ Failed to delete comment (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete comment: {e}')

        # Delete Follow
        if 'Follow' in created_entities:
            print('\n🗑️  Deleting follow...')
            try:
                deleted = self.follow_repo.delete_follow(
                    created_entities['Follow'].user_id, created_entities['Follow'].follower_id
                )

                if deleted:
                    print('✅ Deleted follow successfully')
                else:
                    print('❌ Failed to delete follow (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete follow: {e}')

        # Delete Like
        if 'Like' in created_entities:
            print('\n🗑️  Deleting like...')
            try:
                deleted = self.like_repo.delete_like(
                    created_entities['Like'].user_id,
                    created_entities['Like'].post_id,
                    created_entities['Like'].liker_user_id,
                )

                if deleted:
                    print('✅ Deleted like successfully')
                else:
                    print('❌ Failed to delete like (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete like: {e}')

        # Delete Post
        if 'Post' in created_entities:
            print('\n🗑️  Deleting post...')
            try:
                deleted = self.post_repo.delete_post(
                    created_entities['Post'].user_id, created_entities['Post'].post_id
                )

                if deleted:
                    print('✅ Deleted post successfully')
                else:
                    print('❌ Failed to delete post (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete post: {e}')

        # Delete UserProfile
        if 'UserProfile' in created_entities:
            print('\n🗑️  Deleting userprofile...')
            try:
                deleted = self.userprofile_repo.delete_user_profile(
                    created_entities['UserProfile'].user_id
                )

                if deleted:
                    print('✅ Deleted userprofile successfully')
                else:
                    print('❌ Failed to delete userprofile (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete userprofile: {e}')
        print('\n💡 Requirements:')
        print("   - DynamoDB table 'SocialMedia' must exist")
        print('   - DynamoDB permissions: GetItem, PutItem, UpdateItem, DeleteItem')

    def _test_additional_access_patterns(self, created_entities: dict):
        """Test additional access patterns beyond basic CRUD"""
        print('\n' + '=' * 60)
        print('🔍 Additional Access Pattern Testing')
        print('=' * 60)
        print()

        # Comment
        # Access Pattern #5: Get comments for a specific post
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #5: Get comments for a specific post')
            print('   Using Main Table')
            result = self.comment_repo.get_post_comments(
                created_entities['Comment'].user_id, created_entities['Comment'].post_id
            )
            print('   ✅ Get comments for a specific post completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #5: {e}')

        # Access Pattern #9: Add comment to post
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #9: Add comment to post')
            print('   Using Main Table')
            test_entity = Comment(
                user_id='user-98765',
                post_id='post-54321',
                comment_id='comment-99999',
                username='data_scientist',
                content='This is exactly what I was looking for. Thanks for the detailed explanation!',
                timestamp=1705664000,
            )
            result = self.comment_repo.add_comment(test_entity)
            print('   ✅ Add comment to post completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #9: {e}')

        # Access Pattern #16: Get comments for a post within comment_id range (Main Table Range Query)
        # Index: Main Table
        # Range Condition: between
        try:
            print(
                '🔍 Testing Access Pattern #16: Get comments for a post within comment_id range (Main Table Range Query)'
            )
            print('   Using Main Table')
            print('   Range Condition: between')
            result = self.comment_repo.get_comments_for_post_range(
                created_entities['Comment'].user_id, '2024-01-01', '2024-12-31'
            )
            print(
                '   ✅ Get comments for a post within comment_id range (Main Table Range Query) completed'
            )
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #16: {e}')

        # Follow
        # Access Pattern #10: Follow a user
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #10: Follow a user')
            print('   Using Main Table')
            test_entity = Follow(
                user_id='user-11111',
                follower_id='user-22222',
                username='ai_researcher',
                timestamp=1705492800,
            )
            result = self.follow_repo.follow_user(test_entity)
            print('   ✅ Follow a user completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #10: {e}')

        # Access Pattern #11: Unfollow a user
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #11: Unfollow a user')
            print('   Using Main Table')
            result = self.follow_repo.unfollow_user(
                created_entities['Follow'].user_id, created_entities['Follow'].follower_id
            )
            print('   ✅ Unfollow a user completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #11: {e}')

        # Access Pattern #13: Get user's followers list
        # Index: Main Table
        try:
            print("🔍 Testing Access Pattern #13: Get user's followers list")
            print('   Using Main Table')
            result = self.follow_repo.get_user_followers('target_user_id_value')
            print("   ✅ Get user's followers list completed")
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #13: {e}')

        # Access Pattern #14: Get user's following list
        # Index: Main Table
        try:
            print("🔍 Testing Access Pattern #14: Get user's following list")
            print('   Using Main Table')
            result = self.follow_repo.get_user_following(created_entities['Follow'].user_id)
            print("   ✅ Get user's following list completed")
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #14: {e}')

        # Like
        # Access Pattern #7: Like a post
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #7: Like a post')
            print('   Using Main Table')
            test_entity = Like(
                user_id='user-33333',
                post_id='post-44444',
                liker_user_id='user-55555',
                username='ml_engineer',
                timestamp=1705406400,
            )
            result = self.like_repo.like_post(test_entity)
            print('   ✅ Like a post completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #7: {e}')

        # Access Pattern #8: Unlike a post
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #8: Unlike a post')
            print('   Using Main Table')
            result = self.like_repo.unlike_post(
                created_entities['Like'].user_id,
                created_entities['Like'].post_id,
                created_entities['Like'].liker_user_id,
            )
            print('   ✅ Unlike a post completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #8: {e}')

        # Access Pattern #12: Get list of users who liked a specific post
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #12: Get list of users who liked a specific post')
            print('   Using Main Table')
            result = self.like_repo.get_post_likes(
                created_entities['Like'].user_id, created_entities['Like'].post_id
            )
            print('   ✅ Get list of users who liked a specific post completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #12: {e}')

        # Access Pattern #17: Get likes for a post after a specific prefix (Main Table Range Query)
        # Index: Main Table
        # Range Condition: >
        try:
            print(
                '🔍 Testing Access Pattern #17: Get likes for a post after a specific prefix (Main Table Range Query)'
            )
            print('   Using Main Table')
            print('   Range Condition: >')
            result = self.like_repo.get_likes_after_prefix(
                created_entities['Like'].user_id, 'like_prefix_value'
            )
            print(
                '   ✅ Get likes for a post after a specific prefix (Main Table Range Query) completed'
            )
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #17: {e}')

        # Post
        # Access Pattern #2: Create new post
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #2: Create new post')
            print('   Using Main Table')
            test_entity = Post(
                user_id='user-77777',
                post_id='post-88888',
                username='startup_founder',
                content="Excited to share our latest product update! We've integrated advanced analytics that will help businesses make better data-driven decisions.",
                media_urls=[
                    'https://example.com/images/product-screenshot.png',
                    'https://example.com/videos/demo.mp4',
                ],
                timestamp=1705320000,
            )
            result = self.post_repo.put_post(test_entity)
            print('   ✅ Create new post completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #2: {e}')

        # Access Pattern #3: Delete post
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #3: Delete post')
            print('   Using Main Table')
            result = self.post_repo.delete_post(
                created_entities['Post'].user_id, created_entities['Post'].post_id
            )
            print('   ✅ Delete post completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #3: {e}')

        # Access Pattern #4: Get personalized feed - posts from followed users
        # Index: Main Table
        try:
            print(
                '🔍 Testing Access Pattern #4: Get personalized feed - posts from followed users'
            )
            print('   Using Main Table')
            result = self.post_repo.get_user_posts(created_entities['Post'].user_id)
            print('   ✅ Get personalized feed - posts from followed users completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #4: {e}')

        # Access Pattern #15: Get user posts by post_id prefix (Main Table Range Query)
        # Index: Main Table
        # Range Condition: begins_with
        try:
            print(
                '🔍 Testing Access Pattern #15: Get user posts by post_id prefix (Main Table Range Query)'
            )
            print('   Using Main Table')
            print('   Range Condition: begins_with')
            result = self.post_repo.get_user_posts_by_prefix(
                created_entities['Post'].user_id, 'post_id_prefix_value'
            )
            print('   ✅ Get user posts by post_id prefix (Main Table Range Query) completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #15: {e}')

        # UserProfile
        # Access Pattern #1: User login/authentication - get user profile by user_id
        # Index: Main Table
        try:
            print(
                '🔍 Testing Access Pattern #1: User login/authentication - get user profile by user_id'
            )
            print('   Using Main Table')
            result = self.userprofile_repo.get_user_profile(
                created_entities['UserProfile'].user_id
            )
            print('   ✅ User login/authentication - get user profile by user_id completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #1: {e}')

        # Access Pattern #6: View user profile and posts
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #6: View user profile and posts')
            print('   Using Main Table')
            result = self.userprofile_repo.get_user_profile_and_posts(
                created_entities['UserProfile'].user_id
            )
            print('   ✅ View user profile and posts completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #6: {e}')

        print('\n💡 Access Pattern Implementation Notes:')
        print('   - Main Table queries use partition key and sort key')
        print('   - GSI queries use different key structures and may have range conditions')
        print(
            '   - Range conditions (begins_with, between, >, <, >=, <=) require additional parameters'
        )
        print('   - Implement the access pattern methods in your repository classes')


def main():
    """Main function to run examples"""
    # 🚨 SAFETY CHECK: Prevent accidental execution against production DynamoDB
    endpoint_url = os.getenv('AWS_ENDPOINT_URL_DYNAMODB', '')

    # Check if running against DynamoDB Local
    is_local = 'localhost' in endpoint_url.lower() or '127.0.0.1' in endpoint_url

    if not is_local:
        print('=' * 80)
        print('🚨 SAFETY WARNING: NOT RUNNING AGAINST DYNAMODB LOCAL')
        print('=' * 80)
        print()
        print(f'Current endpoint: {endpoint_url or "AWS DynamoDB (production)"}')
        print()
        print('⚠️  This script performs CREATE, UPDATE, and DELETE operations that could')
        print('   affect your production data!')
        print()
        print('To run against production DynamoDB:')
        print('  1. Review the code carefully to understand what data will be modified')
        print("  2. Search for 'SAFETY CHECK' in this file")
        print("  3. Comment out the 'raise RuntimeError' line below the safety check")
        print('  4. Understand the risks before proceeding')
        print()
        print('To run safely against DynamoDB Local:')
        print('  export AWS_ENDPOINT_URL_DYNAMODB=http://localhost:8000')
        print()
        print('=' * 80)

        # 🛑 SAFETY CHECK: Comment out this line to run against production
        raise RuntimeError(
            'Safety check: Refusing to run against production DynamoDB. See warning above.'
        )

    # Parse command line arguments
    include_additional_access_patterns = '--all' in sys.argv

    # Check if we're running against DynamoDB Local
    if endpoint_url:
        print(f'🔗 Using DynamoDB endpoint: {endpoint_url}')
        print(f'🌍 Using region: {os.getenv("AWS_DEFAULT_REGION", "us-east-1")}')
    else:
        print('🌐 Using AWS DynamoDB (no local endpoint specified)')

    print('📊 Using multiple tables:')
    print('   - SocialMedia')

    if include_additional_access_patterns:
        print('🔍 Including additional access pattern examples')

    examples = UsageExamples()
    examples.run_examples(include_additional_access_patterns=include_additional_access_patterns)


if __name__ == '__main__':
    main()
