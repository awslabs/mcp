# Auto-generated entities
from __future__ import annotations

from base_repository import ConfigurableEntity, EntityConfig
from decimal import Decimal


# Delivery Entity Configuration
DELIVERY_CONFIG = EntityConfig(
    entity_type='DELIVERY',
    pk_builder=lambda entity: f'CUSTOMER#{entity.customer_id}',
    pk_lookup_builder=lambda customer_id: f'CUSTOMER#{customer_id}',
    sk_builder=lambda entity: f'DELIVERY#{entity.order_date}#{entity.delivery_id}',
    sk_lookup_builder=lambda order_date, delivery_id: f'DELIVERY#{order_date}#{delivery_id}',
    prefix_builder=lambda **kwargs: 'DELIVERY#',
)


class Delivery(ConfigurableEntity):
    customer_id: str
    delivery_id: str
    order_date: str
    restaurant_id: str
    driver_id: str = None
    status: str
    total: Decimal
    delivery_fee: Decimal
    tip: Decimal = None
    items: list[str]
    special_instructions: str = None
    cancelled_at: str = None
    estimated_delivery_time: str = None
    created_at: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return DELIVERY_CONFIG


# DeliveryEvent Entity Configuration
DELIVERYEVENT_CONFIG = EntityConfig(
    entity_type='DELIVERY_EVENT',
    pk_builder=lambda entity: f'DELIVERY#{entity.delivery_id}',
    pk_lookup_builder=lambda delivery_id: f'DELIVERY#{delivery_id}',
    sk_builder=lambda entity: f'EVENT#{entity.event_timestamp}#{entity.event_id}',
    sk_lookup_builder=lambda event_timestamp, event_id: f'EVENT#{event_timestamp}#{event_id}',
    prefix_builder=lambda **kwargs: 'EVENT#',
)


class DeliveryEvent(ConfigurableEntity):
    delivery_id: str
    event_id: str
    event_timestamp: str
    event_type: str
    description: str = None
    actor: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return DELIVERYEVENT_CONFIG


# Restaurant Entity Configuration
RESTAURANT_CONFIG = EntityConfig(
    entity_type='RESTAURANT',
    pk_builder=lambda entity: f'RESTAURANT#{entity.restaurant_id}',
    pk_lookup_builder=lambda restaurant_id: f'RESTAURANT#{restaurant_id}',
    sk_builder=lambda entity: 'PROFILE',
    sk_lookup_builder=lambda: 'PROFILE',
    prefix_builder=lambda **kwargs: 'RESTAURANT#',
)


class Restaurant(ConfigurableEntity):
    restaurant_id: str
    name: str
    cuisine_type: str
    rating: Decimal
    is_active: bool
    address: str
    created_at: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return RESTAURANT_CONFIG


# Driver Entity Configuration
DRIVER_CONFIG = EntityConfig(
    entity_type='DRIVER',
    pk_builder=lambda entity: f'DRIVER#{entity.driver_id}',
    pk_lookup_builder=lambda driver_id: f'DRIVER#{driver_id}',
    sk_builder=None,  # No sort key for this entity
    sk_lookup_builder=None,  # No sort key for this entity
    prefix_builder=None,  # No sort key prefix for this entity
)


class Driver(ConfigurableEntity):
    driver_id: str
    name: str
    phone: str
    vehicle_type: str
    tags: list[str] = None
    rating: Decimal
    total_deliveries: int
    is_available: bool
    created_at: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return DRIVER_CONFIG
