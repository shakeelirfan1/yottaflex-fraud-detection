"""Reproducible synthetic insurance data generator. No real personal data is used."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Dict
import numpy as np
import pandas as pd

DEFAULT_SEED = 20261022

def _id(prefix: str, n: int, year: int | None = None) -> str:
    return f"{prefix}-{year}-{n:06d}" if year else f"{prefix}-{n:06d}"

def generate_dataset(out_dir: str | Path = "data/generated", truth_dir: str | Path = "data/ground_truth", *, seed: int = DEFAULT_SEED, n_claims: int = 5000, n_claimants: int = 2000, n_providers: int = 500, n_edges: int = 8000) -> dict:
    """Generate all source tables and separate labels from a fixed seed.

    Required planted exception cases are explicit issue_type values. Ground truth is
    written separately and must never be passed as a detection feature.
    """
    if min(n_claims, n_claimants, n_providers) < 1 or n_edges < 0:
        raise ValueError("Counts must be positive (edges may be zero).")
    rng = np.random.default_rng(seed)
    out_dir, truth_dir = Path(out_dir), Path(truth_dir)
    out_dir.mkdir(parents=True, exist_ok=True); truth_dir.mkdir(parents=True, exist_ok=True)

    # Master entities first.
    claimants = pd.DataFrame({
        "claimant_id": [_id("CHT", i) for i in range(1, n_claimants+1)],
        "full_name": [f"Synthetic Claimant {i:05d}" for i in range(1, n_claimants+1)],
        "email": [f"claimant{i:05d}@example.test" for i in range(1, n_claimants+1)],
        "phone": [f"555{int(x):07d}" for x in rng.integers(0, 10_000_000, n_claimants)],
        "address_id": [f"ADDR-{int(x):05d}" for x in rng.integers(1, max(20, n_claimants//2), n_claimants)],
        "created_at": pd.to_datetime(rng.integers(pd.Timestamp('2023-01-01').value//10**9, pd.Timestamp('2026-01-01').value//10**9, n_claimants), unit="s").date.astype(str),
    })
    # Deliberately benign shared households; address alone is not a fraud signal.
    if n_claimants >= 8:
        claimants.loc[0:3, "address_id"] = "ADDR-BENIGN-HOUSEHOLD-01"
    policies = pd.DataFrame({
        "policy_id": [_id("POL", i) for i in range(1, max(n_claims//2, n_claimants)+1)],
        "claimant_id": rng.choice(claimants.claimant_id, size=max(n_claims//2, n_claimants)),
        "policy_type": rng.choice(["auto", "home", "health"], size=max(n_claims//2, n_claimants), p=[.45,.25,.30]),
        "effective_date": pd.to_datetime(rng.integers(pd.Timestamp('2022-01-01').value//10**9, pd.Timestamp('2026-01-01').value//10**9, max(n_claims//2, n_claimants)), unit="s").date.astype(str),
        "expiry_date": "2027-12-31", "premium_amount": np.round(rng.uniform(250, 5000, max(n_claims//2, n_claimants)), 2),
        "status": "active",
    })
    providers = pd.DataFrame({
        "provider_id": [_id("PRV", i) for i in range(1, n_providers+1)],
        "provider_name": [f"Synthetic Provider {i:04d}" for i in range(1, n_providers+1)],
        "provider_type": rng.choice(["repairer", "medical", "assessor"], n_providers),
        "phone": [f"555{int(x):07d}" for x in rng.integers(0, 10_000_000, n_providers)],
        "address_id": [f"PADDR-{int(x):04d}" for x in rng.integers(1, max(20,n_providers//3), n_providers)],
        "created_at": "2024-01-01",
    })

    # Incidents and claims reference existing master IDs.
    inc_ids = [_id("INC", i, 2026) for i in range(1, n_claims+1)]
    incident_dates = pd.to_datetime(rng.integers(pd.Timestamp('2025-01-01').value//10**9, pd.Timestamp('2026-10-01').value//10**9, n_claims), unit="s").normalize()
    narratives = np.array(["rear-end collision at intersection", "water leak damaged kitchen", "slipped on wet floor", "vehicle window broken", "routine medical treatment", "storm damaged roof", "vehicle collision at junction"])
    incidents = pd.DataFrame({"incident_id": inc_ids, "incident_date": incident_dates.date.astype(str), "incident_type": rng.choice(["collision","property_damage","injury","theft","medical"], n_claims), "narrative": [f"{base}; synthetic report detail {int(code):06d}" for base, code in zip(rng.choice(narratives, n_claims), rng.integers(0, 1_000_000, n_claims))], "location_id": [f"LOC-{int(x):04d}" for x in rng.integers(1, 1000, n_claims)], "reported_at": (incident_dates + pd.to_timedelta(rng.integers(0, 12, n_claims), unit="D")).date.astype(str)})
    policy_ids = policies.policy_id.to_numpy()
    claims = pd.DataFrame({
        "claim_id": [_id("CLM", i, 2026) for i in range(1, n_claims+1)],
        "claimant_id": rng.choice(claimants.claimant_id, n_claims),
        "policy_id": rng.choice(policy_ids, n_claims),
        "incident_id": inc_ids,
        "provider_id": rng.choice(providers.provider_id, n_claims),
        "filed_at": (incident_dates + pd.to_timedelta(rng.integers(1, 30, n_claims), unit="D")).date.astype(str),
        "claimed_amount": np.round(rng.uniform(150, 15000, n_claims), 2),
        "approved_amount": 0.0,
        "status": rng.choice(["submitted","under_review","approved","rejected","paid"], n_claims, p=[.25,.25,.25,.10,.15]),
        "issue_type": "",
    })
    claims["approved_amount"] = np.where(claims.status.isin(["approved","paid"]), np.round(claims.claimed_amount * rng.uniform(.55, 1.0, n_claims), 2), 0.0)

    # Invoice and payment events derive from claims and approved amounts.
    invoices = pd.DataFrame({
        "invoice_id": [f"INV-{pid}-{i:06d}" for i,pid in enumerate(claims.provider_id, 1)],
        "invoice_number": [f"BILL-{i:08d}" for i in range(1, n_claims+1)],
        "claim_id": claims.claim_id, "provider_id": claims.provider_id,
        "invoice_date": claims.filed_at, "invoice_amount": claims.claimed_amount,
        "currency": "USD", "status": "received",
    })
    payments = pd.DataFrame({
        "payment_id": [_id("PAY", i, 2026) for i in range(1, n_claims+1)],
        "claim_id": claims.claim_id, "invoice_id": invoices.invoice_id,
        "payment_date": claims.filed_at,
        "payment_amount": np.where(claims.approved_amount > 0, np.round(claims.approved_amount * rng.uniform(.7,1.0,n_claims),2), 0.0),
        "status": np.where(claims.approved_amount > 0, "processed", "not_issued"),
    })

    # Relationship edges; normal shared address edges exist too, but are not proof.
    edge_rows = []
    entity_ids = [("claimant", x) for x in claimants.claimant_id] + [("provider", x) for x in providers.provider_id]
    for i in range(n_edges):
        a = entity_ids[int(rng.integers(0, len(entity_ids)))]
        b = entity_ids[int(rng.integers(0, len(entity_ids)))]
        while b == a: b = entity_ids[int(rng.integers(0, len(entity_ids)))]
        edge_rows.append({"edge_id": _id("REDGE", i+1), "source_type": a[0], "source_id": a[1], "target_type": b[0], "target_id": b[1], "relationship_type": rng.choice(["shared_contact","same_address","used_provider","referral"]), "effective_from": "2025-01-01", "effective_to": "", "source": "synthetic_generator"})
    edges = pd.DataFrame(edge_rows, columns=["edge_id","source_type","source_id","target_type","target_id","relationship_type","effective_from","effective_to","source"])

    # Plant deterministic fraud patterns and five required exception paths.
    truth_rows = []
    def label(entity_type, entity_id, issue_type, expected_decision, evidence):
        truth_rows.append({"entity_type": entity_type, "entity_id": entity_id, "issue_type": issue_type, "expected_decision": expected_decision, "evidence": evidence})
    if n_claims >= 10 and n_claimants >= 5 and n_providers >= 3:
        # A compact collusive cluster: same contact shared by multiple claimants and provider.
        network_claim_ids = claims.claim_id.iloc[:5].tolist()
        shared_claimant_ids = claims.claimant_id.iloc[:5].tolist()
        shared_phone = "5559999000"
        for cid in set(shared_claimant_ids):
            claimants.loc[claimants.claimant_id == cid, "phone"] = shared_phone
        repeated_narrative = "repeated staged collision narrative at same junction"
        incidents.loc[:4, "narrative"] = repeated_narrative
        incidents.loc[:4, "location_id"] = "LOC-PLANTED-01"
        claims.loc[:4, "provider_id"] = providers.provider_id.iloc[0]
        invoices.loc[:4, "provider_id"] = providers.provider_id.iloc[0]
        for cid in network_claim_ids: label("claim", cid, "planted_suspicious_network", "investigate", "Shared claimant phone, repeated narrative/location and common provider")
        for pid in set(shared_claimant_ids): label("claimant", pid, "shared_contact_network", "investigate", "Shared synthetic phone in planted network")
        # Payment exceeds approved amount (explicit issue).
        claims.loc[0, "status"] = "approved"; claims.loc[0, "approved_amount"] = round(float(claims.loc[0,"claimed_amount"])*.6,2)
        payments.loc[0, "payment_amount"] = round(float(claims.loc[0,"approved_amount"])+500,2)
        claims.loc[0, "issue_type"] = "payment_exceeds_approved"
        label("payment", payments.loc[0,"payment_id"], "payment_exceeds_approved", "exception", "Payment amount exceeds claim approved amount")
        label("claim", claims.loc[0,"claim_id"], "claim_payment_exceeds_approved", "investigate", "Linked payment exceeds approved amount")
        # Duplicate invoice fingerprint across two claimants/claims.
        if n_claims >= 2:
            invoices.loc[1, "invoice_number"] = invoices.loc[0, "invoice_number"]
            invoices.loc[1, "status"] = "duplicate_suspected"
            claims.loc[1, "issue_type"] = "duplicate_invoice"
            label("invoice", invoices.loc[1,"invoice_id"], "duplicate_invoice_across_claims", "investigate", "Same invoice number appears on separate claims")
            label("claim", claims.loc[1,"claim_id"], "claim_duplicate_invoice", "investigate", "Linked invoice number is duplicated across claims")
        # Invalid policy reference, retained as a labelled exception instead of hidden corruption.
        claims.loc[2, "policy_id"] = "POL-INVALID-999999"
        claims.loc[2, "issue_type"] = "missing_policy_reference"
        label("claim", claims.loc[2,"claim_id"], "claim_missing_policy", "exception", "policy_id does not exist in policy master")
        # Planted suspicious relationship intentionally omitted from edges.
        if len(shared_claimant_ids) >= 2:
            label("relationship", f"{shared_claimant_ids[0]}::{shared_claimant_ids[1]}", "missing_relationship_edge", "investigate", "Known planted pair is absent from RelationshipEdge; infer from other evidence")
        # benign common address should not be labelled as fraud by itself.
        if n_claimants >= 4:
            label("claimant_group", "ADDR-BENIGN-HOUSEHOLD-01", "benign_shared_address", "do_not_flag_on_address_alone", "Shared household address is intentionally benign")

    # Derived fraud indicators and investigation lifecycle records are generated from labels/rules.
    fraud_indicators = pd.DataFrame([
        {"indicator_id": _id("FIND", i+1), "entity_type": r["entity_type"], "entity_id": r["entity_id"], "indicator_type": r["issue_type"], "severity": "high" if r["expected_decision"] in ("investigate","exception") else "info", "score": 90 if r["expected_decision"] in ("investigate","exception") else 0, "created_at": "2026-10-01", "evidence": r["evidence"]}
        for i,r in enumerate(truth_rows)
    ], columns=["indicator_id","entity_type","entity_id","indicator_type","severity","score","created_at","evidence"])
    investigations = pd.DataFrame([
        {"investigation_id": _id("INVG", i+1, 2026), "entity_type": r["entity_type"], "entity_id": r["entity_id"], "opened_at": "2026-10-01", "status": "open" if r["expected_decision"] == "investigate" else "needs_review", "assigned_to": "risk-queue", "resolution": ""}
        for i,r in enumerate(truth_rows) if r["expected_decision"] in ("investigate","exception")
    ], columns=["investigation_id","entity_type","entity_id","opened_at","status","assigned_to","resolution"])

    tables: Dict[str,pd.DataFrame] = {"claimants":claimants,"policies":policies,"claims":claims,"incidents":incidents,"providers":providers,"invoices":invoices,"payments":payments,"relationship_edges":edges,"fraud_indicators":fraud_indicators,"investigations":investigations}
    for name, df in tables.items(): df.to_csv(out_dir / f"{name}.csv", index=False)
    truth = pd.DataFrame(truth_rows, columns=["entity_type","entity_id","issue_type","expected_decision","evidence"])
    truth.to_csv(truth_dir / "ground_truth.csv", index=False)
    manifest = {"seed": seed, "counts": {name: int(len(df)) for name,df in tables.items()}, "ground_truth_rows": int(len(truth)), "generator": "src.generator.generate_dataset", "synthetic_only": True}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest

def checksums(directory: str | Path) -> dict:
    """SHA-256 hashes of generated CSV/JSON files for reproducibility checks."""
    result = {}
    for path in sorted(Path(directory).glob("*")):
        if path.is_file(): result[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result
