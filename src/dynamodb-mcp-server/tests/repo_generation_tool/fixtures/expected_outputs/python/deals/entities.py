# Auto-generated entities
from __future__ import annotations

from base_repository import ConfigurableEntity, EntityConfig
from decimal import Decimal


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
    def build_gsi_pk_for_lookup_dealsbybrand(cls, brand_id) -> str:
        """Build GSI partition key for DealsByBrand lookup operations"""
        return f'{brand_id}'

    @classmethod
    def build_gsi_sk_for_lookup_dealsbybrand(cls, created_at) -> str:
        """Build GSI sort key for DealsByBrand lookup operations"""
        return f'{created_at}'

    @classmethod
    def build_gsi_pk_for_lookup_dealsbycategory(cls, category_id) -> str:
        """Build GSI partition key for DealsByCategory lookup operations"""
        return f'{category_id}'

    @classmethod
    def build_gsi_sk_for_lookup_dealsbycategory(cls, created_at) -> str:
        """Build GSI sort key for DealsByCategory lookup operations"""
        return f'{created_at}'

    # GSI Key Builder Instance Methods

    def build_gsi_pk_dealsbybrand(self) -> str:
        """Build GSI partition key for DealsByBrand from entity instance"""
        return f'{self.brand_id}'

    def build_gsi_sk_dealsbybrand(self) -> str:
        """Build GSI sort key for DealsByBrand from entity instance"""
        return f'{self.created_at}'

    def build_gsi_pk_dealsbycategory(self) -> str:
        """Build GSI partition key for DealsByCategory from entity instance"""
        return f'{self.category_id}'

    def build_gsi_sk_dealsbycategory(self) -> str:
        """Build GSI sort key for DealsByCategory from entity instance"""
        return f'{self.created_at}'

    # GSI Prefix Helper Methods

    @classmethod
    def get_gsi_pk_prefix_dealsbybrand(cls) -> str:
        """Get GSI partition key prefix for DealsByBrand query operations"""
        return ''

    @classmethod
    def get_gsi_sk_prefix_dealsbybrand(cls) -> str:
        """Get GSI sort key prefix for DealsByBrand query operations"""
        return ''

    @classmethod
    def get_gsi_pk_prefix_dealsbycategory(cls) -> str:
        """Get GSI partition key prefix for DealsByCategory query operations"""
        return ''

    @classmethod
    def get_gsi_sk_prefix_dealsbycategory(cls) -> str:
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
    target_id: str
    target_name: str
    brand_id: str = None
    category_id: str = None
    created_at: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return USERWATCH_CONFIG

    # GSI Key Builder Class Methods

    @classmethod
    def build_gsi_pk_for_lookup_watchesbybrand(cls, brand_id) -> str:
        """Build GSI partition key for WatchesByBrand lookup operations"""
        return f'{brand_id}'

    @classmethod
    def build_gsi_sk_for_lookup_watchesbybrand(cls, user_id) -> str:
        """Build GSI sort key for WatchesByBrand lookup operations"""
        return f'{user_id}'

    @classmethod
    def build_gsi_pk_for_lookup_watchesbycategory(cls, category_id) -> str:
        """Build GSI partition key for WatchesByCategory lookup operations"""
        return f'{category_id}'

    # GSI Key Builder Instance Methods

    def build_gsi_pk_watchesbybrand(self) -> str:
        """Build GSI partition key for WatchesByBrand from entity instance"""
        return f'{self.brand_id}'

    def build_gsi_sk_watchesbybrand(self) -> str:
        """Build GSI sort key for WatchesByBrand from entity instance"""
        return f'{self.user_id}'

    def build_gsi_pk_watchesbycategory(self) -> str:
        """Build GSI partition key for WatchesByCategory from entity instance"""
        return f'{self.category_id}'

    # GSI Prefix Helper Methods

    @classmethod
    def get_gsi_pk_prefix_watchesbybrand(cls) -> str:
        """Get GSI partition key prefix for WatchesByBrand query operations"""
        return ''

    @classmethod
    def get_gsi_sk_prefix_watchesbybrand(cls) -> str:
        """Get GSI sort key prefix for WatchesByBrand query operations"""
        return ''

    @classmethod
    def get_gsi_pk_prefix_watchesbycategory(cls) -> str:
        """Get GSI partition key prefix for WatchesByCategory query operations"""
        return ''
