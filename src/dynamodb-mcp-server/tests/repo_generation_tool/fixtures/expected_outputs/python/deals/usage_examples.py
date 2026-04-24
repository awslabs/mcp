"""Generated usage examples for DynamoDB entities and repositories"""

from __future__ import annotations

import os
import sys
from decimal import Decimal

# Import generated entities and repositories
from entities import Brand, Deal, TrendingDeal, User, UserActivity, UserWatch
from repositories import (
    BrandRepository,
    DealRepository,
    TrendingDealRepository,
    UserActivityRepository,
    UserRepository,
    UserWatchRepository,
)


class UsageExamples:
    """Examples of using the generated entities and repositories"""

    def __init__(self):
        """Initialize repositories with default table names from schema."""
        # Initialize repositories with their respective table names
        # Deals table repositories
        try:
            self.deal_repo = DealRepository('Deals')
            print("✅ Initialized DealRepository for table 'Deals'")
        except Exception as e:
            print(f'❌ Failed to initialize DealRepository: {e}')
            self.deal_repo = None
        # Users table repositories
        try:
            self.user_repo = UserRepository('Users')
            print("✅ Initialized UserRepository for table 'Users'")
        except Exception as e:
            print(f'❌ Failed to initialize UserRepository: {e}')
            self.user_repo = None
        # Brands table repositories
        try:
            self.brand_repo = BrandRepository('Brands')
            print("✅ Initialized BrandRepository for table 'Brands'")
        except Exception as e:
            print(f'❌ Failed to initialize BrandRepository: {e}')
            self.brand_repo = None
        # UserWatches table repositories
        try:
            self.userwatch_repo = UserWatchRepository('UserWatches')
            print("✅ Initialized UserWatchRepository for table 'UserWatches'")
        except Exception as e:
            print(f'❌ Failed to initialize UserWatchRepository: {e}')
            self.userwatch_repo = None
        # UserActivities table repositories
        try:
            self.useractivity_repo = UserActivityRepository('UserActivities')
            print("✅ Initialized UserActivityRepository for table 'UserActivities'")
        except Exception as e:
            print(f'❌ Failed to initialize UserActivityRepository: {e}')
            self.useractivity_repo = None
        # TrendingDeals table repositories
        try:
            self.trendingdeal_repo = TrendingDealRepository('TrendingDeals')
            print("✅ Initialized TrendingDealRepository for table 'TrendingDeals'")
        except Exception as e:
            print(f'❌ Failed to initialize TrendingDealRepository: {e}')
            self.trendingdeal_repo = None

    def run_examples(self, include_additional_access_patterns: bool = False):
        """Run CRUD examples for all entities"""
        # Dictionary to store created entities for access pattern testing
        created_entities = {}

        # Step 0: Cleanup any leftover entities from previous runs (makes tests idempotent)
        print('🧹 Pre-test Cleanup: Removing any leftover entities from previous runs')
        print('=' * 50)
        # Try to delete Deal (deal_id)
        try:
            sample_deal = Deal(
                deal_id='deal-12345',
                title='50% Off Premium Headphones',
                description='High-quality wireless headphones with noise cancellation',
                price=Decimal('149.99'),
                brand_id='brand-sony',
                brand_name='Sony',
                category_id='electronics',
                category_name='Electronics',
                created_at='2024-01-15T10:00:00Z',
                status='active',
            )
            self.deal_repo.delete_deal(sample_deal.deal_id)
            print('   🗑️  Deleted leftover deal (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete User (user_id)
        try:
            sample_user = User(
                user_id='user-67890',
                username='dealseeker123',
                email='john.doe@example.com',
                display_name='John Doe',
                created_at='2024-01-10T08:30:00Z',
                last_login='2024-01-15T09:45:00Z',
            )
            self.user_repo.delete_user(sample_user.user_id)
            print('   🗑️  Deleted leftover user (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete Brand (brand_id)
        try:
            sample_brand = Brand(
                brand_id='brand-sony',
                brand_name='Sony',
                description='Leading electronics and entertainment company',
                logo_url='https://example.com/logos/sony.png',
                created_at='2024-01-01T00:00:00Z',
            )
            self.brand_repo.delete_brand(sample_brand.brand_id)
            print('   🗑️  Deleted leftover brand (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete UserWatch (user_id, watch_key)
        try:
            sample_userwatch = UserWatch(
                user_id='user-67890',
                watch_key='watch-electronics-sony',
                watch_type='brand_category',
                target_id='brand-sony',
                target_name='Sony Electronics',
                brand_id='brand-sony',
                category_id='electronics',
                created_at='2024-01-12T16:00:00Z',
            )
            self.userwatch_repo.delete_user_watch(
                sample_userwatch.user_id, sample_userwatch.watch_key
            )
            print('   🗑️  Deleted leftover userwatch (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete UserActivity (user_id, timestamp, activity_id)
        try:
            sample_useractivity = UserActivity(
                user_id='user-67890',
                timestamp='2024-01-15T10:30:00Z',
                activity_id='activity-view-deal-12345',
                activity_type='deal_view',
                details={'deal_id': 'deal-12345', 'duration_seconds': 45, 'source': 'homepage'},
            )
            self.useractivity_repo.delete_user_activity(
                sample_useractivity.user_id,
                sample_useractivity.timestamp,
                sample_useractivity.activity_id,
            )
            print('   🗑️  Deleted leftover useractivity (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete TrendingDeal (category_id, engagement_score)
        try:
            sample_trendingdeal = TrendingDeal(
                category_id='electronics',
                engagement_score=850,
                deal_id='deal-12345',
                title='50% Off Premium Headphones',
                brand_id='brand-sony',
                discount_percentage=Decimal('50.0'),
                views=1250,
                clicks=89,
            )
            self.trendingdeal_repo.delete_trending_deal(
                sample_trendingdeal.category_id, sample_trendingdeal.engagement_score
            )
            print('   🗑️  Deleted leftover trendingdeal (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        print('✅ Pre-test cleanup completed\n')

        print('Running Repository Examples')
        print('=' * 50)
        print('\n=== Deals Table Operations ===')

        # Deal example
        print('\n--- Deal ---')

        # 1. CREATE - Create sample deal
        sample_deal = Deal(
            deal_id='deal-12345',
            title='50% Off Premium Headphones',
            description='High-quality wireless headphones with noise cancellation',
            price=Decimal('149.99'),
            brand_id='brand-sony',
            brand_name='Sony',
            category_id='electronics',
            category_name='Electronics',
            created_at='2024-01-15T10:00:00Z',
            status='active',
        )

        print('📝 Creating deal...')
        print(f'📝 PK: {sample_deal.pk()}, SK: {sample_deal.sk()}')

        try:
            created_deal = self.deal_repo.create_deal(sample_deal)
            print(f'✅ Created: {created_deal}')
            # Store created entity for access pattern testing
            created_entities['Deal'] = created_deal
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  deal already exists, retrieving existing entity...')
                try:
                    existing_deal = self.deal_repo.get_deal(sample_deal.deal_id)

                    if existing_deal:
                        print(f'✅ Retrieved existing: {existing_deal}')
                        # Store existing entity for access pattern testing
                        created_entities['Deal'] = existing_deal
                    else:
                        print('❌ Failed to retrieve existing deal')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing deal: {get_error}')
            else:
                print(f'❌ Failed to create deal: {e}')
        # 2. UPDATE - Update non-key field (title)
        if 'Deal' in created_entities:
            print('\n🔄 Updating title field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['Deal']
                refreshed_entity = self.deal_repo.get_deal(entity_for_refresh.deal_id)

                if refreshed_entity:
                    original_value = refreshed_entity.title
                    refreshed_entity.title = '60% Off Premium Headphones - Limited Time'

                    updated_deal = self.deal_repo.update_deal(refreshed_entity)
                    print(f'✅ Updated title: {original_value} → {updated_deal.title}')

                    # Update stored entity with updated values
                    created_entities['Deal'] = updated_deal
                else:
                    print('❌ Could not refresh deal for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(f'⚠️  deal was modified by another process (optimistic locking): {e}')
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update deal: {e}')

        # 3. GET - Retrieve and print the entity
        if 'Deal' in created_entities:
            print('\n🔍 Retrieving deal...')
            try:
                entity_for_get = created_entities['Deal']
                retrieved_deal = self.deal_repo.get_deal(entity_for_get.deal_id)

                if retrieved_deal:
                    print(f'✅ Retrieved: {retrieved_deal}')
                else:
                    print('❌ Failed to retrieve deal')
            except Exception as e:
                print(f'❌ Failed to retrieve deal: {e}')

        print('🎯 Deal CRUD cycle completed!')
        print('\n=== Users Table Operations ===')

        # User example
        print('\n--- User ---')

        # 1. CREATE - Create sample user
        sample_user = User(
            user_id='user-67890',
            username='dealseeker123',
            email='john.doe@example.com',
            display_name='John Doe',
            created_at='2024-01-10T08:30:00Z',
            last_login='2024-01-15T09:45:00Z',
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
        # 2. UPDATE - Update non-key field (username)
        if 'User' in created_entities:
            print('\n🔄 Updating username field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['User']
                refreshed_entity = self.user_repo.get_user(entity_for_refresh.user_id)

                if refreshed_entity:
                    original_value = refreshed_entity.username
                    refreshed_entity.username = 'dealhunter123'

                    updated_user = self.user_repo.update_user(refreshed_entity)
                    print(f'✅ Updated username: {original_value} → {updated_user.username}')

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
        print('\n=== Brands Table Operations ===')

        # Brand example
        print('\n--- Brand ---')

        # 1. CREATE - Create sample brand
        sample_brand = Brand(
            brand_id='brand-sony',
            brand_name='Sony',
            description='Leading electronics and entertainment company',
            logo_url='https://example.com/logos/sony.png',
            created_at='2024-01-01T00:00:00Z',
        )

        print('📝 Creating brand...')
        print(f'📝 PK: {sample_brand.pk()}, SK: {sample_brand.sk()}')

        try:
            created_brand = self.brand_repo.create_brand(sample_brand)
            print(f'✅ Created: {created_brand}')
            # Store created entity for access pattern testing
            created_entities['Brand'] = created_brand
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  brand already exists, retrieving existing entity...')
                try:
                    existing_brand = self.brand_repo.get_brand(sample_brand.brand_id)

                    if existing_brand:
                        print(f'✅ Retrieved existing: {existing_brand}')
                        # Store existing entity for access pattern testing
                        created_entities['Brand'] = existing_brand
                    else:
                        print('❌ Failed to retrieve existing brand')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing brand: {get_error}')
            else:
                print(f'❌ Failed to create brand: {e}')
        # 2. UPDATE - Update non-key field (brand_name)
        if 'Brand' in created_entities:
            print('\n🔄 Updating brand_name field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['Brand']
                refreshed_entity = self.brand_repo.get_brand(entity_for_refresh.brand_id)

                if refreshed_entity:
                    original_value = refreshed_entity.brand_name
                    refreshed_entity.brand_name = 'Sony Corporation'

                    updated_brand = self.brand_repo.update_brand(refreshed_entity)
                    print(f'✅ Updated brand_name: {original_value} → {updated_brand.brand_name}')

                    # Update stored entity with updated values
                    created_entities['Brand'] = updated_brand
                else:
                    print('❌ Could not refresh brand for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(f'⚠️  brand was modified by another process (optimistic locking): {e}')
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update brand: {e}')

        # 3. GET - Retrieve and print the entity
        if 'Brand' in created_entities:
            print('\n🔍 Retrieving brand...')
            try:
                entity_for_get = created_entities['Brand']
                retrieved_brand = self.brand_repo.get_brand(entity_for_get.brand_id)

                if retrieved_brand:
                    print(f'✅ Retrieved: {retrieved_brand}')
                else:
                    print('❌ Failed to retrieve brand')
            except Exception as e:
                print(f'❌ Failed to retrieve brand: {e}')

        print('🎯 Brand CRUD cycle completed!')
        print('\n=== UserWatches Table Operations ===')

        # UserWatch example
        print('\n--- UserWatch ---')

        # 1. CREATE - Create sample userwatch
        sample_userwatch = UserWatch(
            user_id='user-67890',
            watch_key='watch-electronics-sony',
            watch_type='brand_category',
            target_id='brand-sony',
            target_name='Sony Electronics',
            brand_id='brand-sony',
            category_id='electronics',
            created_at='2024-01-12T16:00:00Z',
        )

        print('📝 Creating userwatch...')
        print(f'📝 PK: {sample_userwatch.pk()}, SK: {sample_userwatch.sk()}')

        try:
            created_userwatch = self.userwatch_repo.create_user_watch(sample_userwatch)
            print(f'✅ Created: {created_userwatch}')
            # Store created entity for access pattern testing
            created_entities['UserWatch'] = created_userwatch
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  userwatch already exists, retrieving existing entity...')
                try:
                    existing_userwatch = self.userwatch_repo.get_user_watch(
                        sample_userwatch.user_id, sample_userwatch.watch_key
                    )

                    if existing_userwatch:
                        print(f'✅ Retrieved existing: {existing_userwatch}')
                        # Store existing entity for access pattern testing
                        created_entities['UserWatch'] = existing_userwatch
                    else:
                        print('❌ Failed to retrieve existing userwatch')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing userwatch: {get_error}')
            else:
                print(f'❌ Failed to create userwatch: {e}')
        # 2. UPDATE - Update non-key field (watch_type)
        if 'UserWatch' in created_entities:
            print('\n🔄 Updating watch_type field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['UserWatch']
                refreshed_entity = self.userwatch_repo.get_user_watch(
                    entity_for_refresh.user_id, entity_for_refresh.watch_key
                )

                if refreshed_entity:
                    original_value = refreshed_entity.watch_type
                    refreshed_entity.watch_type = 'premium_brand_category'

                    updated_userwatch = self.userwatch_repo.update_user_watch(refreshed_entity)
                    print(
                        f'✅ Updated watch_type: {original_value} → {updated_userwatch.watch_type}'
                    )

                    # Update stored entity with updated values
                    created_entities['UserWatch'] = updated_userwatch
                else:
                    print('❌ Could not refresh userwatch for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  userwatch was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update userwatch: {e}')

        # 3. GET - Retrieve and print the entity
        if 'UserWatch' in created_entities:
            print('\n🔍 Retrieving userwatch...')
            try:
                entity_for_get = created_entities['UserWatch']
                retrieved_userwatch = self.userwatch_repo.get_user_watch(
                    entity_for_get.user_id, entity_for_get.watch_key
                )

                if retrieved_userwatch:
                    print(f'✅ Retrieved: {retrieved_userwatch}')
                else:
                    print('❌ Failed to retrieve userwatch')
            except Exception as e:
                print(f'❌ Failed to retrieve userwatch: {e}')

        print('🎯 UserWatch CRUD cycle completed!')
        print('\n=== UserActivities Table Operations ===')

        # UserActivity example
        print('\n--- UserActivity ---')

        # 1. CREATE - Create sample useractivity
        sample_useractivity = UserActivity(
            user_id='user-67890',
            timestamp='2024-01-15T10:30:00Z',
            activity_id='activity-view-deal-12345',
            activity_type='deal_view',
            details={'deal_id': 'deal-12345', 'duration_seconds': 45, 'source': 'homepage'},
        )

        print('📝 Creating useractivity...')
        print(f'📝 PK: {sample_useractivity.pk()}, SK: {sample_useractivity.sk()}')

        try:
            created_useractivity = self.useractivity_repo.create_user_activity(sample_useractivity)
            print(f'✅ Created: {created_useractivity}')
            # Store created entity for access pattern testing
            created_entities['UserActivity'] = created_useractivity
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  useractivity already exists, retrieving existing entity...')
                try:
                    existing_useractivity = self.useractivity_repo.get_user_activity(
                        sample_useractivity.user_id,
                        sample_useractivity.timestamp,
                        sample_useractivity.activity_id,
                    )

                    if existing_useractivity:
                        print(f'✅ Retrieved existing: {existing_useractivity}')
                        # Store existing entity for access pattern testing
                        created_entities['UserActivity'] = existing_useractivity
                    else:
                        print('❌ Failed to retrieve existing useractivity')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing useractivity: {get_error}')
            else:
                print(f'❌ Failed to create useractivity: {e}')
        # 2. UPDATE - Update non-key field (activity_type)
        if 'UserActivity' in created_entities:
            print('\n🔄 Updating activity_type field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['UserActivity']
                refreshed_entity = self.useractivity_repo.get_user_activity(
                    entity_for_refresh.user_id,
                    entity_for_refresh.timestamp,
                    entity_for_refresh.activity_id,
                )

                if refreshed_entity:
                    original_value = refreshed_entity.activity_type
                    refreshed_entity.activity_type = 'deal_interaction'

                    updated_useractivity = self.useractivity_repo.update_user_activity(
                        refreshed_entity
                    )
                    print(
                        f'✅ Updated activity_type: {original_value} → {updated_useractivity.activity_type}'
                    )

                    # Update stored entity with updated values
                    created_entities['UserActivity'] = updated_useractivity
                else:
                    print('❌ Could not refresh useractivity for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  useractivity was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update useractivity: {e}')

        # 3. GET - Retrieve and print the entity
        if 'UserActivity' in created_entities:
            print('\n🔍 Retrieving useractivity...')
            try:
                entity_for_get = created_entities['UserActivity']
                retrieved_useractivity = self.useractivity_repo.get_user_activity(
                    entity_for_get.user_id, entity_for_get.timestamp, entity_for_get.activity_id
                )

                if retrieved_useractivity:
                    print(f'✅ Retrieved: {retrieved_useractivity}')
                else:
                    print('❌ Failed to retrieve useractivity')
            except Exception as e:
                print(f'❌ Failed to retrieve useractivity: {e}')

        print('🎯 UserActivity CRUD cycle completed!')
        print('\n=== TrendingDeals Table Operations ===')

        # TrendingDeal example
        print('\n--- TrendingDeal ---')

        # 1. CREATE - Create sample trendingdeal
        sample_trendingdeal = TrendingDeal(
            category_id='electronics',
            engagement_score=850,
            deal_id='deal-12345',
            title='50% Off Premium Headphones',
            brand_id='brand-sony',
            discount_percentage=Decimal('50.0'),
            views=1250,
            clicks=89,
        )

        print('📝 Creating trendingdeal...')
        print(f'📝 PK: {sample_trendingdeal.pk()}, SK: {sample_trendingdeal.sk()}')

        try:
            created_trendingdeal = self.trendingdeal_repo.create_trending_deal(sample_trendingdeal)
            print(f'✅ Created: {created_trendingdeal}')
            # Store created entity for access pattern testing
            created_entities['TrendingDeal'] = created_trendingdeal
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  trendingdeal already exists, retrieving existing entity...')
                try:
                    existing_trendingdeal = self.trendingdeal_repo.get_trending_deal(
                        sample_trendingdeal.category_id, sample_trendingdeal.engagement_score
                    )

                    if existing_trendingdeal:
                        print(f'✅ Retrieved existing: {existing_trendingdeal}')
                        # Store existing entity for access pattern testing
                        created_entities['TrendingDeal'] = existing_trendingdeal
                    else:
                        print('❌ Failed to retrieve existing trendingdeal')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing trendingdeal: {get_error}')
            else:
                print(f'❌ Failed to create trendingdeal: {e}')
        # 2. UPDATE - Update non-key field (engagement_score)
        if 'TrendingDeal' in created_entities:
            print('\n🔄 Updating engagement_score field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['TrendingDeal']
                refreshed_entity = self.trendingdeal_repo.get_trending_deal(
                    entity_for_refresh.category_id, entity_for_refresh.engagement_score
                )

                if refreshed_entity:
                    original_value = refreshed_entity.engagement_score
                    refreshed_entity.engagement_score = 920

                    updated_trendingdeal = self.trendingdeal_repo.update_trending_deal(
                        refreshed_entity
                    )
                    print(
                        f'✅ Updated engagement_score: {original_value} → {updated_trendingdeal.engagement_score}'
                    )

                    # Update stored entity with updated values
                    created_entities['TrendingDeal'] = updated_trendingdeal
                else:
                    print('❌ Could not refresh trendingdeal for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  trendingdeal was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update trendingdeal: {e}')

        # 3. GET - Retrieve and print the entity
        if 'TrendingDeal' in created_entities:
            print('\n🔍 Retrieving trendingdeal...')
            try:
                entity_for_get = created_entities['TrendingDeal']
                retrieved_trendingdeal = self.trendingdeal_repo.get_trending_deal(
                    entity_for_get.category_id, entity_for_get.engagement_score
                )

                if retrieved_trendingdeal:
                    print(f'✅ Retrieved: {retrieved_trendingdeal}')
                else:
                    print('❌ Failed to retrieve trendingdeal')
            except Exception as e:
                print(f'❌ Failed to retrieve trendingdeal: {e}')

        print('🎯 TrendingDeal CRUD cycle completed!')

        print('\n' + '=' * 50)
        print('🎉 Basic CRUD examples completed!')

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
            try:
                deleted = self.deal_repo.delete_deal(created_entities['Deal'].deal_id)

                if deleted:
                    print('✅ Deleted deal successfully')
                else:
                    print('❌ Failed to delete deal (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete deal: {e}')

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

        # Delete Brand
        if 'Brand' in created_entities:
            print('\n🗑️  Deleting brand...')
            try:
                deleted = self.brand_repo.delete_brand(created_entities['Brand'].brand_id)

                if deleted:
                    print('✅ Deleted brand successfully')
                else:
                    print('❌ Failed to delete brand (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete brand: {e}')

        # Delete UserWatch
        if 'UserWatch' in created_entities:
            print('\n🗑️  Deleting userwatch...')
            try:
                deleted = self.userwatch_repo.delete_user_watch(
                    created_entities['UserWatch'].user_id, created_entities['UserWatch'].watch_key
                )

                if deleted:
                    print('✅ Deleted userwatch successfully')
                else:
                    print('❌ Failed to delete userwatch (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete userwatch: {e}')

        # Delete UserActivity
        if 'UserActivity' in created_entities:
            print('\n🗑️  Deleting useractivity...')
            try:
                deleted = self.useractivity_repo.delete_user_activity(
                    created_entities['UserActivity'].user_id,
                    created_entities['UserActivity'].timestamp,
                    created_entities['UserActivity'].activity_id,
                )

                if deleted:
                    print('✅ Deleted useractivity successfully')
                else:
                    print('❌ Failed to delete useractivity (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete useractivity: {e}')

        # Delete TrendingDeal
        if 'TrendingDeal' in created_entities:
            print('\n🗑️  Deleting trendingdeal...')
            try:
                deleted = self.trendingdeal_repo.delete_trending_deal(
                    created_entities['TrendingDeal'].category_id,
                    created_entities['TrendingDeal'].engagement_score,
                )

                if deleted:
                    print('✅ Deleted trendingdeal successfully')
                else:
                    print('❌ Failed to delete trendingdeal (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete trendingdeal: {e}')
        print('\n💡 Requirements:')
        print("   - DynamoDB table 'Deals' must exist")
        print("   - DynamoDB table 'Users' must exist")
        print("   - DynamoDB table 'Brands' must exist")
        print("   - DynamoDB table 'UserWatches' must exist")
        print("   - DynamoDB table 'UserActivities' must exist")
        print("   - DynamoDB table 'TrendingDeals' must exist")
        print('   - DynamoDB permissions: GetItem, PutItem, UpdateItem, DeleteItem')

    def _test_additional_access_patterns(self, created_entities: dict):
        """Test additional access patterns beyond basic CRUD"""
        print('\n' + '=' * 60)
        print('🔍 Additional Access Pattern Testing')
        print('=' * 60)
        print()

        # Deal
        # Access Pattern #1: Get deal details by deal_id
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #1: Get deal details by deal_id')
            print('   Using Main Table')
            result = self.deal_repo.get_deal(created_entities['Deal'].deal_id)
            print('   ✅ Get deal details by deal_id completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #1: {e}')

        # Access Pattern #2: Create a new deal
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #2: Create a new deal')
            print('   Using Main Table')
            test_entity = Deal(
                deal_id='deal-98765',
                title='30% Off Gaming Laptop',
                description='High-performance gaming laptop with RTX graphics card and 16GB RAM',
                price=Decimal('899.99'),
                brand_id='brand-asus',
                brand_name='ASUS',
                category_id='computers',
                category_name='Computers',
                created_at='2024-01-12T14:30:00Z',
                status='featured',
            )
            result = self.deal_repo.put_deal(test_entity)
            print('   ✅ Create a new deal completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #2: {e}')

        # Access Pattern #3: Get all deals for a brand sorted by creation date
        # GSI: DealsByBrand
        try:
            print(
                '🔍 Testing Access Pattern #3: Get all deals for a brand sorted by creation date'
            )
            print('   Using GSI: DealsByBrand')
            result = self.deal_repo.get_deals_by_brand(created_entities['Deal'].brand_id)
            print('   ✅ Get all deals for a brand sorted by creation date completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #3: {e}')

        # Access Pattern #4: Get all deals for a category sorted by creation date
        # GSI: DealsByCategory
        try:
            print(
                '🔍 Testing Access Pattern #4: Get all deals for a category sorted by creation date'
            )
            print('   Using GSI: DealsByCategory')
            result = self.deal_repo.get_deals_by_category(created_entities['Deal'].category_id)
            print('   ✅ Get all deals for a category sorted by creation date completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #4: {e}')

        # Access Pattern #5: Get recent deals for a brand after a specific date
        # GSI: DealsByBrand
        # Range Condition: >=
        try:
            print(
                '🔍 Testing Access Pattern #5: Get recent deals for a brand after a specific date'
            )
            print('   Using GSI: DealsByBrand')
            print('   Range Condition: >=')
            result = self.deal_repo.get_recent_deals_by_brand(
                created_entities['Deal'].brand_id, '2024-01-01'
            )
            print('   ✅ Get recent deals for a brand after a specific date completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #5: {e}')

        # User
        # Access Pattern #6: Get user by user_id
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #6: Get user by user_id')
            print('   Using Main Table')
            result = self.user_repo.get_user(created_entities['User'].user_id)
            print('   ✅ Get user by user_id completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #6: {e}')

        # Access Pattern #7: Create a new user account
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #7: Create a new user account')
            print('   Using Main Table')
            test_entity = User(
                user_id='user-54321',
                username='bargainhunter',
                email='sarah.wilson@gmail.com',
                display_name='Sarah Wilson',
                created_at='2024-01-08T12:15:00Z',
                last_login='2024-01-14T18:30:00Z',
            )
            result = self.user_repo.put_user(test_entity)
            print('   ✅ Create a new user account completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #7: {e}')

        # Brand
        # Access Pattern #8: Get brand details by brand_id
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #8: Get brand details by brand_id')
            print('   Using Main Table')
            result = self.brand_repo.get_brand(created_entities['Brand'].brand_id)
            print('   ✅ Get brand details by brand_id completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #8: {e}')

        # Access Pattern #9: Create a new brand
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #9: Create a new brand')
            print('   Using Main Table')
            test_entity = Brand(
                brand_id='brand-apple',
                brand_name='Apple',
                description='Innovative technology company known for premium consumer electronics',
                logo_url='https://example.com/logos/apple.png',
                created_at='2023-12-15T00:00:00Z',
            )
            result = self.brand_repo.put_brand(test_entity)
            print('   ✅ Create a new brand completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #9: {e}')

        # UserWatch
        # Access Pattern #10: Get all watches for a user
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #10: Get all watches for a user')
            print('   Using Main Table')
            result = self.userwatch_repo.get_user_watches(created_entities['UserWatch'].user_id)
            print('   ✅ Get all watches for a user completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #10: {e}')

        # Access Pattern #11: Get all users watching a specific brand
        # GSI: WatchesByBrand
        try:
            print('🔍 Testing Access Pattern #11: Get all users watching a specific brand')
            print('   Using GSI: WatchesByBrand')
            result = self.userwatch_repo.get_brand_watchers(created_entities['UserWatch'].brand_id)
            print('   ✅ Get all users watching a specific brand completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #11: {e}')

        # Access Pattern #12: Get all users watching a specific category (partition key only)
        # GSI: WatchesByCategory
        try:
            print(
                '🔍 Testing Access Pattern #12: Get all users watching a specific category (partition key only)'
            )
            print('   Using GSI: WatchesByCategory')
            result = self.userwatch_repo.get_category_watchers(
                created_entities['UserWatch'].category_id
            )
            print(
                '   ✅ Get all users watching a specific category (partition key only) completed'
            )
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #12: {e}')

        # Access Pattern #18: Get watches by target type
        # GSI: WatchesByType
        try:
            print('🔍 Testing Access Pattern #18: Get watches by target type')
            print('   Using GSI: WatchesByType')
            result = self.userwatch_repo.get_watches_by_type(
                created_entities['UserWatch'].watch_type
            )
            print('   ✅ Get watches by target type completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #18: {e}')

        # UserActivity
        # Access Pattern #13: Get all activities for a user
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #13: Get all activities for a user')
            print('   Using Main Table')
            result = self.useractivity_repo.get_user_activities(
                created_entities['UserActivity'].user_id
            )
            print('   ✅ Get all activities for a user completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #13: {e}')

        # Access Pattern #14: Get user activities after a specific timestamp
        # Index: Main Table
        # Range Condition: >=
        try:
            print('🔍 Testing Access Pattern #14: Get user activities after a specific timestamp')
            print('   Using Main Table')
            print('   Range Condition: >=')
            result = self.useractivity_repo.get_user_activities_after(
                created_entities['UserActivity'].user_id, '2024-01-01'
            )
            print('   ✅ Get user activities after a specific timestamp completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #14: {e}')

        # TrendingDeal
        # Access Pattern #15: Get trending deals for a category sorted by engagement score
        # Index: Main Table
        try:
            print(
                '🔍 Testing Access Pattern #15: Get trending deals for a category sorted by engagement score'
            )
            print('   Using Main Table')
            result = self.trendingdeal_repo.get_trending_by_category(
                created_entities['TrendingDeal'].category_id
            )
            print('   ✅ Get trending deals for a category sorted by engagement score completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #15: {e}')

        # Access Pattern #16: Get trending deals with engagement score above threshold
        # Index: Main Table
        # Range Condition: >=
        try:
            print(
                '🔍 Testing Access Pattern #16: Get trending deals with engagement score above threshold'
            )
            print('   Using Main Table')
            print('   Range Condition: >=')
            result = self.trendingdeal_repo.get_highly_engaged_deals(
                created_entities['TrendingDeal'].category_id, 0
            )
            print('   ✅ Get trending deals with engagement score above threshold completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #16: {e}')

        # Access Pattern #17: Get deals by brand with high discount percentage
        # GSI: TrendingByDiscount
        # Range Condition: >=
        try:
            print(
                '🔍 Testing Access Pattern #17: Get deals by brand with high discount percentage'
            )
            print('   Using GSI: TrendingByDiscount')
            print('   Range Condition: >=')
            result = self.trendingdeal_repo.get_high_discount_deals(
                created_entities['TrendingDeal'].brand_id, '2024-01-01'
            )
            print('   ✅ Get deals by brand with high discount percentage completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #17: {e}')

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
    print('   - Deals')
    print('   - Users')
    print('   - Brands')
    print('   - UserWatches')
    print('   - UserActivities')
    print('   - TrendingDeals')

    if include_additional_access_patterns:
        print('🔍 Including additional access pattern examples')

    examples = UsageExamples()
    examples.run_examples(include_additional_access_patterns=include_additional_access_patterns)


if __name__ == '__main__':
    main()
