# Auto-generated entities
from __future__ import annotations

from base_repository import ConfigurableEntity, EntityConfig, KeyType
from decimal import Decimal
from typing import Any


# Deal Entity Configuration
DEAL_CONFIG = EntityConfig(
    entity_type='DEAL',
    pk_builder=lambda entity: f'{entity.deal_id}',
    pk_lookup_builder=lambda deal_id: f'{deal_id}',
    sk_builder=None,  # No sort key for this entity
    sk_lookup_builder=None,  # No sort key for this entity
    prefix_builder=None,  # No sort key prefix for this entity
)


class Deal(ConfigurableEntity):
    deal_id: str
    title: str
    description: str
    price: Decimal
    brand_id: str
    brand_name: str
    category_id: str
    category_name: str
    created_at: str
    status: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return DEAL_CONFIG

    # GSI Key Builder Class Methods

    @classmethod
    def build_gsi_pk_for_lookup_deals_by_brand(cls, brand_id) -> KeyType:
        """Build GSI partition key for DealsByBrand lookup operations"""
        return f'{brand_id}'

    @classmethod
    def build_gsi_sk_for_lookup_deals_by_brand(cls, created_at) -> KeyType:
        """Build GSI sort key for DealsByBrand lookup operations"""
        return f'{created_at}'

    @classmethod
    def build_gsi_pk_for_lookup_deals_by_category(cls, category_id) -> KeyType:
        """Build GSI partition key for DealsByCategory lookup operations"""
        return f'{category_id}'

    @classmethod
    def build_gsi_sk_for_lookup_deals_by_category(cls, created_at) -> KeyType:
        """Build GSI sort key for DealsByCategory lookup operations"""
        return f'{created_at}'

    # GSI Key Builder Instance Methods

    def build_gsi_pk_deals_by_brand(self) -> KeyType:
        """Build GSI partition key for DealsByBrand from entity instance"""
        return f'{self.brand_id}'

    def build_gsi_sk_deals_by_brand(self) -> KeyType:
        """Build GSI sort key for DealsByBrand from entity instance"""
        return f'{self.created_at}'

    def build_gsi_pk_deals_by_category(self) -> KeyType:
        """Build GSI partition key for DealsByCategory from entity instance"""
        return f'{self.category_id}'

    def build_gsi_sk_deals_by_category(self) -> KeyType:
        """Build GSI sort key for DealsByCategory from entity instance"""
        return f'{self.created_at}'

    # GSI Prefix Helper Methods

    @classmethod
    def get_gsi_pk_prefix_deals_by_brand(cls) -> str:
        """Get GSI partition key prefix for DealsByBrand query operations"""
        return ''

    @classmethod
    def get_gsi_sk_prefix_deals_by_brand(cls) -> str:
        """Get GSI sort key prefix for DealsByBrand query operations"""
        return ''

    @classmethod
    def get_gsi_pk_prefix_deals_by_category(cls) -> str:
        """Get GSI partition key prefix for DealsByCategory query operations"""
        return ''

    @classmethod
    def get_gsi_sk_prefix_deals_by_category(cls) -> str:
        """Get GSI sort key prefix for DealsByCategory query operations"""
        return ''


# User Entity Configuration
USER_CONFIG = EntityConfig(
    entity_type='USER',
    pk_builder=lambda entity: f'{entity.user_id}',
    pk_lookup_builder=lambda user_id: f'{user_id}',
    sk_builder=None,  # No sort key for this entity
    sk_lookup_builder=None,  # No sort key for this entity
    prefix_builder=None,  # No sort key prefix for this entity
)


class User(ConfigurableEntity):
    user_id: str
    username: str
    email: str
    display_name: str
    created_at: str
    last_login: str = None

    @classmethod
    def get_config(cls) -> EntityConfig:
        return USER_CONFIG


# Brand Entity Configuration
BRAND_CONFIG = EntityConfig(
    entity_type='BRAND',
    pk_builder=lambda entity: f'{entity.brand_id}',
    pk_lookup_builder=lambda brand_id: f'{brand_id}',
    sk_builder=None,  # No sort key for this entity
    sk_lookup_builder=None,  # No sort key for this entity
    prefix_builder=None,  # No sort key prefix for this entity
)


class Brand(ConfigurableEntity):
    brand_id: str
    brand_name: str
    description: str = None
    logo_url: str = None
    created_at: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return BRAND_CONFIG


# UserWatch Entity Configuration
USERWATCH_CONFIG = EntityConfig(
    entity_type='WATCH',
    pk_builder=lambda entity: f'{entity.user_id}',
    pk_lookup_builder=lambda user_id: f'{user_id}',
    sk_builder=lambda entity: f'{entity.watch_key}',
    sk_lookup_builder=lambda watch_key: f'{watch_key}',
    prefix_builder=lambda **kwargs: 'WATCH#',
)


