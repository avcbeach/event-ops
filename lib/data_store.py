import io
import pandas as pd
from lib.github_store import github_read_text, github_write_text

def read_csv(path: str, columns: list[str]) -> pd.DataFrame:
    txt, _ = github_read_text(path)
    if txt.strip():
        return pd.read_csv(io.StringIO(txt), dtype=str).fillna("")
    return pd.DataFrame(columns=columns)

def write_csv(path: str, df: pd.DataFrame, message: str):
    csv_text = df.to_csv(index=False)
    github_write_text(path, csv_text, message)
