# Auto-generated entities
from __future__ import annotations

from base_repository import ConfigurableEntity, EntityConfig, KeyType
from decimal import Decimal
from typing import Any


# Recipient Entity Configuration
RECIPIENT_CONFIG = EntityConfig(
    entity_type='RECIPIENT',
    pk_builder=lambda entity: f'{entity.recipient_id}',
    pk_lookup_builder=lambda recipient_id: f'{recipient_id}',
    sk_builder=None,  # No sort key for this entity
    sk_lookup_builder=None,  # No sort key for this entity
    prefix_builder=None,  # No sort key prefix for this entity
)


class Recipient(ConfigurableEntity):
    recipient_id: str
    name: str
    email: str
    phone: str
    city: str
    created_at: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return RECIPIENT_CONFIG


# Courier Entity Configuration
COURIER_CONFIG = EntityConfig(
    entity_type='COURIER',
    pk_builder=lambda entity: f'{entity.courier_id}',
    pk_lookup_builder=lambda courier_id: f'{courier_id}',
    sk_builder=None,  # No sort key for this entity
    sk_lookup_builder=None,  # No sort key for this entity
    prefix_builder=None,  # No sort key prefix for this entity
)


class Courier(ConfigurableEntity):
    courier_id: str
    name: str
    email: str
    phone: str
    city: str
    vehicle_type: str
    created_at: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return COURIER_CONFIG


# Product Entity Configuration
PRODUCT_CONFIG = EntityConfig(
    entity_type='MENU',
    pk_builder=lambda entity: f'{entity.warehouse_id}',
    pk_lookup_builder=lambda warehouse_id: f'{warehouse_id}',
    sk_builder=lambda entity: f'MENU#{entity.category}#{entity.product_id}',
    sk_lookup_builder=lambda category, product_id: f'MENU#{category}#{product_id}',
    prefix_builder=lambda **kwargs: 'MENU#',
)


class Product(ConfigurableEntity):
    warehouse_id: str
    sort_key: str
    product_id: str
    category: str
    description: str
    price: Decimal
    available: bool
    city: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return PRODUCT_CONFIG

    # GSI Key Builder Class Methods

    @classmethod
    def build_gsi_pk_for_lookup_products_by_category(cls, city) -> KeyType:
        """Build GSI partition key for ProductsByCategory lookup operations"""
        return f'{city}'

    @classmethod
    def build_gsi_sk_for_lookup_products_by_category(cls, category, sort_key) -> tuple:
        """Build GSI multi-attribute sort key for ProductsByCategory lookup operations

        Returns tuple of key values in order: (category, sort_key)
        """
        return (f'{category}', f'{sort_key}')

    # GSI Key Builder Instance Methods

    def build_gsi_pk_products_by_category(self) -> KeyType:
        """Build GSI partition key for ProductsByCategory from entity instance"""
        return f'{self.city}'

    def build_gsi_sk_products_by_category(self) -> tuple:
        """Build GSI multi-attribute sort key for ProductsByCategory from entity instance

        Returns tuple of key values in order: (category, sort_key)
        """
        return (f'{self.category}', f'{self.sort_key}')

    # GSI Prefix Helper Methods

    @classmethod
    def get_gsi_pk_prefix_products_by_category(cls) -> str:
        """Get GSI partition key prefix for ProductsByCategory query operations"""
        return ''

    @classmethod
    def get_gsi_sk_prefix_products_by_category(cls) -> str:
        """Get GSI sort key prefix for ProductsByCategory query operations"""
        return "['{category}', '{sort_key}']"


# Rating Entity Configuration
RATING_CONFIG = EntityConfig(
    entity_type='REVIEW',
    pk_builder=lambda entity: f'{entity.warehouse_id}',
    pk_lookup_builder=lambda warehouse_id: f'{warehouse_id}',
    sk_builder=lambda entity: f'REVIEW#{entity.created_at}#{entity.rating_id}',
    sk_lookup_builder=lambda created_at, rating_id: f'REVIEW#{created_at}#{rating_id}',
    prefix_builder=lambda **kwargs: 'REVIEW#',
)


class Rating(ConfigurableEntity):
    warehouse_id: str
    sort_key: str
    rating_id: str
    recipient_name: str
    feedback: str
    score: int
    created_at: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return RATING_CONFIG


# WarehouseProfile Entity Configuration
WAREHOUSEPROFILE_CONFIG = EntityConfig(
    entity_type='PROFILE',
    pk_builder=lambda entity: f'{entity.warehouse_id}',
    pk_lookup_builder=lambda warehouse_id: f'{warehouse_id}',
    sk_builder=lambda entity: 'PROFILE',
    sk_lookup_builder=lambda: 'PROFILE',
    prefix_builder=lambda **kwargs: 'PROFILE#',
)


