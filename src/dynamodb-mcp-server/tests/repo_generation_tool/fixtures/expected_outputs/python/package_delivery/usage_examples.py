"""Generated usage examples for DynamoDB entities and repositories"""

from __future__ import annotations

import os
import sys
from decimal import Decimal

# Import generated entities and repositories
from entities import Courier, Product, Rating, Recipient, Shipment, WarehouseProfile
from repositories import (
    CourierRepository,
    ProductRepository,
    RatingRepository,
    RecipientRepository,
    ShipmentRepository,
    WarehouseProfileRepository,
)


class UsageExamples:
    """Examples of using the generated entities and repositories"""

    def __init__(self):
        """Initialize repositories with default table names from schema."""
        # Initialize repositories with their respective table names
        # Recipients table repositories
        try:
            self.recipient_repo = RecipientRepository('Recipients')
            print("✅ Initialized RecipientRepository for table 'Recipients'")
        except Exception as e:
            print(f'❌ Failed to initialize RecipientRepository: {e}')
            self.recipient_repo = None
        # Couriers table repositories
        try:
            self.courier_repo = CourierRepository('Couriers')
            print("✅ Initialized CourierRepository for table 'Couriers'")
        except Exception as e:
            print(f'❌ Failed to initialize CourierRepository: {e}')
            self.courier_repo = None
        # Warehouses table repositories
        try:
            self.product_repo = ProductRepository('Warehouses')
            print("✅ Initialized ProductRepository for table 'Warehouses'")
        except Exception as e:
            print(f'❌ Failed to initialize ProductRepository: {e}')
            self.product_repo = None
        try:
            self.rating_repo = RatingRepository('Warehouses')
            print("✅ Initialized RatingRepository for table 'Warehouses'")
        except Exception as e:
            print(f'❌ Failed to initialize RatingRepository: {e}')
            self.rating_repo = None
        try:
            self.warehouseprofile_repo = WarehouseProfileRepository('Warehouses')
            print("✅ Initialized WarehouseProfileRepository for table 'Warehouses'")
        except Exception as e:
            print(f'❌ Failed to initialize WarehouseProfileRepository: {e}')
            self.warehouseprofile_repo = None
        # Shipments table repositories
        try:
            self.shipment_repo = ShipmentRepository('Shipments')
            print("✅ Initialized ShipmentRepository for table 'Shipments'")
        except Exception as e:
            print(f'❌ Failed to initialize ShipmentRepository: {e}')
            self.shipment_repo = None

    def run_examples(self, include_additional_access_patterns: bool = False):
        """Run CRUD examples for all entities"""
        # Dictionary to store created entities for access pattern testing
        created_entities = {}

        # Step 0: Cleanup any leftover entities from previous runs (makes tests idempotent)
        print('🧹 Pre-test Cleanup: Removing any leftover entities from previous runs')
        print('=' * 50)
        # Try to delete Recipient (recipient_id)
        try:
            sample_recipient = Recipient(
                recipient_id='rcpt_7891',
                name='Sarah Connor',
                email='sarah@email.com',
                phone='+1-555-0789',
                city='Seattle',
                created_at='2026-02-01T09:00:00Z',
            )
            self.recipient_repo.delete_recipient(sample_recipient.recipient_id)
            print('   🗑️  Deleted leftover recipient (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete Courier (courier_id)
        try:
            sample_courier = Courier(
                courier_id='cour_7891',
                name='Mike Chen',
                email='mike@email.com',
                phone='+1-555-0788',
                city='Seattle',
                vehicle_type='motorcycle',
                created_at='2026-02-01T08:00:00Z',
            )
            self.courier_repo.delete_courier(sample_courier.courier_id)
            print('   🗑️  Deleted leftover courier (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete Product (warehouse_id, category, product_id)
        try:
            sample_product = Product(
                warehouse_id='wh_7891',
                sort_key='MENU#Electronics#prod_789',
                product_id='prod_789',
                category='Electronics',
                description='Wireless Headphones',
                price=Decimal('15.99'),
                available=True,
                city='Seattle',
            )
            self.product_repo.delete_product(
                sample_product.warehouse_id, sample_product.category, sample_product.product_id
            )
            print('   🗑️  Deleted leftover product (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete Rating (warehouse_id, created_at, rating_id)
        try:
            sample_rating = Rating(
                warehouse_id='wh_7891',
                sort_key='REVIEW#2026-02-19T16:00:00Z#rat_789',
                rating_id='rat_789',
                recipient_name='Sarah Connor',
                feedback='Excellent service and fast processing!',
                score=5,
                created_at='2026-02-19T16:00:00Z',
            )
            self.rating_repo.delete_rating(
                sample_rating.warehouse_id, sample_rating.created_at, sample_rating.rating_id
            )
            print('   🗑️  Deleted leftover rating (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete WarehouseProfile (warehouse_id)
        try:
            sample_warehouseprofile = WarehouseProfile(
                warehouse_id='wh_7891',
                sort_key='PROFILE',
                name='Metro Warehouse',
                address='500 Pine St',
                city='Seattle',
                category='Electronics',
                rating=Decimal('4.6'),
                processing_time=35,
                created_at='2026-02-01T00:00:00Z',
            )
            self.warehouseprofile_repo.delete_warehouse_profile(
                sample_warehouseprofile.warehouse_id
            )
            print('   🗑️  Deleted leftover warehouseprofile (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete Shipment (shipment_id)
        try:
            sample_shipment = Shipment(
                shipment_id='shp_7891',
                recipient_id='rcpt_7891',
                warehouse_id='wh_7891',
                warehouse_name='Metro Warehouse',
                recipient_name='Sarah Connor',
                status='DELIVERED',
                packages=[
                    {
                        'name': 'Wireless Headphones',
                        'product_id': 'prod_789',
                        'qty': 2,
                        'weight': Decimal('0.5'),
                    }
                ],
                total_weight=Decimal('1.0'),
                destination_address='100 Maple Ave',
                origin_address='500 Pine St',
                created_at='2026-02-19T14:00:00Z',
                updated_at='2026-02-19T15:00:00Z',
                courier_id='cour_7891',
                available_city='Seattle',
                active_delivery='sample_active_delivery',
            )
            self.shipment_repo.delete_shipment(sample_shipment.shipment_id)
            print('   🗑️  Deleted leftover shipment (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        print('✅ Pre-test cleanup completed\n')

        print('Running Repository Examples')
        print('=' * 50)
        print('\n=== Recipients Table Operations ===')

        # Recipient example
        print('\n--- Recipient ---')

        # 1. CREATE - Create sample recipient
        sample_recipient = Recipient(
            recipient_id='rcpt_7891',
            name='Sarah Connor',
            email='sarah@email.com',
            phone='+1-555-0789',
            city='Seattle',
            created_at='2026-02-01T09:00:00Z',
        )

        print('📝 Creating recipient...')
        print(f'📝 PK: {sample_recipient.pk()}, SK: {sample_recipient.sk()}')

        try:
            created_recipient = self.recipient_repo.create_recipient(sample_recipient)
            print(f'✅ Created: {created_recipient}')
            # Store created entity for access pattern testing
            created_entities['Recipient'] = created_recipient
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  recipient already exists, retrieving existing entity...')
                try:
                    existing_recipient = self.recipient_repo.get_recipient(
                        sample_recipient.recipient_id
                    )

                    if existing_recipient:
                        print(f'✅ Retrieved existing: {existing_recipient}')
                        # Store existing entity for access pattern testing
                        created_entities['Recipient'] = existing_recipient
                    else:
                        print('❌ Failed to retrieve existing recipient')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing recipient: {get_error}')
            else:
                print(f'❌ Failed to create recipient: {e}')
        # 2. UPDATE - Update non-key field (name)
        if 'Recipient' in created_entities:
            print('\n🔄 Updating name field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['Recipient']
                refreshed_entity = self.recipient_repo.get_recipient(
                    entity_for_refresh.recipient_id
                )

                if refreshed_entity:
                    original_value = refreshed_entity.name
                    refreshed_entity.name = 'Sarah Connor-Updated'

                    updated_recipient = self.recipient_repo.update_recipient(refreshed_entity)
                    print(f'✅ Updated name: {original_value} → {updated_recipient.name}')

                    # Update stored entity with updated values
                    created_entities['Recipient'] = updated_recipient
                else:
                    print('❌ Could not refresh recipient for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  recipient was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update recipient: {e}')

        # 3. GET - Retrieve and print the entity
        if 'Recipient' in created_entities:
            print('\n🔍 Retrieving recipient...')
            try:
                entity_for_get = created_entities['Recipient']
                retrieved_recipient = self.recipient_repo.get_recipient(
                    entity_for_get.recipient_id
                )

                if retrieved_recipient:
                    print(f'✅ Retrieved: {retrieved_recipient}')
                else:
                    print('❌ Failed to retrieve recipient')
            except Exception as e:
                print(f'❌ Failed to retrieve recipient: {e}')

        print('🎯 Recipient CRUD cycle completed!')
        print('\n=== Couriers Table Operations ===')

        # Courier example
        print('\n--- Courier ---')

        # 1. CREATE - Create sample courier
        sample_courier = Courier(
            courier_id='cour_7891',
            name='Mike Chen',
            email='mike@email.com',
            phone='+1-555-0788',
            city='Seattle',
            vehicle_type='motorcycle',
            created_at='2026-02-01T08:00:00Z',
        )

        print('📝 Creating courier...')
        print(f'📝 PK: {sample_courier.pk()}, SK: {sample_courier.sk()}')

        try:
            created_courier = self.courier_repo.create_courier(sample_courier)
            print(f'✅ Created: {created_courier}')
            # Store created entity for access pattern testing
            created_entities['Courier'] = created_courier
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  courier already exists, retrieving existing entity...')
                try:
                    existing_courier = self.courier_repo.get_courier(sample_courier.courier_id)

                    if existing_courier:
                        print(f'✅ Retrieved existing: {existing_courier}')
                        # Store existing entity for access pattern testing
                        created_entities['Courier'] = existing_courier
                    else:
                        print('❌ Failed to retrieve existing courier')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing courier: {get_error}')
            else:
                print(f'❌ Failed to create courier: {e}')
        # 2. UPDATE - Update non-key field (name)
        if 'Courier' in created_entities:
            print('\n🔄 Updating name field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['Courier']
                refreshed_entity = self.courier_repo.get_courier(entity_for_refresh.courier_id)

                if refreshed_entity:
                    original_value = refreshed_entity.name
                    refreshed_entity.name = 'Mike Chen-Updated'

                    updated_courier = self.courier_repo.update_courier(refreshed_entity)
                    print(f'✅ Updated name: {original_value} → {updated_courier.name}')

                    # Update stored entity with updated values
                    created_entities['Courier'] = updated_courier
                else:
                    print('❌ Could not refresh courier for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(f'⚠️  courier was modified by another process (optimistic locking): {e}')
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update courier: {e}')

        # 3. GET - Retrieve and print the entity
        if 'Courier' in created_entities:
            print('\n🔍 Retrieving courier...')
            try:
                entity_for_get = created_entities['Courier']
                retrieved_courier = self.courier_repo.get_courier(entity_for_get.courier_id)

                if retrieved_courier:
                    print(f'✅ Retrieved: {retrieved_courier}')
                else:
                    print('❌ Failed to retrieve courier')
            except Exception as e:
                print(f'❌ Failed to retrieve courier: {e}')

        print('🎯 Courier CRUD cycle completed!')
        print('\n=== Warehouses Table Operations ===')

        # Product example
        print('\n--- Product ---')

        # 1. CREATE - Create sample product
        sample_product = Product(
            warehouse_id='wh_7891',
            sort_key='MENU#Electronics#prod_789',
            product_id='prod_789',
            category='Electronics',
            description='Wireless Headphones',
            price=Decimal('15.99'),
            available=True,
            city='Seattle',
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
                    existing_product = self.product_repo.get_product(
                        sample_product.warehouse_id,
                        sample_product.category,
                        sample_product.product_id,
                    )

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
        # 2. UPDATE - Update non-key field (description)
        if 'Product' in created_entities:
            print('\n🔄 Updating description field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['Product']
                refreshed_entity = self.product_repo.get_product(
                    entity_for_refresh.warehouse_id,
                    entity_for_refresh.category,
                    entity_for_refresh.product_id,
                )

                if refreshed_entity:
                    original_value = refreshed_entity.description
                    refreshed_entity.description = 'Wireless Headphones (Noise Cancelling)'

                    updated_product = self.product_repo.update_product(refreshed_entity)
                    print(
                        f'✅ Updated description: {original_value} → {updated_product.description}'
                    )

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
                retrieved_product = self.product_repo.get_product(
                    entity_for_get.warehouse_id, entity_for_get.category, entity_for_get.product_id
                )

                if retrieved_product:
                    print(f'✅ Retrieved: {retrieved_product}')
                else:
                    print('❌ Failed to retrieve product')
            except Exception as e:
                print(f'❌ Failed to retrieve product: {e}')

        print('🎯 Product CRUD cycle completed!')

        # Rating example
        print('\n--- Rating ---')

        # 1. CREATE - Create sample rating
        sample_rating = Rating(
            warehouse_id='wh_7891',
            sort_key='REVIEW#2026-02-19T16:00:00Z#rat_789',
            rating_id='rat_789',
            recipient_name='Sarah Connor',
            feedback='Excellent service and fast processing!',
            score=5,
            created_at='2026-02-19T16:00:00Z',
        )

        print('📝 Creating rating...')
        print(f'📝 PK: {sample_rating.pk()}, SK: {sample_rating.sk()}')

        try:
            created_rating = self.rating_repo.create_rating(sample_rating)
            print(f'✅ Created: {created_rating}')
            # Store created entity for access pattern testing
            created_entities['Rating'] = created_rating
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  rating already exists, retrieving existing entity...')
                try:
                    existing_rating = self.rating_repo.get_rating(
                        sample_rating.warehouse_id,
                        sample_rating.created_at,
                        sample_rating.rating_id,
                    )

                    if existing_rating:
                        print(f'✅ Retrieved existing: {existing_rating}')
                        # Store existing entity for access pattern testing
                        created_entities['Rating'] = existing_rating
                    else:
                        print('❌ Failed to retrieve existing rating')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing rating: {get_error}')
            else:
                print(f'❌ Failed to create rating: {e}')
        # 2. UPDATE - Update non-key field (feedback)
        if 'Rating' in created_entities:
            print('\n🔄 Updating feedback field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['Rating']
                refreshed_entity = self.rating_repo.get_rating(
                    entity_for_refresh.warehouse_id,
                    entity_for_refresh.created_at,
                    entity_for_refresh.rating_id,
                )

                if refreshed_entity:
                    original_value = refreshed_entity.feedback
                    refreshed_entity.feedback = 'Updated: Excellent service and fast processing!'

                    updated_rating = self.rating_repo.update_rating(refreshed_entity)
                    print(f'✅ Updated feedback: {original_value} → {updated_rating.feedback}')

                    # Update stored entity with updated values
                    created_entities['Rating'] = updated_rating
                else:
                    print('❌ Could not refresh rating for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(f'⚠️  rating was modified by another process (optimistic locking): {e}')
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update rating: {e}')

        # 3. GET - Retrieve and print the entity
        if 'Rating' in created_entities:
            print('\n🔍 Retrieving rating...')
            try:
                entity_for_get = created_entities['Rating']
                retrieved_rating = self.rating_repo.get_rating(
                    entity_for_get.warehouse_id,
                    entity_for_get.created_at,
                    entity_for_get.rating_id,
                )

                if retrieved_rating:
                    print(f'✅ Retrieved: {retrieved_rating}')
                else:
                    print('❌ Failed to retrieve rating')
            except Exception as e:
                print(f'❌ Failed to retrieve rating: {e}')

        print('🎯 Rating CRUD cycle completed!')

        # WarehouseProfile example
        print('\n--- WarehouseProfile ---')

        # 1. CREATE - Create sample warehouseprofile
        sample_warehouseprofile = WarehouseProfile(
            warehouse_id='wh_7891',
            sort_key='PROFILE',
            name='Metro Warehouse',
            address='500 Pine St',
            city='Seattle',
            category='Electronics',
            rating=Decimal('4.6'),
            processing_time=35,
            created_at='2026-02-01T00:00:00Z',
        )

        print('📝 Creating warehouseprofile...')
        print(f'📝 PK: {sample_warehouseprofile.pk()}, SK: {sample_warehouseprofile.sk()}')

        try:
            created_warehouseprofile = self.warehouseprofile_repo.create_warehouse_profile(
                sample_warehouseprofile
            )
            print(f'✅ Created: {created_warehouseprofile}')
            # Store created entity for access pattern testing
            created_entities['WarehouseProfile'] = created_warehouseprofile
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  warehouseprofile already exists, retrieving existing entity...')
                try:
                    existing_warehouseprofile = self.warehouseprofile_repo.get_warehouse_profile(
                        sample_warehouseprofile.warehouse_id
                    )

                    if existing_warehouseprofile:
                        print(f'✅ Retrieved existing: {existing_warehouseprofile}')
                        # Store existing entity for access pattern testing
                        created_entities['WarehouseProfile'] = existing_warehouseprofile
                    else:
                        print('❌ Failed to retrieve existing warehouseprofile')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing warehouseprofile: {get_error}')
            else:
                print(f'❌ Failed to create warehouseprofile: {e}')
        # 2. UPDATE - Update non-key field (name)
        if 'WarehouseProfile' in created_entities:
            print('\n🔄 Updating name field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['WarehouseProfile']
                refreshed_entity = self.warehouseprofile_repo.get_warehouse_profile(
                    entity_for_refresh.warehouse_id
                )

                if refreshed_entity:
                    original_value = refreshed_entity.name
                    refreshed_entity.name = 'Metro Warehouse Updated'

                    updated_warehouseprofile = self.warehouseprofile_repo.update_warehouse_profile(
                        refreshed_entity
                    )
                    print(f'✅ Updated name: {original_value} → {updated_warehouseprofile.name}')

                    # Update stored entity with updated values
                    created_entities['WarehouseProfile'] = updated_warehouseprofile
                else:
                    print('❌ Could not refresh warehouseprofile for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  warehouseprofile was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update warehouseprofile: {e}')

        # 3. GET - Retrieve and print the entity
        if 'WarehouseProfile' in created_entities:
            print('\n🔍 Retrieving warehouseprofile...')
            try:
                entity_for_get = created_entities['WarehouseProfile']
                retrieved_warehouseprofile = self.warehouseprofile_repo.get_warehouse_profile(
                    entity_for_get.warehouse_id
                )

                if retrieved_warehouseprofile:
                    print(f'✅ Retrieved: {retrieved_warehouseprofile}')
                else:
                    print('❌ Failed to retrieve warehouseprofile')
            except Exception as e:
                print(f'❌ Failed to retrieve warehouseprofile: {e}')

        print('🎯 WarehouseProfile CRUD cycle completed!')
        print('\n=== Shipments Table Operations ===')

        # Shipment example
        print('\n--- Shipment ---')

        # 1. CREATE - Create sample shipment
        sample_shipment = Shipment(
            shipment_id='shp_7891',
            recipient_id='rcpt_7891',
            warehouse_id='wh_7891',
            warehouse_name='Metro Warehouse',
            recipient_name='Sarah Connor',
            status='DELIVERED',
            packages=[
                {
                    'name': 'Wireless Headphones',
                    'product_id': 'prod_789',
                    'qty': 2,
                    'weight': Decimal('0.5'),
                }
            ],
            total_weight=Decimal('1.0'),
            destination_address='100 Maple Ave',
            origin_address='500 Pine St',
            created_at='2026-02-19T14:00:00Z',
            updated_at='2026-02-19T15:00:00Z',
            courier_id='cour_7891',
            available_city='Seattle',
            active_delivery='sample_active_delivery',
        )

        print('📝 Creating shipment...')
        print(f'📝 PK: {sample_shipment.pk()}, SK: {sample_shipment.sk()}')

        try:
            created_shipment = self.shipment_repo.create_shipment(sample_shipment)
            print(f'✅ Created: {created_shipment}')
            # Store created entity for access pattern testing
            created_entities['Shipment'] = created_shipment
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  shipment already exists, retrieving existing entity...')
                try:
                    existing_shipment = self.shipment_repo.get_shipment(
                        sample_shipment.shipment_id
                    )

                    if existing_shipment:
                        print(f'✅ Retrieved existing: {existing_shipment}')
                        # Store existing entity for access pattern testing
                        created_entities['Shipment'] = existing_shipment
                    else:
                        print('❌ Failed to retrieve existing shipment')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing shipment: {get_error}')
            else:
                print(f'❌ Failed to create shipment: {e}')
        # 2. UPDATE - Update non-key field (status)
        if 'Shipment' in created_entities:
            print('\n🔄 Updating status field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['Shipment']
                refreshed_entity = self.shipment_repo.get_shipment(entity_for_refresh.shipment_id)

                if refreshed_entity:
                    original_value = refreshed_entity.status
                    refreshed_entity.status = 'IN_TRANSIT'

                    updated_shipment = self.shipment_repo.update_shipment(refreshed_entity)
                    print(f'✅ Updated status: {original_value} → {updated_shipment.status}')

                    # Update stored entity with updated values
                    created_entities['Shipment'] = updated_shipment
                else:
                    print('❌ Could not refresh shipment for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(f'⚠️  shipment was modified by another process (optimistic locking): {e}')
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update shipment: {e}')

        # 3. GET - Retrieve and print the entity
        if 'Shipment' in created_entities:
            print('\n🔍 Retrieving shipment...')
            try:
                entity_for_get = created_entities['Shipment']
                retrieved_shipment = self.shipment_repo.get_shipment(entity_for_get.shipment_id)

                if retrieved_shipment:
                    print(f'✅ Retrieved: {retrieved_shipment}')
                else:
                    print('❌ Failed to retrieve shipment')
            except Exception as e:
                print(f'❌ Failed to retrieve shipment: {e}')

        print('🎯 Shipment CRUD cycle completed!')

        print('\n' + '=' * 50)
        print('🎉 Basic CRUD examples completed!')

        # Additional Access Pattern Testing Section (before cleanup)
        if include_additional_access_patterns:
            self._test_additional_access_patterns(created_entities)

        # Cleanup - Delete all created entities
        print('\n' + '=' * 50)
        print('🗑️  Cleanup: Deleting all created entities')
        print('=' * 50)

        # Delete Recipient
        if 'Recipient' in created_entities:
            print('\n🗑️  Deleting recipient...')
            try:
                deleted = self.recipient_repo.delete_recipient(
                    created_entities['Recipient'].recipient_id
                )

                if deleted:
                    print('✅ Deleted recipient successfully')
                else:
                    print('❌ Failed to delete recipient (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete recipient: {e}')

        # Delete Courier
        if 'Courier' in created_entities:
            print('\n🗑️  Deleting courier...')
            try:
                deleted = self.courier_repo.delete_courier(created_entities['Courier'].courier_id)

                if deleted:
                    print('✅ Deleted courier successfully')
                else:
                    print('❌ Failed to delete courier (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete courier: {e}')

        # Delete Product
        if 'Product' in created_entities:
            print('\n🗑️  Deleting product...')
            try:
                deleted = self.product_repo.delete_product(
                    created_entities['Product'].warehouse_id,
                    created_entities['Product'].category,
                    created_entities['Product'].product_id,
                )

                if deleted:
                    print('✅ Deleted product successfully')
                else:
                    print('❌ Failed to delete product (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete product: {e}')

        # Delete Rating
        if 'Rating' in created_entities:
            print('\n🗑️  Deleting rating...')
            try:
                deleted = self.rating_repo.delete_rating(
                    created_entities['Rating'].warehouse_id,
                    created_entities['Rating'].created_at,
                    created_entities['Rating'].rating_id,
                )

                if deleted:
                    print('✅ Deleted rating successfully')
                else:
                    print('❌ Failed to delete rating (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete rating: {e}')

        # Delete WarehouseProfile
        if 'WarehouseProfile' in created_entities:
            print('\n🗑️  Deleting warehouseprofile...')
            try:
                deleted = self.warehouseprofile_repo.delete_warehouse_profile(
                    created_entities['WarehouseProfile'].warehouse_id
                )

                if deleted:
                    print('✅ Deleted warehouseprofile successfully')
                else:
                    print('❌ Failed to delete warehouseprofile (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete warehouseprofile: {e}')

        # Delete Shipment
        if 'Shipment' in created_entities:
            print('\n🗑️  Deleting shipment...')
            try:
                deleted = self.shipment_repo.delete_shipment(
                    created_entities['Shipment'].shipment_id
                )

                if deleted:
                    print('✅ Deleted shipment successfully')
                else:
                    print('❌ Failed to delete shipment (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete shipment: {e}')
        print('\n💡 Requirements:')
        print("   - DynamoDB table 'Recipients' must exist")
        print("   - DynamoDB table 'Couriers' must exist")
        print("   - DynamoDB table 'Warehouses' must exist")
        print("   - DynamoDB table 'Shipments' must exist")
        print('   - DynamoDB permissions: GetItem, PutItem, UpdateItem, DeleteItem')

    def _test_additional_access_patterns(self, created_entities: dict):
        """Test additional access patterns beyond basic CRUD"""
        print('\n' + '=' * 60)
        print('🔍 Additional Access Pattern Testing')
        print('=' * 60)
        print()

        # Recipient
        # Access Pattern #16: Create recipient account
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #16: Create recipient account')
            print('   Using Main Table')
            test_entity = Recipient(
                recipient_id='rcpt_5432',
                name='Tom Hardy',
                email='tom@email.com',
                phone='+1-555-0543',
                city='Portland',
                created_at='2026-02-05T10:30:00Z',
            )
            result = self.recipient_repo.put_recipient(test_entity)
            print('   ✅ Create recipient account completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #16: {e}')

        # Access Pattern #21: Get recipient profile by ID
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #21: Get recipient profile by ID')
            print('   Using Main Table')
            result = self.recipient_repo.get_recipient(created_entities['Recipient'].recipient_id)
            print('   ✅ Get recipient profile by ID completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #21: {e}')

        # Courier
        # Access Pattern #18: Register courier
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #18: Register courier')
            print('   Using Main Table')
            test_entity = Courier(
                courier_id='cour_5432',
                name='Lisa Park',
                email='lisa@email.com',
                phone='+1-555-0544',
                city='Portland',
                vehicle_type='car',
                created_at='2026-02-03T07:30:00Z',
            )
            result = self.courier_repo.register_courier(test_entity)
            print('   ✅ Register courier completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #18: {e}')

        # Access Pattern #22: Get courier profile by ID
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #22: Get courier profile by ID')
            print('   Using Main Table')
            result = self.courier_repo.get_courier(created_entities['Courier'].courier_id)
            print('   ✅ Get courier profile by ID completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #22: {e}')

        # Product
        # Access Pattern #8: Add or update product
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #8: Add or update product')
            print('   Using Main Table')
            test_entity = Product(
                warehouse_id='wh_5432',
                sort_key='MENU#Accessories#prod_543',
                product_id='prod_543',
                category='Accessories',
                description='USB Cable',
                price=Decimal('5.99'),
                available=True,
                city='Portland',
            )
            result = self.product_repo.upsert_product(test_entity)
            print('   ✅ Add or update product completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #8: {e}')

        # Access Pattern #9: Remove product
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #9: Remove product')
            print('   Using Main Table')
            result = self.product_repo.delete_product_with_warehouse_id_and_sort_key(
                created_entities['Product'].warehouse_id, created_entities['Product'].sort_key
            )
            print('   ✅ Remove product completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #9: {e}')

        # Access Pattern #30: View warehouse products
        # Index: Main Table
        # Range Condition: begins_with
        try:
            print('🔍 Testing Access Pattern #30: View warehouse products')
            print('   Using Main Table')
            print('   Range Condition: begins_with')
            result = self.product_repo.get_warehouse_products(
                created_entities['Product'].warehouse_id, 'sort_key_prefix_value'
            )
            print('   ✅ View warehouse products completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #30: {e}')

        # Access Pattern #28: Get all products by city and category
        # GSI: ProductsByCategory
        try:
            print('🔍 Testing Access Pattern #28: Get all products by city and category')
            print('   Using GSI: ProductsByCategory')
            result = self.product_repo.get_products_by_city_category(
                created_entities['Product'].city, created_entities['Product'].category
            )
            print('   ✅ Get all products by city and category completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #28: {e}')

        # Rating
        # Access Pattern #19: Recipient rates warehouse
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #19: Recipient rates warehouse')
            print('   Using Main Table')
            test_entity = Rating(
                warehouse_id='wh_5432',
                sort_key='REVIEW#2026-02-18T12:00:00Z#rat_543',
                rating_id='rat_543',
                recipient_name='Tom Hardy',
                feedback='Good service, a bit slow.',
                score=3,
                created_at='2026-02-18T12:00:00Z',
            )
            result = self.rating_repo.put_rating(test_entity)
            print('   ✅ Recipient rates warehouse completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #19: {e}')

        # Access Pattern #20: View ratings for warehouse
        # Index: Main Table
        # Range Condition: begins_with
        try:
            print('🔍 Testing Access Pattern #20: View ratings for warehouse')
            print('   Using Main Table')
            print('   Range Condition: begins_with')
            result = self.rating_repo.get_warehouse_ratings(
                created_entities['Rating'].warehouse_id, 'sort_key_prefix_value'
            )
            print('   ✅ View ratings for warehouse completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #20: {e}')

        # WarehouseProfile
        # Access Pattern #17: Create warehouse profile
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #17: Create warehouse profile')
            print('   Using Main Table')
            test_entity = WarehouseProfile(
                warehouse_id='wh_5432',
                sort_key='PROFILE',
                name='Harbor Storage',
                address='200 Oak Blvd',
                city='Portland',
                category='Accessories',
                rating=Decimal('4.3'),
                processing_time=40,
                created_at='2026-02-03T00:00:00Z',
            )
            result = self.warehouseprofile_repo.create_warehouse(test_entity)
            print('   ✅ Create warehouse profile completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #17: {e}')

        # Access Pattern #3: View warehouse profile
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #3: View warehouse profile')
            print('   Using Main Table')
            result = self.warehouseprofile_repo.get_warehouse_profile(
                created_entities['WarehouseProfile'].warehouse_id
            )
            print('   ✅ View warehouse profile completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #3: {e}')

        # Access Pattern #7: Update warehouse profile
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #7: Update warehouse profile')
            print('   Using Main Table')
            result = (
                self.warehouseprofile_repo.update_warehouse_profile_with_warehouse_id_and_name(
                    created_entities['WarehouseProfile'].warehouse_id,
                    created_entities['WarehouseProfile'].name,
                    created_entities['WarehouseProfile'].processing_time,
                )
            )
            print('   ✅ Update warehouse profile completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #7: {e}')

        # Access Pattern #1: Get warehouses by city and category
        # GSI: WarehousesByCity
        try:
            print('🔍 Testing Access Pattern #1: Get warehouses by city and category')
            print('   Using GSI: WarehousesByCity')
            result = self.warehouseprofile_repo.get_warehouses_by_city_category(
                created_entities['WarehouseProfile'].city,
                created_entities['WarehouseProfile'].category,
            )
            print('   ✅ Get warehouses by city and category completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #1: {e}')

        # Access Pattern #27: Get warehouses by city, category and minimum rating
        # GSI: WarehousesByCity
        # Range Condition: >=
        try:
            print(
                '🔍 Testing Access Pattern #27: Get warehouses by city, category and minimum rating'
            )
            print('   Using GSI: WarehousesByCity')
            print('   Range Condition: >=')
            result = self.warehouseprofile_repo.get_warehouses_by_city_category_rating(
                created_entities['WarehouseProfile'].city,
                created_entities['WarehouseProfile'].category,
                Decimal('0.00'),
            )
            print('   ✅ Get warehouses by city, category and minimum rating completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #27: {e}')

        # Access Pattern #2: Search warehouses by name prefix within a city
        # GSI: WarehousesByName
        # Range Condition: begins_with
        try:
            print('🔍 Testing Access Pattern #2: Search warehouses by name prefix within a city')
            print('   Using GSI: WarehousesByName')
            print('   Range Condition: begins_with')
            result = self.warehouseprofile_repo.search_warehouses_by_name(
                created_entities['WarehouseProfile'].city, 'name_prefix_value'
            )
            print('   ✅ Search warehouses by name prefix within a city completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #2: {e}')

        # Shipment
        # Access Pattern #4: Create a shipment
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #4: Create a shipment')
            print('   Using Main Table')
            test_entity = Shipment(
                shipment_id='shp_5432',
                recipient_id='rcpt_5432',
                warehouse_id='wh_5432',
                warehouse_name='Harbor Storage',
                recipient_name='Tom Hardy',
                status='READY_FOR_PICKUP',
                packages=[
                    {
                        'name': 'USB Cable',
                        'product_id': 'prod_543',
                        'qty': 1,
                        'weight': Decimal('0.1'),
                    }
                ],
                total_weight=Decimal('0.1'),
                destination_address='200 Birch Ln',
                origin_address='200 Oak Blvd',
                created_at='2026-02-19T15:30:00Z',
                updated_at='2026-02-19T15:45:00Z',
                courier_id='courier_id123',
                available_city='Portland',
                active_delivery='sample_active_delivery',
            )
            result = self.shipment_repo.put_shipment(test_entity)
            print('   ✅ Create a shipment completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #4: {e}')

        # Access Pattern #5: View shipment status
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #5: View shipment status')
            print('   Using Main Table')
            result = self.shipment_repo.get_shipment(created_entities['Shipment'].shipment_id)
            print('   ✅ View shipment status completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #5: {e}')

        # Access Pattern #11: Update shipment status (warehouse)
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #11: Update shipment status (warehouse)')
            print('   Using Main Table')
            result = self.shipment_repo.update_shipment_status(
                created_entities['Shipment'].shipment_id, created_entities['Shipment'].status
            )
            print('   ✅ Update shipment status (warehouse) completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #11: {e}')

        # Access Pattern #13: Accept a delivery (assign courier)
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #13: Accept a delivery (assign courier)')
            print('   Using Main Table')
            result = self.shipment_repo.accept_delivery(
                created_entities['Shipment'].shipment_id,
                created_entities['Shipment'].courier_id,
                created_entities['Shipment'].active_delivery,
            )
            print('   ✅ Accept a delivery (assign courier) completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #13: {e}')

        # Access Pattern #14: Update delivery status
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #14: Update delivery status')
            print('   Using Main Table')
            result = self.shipment_repo.update_delivery_status(
                created_entities['Shipment'].shipment_id, created_entities['Shipment'].status
            )
            print('   ✅ Update delivery status completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #14: {e}')

        # Access Pattern #6: View recipient shipment history
        # GSI: ShipmentsByRecipient
        try:
            print('🔍 Testing Access Pattern #6: View recipient shipment history')
            print('   Using GSI: ShipmentsByRecipient')
            result = self.shipment_repo.get_recipient_shipments(
                created_entities['Shipment'].recipient_id
            )
            print('   ✅ View recipient shipment history completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #6: {e}')

        # Access Pattern #24: Get shipments by recipient and status
        # GSI: ShipmentsByRecipient
        try:
            print('🔍 Testing Access Pattern #24: Get shipments by recipient and status')
            print('   Using GSI: ShipmentsByRecipient')
            result = self.shipment_repo.get_recipient_shipments_by_status(
                created_entities['Shipment'].recipient_id, created_entities['Shipment'].status
            )
            print('   ✅ Get shipments by recipient and status completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #24: {e}')

        # Access Pattern #10: View incoming shipments for warehouse
        # GSI: ShipmentsByWarehouse
        try:
            print('🔍 Testing Access Pattern #10: View incoming shipments for warehouse')
            print('   Using GSI: ShipmentsByWarehouse')
            result = self.shipment_repo.get_warehouse_shipments(
                created_entities['Shipment'].warehouse_id, created_entities['Shipment'].status
            )
            print('   ✅ View incoming shipments for warehouse completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #10: {e}')

        # Access Pattern #25: Get shipments by warehouse and status
        # GSI: ShipmentsByWarehouse
        try:
            print('🔍 Testing Access Pattern #25: Get shipments by warehouse and status')
            print('   Using GSI: ShipmentsByWarehouse')
            result = self.shipment_repo.get_warehouse_shipments_by_status(
                created_entities['Shipment'].warehouse_id, created_entities['Shipment'].status
            )
            print('   ✅ Get shipments by warehouse and status completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #25: {e}')

        # Access Pattern #15: View courier delivery history
        # GSI: ShipmentsByCourier
        try:
            print('🔍 Testing Access Pattern #15: View courier delivery history')
            print('   Using GSI: ShipmentsByCourier')
            result = self.shipment_repo.get_courier_shipments(
                created_entities['Shipment'].courier_id
            )
            print('   ✅ View courier delivery history completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #15: {e}')

        # Access Pattern #26: Get shipments by courier and status
        # GSI: ShipmentsByCourier
        try:
            print('🔍 Testing Access Pattern #26: Get shipments by courier and status')
            print('   Using GSI: ShipmentsByCourier')
            result = self.shipment_repo.get_courier_shipments_by_status(
                created_entities['Shipment'].courier_id, created_entities['Shipment'].status
            )
            print('   ✅ Get shipments by courier and status completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #26: {e}')

        # Access Pattern #12: View available shipments for pickup by city
        # GSI: AvailableShipmentsByCity
        try:
            print('🔍 Testing Access Pattern #12: View available shipments for pickup by city')
            print('   Using GSI: AvailableShipmentsByCity')
            result = self.shipment_repo.get_available_shipments_by_city(
                created_entities['Shipment'].available_city
            )
            print('   ✅ View available shipments for pickup by city completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #12: {e}')

        # Access Pattern #23: Get courier's current active delivery
        # GSI: CourierActiveDelivery
        try:
            print("🔍 Testing Access Pattern #23: Get courier's current active delivery")
            print('   Using GSI: CourierActiveDelivery')
            result = self.shipment_repo.get_courier_active_delivery(
                created_entities['Shipment'].active_delivery
            )
            print("   ✅ Get courier's current active delivery completed")
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #23: {e}')

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
    print('   - Recipients')
    print('   - Couriers')
    print('   - Warehouses')
    print('   - Shipments')

    if include_additional_access_patterns:
        print('🔍 Including additional access pattern examples')

    examples = UsageExamples()
    examples.run_examples(include_additional_access_patterns=include_additional_access_patterns)


if __name__ == '__main__':
    main()
