# Auto-generated entities
from __future__ import annotations

from base_repository import ConfigurableEntity, EntityConfig
from decimal import Decimal
from typing import Any


# User Entity Configuration
USER_CONFIG = EntityConfig(
    entity_type='USER',
    pk_builder=lambda entity: f'USER#{entity.user_id}',
    pk_lookup_builder=lambda user_id: f'USER#{user_id}',
    sk_builder=lambda entity: 'PROFILE',
    sk_lookup_builder=lambda: 'PROFILE',
    prefix_builder=lambda **kwargs: 'USER#',
)


class User(ConfigurableEntity):
    user_id: str
    email: str
    first_name: str
    last_name: str
    phone: str = None
    created_at: str
    status: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return USER_CONFIG


# UserAddress Entity Configuration
USERADDRESS_CONFIG = EntityConfig(
    entity_type='ADDRESS',
    pk_builder=lambda entity: f'USER#{entity.user_id}',
    pk_lookup_builder=lambda user_id: f'USER#{user_id}',
    sk_builder=lambda entity: f'ADDRESS#{entity.address_id}',
    sk_lookup_builder=lambda address_id: f'ADDRESS#{address_id}',
    prefix_builder=lambda **kwargs: 'ADDRESS#',
)


class UserAddress(ConfigurableEntity):
    user_id: str
    address_id: str
    address_type: str
    street_address: str
    city: str
    state: str
    postal_code: str
    country: str
    is_default: bool

    @classmethod
    def get_config(cls) -> EntityConfig:
        return USERADDRESS_CONFIG


# Product Entity Configuration
PRODUCT_CONFIG = EntityConfig(
    entity_type='PRODUCT',
    pk_builder=lambda entity: f'PRODUCT#{entity.product_id}',
    pk_lookup_builder=lambda product_id: f'PRODUCT#{product_id}',
    sk_builder=lambda entity: 'DETAILS',
    sk_lookup_builder=lambda: 'DETAILS',
    prefix_builder=lambda **kwargs: 'PRODUCT#',
)


class Product(ConfigurableEntity):
    product_id: str
    name: str
    description: str
    category: str
    brand: str
    price: Decimal
    currency: str
    stock_quantity: int
    sku: str
    weight: Decimal = None
    dimensions: dict[str, Any] = None
    created_at: str
    updated_at: str
    status: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return PRODUCT_CONFIG


# ProductCategory Entity Configuration
PRODUCTCATEGORY_CONFIG = EntityConfig(
    entity_type='CATEGORY',
    pk_builder=lambda entity: f'CATEGORY#{entity.category_name}',
    pk_lookup_builder=lambda category_name: f'CATEGORY#{category_name}',
    sk_builder=lambda entity: f'PRODUCT#{entity.product_id}',
    sk_lookup_builder=lambda product_id: f'PRODUCT#{product_id}',
    prefix_builder=lambda **kwargs: 'PRODUCT#',
)


class ProductCategory(ConfigurableEntity):
    category_name: str
    product_id: str
    product_name: str
    price: Decimal
    stock_quantity: int

    @classmethod
    def get_config(cls) -> EntityConfig:
        return PRODUCTCATEGORY_CONFIG


# ProductReview Entity Configuration
PRODUCTREVIEW_CONFIG = EntityConfig(
    entity_type='REVIEW',
    pk_builder=lambda entity: f'PRODUCT#{entity.product_id}',
    pk_lookup_builder=lambda product_id: f'PRODUCT#{product_id}',
    sk_builder=lambda entity: f'REVIEW#{entity.review_id}',
    sk_lookup_builder=lambda review_id: f'REVIEW#{review_id}',
    prefix_builder=lambda **kwargs: 'REVIEW#',
)


class ProductReview(ConfigurableEntity):
    product_id: str
    review_id: str
    user_id: str
    rating: int
    title: str
    comment: str = None
    created_at: str
    verified_purchase: bool

    @classmethod
    def get_config(cls) -> EntityConfig:
        return PRODUCTREVIEW_CONFIG


# Order Entity Configuration
ORDER_CONFIG = EntityConfig(
    entity_type='ORDER',
    pk_builder=lambda entity: f'ORDER#{entity.order_id}',
    pk_lookup_builder=lambda order_id: f'ORDER#{order_id}',
    sk_builder=lambda entity: 'DETAILS',
    sk_lookup_builder=lambda: 'DETAILS',
    prefix_builder=lambda **kwargs: 'ORDER#',
)


class Order(ConfigurableEntity):
    order_id: str
    user_id: str
    order_date: str
    status: str
    total_amount: Decimal
    currency: str
    shipping_address: dict[str, Any]
    billing_address: dict[str, Any]
    payment_method: str
    shipping_method: str
    tracking_number: str = None
    estimated_delivery: str = None
    created_at: str
    updated_at: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return ORDER_CONFIG


# OrderItem Entity Configuration
ORDERITEM_CONFIG = EntityConfig(
    entity_type='ORDER_ITEM',
    pk_builder=lambda entity: f'ORDER#{entity.order_id}',
    pk_lookup_builder=lambda order_id: f'ORDER#{order_id}',
    sk_builder=lambda entity: f'ITEM#{entity.product_id}',
    sk_lookup_builder=lambda product_id: f'ITEM#{product_id}',
    prefix_builder=lambda **kwargs: 'ITEM#',
)


class OrderItem(ConfigurableEntity):
    order_id: str
    product_id: str
    product_name: str
    sku: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    currency: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return ORDERITEM_CONFIG


# UserOrderHistory Entity Configuration
USERORDERHISTORY_CONFIG = EntityConfig(
    entity_type='USER_ORDER',
    pk_builder=lambda entity: f'USER#{entity.user_id}',
    pk_lookup_builder=lambda user_id: f'USER#{user_id}',
    sk_builder=lambda entity: f'ORDER#{entity.order_date}#{entity.order_id}',
    sk_lookup_builder=lambda order_date, order_id: f'ORDER#{order_date}#{order_id}',
    prefix_builder=lambda **kwargs: 'ORDER#',
)


class UserOrderHistory(ConfigurableEntity):
    user_id: str
    order_id: str
    order_date: str
    status: str
    total_amount: Decimal
    currency: str
    item_count: int

    @classmethod
    def get_config(cls) -> EntityConfig:
        return USERORDERHISTORY_CONFIG
