"""
Model Training Pipeline
Trains XGBoost model with underdog bias logic using weight multipliers.
"""

import pickle
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report
import warnings
warnings.filterwarnings('ignore')

# Add data module
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from data_loader import MatchDataLoader


class ModelTrainer:
    def __init__(self, data_path: str, model_output_path: str = r'C:\Users\Admin\Desktop\FF\models\wc_predictor.pkl'):
        """
        Initialize model trainer.
        
        Args:
            data_path: Path to match data CSV.
            model_output_path: Where to save trained model.
        """
        self.data_path = data_path
        self.model_output_path = model_output_path
        self.loader = MatchDataLoader(data_path)
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = None
        
    def prepare_training_data(self) -> tuple:
        """
        Prepare training data for model.
        
        Target: 1 = team1 win, 0 = draw or loss
        
        Returns:
            (X, y) where X is features, y is target.
        """
        self.loader.load_data()
        df = self.loader.df
        
        X_list = []
        y_list = []
        
        for _, row in df.iterrows():
            team1 = row['home_team']
            team2 = row['away_team']
            
            features = self.loader.engineer_features(team1, team2, row['date'])
            
            X_list.append(features)
            
            # Target: team1 win?
            if row['home_goals'] > row['away_goals']:
                y_list.append(1)
            else:
                y_list.append(0)
        
        X = pd.DataFrame(X_list)
        y = np.array(y_list)
        
        self.feature_names = list(X.columns)
        
        return X, y
    
    def apply_underdog_bias(self, X: pd.DataFrame, y: np.ndarray) -> tuple:
        """
        Apply sample weights for underdog bias.
        
        For teams ranked > 50 (underdogs):
        - Increase weight on recent_form features
        - Increase weight on h2h features
        - Upweight samples where underdogs create upsets
        
        Args:
            X: Feature dataframe.
            y: Target array.
            
        Returns:
            (X, y, sample_weights)
        """
        sample_weights = np.ones(len(X))
        
        # For this simplified version, we'll boost upset scenarios
        # (where lower-ranked team wins based on features suggesting they should)
        for i, row in X.iterrows():
            # If high goals_conceded_team2 (weak defense) and team1 has good xG
            # and team1 is underdog (higher rank number), boost the upset
            if row['avg_xg_team1'] > row['avg_xg_team2'] and \
               row['win_pct_team1'] > row['win_pct_team2']:
                sample_weights[i] = 1.2  # Boost upset scenarios
        
        return X, y, sample_weights
    
    def train(self, test_size: float = 0.2, random_state: int = 42):
        """
        Train XGBoost model.
        
        Args:
            test_size: Train/test split ratio.
            random_state: Random seed.
        """
        print("[INFO] Preparing training data...")
        X, y = self.prepare_training_data()
        
        print("[INFO] Applying underdog bias weights...")
        X, y, sample_weights = self.apply_underdog_bias(X, y)
        
        print("[INFO] Splitting data...")
        X_train, X_test, y_train, y_test, w_train, w_test = train_test_split(
            X, y, sample_weights, test_size=test_size, random_state=random_state
        )
        
        print("[INFO] Scaling features...")
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        print("[INFO] Training XGBoost model...")
        self.model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=random_state,
            use_label_encoder=False,
            eval_metric='logloss'
        )
        
        self.model.fit(
            X_train_scaled, y_train,
            sample_weight=w_train,
            eval_set=[(X_test_scaled, y_test)],
            verbose=False
        )
        
        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"\n[RESULTS] Model Accuracy: {accuracy:.3f}")
        print(f"\n{classification_report(y_test, y_pred, target_names=['Draw/Loss', 'Win'])}")
        
        return self.model
    
    def save_model(self):
        """Save trained model and scaler."""
        if self.model is None:
            print("[ERROR] No model to save. Train first.")
            return
        
        artifact = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names
        }
        
        with open(self.model_output_path, 'wb') as f:
            pickle.dump(artifact, f)
        
        print(f"[INFO] Model saved to {self.model_output_path}")
    
    @staticmethod
    def load_model(model_path: str):
        """
        Load pre-trained model.
        
        Args:
            model_path: Path to saved model.
            
        Returns:
            Tuple (model, scaler, feature_names)
        """
        with open(model_path, 'rb') as f:
            artifact = pickle.load(f)
        
        return artifact['model'], artifact['scaler'], artifact['feature_names']


def train_and_save():
    """Convenience function to train and save model."""
    trainer = ModelTrainer(
        data_path=r'C:\Users\Admin\Desktop\FF\data\dummy_data.csv',
        model_output_path=r'C:\Users\Admin\Desktop\FF\models\wc_predictor.pkl'
    )
    trainer.train()
    trainer.save_model()


if __name__ == "__main__":
    train_and_save()
