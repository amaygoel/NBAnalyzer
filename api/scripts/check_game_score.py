"""Quick script to check current game score from NBA API."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nba_api.stats.endpoints import scoreboardv2

sb = scoreboardv2.ScoreboardV2(game_date='01/26/2026')
games = sb.get_data_frames()[0]
line_scores = sb.get_data_frames()[1]

game = games[games['GAME_ID'] == 22500657]
if not game.empty:
    print(f"Game Status: {game['GAME_STATUS_TEXT'].values[0]}")
    print(f"Status ID: {game['GAME_STATUS_ID'].values[0]}")

    cha_line = line_scores[line_scores['TEAM_ID'] == 1610612766]
    phi_line = line_scores[line_scores['TEAM_ID'] == 1610612755]

    if not cha_line.empty and not phi_line.empty:
        print(f"CHA (Home): {int(cha_line['PTS'].values[0])}")
        print(f"PHI (Away): {int(phi_line['PTS'].values[0])}")
else:
    print("Game not found")
