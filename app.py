import os
import sqlite3
import pandas as pd
import pickle
import requests
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder="static", template_folder="template")
CORS(app)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "Upload")
MODEL_ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "model_artifacts")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MODEL_ARTIFACTS_DIR, exist_ok=True)
DATABASE_PATH = os.path.join(UPLOAD_FOLDER, "Database.db")
DATASET_PATH = os.path.join(UPLOAD_FOLDER, "Dataset.db")

def initialize_database():
    # Initialize both databases
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS uploaded_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        DiseaseName TEXT,
        GeneAffected TEXT,
        RiskPercentage REAL
    )""")
    conn.commit()
    conn.close()

    conn = sqlite3.connect(DATASET_PATH)
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS uploaded_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        DiseaseName TEXT,
        GeneAffected TEXT,
        RiskPercentage REAL
    )""")
    conn.commit()
    conn.close()

initialize_database()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload-page")
def upload_page():
    return render_template("upload.html")

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)

@app.route("/upload-dataset", methods=["POST"])
def upload_dataset():
    file = request.files.get("file")
    if not file:
        return jsonify({"message": "No file uploaded"}), 400

    filename = secure_filename(file.filename)
    if not filename.endswith(".csv"):
        return jsonify({"message": "Only CSV files are allowed"}), 400

    try:
        df = pd.read_csv(file)
        if df.empty:
            return jsonify({"message": "CSV is empty"}), 400

        expected_columns = {'DiseaseName', 'GeneAffected', 'RiskPercentage'}
        if not all(col in df.columns for col in expected_columns):
            return jsonify({"message": "CSV must contain DiseaseName, GeneAffected, and RiskPercentage columns"}), 400

        # Insert data into both databases
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM uploaded_data")
        for _, row in df.iterrows():
            cursor.execute("""INSERT INTO uploaded_data (DiseaseName, GeneAffected, RiskPercentage) 
                              VALUES (?, ?, ?)""", (row['DiseaseName'], row['GeneAffected'], row['RiskPercentage']))
        conn.commit()
        conn.close()

        conn = sqlite3.connect(DATASET_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM uploaded_data")
        for _, row in df.iterrows():
            cursor.execute("""INSERT INTO uploaded_data (DiseaseName, GeneAffected, RiskPercentage)
                              VALUES (?, ?, ?)""", (row['DiseaseName'], row['GeneAffected'], row['RiskPercentage']))
        conn.commit()
        conn.close()

        return jsonify({"message": "Dataset uploaded successfully"})
    except Exception as e:
        return jsonify({"message": f"Upload failed: {str(e)}"}), 500

@app.route("/check-dataset")
def check_dataset():
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM uploaded_data")
        count = cursor.fetchone()[0]
        conn.close()
        return jsonify({"exists": count > 0})
    except:
        return jsonify({"exists": False})

@app.route("/get-valid-genes")
def get_valid_genes():
    try:
        conn = sqlite3.connect(DATASET_PATH)
        df = pd.read_sql_query("SELECT DISTINCT GeneAffected FROM uploaded_data", conn)
        conn.close()
        return jsonify({"genes": sorted(df['GeneAffected'].tolist())})
    except Exception as e:
        return jsonify({"error": f"Failed to fetch valid genes: {str(e)}"}), 500

def fetch_disease_info_online(disease):
    """ Fetch additional disease information from Wikipedia API (fatality rate, life expectancy, description) """
    try:
        search_query = f"{disease} disease fatality rate, life expectancy, and description"
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{disease.replace(' ', '%20')}"
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            return {
                "fatalityRate": "Data not available",  # Placeholder, update if necessary.
                "lifeExpectancy": "Data not available",  # Placeholder, update if necessary.
                "description": data.get("extract", "Description not available")
            }
    except Exception as e:
        print(f"Error fetching disease info: {str(e)}")
    return {
        "fatalityRate": "Data not available",
        "lifeExpectancy": "Data not available",
        "description": "Description not available"
    }

@app.route("/predict-disease", methods=["POST"])
def predict_disease():
    try:
        data = request.json
        if not data or 'GeneAffected' not in data:
            return jsonify({"error": "GeneAffected is required"}), 400

        try:
            with open(os.path.join(MODEL_ARTIFACTS_DIR, 'disease_encoder.pkl'), 'rb') as f:
                label_encoder_disease = pickle.load(f)
            with open(os.path.join(MODEL_ARTIFACTS_DIR, 'gene_encoder.pkl'), 'rb') as f:
                label_encoder_gene = pickle.load(f)
            with open(os.path.join(MODEL_ARTIFACTS_DIR, 'genetic_disease_model.pkl'), 'rb') as f:
                model = pickle.load(f)
        except FileNotFoundError:
            return jsonify({"error": "Model or encoders not found. Please ensure model training is complete."}), 500

        conn = sqlite3.connect(DATASET_PATH)
        df = pd.read_sql_query("SELECT DISTINCT DiseaseName, RiskPercentage FROM uploaded_data WHERE GeneAffected = ?",
                              conn, params=(data['GeneAffected'],))
        conn.close()

        if df.empty:
            return jsonify({"error": "No diseases found for the specified gene."}), 400

        predictions = []
        try:
            gene_encoded = label_encoder_gene.transform([data['GeneAffected']])[0]
        except ValueError:
            return jsonify({"error": "Unknown GeneAffected value."}), 400

        for _, row in df.iterrows():
            try:
                disease_encoded = label_encoder_disease.transform([row['DiseaseName']])[0]
            except ValueError:
                continue

            input_data = pd.DataFrame({
                'DiseaseName': [disease_encoded],
                'GeneAffected': [gene_encoded]
            })
            prediction_proba = model.predict_proba(input_data)[:, 1][0]
            prediction = (prediction_proba > 0.2).astype(int)
            risk_label = "High Risk" if prediction == 1 else "Low Risk"

            extra_info = fetch_disease_info_online(row['DiseaseName'])

            predictions.append({
                "disease": row['DiseaseName'],
                "risk_probability": float(prediction_proba),
                "risk_label": risk_label,
                "fatalityRate": extra_info['fatalityRate'],
                "lifeExpectancy": extra_info['lifeExpectancy'],
                "description": extra_info['description']
            })

        if not predictions:
            return jsonify({"error": "No valid predictions could be made for the gene."}), 400

        return jsonify({"gene": data['GeneAffected'], "predictions": predictions})

    except Exception as e:
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
