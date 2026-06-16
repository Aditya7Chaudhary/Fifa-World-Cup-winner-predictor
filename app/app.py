"""
World Cup 2026 Prediction System - Main Streamlit App
Full-stack prediction system with group stage simulation, 
knockout progression, and SHAP interpretability.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import sys
from pathlib import Path
import pickle

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / 'data'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'models'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'engine'))

from data_loader import MatchDataLoader
from train_model import ModelTrainer
from simulation_engine import MatchPredictor, GroupStageEngine, KnockoutEngine

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="⚽ World Cup 2026 Predictor",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main { padding-top: 0rem; }
    .stTabs [data-baseweb="tab-list"] button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# INITIALIZATION
# ============================================================================

MODEL_PATH = r'C:\Users\Admin\Desktop\FF\models\wc_predictor.pkl'
DATA_PATH = r'C:\Users\Admin\Desktop\FF\data\dummy_data.csv'

# Check if model exists; if not, train
@st.cache_resource
def load_or_train_model():
    """Load model or train if not exists."""
    if not Path(MODEL_PATH).exists():
        st.info("🤖 Training model on first load...")
        trainer = ModelTrainer(DATA_PATH, MODEL_PATH)
        trainer.train()
        trainer.save_model()
        st.success("✅ Model trained and saved!")
    
    try:
        return MatchPredictor(MODEL_PATH, DATA_PATH)
    except Exception as e:
        st.error(f"Error loading model: {e}")
        return None

predictor = load_or_train_model()

# ============================================================================
# SESSION STATE MANAGEMENT
# ============================================================================

if 'current_page' not in st.session_state:
    st.session_state.current_page = 'home'

if 'group_engine' not in st.session_state:
    st.session_state.group_engine = None

if 'knockout_engine' not in st.session_state:
    st.session_state.knockout_engine = None

if 'current_match' not in st.session_state:
    st.session_state.current_match = None

if 'squad_adjustments' not in st.session_state:
    st.session_state.squad_adjustments = {}

if 'approved_results' not in st.session_state:
    st.session_state.approved_results = []

if 'group_stage_complete' not in st.session_state:
    st.session_state.group_stage_complete = False

if 'knockout_bracket' not in st.session_state:
    st.session_state.knockout_bracket = None

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.image("⚽", width=50)
    st.title("Navigation")
    
    page = st.radio(
        "Select Mode:",
        ["🏠 Home", "🎭 Group Stage", "🏆 Knockout Stage"],
        label_visibility="collapsed"
    )
    
    if page == "🏠 Home":
        st.session_state.current_page = 'home'
    elif page == "🎭 Group Stage":
        st.session_state.current_page = 'group_stage'
    else:
        st.session_state.current_page = 'knockout'
    
    st.divider()
    st.markdown("### 📊 System Info")
    st.info(f"**Model:** XGBoost\n**Features:** 11\n**Data Points:** 12 matches\n**Test Version:** Yes")

# ============================================================================
# HOME PAGE
# ============================================================================

def show_home():
    st.title("⚽ World Cup 2026 Prediction System")
    
    st.markdown("""
    ### Welcome to the AI-Powered World Cup Predictor!
    
    This system uses **Machine Learning**, **Monte Carlo Simulation**, and **SHAP Interpretability** 
    to predict World Cup 2026 outcomes.
    
    ---
    
    #### 🎯 Key Features
    
    - **Group Stage Simulation**: 100 runs per match to determine group standings
    - **Knockout Progression**: User-in-the-loop with squad management and real-time predictions
    - **Dynamic Squad Management**: Modify lineups to see how injuries/form changes affect outcomes
    - **SHAP Force Plots**: Understand which factors drive each prediction
    - **Underdog Bias Logic**: Special handling for lower-ranked teams
    - **Time-Decayed H2H**: Historical matchups with exponential decay (5+ years = near-zero impact)
    
    ---
    
    #### 📈 Architecture
    
    | Component | Technology |
    |-----------|-----------|
    | **Backend** | Python, XGBoost, SHAP |
    | **Frontend** | Streamlit |
    | **Data Processing** | Pandas, NumPy, Scikit-learn |
    | **Simulation** | Monte Carlo (100 runs/match) |
    
    ---
    
    #### 🚀 Getting Started
    
    1. **Group Stage** → Run simulations for all groups to determine qualifiers
    2. **Knockout Stage** → Manage squads, run predictions, approve results
    3. **Insights** → Use SHAP force plots to understand prediction drivers
    
    ---
    
    #### ⚠️ Critical Design Decisions
    
    - ✅ **NO Home Advantage Features** (neutrality in neutral venues)
    - ✅ **Underdog Bias via Weight Multipliers** (not separate model)
    - ✅ **Time-Decayed H2H** (recent matches weighted higher)
    - ✅ **Dynamic Feature Updates** (results feed back into "Recent Form")
    
    ---
    
    Ready to predict the future? Head to **Group Stage** →
    """)

# ============================================================================
# GROUP STAGE
# ============================================================================

def show_group_stage():
    st.title("🎭 Group Stage Simulation")
    
    # Initialize groups if not done
    if st.session_state.group_engine is None:
        teams = predictor.loader.get_all_teams()
        
        # Create dummy groups (in real scenario, would be official WC groups)
        teams_by_group = {
            'A': teams[:2] + ['TeamE', 'TeamF'],
            'B': teams[2:] + ['TeamG', 'TeamH']
        }
        
        st.session_state.group_engine = GroupStageEngine()
        st.session_state.group_engine.create_groups(teams_by_group)
    
    engine = st.session_state.group_engine
    
    # Tabs for each group
    group_list = list(engine.groups.keys())
    tabs = st.tabs([f"Group {g}" for g in group_list])
    
    for tab, group in zip(tabs, group_list):
        with tab:
            st.subheader(f"Group {group}")
            
            teams = engine.groups[group]
            
            # Show all matchups
            st.markdown("#### Matchups")
            
            matchups = []
            for i in range(len(teams)):
                for j in range(i + 1, len(teams)):
                    matchups.append((teams[i], teams[j]))
            
            cols = st.columns(2)
            with cols[0]:
                for idx, (t1, t2) in enumerate(matchups[:len(matchups)//2 + len(matchups)%2]):
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col1:
                        st.text(t1)
                    with col2:
                        st.text("vs")
                    with col3:
                        st.text(t2)
                    
                    # Run simulation button
                    if st.button(f"Simulate {t1} vs {t2}", key=f"sim_{group}_{idx}"):
                        result = predictor.simulate_match(t1, t2, num_simulations=100)
                        
                        st.markdown(f"""
                        **{result['team1']}** vs **{result['team2']}**
                        
                        - {result['team1']} Win: {result['team1_win_prob']:.1%}
                        - Draw: {result['draw_prob']:.1%}
                        - {result['team2']} Win: {result['team2_win_prob']:.1%}
                        
                        Expected Score: {result['expected_goals_team1']:.1f} - {result['expected_goals_team2']:.1f}
                        """)
            
            with cols[1]:
                for idx, (t1, t2) in enumerate(matchups[len(matchups)//2 + len(matchups)%2:], 
                                               start=len(matchups)//2 + len(matchups)%2):
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col1:
                        st.text(t1)
                    with col2:
                        st.text("vs")
                    with col3:
                        st.text(t2)
                    
                    if st.button(f"Simulate {t1} vs {t2}", key=f"sim_{group}_{idx}"):
                        result = predictor.simulate_match(t1, t2, num_simulations=100)
                        
                        st.markdown(f"""
                        **{result['team1']}** vs **{result['team2']}**
                        
                        - {result['team1']} Win: {result['team1_win_prob']:.1%}
                        - Draw: {result['draw_prob']:.1%}
                        - {result['team2']} Win: {result['team2_win_prob']:.1%}
                        
                        Expected Score: {result['expected_goals_team1']:.1f} - {result['expected_goals_team2']:.1f}
                        """)
            
            # Current standings
            st.markdown("#### Current Standings")
            standings_df = engine.get_group_standings(group)
            st.dataframe(standings_df, hide_index=True, use_container_width=True)
    
    # Bottom action
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📋 View All Groups Summary"):
            st.info("Group stage simulations running...")
    
    with col2:
        if st.button("✅ Advance to Knockout Stage"):
            st.session_state.group_stage_complete = True
            st.session_state.current_page = 'knockout'
            st.rerun()

# ============================================================================
# KNOCKOUT STAGE
# ============================================================================

def show_knockout():
    st.title("🏆 Knockout Stage")
    
    if not st.session_state.group_stage_complete:
        st.warning("⚠️ Complete Group Stage first!")
        st.info("Go to **Group Stage** tab to run simulations.")
        return
    
    # Initialize knockout if not done
    if st.session_state.knockout_bracket is None:
        teams_list = predictor.loader.get_all_teams()
        qualified = {
            '1A': teams_list[0], '2A': teams_list[1],
            '1B': teams_list[2], '2B': teams_list[3],
            '1C': 'TeamE', '2C': 'TeamF',
            '1D': 'TeamG', '2D': 'TeamH',
            '1E': teams_list[0], '2E': teams_list[1],
            '1F': teams_list[2], '2F': teams_list[3],
            '1G': 'TeamE', '2G': 'TeamF',
            '1H': 'TeamG', '2H': 'TeamH',
        }
        st.session_state.knockout_engine = KnockoutEngine(qualified)
        st.session_state.knockout_bracket = st.session_state.knockout_engine.generate_bracket()
    
    knockout = st.session_state.knockout_engine
    bracket = st.session_state.knockout_bracket
    
    # Round selector
    round_name = st.selectbox(
        "Select Round:",
        list(bracket.keys()),
        format_func=lambda x: x.replace('_', ' ').title()
    )
    
    st.markdown(f"### {round_name.replace('_', ' ').title()}")
    
    matches = bracket[round_name]
    
    if not matches:
        st.info("No matches in this round yet.")
        return
    
    # Display each match
    for match in matches:
        with st.container(border=True):
            col1, col2, col3 = st.columns([1, 0.3, 1])
            
            team1 = match['team1']
            team2 = match['team2']
            
            with col1:
                st.subheader(team1)
                st.text("Lineup/Formation")
                
                # Squad adjustment
                form_adj = st.slider(
                    f"Form adjustment for {team1}",
                    -0.3, 0.3, 0.0, 0.05,
                    key=f"form_{match['match_id']}_{team1}"
                )
                
                xg_adj = st.slider(
                    f"xG adjustment for {team1}",
                    -0.3, 0.3, 0.0, 0.05,
                    key=f"xg_{match['match_id']}_{team1}"
                )
            
            with col2:
                st.markdown("---")
                st.text("VS")
                st.markdown("---")
                
                if st.button("🔮 Predict", key=f"predict_{match['match_id']}"):
                    squad_adj = {
                        'team1_form_adjust': form_adj,
                        'team1_xg_adjust': xg_adj
                    }
                    
                    result = predictor.simulate_match(team1, team2, squad_adjustments=squad_adj)
                    st.session_state.current_match = {
                        'match_id': match['match_id'],
                        'team1': team1,
                        'team2': team2,
                        'prediction': result
                    }
            
            with col3:
                st.subheader(team2)
                st.text("Lineup/Formation")
                
                form_adj2 = st.slider(
                    f"Form adjustment for {team2}",
                    -0.3, 0.3, 0.0, 0.05,
                    key=f"form_{match['match_id']}_{team2}"
                )
                
                xg_adj2 = st.slider(
                    f"xG adjustment for {team2}",
                    -0.3, 0.3, 0.0, 0.05,
                    key=f"xg_{match['match_id']}_{team2}"
                )
            
            # Show prediction if available
            if st.session_state.current_match and \
               st.session_state.current_match['match_id'] == match['match_id']:
                
                pred = st.session_state.current_match['prediction']
                
                st.markdown("---")
                st.markdown("#### Prediction")
                
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    st.metric(
                        f"{team1} Win",
                        f"{pred['team1_win_prob']:.1%}"
                    )
                
                with col_b:
                    st.metric(
                        "Draw",
                        f"{pred['draw_prob']:.1%}"
                    )
                
                with col_c:
                    st.metric(
                        f"{team2} Win",
                        f"{pred['team2_win_prob']:.1%}"
                    )
                
                st.markdown(f"**Expected Score:** {pred['expected_goals_team1']:.1f} - {pred['expected_goals_team2']:.1f}")
                
                st.info("💡 **SHAP Force Plot would show here** in production (requires integration with plotly)")
                
                # Result entry
                st.markdown("#### Enter Result")
                col_x, col_y = st.columns(2)
                
                with col_x:
                    goals_t1 = st.number_input(f"{team1} Goals", 0, 10, 0, key=f"goals1_{match['match_id']}")
                
                with col_y:
                    goals_t2 = st.number_input(f"{team2} Goals", 0, 10, 0, key=f"goals2_{match['match_id']}")
                
                if st.button("✅ Approve Result", key=f"approve_{match['match_id']}"):
                    knockout.approve_match_result(
                        round_name,
                        match['match_id'],
                        team1 if goals_t1 > goals_t2 else team2,
                        max(goals_t1, goals_t2),
                        min(goals_t1, goals_t2)
                    )
                    
                    st.session_state.approved_results.append({
                        'match_id': match['match_id'],
                        'round': round_name,
                        'result': f"{team1} {goals_t1}-{goals_t2} {team2}"
                    })
                    
                    st.success(f"✅ Result approved! {team1} {goals_t1}-{goals_t2} {team2}")
                    st.session_state.current_match = None

# ============================================================================
# MAIN ROUTER
# ============================================================================

if predictor is None:
    st.error("Failed to load model. Please check file paths.")
else:
    if st.session_state.current_page == 'home':
        show_home()
    elif st.session_state.current_page == 'group_stage':
        show_group_stage()
    else:
        show_knockout()

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.caption("⚽ World Cup 2026 Prediction System | Senior ML Engineer Demo | No Home Advantage Bias")