class WarehouseProfile(ConfigurableEntity):
    warehouse_id: str
    sort_key: str
    name: str
    address: str = None
    city: str
    category: str
    rating: Decimal
    processing_time: int
    created_at: str = None

    @classmethod
    def get_config(cls) -> EntityConfig:
        return WAREHOUSEPROFILE_CONFIG

    # GSI Key Builder Class Methods

    @classmethod
    def build_gsi_pk_for_lookup_warehouses_by_city(cls, city) -> KeyType:
        """Build GSI partition key for WarehousesByCity lookup operations"""
        return f'{city}'

    @classmethod
    def build_gsi_sk_for_lookup_warehouses_by_city(cls, category, rating) -> tuple:
        """Build GSI multi-attribute sort key for WarehousesByCity lookup operations

        Returns tuple of key values in order: (category, rating)
        """
        return (f'{category}', f'{rating}')

    @classmethod
    def build_gsi_pk_for_lookup_warehouses_by_name(cls, city) -> KeyType:
        """Build GSI partition key for WarehousesByName lookup operations"""
        return f'{city}'

    @classmethod
    def build_gsi_sk_for_lookup_warehouses_by_name(cls, name) -> KeyType:
        """Build GSI sort key for WarehousesByName lookup operations"""
        return f'{name}'

    # GSI Key Builder Instance Methods

    def build_gsi_pk_warehouses_by_city(self) -> KeyType:
        """Build GSI partition key for WarehousesByCity from entity instance"""
        return f'{self.city}'

    def build_gsi_sk_warehouses_by_city(self) -> tuple:
        """Build GSI multi-attribute sort key for WarehousesByCity from entity instance

        Returns tuple of key values in order: (category, rating)
        """
        return (f'{self.category}', f'{self.rating}')

    def build_gsi_pk_warehouses_by_name(self) -> KeyType:
        """Build GSI partition key for WarehousesByName from entity instance"""
        return f'{self.city}'

    def build_gsi_sk_warehouses_by_name(self) -> KeyType:
        """Build GSI sort key for WarehousesByName from entity instance"""
        return f'{self.name}'

    # GSI Prefix Helper Methods

    @classmethod
    def get_gsi_pk_prefix_warehouses_by_city(cls) -> str:
        """Get GSI partition key prefix for WarehousesByCity query operations"""
        return ''

    @classmethod
    def get_gsi_sk_prefix_warehouses_by_city(cls) -> str:
        """Get GSI sort key prefix for WarehousesByCity query operations"""
        return "['{category}', '{rating}']"

    @classmethod
    def get_gsi_pk_prefix_warehouses_by_name(cls) -> str:
        """Get GSI partition key prefix for WarehousesByName query operations"""
        return ''

    @classmethod
    def get_gsi_sk_prefix_warehouses_by_name(cls) -> str:
        """Get GSI sort key prefix for WarehousesByName query operations"""
        return ''


# Shipment Entity Configuration
SHIPMENT_CONFIG = EntityConfig(
    entity_type='SHIPMENT',
    pk_builder=lambda entity: f'{entity.shipment_id}',
    pk_lookup_builder=lambda shipment_id: f'{shipment_id}',
    sk_builder=None,  # No sort key for this entity
    sk_lookup_builder=None,  # No sort key for this entity
    prefix_builder=None,  # No sort key prefix for this entity
)


