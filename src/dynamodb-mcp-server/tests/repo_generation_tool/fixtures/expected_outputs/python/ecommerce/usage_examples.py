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
        self.user_repo = UserRepository('UserTable')
        self.useraddress_repo = UserAddressRepository('UserTable')
        # ProductTable table repositories
        self.product_repo = ProductRepository('ProductTable')
        self.productcategory_repo = ProductCategoryRepository('ProductTable')
        self.productreview_repo = ProductReviewRepository('ProductTable')
        # OrderTable table repositories
        self.order_repo = OrderRepository('OrderTable')
        self.orderitem_repo = OrderItemRepository('OrderTable')
        self.userorderhistory_repo = UserOrderHistoryRepository('OrderTable')

    def run_examples(self, include_additional_access_patterns: bool = False):
        """Run CRUD examples for all entities"""
        # Dictionary to store created entities for access pattern testing
        created_entities = {}

        print('Running Repository Examples')
        print('=' * 50)
        print('\n=== UserTable Table Operations ===')

        # User example
        print('\n--- User ---')

        # 1. CREATE - Create sample user
        sample_user = User(
            user_id='user_id123',
            email='sample_email',
            first_name='sample_first_name',
            last_name='sample_last_name',
            phone='sample_phone',
            created_at='sample_created_at',
            status='active',
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

        # UserAddress example
        print('\n--- UserAddress ---')

        # 1. CREATE - Create sample useraddress
        sample_useraddress = UserAddress(
            user_id='user_id123',
            address_id='address_id123',
            address_type='sample_address_type',
            street_address='sample_street_address',
            city='Seattle',
            state='sample_state',
            postal_code='sample_postal_code',
            country='US',
            is_default=True,
        )

        print('📝 Creating useraddress...')
        print(f'📝 PK: {sample_useraddress.pk()}, SK: {sample_useraddress.sk()}')

        created_useraddress = self.useraddress_repo.create_user_address(sample_useraddress)
        print(f'✅ Created: {created_useraddress}')

        # Store created entity for access pattern testing
        created_entities['UserAddress'] = created_useraddress
        # 2. UPDATE - Update non-key field (address_type)
        print('\n🔄 Updating address_type field...')
        original_value = created_useraddress.address_type
        created_useraddress.address_type = 'updated_address_type'

        updated_useraddress = self.useraddress_repo.update_user_address(created_useraddress)
        print(f'✅ Updated address_type: {original_value} → {updated_useraddress.address_type}')

        # Update stored entity with updated values
        created_entities['UserAddress'] = updated_useraddress

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving useraddress...')
        retrieved_useraddress = self.useraddress_repo.get_user_address(
            created_useraddress.user_id, created_useraddress.address_id
        )

        if retrieved_useraddress:
            print(f'✅ Retrieved: {retrieved_useraddress}')
        else:
            print('❌ Failed to retrieve useraddress')

        print('🎯 UserAddress CRUD cycle completed successfully!')
        print('\n=== ProductTable Table Operations ===')

        # Product example
        print('\n--- Product ---')

        # 1. CREATE - Create sample product
        sample_product = Product(
            product_id='product_id123',
            name='sample_name',
            description='sample_description',
            category='electronics',
            brand='sample_brand',
            price=Decimal('29.99'),
            currency='sample_currency',
            stock_quantity=42,
            sku='sample_sku',
            weight=Decimal('3.14'),
            dimensions={'key': 'value'},
            created_at='sample_created_at',
            updated_at='sample_updated_at',
            status='active',
        )

        print('📝 Creating product...')
        print(f'📝 PK: {sample_product.pk()}, SK: {sample_product.sk()}')

        created_product = self.product_repo.create_product(sample_product)
        print(f'✅ Created: {created_product}')

        # Store created entity for access pattern testing
        created_entities['Product'] = created_product
        # 2. UPDATE - Update non-key field (name)
        print('\n🔄 Updating name field...')
        original_value = created_product.name
        created_product.name = 'updated_name'

        updated_product = self.product_repo.update_product(created_product)
        print(f'✅ Updated name: {original_value} → {updated_product.name}')

        # Update stored entity with updated values
        created_entities['Product'] = updated_product

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving product...')
        retrieved_product = self.product_repo.get_product(created_product.product_id)

        if retrieved_product:
            print(f'✅ Retrieved: {retrieved_product}')
        else:
            print('❌ Failed to retrieve product')

        print('🎯 Product CRUD cycle completed successfully!')

        # ProductCategory example
        print('\n--- ProductCategory ---')

        # 1. CREATE - Create sample productcategory
        sample_productcategory = ProductCategory(
            category_name='electronics',
            product_id='product_id123',
            product_name='sample_product_name',
            price=Decimal('29.99'),
            stock_quantity=42,
        )

        print('📝 Creating productcategory...')
        print(f'📝 PK: {sample_productcategory.pk()}, SK: {sample_productcategory.sk()}')

        created_productcategory = self.productcategory_repo.create_product_category(
            sample_productcategory
        )
        print(f'✅ Created: {created_productcategory}')

        # Store created entity for access pattern testing
        created_entities['ProductCategory'] = created_productcategory
        # 2. UPDATE - Update non-key field (product_name)
        print('\n🔄 Updating product_name field...')
        original_value = created_productcategory.product_name
        created_productcategory.product_name = 'updated_product_name'

        updated_productcategory = self.productcategory_repo.update_product_category(
            created_productcategory
        )
        print(
            f'✅ Updated product_name: {original_value} → {updated_productcategory.product_name}'
        )

        # Update stored entity with updated values
        created_entities['ProductCategory'] = updated_productcategory

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving productcategory...')
        retrieved_productcategory = self.productcategory_repo.get_product_category(
            created_productcategory.category_name, created_productcategory.product_id
        )

        if retrieved_productcategory:
            print(f'✅ Retrieved: {retrieved_productcategory}')
        else:
            print('❌ Failed to retrieve productcategory')

        print('🎯 ProductCategory CRUD cycle completed successfully!')

        # ProductReview example
        print('\n--- ProductReview ---')

        # 1. CREATE - Create sample productreview
        sample_productreview = ProductReview(
            product_id='product_id123',
            review_id='review_id123',
            user_id='user_id123',
            rating=42,
            title='sample_title',
            comment='sample_comment',
            created_at='sample_created_at',
            verified_purchase=True,
        )

        print('📝 Creating productreview...')
        print(f'📝 PK: {sample_productreview.pk()}, SK: {sample_productreview.sk()}')

        created_productreview = self.productreview_repo.create_product_review(sample_productreview)
        print(f'✅ Created: {created_productreview}')

        # Store created entity for access pattern testing
        created_entities['ProductReview'] = created_productreview
        # 2. UPDATE - Update non-key field (user_id)
        print('\n🔄 Updating user_id field...')
        original_value = created_productreview.user_id
        created_productreview.user_id = 'updated_user_id'

        updated_productreview = self.productreview_repo.update_product_review(
            created_productreview
        )
        print(f'✅ Updated user_id: {original_value} → {updated_productreview.user_id}')

        # Update stored entity with updated values
        created_entities['ProductReview'] = updated_productreview

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving productreview...')
        retrieved_productreview = self.productreview_repo.get_product_review(
            created_productreview.product_id, created_productreview.review_id
        )

        if retrieved_productreview:
            print(f'✅ Retrieved: {retrieved_productreview}')
        else:
            print('❌ Failed to retrieve productreview')

        print('🎯 ProductReview CRUD cycle completed successfully!')
        print('\n=== OrderTable Table Operations ===')

        # Order example
        print('\n--- Order ---')

        # 1. CREATE - Create sample order
        sample_order = Order(
            order_id='order_id123',
            user_id='user_id123',
            order_date='sample_order_date',
            status='active',
            total_amount=Decimal('3.14'),
            currency='sample_currency',
            shipping_address={'key': 'value'},
            billing_address={'key': 'value'},
            payment_method='sample_payment_method',
            shipping_method='sample_shipping_method',
            tracking_number='sample_tracking_number',
            estimated_delivery='sample_estimated_delivery',
            created_at='sample_created_at',
            updated_at='sample_updated_at',
        )

        print('📝 Creating order...')
        print(f'📝 PK: {sample_order.pk()}, SK: {sample_order.sk()}')

        created_order = self.order_repo.create_order(sample_order)
        print(f'✅ Created: {created_order}')

        # Store created entity for access pattern testing
        created_entities['Order'] = created_order
        # 2. UPDATE - Update non-key field (user_id)
        print('\n🔄 Updating user_id field...')
        original_value = created_order.user_id
        created_order.user_id = 'updated_user_id'

        updated_order = self.order_repo.update_order(created_order)
        print(f'✅ Updated user_id: {original_value} → {updated_order.user_id}')

        # Update stored entity with updated values
        created_entities['Order'] = updated_order

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving order...')
        retrieved_order = self.order_repo.get_order(created_order.order_id)

        if retrieved_order:
            print(f'✅ Retrieved: {retrieved_order}')
        else:
            print('❌ Failed to retrieve order')

        print('🎯 Order CRUD cycle completed successfully!')

        # OrderItem example
        print('\n--- OrderItem ---')

        # 1. CREATE - Create sample orderitem
        sample_orderitem = OrderItem(
            order_id='order_id123',
            product_id='product_id123',
            product_name='sample_product_name',
            sku='sample_sku',
            quantity=42,
            unit_price=Decimal('29.99'),
            total_price=Decimal('29.99'),
            currency='sample_currency',
        )

        print('📝 Creating orderitem...')
        print(f'📝 PK: {sample_orderitem.pk()}, SK: {sample_orderitem.sk()}')

        created_orderitem = self.orderitem_repo.create_order_item(sample_orderitem)
        print(f'✅ Created: {created_orderitem}')

        # Store created entity for access pattern testing
        created_entities['OrderItem'] = created_orderitem
        # 2. UPDATE - Update non-key field (product_name)
        print('\n🔄 Updating product_name field...')
        original_value = created_orderitem.product_name
        created_orderitem.product_name = 'updated_product_name'

        updated_orderitem = self.orderitem_repo.update_order_item(created_orderitem)
        print(f'✅ Updated product_name: {original_value} → {updated_orderitem.product_name}')

        # Update stored entity with updated values
        created_entities['OrderItem'] = updated_orderitem

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving orderitem...')
        retrieved_orderitem = self.orderitem_repo.get_order_item(
            created_orderitem.order_id, created_orderitem.product_id
        )

        if retrieved_orderitem:
            print(f'✅ Retrieved: {retrieved_orderitem}')
        else:
            print('❌ Failed to retrieve orderitem')

        print('🎯 OrderItem CRUD cycle completed successfully!')

        # UserOrderHistory example
        print('\n--- UserOrderHistory ---')

        # 1. CREATE - Create sample userorderhistory
        sample_userorderhistory = UserOrderHistory(
            user_id='user_id123',
            order_id='order_id123',
            order_date='sample_order_date',
            status='active',
            total_amount=Decimal('3.14'),
            currency='sample_currency',
            item_count=42,
        )

        print('📝 Creating userorderhistory...')
        print(f'📝 PK: {sample_userorderhistory.pk()}, SK: {sample_userorderhistory.sk()}')

        created_userorderhistory = self.userorderhistory_repo.create_user_order_history(
            sample_userorderhistory
        )
        print(f'✅ Created: {created_userorderhistory}')

        # Store created entity for access pattern testing
        created_entities['UserOrderHistory'] = created_userorderhistory
        # 2. UPDATE - Update non-key field (status)
        print('\n🔄 Updating status field...')
        original_value = created_userorderhistory.status
        created_userorderhistory.status = 'updated_status'

        updated_userorderhistory = self.userorderhistory_repo.update_user_order_history(
            created_userorderhistory
        )
        print(f'✅ Updated status: {original_value} → {updated_userorderhistory.status}')

        # Update stored entity with updated values
        created_entities['UserOrderHistory'] = updated_userorderhistory

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving userorderhistory...')
        retrieved_userorderhistory = self.userorderhistory_repo.get_user_order_history(
            created_userorderhistory.user_id,
            created_userorderhistory.order_date,
            created_userorderhistory.order_id,
        )

        if retrieved_userorderhistory:
            print(f'✅ Retrieved: {retrieved_userorderhistory}')
        else:
            print('❌ Failed to retrieve userorderhistory')

        print('🎯 UserOrderHistory CRUD cycle completed successfully!')

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

        # Delete UserAddress
        if 'UserAddress' in created_entities:
            print('\n🗑️  Deleting useraddress...')
            deleted = self.useraddress_repo.delete_user_address(
                created_entities['UserAddress'].user_id, created_entities['UserAddress'].address_id
            )

            if deleted:
                print('✅ Deleted useraddress successfully')
            else:
                print('❌ Failed to delete useraddress')

        # Delete Product
        if 'Product' in created_entities:
            print('\n🗑️  Deleting product...')
            deleted = self.product_repo.delete_product(created_entities['Product'].product_id)

            if deleted:
                print('✅ Deleted product successfully')
            else:
                print('❌ Failed to delete product')

        # Delete ProductCategory
        if 'ProductCategory' in created_entities:
            print('\n🗑️  Deleting productcategory...')
            deleted = self.productcategory_repo.delete_product_category(
                created_entities['ProductCategory'].category_name,
                created_entities['ProductCategory'].product_id,
            )

            if deleted:
                print('✅ Deleted productcategory successfully')
            else:
                print('❌ Failed to delete productcategory')

        # Delete ProductReview
        if 'ProductReview' in created_entities:
            print('\n🗑️  Deleting productreview...')
            deleted = self.productreview_repo.delete_product_review(
                created_entities['ProductReview'].product_id,
                created_entities['ProductReview'].review_id,
            )

            if deleted:
                print('✅ Deleted productreview successfully')
            else:
                print('❌ Failed to delete productreview')

        # Delete Order
        if 'Order' in created_entities:
            print('\n🗑️  Deleting order...')
            deleted = self.order_repo.delete_order(created_entities['Order'].order_id)

            if deleted:
                print('✅ Deleted order successfully')
            else:
                print('❌ Failed to delete order')

        # Delete OrderItem
        if 'OrderItem' in created_entities:
            print('\n🗑️  Deleting orderitem...')
            deleted = self.orderitem_repo.delete_order_item(
                created_entities['OrderItem'].order_id, created_entities['OrderItem'].product_id
            )

            if deleted:
                print('✅ Deleted orderitem successfully')
            else:
                print('❌ Failed to delete orderitem')

        # Delete UserOrderHistory
        if 'UserOrderHistory' in created_entities:
            print('\n🗑️  Deleting userorderhistory...')
            deleted = self.userorderhistory_repo.delete_user_order_history(
                created_entities['UserOrderHistory'].user_id,
                created_entities['UserOrderHistory'].order_date,
                created_entities['UserOrderHistory'].order_id,
            )

            if deleted:
                print('✅ Deleted userorderhistory successfully')
            else:
                print('❌ Failed to delete userorderhistory')

        print('\n💡 Requirements:')
        print("   - DynamoDB table 'UserTable' must exist")
        print("   - DynamoDB table 'ProductTable' must exist")
        print("   - DynamoDB table 'OrderTable' must exist")
        print('   - DynamoDB permissions: GetItem, PutItem, UpdateItem, DeleteItem')

    def _test_additional_access_patterns(self, created_entities: dict):
        """Test additional access patterns beyond basic CRUD (commented out by default for manual implementation)"""
        print('\n' + '=' * 60)
        print('🔍 Additional Access Pattern Testing (Commented Out)')
        print('=' * 60)
        print('💡 Uncomment the lines below after implementing the additional access patterns')
        print()

        # User
        # Access Pattern #1: Get user profile by user ID
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #1: Get user profile by user ID")
        #     print("   Using Main Table")
        #     user_id = created_entities["User"].user_id
        #     self.user_repo.get_user(
        #         user_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #1: {e}")

        # Access Pattern #2: Create new user account
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #2: Create new user account")
        #     print("   Using Main Table")
        #     user = created_entities["User"]
        #     self.user_repo.create_user(
        #         user,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #2: {e}")

        # Access Pattern #3: Update user profile information
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #3: Update user profile information")
        #     print("   Using Main Table")
        #     user_id = created_entities["User"].user_id
        #     updates = ""
        #     # Determine appropriate update value based on entity fields
        #     update_value = "updated_email"
        #     self.user_repo.update_user_profile(
        #         user_id,
        #         updates,
        #         update_value,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #3: {e}")

        # UserAddress
        # Access Pattern #4: Get all addresses for a user
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #4: Get all addresses for a user")
        #     print("   Using Main Table")
        #     user_id = created_entities["UserAddress"].user_id
        #     self.useraddress_repo.get_user_addresses(
        #         user_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #4: {e}")

        # Access Pattern #5: Add new address for user
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #5: Add new address for user")
        #     print("   Using Main Table")
        #     address = created_entities["UserAddress"]
        #     self.useraddress_repo.add_user_address(
        #         address,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #5: {e}")

        # Product
        # Access Pattern #6: Get product details by product ID
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #6: Get product details by product ID")
        #     print("   Using Main Table")
        #     product_id = created_entities["Product"].product_id
        #     self.product_repo.get_product(
        #         product_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #6: {e}")

        # Access Pattern #7: Create new product
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #7: Create new product")
        #     print("   Using Main Table")
        #     product = created_entities["Product"]
        #     self.product_repo.create_product(
        #         product,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #7: {e}")

        # Access Pattern #8: Update product stock quantity
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #8: Update product stock quantity")
        #     print("   Using Main Table")
        #     product_id = created_entities["Product"].product_id
        #     quantity_change = ""
        #     # Determine appropriate update value based on entity fields
        #     update_value = "updated_product_id"
        #     self.product_repo.update_product_stock(
        #         product_id,
        #         quantity_change,
        #         update_value,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #8: {e}")

        # ProductCategory
        # Access Pattern #9: Get all products in a specific category
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #9: Get all products in a specific category")
        #     print("   Using Main Table")
        #     category_name = created_entities["ProductCategory"].category_name
        #     self.productcategory_repo.get_products_by_category(
        #         category_name,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #9: {e}")

        # Access Pattern #10: Add product to category index
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #10: Add product to category index")
        #     print("   Using Main Table")
        #     category_item = created_entities["ProductCategory"]
        #     self.productcategory_repo.add_product_to_category(
        #         category_item,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #10: {e}")

        # Access Pattern #24: Get category products after a specific product_id (Main Table Range Query)
        # Index: Main Table
        # Range Condition: >
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #24: Get category products after a specific product_id (Main Table Range Query)")
        #     print("   Using Main Table")
        #     print("   Range Condition: >")
        #     category_name = created_entities["ProductCategory"].category_name
        #     after_product_id = ""
        #     self.productcategory_repo.get_category_products_after_id(
        #         category_name,
        #         after_product_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #24: {e}")

        # ProductReview
        # Access Pattern #11: Get all reviews for a product
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #11: Get all reviews for a product")
        #     print("   Using Main Table")
        #     product_id = created_entities["ProductReview"].product_id
        #     self.productreview_repo.get_product_reviews(
        #         product_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #11: {e}")

        # Access Pattern #12: Create new product review with user reference
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #12: Create new product review with user reference")
        #     print("   Using Main Table")
        #     review = created_entities["ProductReview"]
        #     user = created_entities["User"]
        #     self.productreview_repo.create_product_review_with_refs(
        #         review,
        #         user,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #12: {e}")

        # Access Pattern #23: Get product reviews by review_id prefix (Main Table Range Query)
        # Index: Main Table
        # Range Condition: begins_with
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #23: Get product reviews by review_id prefix (Main Table Range Query)")
        #     print("   Using Main Table")
        #     print("   Range Condition: begins_with")
        #     product_id = created_entities["ProductReview"].product_id
        #     review_id_prefix = ""
        #     self.productreview_repo.get_product_reviews_by_id_prefix(
        #         product_id,
        #         review_id_prefix,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #23: {e}")

        # Order
        # Access Pattern #13: Get order details by order ID
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #13: Get order details by order ID")
        #     print("   Using Main Table")
        #     order_id = created_entities["Order"].order_id
        #     self.order_repo.get_order(
        #         order_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #13: {e}")

        # Access Pattern #14: Create new order with user reference
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #14: Create new order with user reference")
        #     print("   Using Main Table")
        #     order = created_entities["Order"]
        #     user = created_entities["User"]
        #     self.order_repo.create_order_with_refs(
        #         order,
        #         user,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #14: {e}")

        # Access Pattern #15: Update order status and tracking information
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #15: Update order status and tracking information")
        #     print("   Using Main Table")
        #     order_id = created_entities["Order"].order_id
        #     status = created_entities["Order"].status
        #     tracking_number = created_entities["Order"].tracking_number
        #     # Determine appropriate update value based on entity fields
        #     update_value = "updated_order_id"
        #     self.order_repo.update_order_status(
        #         order_id,
        #         status,
        #         tracking_number,
        #         update_value,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #15: {e}")

        # OrderItem
        # Access Pattern #16: Get all items for an order
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #16: Get all items for an order")
        #     print("   Using Main Table")
        #     order_id = created_entities["OrderItem"].order_id
        #     self.orderitem_repo.get_order_items(
        #         order_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #16: {e}")

        # Access Pattern #17: Add item to order with product reference
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #17: Add item to order with product reference")
        #     print("   Using Main Table")
        #     order_item = created_entities["OrderItem"]
        #     product = created_entities["Product"]
        #     self.orderitem_repo.add_order_item(
        #         order_item,
        #         product,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #17: {e}")

        # UserOrderHistory
        # Access Pattern #18: Get order history for a user (sorted by date)
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #18: Get order history for a user (sorted by date)")
        #     print("   Using Main Table")
        #     user_id = created_entities["UserOrderHistory"].user_id
        #     self.userorderhistory_repo.get_user_order_history_list(
        #         user_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #18: {e}")

        # Access Pattern #19: Get recent orders for a user with date range
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #19: Get recent orders for a user with date range")
        #     print("   Using Main Table")
        #     user_id = created_entities["UserOrderHistory"].user_id
        #     start_date = ""
        #     end_date = ""
        #     self.userorderhistory_repo.get_user_recent_orders(
        #         user_id,
        #         start_date,
        #         end_date,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #19: {e}")

        # Access Pattern #20: Add order to user's order history with cross-table references
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #20: Add order to user's order history with cross-table references")
        #     print("   Using Main Table")
        #     user_order = created_entities["UserOrderHistory"]
        #     user = created_entities["User"]
        #     order = created_entities["Order"]
        #     self.userorderhistory_repo.add_order_to_user_history(
        #         user_order,
        #         user,
        #         order,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #20: {e}")

        # Access Pattern #21: Get user orders after a specific date (Main Table Range Query)
        # Index: Main Table
        # Range Condition: >=
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #21: Get user orders after a specific date (Main Table Range Query)")
        #     print("   Using Main Table")
        #     print("   Range Condition: >=")
        #     user_id = created_entities["UserOrderHistory"].user_id
        #     since_date = ""
        #     self.userorderhistory_repo.get_user_orders_after_date(
        #         user_id,
        #         since_date,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #21: {e}")

        # Access Pattern #22: Get user orders within date range (Main Table Range Query)
        # Index: Main Table
        # Range Condition: between
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #22: Get user orders within date range (Main Table Range Query)")
        #     print("   Using Main Table")
        #     print("   Range Condition: between")
        #     user_id = created_entities["UserOrderHistory"].user_id
        #     start_date = ""
        #     end_date = ""
        #     self.userorderhistory_repo.get_user_orders_in_date_range(
        #         user_id,
        #         start_date,
        #         end_date,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #22: {e}")

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
    print('   - UserTable')
    print('   - ProductTable')
    print('   - OrderTable')

    if include_additional_access_patterns:
        print('🔍 Including additional access pattern examples (commented out)')

    examples = UsageExamples()
    examples.run_examples(include_additional_access_patterns=include_additional_access_patterns)


if __name__ == '__main__':
    main()
