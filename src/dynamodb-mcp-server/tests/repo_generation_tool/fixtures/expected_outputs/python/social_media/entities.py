# Auto-generated entities
from __future__ import annotations

from base_repository import ConfigurableEntity, EntityConfig


# Comment Entity Configuration
COMMENT_CONFIG = EntityConfig(
    entity_type='COMMENT',
    pk_builder=lambda entity: f'{entity.user_id}',
    pk_lookup_builder=lambda user_id: f'{user_id}',
    sk_builder=lambda entity: f'COMMENT#{entity.post_id}#{entity.comment_id}',
    sk_lookup_builder=lambda post_id, comment_id: f'COMMENT#{post_id}#{comment_id}',
    prefix_builder=lambda **kwargs: 'COMMENT#',
)


class Comment(ConfigurableEntity):
    user_id: str
    post_id: str
    comment_id: str
    username: str
    content: str
    timestamp: int

    @classmethod
    def get_config(cls) -> EntityConfig:
        return COMMENT_CONFIG


# Follow Entity Configuration
FOLLOW_CONFIG = EntityConfig(
    entity_type='FOLLOW',
    pk_builder=lambda entity: f'{entity.user_id}',
    pk_lookup_builder=lambda user_id: f'{user_id}',
    sk_builder=lambda entity: f'FOLLOW#{entity.follower_id}',
    sk_lookup_builder=lambda follower_id: f'FOLLOW#{follower_id}',
    prefix_builder=lambda **kwargs: 'FOLLOW#',
)


class Follow(ConfigurableEntity):
    user_id: str
    follower_id: str
    username: str
    timestamp: int

    @classmethod
    def get_config(cls) -> EntityConfig:
        return FOLLOW_CONFIG


# Like Entity Configuration
LIKE_CONFIG = EntityConfig(
    entity_type='LIKE',
    pk_builder=lambda entity: f'{entity.user_id}',
    pk_lookup_builder=lambda user_id: f'{user_id}',
    sk_builder=lambda entity: f'LIKE#{entity.post_id}#{entity.liker_user_id}',
    sk_lookup_builder=lambda post_id, liker_user_id: f'LIKE#{post_id}#{liker_user_id}',
    prefix_builder=lambda **kwargs: 'LIKE#',
)


class Like(ConfigurableEntity):
    user_id: str
    post_id: str
    liker_user_id: str
    username: str
    timestamp: int

    @classmethod
    def get_config(cls) -> EntityConfig:
        return LIKE_CONFIG


# Post Entity Configuration
POST_CONFIG = EntityConfig(
    entity_type='POST',
    pk_builder=lambda entity: f'{entity.user_id}',
    pk_lookup_builder=lambda user_id: f'{user_id}',
    sk_builder=lambda entity: f'POST#{entity.post_id}',
    sk_lookup_builder=lambda post_id: f'POST#{post_id}',
    prefix_builder=lambda **kwargs: 'POST#',
)


class Post(ConfigurableEntity):
    user_id: str
    post_id: str
    username: str
    content: str
    media_urls: list[str] = None
    timestamp: int

    @classmethod
    def get_config(cls) -> EntityConfig:
        return POST_CONFIG


# UserProfile Entity Configuration
USERPROFILE_CONFIG = EntityConfig(
    entity_type='PROFILE',
    pk_builder=lambda entity: f'{entity.user_id}',
    pk_lookup_builder=lambda user_id: f'{user_id}',
    sk_builder=lambda entity: 'PROFILE',
    sk_lookup_builder=lambda: 'PROFILE',
    prefix_builder=lambda **kwargs: 'PROFILE#',
)


class UserProfile(ConfigurableEntity):
    user_id: str
    username: str
    email: str
    timestamp: int

    @classmethod
    def get_config(cls) -> EntityConfig:
        return USERPROFILE_CONFIG
