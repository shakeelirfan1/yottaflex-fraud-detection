# Schema and validation design

The CSV snapshot is generated from synthetic-only data. `src/schema.sql` defines the relational schema; `scripts/export_sql_seed.py` exports the generated CSVs as SQLite-compatible insert statements. The intentionally invalid policy reference is retained as a labelled exception, so import must occur with foreign-key enforcement disabled and must be followed by the validation report.

## Entities and relationships
- Claimant 1:N Policy; Claimant 1:N Claim.
- Policy 1:N Claim (one invalid policy reference is intentionally injected and labelled in ground truth).
- Incident 1:N Claim; Provider 1:N Claim and Invoice.
- Claim 1:N Invoice; Claim 1:N Payment; Invoice 1:N Payment in the generated model.
- RelationshipEdge is a typed bridge that supports N:M links between claimant, policy, claim, incident, provider, invoice and payment entities.
- Any supported entity may have 0:N FraudIndicators and 0:N Investigations.
- Investigation 1:N InvestigationEvent; Claim 1:N ClaimStatusEvent. Event rows preserve the initial state and include explicit synthetic status-change examples; later user-driven transitions are not yet exposed through the API.

## Keys and lifecycle
Every entity and event table has an immutable string primary key. Foreign-key-like references are checked in `src/validation.py`, including typed relationship endpoints and indicator/investigation entity references. Dates use ISO `YYYY-MM-DD`; amounts are USD unless a currency field says otherwise. Allowed enum values, date ordering, amount reconciliation, primary-key uniqueness and selected event-state values are validated.

## Exception handling
Known exceptions are not silently repaired. The validator emits machine-readable codes for `missing_policy_reference`, `payment_exceeds_approved` and `duplicate_invoice`; these are expected test cases. `issue_type` labels live only in `data/ground_truth/ground_truth.csv`, never in claim input columns. The duplicate invoice scenario reuses a business `invoice_number` while retaining unique `invoice_id` values.

## Relationship-edge semantics
Edge endpoints are typed and validated against their source entity table. `relationship_type` values are synthetic candidate links such as shared contact, same address, used provider, referral, same incident, same policy, invoice link and payment link. The generator uses these as broad synthetic graph relations, not verified real-world associations.
