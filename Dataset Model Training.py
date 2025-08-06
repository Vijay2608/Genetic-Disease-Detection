import sqlite3
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier
import pickle
import os

DATABASE_PATH = 'Upload/Dataset.db'
MODEL_ARTIFACTS_DIR = 'model_artifacts'

def load_data():
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        query = "SELECT DiseaseName, GeneAffected, RiskPercentage FROM uploaded_data"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return None

def preprocess_data(df):
    df = df.dropna()
    label_encoder_disease = LabelEncoder()
    label_encoder_gene = LabelEncoder()
    df['DiseaseName'] = label_encoder_disease.fit_transform(df['DiseaseName'])
    df['GeneAffected'] = label_encoder_gene.fit_transform(df['GeneAffected'])
    with open(os.path.join(MODEL_ARTIFACTS_DIR, 'disease_encoder.pkl'), 'wb') as f:
        pickle.dump(label_encoder_disease, f)
    with open(os.path.join(MODEL_ARTIFACTS_DIR, 'gene_encoder.pkl'), 'wb') as f:
        pickle.dump(label_encoder_gene, f)
    X = df[['DiseaseName', 'GeneAffected']]
    y = (df['RiskPercentage'] > 0.2).astype(int)
    return X, y

def train_model(X, y):
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    scale_pos_weight = (len(y_train) - sum(y_train)) / sum(y_train)
    xgb = XGBClassifier(random_state=42, eval_metric='logloss', scale_pos_weight=scale_pos_weight)
    param_grid = {
        'n_estimators': [100, 200],
        'max_depth': [3, 5],
        'learning_rate': [0.05, 0.1],
        'subsample': [0.8, 1.0]
    }
    grid_search = GridSearchCV(
        estimator=xgb,
        param_grid=param_grid,
        cv=3,
        scoring='balanced_accuracy',
        n_jobs=-1
    )
    grid_search.fit(X_train, y_train)
    return grid_search.best_estimator_, X_test, y_test

def save_model(model):
    os.makedirs(MODEL_ARTIFACTS_DIR, exist_ok=True)
    with open(os.path.join(MODEL_ARTIFACTS_DIR, 'genetic_disease_model.pkl'), 'wb') as f:
        pickle.dump(model, f)
    print(f"Model saved to {os.path.join(MODEL_ARTIFACTS_DIR, 'genetic_disease_model.pkl')}")

def main():
    os.makedirs('Upload', exist_ok=True)
    os.makedirs(MODEL_ARTIFACTS_DIR, exist_ok=True)
    df = load_data()
    if df is None or df.empty:
        print("No data to process.")
        return
    X, y = preprocess_data(df)
    model, _, _ = train_model(X, y)
    save_model(model)

if __name__ == "__main__":
    main()
