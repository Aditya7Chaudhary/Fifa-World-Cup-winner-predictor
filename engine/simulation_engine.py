"""
Simulation Engine
Handles Monte Carlo group stage simulations and knockout bracket progression.
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple

# Add paths
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.data_loader import MatchDataLoader
from models.train_model import ModelTrainer


class MatchPredictor:
    """Predicts match outcome using trained model."""
    
    def __init__(self, model_path: str, data_path: str):
        """
        Initialize predictor.
        
        Args:
            model_path: Path to saved model.
            data_path: Path to match data CSV (for loader).
        """
        self.model, self.scaler, self.feature_names = ModelTrainer.load_model(model_path)
        self.loader = MatchDataLoader(data_path)
        self.loader.load_data()
    
    def predict_win_probability(self, team1: str, team2: str, 
                                reference_date: datetime = None,
                                squad_adjustments: dict = None) -> Tuple[float, dict]:
        """
        Predict win probability for team1.
        
        Args:
            team1: First team.
            team2: Second team.
            reference_date: Reference date for features.
            squad_adjustments: Dict with keys 'team1_form_adjust', 'team1_xg_adjust', etc.
                              to simulate squad changes.
            
        Returns:
            (win_prob_team1, raw_prediction_dict)
        """
        if reference_date is None:
            reference_date = datetime.now()
        
        features = self.loader.engineer_features(team1, team2, reference_date)
        
        # Apply squad adjustments (e.g., remove key player)
        if squad_adjustments:
            if 'team1_form_adjust' in squad_adjustments:
                features['win_pct_team1'] *= (1 + squad_adjustments['team1_form_adjust'])
            if 'team1_xg_adjust' in squad_adjustments:
                features['avg_xg_team1'] *= (1 + squad_adjustments['team1_xg_adjust'])
            if 'team2_form_adjust' in squad_adjustments:
                features['win_pct_team2'] *= (1 + squad_adjustments['team2_form_adjust'])
            if 'team2_xg_adjust' in squad_adjustments:
                features['avg_xg_team2'] *= (1 + squad_adjustments['team2_xg_adjust'])
        
        # Apply underdog bias: boost probability for underdogs
        rank1 = self.loader.get_team_fifa_rank(team1)
        rank2 = self.loader.get_team_fifa_rank(team2)
        
        if rank1 > 50:  # team1 is underdog
            underdog_multiplier = 1.1 + (rank1 - 50) * 0.002  # Increase ~0.2% per rank beyond 50
            features['win_pct_team1'] *= underdog_multiplier
            features['h2h_win_pct_team1'] *= 1.05
        
        if rank2 > 50:  # team2 is underdog
            underdog_multiplier = 1.1 + (rank2 - 50) * 0.002
            features['win_pct_team2'] *= underdog_multiplier
            features['h2h_win_pct_team2'] *= 1.05
        
        # Create feature vector in correct order
        X = np.array([features[name] for name in self.feature_names]).reshape(1, -1)
        X_scaled = self.scaler.transform(X)
        
        # Get prediction
        win_prob = self.model.predict_proba(X_scaled)[0, 1]  # Probability of class 1 (team1 win)
        
        prediction_dict = {
            'team1': team1,
            'team2': team2,
            'team1_win_prob': float(win_prob),
            'team2_win_prob': float(1 - win_prob),
            'features': features
        }
        
        return win_prob, prediction_dict
    
    def simulate_match(self, team1: str, team2: str, reference_date: datetime = None,
                       squad_adjustments: dict = None, num_simulations: int = 100) -> dict:
        """
        Run Monte Carlo simulation for a match.
        
        Args:
            team1: First team.
            team2: Second team.
            reference_date: Reference date.
            squad_adjustments: Squad modifications.
            num_simulations: Number of simulation runs.
            
        Returns:
            Dict with simulation results (expected score, outcome probabilities).
        """
        win_prob, _ = self.predict_win_probability(team1, team2, reference_date, squad_adjustments)
        
        # Simulate outcomes
        outcomes = np.random.rand(num_simulations) < win_prob
        team1_wins = np.sum(outcomes)
        
        # Simple expected goals-based score model
        stats1 = self.loader.compute_team_stats(team1, reference_date)
        stats2 = self.loader.compute_team_stats(team2, reference_date)
        
        # Expected goals adjusted by xG
        expected_goals_team1 = stats1['avg_xg'] * (1 + win_prob * 0.3)
        expected_goals_team2 = stats2['avg_xg'] * (1 + (1 - win_prob) * 0.3)
        
        return {
            'team1': team1,
            'team2': team2,
            'team1_win_prob': float(win_prob),
            'draw_prob': 0.15,  # Simplified
            'team2_win_prob': float(1 - win_prob - 0.15),
            'expected_goals_team1': float(expected_goals_team1),
            'expected_goals_team2': float(expected_goals_team2),
            'simulations_run': num_simulations
        }


class GroupStageEngine:
    """Handles group stage logic and standings."""
    
    def __init__(self):
        """Initialize group stage."""
        self.groups = {}
        self.standings = {}
    
    def create_groups(self, teams_by_group: Dict[str, List[str]]):
        """
        Set up groups.
        
        Args:
            teams_by_group: Dict like {'A': ['TeamA', 'TeamB', 'TeamC', 'TeamD'], ...}
        """
        self.groups = teams_by_group
        self.standings = {group: {} for group in teams_by_group.keys()}
        
        for group, teams in teams_by_group.items():
            for team in teams:
                self.standings[group][team] = {
                    'played': 0,
                    'wins': 0,
                    'draws': 0,
                    'losses': 0,
                    'goals_for': 0,
                    'goals_against': 0,
                    'points': 0
                }
    
    def update_standings(self, group: str, team1: str, team2: str, 
                        goals_team1: int, goals_team2: int):
        """
        Update standings after a match.
        
        Args:
            group: Group name.
            team1: First team.
            team2: Second team.
            goals_team1: Goals scored by team1.
            goals_team2: Goals scored by team2.
        """
        for team, goals_for, goals_against in [(team1, goals_team1, goals_team2),
                                               (team2, goals_team2, goals_team1)]:
            s = self.standings[group][team]
            s['played'] += 1
            s['goals_for'] += goals_for
            s['goals_against'] += goals_against
            
            if goals_for > goals_against:
                s['wins'] += 1
                s['points'] += 3
            elif goals_for == goals_against:
                s['draws'] += 1
                s['points'] += 1
            else:
                s['losses'] += 1
    
    def get_group_standings(self, group: str) -> pd.DataFrame:
        """
        Get standings DataFrame for a group.
        
        Args:
            group: Group name.
            
        Returns:
            DataFrame with standings sorted by points.
        """
        standings = self.standings[group]
        rows = []
        
        for team, stats in standings.items():
            goal_diff = stats['goals_for'] - stats['goals_against']
            rows.append({
                'Team': team,
                'P': stats['played'],
                'W': stats['wins'],
                'D': stats['draws'],
                'L': stats['losses'],
                'GF': stats['goals_for'],
                'GA': stats['goals_against'],
                'GD': goal_diff,
                'Pts': stats['points']
            })
        
        df = pd.DataFrame(rows)
        df = df.sort_values(by=['Pts', 'GD', 'GF'], ascending=[False, False, False])
        df = df.reset_index(drop=True)
        df['Position'] = range(1, len(df) + 1)
        
        return df


class KnockoutEngine:
    """Handles knockout stage progression."""
    
    def __init__(self, qualified_teams: Dict[str, List[str]]):
        """
        Initialize knockout stage.
        
        Args:
            qualified_teams: Dict like {'1A': 'TeamA', '2B': 'TeamB', ...}
                            where key is seed (1=winner, 2=runner-up, letter=group).
        """
        self.qualified_teams = qualified_teams
        self.bracket = {}
        self.results = {}
    
    def generate_bracket(self) -> dict:
        """
        Generate knockout bracket (Round of 16 onwards).
        
        Returns:
            Dict with match structure.
        """
        # Simple Round of 16: 1A vs 2B, 1C vs 2D, etc.
        # This is a simplified version; real WC has more complex seeding
        
        bracket = {
            'round_of_16': [],
            'quarterfinals': [],
            'semifinals': [],
            'finals': []
        }
        
        # Parse qualified teams into R16 matchups
        groups = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        for i in range(0, len(groups), 2):
            team1_key = f"1{groups[i]}"
            team2_key = f"2{groups[i+1]}"
            
            if team1_key in self.qualified_teams and team2_key in self.qualified_teams:
                bracket['round_of_16'].append({
                    'match_id': f"R16_{i//2 + 1}",
                    'team1': self.qualified_teams[team1_key],
                    'team2': self.qualified_teams[team2_key],
                    'status': 'pending'
                })
        
        self.bracket = bracket
        return bracket
    
    def approve_match_result(self, round_name: str, match_id: str, 
                            winner: str, goals_winner: int, goals_loser: int):
        """
        Record an approved match result.
        
        Args:
            round_name: 'round_of_16', 'quarterfinals', etc.
            match_id: Match identifier.
            winner: Winning team.
            goals_winner: Goals by winner.
            goals_loser: Goals by loser.
        """
        result = {
            'match_id': match_id,
            'winner': winner,
            'goals_winner': goals_winner,
            'goals_loser': goals_loser,
            'round': round_name
        }
        self.results[match_id] = result


if __name__ == "__main__":
    print("[INFO] Simulation engine loaded successfully.")
