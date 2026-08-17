import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import joblib

def train_grading_model():
    # 1. Load the dataset
    CSV_PATH = "dataset.csv"
    if not pd.io.common.file_exists(CSV_PATH):
        print(f"❌ Error: {CSV_PATH} not found. Run dataset.py first!")
        return

    df = pd.read_csv(CSV_PATH)

    # 2. Feature Engineering
    # We create a 'length_ratio' because XGBoost works better with ratios than raw numbers
    df['length_ratio'] = df['actual_word_count'] / df['total_word_count']
    
    # Define our Features (X) and our Target (y)
    # Target: We normalize the human score (human_score / max_marks) to get a 0.0 to 1.0 range
    X = df[['logic_score', 'semantic_score', 'length_ratio']]
    y = df['human_score'] / df['max_marks']

    # 3. 📊 DATA SPLIT (Training, Validation, Testing)
    # First, split 70% for Training and 30% for the rest
    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.30, random_state=42)
    
    # Now, split that 30% into half Validation (15%) and half Testing (15%)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.50, random_state=42)

    print(f"📈 Split Summary: Train={len(X_train)}, Val={len(X_val)}, Test={len(X_test)}")

    # 4. Initialize XGBoost Regressor
    # We use early_stopping_rounds to prevent overfitting using the Validation set
    model = xgb.XGBRegressor(
        n_estimators=1000,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="mae",
        early_stopping_rounds=50 
    )

    # 5. 🚀 Training with Validation
    print("🚀 Training starting...")
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False
    )

    # 6. Evaluate on the 15% Test Set (The unseen data)
    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)

    print("\n--- 🏁 TRAINING COMPLETE ---")
    print(f"✅ Test MAE: {mae:.4f} (Average error in percentage)")
    print(f"✅ R² Score: {r2:.4f} (How well model fits human logic)")

    # 7. Save the Model
    model.save_model("grading_model.json")
    print("💾 Model saved as 'grading_model.json'")

if __name__ == "__main__":
    train_grading_model()