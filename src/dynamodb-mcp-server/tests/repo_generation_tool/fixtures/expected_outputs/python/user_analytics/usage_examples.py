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
        self.user_repo = UserRepository('UserAnalytics')

    def run_examples(self, include_additional_access_patterns: bool = False):
        """Run CRUD examples for all entities"""
        # Dictionary to store created entities for access pattern testing
        created_entities = {}

        print('Running Repository Examples')
        print('=' * 50)
        print('\n=== UserAnalytics Table Operations ===')

        # User example
        print('\n--- User ---')

        # 1. CREATE - Create sample user
        sample_user = User(
            user_id='user_id123',
            email='sample_email',
            status='active',
            last_active='sample_last_active',
            country='US',
            city='Seattle',
            signup_date='sample_signup_date',
            engagement_level='sample_engagement_level',
            session_count=42,
            age_group='sample_age_group',
            total_sessions=42,
            last_purchase_date='sample_last_purchase_date',
        )

        print('📝 Creating user...')
        print(f'📝 PK: {sample_user.pk()}, SK: {sample_user.sk()}')

        created_user = self.user_repo.create_user(sample_user)
        print(f'✅ Created: {created_user}')

        # Store created entity for access pattern testing
        created_entities['User'] = created_user
        # 2. UPDATE - Update non-key field (email)
        print('\n🔄 Updating email field...')
        original_value = created_user.email
        created_user.email = 'updated_email'

        updated_user = self.user_repo.update_user(created_user)
        print(f'✅ Updated email: {original_value} → {updated_user.email}')

        # Update stored entity with updated values
        created_entities['User'] = updated_user

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving user...')
        retrieved_user = self.user_repo.get_user(created_user.user_id)

        if retrieved_user:
            print(f'✅ Retrieved: {retrieved_user}')
        else:
            print('❌ Failed to retrieve user')

        print('🎯 User CRUD cycle completed successfully!')

        print('\n' + '=' * 50)
        print('🎉 Basic CRUD examples completed successfully!')

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
            deleted = self.user_repo.delete_user(created_entities['User'].user_id)

            if deleted:
                print('✅ Deleted user successfully')
            else:
                print('❌ Failed to delete user')

        print('\n💡 Requirements:')
        print("   - DynamoDB table 'UserAnalytics' must exist")
        print('   - DynamoDB permissions: GetItem, PutItem, UpdateItem, DeleteItem')

    def _test_additional_access_patterns(self, created_entities: dict):
        """Test additional access patterns beyond basic CRUD (commented out by default for manual implementation)"""
        print('\n' + '=' * 60)
        print('🔍 Additional Access Pattern Testing (Commented Out)')
        print('=' * 60)
        print('💡 Uncomment the lines below after implementing the additional access patterns')
        print()

        # User
        # Access Pattern #1: Get user profile by ID
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #1: Get user profile by ID")
        #     print("   Using Main Table")
        #     user_id = created_entities["User"].user_id
        #     self.user_repo.get_user(
        #         user_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #1: {e}")

        # Access Pattern #2: Get users by status
        # GSI: StatusIndex
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #2: Get users by status")
        #     print("   Using GSI: StatusIndex")
        #     status = created_entities["User"].status
        #     self.user_repo.get_active_users(
        #         status,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #2: {e}")

        # Access Pattern #3: Get recently active users by status
        # GSI: StatusIndex
        # Range Condition: >=
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #3: Get recently active users by status")
        #     print("   Using GSI: StatusIndex")
        #     print("   Range Condition: >=")
        #     status = created_entities["User"].status
        #     since_date = ""
        #     self.user_repo.get_recent_active_users(
        #         status,
        #         since_date,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #3: {e}")

        # Access Pattern #4: Get users by country and city
        # GSI: LocationIndex
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #4: Get users by country and city")
        #     print("   Using GSI: LocationIndex")
        #     country = created_entities["User"].country
        #     city = created_entities["User"].city
        #     self.user_repo.get_users_by_location(
        #         country,
        #         city,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #4: {e}")

        # Access Pattern #5: Get users by country with city prefix
        # GSI: LocationIndex
        # Range Condition: begins_with
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #5: Get users by country with city prefix")
        #     print("   Using GSI: LocationIndex")
        #     print("   Range Condition: begins_with")
        #     country = created_entities["User"].country
        #     city_prefix = ""
        #     self.user_repo.get_users_by_country_prefix(
        #         country,
        #         city_prefix,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #5: {e}")

        # Access Pattern #6: Get users by engagement level
        # GSI: EngagementIndex
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #6: Get users by engagement level")
        #     print("   Using GSI: EngagementIndex")
        #     engagement_level = created_entities["User"].engagement_level
        #     self.user_repo.get_users_by_engagement_level(
        #         engagement_level,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #6: {e}")

        # Access Pattern #7: Get highly engaged users within session count range
        # GSI: EngagementIndex
        # Range Condition: between
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #7: Get highly engaged users within session count range")
        #     print("   Using GSI: EngagementIndex")
        #     print("   Range Condition: between")
        #     engagement_level = created_entities["User"].engagement_level
        #     min_sessions = ""
        #     max_sessions = ""
        #     self.user_repo.get_highly_engaged_users_by_session_range(
        #         engagement_level,
        #         min_sessions,
        #         max_sessions,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #7: {e}")

        # Access Pattern #8: Get users by age group
        # GSI: AgeGroupIndex
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #8: Get users by age group")
        #     print("   Using GSI: AgeGroupIndex")
        #     age_group = created_entities["User"].age_group
        #     self.user_repo.get_users_by_age_group(
        #         age_group,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #8: {e}")

        # Access Pattern #9: Get users who signed up after a specific date in age group
        # GSI: AgeGroupIndex
        # Range Condition: >=
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #9: Get users who signed up after a specific date in age group")
        #     print("   Using GSI: AgeGroupIndex")
        #     print("   Range Condition: >=")
        #     age_group = created_entities["User"].age_group
        #     since_date = ""
        #     self.user_repo.get_recent_signups_by_age_group(
        #         age_group,
        #         since_date,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #9: {e}")

        # Access Pattern #10: Get users who signed up within date range for age group
        # GSI: AgeGroupIndex
        # Range Condition: between
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #10: Get users who signed up within date range for age group")
        #     print("   Using GSI: AgeGroupIndex")
        #     print("   Range Condition: between")
        #     age_group = created_entities["User"].age_group
        #     start_date = ""
        #     end_date = ""
        #     self.user_repo.get_users_signup_date_range(
        #         age_group,
        #         start_date,
        #         end_date,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #10: {e}")

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
    print('   - UserAnalytics')

    if include_additional_access_patterns:
        print('🔍 Including additional access pattern examples (commented out)')

    examples = UsageExamples()
    examples.run_examples(include_additional_access_patterns=include_additional_access_patterns)


if __name__ == '__main__':
    main()
