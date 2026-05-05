"""Generated usage examples for DynamoDB entities and repositories"""

from __future__ import annotations

import os
import sys
from decimal import Decimal

# Import generated entities and repositories
from entities import (
    Order,
    OrderItem,
    Product,
    ProductCategory,
    ProductReview,
    User,
    UserAddress,
    UserOrderHistory,
)
from repositories import (
    OrderItemRepository,
    OrderRepository,
    ProductCategoryRepository,
    ProductRepository,
    ProductReviewRepository,
    UserAddressRepository,
    UserOrderHistoryRepository,
    UserRepository,
)


class UsageExamples:
    """Examples of using the generated entities and repositories"""

    def __init__(self):
        """Initialize repositories with default table names from schema."""
        # Initialize repositories with their respective table names
        # UserTable table repositories
        try:
            self.user_repo = UserRepository('UserTable')
            print("✅ Initialized UserRepository for table 'UserTable'")
        except Exception as e:
            print(f'❌ Failed to initialize UserRepository: {e}')
            self.user_repo = None
        try:
            self.useraddress_repo = UserAddressRepository('UserTable')
            print("✅ Initialized UserAddressRepository for table 'UserTable'")
        except Exception as e:
            print(f'❌ Failed to initialize UserAddressRepository: {e}')
            self.useraddress_repo = None
        # ProductTable table repositories
        try:
            self.product_repo = ProductRepository('ProductTable')
            print("✅ Initialized ProductRepository for table 'ProductTable'")
        except Exception as e:
            print(f'❌ Failed to initialize ProductRepository: {e}')
            self.product_repo = None
        try:
            self.productcategory_repo = ProductCategoryRepository('ProductTable')
            print("✅ Initialized ProductCategoryRepository for table 'ProductTable'")
        except Exception as e:
            print(f'❌ Failed to initialize ProductCategoryRepository: {e}')
            self.productcategory_repo = None
        try:
            self.productreview_repo = ProductReviewRepository('ProductTable')
            print("✅ Initialized ProductReviewRepository for table 'ProductTable'")
        except Exception as e:
            print(f'❌ Failed to initialize ProductReviewRepository: {e}')
            self.productreview_repo = None
        # OrderTable table repositories
        try:
            self.order_repo = OrderRepository('OrderTable')
            print("✅ Initialized OrderRepository for table 'OrderTable'")
        except Exception as e:
            print(f'❌ Failed to initialize OrderRepository: {e}')
            self.order_repo = None
        try:
            self.orderitem_repo = OrderItemRepository('OrderTable')
            print("✅ Initialized OrderItemRepository for table 'OrderTable'")
        except Exception as e:
            print(f'❌ Failed to initialize OrderItemRepository: {e}')
            self.orderitem_repo = None
        try:
            self.userorderhistory_repo = UserOrderHistoryRepository('OrderTable')
            print("✅ Initialized UserOrderHistoryRepository for table 'OrderTable'")
        except Exception as e:
            print(f'❌ Failed to initialize UserOrderHistoryRepository: {e}')
            self.userorderhistory_repo = None

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
                email='john.doe@example.com',
                first_name='John',
                last_name='Doe',
                phone='+1-555-0123',
                created_at='2024-01-15T10:00:00Z',
                status='active',
            )
            self.user_repo.delete_user(sample_user.user_id)
            print('   🗑️  Deleted leftover user (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete UserAddress (user_id, address_id)
        try:
            sample_useraddress = UserAddress(
                user_id='user-12345',
                address_id='addr-67890',
                address_type='shipping',
                street_address='123 Main Street',
                city='New York',
                state='NY',
                postal_code='10001',
                country='USA',
                is_default=True,
            )
            self.useraddress_repo.delete_user_address(
                sample_useraddress.user_id, sample_useraddress.address_id
            )
            print('   🗑️  Deleted leftover useraddress (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete Product (product_id)
        try:
            sample_product = Product(
                product_id='prod-11111',
                name='Wireless Bluetooth Headphones',
                description='High-quality wireless headphones with noise cancellation',
                category='Electronics',
                brand='TechBrand',
                price=Decimal('199.99'),
                currency='sample_currency',
                stock_quantity=50,
                sku='TB-WBH-001',
                weight=Decimal('3.14'),
                dimensions={'key': 'value'},
                created_at='2024-01-10T08:00:00Z',
                updated_at='sample_updated_at',
                status='active',
            )
            self.product_repo.delete_product(sample_product.product_id)
            print('   🗑️  Deleted leftover product (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete ProductCategory (category_name, product_id)
        try:
            sample_productcategory = ProductCategory(
                category_name='Electronics',
                product_id='prod-11111',
                product_name='Wireless Bluetooth Headphones',
                price=Decimal('199.99'),
                stock_quantity=50,
            )
            self.productcategory_repo.delete_product_category(
                sample_productcategory.category_name, sample_productcategory.product_id
            )
            print('   🗑️  Deleted leftover productcategory (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete ProductReview (product_id, review_id)
        try:
            sample_productreview = ProductReview(
                product_id='prod-11111',
                review_id='review-22222',
                user_id='user-12345',
                rating=5,
                title='Excellent headphones!',
                comment='Great sound quality and comfortable to wear for long periods.',
                created_at='2024-01-18T16:45:00Z',
                verified_purchase=True,
            )
            self.productreview_repo.delete_product_review(
                sample_productreview.product_id, sample_productreview.review_id
            )
            print('   🗑️  Deleted leftover productreview (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete Order (order_id)
        try:
            sample_order = Order(
                order_id='order-33333',
                user_id='user-12345',
                order_date='sample_order_date',
                status='processing',
                total_amount=Decimal('199.99'),
                currency='sample_currency',
                shipping_address={'value': '123 Main Street, New York, NY 10001'},
                billing_address={'key': 'value'},
                payment_method='credit_card',
                shipping_method='sample_shipping_method',
                tracking_number='sample_tracking_number',
                estimated_delivery='sample_estimated_delivery',
                created_at='2024-01-20T11:30:00Z',
                updated_at='2024-01-20T11:30:00Z',
            )
            self.order_repo.delete_order(sample_order.order_id)
            print('   🗑️  Deleted leftover order (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete OrderItem (order_id, product_id)
        try:
            sample_orderitem = OrderItem(
                order_id='order-33333',
                product_id='prod-11111',
                product_name='Wireless Bluetooth Headphones',
                sku='sample_sku',
                quantity=1,
                unit_price=Decimal('199.99'),
                total_price=Decimal('199.99'),
                currency='sample_currency',
            )
            self.orderitem_repo.delete_order_item(
                sample_orderitem.order_id, sample_orderitem.product_id
            )
            print('   🗑️  Deleted leftover orderitem (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete UserOrderHistory (user_id, order_date, order_id)
        try:
            sample_userorderhistory = UserOrderHistory(
                user_id='user-12345',
                order_id='order-33333',
                order_date='2024-01-20',
                status='processing',
                total_amount=Decimal('199.99'),
                currency='sample_currency',
                item_count=1,
            )
            self.userorderhistory_repo.delete_user_order_history(
                sample_userorderhistory.user_id,
                sample_userorderhistory.order_date,
                sample_userorderhistory.order_id,
            )
            print('   🗑️  Deleted leftover userorderhistory (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        print('✅ Pre-test cleanup completed\n')

        print('Running Repository Examples')
        print('=' * 50)
        print('\n=== UserTable Table Operations ===')

        # User example
        print('\n--- User ---')

        # 1. CREATE - Create sample user
        sample_user = User(
            user_id='user-12345',
            email='john.doe@example.com',
            first_name='John',
            last_name='Doe',
            phone='+1-555-0123',
            created_at='2024-01-15T10:00:00Z',
            status='active',
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
        # 2. UPDATE - Update non-key field (phone)
        if 'User' in created_entities:
            print('\n🔄 Updating phone field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['User']
                refreshed_entity = self.user_repo.get_user(entity_for_refresh.user_id)

                if refreshed_entity:
                    original_value = refreshed_entity.phone
                    refreshed_entity.phone = '+1-555-0199'

                    updated_user = self.user_repo.update_user(refreshed_entity)
                    print(f'✅ Updated phone: {original_value} → {updated_user.phone}')

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

        # UserAddress example
        print('\n--- UserAddress ---')

        # 1. CREATE - Create sample useraddress
        sample_useraddress = UserAddress(
            user_id='user-12345',
            address_id='addr-67890',
            address_type='shipping',
            street_address='123 Main Street',
            city='New York',
            state='NY',
            postal_code='10001',
            country='USA',
            is_default=True,
        )

        print('📝 Creating useraddress...')
        print(f'📝 PK: {sample_useraddress.pk()}, SK: {sample_useraddress.sk()}')

        try:
            created_useraddress = self.useraddress_repo.create_user_address(sample_useraddress)
            print(f'✅ Created: {created_useraddress}')
            # Store created entity for access pattern testing
            created_entities['UserAddress'] = created_useraddress
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  useraddress already exists, retrieving existing entity...')
                try:
                    existing_useraddress = self.useraddress_repo.get_user_address(
                        sample_useraddress.user_id, sample_useraddress.address_id
                    )

                    if existing_useraddress:
                        print(f'✅ Retrieved existing: {existing_useraddress}')
                        # Store existing entity for access pattern testing
                        created_entities['UserAddress'] = existing_useraddress
                    else:
                        print('❌ Failed to retrieve existing useraddress')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing useraddress: {get_error}')
            else:
                print(f'❌ Failed to create useraddress: {e}')
        # 2. UPDATE - Update non-key field (street_address)
        if 'UserAddress' in created_entities:
            print('\n🔄 Updating street_address field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['UserAddress']
                refreshed_entity = self.useraddress_repo.get_user_address(
                    entity_for_refresh.user_id, entity_for_refresh.address_id
                )

                if refreshed_entity:
                    original_value = refreshed_entity.street_address
                    refreshed_entity.street_address = '456 Oak Avenue'

                    updated_useraddress = self.useraddress_repo.update_user_address(
                        refreshed_entity
                    )
                    print(
                        f'✅ Updated street_address: {original_value} → {updated_useraddress.street_address}'
                    )

                    # Update stored entity with updated values
                    created_entities['UserAddress'] = updated_useraddress
                else:
                    print('❌ Could not refresh useraddress for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  useraddress was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update useraddress: {e}')

        # 3. GET - Retrieve and print the entity
        if 'UserAddress' in created_entities:
            print('\n🔍 Retrieving useraddress...')
            try:
                entity_for_get = created_entities['UserAddress']
                retrieved_useraddress = self.useraddress_repo.get_user_address(
                    entity_for_get.user_id, entity_for_get.address_id
                )

                if retrieved_useraddress:
                    print(f'✅ Retrieved: {retrieved_useraddress}')
                else:
                    print('❌ Failed to retrieve useraddress')
            except Exception as e:
                print(f'❌ Failed to retrieve useraddress: {e}')

        print('🎯 UserAddress CRUD cycle completed!')
        print('\n=== ProductTable Table Operations ===')

        # Product example
        print('\n--- Product ---')

        # 1. CREATE - Create sample product
        sample_product = Product(
            product_id='prod-11111',
            name='Wireless Bluetooth Headphones',
            description='High-quality wireless headphones with noise cancellation',
            category='Electronics',
            brand='TechBrand',
            price=Decimal('199.99'),
            currency='sample_currency',
            stock_quantity=50,
            sku='TB-WBH-001',
            weight=Decimal('3.14'),
            dimensions={'key': 'value'},
            created_at='2024-01-10T08:00:00Z',
            updated_at='sample_updated_at',
            status='active',
        )

        print('📝 Creating product...')
        print(f'📝 PK: {sample_product.pk()}, SK: {sample_product.sk()}')

        try:
            created_product = self.product_repo.create_product(sample_product)
            print(f'✅ Created: {created_product}')
            # Store created entity for access pattern testing
            created_entities['Product'] = created_product
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  product already exists, retrieving existing entity...')
                try:
                    existing_product = self.product_repo.get_product(sample_product.product_id)

                    if existing_product:
                        print(f'✅ Retrieved existing: {existing_product}')
                        # Store existing entity for access pattern testing
                        created_entities['Product'] = existing_product
                    else:
                        print('❌ Failed to retrieve existing product')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing product: {get_error}')
            else:
                print(f'❌ Failed to create product: {e}')
        # 2. UPDATE - Update non-key field (name)
        if 'Product' in created_entities:
            print('\n🔄 Updating name field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['Product']
                refreshed_entity = self.product_repo.get_product(entity_for_refresh.product_id)

                if refreshed_entity:
                    original_value = refreshed_entity.name
                    refreshed_entity.name = 'Premium Wireless Bluetooth Headphones'

                    updated_product = self.product_repo.update_product(refreshed_entity)
                    print(f'✅ Updated name: {original_value} → {updated_product.name}')

                    # Update stored entity with updated values
                    created_entities['Product'] = updated_product
                else:
                    print('❌ Could not refresh product for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(f'⚠️  product was modified by another process (optimistic locking): {e}')
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update product: {e}')

        # 3. GET - Retrieve and print the entity
        if 'Product' in created_entities:
            print('\n🔍 Retrieving product...')
            try:
                entity_for_get = created_entities['Product']
                retrieved_product = self.product_repo.get_product(entity_for_get.product_id)

                if retrieved_product:
                    print(f'✅ Retrieved: {retrieved_product}')
                else:
                    print('❌ Failed to retrieve product')
            except Exception as e:
                print(f'❌ Failed to retrieve product: {e}')

        print('🎯 Product CRUD cycle completed!')

        # ProductCategory example
        print('\n--- ProductCategory ---')

        # 1. CREATE - Create sample productcategory
        sample_productcategory = ProductCategory(
            category_name='Electronics',
            product_id='prod-11111',
            product_name='Wireless Bluetooth Headphones',
            price=Decimal('199.99'),
            stock_quantity=50,
        )

        print('📝 Creating productcategory...')
        print(f'📝 PK: {sample_productcategory.pk()}, SK: {sample_productcategory.sk()}')

        try:
            created_productcategory = self.productcategory_repo.create_product_category(
                sample_productcategory
            )
            print(f'✅ Created: {created_productcategory}')
            # Store created entity for access pattern testing
            created_entities['ProductCategory'] = created_productcategory
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  productcategory already exists, retrieving existing entity...')
                try:
                    existing_productcategory = self.productcategory_repo.get_product_category(
                        sample_productcategory.category_name, sample_productcategory.product_id
                    )

                    if existing_productcategory:
                        print(f'✅ Retrieved existing: {existing_productcategory}')
                        # Store existing entity for access pattern testing
                        created_entities['ProductCategory'] = existing_productcategory
                    else:
                        print('❌ Failed to retrieve existing productcategory')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing productcategory: {get_error}')
            else:
                print(f'❌ Failed to create productcategory: {e}')
        # 2. UPDATE - Update non-key field (product_name)
        if 'ProductCategory' in created_entities:
            print('\n🔄 Updating product_name field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['ProductCategory']
                refreshed_entity = self.productcategory_repo.get_product_category(
                    entity_for_refresh.category_name, entity_for_refresh.product_id
                )

                if refreshed_entity:
                    original_value = refreshed_entity.product_name
                    refreshed_entity.product_name = 'Premium Wireless Bluetooth Headphones'

                    updated_productcategory = self.productcategory_repo.update_product_category(
                        refreshed_entity
                    )
                    print(
                        f'✅ Updated product_name: {original_value} → {updated_productcategory.product_name}'
                    )

                    # Update stored entity with updated values
                    created_entities['ProductCategory'] = updated_productcategory
                else:
                    print('❌ Could not refresh productcategory for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  productcategory was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update productcategory: {e}')

        # 3. GET - Retrieve and print the entity
        if 'ProductCategory' in created_entities:
            print('\n🔍 Retrieving productcategory...')
            try:
                entity_for_get = created_entities['ProductCategory']
                retrieved_productcategory = self.productcategory_repo.get_product_category(
                    entity_for_get.category_name, entity_for_get.product_id
                )

                if retrieved_productcategory:
                    print(f'✅ Retrieved: {retrieved_productcategory}')
                else:
                    print('❌ Failed to retrieve productcategory')
            except Exception as e:
                print(f'❌ Failed to retrieve productcategory: {e}')

        print('🎯 ProductCategory CRUD cycle completed!')

        # ProductReview example
        print('\n--- ProductReview ---')

        # 1. CREATE - Create sample productreview
        sample_productreview = ProductReview(
            product_id='prod-11111',
            review_id='review-22222',
            user_id='user-12345',
            rating=5,
            title='Excellent headphones!',
            comment='Great sound quality and comfortable to wear for long periods.',
            created_at='2024-01-18T16:45:00Z',
            verified_purchase=True,
        )

        print('📝 Creating productreview...')
        print(f'📝 PK: {sample_productreview.pk()}, SK: {sample_productreview.sk()}')

        try:
            created_productreview = self.productreview_repo.create_product_review(
                sample_productreview
            )
            print(f'✅ Created: {created_productreview}')
            # Store created entity for access pattern testing
            created_entities['ProductReview'] = created_productreview
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  productreview already exists, retrieving existing entity...')
                try:
                    existing_productreview = self.productreview_repo.get_product_review(
                        sample_productreview.product_id, sample_productreview.review_id
                    )

                    if existing_productreview:
                        print(f'✅ Retrieved existing: {existing_productreview}')
                        # Store existing entity for access pattern testing
                        created_entities['ProductReview'] = existing_productreview
                    else:
                        print('❌ Failed to retrieve existing productreview')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing productreview: {get_error}')
            else:
                print(f'❌ Failed to create productreview: {e}')
        # 2. UPDATE - Update non-key field (rating)
        if 'ProductReview' in created_entities:
            print('\n🔄 Updating rating field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['ProductReview']
                refreshed_entity = self.productreview_repo.get_product_review(
                    entity_for_refresh.product_id, entity_for_refresh.review_id
                )

                if refreshed_entity:
                    original_value = refreshed_entity.rating
                    refreshed_entity.rating = 4

                    updated_productreview = self.productreview_repo.update_product_review(
                        refreshed_entity
                    )
                    print(f'✅ Updated rating: {original_value} → {updated_productreview.rating}')

                    # Update stored entity with updated values
                    created_entities['ProductReview'] = updated_productreview
                else:
                    print('❌ Could not refresh productreview for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  productreview was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update productreview: {e}')

        # 3. GET - Retrieve and print the entity
        if 'ProductReview' in created_entities:
            print('\n🔍 Retrieving productreview...')
            try:
                entity_for_get = created_entities['ProductReview']
                retrieved_productreview = self.productreview_repo.get_product_review(
                    entity_for_get.product_id, entity_for_get.review_id
                )

                if retrieved_productreview:
                    print(f'✅ Retrieved: {retrieved_productreview}')
                else:
                    print('❌ Failed to retrieve productreview')
            except Exception as e:
                print(f'❌ Failed to retrieve productreview: {e}')

        print('🎯 ProductReview CRUD cycle completed!')
        print('\n=== OrderTable Table Operations ===')

        # Order example
        print('\n--- Order ---')

        # 1. CREATE - Create sample order
        sample_order = Order(
            order_id='order-33333',
            user_id='user-12345',
            order_date='sample_order_date',
            status='processing',
            total_amount=Decimal('199.99'),
            currency='sample_currency',
            shipping_address={'value': '123 Main Street, New York, NY 10001'},
            billing_address={'key': 'value'},
            payment_method='credit_card',
            shipping_method='sample_shipping_method',
            tracking_number='sample_tracking_number',
            estimated_delivery='sample_estimated_delivery',
            created_at='2024-01-20T11:30:00Z',
            updated_at='2024-01-20T11:30:00Z',
        )

        print('📝 Creating order...')
        print(f'📝 PK: {sample_order.pk()}, SK: {sample_order.sk()}')

        try:
            created_order = self.order_repo.create_order(sample_order)
            print(f'✅ Created: {created_order}')
            # Store created entity for access pattern testing
            created_entities['Order'] = created_order
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  order already exists, retrieving existing entity...')
                try:
                    existing_order = self.order_repo.get_order(sample_order.order_id)

                    if existing_order:
                        print(f'✅ Retrieved existing: {existing_order}')
                        # Store existing entity for access pattern testing
                        created_entities['Order'] = existing_order
                    else:
                        print('❌ Failed to retrieve existing order')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing order: {get_error}')
            else:
                print(f'❌ Failed to create order: {e}')
        # 2. UPDATE - Update non-key field (status)
        if 'Order' in created_entities:
            print('\n🔄 Updating status field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['Order']
                refreshed_entity = self.order_repo.get_order(entity_for_refresh.order_id)

                if refreshed_entity:
                    original_value = refreshed_entity.status
                    refreshed_entity.status = 'shipped'

                    updated_order = self.order_repo.update_order(refreshed_entity)
                    print(f'✅ Updated status: {original_value} → {updated_order.status}')

                    # Update stored entity with updated values
                    created_entities['Order'] = updated_order
                else:
                    print('❌ Could not refresh order for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(f'⚠️  order was modified by another process (optimistic locking): {e}')
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update order: {e}')

        # 3. GET - Retrieve and print the entity
        if 'Order' in created_entities:
            print('\n🔍 Retrieving order...')
            try:
                entity_for_get = created_entities['Order']
                retrieved_order = self.order_repo.get_order(entity_for_get.order_id)

                if retrieved_order:
                    print(f'✅ Retrieved: {retrieved_order}')
                else:
                    print('❌ Failed to retrieve order')
            except Exception as e:
                print(f'❌ Failed to retrieve order: {e}')

        print('🎯 Order CRUD cycle completed!')

        # OrderItem example
        print('\n--- OrderItem ---')

        # 1. CREATE - Create sample orderitem
        sample_orderitem = OrderItem(
            order_id='order-33333',
            product_id='prod-11111',
            product_name='Wireless Bluetooth Headphones',
            sku='sample_sku',
            quantity=1,
            unit_price=Decimal('199.99'),
            total_price=Decimal('199.99'),
            currency='sample_currency',
        )

        print('📝 Creating orderitem...')
        print(f'📝 PK: {sample_orderitem.pk()}, SK: {sample_orderitem.sk()}')

        try:
            created_orderitem = self.orderitem_repo.create_order_item(sample_orderitem)
            print(f'✅ Created: {created_orderitem}')
            # Store created entity for access pattern testing
            created_entities['OrderItem'] = created_orderitem
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  orderitem already exists, retrieving existing entity...')
                try:
                    existing_orderitem = self.orderitem_repo.get_order_item(
                        sample_orderitem.order_id, sample_orderitem.product_id
                    )

                    if existing_orderitem:
                        print(f'✅ Retrieved existing: {existing_orderitem}')
                        # Store existing entity for access pattern testing
                        created_entities['OrderItem'] = existing_orderitem
                    else:
                        print('❌ Failed to retrieve existing orderitem')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing orderitem: {get_error}')
            else:
                print(f'❌ Failed to create orderitem: {e}')
        # 2. UPDATE - Update non-key field (quantity)
        if 'OrderItem' in created_entities:
            print('\n🔄 Updating quantity field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['OrderItem']
                refreshed_entity = self.orderitem_repo.get_order_item(
                    entity_for_refresh.order_id, entity_for_refresh.product_id
                )

                if refreshed_entity:
                    original_value = refreshed_entity.quantity
                    refreshed_entity.quantity = 2

                    updated_orderitem = self.orderitem_repo.update_order_item(refreshed_entity)
                    print(f'✅ Updated quantity: {original_value} → {updated_orderitem.quantity}')

                    # Update stored entity with updated values
                    created_entities['OrderItem'] = updated_orderitem
                else:
                    print('❌ Could not refresh orderitem for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  orderitem was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update orderitem: {e}')

        # 3. GET - Retrieve and print the entity
        if 'OrderItem' in created_entities:
            print('\n🔍 Retrieving orderitem...')
            try:
                entity_for_get = created_entities['OrderItem']
                retrieved_orderitem = self.orderitem_repo.get_order_item(
                    entity_for_get.order_id, entity_for_get.product_id
                )

                if retrieved_orderitem:
                    print(f'✅ Retrieved: {retrieved_orderitem}')
                else:
                    print('❌ Failed to retrieve orderitem')
            except Exception as e:
                print(f'❌ Failed to retrieve orderitem: {e}')

        print('🎯 OrderItem CRUD cycle completed!')

        # UserOrderHistory example
        print('\n--- UserOrderHistory ---')

        # 1. CREATE - Create sample userorderhistory
        sample_userorderhistory = UserOrderHistory(
            user_id='user-12345',
            order_id='order-33333',
            order_date='2024-01-20',
            status='processing',
            total_amount=Decimal('199.99'),
            currency='sample_currency',
            item_count=1,
        )

        print('📝 Creating userorderhistory...')
        print(f'📝 PK: {sample_userorderhistory.pk()}, SK: {sample_userorderhistory.sk()}')

        try:
            created_userorderhistory = self.userorderhistory_repo.create_user_order_history(
                sample_userorderhistory
            )
            print(f'✅ Created: {created_userorderhistory}')
            # Store created entity for access pattern testing
            created_entities['UserOrderHistory'] = created_userorderhistory
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  userorderhistory already exists, retrieving existing entity...')
                try:
                    existing_userorderhistory = self.userorderhistory_repo.get_user_order_history(
                        sample_userorderhistory.user_id,
                        sample_userorderhistory.order_date,
                        sample_userorderhistory.order_id,
                    )

                    if existing_userorderhistory:
                        print(f'✅ Retrieved existing: {existing_userorderhistory}')
                        # Store existing entity for access pattern testing
                        created_entities['UserOrderHistory'] = existing_userorderhistory
                    else:
                        print('❌ Failed to retrieve existing userorderhistory')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing userorderhistory: {get_error}')
            else:
                print(f'❌ Failed to create userorderhistory: {e}')
        # 2. UPDATE - Update non-key field (status)
        if 'UserOrderHistory' in created_entities:
            print('\n🔄 Updating status field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['UserOrderHistory']
                refreshed_entity = self.userorderhistory_repo.get_user_order_history(
                    entity_for_refresh.user_id,
                    entity_for_refresh.order_date,
                    entity_for_refresh.order_id,
                )

                if refreshed_entity:
                    original_value = refreshed_entity.status
                    refreshed_entity.status = 'shipped'

                    updated_userorderhistory = (
                        self.userorderhistory_repo.update_user_order_history(refreshed_entity)
                    )
                    print(
                        f'✅ Updated status: {original_value} → {updated_userorderhistory.status}'
                    )

                    # Update stored entity with updated values
                    created_entities['UserOrderHistory'] = updated_userorderhistory
                else:
                    print('❌ Could not refresh userorderhistory for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  userorderhistory was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update userorderhistory: {e}')

        # 3. GET - Retrieve and print the entity
        if 'UserOrderHistory' in created_entities:
            print('\n🔍 Retrieving userorderhistory...')
            try:
                entity_for_get = created_entities['UserOrderHistory']
                retrieved_userorderhistory = self.userorderhistory_repo.get_user_order_history(
                    entity_for_get.user_id, entity_for_get.order_date, entity_for_get.order_id
                )

                if retrieved_userorderhistory:
                    print(f'✅ Retrieved: {retrieved_userorderhistory}')
                else:
                    print('❌ Failed to retrieve userorderhistory')
            except Exception as e:
                print(f'❌ Failed to retrieve userorderhistory: {e}')

        print('🎯 UserOrderHistory CRUD cycle completed!')

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

        # Delete UserAddress
        if 'UserAddress' in created_entities:
            print('\n🗑️  Deleting useraddress...')
            try:
                deleted = self.useraddress_repo.delete_user_address(
                    created_entities['UserAddress'].user_id,
                    created_entities['UserAddress'].address_id,
                )

                if deleted:
                    print('✅ Deleted useraddress successfully')
                else:
                    print('❌ Failed to delete useraddress (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete useraddress: {e}')

        # Delete Product
        if 'Product' in created_entities:
            print('\n🗑️  Deleting product...')
            try:
                deleted = self.product_repo.delete_product(created_entities['Product'].product_id)

                if deleted:
                    print('✅ Deleted product successfully')
                else:
                    print('❌ Failed to delete product (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete product: {e}')

        # Delete ProductCategory
        if 'ProductCategory' in created_entities:
            print('\n🗑️  Deleting productcategory...')
            try:
                deleted = self.productcategory_repo.delete_product_category(
                    created_entities['ProductCategory'].category_name,
                    created_entities['ProductCategory'].product_id,
                )

                if deleted:
                    print('✅ Deleted productcategory successfully')
                else:
                    print('❌ Failed to delete productcategory (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete productcategory: {e}')

        # Delete ProductReview
        if 'ProductReview' in created_entities:
            print('\n🗑️  Deleting productreview...')
            try:
                deleted = self.productreview_repo.delete_product_review(
                    created_entities['ProductReview'].product_id,
                    created_entities['ProductReview'].review_id,
                )

                if deleted:
                    print('✅ Deleted productreview successfully')
                else:
                    print('❌ Failed to delete productreview (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete productreview: {e}')

        # Delete Order
        if 'Order' in created_entities:
            print('\n🗑️  Deleting order...')
            try:
                deleted = self.order_repo.delete_order(created_entities['Order'].order_id)

                if deleted:
                    print('✅ Deleted order successfully')
                else:
                    print('❌ Failed to delete order (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete order: {e}')

        # Delete OrderItem
        if 'OrderItem' in created_entities:
            print('\n🗑️  Deleting orderitem...')
            try:
                deleted = self.orderitem_repo.delete_order_item(
                    created_entities['OrderItem'].order_id,
                    created_entities['OrderItem'].product_id,
                )

                if deleted:
                    print('✅ Deleted orderitem successfully')
                else:
                    print('❌ Failed to delete orderitem (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete orderitem: {e}')

        # Delete UserOrderHistory
        if 'UserOrderHistory' in created_entities:
            print('\n🗑️  Deleting userorderhistory...')
            try:
                deleted = self.userorderhistory_repo.delete_user_order_history(
                    created_entities['UserOrderHistory'].user_id,
                    created_entities['UserOrderHistory'].order_date,
                    created_entities['UserOrderHistory'].order_id,
                )

                if deleted:
                    print('✅ Deleted userorderhistory successfully')
                else:
                    print('❌ Failed to delete userorderhistory (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete userorderhistory: {e}')
        print('\n💡 Requirements:')
        print("   - DynamoDB table 'UserTable' must exist")
        print("   - DynamoDB table 'ProductTable' must exist")
        print("   - DynamoDB table 'OrderTable' must exist")
        print('   - DynamoDB permissions: GetItem, PutItem, UpdateItem, DeleteItem')

    def _test_additional_access_patterns(self, created_entities: dict):
        """Test additional access patterns beyond basic CRUD"""
        print('\n' + '=' * 60)
        print('🔍 Additional Access Pattern Testing')
        print('=' * 60)
        print()

        # User
        # Access Pattern #1: Get user profile by user ID
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #1: Get user profile by user ID')
            print('   Using Main Table')
            result = self.user_repo.get_user(created_entities['User'].user_id)
            print('   ✅ Get user profile by user ID completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #1: {e}')

        # Access Pattern #2: Create new user account
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #2: Create new user account')
            print('   Using Main Table')
            test_entity = User(
                user_id='user-98765',
                email='sarah.johnson@gmail.com',
                first_name='Sarah',
                last_name='Johnson',
                phone='+1-555-0456',
                created_at='2024-01-08T14:22:00Z',
                status='premium',
            )
            result = self.user_repo.put_user(test_entity)
            print('   ✅ Create new user account completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #2: {e}')

        # Access Pattern #3: Update user profile information
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #3: Update user profile information')
            print('   Using Main Table')
            result = self.user_repo.update_user_profile(
                created_entities['User'].user_id, created_entities['User'].email
            )
            print('   ✅ Update user profile information completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #3: {e}')

        # UserAddress
        # Access Pattern #4: Get all addresses for a user
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #4: Get all addresses for a user')
            print('   Using Main Table')
            result = self.useraddress_repo.get_user_addresses(
                created_entities['UserAddress'].user_id
            )
            print('   ✅ Get all addresses for a user completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #4: {e}')

        # Access Pattern #5: Add new address for user
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #5: Add new address for user')
            print('   Using Main Table')
            test_entity = UserAddress(
                user_id='user-98765',
                address_id='addr-54321',
                address_type='billing',
                street_address='789 Pine Street, Apt 4B',
                city='San Francisco',
                state='CA',
                postal_code='94102',
                country='USA',
                is_default=False,
            )
            result = self.useraddress_repo.add_user_address(test_entity)
            print('   ✅ Add new address for user completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #5: {e}')

        # Product
        # Access Pattern #6: Get product details by product ID
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #6: Get product details by product ID')
            print('   Using Main Table')
            result = self.product_repo.get_product(created_entities['Product'].product_id)
            print('   ✅ Get product details by product ID completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #6: {e}')

        # Access Pattern #7: Create new product
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #7: Create new product')
            print('   Using Main Table')
            test_entity = Product(
                product_id='prod-77777',
                name='Smart Fitness Watch',
                description='Advanced fitness tracker with heart rate monitoring, GPS, and 7-day battery life',
                category='Wearables',
                brand='FitTech',
                price=Decimal('299.99'),
                currency='sample_currency',
                stock_quantity=25,
                sku='FT-SFW-002',
                weight=Decimal('3.14'),
                dimensions={'key': 'value'},
                created_at='2024-01-05T12:30:00Z',
                updated_at='sample_updated_at',
                status='active',
            )
            result = self.product_repo.put_product(test_entity)
            print('   ✅ Create new product completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #7: {e}')

        # Access Pattern #8: Update product stock quantity
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #8: Update product stock quantity')
            print('   Using Main Table')
            result = self.product_repo.update_product_stock(
                created_entities['Product'].product_id, created_entities['Product'].stock_quantity
            )
            print('   ✅ Update product stock quantity completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #8: {e}')

        # ProductCategory
        # Access Pattern #9: Get all products in a specific category
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #9: Get all products in a specific category')
            print('   Using Main Table')
            result = self.productcategory_repo.get_products_by_category(
                created_entities['ProductCategory'].category_name
            )
            print('   ✅ Get all products in a specific category completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #9: {e}')

        # Access Pattern #10: Add product to category index
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #10: Add product to category index')
            print('   Using Main Table')
            test_entity = ProductCategory(
                category_name='Wearables',
                product_id='prod-77777',
                product_name='Smart Fitness Watch',
                price=Decimal('299.99'),
                stock_quantity=25,
            )
            result = self.productcategory_repo.add_product_to_category(test_entity)
            print('   ✅ Add product to category index completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #10: {e}')

        # Access Pattern #24: Get category products after a specific product_id (Main Table Range Query)
        # Index: Main Table
        # Range Condition: >
        try:
            print(
                '🔍 Testing Access Pattern #24: Get category products after a specific product_id (Main Table Range Query)'
            )
            print('   Using Main Table')
            print('   Range Condition: >')
            result = self.productcategory_repo.get_category_products_after_id(
                created_entities['ProductCategory'].category_name, 'after_product_id_value'
            )
            print(
                '   ✅ Get category products after a specific product_id (Main Table Range Query) completed'
            )
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #24: {e}')

        # ProductReview
        # Access Pattern #11: Get all reviews for a product
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #11: Get all reviews for a product')
            print('   Using Main Table')
            result = self.productreview_repo.get_product_reviews(
                created_entities['ProductReview'].product_id
            )
            print('   ✅ Get all reviews for a product completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #11: {e}')

        # Access Pattern #12: Create new product review with user reference
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #12: Create new product review with user reference')
            print('   Using Main Table')
            test_entity = ProductReview(
                product_id='prod-77777',
                review_id='review-88888',
                user_id='user-98765',
                rating=4,
                title='Great fitness tracker',
                comment='Love the GPS accuracy and battery life. The heart rate monitor is very reliable during workouts.',
                created_at='2024-01-12T09:20:00Z',
                verified_purchase=True,
            )
            result = self.productreview_repo.put_product_review(test_entity)
            print('   ✅ Create new product review with user reference completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #12: {e}')

        # Access Pattern #23: Get product reviews by review_id prefix (Main Table Range Query)
        # Index: Main Table
        # Range Condition: begins_with
        try:
            print(
                '🔍 Testing Access Pattern #23: Get product reviews by review_id prefix (Main Table Range Query)'
            )
            print('   Using Main Table')
            print('   Range Condition: begins_with')
            result = self.productreview_repo.get_product_reviews_by_id_prefix(
                created_entities['ProductReview'].product_id, 'review_id_prefix_value'
            )
            print(
                '   ✅ Get product reviews by review_id prefix (Main Table Range Query) completed'
            )
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #23: {e}')

        # Order
        # Access Pattern #13: Get order details by order ID
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #13: Get order details by order ID')
            print('   Using Main Table')
            result = self.order_repo.get_order(created_entities['Order'].order_id)
            print('   ✅ Get order details by order ID completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #13: {e}')

        # Access Pattern #14: Create new order with user reference
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #14: Create new order with user reference')
            print('   Using Main Table')
            test_entity = Order(
                order_id='order-66666',
                user_id='user-98765',
                order_date='sample_order_date',
                status='delivered',
                total_amount=Decimal('349.98'),
                currency='sample_currency',
                shipping_address={'value': '789 Pine Street, Apt 4B, San Francisco, CA 94102'},
                billing_address={'key': 'value'},
                payment_method='paypal',
                shipping_method='sample_shipping_method',
                tracking_number='sample_tracking_number',
                estimated_delivery='sample_estimated_delivery',
                created_at='2024-01-16T15:45:00Z',
                updated_at='2024-01-19T10:30:00Z',
            )
            result = self.order_repo.put_order(test_entity)
            print('   ✅ Create new order with user reference completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #14: {e}')

        # Access Pattern #15: Update order status and tracking information
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #15: Update order status and tracking information')
            print('   Using Main Table')
            result = self.order_repo.update_order_status(
                created_entities['Order'].order_id,
                created_entities['Order'].status,
                created_entities['Order'].tracking_number,
            )
            print('   ✅ Update order status and tracking information completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #15: {e}')

        # OrderItem
        # Access Pattern #16: Get all items for an order
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #16: Get all items for an order')
            print('   Using Main Table')
            result = self.orderitem_repo.get_order_items(created_entities['OrderItem'].order_id)
            print('   ✅ Get all items for an order completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #16: {e}')

        # Access Pattern #17: Add item to order with product reference
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #17: Add item to order with product reference')
            print('   Using Main Table')
            test_entity = OrderItem(
                order_id='order-66666',
                product_id='prod-77777',
                product_name='Smart Fitness Watch',
                sku='sample_sku',
                quantity=1,
                unit_price=Decimal('299.99'),
                total_price=Decimal('299.99'),
                currency='sample_currency',
            )
            result = self.orderitem_repo.add_order_item(test_entity)
            print('   ✅ Add item to order with product reference completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #17: {e}')

        # UserOrderHistory
        # Access Pattern #18: Get order history for a user (sorted by date)
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #18: Get order history for a user (sorted by date)')
            print('   Using Main Table')
            result = self.userorderhistory_repo.get_user_order_history_list(
                created_entities['UserOrderHistory'].user_id
            )
            print('   ✅ Get order history for a user (sorted by date) completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #18: {e}')

        # Access Pattern #19: Get recent orders for a user with date range
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #19: Get recent orders for a user with date range')
            print('   Using Main Table')
            result = self.userorderhistory_repo.get_user_recent_orders(
                created_entities['UserOrderHistory'].user_id, '2024-01-01', '2024-12-31'
            )
            print('   ✅ Get recent orders for a user with date range completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #19: {e}')

        # Access Pattern #20: Add order to user's order history with cross-table references
        # Index: Main Table
        try:
            print(
                "🔍 Testing Access Pattern #20: Add order to user's order history with cross-table references"
            )
            print('   Using Main Table')
            test_entity = UserOrderHistory(
                user_id='user-98765',
                order_id='order-66666',
                order_date='2024-01-16',
                status='delivered',
                total_amount=Decimal('349.98'),
                currency='sample_currency',
                item_count=2,
            )
            result = self.userorderhistory_repo.add_order_to_user_history(test_entity)
            print("   ✅ Add order to user's order history with cross-table references completed")
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #20: {e}')

        # Access Pattern #21: Get user orders after a specific date (Main Table Range Query)
        # Index: Main Table
        # Range Condition: >=
        try:
            print(
                '🔍 Testing Access Pattern #21: Get user orders after a specific date (Main Table Range Query)'
            )
            print('   Using Main Table')
            print('   Range Condition: >=')
            result = self.userorderhistory_repo.get_user_orders_after_date(
                created_entities['UserOrderHistory'].user_id, '2024-01-01'
            )
            print('   ✅ Get user orders after a specific date (Main Table Range Query) completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #21: {e}')

        # Access Pattern #22: Get user orders within date range (Main Table Range Query)
        # Index: Main Table
        # Range Condition: between
        try:
            print(
                '🔍 Testing Access Pattern #22: Get user orders within date range (Main Table Range Query)'
            )
            print('   Using Main Table')
            print('   Range Condition: between')
            result = self.userorderhistory_repo.get_user_orders_in_date_range(
                created_entities['UserOrderHistory'].user_id, '2024-01-01', '2024-12-31'
            )
            print('   ✅ Get user orders within date range (Main Table Range Query) completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #22: {e}')

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
    print('   - UserTable')
    print('   - ProductTable')
    print('   - OrderTable')

    if include_additional_access_patterns:
        print('🔍 Including additional access pattern examples')

    examples = UsageExamples()
    examples.run_examples(include_additional_access_patterns=include_additional_access_patterns)


if __name__ == '__main__':
    main()
