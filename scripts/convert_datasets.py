"""Utility script to convert the raw China ARFF and Desharnais Excel files to CSV."""

from pathlib import Path

import pandas as pd
from scipy.io import arff

# Define paths
RAW_DIR = Path("data/raw")
CHINA_ARFF = RAW_DIR / "china.arff"
# Note: We will guess the extension, adjust if your file is .xlsx instead of .xls
DESHARNAIS_EXCEL = RAW_DIR / "02.desharnais.xls"


def convert_china():
    print("Converting China ARFF to CSV...")
    # Load ARFF file
    data, meta = arff.loadarff(CHINA_ARFF)
    df = pd.DataFrame(data)

    # Decode byte strings (ARFF files often store strings as bytes)
    df = df.apply(lambda col: col.map(lambda x: x.decode("utf-8") if isinstance(x, bytes) else x))

    # Save to CSV
    output_path = RAW_DIR / "china.csv"
    df.to_csv(output_path, index=False)
    print(f"Saved China dataset to {output_path} with {len(df)} rows.")


def convert_desharnais():
    print("Converting Desharnais Excel to CSV...")
    try:
        # Try reading as Excel
        df = pd.read_excel(DESHARNAIS_EXCEL)
    except FileNotFoundError:
        print(
            f"Error: Could not find {DESHARNAIS_EXCEL}. Please check the file extension in data/raw/"
        )
        return

    # Save to CSV
    output_path = RAW_DIR / "desharnais.csv"
    df.to_csv(output_path, index=False)
    print(f"Saved Desharnais dataset to {output_path} with {len(df)} rows.")


if __name__ == "__main__":
    convert_china()
    convert_desharnais()
