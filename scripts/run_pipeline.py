import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.pipeline import run_pipeline

p = argparse.ArgumentParser(description="Generate synthetic insurance data and run fraud detection.")
p.add_argument("--seed", type=int, default=20261022)
p.add_argument("--claims", type=int, default=5000)
p.add_argument("--claimants", type=int, default=2000)
p.add_argument("--providers", type=int, default=500)
p.add_argument("--edges", type=int, default=8000)
p.add_argument("--data-dir", default="data/generated")
p.add_argument("--truth-dir", default="data/ground_truth")
a = p.parse_args()
print(json.dumps(run_pipeline(a.seed,a.claims,a.claimants,a.providers,a.edges,a.data_dir,a.truth_dir),indent=2))