class UserWatch(ConfigurableEntity):
    user_id: str
    watch_key: str
    watch_type: str
    target_id: str = None
    target_name: str = None
    brand_id: str = None
    category_id: str = None
    created_at: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return USERWATCH_CONFIG

    # GSI Key Builder Class Methods

    @classmethod
    def build_gsi_pk_for_lookup_watches_by_brand(cls, brand_id) -> KeyType:
        """Build GSI partition key for WatchesByBrand lookup operations"""
        return f'{brand_id}'

    @classmethod
    def build_gsi_sk_for_lookup_watches_by_brand(cls, user_id) -> KeyType:
        """Build GSI sort key for WatchesByBrand lookup operations"""
        return f'{user_id}'

    @classmethod
    def build_gsi_pk_for_lookup_watches_by_category(cls, category_id) -> KeyType:
        """Build GSI partition key for WatchesByCategory lookup operations"""
        return f'{category_id}'

    @classmethod
    def build_gsi_pk_for_lookup_watches_by_type(cls, watch_type) -> KeyType:
        """Build GSI partition key for WatchesByType lookup operations"""
        return f'{watch_type}'

    @classmethod
    def build_gsi_sk_for_lookup_watches_by_type(cls, created_at) -> KeyType:
        """Build GSI sort key for WatchesByType lookup operations"""
        return f'{created_at}'

    # GSI Key Builder Instance Methods

    def build_gsi_pk_watches_by_brand(self) -> KeyType:
        """Build GSI partition key for WatchesByBrand from entity instance"""
        return f'{self.brand_id}'

    def build_gsi_sk_watches_by_brand(self) -> KeyType:
        """Build GSI sort key for WatchesByBrand from entity instance"""
        return f'{self.user_id}'

    def build_gsi_pk_watches_by_category(self) -> KeyType:
        """Build GSI partition key for WatchesByCategory from entity instance"""
        return f'{self.category_id}'

    def build_gsi_pk_watches_by_type(self) -> KeyType:
        """Build GSI partition key for WatchesByType from entity instance"""
        return f'{self.watch_type}'

    def build_gsi_sk_watches_by_type(self) -> KeyType:
        """Build GSI sort key for WatchesByType from entity instance"""
        return f'{self.created_at}'

    # GSI Prefix Helper Methods

    @classmethod
    def get_gsi_pk_prefix_watches_by_brand(cls) -> str:
        """Get GSI partition key prefix for WatchesByBrand query operations"""
        return ''

    @classmethod
    def get_gsi_sk_prefix_watches_by_brand(cls) -> str:
        """Get GSI sort key prefix for WatchesByBrand query operations"""
        return ''

    @classmethod
    def get_gsi_pk_prefix_watches_by_category(cls) -> str:
        """Get GSI partition key prefix for WatchesByCategory query operations"""
        return ''

    @classmethod
    def get_gsi_pk_prefix_watches_by_type(cls) -> str:
        """Get GSI partition key prefix for WatchesByType query operations"""
        return ''

    @classmethod
    def get_gsi_sk_prefix_watches_by_type(cls) -> str:
        """Get GSI sort key prefix for WatchesByType query operations"""
        return ''


# UserActivity Entity Configuration
USERACTIVITY_CONFIG = EntityConfig(
    entity_type='ACTIVITY',
    pk_builder=lambda entity: f'{entity.user_id}',
    pk_lookup_builder=lambda user_id: f'{user_id}',
    sk_builder=lambda entity: f'{entity.timestamp}#{entity.activity_id}',
    sk_lookup_builder=lambda timestamp, activity_id: f'{timestamp}#{activity_id}',
    prefix_builder=lambda **kwargs: 'ACTIVITY#',
)


class UserActivity(ConfigurableEntity):
    user_id: str
    timestamp: str
    activity_id: str
    activity_type: str
    details: dict[str, Any] = None

    @classmethod
    def get_config(cls) -> EntityConfig:
        return USERACTIVITY_CONFIG


# TrendingDeal Entity Configuration
TRENDINGDEAL_CONFIG = EntityConfig(
    entity_type='TRENDING',
    pk_builder=lambda entity: f'{entity.category_id}',
    pk_lookup_builder=lambda category_id: f'{category_id}',
    sk_builder=lambda entity: entity.engagement_score,
    sk_lookup_builder=lambda engagement_score: engagement_score,
    prefix_builder=lambda **kwargs: 'TRENDING#',
)


class TrendingDeal(ConfigurableEntity):
    category_id: str
    engagement_score: int
    deal_id: str
    title: str
    brand_id: str
    discount_percentage: Decimal
    views: int
    clicks: int

    @classmethod
    def get_config(cls) -> EntityConfig:
        return TRENDINGDEAL_CONFIG

    # GSI Key Builder Class Methods

    @classmethod
    def build_gsi_pk_for_lookup_trending_by_discount(cls, brand_id) -> KeyType:
        """Build GSI partition key for TrendingByDiscount lookup operations"""
        return f'{brand_id}'

    @classmethod
    def build_gsi_sk_for_lookup_trending_by_discount(cls, discount_percentage) -> KeyType:
        """Build GSI sort key for TrendingByDiscount lookup operations"""
        return discount_percentage

    # GSI Key Builder Instance Methods

    def build_gsi_pk_trending_by_discount(self) -> KeyType:
        """Build GSI partition key for TrendingByDiscount from entity instance"""
        return f'{self.brand_id}'

    def build_gsi_sk_trending_by_discount(self) -> KeyType:
        """Build GSI sort key for TrendingByDiscount from entity instance"""
        return self.discount_percentage

    # GSI Prefix Helper Methods

    @classmethod
    def get_gsi_pk_prefix_trending_by_discount(cls) -> str:
        """Get GSI partition key prefix for TrendingByDiscount query operations"""
        return ''

    @classmethod
    def get_gsi_sk_prefix_trending_by_discount(cls) -> str:
        """Get GSI sort key prefix for TrendingByDiscount query operations"""
        return ''
