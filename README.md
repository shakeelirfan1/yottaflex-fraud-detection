# YottaFlex Synthetic Insurance Fraud Detection

A reproducible, explainable prototype for linking synthetic claimants, policies, incidents, providers, invoices, payments and relationship edges to surface suspicious insurance claim networks for investigation.

> **Safety and scope:** All records are synthetic. A risk score is a triage signal, not proof of fraud. Ground-truth labels are stored separately from detection features. This repository is an assessment prototype, not a production insurance decision system.

## Features
- Seeded synthetic data generator (`20261022` by default), parameterized for small test runs and the requested full volume.
- Core CSV entities plus append-only claim/investigation status-event tables: Claimant, Policy, Claim, Incident, Provider, Invoice, Payment, RelationshipEdge, FraudIndicator, Investigation; normalized SQLite-compatible schema in `src/schema.sql`.
- Deterministic IDs, a source manifest, SHA-256 checksums, separate ground-truth labels and validation report.
- Explicit edge cases: invalid policy reference, payment above approved amount, duplicate invoice business number, planted relationship missing from the graph, and benign shared household address.
- Explainable rules-based triage and metrics: precision, recall, F1, false-positive and false-negative rates.
- FastAPI endpoints and a Streamlit dashboard.
- Pytest tests for reproducibility, required cases, detector outputs and exception reporting.

## Requirements
Python 3.11 or 3.12 recommended.

## Setup (Windows PowerShell)
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```
If `py -3.12` is unavailable, use `python -m venv .venv` with an installed supported Python version.

## Run full dataset and pipeline
From the repository root:
```powershell
python scripts/run_pipeline.py
```
Default counts are 5,000 claims, 2,000 claimants, 500 providers and 8,000 relationship edges. Output files are written to `data/generated/`; ground truth is written separately to `data/ground_truth/`.

For a fast smoke test:
```powershell
python scripts/run_pipeline.py --claims 100 --claimants 50 --providers 20 --edges 100 --data-dir data/smoke --truth-dir data/smoke_truth
```

## Tests
```powershell
python -m pytest -q
```

## Start the API
After running the pipeline:
```powershell
uvicorn src.api:app --reload
```
Open `http://127.0.0.1:8000/docs`. Endpoints include `/health`, `/claims`, `/claims/{claim_id}`, `/validation` and `/metrics`.

## Start the dashboard
In another terminal, from the repository root:
```powershell
streamlit run dashboard/app.py
```

## Reproducibility
The generator uses NumPy's `default_rng(seed)`. Run twice using the same seed and same parameters into two different directories, then compare generated-file SHA-256 hashes. Example:
```powershell
python scripts/run_pipeline.py --seed 20261022 --claims 100 --claimants 50 --providers 20 --edges 100 --data-dir data/run1 --truth-dir data/truth1
python scripts/run_pipeline.py --seed 20261022 --claims 100 --claimants 50 --providers 20 --edges 100 --data-dir data/run2 --truth-dir data/truth2
```
Compare the CSV/JSON hashes listed in each `validation_report.json`, excluding `validation_report.json` itself because it contains output-directory checksums. The tests also compare two generated runs.

## Data separation
`data/ground_truth/ground_truth.csv` is evaluation-only and must not be used as a model feature or passed to `detect_suspicious`. `src/detection.py` loads source entities only. The planted labels document expected outcomes and evidence for evaluation.

## Example output (seed 20261022)
A default full run generates 5,000 claims, 2,000 claimants, 500 providers and 8,000 relationship edges. The validation report records expected injected exceptions such as a missing policy reference, a payment above approved amount, and a duplicate invoice business number. Exact exception counts and evaluation metrics are written to `data/generated/validation_report.json` for each run; they are not hard-coded in this README because they depend on generator version and parameters.

Example generated artifact summary:
```text
Synthetic data generation complete
claims: 5000 | claimants: 2000 | providers: 500 | relationship_edges: 8000
Validation report: data/generated/validation_report.json
Detection results: data/generated/detection_results.csv
Ground truth: data/ground_truth/ground_truth.csv
```

## SQL schema and seed export
`src/schema.sql` defines the SQLite-compatible relational schema. After generating the dataset, create SQL insert statements from the CSV snapshot:
```powershell
python scripts/export_sql_seed.py
```
This writes `data/generated/seed_data.sql`. Foreign-key enforcement is temporarily disabled during import because the dataset intentionally contains a labelled missing-policy exception; review the validation report before treating the snapshot as clean production data.

## Known limitations
- Relationships are synthetic and may not reflect real-world network prevalence. Endpoint IDs are validated, but relationship-type semantics are intentionally broad for this assessment prototype.
- The rules are transparent heuristics. Thresholds are not calibrated on real claims; synthetic planted patterns do not establish real-world fraud performance.
- Event tables preserve initial seeded claim states and include explicit synthetic investigation status-change examples. This is not a full event-sourced application: there is no UI/API workflow for recording later transitions yet.
- Evaluation is against planted labels only. Reported metrics describe this generated sample and must not be interpreted as real-world accuracy.

## Source manifest and lawful provenance
No external or personal dataset is used. Every record is synthetically generated by this repository. The manifest records seed, counts and generator entry point. Ground truth is an evaluation artifact committed alongside the generated synthetic snapshot; it is never loaded by the detector.
