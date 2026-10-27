from pathlib import Path
import json
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Insurance Fraud Triage", page_icon="🔎", layout="wide")
st.title("Synthetic Insurance Fraud Triage")
st.caption("Demonstration using generated data only. A risk score is a triage signal, not proof of fraud.")
DATA = Path("data/generated")
results_path = DATA / "detection_results.csv"
report_path = DATA / "validation_report.json"
if not results_path.exists():
    st.warning("Data has not been generated yet. From the project root, run: `python scripts/run_pipeline.py`")
    st.stop()
df = pd.read_csv(results_path, keep_default_na=False)
report = json.loads(report_path.read_text()) if report_path.exists() else {}
metrics = report.get("metrics", {})
a,b,c,d = st.columns(4)
a.metric("Claims analyzed", f"{len(df):,}")
b.metric("Investigate", f"{(df.decision == 'investigate').sum():,}")
c.metric("Review", f"{(df.decision == 'review').sum():,}")
d.metric("Mean risk score", f"{df.risk_score.mean():.1f}/100")
st.subheader("Evaluation against planted claim-level ground truth")
cols = st.columns(5)
for col, key, label in zip(cols,["precision","recall","f1","false_positive_rate","false_negative_rate"],["Precision","Recall","F1 score","False-positive rate","False-negative rate"]):
    col.metric(label, f"{metrics.get(key,0):.3f}")
st.subheader("Claim queue")
min_score = st.slider("Minimum risk score",0,100,20)
decisions = st.multiselect("Decision", ["investigate","review","no_flag"], default=["investigate","review"])
query = st.text_input("Search claim or claimant ID")
view = df[(pd.to_numeric(df.risk_score) >= min_score) & df.decision.isin(decisions)]
if query:
    view = view[view.claim_id.str.contains(query,case=False) | view.claimant_id.str.contains(query,case=False)]
st.dataframe(view, use_container_width=True, hide_index=True)
st.subheader("Selected claim evidence")
if not view.empty:
    selected = st.selectbox("Claim ID", view.claim_id.tolist())
    row = view[view.claim_id == selected].iloc[0]
    st.write({"claim_id":row.claim_id,"decision":row.decision,"risk_score":int(row.risk_score),"evidence":row.evidence})
    st.info("Review evidence and source records before taking action. This synthetic prototype does not make final fraud determinations.")
