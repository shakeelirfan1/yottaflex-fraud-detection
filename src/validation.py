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
        "fraud_indicators":"indicator_id", "investigations":"investigation_id", "investigation_events":"event_id", "claim_status_events":"event_id",
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
    fk("investigation_events","investigation_id","investigations","investigation_id")
    fk("claim_status_events","claim_id","claims","claim_id")
    # Typed entity references must resolve to the corresponding entity table.
    entity_tables = {"claimant":"claimants", "policy":"policies", "claim":"claims", "incident":"incidents", "provider":"providers", "invoice":"invoices", "payment":"payments", "claimant_group":"claimants"}
    entity_key_sets = {name: set(df[primary_keys[name]].astype(str)) for name, df in tables.items() if name in primary_keys and primary_keys[name] in df.columns}
    for table in ("fraud_indicators", "investigations"):
        if table in tables and {"entity_type", "entity_id"}.issubset(tables[table].columns):
            for _, r in tables[table].iterrows():
                target = entity_tables.get(str(r.entity_type))
                # claimant_group is a documented group-level label, not a single claimant FK.
                if str(r.entity_type) in {"claimant_group", "relationship"}:
                    continue
                if target and target in tables:
                    key = primary_keys.get(target)
                    if key and str(r.entity_id) not in entity_key_sets.get(target, set()):
                        issues.append({"severity":"error","code":"invalid_typed_entity_reference","table":table,"row_id":str(r.iloc[0]),"message":f"{r.entity_type}:{r.entity_id} does not resolve to {target}.{key}"})
    # RelationshipEdge endpoints are typed references; verify both sides.
    if "relationship_edges" in tables:
        edge_table = tables["relationship_edges"]
        for _, r in edge_table.iterrows():
            for side in ("source", "target"):
                target = entity_tables.get(str(r[f"{side}_type"]))
                if target and target in tables:
                    key = primary_keys.get(target)
                    if key and str(r[f"{side}_id"]) not in entity_key_sets.get(target, set()):
                        issues.append({"severity":"error","code":"invalid_relationship_endpoint","table":"relationship_edges","row_id":str(r.edge_id),"message":f"{side} {r[side+'_type']}:{r[side+'_id']} does not resolve to {target}.{key}"})
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
    # Allowed-value checks and date ordering. Expected injected exceptions are retained separately.
    enum_specs = {
        "policies": {"policy_type": {"auto", "home", "health"}, "status": {"active", "expired", "cancelled"}},
        "providers": {"provider_type": {"repairer", "medical", "assessor"}},
        "claims": {"status": {"submitted", "under_review", "approved", "rejected", "paid"}},
        "invoices": {"currency": {"USD"}, "status": {"received", "duplicate_suspected"}},
        "payments": {"status": {"processed", "not_issued"}},
        "investigations": {"status": {"open", "needs_review", "closed"}},
        "fraud_indicators": {"severity": {"low", "medium", "high", "info"}},
        "relationship_edges": {"source_type": {"claimant", "policy", "claim", "incident", "provider", "invoice", "payment"}, "target_type": {"claimant", "policy", "claim", "incident", "provider", "invoice", "payment"}, "relationship_type": {"shared_contact", "same_address", "used_provider", "referral", "same_incident", "same_policy", "invoice_link", "payment_link", "reported_with", "serviced_by"}},
    }
    for table, columns in enum_specs.items():
        if table not in tables: continue
        for col, allowed in columns.items():
            if col not in tables[table]: continue
            for _, r in tables[table].iterrows():
                if str(r[col]) not in allowed:
                    issues.append({"severity":"error","code":"invalid_enum_value","table":table,"row_id":str(r.iloc[0]),"message":f"{col}={r[col]!r} not in allowed values {sorted(allowed)}"})
    date_pairs = {
        "policies": [("effective_date", "expiry_date", "policy_date_order")],
        "incidents": [("incident_date", "reported_at", "incident_report_date_order")],
        "relationship_edges": [("effective_from", "effective_to", "relationship_effective_date_order")],
        "claims": [("filed_at", "incident_id", "claim_incident_date_order")],
    }
    for table, pairs in date_pairs.items():
        if table not in tables: continue
        df = tables[table]
        for start, end, code in pairs:
            if table == "claims":
                if "incidents" not in tables: continue
                incident_dates = tables["incidents"].set_index("incident_id").incident_date.to_dict()
                for _, r in df.iterrows():
                    incident_date = incident_dates.get(str(r[end]))
                    if incident_date and str(r[start]) < str(incident_date):
                        issues.append({"severity":"error","code":code,"table":table,"row_id":str(r.iloc[0]),"message":f"filed_at {r[start]} precedes incident date {incident_date}"})
            else:
                for _, r in df.iterrows():
                    if str(r[start]) and str(r[end]) and str(r[end]) != "nan" and str(r[start]) > str(r[end]):
                        issues.append({"severity":"error","code":code,"table":table,"row_id":str(r.iloc[0]),"message":f"{start} occurs after {end}"})
    if "claim_status_events" in tables:
        allowed_claim_statuses = {"submitted", "under_review", "approved", "rejected", "paid"}
        for _, r in tables["claim_status_events"].iterrows():
            if str(r.to_status) not in allowed_claim_statuses or (str(r.from_status) and str(r.from_status) not in allowed_claim_statuses):
                issues.append({"severity":"error","code":"invalid_claim_status_transition","table":"claim_status_events","row_id":str(r.event_id),"message":"Invalid claim status transition value"})
    if "investigation_events" in tables:
        allowed_statuses = {"open", "needs_review", "closed"}
        for _, r in tables["investigation_events"].iterrows():
            if str(r.to_status) not in allowed_statuses:
                issues.append({"severity":"error","code":"invalid_investigation_transition","table":"investigation_events","row_id":str(r.event_id),"message":f"Invalid destination status {r.to_status}"})
            if str(r.from_status) and str(r.from_status) not in allowed_statuses:
                issues.append({"severity":"error","code":"invalid_investigation_transition","table":"investigation_events","row_id":str(r.event_id),"message":f"Invalid source status {r.from_status}"})
            if str(r.from_status) and str(r.from_status) == str(r.to_status):
                issues.append({"severity":"error","code":"invalid_investigation_transition","table":"investigation_events","row_id":str(r.event_id),"message":"Status-change event must change the status"})
        if "investigations" in tables:
            for _, current in tables["investigations"].iterrows():
                history = tables["investigation_events"][tables["investigation_events"].investigation_id.astype(str) == str(current.investigation_id)].sort_values("event_at")
                if history.empty or str(history.iloc[-1].to_status) != str(current.status):
                    issues.append({"severity":"error","code":"investigation_history_mismatch","table":"investigations","row_id":str(current.investigation_id),"message":"Current investigation status does not match latest event"})
    return issues
