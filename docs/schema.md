# Schema and validation design

See `data_dictionary.md` for fields, identifiers and cardinalities. The CSV files form the reproducible seed dataset; foreign keys are checked in `src/validation.py`.

## Entity links
- Claimant → Policy → Claim
- Claimant → Claim
- Incident → Claim
- Provider → Claim and Invoice
- Claim → Invoice → Payment
- RelationshipEdge → typed source and target entity IDs
- FraudIndicator and Investigation → typed entity references

## Exception handling
Known exception records are labelled in the source row where applicable and documented in the separate ground-truth file. The validator emits machine-readable issue codes and does not repair the data silently. `missing_policy_reference`, `payment_exceeds_approved`, and `duplicate_invoice` are expected in the deliberately injected test data.
