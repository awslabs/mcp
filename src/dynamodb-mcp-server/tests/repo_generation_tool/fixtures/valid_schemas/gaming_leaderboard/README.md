# Gaming Leaderboard Multi-Table Schema Example

This example demonstrates a gaming leaderboard platform using multiple DynamoDB tables with numeric sort keys for score-based ranking and achievement tracking.

## Architecture Overview

The schema is designed around four main tables representing the gaming ecosystem:
- **GameTable**: Manages game metadata and configuration
- **LeaderboardTable**: Stores player scores with numeric sort key for ranking
- **AchievementTable**: Tracks player achievements with point values
- **TournamentTable**: Manages tournament rankings with numeric positioning

## Tables and Entities

### GameTable
- **Game**: Core game metadata including title, genre, publisher, and player limits

### LeaderboardTable
- **LeaderboardEntry**: Player scores with numeric sort key for efficient top-N queries
- **GSI**: PlayerScoresIndex for querying a player's scores across games

### AchievementTable
- **PlayerAchievement**: Achievement records with point values
- **GSI**: GameAchievementsIndex for querying achievements by game sorted by points

### TournamentTable
- **TournamentEntry**: Tournament rankings with numeric ranking sort key

## Key Features Demonstrated

### Numeric Sort Key Patterns
- **Score-based ranking**: `score` (integer) as sort key for natural ordering
- **Ranking positions**: `ranking` (integer) for tournament standings
- **Point values**: `points` (integer) in GSI for achievement sorting

### GSI Patterns
- **PlayerScoresIndex**: Query player's scores across all games
- **GameAchievementsIndex**: Query achievements for a game sorted by point value

### Multi-Table Design
- Separate tables for different access patterns
- Cross-table relationships via player_id and game_id
- Optimized for high-frequency leaderboard queries

## Sample Use Cases

1. **Game Management**: Create and manage game metadata
2. **Score Submission**: Submit player scores to leaderboards
3. **Top Scores**: Query top N scores for a game (uses numeric sort key)
4. **Player History**: Get all scores for a specific player via GSI
5. **Achievement Tracking**: Unlock and query player achievements
6. **Tournament Rankings**: Manage competitive tournament standings

## Numeric Key Design Benefits

This schema demonstrates the use of numeric sort keys which:
- Enable efficient range queries on scores/rankings
- Support natural descending order for leaderboards
- Allow numeric comparisons (greater than, less than, between)
- Optimize for gaming-specific access patterns

## Access Patterns

| Pattern | Table | Key Design | Description |
|---------|-------|------------|-------------|
| Get top scores | LeaderboardTable | PK: game_id, SK: score (int) | Efficient top-N queries |
| Player scores | LeaderboardTable GSI | PK: player_id, SK: score (int) | Player's score history |
| Game achievements | AchievementTable GSI | PK: game_id, SK: points (int) | Achievements by point value |
| Tournament rankings | TournamentTable | PK: tournament_id, SK: ranking (int) | Ordered standings |

This schema showcases how to build a high-performance gaming leaderboard system with proper numeric key design for score-based queries and ranking operations.
