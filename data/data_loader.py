"""
Data Loader & Feature Engineering Module
Handles CSV loading, time-decayed H2H, and feature standardization.
NO home advantage features.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')


class MatchDataLoader:
    def __init__(self, data_path: str, decay_lambda: float = 0.15):
        """
        Initialize the data loader.
        
        Args:
            data_path: Path to CSV with match data.
            decay_lambda: Decay constant for H2H. Tuned so matches older than 5 years have ~0 impact.
        """
        self.data_path = data_path
        self.decay_lambda = decay_lambda
        self.df = None
        self.team_stats = {}
        self.h2h_cache = {}
        
    def load_data(self) -> pd.DataFrame:
        """Load CSV data."""
        self.df = pd.read_csv(self.data_path)
        self.df['date'] = pd.to_datetime(self.df['date'])
        return self.df
    
    def time_decay_factor(self, days_ago: int) -> float:
        """
        Exponential decay function: W = e^(-λt)
        
        After 5 years (1825 days):
        W = e^(-0.15 * 1825) ≈ 1.3e-119 (essentially 0)
        
        Args:
            days_ago: Number of days in the past.
            
        Returns:
            Weight factor [0, 1].
        """
        return np.exp(-self.decay_lambda * days_ago)
    
    def compute_h2h_time_decayed(self, team1: str, team2: str, reference_date: datetime = None) -> dict:
        """
        Compute time-decayed head-to-head record between two teams.
        
        Args:
            team1: First team.
            team2: Second team.
            reference_date: Date to compute decay from (default: today).
            
        Returns:
            Dict with keys: 'team1_wins', 'team2_wins', 'draws', 'weighted_avg_goals_for_team1', 'weighted_avg_goals_for_team2'
        """
        if reference_date is None:
            reference_date = datetime.now()
        
        # Look in cache first
        cache_key = (team1, team2, reference_date.date())
        if cache_key in self.h2h_cache:
            return self.h2h_cache[cache_key]
        
        # Find all matches between these two teams
        mask = ((self.df['home_team'] == team1) & (self.df['away_team'] == team2)) | \
               ((self.df['home_team'] == team2) & (self.df['away_team'] == team1))
        
        matches = self.df[mask].copy()
        
        if len(matches) == 0:
            return {
                'team1_wins': 0.0, 'team2_wins': 0.0, 'draws': 0.0,
                'weighted_avg_goals_for_team1': 0.0, 'weighted_avg_goals_for_team2': 0.0
            }
        
        # Compute decay weights
        matches['days_ago'] = (reference_date - matches['date']).dt.days
        matches['weight'] = matches['days_ago'].apply(self.time_decay_factor)
        
        total_weight = matches['weight'].sum()
        
        team1_wins = 0.0
        team2_wins = 0.0
        draws = 0.0
        weighted_goals_team1 = 0.0
        weighted_goals_team2 = 0.0
        
        for _, row in matches.iterrows():
            w = row['weight']
            if row['home_team'] == team1:
                team1_goals = row['home_goals']
                team2_goals = row['away_goals']
            else:
                team1_goals = row['away_goals']
                team2_goals = row['home_goals']
            
            if team1_goals > team2_goals:
                team1_wins += w
            elif team2_goals > team1_goals:
                team2_wins += w
            else:
                draws += w
            
            weighted_goals_team1 += team1_goals * w
            weighted_goals_team2 += team2_goals * w
        
        # Normalize by total weight
        if total_weight > 0:
            team1_wins /= total_weight
            team2_wins /= total_weight
            draws /= total_weight
            weighted_goals_team1 /= total_weight
            weighted_goals_team2 /= total_weight
        
        result = {
            'team1_wins': team1_wins,
            'team2_wins': team2_wins,
            'draws': draws,
            'weighted_avg_goals_for_team1': weighted_goals_team1,
            'weighted_avg_goals_for_team2': weighted_goals_team2
        }
        
        self.h2h_cache[cache_key] = result
        return result
    
    def compute_team_stats(self, team: str, reference_date: datetime = None) -> dict:
        """
        Compute aggregate team statistics.
        
        Args:
            team: Team name.
            reference_date: Date for computing recent form (default: today).
            
        Returns:
            Dict with team stats.
        """
        if reference_date is None:
            reference_date = datetime.now()
        
        # Home and away matches
        home_matches = self.df[self.df['home_team'] == team]
        away_matches = self.df[self.df['away_team'] == team]
        
        all_matches = pd.concat([home_matches, away_matches], ignore_index=True)
        
        if len(all_matches) == 0:
            return {
                'avg_xg': 0.0,
                'win_pct': 0.0,
                'avg_goals_conceded': 0.0,
                'wc_history_rating': 5.0  # Default neutral rating
            }
        
        # Average xG (excluding home advantage bias)
        home_xg = home_matches['home_xg'].mean() if len(home_matches) > 0 else 0
        away_xg = away_matches['away_xg'].mean() if len(away_matches) > 0 else 0
        avg_xg = (home_xg + away_xg) / 2 if (home_xg > 0 or away_xg > 0) else 0
        
        # Win percentage
        wins = 0
        for _, row in home_matches.iterrows():
            if row['home_goals'] > row['away_goals']:
                wins += 1
        for _, row in away_matches.iterrows():
            if row['away_goals'] > row['home_goals']:
                wins += 1
        
        total_games = len(all_matches)
        win_pct = wins / total_games if total_games > 0 else 0
        
        # Goals conceded per game
        goals_conceded = 0
        for _, row in home_matches.iterrows():
            goals_conceded += row['away_goals']
        for _, row in away_matches.iterrows():
            goals_conceded += row['home_goals']
        
        avg_goals_conceded = goals_conceded / total_games if total_games > 0 else 0
        
        # WC history rating (from dataset)
        wc_ratings = []
        for _, row in home_matches.iterrows():
            wc_ratings.append(row['home_wc_history'])
        for _, row in away_matches.iterrows():
            wc_ratings.append(row['away_wc_history'])
        
        wc_history_rating = np.mean(wc_ratings) if wc_ratings else 5.0
        
        return {
            'avg_xg': avg_xg,
            'win_pct': win_pct,
            'avg_goals_conceded': avg_goals_conceded,
            'wc_history_rating': wc_history_rating
        }
    
    def engineer_features(self, team1: str, team2: str, reference_date: datetime = None) -> dict:
        """
        Engineer features for a match between two teams.
        
        CRITICAL: NO home advantage features.
        
        Features returned (neutral perspective):
        - avg_xg_{team1,team2}
        - win_pct_{team1,team2}
        - avg_goals_conceded_{team1,team2}
        - wc_history_{team1,team2}
        - h2h_win_pct_{team1,team2}
        - h2h_draw_pct
        
        Args:
            team1: First team.
            team2: Second team.
            reference_date: Reference date for stats (default: today).
            
        Returns:
            Dict with engineered features.
        """
        if reference_date is None:
            reference_date = datetime.now()
        
        # Team stats
        stats1 = self.compute_team_stats(team1, reference_date)
        stats2 = self.compute_team_stats(team2, reference_date)
        
        # Time-decayed H2H
        h2h = self.compute_h2h_time_decayed(team1, team2, reference_date)
        
        features = {
            'avg_xg_team1': stats1['avg_xg'],
            'avg_xg_team2': stats2['avg_xg'],
            'win_pct_team1': stats1['win_pct'],
            'win_pct_team2': stats2['win_pct'],
            'avg_goals_conceded_team1': stats1['avg_goals_conceded'],
            'avg_goals_conceded_team2': stats2['avg_goals_conceded'],
            'wc_history_team1': stats1['wc_history_rating'],
            'wc_history_team2': stats2['wc_history_rating'],
            'h2h_win_pct_team1': h2h['team1_wins'],
            'h2h_win_pct_team2': h2h['team2_wins'],
            'h2h_draw_pct': h2h['draws'],
        }
        
        return features
    
    def get_all_teams(self) -> list:
        """Get unique list of teams from dataset."""
        teams = pd.concat([self.df['home_team'], self.df['away_team']]).unique()
        return sorted(list(teams))
    
    def get_team_fifa_rank(self, team: str) -> int:
        """
        Get FIFA ranking for a team. Used for underdog bias logic.
        
        Args:
            team: Team name.
            
        Returns:
            FIFA ranking (lower is better).
        """
        home_matches = self.df[self.df['home_team'] == team]
        if len(home_matches) > 0:
            return int(home_matches.iloc[0]['home_rank'])
        
        away_matches = self.df[self.df['away_team'] == team]
        if len(away_matches) > 0:
            return int(away_matches.iloc[0]['away_rank'])
        
        return 100  # Default high rank


def standardize_features(features_dict: dict) -> dict:
    """
    Standardize feature dict using z-score normalization.
    
    Args:
        features_dict: Dict of features from engineer_features().
        
    Returns:
        Standardized features dict.
    """
    scaler = StandardScaler()
    
    feature_values = np.array(list(features_dict.values())).reshape(-1, 1)
    standardized_values = scaler.fit_transform(feature_values).flatten()
    
    standardized = {}
    for i, key in enumerate(features_dict.keys()):
        standardized[key] = float(standardized_values[i])
    
    return standardized


if __name__ == "__main__":
    # Test the loader
    loader = MatchDataLoader(r'C:\Users\Admin\Desktop\FF\data\dummy_data.csv')
    loader.load_data()
    
    teams = loader.get_all_teams()
    print(f"Teams: {teams}")
    
    features = loader.engineer_features('TeamA', 'TeamB')
    print(f"\nFeatures (TeamA vs TeamB):\n{features}")
    
    h2h = loader.compute_h2h_time_decayed('TeamA', 'TeamB')
    print(f"\nH2H (TeamA vs TeamB):\n{h2h}")
    
    print(f"\nTeamA FIFA Rank: {loader.get_team_fifa_rank('TeamA')}")
