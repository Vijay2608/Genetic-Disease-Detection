import sqlite3
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import matplotlib.pyplot as plt
import pickle
import os

DATABASE_PATH = 'Upload/Dataset.db'
MODEL_ARTIFACTS_DIR = 'model_artifacts'
PLOT_DIR = 'plots'


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
    with open(os.path.join(MODEL_ARTIFACTS_DIR, 'disease_encoder.pkl'), 'rb') as f:
        label_encoder_disease = pickle.load(f)
    with open(os.path.join(MODEL_ARTIFACTS_DIR, 'gene_encoder.pkl'), 'rb') as f:
        label_encoder_gene = pickle.load(f)

    if 'DiseaseName' not in df.columns or 'GeneAffected' not in df.columns:
        raise ValueError("Both 'DiseaseName' and 'GeneAffected' columns must be provided for prediction.")

    df['DiseaseName'] = label_encoder_disease.transform(df['DiseaseName'])
    df['GeneAffected'] = label_encoder_gene.transform(df['GeneAffected'])
    X = df[['DiseaseName', 'GeneAffected']]
    y = (df['RiskPercentage'] > 0.2).astype(int)  # Default prediction threshold
    return X, y


def predict(X):
    with open(os.path.join(MODEL_ARTIFACTS_DIR, 'genetic_disease_model.pkl'), 'rb') as f:
        model = pickle.load(f)
    y_pred_proba = model.predict_proba(X)[:, 1]  # Probability of positive class
    y_pred = (y_pred_proba > 0.2).astype(int)  # Default threshold
    return y_pred, y_pred_proba


def plot_metrics_graphs(thresholds, accuracies, precisions, recalls, f1_scores, roc_aucs):

    os.makedirs(PLOT_DIR, exist_ok=True)

    def plot_line_graph(x, y, metric_name, save_path):
        plt.figure(figsize=(8, 6))
        plt.plot(x, y, marker='o', label=metric_name)
        plt.xlabel('Classification Threshold')
        plt.ylabel(metric_name)
        plt.title(f'{metric_name} vs Threshold')
        plt.grid(True)
        plt.legend()
        plt.savefig(save_path)
        plt.close()

    plot_line_graph(thresholds, accuracies, 'Accuracy', os.path.join(PLOT_DIR, 'accuracy_line.png'))
    plot_line_graph(thresholds, precisions, 'Precision', os.path.join(PLOT_DIR, 'precision_line.png'))
    plot_line_graph(thresholds, recalls, 'Recall', os.path.join(PLOT_DIR, 'recall_line.png'))
    plot_line_graph(thresholds, f1_scores, 'F1 Score', os.path.join(PLOT_DIR, 'f1_score_line.png'))
    plot_line_graph(thresholds, roc_aucs, 'ROC AUC', os.path.join(PLOT_DIR, 'roc_auc_line.png'))


def main():
    os.makedirs('Upload', exist_ok=True)
    os.makedirs(MODEL_ARTIFACTS_DIR, exist_ok=True)
    df = load_data()
    if df is None or df.empty:
        print("No data to process.")
        return

    try:
        X, y = preprocess_data(df)
        y_pred, y_pred_proba = predict(X)

        thresholds = np.arange(0.1, 1.0, 0.1)
        accuracies = []
        precisions = []
        recalls = []
        f1_scores = []
        roc_aucs = []

        for thresh in thresholds:
            y_pred_model = (y_pred_proba > thresh).astype(int)
            accuracy = accuracy_score(y, y_pred_model)
            precision = precision_score(y, y_pred_model, zero_division=0)
            recall = recall_score(y, y_pred_model)
            f1 = f1_score(y, y_pred_model)
            roc_auc = roc_auc_score(y, y_pred_proba)

            accuracies.append(accuracy)
            precisions.append(precision)
            recalls.append(recall)
            f1_scores.append(f1)
            roc_aucs.append(roc_auc)

        print(f"Accuracy: {accuracies[1] * 100:.2f}%")
        print(f"Precision: {precisions[1]:.4f}")
        print(f"Recall: {recalls[1]:.4f}")
        print(f"F1 Score: {f1_scores[1]:.4f}")
        print(f"ROC AUC: {roc_aucs[1]:.4f}")

        plot_metrics_graphs(thresholds, accuracies, precisions, recalls, f1_scores, roc_aucs)

    except ValueError as e:
        print(f"Error during prediction: {e}")


if __name__ == "__main__":
    main()
