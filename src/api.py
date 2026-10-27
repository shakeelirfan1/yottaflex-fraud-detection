from fastapi import FastAPI, HTTPException
from pathlib import Path
import pandas as pd
from .detection import detect_suspicious
from .validation import load_tables, validate_tables

app = FastAPI(title="YottaFlex Synthetic Insurance Fraud API", version="1.0.0", description="Explainable fraud triage over synthetic insurance data.")
DATA_DIR = Path("data/generated")

@app.get("/health")
def health(): return {"status":"ok","data_directory":str(DATA_DIR),"data_available":DATA_DIR.exists()}

@app.get("/claims")
def list_claims(limit: int = 100, decision: str | None = None):
    if limit < 1 or limit > 1000: raise HTTPException(400, "limit must be between 1 and 1000")
    p = DATA_DIR / "detection_results.csv"
    if not p.exists(): raise HTTPException(404, "Run python scripts/run_pipeline.py first")
    df = pd.read_csv(p, keep_default_na=False)
    if decision: df = df[df.decision == decision]
    return {"count":int(len(df.head(limit))),"results":df.head(limit).to_dict(orient="records")}

@app.get("/claims/{claim_id}")
def get_claim(claim_id: str):
    p = DATA_DIR / "detection_results.csv"
    if not p.exists(): raise HTTPException(404, "Run the pipeline first")
    df = pd.read_csv(p, keep_default_na=False)
    hit = df[df.claim_id == claim_id]
    if hit.empty: raise HTTPException(404, "Claim not found")
    return hit.iloc[0].to_dict()

@app.get("/validation")
def validation():
    if not DATA_DIR.exists(): raise HTTPException(404, "Run the pipeline first")
    issues = validate_tables(load_tables(DATA_DIR))
    return {"issue_count":len(issues),"issues":issues[:500]}

@app.get("/metrics")
def metrics():
    p = DATA_DIR / "validation_report.json"
    if not p.exists(): raise HTTPException(404, "Run the pipeline first")
    import json
    report = json.loads(p.read_text(encoding="utf-8"))
    return report.get("metrics", {})
