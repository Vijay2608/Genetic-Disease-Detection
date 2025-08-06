import sqlite3
import pandas as pd

DATABASE_PATH = 'Upload/database.db'
NEW_DATABASE_PATH = 'Upload/Dataset.db'

def get_table_columns(cursor, table_name):
    """Fetch column names from a SQLite table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [info[1] for info in cursor.fetchall()]

def preprocess_dataset(df, columns):
    """Preprocess the DataFrame based on detected columns."""
    # Drop rows with missing values
    df = df.dropna()

    # Create a copy to avoid SettingWithCopyWarning
    df = df.copy()

    # Apply column-specific preprocessing
    for col in columns:
        if col.lower() in ['mutation', 'geneaffected']:
            # Standardize to uppercase for mutation or gene-related columns
            df.loc[:, col] = df[col].str.upper()
        elif col.lower() in ['disorder', 'diseasename']:
            # Standardize to title case for disease/disorder names
            df.loc[:, col] = df[col].str.title()
        elif col.lower() in ['riskpercentage']:
            # Ensure risk percentage is numeric and within valid range (0-100)
            df.loc[:, col] = pd.to_numeric(df[col], errors='coerce')
            df = df[df[col].between(0, 100, inclusive='both')]

    # Remove duplicates based on mutation/gene or disease column if present
    dedup_cols = [col for col in columns if col.lower() in ['mutation', 'geneaffected', 'disorder', 'diseasename']]
    if dedup_cols:
        df = df.drop_duplicates(subset=dedup_cols[0])

    return df

def preprocess_and_upload_data():
    try:
        # Connect to source database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Get column names dynamically
        columns = get_table_columns(cursor, 'uploaded_data')
        if not columns:
            raise ValueError("No columns found in uploaded_data table")

        # Remove 'id' from columns to avoid duplication
        columns = [col for col in columns if col.lower() != 'id']

        # Construct quoted column names for SQL query
        quoted_columns = [f'"{col}"' for col in columns]
        query = f"SELECT {', '.join(quoted_columns)} FROM uploaded_data"

        # Fetch all data from uploaded_data
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        # Create DataFrame with dynamic columns
        df = pd.DataFrame(rows, columns=columns)
        if df.empty:
            raise ValueError("No data found in uploaded_data table")

        # Preprocess the DataFrame
        df = preprocess_dataset(df, columns)

        # Connect to new database
        conn = sqlite3.connect(NEW_DATABASE_PATH)
        cursor = conn.cursor()

        # Drop existing table to avoid conflicts
        cursor.execute("DROP TABLE IF EXISTS uploaded_data")

        # Create table dynamically based on columns
        col_defs = ', '.join([f'"{col}" {"REAL" if col.lower() == "riskpercentage" else "TEXT"}' for col in columns])
        cursor.execute(f"""
            CREATE TABLE uploaded_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                {col_defs}
            )
        """)

        # Insert preprocessed data
        placeholders = ', '.join(['?' for _ in columns])
        for _, row in df.iterrows():
            cursor.execute(f"""
                INSERT INTO uploaded_data ({', '.join([f'"{col}"' for col in columns])})
                VALUES ({placeholders})
            """, tuple(row[col] for col in columns))

        conn.commit()
        conn.close()

        print("Data successfully preprocessed and uploaded to the new database.")

    except Exception as e:
        print(f"Error during preprocessing or upload: {e}")

if __name__ == "__main__":
    preprocess_and_upload_data()

