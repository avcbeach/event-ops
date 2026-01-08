import streamlit as st
import pandas as pd
from lib.data_store import read_csv, write_csv

DATA_DIR = "data"

st.title("Nominate Referees")

events = read_csv(f"{DATA_DIR}/events.csv")
refs = read_csv(f"{DATA_DIR}/referees.csv")
assign = read_csv(f"{DATA_DIR}/assignments.csv")

# basic safety
required_assign_cols = ["assign_id", "ref_id", "event_id", "position"]
for c in required_assign_cols:
    if c not in assign.columns:
        assign[c] = "" if c != "assign_id" else 0

event_id = st.selectbox("Event", events["event_id"].astype(str).tolist())

# build readable referee labels
name_cols = []
for c in ["last_name", "first_name", "name"]:
    if c in refs.columns:
        name_cols.append(c)

def label_row(r):
    parts = []
    if "ref_id" in r: parts.append(f"#{r['ref_id']}")
    if "last_name" in r or "first_name" in r:
        parts.append(f"{str(r.get('last_name','')).strip()} {str(r.get('first_name','')).strip()}".strip())
    elif "name" in r:
        parts.append(str(r.get("name","")).strip())
    if "nf" in r: parts.append(str(r["nf"]))
    return " | ".join([p for p in parts if p])

refs["__label"] = refs.apply(label_row, axis=1)
ref_label = st.selectbox("Referee", refs["__label"].tolist())

role = st.selectbox("Role (position)", [
    "Referee Delegate", "Referee", "Candidate", "Line Judge", "Other"
])

if st.button("Add nomination"):
    ref_id = int(ref_label.split("|")[0].replace("#", "").strip())

    # prevent exact duplicates
    dup = assign[
        (assign["event_id"].astype(str) == str(event_id)) &
        (assign["ref_id"].astype(str) == str(ref_id)) &
        (assign["position"].astype(str) == str(role))
    ]
    if not dup.empty:
        st.warning("This referee + role already exists for this event.")
        st.stop()

    # assign_id incremental
    max_id = pd.to_numeric(assign["assign_id"], errors="coerce").fillna(0).max()
    new_row = {
        "assign_id": int(max_id) + 1,
        "ref_id": ref_id,
        "event_id": event_id,
        "position": role
    }
    assign = pd.concat([assign, pd.DataFrame([new_row])], ignore_index=True)

    write_csv(f"{DATA_DIR}/assignments.csv", assign, f"Add assignment: {event_id} ref {ref_id}")
    st.success("Added.")
