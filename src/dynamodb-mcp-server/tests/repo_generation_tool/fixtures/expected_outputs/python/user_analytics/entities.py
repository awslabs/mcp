# Auto-generated entities
from __future__ import annotations

from base_repository import ConfigurableEntity, EntityConfig


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
    status: str
    last_active: str
    country: str
    city: str
    signup_date: str
    engagement_level: str
    session_count: int
    age_group: str
    total_sessions: int = None
    last_purchase_date: str = None

    @classmethod
    def get_config(cls) -> EntityConfig:
        return USER_CONFIG

    # GSI Key Builder Class Methods

    @classmethod
    def build_gsi_pk_for_lookup_statusindex(cls, status) -> str:
        """Build GSI partition key for StatusIndex lookup operations"""
        return f'STATUS#{status}'

    @classmethod
    def build_gsi_sk_for_lookup_statusindex(cls, last_active) -> str:
        """Build GSI sort key for StatusIndex lookup operations"""
        return f'{last_active}'

    @classmethod
    def build_gsi_pk_for_lookup_locationindex(cls, country) -> str:
        """Build GSI partition key for LocationIndex lookup operations"""
        return f'COUNTRY#{country}'

    @classmethod
    def build_gsi_sk_for_lookup_locationindex(cls, city) -> str:
        """Build GSI sort key for LocationIndex lookup operations"""
        return f'CITY#{city}'

    @classmethod
    def build_gsi_pk_for_lookup_engagementindex(cls, engagement_level) -> str:
        """Build GSI partition key for EngagementIndex lookup operations"""
        return f'ENGAGEMENT#{engagement_level}'

    @classmethod
    def build_gsi_sk_for_lookup_engagementindex(cls, session_count):
        """Build GSI sort key for EngagementIndex lookup operations"""
        return session_count

    @classmethod
    def build_gsi_pk_for_lookup_agegroupindex(cls, age_group) -> str:
        """Build GSI partition key for AgeGroupIndex lookup operations"""
        return f'AGE_GROUP#{age_group}'

    @classmethod
    def build_gsi_sk_for_lookup_agegroupindex(cls, signup_date) -> str:
        """Build GSI sort key for AgeGroupIndex lookup operations"""
        return f'{signup_date}'

    # GSI Key Builder Instance Methods

    def build_gsi_pk_statusindex(self) -> str:
        """Build GSI partition key for StatusIndex from entity instance"""
        return f'STATUS#{self.status}'

    def build_gsi_sk_statusindex(self) -> str:
        """Build GSI sort key for StatusIndex from entity instance"""
        return f'{self.last_active}'

    def build_gsi_pk_locationindex(self) -> str:
        """Build GSI partition key for LocationIndex from entity instance"""
        return f'COUNTRY#{self.country}'

    def build_gsi_sk_locationindex(self) -> str:
        """Build GSI sort key for LocationIndex from entity instance"""
        return f'CITY#{self.city}'

    def build_gsi_pk_engagementindex(self) -> str:
        """Build GSI partition key for EngagementIndex from entity instance"""
        return f'ENGAGEMENT#{self.engagement_level}'

    def build_gsi_sk_engagementindex(self):
        """Build GSI sort key for EngagementIndex from entity instance"""
        return self.session_count

    def build_gsi_pk_agegroupindex(self) -> str:
        """Build GSI partition key for AgeGroupIndex from entity instance"""
        return f'AGE_GROUP#{self.age_group}'

    def build_gsi_sk_agegroupindex(self) -> str:
        """Build GSI sort key for AgeGroupIndex from entity instance"""
        return f'{self.signup_date}'

    # GSI Prefix Helper Methods

    @classmethod
    def get_gsi_pk_prefix_statusindex(cls) -> str:
        """Get GSI partition key prefix for StatusIndex query operations"""
        return 'STATUS#'

    @classmethod
    def get_gsi_sk_prefix_statusindex(cls) -> str:
        """Get GSI sort key prefix for StatusIndex query operations"""
        return ''

    @classmethod
    def get_gsi_pk_prefix_locationindex(cls) -> str:
        """Get GSI partition key prefix for LocationIndex query operations"""
        return 'COUNTRY#'

    @classmethod
    def get_gsi_sk_prefix_locationindex(cls) -> str:
        """Get GSI sort key prefix for LocationIndex query operations"""
        return 'CITY#'

    @classmethod
    def get_gsi_pk_prefix_engagementindex(cls) -> str:
        """Get GSI partition key prefix for EngagementIndex query operations"""
        return 'ENGAGEMENT#'

    @classmethod
    def get_gsi_sk_prefix_engagementindex(cls) -> str:
        """Get GSI sort key prefix for EngagementIndex query operations"""
        return ''

    @classmethod
    def get_gsi_pk_prefix_agegroupindex(cls) -> str:
        """Get GSI partition key prefix for AgeGroupIndex query operations"""
        return 'AGE_GROUP#'

    @classmethod
    def get_gsi_sk_prefix_agegroupindex(cls) -> str:
        """Get GSI sort key prefix for AgeGroupIndex query operations"""
        return ''
