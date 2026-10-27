"""Explainable rules-based detection; ground truth is not an input to this module."""
from pathlib import Path
import pandas as pd
from .validation import load_tables

def detect_suspicious(data_dir: str | Path = "data/generated") -> pd.DataFrame:
    t = load_tables(data_dir)
    claims, claimants, incidents, invoices, payments = (t[k].copy() for k in ["claims","claimants","incidents","invoices","payments"])
    for col in ["claimed_amount","approved_amount"]: claims[col] = pd.to_numeric(claims[col], errors="coerce").fillna(0)
    payments["payment_amount"] = pd.to_numeric(payments.payment_amount, errors="coerce").fillna(0)
    claimants["phone"] = claimants.phone.astype(str)
    merged = claims.merge(claimants[["claimant_id","phone","address_id"]], on="claimant_id", how="left").merge(incidents[["incident_id","narrative","location_id","incident_date"]], on="incident_id", how="left")
    # Repeated narrative/location is stronger than a shared address alone.
    narrative_counts = merged.groupby("narrative").claim_id.transform("count")
    loc_counts = merged.groupby("location_id").claim_id.transform("count")
    phone_counts = merged.groupby("phone").claimant_id.transform("nunique")
    provider_counts = claims.groupby("provider_id").claim_id.transform("count")
    reasons = [[] for _ in range(len(merged))]
    scores = [0] * len(merged)
    def add(mask, points, reason):
        for i, hit in enumerate(mask.fillna(False).tolist()):
            if hit:
                scores[i] += points
                reasons[i].append(reason)
    add(phone_counts >= 3, 25, "claimant phone shared by 3+ claimants")
    add((narrative_counts >= 3) & (loc_counts >= 3), 30, "repeated incident narrative and location")
    add(provider_counts >= max(8, int(len(claims)*0.01)), 15, "provider associated with unusually many claims")
    invoice_dups = invoices.invoice_number.astype(str).duplicated(keep=False)
    duplicate_claim_ids = set(invoices.loc[invoice_dups, "claim_id"].astype(str))
    add(merged.claim_id.astype(str).isin(duplicate_claim_ids), 35, "duplicate invoice number/fingerprint")
    payment_by_claim = payments.groupby("claim_id").payment_amount.sum()
    overpaid = merged.apply(lambda r: payment_by_claim.get(r.claim_id, 0) > r.approved_amount, axis=1)
    add(overpaid, 40, "payment exceeds approved amount")
    valid_policy_ids = set(t["policies"].policy_id.astype(str))
    add(~merged.policy_id.astype(str).isin(valid_policy_ids), 40, "claim references nonexistent policy")
    merged["risk_score"] = [min(100, int(s)) for s in scores]
    merged["evidence"] = ["; ".join(dict.fromkeys(x)) if x else "No configured risk indicators triggered" for x in reasons]
    merged["decision"] = merged.risk_score.map(lambda x: "investigate" if x >= 40 else ("review" if x >= 20 else "no_flag"))
    # Deliberately do not use address-only matching as a fraud rule.
    return merged[["claim_id","claimant_id","policy_id","incident_id","provider_id","claimed_amount","approved_amount","risk_score","decision","evidence"]].sort_values(["risk_score","claim_id"], ascending=[False,True]).reset_index(drop=True)

def evaluate_predictions(predictions: pd.DataFrame, truth_path: str | Path = "data/ground_truth/ground_truth.csv") -> dict:
    """Evaluate claim-level predictions against separately stored planted network labels."""
    truth = pd.read_csv(truth_path, keep_default_na=False)
    actual = set(truth.loc[(truth.entity_type == "claim") & (truth.expected_decision.isin(["investigate", "exception"])), "entity_id"].astype(str))
    predicted = set(predictions.loc[predictions.decision == "investigate", "claim_id"].astype(str))
    tp, fp, fn = len(actual & predicted), len(predicted - actual), len(actual - predicted)
    precision = tp/(tp+fp) if tp+fp else 0.0
    recall = tp/(tp+fn) if tp+fn else 0.0
    f1 = 2*precision*recall/(precision+recall) if precision+recall else 0.0
    tn = max(0, len(predictions)-tp-fp-fn)
    fpr = fp/(fp+tn) if fp+tn else 0.0
    fnr = fn/(fn+tp) if fn+tp else 0.0
    return {"true_positives":tp,"false_positives":fp,"false_negatives":fn,"true_negatives_estimate":tn,"precision":round(precision,4),"recall":round(recall,4),"f1":round(f1,4),"false_positive_rate":round(fpr,4),"false_negative_rate":round(fnr,4),"ground_truth_claims":len(actual)}
