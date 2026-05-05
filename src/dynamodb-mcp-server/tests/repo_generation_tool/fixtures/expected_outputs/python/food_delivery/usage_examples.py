"""Generated usage examples for DynamoDB entities and repositories"""

from __future__ import annotations

import os
import sys
from decimal import Decimal

# Import generated entities and repositories
from entities import Delivery, DeliveryEvent, Driver, Restaurant
from repositories import (
    DeliveryEventRepository,
    DeliveryRepository,
    DriverRepository,
    RestaurantRepository,
)


class UsageExamples:
    """Examples of using the generated entities and repositories"""

    def __init__(self):
        """Initialize repositories with default table names from schema."""
        # Initialize repositories with their respective table names
        # DeliveryTable table repositories
        try:
            self.delivery_repo = DeliveryRepository('DeliveryTable')
            print("✅ Initialized DeliveryRepository for table 'DeliveryTable'")
        except Exception as e:
            print(f'❌ Failed to initialize DeliveryRepository: {e}')
            self.delivery_repo = None
        try:
            self.deliveryevent_repo = DeliveryEventRepository('DeliveryTable')
            print("✅ Initialized DeliveryEventRepository for table 'DeliveryTable'")
        except Exception as e:
            print(f'❌ Failed to initialize DeliveryEventRepository: {e}')
            self.deliveryevent_repo = None
        # RestaurantTable table repositories
        try:
            self.restaurant_repo = RestaurantRepository('RestaurantTable')
            print("✅ Initialized RestaurantRepository for table 'RestaurantTable'")
        except Exception as e:
            print(f'❌ Failed to initialize RestaurantRepository: {e}')
            self.restaurant_repo = None
        # DriverTable table repositories
        try:
            self.driver_repo = DriverRepository('DriverTable')
            print("✅ Initialized DriverRepository for table 'DriverTable'")
        except Exception as e:
            print(f'❌ Failed to initialize DriverRepository: {e}')
            self.driver_repo = None

    def run_examples(self, include_additional_access_patterns: bool = False):
        """Run CRUD examples for all entities"""
        # Dictionary to store created entities for access pattern testing
        created_entities = {}

        # Step 0: Cleanup any leftover entities from previous runs (makes tests idempotent)
        print('🧹 Pre-test Cleanup: Removing any leftover entities from previous runs')
        print('=' * 50)
        # Try to delete Delivery (customer_id, order_date, delivery_id)
        try:
            sample_delivery = Delivery(
                customer_id='cust-001',
                delivery_id='del-10001',
                order_date='2024-03-15',
                restaurant_id='rest-501',
                driver_id='drv-201',
                status='DELIVERED',
                total=Decimal('42.5'),
                delivery_fee=Decimal('5.99'),
                tip=Decimal('8.0'),
                items=['Pad Thai', 'Spring Rolls', 'Thai Iced Tea'],
                special_instructions='Leave at door',
                cancelled_at='sample_cancelled_at',
                estimated_delivery_time='2024-03-15T19:30:00Z',
                created_at='2024-03-15T18:45:00Z',
            )
            self.delivery_repo.delete_delivery(
                sample_delivery.customer_id,
                sample_delivery.order_date,
                sample_delivery.delivery_id,
            )
            print('   🗑️  Deleted leftover delivery (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete DeliveryEvent (delivery_id, event_timestamp, event_id)
        try:
            sample_deliveryevent = DeliveryEvent(
                delivery_id='del-10001',
                event_id='evt-001',
                event_timestamp='2024-03-15T18:45:00Z',
                event_type='ORDER_PLACED',
                description='Order placed by customer',
                actor='cust-001',
            )
            self.deliveryevent_repo.delete_delivery_event(
                sample_deliveryevent.delivery_id,
                sample_deliveryevent.event_timestamp,
                sample_deliveryevent.event_id,
            )
            print('   🗑️  Deleted leftover deliveryevent (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete Restaurant (restaurant_id)
        try:
            sample_restaurant = Restaurant(
                restaurant_id='rest-501',
                name='Thai Garden',
                cuisine_type='Thai',
                rating=Decimal('4.5'),
                is_active=True,
                address='123 Main St, Seattle, WA 98101',
                created_at='2023-06-01T10:00:00Z',
            )
            self.restaurant_repo.delete_restaurant(sample_restaurant.restaurant_id)
            print('   🗑️  Deleted leftover restaurant (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete Driver (driver_id)
        try:
            sample_driver = Driver(
                driver_id='drv-201',
                name='Alex Thompson',
                phone='+1-555-0201',
                vehicle_type='car',
                tags=['express', 'fragile-items', 'large-orders'],
                rating=Decimal('4.9'),
                total_deliveries=1250,
                is_available=True,
                created_at='2023-01-10T08:00:00Z',
            )
            self.driver_repo.delete_driver(sample_driver.driver_id)
            print('   🗑️  Deleted leftover driver (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        print('✅ Pre-test cleanup completed\n')

        print('Running Repository Examples')
        print('=' * 50)
        print('\n=== DeliveryTable Table Operations ===')

        # Delivery example
        print('\n--- Delivery ---')

        # 1. CREATE - Create sample delivery
        sample_delivery = Delivery(
            customer_id='cust-001',
            delivery_id='del-10001',
            order_date='2024-03-15',
            restaurant_id='rest-501',
            driver_id='drv-201',
            status='DELIVERED',
            total=Decimal('42.5'),
            delivery_fee=Decimal('5.99'),
            tip=Decimal('8.0'),
            items=['Pad Thai', 'Spring Rolls', 'Thai Iced Tea'],
            special_instructions='Leave at door',
            cancelled_at='sample_cancelled_at',
            estimated_delivery_time='2024-03-15T19:30:00Z',
            created_at='2024-03-15T18:45:00Z',
        )

        print('📝 Creating delivery...')
        print(f'📝 PK: {sample_delivery.pk()}, SK: {sample_delivery.sk()}')

        try:
            created_delivery = self.delivery_repo.create_delivery(sample_delivery)
            print(f'✅ Created: {created_delivery}')
            # Store created entity for access pattern testing
            created_entities['Delivery'] = created_delivery
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  delivery already exists, retrieving existing entity...')
                try:
                    existing_delivery = self.delivery_repo.get_delivery(
                        sample_delivery.customer_id,
                        sample_delivery.order_date,
                        sample_delivery.delivery_id,
                    )

                    if existing_delivery:
                        print(f'✅ Retrieved existing: {existing_delivery}')
                        # Store existing entity for access pattern testing
                        created_entities['Delivery'] = existing_delivery
                    else:
                        print('❌ Failed to retrieve existing delivery')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing delivery: {get_error}')
            else:
                print(f'❌ Failed to create delivery: {e}')
        # 2. UPDATE - Update non-key field (driver_id)
        if 'Delivery' in created_entities:
            print('\n🔄 Updating driver_id field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['Delivery']
                refreshed_entity = self.delivery_repo.get_delivery(
                    entity_for_refresh.customer_id,
                    entity_for_refresh.order_date,
                    entity_for_refresh.delivery_id,
                )

                if refreshed_entity:
                    original_value = refreshed_entity.driver_id
                    refreshed_entity.driver_id = 'drv-203'

                    updated_delivery = self.delivery_repo.update_delivery(refreshed_entity)
                    print(f'✅ Updated driver_id: {original_value} → {updated_delivery.driver_id}')

                    # Update stored entity with updated values
                    created_entities['Delivery'] = updated_delivery
                else:
                    print('❌ Could not refresh delivery for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(f'⚠️  delivery was modified by another process (optimistic locking): {e}')
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update delivery: {e}')

        # 3. GET - Retrieve and print the entity
        if 'Delivery' in created_entities:
            print('\n🔍 Retrieving delivery...')
            try:
                entity_for_get = created_entities['Delivery']
                retrieved_delivery = self.delivery_repo.get_delivery(
                    entity_for_get.customer_id,
                    entity_for_get.order_date,
                    entity_for_get.delivery_id,
                )

                if retrieved_delivery:
                    print(f'✅ Retrieved: {retrieved_delivery}')
                else:
                    print('❌ Failed to retrieve delivery')
            except Exception as e:
                print(f'❌ Failed to retrieve delivery: {e}')

        print('🎯 Delivery CRUD cycle completed!')

        # DeliveryEvent example
        print('\n--- DeliveryEvent ---')

        # 1. CREATE - Create sample deliveryevent
        sample_deliveryevent = DeliveryEvent(
            delivery_id='del-10001',
            event_id='evt-001',
            event_timestamp='2024-03-15T18:45:00Z',
            event_type='ORDER_PLACED',
            description='Order placed by customer',
            actor='cust-001',
        )

        print('📝 Creating deliveryevent...')
        print(f'📝 PK: {sample_deliveryevent.pk()}, SK: {sample_deliveryevent.sk()}')

        try:
            created_deliveryevent = self.deliveryevent_repo.create_delivery_event(
                sample_deliveryevent
            )
            print(f'✅ Created: {created_deliveryevent}')
            # Store created entity for access pattern testing
            created_entities['DeliveryEvent'] = created_deliveryevent
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  deliveryevent already exists, retrieving existing entity...')
                try:
                    existing_deliveryevent = self.deliveryevent_repo.get_delivery_event(
                        sample_deliveryevent.delivery_id,
                        sample_deliveryevent.event_timestamp,
                        sample_deliveryevent.event_id,
                    )

                    if existing_deliveryevent:
                        print(f'✅ Retrieved existing: {existing_deliveryevent}')
                        # Store existing entity for access pattern testing
                        created_entities['DeliveryEvent'] = existing_deliveryevent
                    else:
                        print('❌ Failed to retrieve existing deliveryevent')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing deliveryevent: {get_error}')
            else:
                print(f'❌ Failed to create deliveryevent: {e}')
        # 2. UPDATE - Update non-key field (description)
        if 'DeliveryEvent' in created_entities:
            print('\n🔄 Updating description field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['DeliveryEvent']
                refreshed_entity = self.deliveryevent_repo.get_delivery_event(
                    entity_for_refresh.delivery_id,
                    entity_for_refresh.event_timestamp,
                    entity_for_refresh.event_id,
                )

                if refreshed_entity:
                    original_value = refreshed_entity.description
                    refreshed_entity.description = 'Updated event description'

                    updated_deliveryevent = self.deliveryevent_repo.update_delivery_event(
                        refreshed_entity
                    )
                    print(
                        f'✅ Updated description: {original_value} → {updated_deliveryevent.description}'
                    )

                    # Update stored entity with updated values
                    created_entities['DeliveryEvent'] = updated_deliveryevent
                else:
                    print('❌ Could not refresh deliveryevent for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  deliveryevent was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update deliveryevent: {e}')

        # 3. GET - Retrieve and print the entity
        if 'DeliveryEvent' in created_entities:
            print('\n🔍 Retrieving deliveryevent...')
            try:
                entity_for_get = created_entities['DeliveryEvent']
                retrieved_deliveryevent = self.deliveryevent_repo.get_delivery_event(
                    entity_for_get.delivery_id,
                    entity_for_get.event_timestamp,
                    entity_for_get.event_id,
                )

                if retrieved_deliveryevent:
                    print(f'✅ Retrieved: {retrieved_deliveryevent}')
                else:
                    print('❌ Failed to retrieve deliveryevent')
            except Exception as e:
                print(f'❌ Failed to retrieve deliveryevent: {e}')

        print('🎯 DeliveryEvent CRUD cycle completed!')
        print('\n=== RestaurantTable Table Operations ===')

        # Restaurant example
        print('\n--- Restaurant ---')

        # 1. CREATE - Create sample restaurant
        sample_restaurant = Restaurant(
            restaurant_id='rest-501',
            name='Thai Garden',
            cuisine_type='Thai',
            rating=Decimal('4.5'),
            is_active=True,
            address='123 Main St, Seattle, WA 98101',
            created_at='2023-06-01T10:00:00Z',
        )

        print('📝 Creating restaurant...')
        print(f'📝 PK: {sample_restaurant.pk()}, SK: {sample_restaurant.sk()}')

        try:
            created_restaurant = self.restaurant_repo.create_restaurant(sample_restaurant)
            print(f'✅ Created: {created_restaurant}')
            # Store created entity for access pattern testing
            created_entities['Restaurant'] = created_restaurant
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  restaurant already exists, retrieving existing entity...')
                try:
                    existing_restaurant = self.restaurant_repo.get_restaurant(
                        sample_restaurant.restaurant_id
                    )

                    if existing_restaurant:
                        print(f'✅ Retrieved existing: {existing_restaurant}')
                        # Store existing entity for access pattern testing
                        created_entities['Restaurant'] = existing_restaurant
                    else:
                        print('❌ Failed to retrieve existing restaurant')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing restaurant: {get_error}')
            else:
                print(f'❌ Failed to create restaurant: {e}')
        # 2. UPDATE - Update non-key field (rating)
        if 'Restaurant' in created_entities:
            print('\n🔄 Updating rating field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['Restaurant']
                refreshed_entity = self.restaurant_repo.get_restaurant(
                    entity_for_refresh.restaurant_id
                )

                if refreshed_entity:
                    original_value = refreshed_entity.rating
                    refreshed_entity.rating = Decimal('4.6')

                    updated_restaurant = self.restaurant_repo.update_restaurant(refreshed_entity)
                    print(f'✅ Updated rating: {original_value} → {updated_restaurant.rating}')

                    # Update stored entity with updated values
                    created_entities['Restaurant'] = updated_restaurant
                else:
                    print('❌ Could not refresh restaurant for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  restaurant was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update restaurant: {e}')

        # 3. GET - Retrieve and print the entity
        if 'Restaurant' in created_entities:
            print('\n🔍 Retrieving restaurant...')
            try:
                entity_for_get = created_entities['Restaurant']
                retrieved_restaurant = self.restaurant_repo.get_restaurant(
                    entity_for_get.restaurant_id
                )

                if retrieved_restaurant:
                    print(f'✅ Retrieved: {retrieved_restaurant}')
                else:
                    print('❌ Failed to retrieve restaurant')
            except Exception as e:
                print(f'❌ Failed to retrieve restaurant: {e}')

        print('🎯 Restaurant CRUD cycle completed!')
        print('\n=== DriverTable Table Operations ===')

        # Driver example
        print('\n--- Driver ---')

        # 1. CREATE - Create sample driver
        sample_driver = Driver(
            driver_id='drv-201',
            name='Alex Thompson',
            phone='+1-555-0201',
            vehicle_type='car',
            tags=['express', 'fragile-items', 'large-orders'],
            rating=Decimal('4.9'),
            total_deliveries=1250,
            is_available=True,
            created_at='2023-01-10T08:00:00Z',
        )

        print('📝 Creating driver...')
        print(f'📝 PK: {sample_driver.pk()}, SK: {sample_driver.sk()}')

        try:
            created_driver = self.driver_repo.create_driver(sample_driver)
            print(f'✅ Created: {created_driver}')
            # Store created entity for access pattern testing
            created_entities['Driver'] = created_driver
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  driver already exists, retrieving existing entity...')
                try:
                    existing_driver = self.driver_repo.get_driver(sample_driver.driver_id)

                    if existing_driver:
                        print(f'✅ Retrieved existing: {existing_driver}')
                        # Store existing entity for access pattern testing
                        created_entities['Driver'] = existing_driver
                    else:
                        print('❌ Failed to retrieve existing driver')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing driver: {get_error}')
            else:
                print(f'❌ Failed to create driver: {e}')
        # 2. UPDATE - Update non-key field (rating)
        if 'Driver' in created_entities:
            print('\n🔄 Updating rating field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['Driver']
                refreshed_entity = self.driver_repo.get_driver(entity_for_refresh.driver_id)

                if refreshed_entity:
                    original_value = refreshed_entity.rating
                    refreshed_entity.rating = Decimal('4.85')

                    updated_driver = self.driver_repo.update_driver(refreshed_entity)
                    print(f'✅ Updated rating: {original_value} → {updated_driver.rating}')

                    # Update stored entity with updated values
                    created_entities['Driver'] = updated_driver
                else:
                    print('❌ Could not refresh driver for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(f'⚠️  driver was modified by another process (optimistic locking): {e}')
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update driver: {e}')

        # 3. GET - Retrieve and print the entity
        if 'Driver' in created_entities:
            print('\n🔍 Retrieving driver...')
            try:
                entity_for_get = created_entities['Driver']
                retrieved_driver = self.driver_repo.get_driver(entity_for_get.driver_id)

                if retrieved_driver:
                    print(f'✅ Retrieved: {retrieved_driver}')
                else:
                    print('❌ Failed to retrieve driver')
            except Exception as e:
                print(f'❌ Failed to retrieve driver: {e}')

        print('🎯 Driver CRUD cycle completed!')

        print('\n' + '=' * 50)
        print('🎉 Basic CRUD examples completed!')

        # Additional Access Pattern Testing Section (before cleanup)
        if include_additional_access_patterns:
            self._test_additional_access_patterns(created_entities)

        # Cleanup - Delete all created entities
        print('\n' + '=' * 50)
        print('🗑️  Cleanup: Deleting all created entities')
        print('=' * 50)

        # Delete Delivery
        if 'Delivery' in created_entities:
            print('\n🗑️  Deleting delivery...')
            try:
                deleted = self.delivery_repo.delete_delivery(
                    created_entities['Delivery'].customer_id,
                    created_entities['Delivery'].order_date,
                    created_entities['Delivery'].delivery_id,
                )

                if deleted:
                    print('✅ Deleted delivery successfully')
                else:
                    print('❌ Failed to delete delivery (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete delivery: {e}')

        # Delete DeliveryEvent
        if 'DeliveryEvent' in created_entities:
            print('\n🗑️  Deleting deliveryevent...')
            try:
                deleted = self.deliveryevent_repo.delete_delivery_event(
                    created_entities['DeliveryEvent'].delivery_id,
                    created_entities['DeliveryEvent'].event_timestamp,
                    created_entities['DeliveryEvent'].event_id,
                )

                if deleted:
                    print('✅ Deleted deliveryevent successfully')
                else:
                    print('❌ Failed to delete deliveryevent (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete deliveryevent: {e}')

        # Delete Restaurant
        if 'Restaurant' in created_entities:
            print('\n🗑️  Deleting restaurant...')
            try:
                deleted = self.restaurant_repo.delete_restaurant(
                    created_entities['Restaurant'].restaurant_id
                )

                if deleted:
                    print('✅ Deleted restaurant successfully')
                else:
                    print('❌ Failed to delete restaurant (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete restaurant: {e}')

        # Delete Driver
        if 'Driver' in created_entities:
            print('\n🗑️  Deleting driver...')
            try:
                deleted = self.driver_repo.delete_driver(created_entities['Driver'].driver_id)

                if deleted:
                    print('✅ Deleted driver successfully')
                else:
                    print('❌ Failed to delete driver (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete driver: {e}')
        print('\n💡 Requirements:')
        print("   - DynamoDB table 'DeliveryTable' must exist")
        print("   - DynamoDB table 'RestaurantTable' must exist")
        print("   - DynamoDB table 'DriverTable' must exist")
        print('   - DynamoDB permissions: GetItem, PutItem, UpdateItem, DeleteItem')

    def _test_additional_access_patterns(self, created_entities: dict):
        """Test additional access patterns beyond basic CRUD"""
        print('\n' + '=' * 60)
        print('🔍 Additional Access Pattern Testing')
        print('=' * 60)
        print()

        # Delivery
        # Access Pattern #1: Get delivery details by customer and delivery ID
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #1: Get delivery details by customer and delivery ID')
            print('   Using Main Table')
            result = self.delivery_repo.get_delivery(
                created_entities['Delivery'].customer_id,
                created_entities['Delivery'].order_date,
                created_entities['Delivery'].delivery_id,
            )
            print('   ✅ Get delivery details by customer and delivery ID completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #1: {e}')

        # Access Pattern #2: Get non-cancelled deliveries for a customer with minimum total
        # Index: Main Table
        try:
            print(
                '🔍 Testing Access Pattern #2: Get non-cancelled deliveries for a customer with minimum total'
            )
            print('   Using Main Table')
            result = self.delivery_repo.get_active_customer_deliveries(
                created_entities['Delivery'].customer_id, 'CANCELLED', Decimal('25.0')
            )
            print('   ✅ Get non-cancelled deliveries for a customer with minimum total completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #2: {e}')

        # Access Pattern #3: Get deliveries for a customer within a delivery fee range
        # Index: Main Table
        try:
            print(
                '🔍 Testing Access Pattern #3: Get deliveries for a customer within a delivery fee range'
            )
            print('   Using Main Table')
            result = self.delivery_repo.get_customer_deliveries_by_fee_range(
                created_entities['Delivery'].customer_id, Decimal('3.0'), Decimal('10.0')
            )
            print('   ✅ Get deliveries for a customer within a delivery fee range completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #3: {e}')

        # Access Pattern #4: Get deliveries for a customer matching specific statuses
        # Index: Main Table
        try:
            print(
                '🔍 Testing Access Pattern #4: Get deliveries for a customer matching specific statuses'
            )
            print('   Using Main Table')
            result = self.delivery_repo.get_customer_deliveries_by_status(
                created_entities['Delivery'].customer_id, 'PENDING', 'PREPARING', 'EN_ROUTE'
            )
            print('   ✅ Get deliveries for a customer matching specific statuses completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #4: {e}')

        # Access Pattern #5: Get deliveries that have special instructions and are not cancelled
        # Index: Main Table
        try:
            print(
                '🔍 Testing Access Pattern #5: Get deliveries that have special instructions and are not cancelled'
            )
            print('   Using Main Table')
            result = self.delivery_repo.get_deliveries_with_special_instructions(
                created_entities['Delivery'].customer_id
            )
            print(
                '   ✅ Get deliveries that have special instructions and are not cancelled completed'
            )
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #5: {e}')

        # Access Pattern #6: Get deliveries with more than a minimum number of items
        # Index: Main Table
        try:
            print(
                '🔍 Testing Access Pattern #6: Get deliveries with more than a minimum number of items'
            )
            print('   Using Main Table')
            result = self.delivery_repo.get_deliveries_with_min_items(
                created_entities['Delivery'].customer_id, 3
            )
            print('   ✅ Get deliveries with more than a minimum number of items completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #6: {e}')

        # Access Pattern #7: Get deliveries with item count within a range
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #7: Get deliveries with item count within a range')
            print('   Using Main Table')
            result = self.delivery_repo.get_deliveries_with_items_in_range(
                created_entities['Delivery'].customer_id, 2, 5
            )
            print('   ✅ Get deliveries with item count within a range completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #7: {e}')

        # Access Pattern #8: Get active deliveries with high total or generous tip
        # Index: Main Table
        try:
            print(
                '🔍 Testing Access Pattern #8: Get active deliveries with high total or generous tip'
            )
            print('   Using Main Table')
            result = self.delivery_repo.get_high_value_active_deliveries(
                created_entities['Delivery'].customer_id, Decimal('25.0'), Decimal('5.0')
            )
            print('   ✅ Get active deliveries with high total or generous tip completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #8: {e}')

        # Access Pattern #9: Create a new delivery
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #9: Create a new delivery')
            print('   Using Main Table')
            test_entity = Delivery(
                customer_id='cust-002',
                delivery_id='del-20002',
                order_date='2024-03-18',
                restaurant_id='rest-502',
                driver_id='drv-202',
                status='EN_ROUTE',
                total=Decimal('67.8'),
                delivery_fee=Decimal('7.5'),
                tip=Decimal('12.0'),
                items=['Margherita Pizza', 'Caesar Salad', 'Garlic Bread', 'Tiramisu'],
                special_instructions='Ring doorbell twice',
                cancelled_at='sample_cancelled_at',
                estimated_delivery_time='2024-03-18T20:15:00Z',
                created_at='2024-03-18T19:30:00Z',
            )
            result = self.delivery_repo.put_delivery(test_entity)
            print('   ✅ Create a new delivery completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #9: {e}')

        # DeliveryEvent
        # Access Pattern #10: Get all events for a delivery
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #10: Get all events for a delivery')
            print('   Using Main Table')
            result = self.deliveryevent_repo.get_delivery_events(
                created_entities['DeliveryEvent'].delivery_id
            )
            print('   ✅ Get all events for a delivery completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #10: {e}')

        # Access Pattern #11: Get delivery events matching a specific event type prefix
        # Index: Main Table
        try:
            print(
                '🔍 Testing Access Pattern #11: Get delivery events matching a specific event type prefix'
            )
            print('   Using Main Table')
            result = self.deliveryevent_repo.get_delivery_events_by_type(
                created_entities['DeliveryEvent'].delivery_id, 'ORDER'
            )
            print('   ✅ Get delivery events matching a specific event type prefix completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #11: {e}')

        # Restaurant
        # Access Pattern #12: Get restaurant profile
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #12: Get restaurant profile')
            print('   Using Main Table')
            result = self.restaurant_repo.get_restaurant(
                created_entities['Restaurant'].restaurant_id
            )
            print('   ✅ Get restaurant profile completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #12: {e}')

        # Access Pattern #13: Scan restaurants filtering by cuisine type containing a keyword
        # Index: Main Table
        try:
            print(
                '🔍 Testing Access Pattern #13: Scan restaurants filtering by cuisine type containing a keyword'
            )
            print('   Using Main Table')
            result = self.restaurant_repo.scan_restaurants_by_cuisine('Italian')
            print(
                '   ✅ Scan restaurants filtering by cuisine type containing a keyword completed'
            )
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #13: {e}')

        # Access Pattern #14: Scan for active restaurants with rating above threshold
        # Index: Main Table
        try:
            print(
                '🔍 Testing Access Pattern #14: Scan for active restaurants with rating above threshold'
            )
            print('   Using Main Table')
            result = self.restaurant_repo.scan_high_rated_active_restaurants(Decimal('4.0'), True)
            print('   ✅ Scan for active restaurants with rating above threshold completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #14: {e}')

        # Driver
        # Access Pattern #15: Get driver by ID
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #15: Get driver by ID')
            print('   Using Main Table')
            result = self.driver_repo.get_driver(created_entities['Driver'].driver_id)
            print('   ✅ Get driver by ID completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #15: {e}')

        # Access Pattern #16: Scan drivers filtering by a skill tag and name prefix
        # Index: Main Table
        try:
            print(
                '🔍 Testing Access Pattern #16: Scan drivers filtering by a skill tag and name prefix'
            )
            print('   Using Main Table')
            result = self.driver_repo.scan_drivers_by_skill('express', 'A')
            print('   ✅ Scan drivers filtering by a skill tag and name prefix completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #16: {e}')

        # Access Pattern #17: Scan for available drivers with minimum deliveries and rating
        # Index: Main Table
        try:
            print(
                '🔍 Testing Access Pattern #17: Scan for available drivers with minimum deliveries and rating'
            )
            print('   Using Main Table')
            result = self.driver_repo.scan_available_experienced_drivers(True, 500, Decimal('4.5'))
            print('   ✅ Scan for available drivers with minimum deliveries and rating completed')
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
    print('   - DeliveryTable')
    print('   - RestaurantTable')
    print('   - DriverTable')

    if include_additional_access_patterns:
        print('🔍 Including additional access pattern examples')

    examples = UsageExamples()
    examples.run_examples(include_additional_access_patterns=include_additional_access_patterns)


if __name__ == '__main__':
    main()
