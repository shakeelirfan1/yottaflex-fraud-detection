# Data dictionary

All records are synthetic. Dates use ISO `YYYY-MM-DD`; money is USD; identifiers are immutable strings. Empty string means optional/unknown. IDs and foreign keys are validated by the pipeline. Ground-truth labels are kept in `data/ground_truth/ground_truth.csv` and are not inputs to `src/detection.py`.

| Table | Primary key | Main fields / validation |
|---|---|---|
| Claimant | `claimant_id` (`CHT-000001`) | `full_name`, `email` required; synthetic contact fields; `address_id` can be shared by a benign household. |
| Policy | `policy_id` (`POL-000001`) | `claimant_id` FK; `policy_type` in auto/home/health; effective and expiry dates; nonnegative premium. |
| Claim | `claim_id` (`CLM-2026-000001`) | FKs to claimant, policy, incident, provider; claimed and approved amounts nonnegative; status in submitted/under_review/approved/rejected/paid; anomaly labels are stored only in ground truth, not this table. |
| Incident | `incident_id` (`INC-2026-000001`) | Incident date, report date, type, narrative, location; report date should not precede incident date in normal records. |
| Provider | `provider_id` (`PRV-000001`) | Provider type in repairer/medical/assessor; synthetic contact/address. |
| Invoice | `invoice_id` (`INV-PRV-000001-000001`) | Claim/provider FKs, unique row ID, `invoice_number` business identifier, invoice date, amount, currency; repeated `invoice_number` is a deliberate duplicate-invoice exception while primary keys remain unique. |
| Payment | `payment_id` (`PAY-2026-000001`) | Claim/invoice FKs, payment date, amount, status; payment amount exceeding approved amount is a deliberate exception. |
| RelationshipEdge | `edge_id` (`REDGE-000001`) | Typed source and target IDs, relationship type, effective dates, provenance. This starter version creates claimant/provider edges; the planted missing relationship is represented in ground truth, not inserted into edges. |
| FraudIndicator | `indicator_id` (`FIND-000001`) | Entity reference, indicator type, severity, score 0–100, evidence. Generated from documented planted labels. |
| Investigation | `investigation_id` (`INVG-2026-000001`) | Entity reference, open date, lifecycle status, queue owner, resolution. Status changes should be appended as events in a production extension. |

| InvestigationEvent | `event_id` (`INVEVT-000001`) | `investigation_id` FK; event type, prior/destination status, timestamp, actor and reason. Initial-state and selected status-change events; future transitions should append rows. |
| ClaimStatusEvent | `event_id` (`CLMEVT-000001`) | `claim_id` FK; prior/destination status, timestamp, actor and reason. One initial event per generated claim. |

## Cardinality
- Claimant 1:N Policy; Claimant 1:N Claim.
- Policy 1:N Claim; Incident 1:N Claim in this synthetic model.
- Provider 1:N Claim and Provider 1:N Invoice.
- Claim 1:N Invoice and Claim 1:N Payment (the generator uses one baseline invoice/payment per claim, but the schema permits multiples).
- RelationshipEdge connects two typed entities; entities can participate in N:M relationships through the edge table.
- Any supported entity may have 0:N FraudIndicators and 0:N Investigations. Investigation 1:N InvestigationEvent; Claim 1:N ClaimStatusEvent.

## Important modeling notes
- The brief's `CLM-2026-...` convention is used for **claims**. Claimants use `CHT-...` to avoid ID collision.
- The required invalid policy reference is preserved as an explicit, labelled exception; validation reports it rather than silently fixing it.
- Address sharing alone is not a fraud indicator.
- Event tables currently capture initial seeded states only. A production implementation should append each later transition transactionally and enforce transition-specific rules.

## Field-level conventions

All fields are required unless explicitly marked optional below. All identifiers are strings and immutable; dates use ISO `YYYY-MM-DD`; monetary amounts are decimal USD unless stated. CSV blank values mean unknown/not applicable, not a numeric zero.

