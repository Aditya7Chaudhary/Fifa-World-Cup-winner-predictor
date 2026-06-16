# World Cup 2026 Prediction System

A full-stack AI/ML prediction system for World Cup 2026 outcomes using Streamlit, XGBoost, and SHAP.

## Project Structure

```
├── /data/
│   ├── dummy_data.csv                 # Sample match data (4 teams)
│   └── data_loader.py                 # Feature engineering & time-decayed H2H
├── /models/
│   ├── train_model.py                 # XGBoost trainer with underdog bias
│   └── wc_predictor.pkl               # Saved model (auto-generated on first run)
├── /engine/
│   └── simulation_engine.py            # Monte Carlo simulation & knockout logic
├── /app/
│   └── app.py                          # Main Streamlit UI
├── requirements.txt                    # Dependencies
└── README.md                           # This file
```

## Key Features

### 1. Data & Feature Engineering (`/data/data_loader.py`)
- **Features Used:**
  - Average xG (expected goals) per game
  - Win percentage (last 2 years)
  - Goals conceded per game
  - World Cup history rating
  - Time-decayed head-to-head record
  
- **CRITICAL Design:** NO home advantage features
- **Time-Decay H2H:** Exponential decay W = e^(-λt) where matches older than 5 years → ~0 impact
- **Underdog Bias:** Applied via weight multipliers for teams ranked >50 in FIFA rankings

### 2. Model Training (`/models/train_model.py`)
- **Algorithm:** XGBoost classifier
- **Underdog Logic:** Weight multiplier approach (not separate model)
- **Auto-Training:** Model trains on first Streamlit run if not found

### 3. Simulation Engine (`/engine/simulation_engine.py`)
- **Group Stage:** Monte Carlo simulation (100 runs per match)
- **Knockout:** Progressive bracket tracking with user approval workflow
- **Squad Management:** Adjust player form/xG to simulate injuries or lineup changes

### 4. Streamlit UI (`/app/app.py`)
- **Home Page:** System overview and architecture
- **Group Stage:** 100 simulations per match, standings per group
- **Knockout Stage:**
  - Interactive squad adjustments (form, xG sliders)
  - Prediction display (win %, draw %, expected score)
  - Result approval workflow (user-in-the-loop)
  - SHAP force plot placeholder (integrate with plotly)

## Installation & Usage

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the App
```bash
streamlit run app/app.py
```

### 3. Train Model (Optional - auto-runs on first launch)
```bash
python models/train_model.py
```

### 4. Test Data Loader
```bash
python data/data_loader.py
```

## Architecture Highlights

| Aspect | Implementation |
|--------|-----------------|
| **Frontend** | Streamlit with `st.session_state` for persistence |
| **Backend** | Python with modular design |
| **ML Model** | XGBoost with SHAP interpretability |
| **Simulation** | Monte Carlo (100 runs per match) |
| **Persistence** | Session state for tournament bracket progression |
| **Bias Handling** | Weight multipliers for underdog probability boost |

## Critical Design Decisions

✅ **NO Home Advantage** - All features engineered to be neutral  
✅ **Underdog Multipliers** - Not a separate model; weight-based  
✅ **Time-Decayed H2H** - Exponential decay ensures old matches don't dominate  
✅ **User-in-the-Loop** - Results must be approved before advancing  
✅ **Dynamic Form Updates** - Approved results feed back into "Recent Form" features  

## Data Format

Expected CSV columns:
```
match_id, date, home_team, away_team, home_goals, away_goals,
home_xg, away_xg, home_recent_form, away_recent_form,
home_wc_history, away_wc_history, home_rank, away_rank,
home_goals_conceded_per_game, away_goals_conceded_per_game
```

## Future Enhancements

- [ ] SHAP force plot integration (plotly)
- [ ] Real FIFA ranking API integration
- [ ] Season data from official sources
- [ ] Squad database with player ratings
- [ ] Advanced tournament seeding (8 groups, 32 teams)
- [ ] Injury probability model
- [ ] Live odds comparison

## Notes for Developers

1. **Start Small:** Use dummy 4-team data for debugging
2. **Session State is Key:** All persistent data (bracket, results, adjustments) stored in `st.session_state`
3. **Keep It Modular:** Each module is independent; swap components easily
4. **Test Underdog Logic:** Verify that rank >50 teams get ~10% probability boost

---

**Version:** 1.0  
**Status:** Production Stage
**Author:** Aditya Chaudhary
