"""Generated usage examples for DynamoDB entities and repositories"""

from __future__ import annotations

import os
import sys
from decimal import Decimal

# Import generated entities and repositories
from entities import Game, LeaderboardEntry, PlayerAchievement, TournamentEntry
from repositories import (
    GameRepository,
    LeaderboardEntryRepository,
    PlayerAchievementRepository,
    TournamentEntryRepository,
)


class UsageExamples:
    """Examples of using the generated entities and repositories"""

    def __init__(self):
        """Initialize repositories with default table names from schema."""
        # Initialize repositories with their respective table names
        # GameTable table repositories
        try:
            self.game_repo = GameRepository('GameTable')
            print("✅ Initialized GameRepository for table 'GameTable'")
        except Exception as e:
            print(f'❌ Failed to initialize GameRepository: {e}')
            self.game_repo = None
        # LeaderboardTable table repositories
        try:
            self.leaderboardentry_repo = LeaderboardEntryRepository('LeaderboardTable')
            print("✅ Initialized LeaderboardEntryRepository for table 'LeaderboardTable'")
        except Exception as e:
            print(f'❌ Failed to initialize LeaderboardEntryRepository: {e}')
            self.leaderboardentry_repo = None
        # AchievementTable table repositories
        try:
            self.playerachievement_repo = PlayerAchievementRepository('AchievementTable')
            print("✅ Initialized PlayerAchievementRepository for table 'AchievementTable'")
        except Exception as e:
            print(f'❌ Failed to initialize PlayerAchievementRepository: {e}')
            self.playerachievement_repo = None
        # TournamentTable table repositories
        try:
            self.tournamententry_repo = TournamentEntryRepository('TournamentTable')
            print("✅ Initialized TournamentEntryRepository for table 'TournamentTable'")
        except Exception as e:
            print(f'❌ Failed to initialize TournamentEntryRepository: {e}')
            self.tournamententry_repo = None

    def run_examples(self, include_additional_access_patterns: bool = False):
        """Run CRUD examples for all entities"""
        # Dictionary to store created entities for access pattern testing
        created_entities = {}

        # Step 0: Cleanup any leftover entities from previous runs (makes tests idempotent)
        print('🧹 Pre-test Cleanup: Removing any leftover entities from previous runs')
        print('=' * 50)
        # Try to delete Game (game_id)
        try:
            sample_game = Game(
                game_id='game-12345',
                title='Space Defenders',
                genre='Action',
                release_date='2024-01-01T00:00:00Z',
                publisher='Galactic Games Studio',
                max_players=4,
                is_active=True,
                verification_code='sample_verification_code',
            )
            self.game_repo.delete_game(sample_game.game_id)
            print('   🗑️  Deleted leftover game (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete LeaderboardEntry (game_id, score)
        try:
            sample_leaderboardentry = LeaderboardEntry(
                game_id='game-12345',
                score=85000,
                player_id='player-67890',
                player_name='ProGamer123',
                achieved_at='2024-01-20T14:30:00Z',
                level_reached=15,
                play_duration_seconds=2700,
            )
            self.leaderboardentry_repo.delete_leaderboard_entry(
                sample_leaderboardentry.game_id, sample_leaderboardentry.score
            )
            print('   🗑️  Deleted leftover leaderboardentry (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete PlayerAchievement (player_id, achievement_id)
        try:
            sample_playerachievement = PlayerAchievement(
                player_id='player-67890',
                achievement_id='achievement-11111',
                game_id='game-12345',
                achievement_name='First Victory',
                description='Win your first game',
                points=100,
                unlocked_at='2024-01-18T16:45:00Z',
                rarity='common',
            )
            self.playerachievement_repo.delete_player_achievement(
                sample_playerachievement.player_id, sample_playerachievement.achievement_id
            )
            print('   🗑️  Deleted leftover playerachievement (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        # Try to delete TournamentEntry (tournament_id, ranking)
        try:
            sample_tournamententry = TournamentEntry(
                tournament_id='tournament-22222',
                ranking=5,
                player_id='player-67890',
                player_name='ProGamer123',
                total_score=78000,
                matches_played=3,
                wins=2,
                prize_amount=Decimal('150.0'),
            )
            self.tournamententry_repo.delete_tournament_entry(
                sample_tournamententry.tournament_id, sample_tournamententry.ranking
            )
            print('   🗑️  Deleted leftover tournamententry (if existed)')
        except Exception:
            pass  # Ignore errors - item might not exist
        print('✅ Pre-test cleanup completed\n')

        print('Running Repository Examples')
        print('=' * 50)
        print('\n=== GameTable Table Operations ===')

        # Game example
        print('\n--- Game ---')

        # 1. CREATE - Create sample game
        sample_game = Game(
            game_id='game-12345',
            title='Space Defenders',
            genre='Action',
            release_date='2024-01-01T00:00:00Z',
            publisher='Galactic Games Studio',
            max_players=4,
            is_active=True,
            verification_code='sample_verification_code',
        )

        print('📝 Creating game...')
        print(f'📝 PK: {sample_game.pk()}, SK: {sample_game.sk()}')

        try:
            created_game = self.game_repo.create_game(sample_game)
            print(f'✅ Created: {created_game}')
            # Store created entity for access pattern testing
            created_entities['Game'] = created_game
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  game already exists, retrieving existing entity...')
                try:
                    existing_game = self.game_repo.get_game(sample_game.game_id)

                    if existing_game:
                        print(f'✅ Retrieved existing: {existing_game}')
                        # Store existing entity for access pattern testing
                        created_entities['Game'] = existing_game
                    else:
                        print('❌ Failed to retrieve existing game')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing game: {get_error}')
            else:
                print(f'❌ Failed to create game: {e}')
        # 2. UPDATE - Update non-key field (title)
        if 'Game' in created_entities:
            print('\n🔄 Updating title field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['Game']
                refreshed_entity = self.game_repo.get_game(entity_for_refresh.game_id)

                if refreshed_entity:
                    original_value = refreshed_entity.title
                    refreshed_entity.title = 'Space Defenders: Ultimate Edition'

                    updated_game = self.game_repo.update_game(refreshed_entity)
                    print(f'✅ Updated title: {original_value} → {updated_game.title}')

                    # Update stored entity with updated values
                    created_entities['Game'] = updated_game
                else:
                    print('❌ Could not refresh game for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(f'⚠️  game was modified by another process (optimistic locking): {e}')
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update game: {e}')

        # 3. GET - Retrieve and print the entity
        if 'Game' in created_entities:
            print('\n🔍 Retrieving game...')
            try:
                entity_for_get = created_entities['Game']
                retrieved_game = self.game_repo.get_game(entity_for_get.game_id)

                if retrieved_game:
                    print(f'✅ Retrieved: {retrieved_game}')
                else:
                    print('❌ Failed to retrieve game')
            except Exception as e:
                print(f'❌ Failed to retrieve game: {e}')

        print('🎯 Game CRUD cycle completed!')
        print('\n=== LeaderboardTable Table Operations ===')

        # LeaderboardEntry example
        print('\n--- LeaderboardEntry ---')

        # 1. CREATE - Create sample leaderboardentry
        sample_leaderboardentry = LeaderboardEntry(
            game_id='game-12345',
            score=85000,
            player_id='player-67890',
            player_name='ProGamer123',
            achieved_at='2024-01-20T14:30:00Z',
            level_reached=15,
            play_duration_seconds=2700,
        )

        print('📝 Creating leaderboardentry...')
        print(f'📝 PK: {sample_leaderboardentry.pk()}, SK: {sample_leaderboardentry.sk()}')

        try:
            created_leaderboardentry = self.leaderboardentry_repo.create_leaderboard_entry(
                sample_leaderboardentry
            )
            print(f'✅ Created: {created_leaderboardentry}')
            # Store created entity for access pattern testing
            created_entities['LeaderboardEntry'] = created_leaderboardentry
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  leaderboardentry already exists, retrieving existing entity...')
                try:
                    existing_leaderboardentry = self.leaderboardentry_repo.get_leaderboard_entry(
                        sample_leaderboardentry.game_id, sample_leaderboardentry.score
                    )

                    if existing_leaderboardentry:
                        print(f'✅ Retrieved existing: {existing_leaderboardentry}')
                        # Store existing entity for access pattern testing
                        created_entities['LeaderboardEntry'] = existing_leaderboardentry
                    else:
                        print('❌ Failed to retrieve existing leaderboardentry')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing leaderboardentry: {get_error}')
            else:
                print(f'❌ Failed to create leaderboardentry: {e}')
        # 2. UPDATE - Update non-key field (score)
        if 'LeaderboardEntry' in created_entities:
            print('\n🔄 Updating score field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['LeaderboardEntry']
                refreshed_entity = self.leaderboardentry_repo.get_leaderboard_entry(
                    entity_for_refresh.game_id, entity_for_refresh.score
                )

                if refreshed_entity:
                    original_value = refreshed_entity.score
                    refreshed_entity.score = 92000

                    updated_leaderboardentry = self.leaderboardentry_repo.update_leaderboard_entry(
                        refreshed_entity
                    )
                    print(f'✅ Updated score: {original_value} → {updated_leaderboardentry.score}')

                    # Update stored entity with updated values
                    created_entities['LeaderboardEntry'] = updated_leaderboardentry
                else:
                    print('❌ Could not refresh leaderboardentry for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  leaderboardentry was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update leaderboardentry: {e}')

        # 3. GET - Retrieve and print the entity
        if 'LeaderboardEntry' in created_entities:
            print('\n🔍 Retrieving leaderboardentry...')
            try:
                entity_for_get = created_entities['LeaderboardEntry']
                retrieved_leaderboardentry = self.leaderboardentry_repo.get_leaderboard_entry(
                    entity_for_get.game_id, entity_for_get.score
                )

                if retrieved_leaderboardentry:
                    print(f'✅ Retrieved: {retrieved_leaderboardentry}')
                else:
                    print('❌ Failed to retrieve leaderboardentry')
            except Exception as e:
                print(f'❌ Failed to retrieve leaderboardentry: {e}')

        print('🎯 LeaderboardEntry CRUD cycle completed!')
        print('\n=== AchievementTable Table Operations ===')

        # PlayerAchievement example
        print('\n--- PlayerAchievement ---')

        # 1. CREATE - Create sample playerachievement
        sample_playerachievement = PlayerAchievement(
            player_id='player-67890',
            achievement_id='achievement-11111',
            game_id='game-12345',
            achievement_name='First Victory',
            description='Win your first game',
            points=100,
            unlocked_at='2024-01-18T16:45:00Z',
            rarity='common',
        )

        print('📝 Creating playerachievement...')
        print(f'📝 PK: {sample_playerachievement.pk()}, SK: {sample_playerachievement.sk()}')

        try:
            created_playerachievement = self.playerachievement_repo.create_player_achievement(
                sample_playerachievement
            )
            print(f'✅ Created: {created_playerachievement}')
            # Store created entity for access pattern testing
            created_entities['PlayerAchievement'] = created_playerachievement
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  playerachievement already exists, retrieving existing entity...')
                try:
                    existing_playerachievement = (
                        self.playerachievement_repo.get_player_achievement(
                            sample_playerachievement.player_id,
                            sample_playerachievement.achievement_id,
                        )
                    )

                    if existing_playerachievement:
                        print(f'✅ Retrieved existing: {existing_playerachievement}')
                        # Store existing entity for access pattern testing
                        created_entities['PlayerAchievement'] = existing_playerachievement
                    else:
                        print('❌ Failed to retrieve existing playerachievement')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing playerachievement: {get_error}')
            else:
                print(f'❌ Failed to create playerachievement: {e}')
        # 2. UPDATE - Update non-key field (achievement_name)
        if 'PlayerAchievement' in created_entities:
            print('\n🔄 Updating achievement_name field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['PlayerAchievement']
                refreshed_entity = self.playerachievement_repo.get_player_achievement(
                    entity_for_refresh.player_id, entity_for_refresh.achievement_id
                )

                if refreshed_entity:
                    original_value = refreshed_entity.achievement_name
                    refreshed_entity.achievement_name = 'First Victory - Updated'

                    updated_playerachievement = (
                        self.playerachievement_repo.update_player_achievement(refreshed_entity)
                    )
                    print(
                        f'✅ Updated achievement_name: {original_value} → {updated_playerachievement.achievement_name}'
                    )

                    # Update stored entity with updated values
                    created_entities['PlayerAchievement'] = updated_playerachievement
                else:
                    print('❌ Could not refresh playerachievement for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  playerachievement was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update playerachievement: {e}')

        # 3. GET - Retrieve and print the entity
        if 'PlayerAchievement' in created_entities:
            print('\n🔍 Retrieving playerachievement...')
            try:
                entity_for_get = created_entities['PlayerAchievement']
                retrieved_playerachievement = self.playerachievement_repo.get_player_achievement(
                    entity_for_get.player_id, entity_for_get.achievement_id
                )

                if retrieved_playerachievement:
                    print(f'✅ Retrieved: {retrieved_playerachievement}')
                else:
                    print('❌ Failed to retrieve playerachievement')
            except Exception as e:
                print(f'❌ Failed to retrieve playerachievement: {e}')

        print('🎯 PlayerAchievement CRUD cycle completed!')
        print('\n=== TournamentTable Table Operations ===')

        # TournamentEntry example
        print('\n--- TournamentEntry ---')

        # 1. CREATE - Create sample tournamententry
        sample_tournamententry = TournamentEntry(
            tournament_id='tournament-22222',
            ranking=5,
            player_id='player-67890',
            player_name='ProGamer123',
            total_score=78000,
            matches_played=3,
            wins=2,
            prize_amount=Decimal('150.0'),
        )

        print('📝 Creating tournamententry...')
        print(f'📝 PK: {sample_tournamententry.pk()}, SK: {sample_tournamententry.sk()}')

        try:
            created_tournamententry = self.tournamententry_repo.create_tournament_entry(
                sample_tournamententry
            )
            print(f'✅ Created: {created_tournamententry}')
            # Store created entity for access pattern testing
            created_entities['TournamentEntry'] = created_tournamententry
        except Exception as e:
            # Check if the error is due to item already existing
            if 'ConditionalCheckFailedException' in str(e) or 'already exists' in str(e).lower():
                print('⚠️  tournamententry already exists, retrieving existing entity...')
                try:
                    existing_tournamententry = self.tournamententry_repo.get_tournament_entry(
                        sample_tournamententry.tournament_id, sample_tournamententry.ranking
                    )

                    if existing_tournamententry:
                        print(f'✅ Retrieved existing: {existing_tournamententry}')
                        # Store existing entity for access pattern testing
                        created_entities['TournamentEntry'] = existing_tournamententry
                    else:
                        print('❌ Failed to retrieve existing tournamententry')
                except Exception as get_error:
                    print(f'❌ Failed to retrieve existing tournamententry: {get_error}')
            else:
                print(f'❌ Failed to create tournamententry: {e}')
        # 2. UPDATE - Update non-key field (ranking)
        if 'TournamentEntry' in created_entities:
            print('\n🔄 Updating ranking field...')
            try:
                # Refresh entity to get latest version (handles optimistic locking)
                entity_for_refresh = created_entities['TournamentEntry']
                refreshed_entity = self.tournamententry_repo.get_tournament_entry(
                    entity_for_refresh.tournament_id, entity_for_refresh.ranking
                )

                if refreshed_entity:
                    original_value = refreshed_entity.ranking
                    refreshed_entity.ranking = 3

                    updated_tournamententry = self.tournamententry_repo.update_tournament_entry(
                        refreshed_entity
                    )
                    print(
                        f'✅ Updated ranking: {original_value} → {updated_tournamententry.ranking}'
                    )

                    # Update stored entity with updated values
                    created_entities['TournamentEntry'] = updated_tournamententry
                else:
                    print('❌ Could not refresh tournamententry for update')
            except Exception as e:
                if 'version' in str(e).lower() or 'modified by another process' in str(e).lower():
                    print(
                        f'⚠️  tournamententry was modified by another process (optimistic locking): {e}'
                    )
                    print('💡 This is expected behavior in concurrent environments')
                else:
                    print(f'❌ Failed to update tournamententry: {e}')

        # 3. GET - Retrieve and print the entity
        if 'TournamentEntry' in created_entities:
            print('\n🔍 Retrieving tournamententry...')
            try:
                entity_for_get = created_entities['TournamentEntry']
                retrieved_tournamententry = self.tournamententry_repo.get_tournament_entry(
                    entity_for_get.tournament_id, entity_for_get.ranking
                )

                if retrieved_tournamententry:
                    print(f'✅ Retrieved: {retrieved_tournamententry}')
                else:
                    print('❌ Failed to retrieve tournamententry')
            except Exception as e:
                print(f'❌ Failed to retrieve tournamententry: {e}')

        print('🎯 TournamentEntry CRUD cycle completed!')

        print('\n' + '=' * 50)
        print('🎉 Basic CRUD examples completed!')

        # Additional Access Pattern Testing Section (before cleanup)
        if include_additional_access_patterns:
            self._test_additional_access_patterns(created_entities)

        # Cleanup - Delete all created entities
        print('\n' + '=' * 50)
        print('🗑️  Cleanup: Deleting all created entities')
        print('=' * 50)

        # Delete Game
        if 'Game' in created_entities:
            print('\n🗑️  Deleting game...')
            try:
                deleted = self.game_repo.delete_game(created_entities['Game'].game_id)

                if deleted:
                    print('✅ Deleted game successfully')
                else:
                    print('❌ Failed to delete game (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete game: {e}')

        # Delete LeaderboardEntry
        if 'LeaderboardEntry' in created_entities:
            print('\n🗑️  Deleting leaderboardentry...')
            try:
                deleted = self.leaderboardentry_repo.delete_leaderboard_entry(
                    created_entities['LeaderboardEntry'].game_id,
                    created_entities['LeaderboardEntry'].score,
                )

                if deleted:
                    print('✅ Deleted leaderboardentry successfully')
                else:
                    print('❌ Failed to delete leaderboardentry (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete leaderboardentry: {e}')

        # Delete PlayerAchievement
        if 'PlayerAchievement' in created_entities:
            print('\n🗑️  Deleting playerachievement...')
            try:
                deleted = self.playerachievement_repo.delete_player_achievement(
                    created_entities['PlayerAchievement'].player_id,
                    created_entities['PlayerAchievement'].achievement_id,
                )

                if deleted:
                    print('✅ Deleted playerachievement successfully')
                else:
                    print('❌ Failed to delete playerachievement (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete playerachievement: {e}')

        # Delete TournamentEntry
        if 'TournamentEntry' in created_entities:
            print('\n🗑️  Deleting tournamententry...')
            try:
                deleted = self.tournamententry_repo.delete_tournament_entry(
                    created_entities['TournamentEntry'].tournament_id,
                    created_entities['TournamentEntry'].ranking,
                )

                if deleted:
                    print('✅ Deleted tournamententry successfully')
                else:
                    print('❌ Failed to delete tournamententry (not found or already deleted)')
            except Exception as e:
                print(f'❌ Failed to delete tournamententry: {e}')
        print('\n💡 Requirements:')
        print("   - DynamoDB table 'GameTable' must exist")
        print("   - DynamoDB table 'LeaderboardTable' must exist")
        print("   - DynamoDB table 'AchievementTable' must exist")
        print("   - DynamoDB table 'TournamentTable' must exist")
        print('   - DynamoDB permissions: GetItem, PutItem, UpdateItem, DeleteItem')

    def _test_additional_access_patterns(self, created_entities: dict):
        """Test additional access patterns beyond basic CRUD"""
        print('\n' + '=' * 60)
        print('🔍 Additional Access Pattern Testing')
        print('=' * 60)
        print()

        # Game
        # Access Pattern #1: Get game details by ID
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #1: Get game details by ID')
            print('   Using Main Table')
            result = self.game_repo.get_game(created_entities['Game'].game_id)
            print('   ✅ Get game details by ID completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #1: {e}')

        # Access Pattern #2: List all games
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #2: List all games')
            print('   Using Main Table')
            result = self.game_repo.list_games()
            print('   ✅ List all games completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #2: {e}')

        # Access Pattern #11: Get game by ID (duplicate of CRUD - should be filtered)
        # Index: Main Table
        try:
            print(
                '🔍 Testing Access Pattern #11: Get game by ID (duplicate of CRUD - should be filtered)'
            )
            print('   Using Main Table')
            result = self.game_repo.get_game(created_entities['Game'].game_id)
            print('   ✅ Get game by ID (duplicate of CRUD - should be filtered) completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #11: {e}')

        # Access Pattern #12: Get game with metadata verification
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #12: Get game with metadata verification')
            print('   Using Main Table')
            result = self.game_repo.get_game_with_verification(
                created_entities['Game'].game_id, created_entities['Game'].verification_code
            )
            print('   ✅ Get game with metadata verification completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #12: {e}')

        # LeaderboardEntry
        # Access Pattern #3: Get top scores for a game
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #3: Get top scores for a game')
            print('   Using Main Table')
            result = self.leaderboardentry_repo.get_top_scores(
                created_entities['LeaderboardEntry'].game_id
            )
            print('   ✅ Get top scores for a game completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #3: {e}')

        # Access Pattern #4: Get all scores for a player
        # GSI: PlayerScoresIndex
        try:
            print('🔍 Testing Access Pattern #4: Get all scores for a player')
            print('   Using GSI: PlayerScoresIndex')
            result = self.leaderboardentry_repo.get_player_scores(
                created_entities['LeaderboardEntry'].player_id
            )
            print('   ✅ Get all scores for a player completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #4: {e}')

        # Access Pattern #5: Submit a new score
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #5: Submit a new score')
            print('   Using Main Table')
            test_entity = LeaderboardEntry(
                game_id='game-98765',
                score=156000,
                player_id='player-11111',
                player_name='SpeedDemon',
                achieved_at='2024-01-18T20:15:00Z',
                level_reached=22,
                play_duration_seconds=4200,
            )
            result = self.leaderboardentry_repo.submit_score(test_entity)
            print('   ✅ Submit a new score completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #5: {e}')

        # PlayerAchievement
        # Access Pattern #6: Get all achievements for a player
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #6: Get all achievements for a player')
            print('   Using Main Table')
            result = self.playerachievement_repo.get_player_achievements(
                created_entities['PlayerAchievement'].player_id
            )
            print('   ✅ Get all achievements for a player completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #6: {e}')

        # Access Pattern #7: Get achievements for a game sorted by points
        # GSI: GameAchievementsIndex
        try:
            print('🔍 Testing Access Pattern #7: Get achievements for a game sorted by points')
            print('   Using GSI: GameAchievementsIndex')
            result = self.playerachievement_repo.get_game_achievements(
                created_entities['PlayerAchievement'].game_id
            )
            print('   ✅ Get achievements for a game sorted by points completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #7: {e}')

        # Access Pattern #8: Unlock an achievement for a player
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #8: Unlock an achievement for a player')
            print('   Using Main Table')
            test_entity = PlayerAchievement(
                player_id='player-22222',
                achievement_id='achievement-55555',
                game_id='game-98765',
                achievement_name='Speed Master',
                description='Complete a race in under 2 minutes',
                points=500,
                unlocked_at='2024-01-16T12:30:00Z',
                rarity='rare',
            )
            result = self.playerachievement_repo.unlock_achievement(test_entity)
            print('   ✅ Unlock an achievement for a player completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #8: {e}')

        # TournamentEntry
        # Access Pattern #9: Get tournament rankings
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #9: Get tournament rankings')
            print('   Using Main Table')
            result = self.tournamententry_repo.get_tournament_rankings(
                created_entities['TournamentEntry'].tournament_id
            )
            print('   ✅ Get tournament rankings completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #9: {e}')

        # Access Pattern #10: Update player ranking in tournament
        # Index: Main Table
        try:
            print('🔍 Testing Access Pattern #10: Update player ranking in tournament')
            print('   Using Main Table')
            result = self.tournamententry_repo.update_ranking(
                created_entities['TournamentEntry'].tournament_id,
                created_entities['TournamentEntry'].ranking,
            )
            print('   ✅ Update player ranking in tournament completed')
            print(f'   📊 Result: {result}')
        except Exception as e:
            print(f'❌ Error testing Access Pattern #10: {e}')

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
    print('   - GameTable')
    print('   - LeaderboardTable')
    print('   - AchievementTable')
    print('   - TournamentTable')

    if include_additional_access_patterns:
        print('🔍 Including additional access pattern examples')

    examples = UsageExamples()
    examples.run_examples(include_additional_access_patterns=include_additional_access_patterns)


if __name__ == '__main__':
    main()
