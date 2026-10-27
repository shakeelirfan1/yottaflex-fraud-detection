# YottaFlex Synthetic Insurance Fraud Detection

A reproducible, explainable prototype for linking synthetic claimants, policies, incidents, providers, invoices, payments, and relationship edges to surface suspicious insurance claim networks for investigation.

> **Safety and scope:** All records are synthetic. A risk score is a triage signal, not proof of fraud. Ground-truth labels are stored separately from detection features. This repository is an assessment prototype, not a production insurance decision system.

## Features

- Seeded synthetic data generator (`20261022` by default), parameterized for small test runs and the requested full volume.
- Core CSV entities and claim/investigation status-event tables: Claimant, Policy, Claim, Incident, Provider, Invoice, Payment, RelationshipEdge, FraudIndicator, and Investigation.
- Normalized SQLite-compatible relational schema in `src/schema.sql`.
- Deterministic IDs, source manifest, SHA-256 checksums, separate ground-truth labels, and validation report.
- Explicit edge cases: invalid policy reference, payment above approved amount, duplicate invoice business number, a planted relationship missing from the graph, and a benign shared household address.
- Explainable rules-based triage with precision, recall, F1 score, false-positive rate, and false-negative rate.
- FastAPI endpoints and a Streamlit dashboard.
- Pytest tests for reproducibility, required edge cases, detector outputs, and exception reporting.

## Requirements

- Python 3.11 or 3.12 recommended.
- Git, to clone the repository.
- Dependencies listed in `requirements.txt`.

## Setup (Windows PowerShell)

Clone the repository and enter its directory:

```powershell
git clone https://github.com/shakeelirfan1/yottaflex-fraud-detection.git
cd yottaflex-fraud-detection
```

Create and activate a virtual environment. Python 3.12 is recommended:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If Python 3.12 is unavailable, use another supported Python version installed on your system:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Verify the installation:

```powershell
python --version
python -m pytest -q
```

If PowerShell blocks virtual-environment activation, use a permitted shell or follow your organization's execution-policy guidance rather than changing system-wide security settings unnecessarily.

## Run the full dataset and pipeline

Run from the repository root:

```powershell
python scripts/run_pipeline.py
```

The default configuration generates:

- 5,000 claims
- 2,000 claimants
- 500 providers
- 8,000 relationship edges

Other entities, event records, and ground-truth labels are generated as part of the pipeline. Generated files are written to `data/generated/`; ground truth is written separately to `data/ground_truth/`.

The validation report is written to:

```text
data/generated/validation_report.json
```

Detection results are written to:

```text
data/generated/detection_results.csv
```

### Fast smoke test

To test the pipeline with a smaller dataset:

```powershell
python scripts/run_pipeline.py --claims 100 --claimants 50 --providers 20 --edges 100 --data-dir data/smoke --truth-dir data/smoke_truth
```

## Tests

Run the test suite from the repository root:

```powershell
python -m pytest -q
```

The current verified project run passed six tests. Run the tests again after making changes or checking out a new version.

## Start the API

First, generate the dataset and validation report:

```powershell
python scripts/run_pipeline.py
```

Then start the API:

```powershell
uvicorn src.api:app --reload
```

Open the interactive API documentation in your browser:

http://127.0.0.1:8000/docs

Available endpoints include:

- `/health`
- `/claims`
- `/claims/{claim_id}`
- `/validation`
- `/metrics`

The API is intended for local assessment and demonstration, not production deployment.

## Start the dashboard

Open a second terminal, activate the virtual environment, and change to the repository root. Then run:

```powershell
streamlit run dashboard/app.py
```

Use the local URL printed by Streamlit to open the dashboard.

## Reproducibility

The generator uses NumPy's `default_rng(seed)`. Identical seeds and parameters should produce identical generated artifacts when the relevant environment and code are unchanged.

Run the pipeline twice using the same seed and parameters, writing to separate directories:

```powershell
python scripts/run_pipeline.py --seed 20261022 --claims 100 --claimants 50 --providers 20 --edges 100 --data-dir data/run1 --truth-dir data/truth1

python scripts/run_pipeline.py --seed 20261022 --claims 100 --claimants 50 --providers 20 --edges 100 --data-dir data/run2 --truth-dir data/truth2
```

Compare the SHA-256 hashes of the corresponding generated artifacts in the two runs. The checksum manifest includes hashes for generated artifacts but excludes `validation_report.json` itself because that report contains the checksum manifest. Hashing the report from inside itself would create a circular dependency.

The tests also compare generated outputs across repeated runs. Re-run these checks after modifying the generator or pipeline.

## Data separation

`data/ground_truth/ground_truth.csv` is an evaluation-only artifact. It must not be used as a model feature or passed to `detect_suspicious`.

`src/detection.py` loads source entities for detection. Planted labels document expected outcomes and evidence for evaluation; they are kept separate to reduce the risk of label leakage.

Evaluation results measure agreement with the planted labels in this synthetic dataset. They do not establish real-world fraud detection performance.

## Example output (seed `20261022`)

A default full run generates 5,000 claims, 2,000 claimants, 500 providers, and 8,000 relationship edges.

Example output summary:

```text
Synthetic data generation complete
claims: 5000 | claimants: 2000 | providers: 500 | relationship_edges: 8000
Validation report: data/generated/validation_report.json
Detection results: data/generated/detection_results.csv
Ground truth: data/ground_truth/ground_truth.csv
```

The validation report records injected exceptions such as a missing policy reference, a payment above the approved amount, and a duplicate invoice business number. Exact exception counts and evaluation metrics are written to `data/generated/validation_report.json` for each run; they are not hard-coded as universal results in this README.

## SQL schema and seed export

`src/schema.sql` defines the SQLite-compatible relational schema.

After generating the dataset, create SQL insert statements from the CSV snapshot:

```powershell
python scripts/export_sql_seed.py
```

This writes:

```text
data/generated/seed_data.sql
```

Foreign-key enforcement is temporarily disabled during import because the dataset intentionally contains a labelled missing-policy exception. Review the validation report before treating the snapshot as clean production data.

## Known limitations

- **Synthetic data only:** Relationships and planted fraud patterns may not reflect real-world prevalence, behavior, or complexity.
- **Rule-based detection:** The detector uses transparent heuristics. Thresholds are not calibrated against real insurance claims.
- **Investigation noise:** In the verified run using seed `20261022`, the detector achieved 100% recall and 21.57% precision against the planted claim labels. All planted positive claims in this sample were recovered, but the low precision indicates substantial investigation noise. These results describe a synthetic benchmark and do not establish real-world fraud detection accuracy.
- **Relationship semantics:** Endpoint IDs are validated, but relationship-type semantics are intentionally broad for this assessment prototype.
- **Event history:** Event tables preserve initial seeded claim states and include explicit synthetic investigation status-change examples. This is not a full event-sourced application; there is no UI/API workflow for recording later transitions yet.
- **Evaluation scope:** Metrics are calculated against planted labels only. The reported results describe this generated sample and must not be interpreted as real-world accuracy.
- **Production readiness:** The prototype has not been established as suitable for production insurance decisions, operational fraud investigations, or regulatory use.

## Source manifest and lawful provenance

No external or personal dataset is used. Every record is synthetically generated by this repository.

The source manifest records the seed, counts, and generator entry point. Ground truth is an evaluation artifact stored separately from generated detection features and is not loaded by the detector.
