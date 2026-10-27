from pathlib import Path
import pandas as pd
from src.generator import generate_dataset, checksums
from src.validation import load_tables, validate_tables
from src.detection import detect_suspicious, evaluate_predictions


def test_generator_reproducible(tmp_path):
    d1, t1, d2, t2 = [tmp_path/x for x in ["d1","t1","d2","t2"]]
    generate_dataset(d1,t1,seed=123,n_claims=50,n_claimants=25,n_providers=10,n_edges=30)
    c1=checksums(d1); truth1=(t1/"ground_truth.csv").read_bytes()
    generate_dataset(d2,t2,seed=123,n_claims=50,n_claimants=25,n_providers=10,n_edges=30)
    assert c1 == checksums(d2)
    assert truth1 == (t2/"ground_truth.csv").read_bytes()

def test_required_exception_cases(tmp_path):
    d,t=tmp_path/"data",tmp_path/"truth"
    generate_dataset(d,t,seed=123,n_claims=50,n_claimants=25,n_providers=10,n_edges=30)
    truth=pd.read_csv(t/"ground_truth.csv")
    types=set(truth.issue_type)
    assert "payment_exceeds_approved" in types
    assert "duplicate_invoice_across_claims" in types
    assert "claim_missing_policy" in types
    assert "missing_relationship_edge" in types
    assert "benign_shared_address" in types

def test_detection_outputs_explanations(tmp_path):
    d,t=tmp_path/"data",tmp_path/"truth"
    generate_dataset(d,t,seed=123,n_claims=50,n_claimants=25,n_providers=10,n_edges=30)
    result=detect_suspicious(d)
    assert len(result)==50
    assert result.risk_score.between(0,100).all()
    assert set(result.decision).issubset({"investigate","review","no_flag"})
    assert result.evidence.notna().all()
    metrics=evaluate_predictions(result,t/"ground_truth.csv")
    assert 0 <= metrics["precision"] <= 1

def test_foreign_key_exception_is_reported(tmp_path):
    d,t=tmp_path/"data",tmp_path/"truth"
    generate_dataset(d,t,seed=123,n_claims=50,n_claimants=25,n_providers=10,n_edges=30)
    issues=validate_tables(load_tables(d))
    assert any(i["code"]=="missing_policy_reference" for i in issues)
    assert any(i["code"]=="payment_exceeds_approved" for i in issues)
    assert any(i["code"]=="duplicate_invoice" for i in issues)

def test_missing_relationship_is_detected_from_indirect_evidence(tmp_path):
    data_dir, truth_dir = tmp_path / "data", tmp_path / "truth"
    generate_dataset(
        data_dir, truth_dir, seed=123,
        n_claims=50, n_claimants=25, n_providers=10, n_edges=30
    )

    truth = pd.read_csv(truth_dir / "ground_truth.csv", keep_default_na=False)
    missing = truth[truth.issue_type == "missing_relationship_edge"]
    assert not missing.empty

    results = detect_suspicious(data_dir).set_index("claim_id")
    claims = pd.read_csv(data_dir / "claims.csv")
    planted_claim_ids = claims["claim_id"].head(5).tolist()

    # The planted cluster must be flagged using observable evidence,
    # not by reading the hidden ground-truth file.
    for claim_id in planted_claim_ids:
        assert results.loc[claim_id, "decision"] == "investigate"
        evidence = results.loc[claim_id, "evidence"]
        assert (
            "claimant phone shared" in evidence
            or "repeated incident narrative and location" in evidence
        )


def test_shared_address_alone_does_not_trigger_investigation(tmp_path):
    data_dir, truth_dir = tmp_path / "data", tmp_path / "truth"
    generate_dataset(
        data_dir, truth_dir, seed=456,
        n_claims=50, n_claimants=25, n_providers=50, n_edges=30
    )

    # Neutralize other risk indicators to isolate shared-address behavior.
    claimants = pd.read_csv(data_dir / "claimants.csv")
    claims = pd.read_csv(data_dir / "claims.csv")
    incidents = pd.read_csv(data_dir / "incidents.csv")
    invoices = pd.read_csv(data_dir / "invoices.csv")
    payments = pd.read_csv(data_dir / "payments.csv")
    policies = pd.read_csv(data_dir / "policies.csv")
    providers = pd.read_csv(data_dir / "providers.csv")

    claimants["phone"] = [
        f"UNIQUE-{i}" for i in range(len(claimants))
    ]
    claims["provider_id"] = providers["provider_id"].iloc[:len(claims)].to_numpy()
    claims["policy_id"] = claims.index.map(lambda i: policies["policy_id"].iloc[i % len(policies)])
    claims["approved_amount"] = pd.to_numeric(
        claims["approved_amount"], errors="coerce"
    ).fillna(0)

    incidents["narrative"] = [
        f"Unique synthetic narrative {i}" for i in range(len(incidents))
    ]
    incidents["location_id"] = [
        f"UNIQUE-LOCATION-{i}" for i in range(len(incidents))
    ]

    invoices["provider_id"] = claims["provider_id"].to_numpy()
    invoices["invoice_number"] = [
        f"UNIQUE-BILL-{i}" for i in range(len(invoices))
    ]
    payments["payment_amount"] = claims["approved_amount"].to_numpy()

    claimants.to_csv(data_dir / "claimants.csv", index=False)
    claims.to_csv(data_dir / "claims.csv", index=False)
    incidents.to_csv(data_dir / "incidents.csv", index=False)
    invoices.to_csv(data_dir / "invoices.csv", index=False)
    payments.to_csv(data_dir / "payments.csv", index=False)

    results = detect_suspicious(data_dir)
    assert (results["decision"] == "no_flag").all()
    assert (results["risk_score"] == 0).all()
