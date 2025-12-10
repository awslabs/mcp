"""Generated usage examples for DynamoDB entities and repositories"""

from __future__ import annotations

import os
import sys
from decimal import Decimal

# Import generated entities and repositories
from entities import Brand, Deal, User, UserWatch
from repositories import BrandRepository, DealRepository, UserRepository, UserWatchRepository


class UsageExamples:
    """Examples of using the generated entities and repositories"""

    def __init__(self):
        """Initialize repositories with default table names from schema."""
        # Initialize repositories with their respective table names
        # Deals table repositories
        self.deal_repo = DealRepository('Deals')
        # Users table repositories
        self.user_repo = UserRepository('Users')
        # Brands table repositories
        self.brand_repo = BrandRepository('Brands')
        # UserWatches table repositories
        self.userwatch_repo = UserWatchRepository('UserWatches')

    def run_examples(self, include_additional_access_patterns: bool = False):
        """Run CRUD examples for all entities"""
        # Dictionary to store created entities for access pattern testing
        created_entities = {}

        print('Running Repository Examples')
        print('=' * 50)
        print('\n=== Deals Table Operations ===')

        # Deal example
        print('\n--- Deal ---')

        # 1. CREATE - Create sample deal
        sample_deal = Deal(
            deal_id='deal_id123',
            title='sample_title',
            description='sample_description',
            price=Decimal('29.99'),
            brand_id='brand_id123',
            brand_name='sample_brand_name',
            category_id='electronics',
            category_name='electronics',
            created_at='sample_created_at',
            status='active',
        )

        print('📝 Creating deal...')
        print(f'📝 PK: {sample_deal.pk()}, SK: {sample_deal.sk()}')

        created_deal = self.deal_repo.create_deal(sample_deal)
        print(f'✅ Created: {created_deal}')

        # Store created entity for access pattern testing
        created_entities['Deal'] = created_deal
        # 2. UPDATE - Update non-key field (title)
        print('\n🔄 Updating title field...')
        original_value = created_deal.title
        created_deal.title = 'updated_title'

        updated_deal = self.deal_repo.update_deal(created_deal)
        print(f'✅ Updated title: {original_value} → {updated_deal.title}')

        # Update stored entity with updated values
        created_entities['Deal'] = updated_deal

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving deal...')
        retrieved_deal = self.deal_repo.get_deal(created_deal.deal_id)

        if retrieved_deal:
            print(f'✅ Retrieved: {retrieved_deal}')
        else:
            print('❌ Failed to retrieve deal')

        print('🎯 Deal CRUD cycle completed successfully!')
        print('\n=== Users Table Operations ===')

        # User example
        print('\n--- User ---')

        # 1. CREATE - Create sample user
        sample_user = User(
            user_id='user_id123',
            username='sample_username',
            email='sample_email',
            display_name='sample_display_name',
            created_at='sample_created_at',
            last_login='sample_last_login',
        )

        print('📝 Creating user...')
        print(f'📝 PK: {sample_user.pk()}, SK: {sample_user.sk()}')

        created_user = self.user_repo.create_user(sample_user)
        print(f'✅ Created: {created_user}')

        # Store created entity for access pattern testing
        created_entities['User'] = created_user
        # 2. UPDATE - Update non-key field (username)
        print('\n🔄 Updating username field...')
        original_value = created_user.username
        created_user.username = 'username_updated'

        updated_user = self.user_repo.update_user(created_user)
        print(f'✅ Updated username: {original_value} → {updated_user.username}')

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
        print('\n=== Brands Table Operations ===')

        # Brand example
        print('\n--- Brand ---')

        # 1. CREATE - Create sample brand
        sample_brand = Brand(
            brand_id='brand_id123',
            brand_name='sample_brand_name',
            description='sample_description',
            logo_url='sample_logo_url',
            created_at='sample_created_at',
        )

        print('📝 Creating brand...')
        print(f'📝 PK: {sample_brand.pk()}, SK: {sample_brand.sk()}')

        created_brand = self.brand_repo.create_brand(sample_brand)
        print(f'✅ Created: {created_brand}')

        # Store created entity for access pattern testing
        created_entities['Brand'] = created_brand
        # 2. UPDATE - Update non-key field (brand_name)
        print('\n🔄 Updating brand_name field...')
        original_value = created_brand.brand_name
        created_brand.brand_name = 'updated_brand_name'

        updated_brand = self.brand_repo.update_brand(created_brand)
        print(f'✅ Updated brand_name: {original_value} → {updated_brand.brand_name}')

        # Update stored entity with updated values
        created_entities['Brand'] = updated_brand

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving brand...')
        retrieved_brand = self.brand_repo.get_brand(created_brand.brand_id)

        if retrieved_brand:
            print(f'✅ Retrieved: {retrieved_brand}')
        else:
            print('❌ Failed to retrieve brand')

        print('🎯 Brand CRUD cycle completed successfully!')
        print('\n=== UserWatches Table Operations ===')

        # UserWatch example
        print('\n--- UserWatch ---')

        # 1. CREATE - Create sample userwatch
        sample_userwatch = UserWatch(
            user_id='user_id123',
            watch_key='sample_watch_key',
            watch_type='sample_watch_type',
            target_id='target_id123',
            target_name='sample_target_name',
            brand_id='brand_id123',
            category_id='electronics',
            created_at='sample_created_at',
        )

        print('📝 Creating userwatch...')
        print(f'📝 PK: {sample_userwatch.pk()}, SK: {sample_userwatch.sk()}')

        created_userwatch = self.userwatch_repo.create_user_watch(sample_userwatch)
        print(f'✅ Created: {created_userwatch}')

        # Store created entity for access pattern testing
        created_entities['UserWatch'] = created_userwatch
        # 2. UPDATE - Update non-key field (watch_type)
        print('\n🔄 Updating watch_type field...')
        original_value = created_userwatch.watch_type
        created_userwatch.watch_type = 'updated_watch_type'

        updated_userwatch = self.userwatch_repo.update_user_watch(created_userwatch)
        print(f'✅ Updated watch_type: {original_value} → {updated_userwatch.watch_type}')

        # Update stored entity with updated values
        created_entities['UserWatch'] = updated_userwatch

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving userwatch...')
        retrieved_userwatch = self.userwatch_repo.get_user_watch(
            created_userwatch.user_id, created_userwatch.watch_key
        )

        if retrieved_userwatch:
            print(f'✅ Retrieved: {retrieved_userwatch}')
        else:
            print('❌ Failed to retrieve userwatch')

        print('🎯 UserWatch CRUD cycle completed successfully!')

        print('\n' + '=' * 50)
        print('🎉 Basic CRUD examples completed successfully!')

        # Additional Access Pattern Testing Section (before cleanup)
        if include_additional_access_patterns:
            self._test_additional_access_patterns(created_entities)

        # Cleanup - Delete all created entities
        print('\n' + '=' * 50)
        print('🗑️  Cleanup: Deleting all created entities')
        print('=' * 50)

        # Delete Deal
        if 'Deal' in created_entities:
            print('\n🗑️  Deleting deal...')
            deleted = self.deal_repo.delete_deal(created_entities['Deal'].deal_id)

            if deleted:
                print('✅ Deleted deal successfully')
            else:
                print('❌ Failed to delete deal')

        # Delete User
        if 'User' in created_entities:
            print('\n🗑️  Deleting user...')
            deleted = self.user_repo.delete_user(created_entities['User'].user_id)

            if deleted:
                print('✅ Deleted user successfully')
            else:
                print('❌ Failed to delete user')

        # Delete Brand
        if 'Brand' in created_entities:
            print('\n🗑️  Deleting brand...')
            deleted = self.brand_repo.delete_brand(created_entities['Brand'].brand_id)

            if deleted:
                print('✅ Deleted brand successfully')
            else:
                print('❌ Failed to delete brand')

        # Delete UserWatch
        if 'UserWatch' in created_entities:
            print('\n🗑️  Deleting userwatch...')
            deleted = self.userwatch_repo.delete_user_watch(
                created_entities['UserWatch'].user_id, created_entities['UserWatch'].watch_key
            )

            if deleted:
                print('✅ Deleted userwatch successfully')
            else:
                print('❌ Failed to delete userwatch')

        print('\n💡 Requirements:')
        print("   - DynamoDB table 'Deals' must exist")
        print("   - DynamoDB table 'Users' must exist")
        print("   - DynamoDB table 'Brands' must exist")
        print("   - DynamoDB table 'UserWatches' must exist")
        print('   - DynamoDB permissions: GetItem, PutItem, UpdateItem, DeleteItem')

    def _test_additional_access_patterns(self, created_entities: dict):
        """Test additional access patterns beyond basic CRUD (commented out by default for manual implementation)"""
        print('\n' + '=' * 60)
        print('🔍 Additional Access Pattern Testing (Commented Out)')
        print('=' * 60)
        print('💡 Uncomment the lines below after implementing the additional access patterns')
        print()

        # Deal
        # Access Pattern #1: Get deal details by deal_id
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #1: Get deal details by deal_id")
        #     print("   Using Main Table")
        #     deal_id = created_entities["Deal"].deal_id
        #     self.deal_repo.get_deal(
        #         deal_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #1: {e}")

        # Access Pattern #2: Create a new deal
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #2: Create a new deal")
        #     print("   Using Main Table")
        #     deal = created_entities["Deal"]
        #     self.deal_repo.create_deal(
        #         deal,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #2: {e}")

        # Access Pattern #3: Get all deals for a brand sorted by creation date
        # GSI: DealsByBrand
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #3: Get all deals for a brand sorted by creation date")
        #     print("   Using GSI: DealsByBrand")
        #     brand_id = created_entities["Deal"].brand_id
        #     self.deal_repo.get_deals_by_brand(
        #         brand_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #3: {e}")

        # Access Pattern #4: Get all deals for a category sorted by creation date
        # GSI: DealsByCategory
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #4: Get all deals for a category sorted by creation date")
        #     print("   Using GSI: DealsByCategory")
        #     category_id = created_entities["Deal"].category_id
        #     self.deal_repo.get_deals_by_category(
        #         category_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #4: {e}")

        # Access Pattern #5: Get recent deals for a brand after a specific date
        # GSI: DealsByBrand
        # Range Condition: >=
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #5: Get recent deals for a brand after a specific date")
        #     print("   Using GSI: DealsByBrand")
        #     print("   Range Condition: >=")
        #     brand_id = created_entities["Deal"].brand_id
        #     since_date = ""
        #     self.deal_repo.get_recent_deals_by_brand(
        #         brand_id,
        #         since_date,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #5: {e}")

        # User
        # Access Pattern #6: Get user by user_id
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #6: Get user by user_id")
        #     print("   Using Main Table")
        #     user_id = created_entities["User"].user_id
        #     self.user_repo.get_user(
        #         user_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #6: {e}")

        # Access Pattern #7: Create a new user account
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #7: Create a new user account")
        #     print("   Using Main Table")
        #     user = created_entities["User"]
        #     self.user_repo.create_user(
        #         user,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #7: {e}")

        # Brand
        # Access Pattern #8: Get brand details by brand_id
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #8: Get brand details by brand_id")
        #     print("   Using Main Table")
        #     brand_id = created_entities["Brand"].brand_id
        #     self.brand_repo.get_brand(
        #         brand_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #8: {e}")

        # Access Pattern #9: Create a new brand
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #9: Create a new brand")
        #     print("   Using Main Table")
        #     brand = created_entities["Brand"]
        #     self.brand_repo.create_brand(
        #         brand,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #9: {e}")

        # UserWatch
        # Access Pattern #10: Get all watches for a user
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #10: Get all watches for a user")
        #     print("   Using Main Table")
        #     user_id = created_entities["UserWatch"].user_id
        #     self.userwatch_repo.get_user_watches(
        #         user_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #10: {e}")

        # Access Pattern #11: Get all users watching a specific brand
        # GSI: WatchesByBrand
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #11: Get all users watching a specific brand")
        #     print("   Using GSI: WatchesByBrand")
        #     brand_id = created_entities["UserWatch"].brand_id
        #     self.userwatch_repo.get_brand_watchers(
        #         brand_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #11: {e}")

        # Access Pattern #12: Get all users watching a specific category (partition key only)
        # GSI: WatchesByCategory
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #12: Get all users watching a specific category (partition key only)")
        #     print("   Using GSI: WatchesByCategory")
        #     category_id = created_entities["UserWatch"].category_id
        #     self.userwatch_repo.get_category_watchers(
        #         category_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #12: {e}")

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
    print('   - Deals')
    print('   - Users')
    print('   - Brands')
    print('   - UserWatches')

    if include_additional_access_patterns:
        print('🔍 Including additional access pattern examples (commented out)')

    examples = UsageExamples()
    examples.run_examples(include_additional_access_patterns=include_additional_access_patterns)


if __name__ == '__main__':
    main()