| Table | Field | Type / requirement | Validation / allowed values |
|---|---|---|---|
| Claimant | claimant_id | string, required, unique PK | `CHT-` plus six digits |
| Claimant | full_name, email | string, required | synthetic values; email unique |
| Claimant | phone, address_id | string, required | synthetic; shared contact/address permitted as evidence only, not proof |
| Claimant | created_at | date string, required | valid ISO date |
| Policy | policy_id, claimant_id | string, required; PK/FK | claimant must exist except labelled claim-side invalid policy case |
| Policy | policy_type | enum, required | auto, home, health |
| Policy | effective_date, expiry_date | date, required | effective date must not exceed expiry |
| Policy | premium_amount | decimal, required | nonnegative |
| Policy | status | enum, required | active, expired, cancelled |
| Claim | claim_id | string, required, unique PK | `CLM-2026-` plus six digits |
| Claim | claimant_id, policy_id, incident_id, provider_id | string FKs, required | parent IDs must resolve; missing policy is an intentional labelled exception |
| Claim | filed_at | date, required | must not precede incident date in baseline records |
| Claim | claimed_amount, approved_amount | decimal, required | nonnegative; approved should not exceed claimed |
| Claim | status | enum, required | submitted, under_review, approved, rejected, paid |
| Incident | incident_id | string, required, unique PK | `INC-2026-` plus six digits |
| Incident | incident_date, reported_at | date, required | reported_at must not precede incident_date |
| Incident | incident_type, narrative, location_id | string, required | type selected from synthetic incident categories; narrative/location are synthetic |
| Provider | provider_id | string, required, unique PK | `PRV-` plus six digits |
| Provider | provider_name, phone, address_id, created_at | string/date, required | synthetic provider attributes |
| Provider | provider_type | enum, required | repairer, medical, assessor |
| Invoice | invoice_id | string, required, unique PK | `INV-PRV-<provider-id>-<sequence>`; sequence per provider |
| Invoice | invoice_number | string, required | business number may repeat only in labelled duplicate case |
| Invoice | claim_id, provider_id | string FKs, required | claim and provider must exist |
| Invoice | invoice_date | date, required | ISO date |
| Invoice | invoice_amount | decimal, required | nonnegative |
| Invoice | currency, status | string/enum, required | USD; received or duplicate_suspected |
| Payment | payment_id | string, required, unique PK | `PAY-2026-` plus six digits |
| Payment | claim_id, invoice_id | string FKs, required | referenced claim and invoice must exist |
| Payment | payment_date | date, required | ISO date; chronology checked against source event dates where applicable |
| Payment | payment_amount | decimal, required | nonnegative; excess over approved amount is a labelled exception |
| Payment | status | enum, required | processed, not_issued |
| RelationshipEdge | edge_id | string, required, unique PK | `REDGE-` plus six digits |
| RelationshipEdge | source_type, target_type | enum, required | claimant, policy, claim, incident, provider, invoice, payment |
| RelationshipEdge | source_id, target_id | string FK-like references, required | each typed ID must exist; source and target must differ |
| RelationshipEdge | relationship_type | enum, required | shared_contact, same_address, used_provider, referral, same_incident, same_policy, invoice_link, payment_link, reported_with, serviced_by |
| RelationshipEdge | effective_from, effective_to, source | string/date, required | effective_to may be blank for open-ended; source describes synthetic provenance |
| FraudIndicator | indicator_id | string, required, unique PK | `FIND-` plus six digits |
| FraudIndicator | entity_type, entity_id | string, required | typed entity reference; group/relationship labels are documented non-row references |
| FraudIndicator | indicator_type, severity, evidence | string, required | severity: low, medium, high, info |
| FraudIndicator | score | integer, required | 0–100 |
| FraudIndicator | created_at | date, required | ISO date |
| Investigation | investigation_id | string, required, unique PK | `INVG-2026-` plus six digits |
| Investigation | entity_type, entity_id | string, required | typed entity reference; group/relationship references are non-row exceptions |
| Investigation | opened_at | date, required | ISO date |
| Investigation | status | enum, required | open, needs_review, closed |
| Investigation | assigned_to | string, required | synthetic queue/owner |
| Investigation | resolution | string, optional | blank until resolved |
| InvestigationEvent | event_id, investigation_id | string, required; PK/FK | event ID unique; investigation must exist |
| InvestigationEvent | event_type, from_status, to_status, event_at, actor, reason | string/date, required | destination status: open, needs_review, closed; blank prior status only for initial event |
| ClaimStatusEvent | event_id, claim_id | string, required; PK/FK | event ID unique; claim must exist |
| ClaimStatusEvent | from_status, to_status, event_at, actor, reason | string/date, required | status enum matches Claim; blank prior status only for initial event |
