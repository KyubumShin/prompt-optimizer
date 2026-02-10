from __future__ import annotations

import csv
import io
from dataclasses import dataclass

@dataclass
class DatasetInfo:
    columns: list[str]
    rows: list[dict[str, str]]
    filename: str

def parse_csv(content: bytes, filename: str) -> DatasetInfo:
    """Parse CSV content bytes into structured dataset."""
    text = content.decode("utf-8-sig")  # Handle BOM
    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        raise ValueError("CSV file has no headers")

    columns = list(reader.fieldnames)
    rows = []
    for i, row in enumerate(reader):
        rows.append({k: (v or "").strip() for k, v in row.items()})

    if not rows:
        raise ValueError("CSV file has no data rows")

    return DatasetInfo(columns=columns, rows=rows, filename=filename)

def validate_prompt_columns(prompt: str, columns: list[str]) -> list[str]:
    """Check that all {placeholder} variables in the prompt match CSV columns. Returns list of missing columns."""
    import re
    placeholders = re.findall(r'\{(\w+)\}', prompt)
    missing = [p for p in placeholders if p not in columns]
    return missing
