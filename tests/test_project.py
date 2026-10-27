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
    for filename in ["fraud_indicators.csv", "investigations.csv", "investigation_events.csv"]:
        assert (d1/filename).read_bytes() == (d2/filename).read_bytes()

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


def test_labels_are_not_in_claim_features(tmp_path):
    d,t=tmp_path/"data",tmp_path/"truth"
    generate_dataset(d,t,seed=456,n_claims=60,n_claimants=30,n_providers=10,n_edges=40)
    claims = pd.read_csv(d/"claims.csv")
    truth = pd.read_csv(t/"ground_truth.csv")
    assert "issue_type" not in claims.columns
    assert "issue_type" in truth.columns
    assert set(truth.issue_type).issuperset({"payment_exceeds_approved", "duplicate_invoice_across_claims", "claim_missing_policy"})


def test_investigation_events_and_typed_relationships_validate(tmp_path):
    d,t=tmp_path/"data",tmp_path/"truth"
    generate_dataset(d,t,seed=789,n_claims=60,n_claimants=30,n_providers=10,n_edges=40)
    tables = load_tables(d)
    assert "investigation_events" in tables
    assert len(tables["investigation_events"]) >= len(tables["investigations"])
    assert "status_changed" in set(tables["investigation_events"].event_type)
    assert set(tables["relationship_edges"].source_type).issubset({"claimant","policy","claim","incident","provider","invoice","payment"})
    issues = validate_tables(tables)
    assert not any(x["code"] in {"invalid_typed_entity_reference", "invalid_relationship_endpoint", "invalid_investigation_transition"} for x in issues)
