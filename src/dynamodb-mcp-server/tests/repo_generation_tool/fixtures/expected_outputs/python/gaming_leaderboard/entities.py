# Auto-generated entities
from __future__ import annotations

from base_repository import ConfigurableEntity, EntityConfig
from decimal import Decimal


# Game Entity Configuration
GAME_CONFIG = EntityConfig(
    entity_type='GAME',
    pk_builder=lambda entity: f'{entity.game_id}',
    pk_lookup_builder=lambda game_id: f'{game_id}',
    sk_builder=lambda entity: 'METADATA',
    sk_lookup_builder=lambda: 'METADATA',
    prefix_builder=lambda **kwargs: 'GAME#',
)


class Game(ConfigurableEntity):
    game_id: str
    title: str
    genre: str
    release_date: str
    publisher: str
    max_players: int = None
    is_active: bool

    @classmethod
    def get_config(cls) -> EntityConfig:
        return GAME_CONFIG


# LeaderboardEntry Entity Configuration
LEADERBOARDENTRY_CONFIG = EntityConfig(
    entity_type='SCORE',
    pk_builder=lambda entity: f'{entity.game_id}',
    pk_lookup_builder=lambda game_id: f'{game_id}',
    sk_builder=lambda entity: entity.score,
    sk_lookup_builder=lambda score: score,
    prefix_builder=lambda **kwargs: 'SCORE#',
)


class LeaderboardEntry(ConfigurableEntity):
    game_id: str
    score: int
    player_id: str
    player_name: str
    achieved_at: str
    level_reached: int = None
    play_duration_seconds: int = None

    @classmethod
    def get_config(cls) -> EntityConfig:
        return LEADERBOARDENTRY_CONFIG

    # GSI Key Builder Class Methods

    @classmethod
    def build_gsi_pk_for_lookup_playerscoresindex(cls, player_id) -> str:
        """Build GSI partition key for PlayerScoresIndex lookup operations"""
        return f'{player_id}'

    @classmethod
    def build_gsi_sk_for_lookup_playerscoresindex(cls, score):
        """Build GSI sort key for PlayerScoresIndex lookup operations"""
        return score

    # GSI Key Builder Instance Methods

    def build_gsi_pk_playerscoresindex(self) -> str:
        """Build GSI partition key for PlayerScoresIndex from entity instance"""
        return f'{self.player_id}'

    def build_gsi_sk_playerscoresindex(self):
        """Build GSI sort key for PlayerScoresIndex from entity instance"""
        return self.score

    # GSI Prefix Helper Methods

    @classmethod
    def get_gsi_pk_prefix_playerscoresindex(cls) -> str:
        """Get GSI partition key prefix for PlayerScoresIndex query operations"""
        return ''

    @classmethod
    def get_gsi_sk_prefix_playerscoresindex(cls) -> str:
        """Get GSI sort key prefix for PlayerScoresIndex query operations"""
        return ''


# PlayerAchievement Entity Configuration
PLAYERACHIEVEMENT_CONFIG = EntityConfig(
    entity_type='ACHIEVEMENT',
    pk_builder=lambda entity: f'{entity.player_id}',
    pk_lookup_builder=lambda player_id: f'{player_id}',
    sk_builder=lambda entity: f'{entity.achievement_id}',
    sk_lookup_builder=lambda achievement_id: f'{achievement_id}',
    prefix_builder=lambda **kwargs: 'ACHIEVEMENT#',
)


class PlayerAchievement(ConfigurableEntity):
    player_id: str
    achievement_id: str
    game_id: str
    achievement_name: str
    description: str = None
    points: int
    unlocked_at: str
    rarity: str = None

    @classmethod
    def get_config(cls) -> EntityConfig:
        return PLAYERACHIEVEMENT_CONFIG

    # GSI Key Builder Class Methods

    @classmethod
    def build_gsi_pk_for_lookup_gameachievementsindex(cls, game_id) -> str:
        """Build GSI partition key for GameAchievementsIndex lookup operations"""
        return f'{game_id}'

    @classmethod
    def build_gsi_sk_for_lookup_gameachievementsindex(cls, points):
        """Build GSI sort key for GameAchievementsIndex lookup operations"""
        return points

    # GSI Key Builder Instance Methods

    def build_gsi_pk_gameachievementsindex(self) -> str:
        """Build GSI partition key for GameAchievementsIndex from entity instance"""
        return f'{self.game_id}'

    def build_gsi_sk_gameachievementsindex(self):
        """Build GSI sort key for GameAchievementsIndex from entity instance"""
        return self.points

    # GSI Prefix Helper Methods

    @classmethod
    def get_gsi_pk_prefix_gameachievementsindex(cls) -> str:
        """Get GSI partition key prefix for GameAchievementsIndex query operations"""
        return ''

    @classmethod
    def get_gsi_sk_prefix_gameachievementsindex(cls) -> str:
        """Get GSI sort key prefix for GameAchievementsIndex query operations"""
        return ''


# TournamentEntry Entity Configuration
TOURNAMENTENTRY_CONFIG = EntityConfig(
    entity_type='TOURNAMENT',
    pk_builder=lambda entity: f'{entity.tournament_id}',
    pk_lookup_builder=lambda tournament_id: f'{tournament_id}',
    sk_builder=lambda entity: entity.ranking,
    sk_lookup_builder=lambda ranking: ranking,
    prefix_builder=lambda **kwargs: 'TOURNAMENT#',
)


class TournamentEntry(ConfigurableEntity):
    tournament_id: str
    ranking: int
    player_id: str
    player_name: str
    total_score: int
    matches_played: int
    wins: int = None
    prize_amount: Decimal = None

    @classmethod
    def get_config(cls) -> EntityConfig:
        return TOURNAMENTENTRY_CONFIG
