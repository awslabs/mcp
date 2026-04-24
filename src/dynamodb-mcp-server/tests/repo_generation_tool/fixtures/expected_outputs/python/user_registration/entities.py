# Auto-generated entities
from __future__ import annotations

from base_repository import ConfigurableEntity, EntityConfig


# User Entity Configuration
USER_CONFIG = EntityConfig(
    entity_type='USER',
    pk_builder=lambda entity: f'USER#{entity.user_id}',
    pk_lookup_builder=lambda user_id: f'USER#{user_id}',
    sk_builder=None,  # No sort key for this entity
    sk_lookup_builder=None,  # No sort key for this entity
    prefix_builder=None,  # No sort key prefix for this entity
)


class User(ConfigurableEntity):
    user_id: str
    email: str
    full_name: str
    created_at: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return USER_CONFIG


# EmailLookup Entity Configuration
EMAILLOOKUP_CONFIG = EntityConfig(
    entity_type='EMAIL_LOOKUP',
    pk_builder=lambda entity: f'EMAIL#{entity.email}',
    pk_lookup_builder=lambda email: f'EMAIL#{email}',
    sk_builder=None,  # No sort key for this entity
    sk_lookup_builder=None,  # No sort key for this entity
    prefix_builder=None,  # No sort key prefix for this entity
)


class EmailLookup(ConfigurableEntity):
    email: str
    user_id: str

    @classmethod
    def get_config(cls) -> EntityConfig:
        return EMAILLOOKUP_CONFIG
