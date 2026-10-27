# Data dictionary

All records are synthetic. Dates use ISO `YYYY-MM-DD`; money is USD; identifiers are immutable strings. Empty string means optional/unknown. IDs and foreign keys are validated by the pipeline. Ground-truth labels are kept in `data/ground_truth/ground_truth.csv` and are not inputs to `src/detection.py`.

| Table | Primary key | Main fields / validation |
|---|---|---|
| Claimant | `claimant_id` (`CHT-000001`) | `full_name`, `email` required; synthetic contact fields; `address_id` can be shared by a benign household. |
| Policy | `policy_id` (`POL-000001`) | `claimant_id` FK; `policy_type` in auto/home/health; effective and expiry dates; nonnegative premium. |
| Claim | `claim_id` (`CLM-2026-000001`) | FKs to claimant, policy, incident, provider; claimed and approved amounts nonnegative; status in submitted/under_review/approved/rejected/paid; `issue_type` records deliberate exceptions. |
| Incident | `incident_id` (`INC-2026-000001`) | Incident date, report date, type, narrative, location; report date should not precede incident date in normal records. |
| Provider | `provider_id` (`PRV-000001`) | Provider type in repairer/medical/assessor; synthetic contact/address. |
| Invoice | `invoice_id` (`INV-PRV-000001-000001`) | Claim/provider FKs, unique row ID, `invoice_number` business identifier, invoice date, amount, currency; repeated `invoice_number` is a deliberate duplicate-invoice exception while primary keys remain unique. |
| Payment | `payment_id` (`PAY-2026-000001`) | Claim/invoice FKs, payment date, amount, status; payment amount exceeding approved amount is a deliberate exception. |
| RelationshipEdge | `edge_id` (`REDGE-000001`) | Typed source and target IDs, relationship type, effective dates, provenance. This starter version creates claimant/provider edges; the planted missing relationship is represented in ground truth, not inserted into edges. |
| FraudIndicator | `indicator_id` (`FIND-000001`) | Entity reference, indicator type, severity, score 0–100, evidence. Generated from documented planted labels. |
| Investigation | `investigation_id` (`INVG-2026-000001`) | Entity reference, open date, lifecycle status, queue owner, resolution. Status changes should be appended as events in a production extension. |

## Cardinality
- Claimant 1:N Policy; Claimant 1:N Claim.
- Policy 1:N Claim; Incident 1:N Claim in this synthetic model.
- Provider 1:N Claim and Provider 1:N Invoice.
- Claim 1:N Invoice and Claim 1:N Payment (the generator uses one baseline invoice/payment per claim, but the schema permits multiples).
- RelationshipEdge connects two typed entities; entities can participate in N:M relationships through the edge table.
- Any entity may have 0:N FraudIndicators and 0:N Investigations.

## Important modeling notes
- The brief's `CLM-2026-...` convention is used for **claims**. Claimants use `CHT-...` to avoid ID collision.
- The required invalid policy reference is preserved as an explicit, labelled exception; validation reports it rather than silently fixing it.
- Address sharing alone is not a fraud indicator.
- This is an MVP schema. Before production, add explicit append-only `InvestigationEvent` and `ClaimStatusEvent` tables and enforce lifecycle transitions transactionally.
