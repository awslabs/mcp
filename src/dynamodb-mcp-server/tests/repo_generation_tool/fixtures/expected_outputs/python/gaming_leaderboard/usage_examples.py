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
        self.game_repo = GameRepository('GameTable')
        # LeaderboardTable table repositories
        self.leaderboardentry_repo = LeaderboardEntryRepository('LeaderboardTable')
        # AchievementTable table repositories
        self.playerachievement_repo = PlayerAchievementRepository('AchievementTable')
        # TournamentTable table repositories
        self.tournamententry_repo = TournamentEntryRepository('TournamentTable')

    def run_examples(self, include_additional_access_patterns: bool = False):
        """Run CRUD examples for all entities"""
        # Dictionary to store created entities for access pattern testing
        created_entities = {}

        print('Running Repository Examples')
        print('=' * 50)
        print('\n=== GameTable Table Operations ===')

        # Game example
        print('\n--- Game ---')

        # 1. CREATE - Create sample game
        sample_game = Game(
            game_id='game_id123',
            title='sample_title',
            genre='sample_genre',
            release_date='sample_release_date',
            publisher='sample_publisher',
            max_players=42,
            is_active=True,
        )

        print('📝 Creating game...')
        print(f'📝 PK: {sample_game.pk()}, SK: {sample_game.sk()}')

        created_game = self.game_repo.create_game(sample_game)
        print(f'✅ Created: {created_game}')

        # Store created entity for access pattern testing
        created_entities['Game'] = created_game
        # 2. UPDATE - Update non-key field (title)
        print('\n🔄 Updating title field...')
        original_value = created_game.title
        created_game.title = 'updated_title'

        updated_game = self.game_repo.update_game(created_game)
        print(f'✅ Updated title: {original_value} → {updated_game.title}')

        # Update stored entity with updated values
        created_entities['Game'] = updated_game

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving game...')
        retrieved_game = self.game_repo.get_game(created_game.game_id)

        if retrieved_game:
            print(f'✅ Retrieved: {retrieved_game}')
        else:
            print('❌ Failed to retrieve game')

        print('🎯 Game CRUD cycle completed successfully!')
        print('\n=== LeaderboardTable Table Operations ===')

        # LeaderboardEntry example
        print('\n--- LeaderboardEntry ---')

        # 1. CREATE - Create sample leaderboardentry
        sample_leaderboardentry = LeaderboardEntry(
            game_id='game_id123',
            score=42,
            player_id='player_id123',
            player_name='sample_player_name',
            achieved_at='sample_achieved_at',
            level_reached=42,
            play_duration_seconds=42,
        )

        print('📝 Creating leaderboardentry...')
        print(f'📝 PK: {sample_leaderboardentry.pk()}, SK: {sample_leaderboardentry.sk()}')

        created_leaderboardentry = self.leaderboardentry_repo.create_leaderboard_entry(
            sample_leaderboardentry
        )
        print(f'✅ Created: {created_leaderboardentry}')

        # Store created entity for access pattern testing
        created_entities['LeaderboardEntry'] = created_leaderboardentry
        # 2. UPDATE - Update non-key field (player_id)
        print('\n🔄 Updating player_id field...')
        original_value = created_leaderboardentry.player_id
        created_leaderboardentry.player_id = 'updated_player_id'

        updated_leaderboardentry = self.leaderboardentry_repo.update_leaderboard_entry(
            created_leaderboardentry
        )
        print(f'✅ Updated player_id: {original_value} → {updated_leaderboardentry.player_id}')

        # Update stored entity with updated values
        created_entities['LeaderboardEntry'] = updated_leaderboardentry

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving leaderboardentry...')
        retrieved_leaderboardentry = self.leaderboardentry_repo.get_leaderboard_entry(
            created_leaderboardentry.game_id, created_leaderboardentry.score
        )

        if retrieved_leaderboardentry:
            print(f'✅ Retrieved: {retrieved_leaderboardentry}')
        else:
            print('❌ Failed to retrieve leaderboardentry')

        print('🎯 LeaderboardEntry CRUD cycle completed successfully!')
        print('\n=== AchievementTable Table Operations ===')

        # PlayerAchievement example
        print('\n--- PlayerAchievement ---')

        # 1. CREATE - Create sample playerachievement
        sample_playerachievement = PlayerAchievement(
            player_id='player_id123',
            achievement_id='achievement_id123',
            game_id='game_id123',
            achievement_name='sample_achievement_name',
            description='sample_description',
            points=42,
            unlocked_at='sample_unlocked_at',
            rarity='sample_rarity',
        )

        print('📝 Creating playerachievement...')
        print(f'📝 PK: {sample_playerachievement.pk()}, SK: {sample_playerachievement.sk()}')

        created_playerachievement = self.playerachievement_repo.create_player_achievement(
            sample_playerachievement
        )
        print(f'✅ Created: {created_playerachievement}')

        # Store created entity for access pattern testing
        created_entities['PlayerAchievement'] = created_playerachievement
        # 2. UPDATE - Update non-key field (game_id)
        print('\n🔄 Updating game_id field...')
        original_value = created_playerachievement.game_id
        created_playerachievement.game_id = 'updated_game_id'

        updated_playerachievement = self.playerachievement_repo.update_player_achievement(
            created_playerachievement
        )
        print(f'✅ Updated game_id: {original_value} → {updated_playerachievement.game_id}')

        # Update stored entity with updated values
        created_entities['PlayerAchievement'] = updated_playerachievement

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving playerachievement...')
        retrieved_playerachievement = self.playerachievement_repo.get_player_achievement(
            created_playerachievement.player_id, created_playerachievement.achievement_id
        )

        if retrieved_playerachievement:
            print(f'✅ Retrieved: {retrieved_playerachievement}')
        else:
            print('❌ Failed to retrieve playerachievement')

        print('🎯 PlayerAchievement CRUD cycle completed successfully!')
        print('\n=== TournamentTable Table Operations ===')

        # TournamentEntry example
        print('\n--- TournamentEntry ---')

        # 1. CREATE - Create sample tournamententry
        sample_tournamententry = TournamentEntry(
            tournament_id='tournament_id123',
            ranking=42,
            player_id='player_id123',
            player_name='sample_player_name',
            total_score=42,
            matches_played=42,
            wins=42,
            prize_amount=Decimal('3.14'),
        )

        print('📝 Creating tournamententry...')
        print(f'📝 PK: {sample_tournamententry.pk()}, SK: {sample_tournamententry.sk()}')

        created_tournamententry = self.tournamententry_repo.create_tournament_entry(
            sample_tournamententry
        )
        print(f'✅ Created: {created_tournamententry}')

        # Store created entity for access pattern testing
        created_entities['TournamentEntry'] = created_tournamententry
        # 2. UPDATE - Update non-key field (player_id)
        print('\n🔄 Updating player_id field...')
        original_value = created_tournamententry.player_id
        created_tournamententry.player_id = 'updated_player_id'

        updated_tournamententry = self.tournamententry_repo.update_tournament_entry(
            created_tournamententry
        )
        print(f'✅ Updated player_id: {original_value} → {updated_tournamententry.player_id}')

        # Update stored entity with updated values
        created_entities['TournamentEntry'] = updated_tournamententry

        # 3. GET - Retrieve and print the entity
        print('\n🔍 Retrieving tournamententry...')
        retrieved_tournamententry = self.tournamententry_repo.get_tournament_entry(
            created_tournamententry.tournament_id, created_tournamententry.ranking
        )

        if retrieved_tournamententry:
            print(f'✅ Retrieved: {retrieved_tournamententry}')
        else:
            print('❌ Failed to retrieve tournamententry')

        print('🎯 TournamentEntry CRUD cycle completed successfully!')

        print('\n' + '=' * 50)
        print('🎉 Basic CRUD examples completed successfully!')

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
            deleted = self.game_repo.delete_game(created_entities['Game'].game_id)

            if deleted:
                print('✅ Deleted game successfully')
            else:
                print('❌ Failed to delete game')

        # Delete LeaderboardEntry
        if 'LeaderboardEntry' in created_entities:
            print('\n🗑️  Deleting leaderboardentry...')
            deleted = self.leaderboardentry_repo.delete_leaderboard_entry(
                created_entities['LeaderboardEntry'].game_id,
                created_entities['LeaderboardEntry'].score,
            )

            if deleted:
                print('✅ Deleted leaderboardentry successfully')
            else:
                print('❌ Failed to delete leaderboardentry')

        # Delete PlayerAchievement
        if 'PlayerAchievement' in created_entities:
            print('\n🗑️  Deleting playerachievement...')
            deleted = self.playerachievement_repo.delete_player_achievement(
                created_entities['PlayerAchievement'].player_id,
                created_entities['PlayerAchievement'].achievement_id,
            )

            if deleted:
                print('✅ Deleted playerachievement successfully')
            else:
                print('❌ Failed to delete playerachievement')

        # Delete TournamentEntry
        if 'TournamentEntry' in created_entities:
            print('\n🗑️  Deleting tournamententry...')
            deleted = self.tournamententry_repo.delete_tournament_entry(
                created_entities['TournamentEntry'].tournament_id,
                created_entities['TournamentEntry'].ranking,
            )

            if deleted:
                print('✅ Deleted tournamententry successfully')
            else:
                print('❌ Failed to delete tournamententry')

        print('\n💡 Requirements:')
        print("   - DynamoDB table 'GameTable' must exist")
        print("   - DynamoDB table 'LeaderboardTable' must exist")
        print("   - DynamoDB table 'AchievementTable' must exist")
        print("   - DynamoDB table 'TournamentTable' must exist")
        print('   - DynamoDB permissions: GetItem, PutItem, UpdateItem, DeleteItem')

    def _test_additional_access_patterns(self, created_entities: dict):
        """Test additional access patterns beyond basic CRUD (commented out by default for manual implementation)"""
        print('\n' + '=' * 60)
        print('🔍 Additional Access Pattern Testing (Commented Out)')
        print('=' * 60)
        print('💡 Uncomment the lines below after implementing the additional access patterns')
        print()

        # Game
        # Access Pattern #1: Get game details by ID
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #1: Get game details by ID")
        #     print("   Using Main Table")
        #     game_id = created_entities["Game"].game_id
        #     self.game_repo.get_game(
        #         game_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #1: {e}")

        # Access Pattern #2: List all games
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #2: List all games")
        #     print("   Using Main Table")
        #     self.game_repo.list_games()
        # except Exception as e:
        #     print(f"Error testing Access Pattern #2: {e}")

        # LeaderboardEntry
        # Access Pattern #3: Get top scores for a game
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #3: Get top scores for a game")
        #     print("   Using Main Table")
        #     game_id = created_entities["LeaderboardEntry"].game_id
        #     self.leaderboardentry_repo.get_top_scores(
        #         game_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #3: {e}")

        # Access Pattern #4: Get all scores for a player
        # GSI: PlayerScoresIndex
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #4: Get all scores for a player")
        #     print("   Using GSI: PlayerScoresIndex")
        #     player_id = created_entities["LeaderboardEntry"].player_id
        #     self.leaderboardentry_repo.get_player_scores(
        #         player_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #4: {e}")

        # Access Pattern #5: Submit a new score
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #5: Submit a new score")
        #     print("   Using Main Table")
        #     entry = created_entities["LeaderboardEntry"]
        #     self.leaderboardentry_repo.submit_score(
        #         entry,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #5: {e}")

        # PlayerAchievement
        # Access Pattern #6: Get all achievements for a player
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #6: Get all achievements for a player")
        #     print("   Using Main Table")
        #     player_id = created_entities["PlayerAchievement"].player_id
        #     self.playerachievement_repo.get_player_achievements(
        #         player_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #6: {e}")

        # Access Pattern #7: Get achievements for a game sorted by points
        # GSI: GameAchievementsIndex
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #7: Get achievements for a game sorted by points")
        #     print("   Using GSI: GameAchievementsIndex")
        #     game_id = created_entities["PlayerAchievement"].game_id
        #     self.playerachievement_repo.get_game_achievements(
        #         game_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #7: {e}")

        # Access Pattern #8: Unlock an achievement for a player
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #8: Unlock an achievement for a player")
        #     print("   Using Main Table")
        #     achievement = created_entities["PlayerAchievement"]
        #     self.playerachievement_repo.unlock_achievement(
        #         achievement,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #8: {e}")

        # TournamentEntry
        # Access Pattern #9: Get tournament rankings
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #9: Get tournament rankings")
        #     print("   Using Main Table")
        #     tournament_id = created_entities["TournamentEntry"].tournament_id
        #     self.tournamententry_repo.get_tournament_rankings(
        #         tournament_id,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #9: {e}")

        # Access Pattern #10: Update player ranking in tournament
        # Index: Main Table
        # Implementation: TODO: Add access pattern call test
        # try:
        #     print("🔍 Testing Access Pattern #10: Update player ranking in tournament")
        #     print("   Using Main Table")
        #     tournament_id = created_entities["TournamentEntry"].tournament_id
        #     ranking = created_entities["TournamentEntry"].ranking
        #     # Determine appropriate update value based on entity fields
        #     update_value = "updated_tournament_id"
        #     self.tournamententry_repo.update_ranking(
        #         tournament_id,
        #         ranking,
        #         update_value,
        #     )
        # except Exception as e:
        #     print(f"Error testing Access Pattern #10: {e}")

        print('\n💡 Access Pattern Implementation Notes:')
        print('   - Main Table queries use partition key and sort key')
        print('   - GSI queries use different key structures and may have range conditions')
        print(
            '   - Range conditions (begins_with, between, >, <, >=, <=) require additional parameters'
        )
        print('   - Implement the access pattern methods in your repository classes')


def main():
    """Main function to run examples"""
    # Parse command line arguments
    include_additional_access_patterns = '--all' in sys.argv

    # Check if we're running against DynamoDB Local
    endpoint_url = os.getenv('AWS_ENDPOINT_URL_DYNAMODB')
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
        print('🔍 Including additional access pattern examples (commented out)')

    examples = UsageExamples()
    examples.run_examples(include_additional_access_patterns=include_additional_access_patterns)


if __name__ == '__main__':
    main()
