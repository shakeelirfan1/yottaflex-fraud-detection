# Source manifest

- Provenance: entirely synthetic; no public or personal data imported.
- Generator: `src.generator.generate_dataset`.
- Default seed: `20261022`.
- Default scale: 5,000 claims, 2,000 claimants, 500 providers, 8,000 relationship edges.
- Ground truth: `data/ground_truth/ground_truth.csv`; evaluation-only and not used as detector input. The synthetic ground-truth CSV is included so reviewers can reproduce evaluation from a clone.
- Generated manifest: `data/generated/manifest.json`.
- Repeatability: full-size generator outputs and ground truth were generated twice with seed `20261022`; all generated-table hashes matched in the remediation workspace.
- Distribution: claimant and provider assignments use seeded heavy-tailed weights to include one-off and repeat activity.
- SQL seed snapshot: `data/generated/seed_data.sql`, exported from generated CSVs; it includes intentional labelled anomalies and should be loaded with foreign-key enforcement temporarily disabled.
- Lifecycle example: investigation events preserve initial status and selected explicit status changes; claim status events record each claim initial state.