class Shipment(ConfigurableEntity):
    shipment_id: str
    recipient_id: str = None
    warehouse_id: str = None
    warehouse_name: str = None
    recipient_name: str = None
    status: str = None
    packages: list[dict[str, Any]] = None
    total_weight: Decimal = None
    destination_address: str = None
    origin_address: str = None
    created_at: str = None
    updated_at: str = None
    courier_id: str = None
    available_city: str = None
    active_delivery: str = None

    @classmethod
    def get_config(cls) -> EntityConfig:
        return SHIPMENT_CONFIG

    # GSI Key Builder Class Methods

    @classmethod
    def build_gsi_pk_for_lookup_shipments_by_recipient(cls, recipient_id) -> KeyType:
        """Build GSI partition key for ShipmentsByRecipient lookup operations"""
        return f'{recipient_id}'

    @classmethod
    def build_gsi_sk_for_lookup_shipments_by_recipient(cls, status, created_at) -> tuple:
        """Build GSI multi-attribute sort key for ShipmentsByRecipient lookup operations

        Returns tuple of key values in order: (status, created_at)
        """
        return (f'{status}', f'{created_at}')

    @classmethod
    def build_gsi_pk_for_lookup_shipments_by_warehouse(cls, warehouse_id) -> KeyType:
        """Build GSI partition key for ShipmentsByWarehouse lookup operations"""
        return f'{warehouse_id}'

    @classmethod
    def build_gsi_sk_for_lookup_shipments_by_warehouse(cls, status, created_at) -> tuple:
        """Build GSI multi-attribute sort key for ShipmentsByWarehouse lookup operations

        Returns tuple of key values in order: (status, created_at)
        """
        return (f'{status}', f'{created_at}')

    @classmethod
    def build_gsi_pk_for_lookup_shipments_by_courier(cls, courier_id) -> KeyType:
        """Build GSI partition key for ShipmentsByCourier lookup operations"""
        return f'{courier_id}'

    @classmethod
    def build_gsi_sk_for_lookup_shipments_by_courier(cls, status, created_at) -> tuple:
        """Build GSI multi-attribute sort key for ShipmentsByCourier lookup operations

        Returns tuple of key values in order: (status, created_at)
        """
        return (f'{status}', f'{created_at}')

    @classmethod
    def build_gsi_pk_for_lookup_available_shipments_by_city(cls, available_city) -> KeyType:
        """Build GSI partition key for AvailableShipmentsByCity lookup operations"""
        return f'{available_city}'

    @classmethod
    def build_gsi_sk_for_lookup_available_shipments_by_city(cls, created_at) -> KeyType:
        """Build GSI sort key for AvailableShipmentsByCity lookup operations"""
        return f'{created_at}'

    @classmethod
    def build_gsi_pk_for_lookup_courier_active_delivery(cls, active_delivery) -> KeyType:
        """Build GSI partition key for CourierActiveDelivery lookup operations"""
        return f'{active_delivery}'

    # GSI Key Builder Instance Methods

    def build_gsi_pk_shipments_by_recipient(self) -> KeyType:
        """Build GSI partition key for ShipmentsByRecipient from entity instance"""
        return f'{self.recipient_id}'

    def build_gsi_sk_shipments_by_recipient(self) -> tuple:
        """Build GSI multi-attribute sort key for ShipmentsByRecipient from entity instance

        Returns tuple of key values in order: (status, created_at)
        """
        return (f'{self.status}', f'{self.created_at}')

    def build_gsi_pk_shipments_by_warehouse(self) -> KeyType:
        """Build GSI partition key for ShipmentsByWarehouse from entity instance"""
        return f'{self.warehouse_id}'

    def build_gsi_sk_shipments_by_warehouse(self) -> tuple:
        """Build GSI multi-attribute sort key for ShipmentsByWarehouse from entity instance

        Returns tuple of key values in order: (status, created_at)
        """
        return (f'{self.status}', f'{self.created_at}')

    def build_gsi_pk_shipments_by_courier(self) -> KeyType:
        """Build GSI partition key for ShipmentsByCourier from entity instance"""
        return f'{self.courier_id}'

    def build_gsi_sk_shipments_by_courier(self) -> tuple:
        """Build GSI multi-attribute sort key for ShipmentsByCourier from entity instance

        Returns tuple of key values in order: (status, created_at)
        """
        return (f'{self.status}', f'{self.created_at}')

    def build_gsi_pk_available_shipments_by_city(self) -> KeyType:
        """Build GSI partition key for AvailableShipmentsByCity from entity instance"""
        return f'{self.available_city}'

    def build_gsi_sk_available_shipments_by_city(self) -> KeyType:
        """Build GSI sort key for AvailableShipmentsByCity from entity instance"""
        return f'{self.created_at}'

    def build_gsi_pk_courier_active_delivery(self) -> KeyType:
        """Build GSI partition key for CourierActiveDelivery from entity instance"""
        return f'{self.active_delivery}'

    # GSI Prefix Helper Methods

    @classmethod
    def get_gsi_pk_prefix_shipments_by_recipient(cls) -> str:
        """Get GSI partition key prefix for ShipmentsByRecipient query operations"""
        return ''

    @classmethod
    def get_gsi_sk_prefix_shipments_by_recipient(cls) -> str:
        """Get GSI sort key prefix for ShipmentsByRecipient query operations"""
        return "['{status}', '{created_at}']"

    @classmethod
    def get_gsi_pk_prefix_shipments_by_warehouse(cls) -> str:
        """Get GSI partition key prefix for ShipmentsByWarehouse query operations"""
        return ''

    @classmethod
    def get_gsi_sk_prefix_shipments_by_warehouse(cls) -> str:
        """Get GSI sort key prefix for ShipmentsByWarehouse query operations"""
        return "['{status}', '{created_at}']"

    @classmethod
    def get_gsi_pk_prefix_shipments_by_courier(cls) -> str:
        """Get GSI partition key prefix for ShipmentsByCourier query operations"""
        return ''

    @classmethod
    def get_gsi_sk_prefix_shipments_by_courier(cls) -> str:
        """Get GSI sort key prefix for ShipmentsByCourier query operations"""
        return "['{status}', '{created_at}']"

    @classmethod
    def get_gsi_pk_prefix_available_shipments_by_city(cls) -> str:
        """Get GSI partition key prefix for AvailableShipmentsByCity query operations"""
        return ''

    @classmethod
    def get_gsi_sk_prefix_available_shipments_by_city(cls) -> str:
        """Get GSI sort key prefix for AvailableShipmentsByCity query operations"""
        return ''

    @classmethod
    def get_gsi_pk_prefix_courier_active_delivery(cls) -> str:
        """Get GSI partition key prefix for CourierActiveDelivery query operations"""
        return ''
