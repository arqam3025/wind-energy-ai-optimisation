
from pathlib import Path
import pandas as pd

data_folder = Path("data/raw")

csv_files = sorted(data_folder.glob("*.csv"))

if not csv_files:
    print("No CSV dataset found in data/raw.")
    print("Download the dataset before running the inspection.")
else:
    for file in csv_files:
        print("=" * 60)
        print("DATASET:", file.name)

        df = pd.read_csv(file)

        print("Rows:", len(df))
        print("Columns:", df.columns.tolist())

        print("\nFIRST FIVE ROWS:")
        print(df.head().to_string(index=False))

        print("\nMISSING VALUES:")
        print(df.isna().sum().to_string())
