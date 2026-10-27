"""Export generated CSV tables as a portable SQLite SQL seed snapshot."""
from __future__ import annotations
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "generated"
OUTPUT = DATA_DIR / "seed_data.sql"
TABLE_MAP = {
    "claimants": "claimant", "policies": "policy", "claims": "claim",
    "incidents": "incident", "providers": "provider", "invoices": "invoice",
    "payments": "payment", "relationship_edges": "relationship_edge",
    "fraud_indicators": "fraud_indicator", "investigations": "investigation",
    "investigation_events": "investigation_event", "claim_status_events": "claim_status_event",
}

def sql_value(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"

def main() -> None:
    if not DATA_DIR.exists() or not (DATA_DIR / "claims.csv").exists():
        raise SystemExit("Generated CSVs not found. Run python scripts/run_pipeline.py first.")
    lines = [
        "-- Generated synthetic seed snapshot; do not treat planted anomalies as clean production data.",
        "PRAGMA foreign_keys = OFF;",
        "BEGIN TRANSACTION;",
    ]
    for filename, table in TABLE_MAP.items():
        path = DATA_DIR / f"{filename}.csv"
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            columns = reader.fieldnames or []
            quoted_columns = ", ".join('"' + c.replace('"', '""') + '"' for c in columns)
            for row in reader:
                values = ", ".join(sql_value(row.get(col, "")) for col in columns)
                lines.append(f'INSERT INTO "{table}" ({quoted_columns}) VALUES ({values});')
    lines.extend(["COMMIT;", "PRAGMA foreign_keys = ON;", ""])
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
