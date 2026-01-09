import pandas as pd
import streamlit as st
from lib.data_store import read_csv, write_csv

st.title("Event Manager")

EVENT_COLS = ["event_id","event_name","location","start_date","end_date","status"]
STATUS_OPTIONS = ["Planned", "Open", "Confirmed", "Ongoing", "Completed", "Cancelled"]

events = read_csv("data/events.csv", EVENT_COLS)

st.subheader("Event list")
if events.empty:
    st.info("No events yet.")
else:
    st.dataframe(events[["event_id","event_name","location","start_date","end_date","status"]], use_container_width=True)

st.divider()
st.subheader("Add new event")

with st.form("add_event"):
    event_id = st.text_input("event_id (unique)", placeholder="EVT-2026-THA-SAMILA-OPEN")
    event_name = st.text_input("event_name")
    location = st.text_input("location")
    start_date = st.text_input("start_date (YYYY-MM-DD)")
    end_date = st.text_input("end_date (YYYY-MM-DD)")
    status = st.selectbox("status", STATUS_OPTIONS, index=0)
    add = st.form_submit_button("Add event")

if add:
    if not event_id.strip():
        st.error("event_id is required.")
    elif (events["event_id"].astype(str) == event_id.strip()).any():
        st.error("This event_id already exists.")
    else:
        new_row = {
            "event_id": event_id.strip(),
            "event_name": event_name.strip(),
            "location": location.strip(),
            "start_date": start_date.strip(),
            "end_date": end_date.strip(),
            "status": status.strip(),
        }
        events = pd.concat([events, pd.DataFrame([new_row])], ignore_index=True)
        write_csv("data/events.csv", events, f"Add event {event_id.strip()}")
        st.success("Added.")
        st.rerun()

st.divider()
st.subheader("Open event")

if events.empty:
    st.info("Add an event first.")
else:
    pick = st.selectbox(
        "Select",
        [f"{r['event_name']} ({r['event_id']})" for _, r in events.iterrows()]
    )
    if st.button("Open selected event"):
        eid = pick.split("(")[-1].replace(")", "").strip()
        st.session_state["selected_event_id"] = eid
        st.switch_page("pages/2_Event_Detail.py")
