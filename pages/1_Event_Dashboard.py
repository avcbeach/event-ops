import streamlit as st
import pandas as pd
from lib.data_store import read_csv

DATA_DIR = "data"  # adjust if your folder name is different

st.title("Event Dashboard")

events = read_csv(f"{DATA_DIR}/events.csv")
refs = read_csv(f"{DATA_DIR}/referees.csv")
assign = read_csv(f"{DATA_DIR}/assignments.csv")

if events.empty:
    st.error("events.csv is empty or not found.")
    st.stop()

# choose event
event_label = st.selectbox(
    "Select event",
    events["event_id"].astype(str) + " — " + events.get("event_name", events["event_id"].astype(str)).astype(str)
)
event_id = event_label.split(" — ")[0].strip()

st.subheader("Assigned referees (from assignments.csv)")
event_assign = assign[assign["event_id"].astype(str) == str(event_id)].copy()

if event_assign.empty:
    st.info("No referees assigned yet.")
else:
    # join to get referee names
    merged = event_assign.merge(refs, on="ref_id", how="left", suffixes=("", "_ref"))
    cols_to_show = [c for c in ["ref_id", "position", "first_name", "last_name", "nf", "level"] if c in merged.columns]
    st.dataframe(merged[cols_to_show], use_container_width=True)
