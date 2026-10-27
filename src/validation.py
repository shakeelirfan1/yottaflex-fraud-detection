"""Data integrity checks and exception reporting."""
from pathlib import Path
import pandas as pd

def load_tables(data_dir: str | Path = "data/generated") -> dict[str, pd.DataFrame]:
    return {p.stem: pd.read_csv(p, keep_default_na=False) for p in Path(data_dir).glob("*.csv")}

def validate_tables(tables: dict[str, pd.DataFrame]) -> list[dict]:
    issues: list[dict] = []
    primary_keys = {
        "claimants":"claimant_id", "policies":"policy_id", "claims":"claim_id", "incidents":"incident_id",
        "providers":"provider_id", "invoices":"invoice_id", "payments":"payment_id", "relationship_edges":"edge_id",
        "fraud_indicators":"indicator_id", "investigations":"investigation_id",
    }
    for table, key in primary_keys.items():
        df = tables.get(table)
        if df is None: issues.append({"severity":"error","code":"missing_table","table":table,"row_id":"","message":f"Missing required table: {table}"}); continue
        if key not in df.columns: issues.append({"severity":"error","code":"missing_primary_key","table":table,"row_id":"","message":f"Missing primary key column {key}"}); continue
        if (df[key].astype(str).str.strip() == "").any(): issues.append({"severity":"error","code":"blank_primary_key","table":table,"row_id":"","message":f"Blank values in {key}"})
        if df[key].duplicated().any():
            for val in df.loc[df[key].duplicated(keep=False), key].unique(): issues.append({"severity":"error","code":"duplicate_primary_key","table":table,"row_id":str(val),"message":f"Duplicate {key}: {val}"})
    def fk(child, col, parent, pcol, allow_blank=False):
        if child not in tables or parent not in tables or col not in tables[child] or pcol not in tables[parent]: return
        valid = set(tables[parent][pcol].astype(str))
        for _, row in tables[child].iterrows():
            value = str(row[col])
            if allow_blank and not value: continue
            if value not in valid: issues.append({"severity":"error","code":"foreign_key_violation","table":child,"row_id":str(row.iloc[0]),"message":f"{col}={value} not found in {parent}.{pcol}"})
    fk("policies","claimant_id","claimants","claimant_id")
    fk("claims","claimant_id","claimants","claimant_id")
    fk("claims","incident_id","incidents","incident_id")
    fk("claims","provider_id","providers","provider_id")
    # Invalid policy is an explicit required exception; classify, do not silently fix.
    if "claims" in tables and "policies" in tables:
        valid = set(tables["policies"].policy_id.astype(str))
        for _, r in tables["claims"].iterrows():
            if str(r.policy_id) not in valid:
                issues.append({"severity":"exception","code":"missing_policy_reference","table":"claims","row_id":str(r.claim_id),"message":f"policy_id={r.policy_id} is not present in policies"})
    fk("invoices","claim_id","claims","claim_id")
    fk("invoices","provider_id","providers","provider_id")
    fk("payments","claim_id","claims","claim_id")
    fk("payments","invoice_id","invoices","invoice_id")
    # Numeric / reconciliation rules.
    if "claims" in tables:
        c = tables["claims"].copy()
        for col in ["claimed_amount","approved_amount"]: c[col] = pd.to_numeric(c[col], errors="coerce")
        for _, r in c.iterrows():
            if pd.isna(r.claimed_amount) or pd.isna(r.approved_amount) or r.claimed_amount < 0 or r.approved_amount < 0:
                issues.append({"severity":"error","code":"invalid_claim_amount","table":"claims","row_id":str(r.claim_id),"message":"Claim and approved amounts must be numeric and nonnegative"})
            if r.approved_amount > r.claimed_amount:
                issues.append({"severity":"error","code":"approved_exceeds_claimed","table":"claims","row_id":str(r.claim_id),"message":"Approved amount exceeds claimed amount"})
    if "payments" in tables and "claims" in tables:
        claims = tables["claims"].set_index("claim_id")
        for _, p in tables["payments"].iterrows():
            if p.claim_id in claims.index:
                try: amount, approved = float(p.payment_amount), float(claims.loc[p.claim_id,"approved_amount"])
                except (ValueError, TypeError): continue
                if amount > approved:
                    issues.append({"severity":"exception","code":"payment_exceeds_approved","table":"payments","row_id":str(p.payment_id),"message":f"Payment {amount:.2f} exceeds approved amount {approved:.2f}"})
    if "invoices" in tables and "invoice_number" in tables["invoices"]:
        inv = tables["invoices"]
        duplicated = inv[inv.invoice_number.duplicated(keep=False)]
        for _, r in duplicated.iterrows(): issues.append({"severity":"exception","code":"duplicate_invoice","table":"invoices","row_id":str(r.invoice_id),"message":f"Invoice number {r.invoice_number} is reused across invoice rows"})
    return issues
