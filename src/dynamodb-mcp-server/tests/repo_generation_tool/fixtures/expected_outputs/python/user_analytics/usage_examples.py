"""Generated usage examples for DynamoDB entities and repositories"""

from __future__ import annotations

import os
import sys

# Import generated entities and repositories
from entities import User
from repositories import UserRepository


class UsageExamples:
    """Examples of using the generated entities and repositories"""

    def __init__(self):
        """Initialize repositories with default table names from schema."""
        # Initialize repositories with their respective table names
        # UserAnalytics table repositories
        try:
            self.user_repo = UserRepository('UserAnalytics')
            print("✅ Initialized UserRepository for table 'UserAnalytics'")
        except Exception as e:
            print(f'❌ Failed to initialize UserRepository: {e}')
            self.user_repo = None

    def run_examples(self, include_additional_access_patterns: bool = False):
        """Run CRUD examples for all entities"""
        # Dictionary to store created entities for access pattern testing
        created_entities = {}

        # Step 0: Cleanup any leftover entities from previous runs (makes tests idempotent)
        print('🧹 Pre-test Cleanup: Removing any leftover entities from previous runs')
        print('=' * 50)
        # Try to delete User (user_id)
        try:
            sample_user = User(
                user_id='user-12345',
                email='user@example.com',
                status='active',
                last_active='2024-01-20T14:30:00Z',
                country='US',
                city='Seattle',
                signup_date='2024-01-15T10:00:00Z',
                engagement_level='high',
                session_count=25,
                age_group='25-34',
                total_sessions=150,
                last_purchase_date='2024-01-18T12:00:00Z',
            )
            self.user_repo.delete_user(sample_user.user_id)
            print('   🗑️  Deleted leftover user (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        print('✅ Pre-test cleanup completed\n')

        print('Running Repository Examples')
        print('=' * 50)
        print('\n=== UserAnalytics Table Operations ===')

        # User example
        print('\n--- User ---')

        # 1. CREATE - Create sample user
        sample_user = User(
            user_id='user-12345',
            email='user@example.com',
            status='active',
            last_active='2024-01-20T14:30:00Z',
            country='US',
            city='Seattle',
            signup_date='2024-01-15T10:00:00Z',
            engagement_level='high',
            session_count=25,
            age_group='25-34',
            total_sessions=150,
            last_purchase_date='2024-01-18T12:00:00Z',
        )

        print('📝 Creating user...')
        print(f'📝 PK: {sample_user.pk()}, SK: {sample_user.sk()}')

        try:
            created_user = self.user_repo.create_user(sample_user)
            print(f'✅ Created: {created_user}')
            # Store created entity for access pattern testing
            created_entities['User'] = created_user
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  user already exists, retrieving existing entity...')
                try:
                    existing_user = self.user_repo.get_user(sample_user.user_id)

                    if existing_user:
                        print(f'✅ Retrieved existing: {existing_user}')
                        # Store existing entity for access pattern testing
                        created_entities['User'] = existing_user
                    else:
                        print('❌ Failed to retrieve existing user')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing user: {get_error}')
            else:
                print(f'❌ Failed to create user: {e}')
        # 2. UPDATE - Update non-key field (status)
        if 'User' in created_entities:
            print('\n🔄 Updating status field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['User']
                refreshed_entity = self.user_repo.get_user(entity_for_refresh.user_id)

                if refreshed_entity:
                    original_value = refreshed_entity.status
                    refreshed_entity.status = 'premium_active'

                    updated_user = self.user_repo.update_user(refreshed_entity)
                    print(f'✅ Updated status: {original_value} → {updated_user.status}')

                    # Update stored entity with updated values
                    created_entities['User'] = updated_user
                else:
                    print('❌ Could not refresh user for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(f'⚠️  user was modified by another process (optimistic locking): {e}')
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update user: {e}')

        # 3. GET - Retrieve and print the entity
        if 'User' in created_entities:
            print('\n🔍 Retrieving user...')
            try:
                entity_for_get = created_entities['User']
                retrieved_user = self.user_repo.get_user(entity_for_get.user_id)

                if retrieved_user:
                    print(f'✅ Retrieved: {retrieved_user}')
                else:
                    print('❌ Failed to retrieve user')
            except Exception as e:
                print(f'❌ Failed to retrieve user: {e}')

        print('🎯 User CRUD cycle completed!')

        print('\n' + '=' * 50)
        print('🎉 Basic CRUD examples completed!')

        # Additional Access Pattern Testing Section (before cleanup)
        if include_additional_access_patterns:
            self._test_additional_access_patterns(created_entities)

        # Cleanup - Delete all created entities
        print('\n' + '=' * 50)
        print('🗑️  Cleanup: Deleting all created entities')
        print('=' * 50)

        # Delete User
        if 'User' in created_entities:
            print('\n🗑️  Deleting user...')
            try:
                deleted = self.user_repo.delete_user(created_entities['User'].user_id)

                if deleted:
                    print('✅ Deleted user successfully')
                else:
                    print('❌ Failed to delete user (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete user: {e}')
        print('\n💡 Requirements:')
        print("   - DynamoDB table 'UserAnalytics' must exist")
        print('   - DynamoDB permissions: GetItem, PutItem, UpdateItem, DeleteItem')

    def _test_additional_access_patterns(self, created_entities: dict):
        """Test additional access patterns beyond basic CRUD"""
        print('\n' + '=' * 60)
        print('🔍 Additional Access Pattern Testing')
        print('=' * 60)
        print()

        # User
        # Access Pattern #1: Get user profile by ID
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #1: Get user profile by ID')
            print('   Using Main Table')
            result = self.user_repo.get_user(created_entities['User'].user_id)
            print('   ✅ Get user profile by ID completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #1: {e}')

        # Access Pattern #2: Get users by status
        # GSI: StatusIndex
        try:
            print('🔍 Testing Access Pattern #2: Get users by status')
            print('   Using GSI: StatusIndex')
            result = self.user_repo.get_active_users(created_entities['User'].status)
            print('   ✅ Get users by status completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #2: {e}')

        # Access Pattern #3: Get recently active users by status
        # GSI: StatusIndex
        # Range Condition: >=
        try:
            print('🔍 Testing Access Pattern #3: Get recently active users by status')
            print('   Using GSI: StatusIndex')
            print('   Range Condition: >=')
            result = self.user_repo.get_recent_active_users(
                created_entities['User'].status, '2024-01-01'
            )
            print('   ✅ Get recently active users by status completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #3: {e}')

        # Access Pattern #4: Get users by country and city
        # GSI: LocationIndex
        try:
            print('🔍 Testing Access Pattern #4: Get users by country and city')
            print('   Using GSI: LocationIndex')
            result = self.user_repo.get_users_by_location(
                created_entities['User'].country, created_entities['User'].city
            )
            print('   ✅ Get users by country and city completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #4: {e}')

        # Access Pattern #5: Get users by country with city prefix
        # GSI: LocationIndex
        # Range Condition: begins_with
        try:
            print('🔍 Testing Access Pattern #5: Get users by country with city prefix')
            print('   Using GSI: LocationIndex')
            print('   Range Condition: begins_with')
            result = self.user_repo.get_users_by_country_prefix(
                created_entities['User'].country, 'city_prefix_value'
            )
            print('   ✅ Get users by country with city prefix completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #5: {e}')

        # Access Pattern #6: Get users by engagement level
        # GSI: EngagementIndex
        try:
            print('🔍 Testing Access Pattern #6: Get users by engagement level')
            print('   Using GSI: EngagementIndex')
            result = self.user_repo.get_users_by_engagement_level(
                created_entities['User'].engagement_level
            )
            print('   ✅ Get users by engagement level completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #6: {e}')

        # Access Pattern #7: Get highly engaged users within session count range
        # GSI: EngagementIndex
        # Range Condition: between
        try:
            print(
                '🔍 Testing Access Pattern #7: Get highly engaged users within session count range'
            )
            print('   Using GSI: EngagementIndex')
            print('   Range Condition: between')
            result = self.user_repo.get_highly_engaged_users_by_session_range(
                created_entities['User'].engagement_level, 0, 9999
            )
            print('   ✅ Get highly engaged users within session count range completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #7: {e}')

        # Access Pattern #8: Get users by age group
        # GSI: AgeGroupIndex
        try:
            print('🔍 Testing Access Pattern #8: Get users by age group')
            print('   Using GSI: AgeGroupIndex')
            result = self.user_repo.get_users_by_age_group(created_entities['User'].age_group)
            print('   ✅ Get users by age group completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #8: {e}')

        # Access Pattern #9: Get users who signed up after a specific date in age group
        # GSI: AgeGroupIndex
        # Range Condition: >=
        try:
            print(
                '🔍 Testing Access Pattern #9: Get users who signed up after a specific date in age group'
            )
            print('   Using GSI: AgeGroupIndex')
            print('   Range Condition: >=')
            result = self.user_repo.get_recent_signups_by_age_group(
                created_entities['User'].age_group, '2024-01-01'
            )
            print('   ✅ Get users who signed up after a specific date in age group completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #9: {e}')

        # Access Pattern #10: Get users who signed up within date range for age group
        # GSI: AgeGroupIndex
        # Range Condition: between
        try:
            print(
                '🔍 Testing Access Pattern #10: Get users who signed up within date range for age group'
            )
            print('   Using GSI: AgeGroupIndex')
            print('   Range Condition: between')
            result = self.user_repo.get_users_signup_date_range(
                created_entities['User'].age_group, '2024-01-01', '2024-12-31'
            )
            print('   ✅ Get users who signed up within date range for age group completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #10: {e}')

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
    print('   - UserAnalytics')

    if include_additional_access_patterns:
        print('🔍 Including additional access pattern examples')

    examples = UsageExamples()
    examples.run_examples(include_additional_access_patterns=include_additional_access_patterns)


if __name__ == '__main__':
    main()
