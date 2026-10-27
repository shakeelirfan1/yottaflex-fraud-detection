from pathlib import Path
import json
from .generator import generate_dataset, checksums
from .validation import load_tables, validate_tables
from .detection import detect_suspicious, evaluate_predictions

def run_pipeline(seed=20261022, n_claims=5000, n_claimants=2000, n_providers=500, n_edges=8000, data_dir="data/generated", truth_dir="data/ground_truth"):
    manifest = generate_dataset(data_dir, truth_dir, seed=seed, n_claims=n_claims, n_claimants=n_claimants, n_providers=n_providers, n_edges=n_edges)
    issues = validate_tables(load_tables(data_dir))
    preds = detect_suspicious(data_dir)
    preds.to_csv(Path(data_dir)/"detection_results.csv", index=False)
    metrics = evaluate_predictions(preds, Path(truth_dir)/"ground_truth.csv")
    report = {"manifest":manifest,"validation_issue_count":len(issues),"validation_issues_by_severity":{s:sum(1 for x in issues if x["severity"]==s) for s in ["error","exception"]},"validation_issues":issues,"metrics":metrics,"checksums":checksums(data_dir)}
    Path(data_dir).joinpath("validation_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report
