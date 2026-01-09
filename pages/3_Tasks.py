import pandas as pd
import streamlit as st
from datetime import date

from lib.data_store import read_csv, write_csv

TASK_COLS  = ["task_id","scope","event_id","task_name","due_date","owner","status","priority","category","notes"]
EVENT_COLS = ["event_id","event_name","location","start_date","end_date","status"]

TASK_STATUS = ["Not started","In progress","Done","Blocked"]
SCOPE = ["General","Event"]

def next_int_id(df, col):
    if df.empty or col not in df.columns:
        return 1
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    return int(s.max()) + 1 if not s.empty else 1

st.title("Tasks (Event + General)")

events = read_csv("data/events.csv", EVENT_COLS)
tasks  = read_csv("data/tasks.csv", TASK_COLS)

# normalize scope
tasks["scope"] = tasks["scope"].astype(str).fillna("")
blank = tasks["scope"].str.strip().eq("")
tasks.loc[blank & tasks["event_id"].astype(str).str.strip().ne(""), "scope"] = "Event"
tasks.loc[blank & tasks["event_id"].astype(str).str.strip().eq(""), "scope"] = "General"

# enrich event name
if not tasks.empty and not events.empty:
    tasks = tasks.merge(events[["event_id","event_name"]], on="event_id", how="left")
    tasks["event_name"] = tasks["event_name"].fillna("")
else:
    tasks["event_name"] = ""

selected_task_id = st.session_state.pop("selected_task_id", None)

# Filters
st.subheader("Filters")
c1,c2,c3 = st.columns([2,1.2,1.8])
with c1:
    q = st.text_input("Search", "")
with c2:
    scope = st.selectbox("Scope", ["All"] + SCOPE, index=0)
with c3:
    status = st.selectbox("Status", ["All"] + TASK_STATUS, index=0)

view = tasks.copy()

if selected_task_id:
    view = view[view["task_id"].astype(str) == str(selected_task_id)]
    st.info(f"Showing selected task_id: {selected_task_id}")

if scope != "All":
    view = view[view["scope"].str.lower() == scope.lower()]

if status != "All":
    view = view[view["status"] == status]

if q.strip():
    qq = q.lower()
    view = view[
        view["task_name"].str.lower().str.contains(qq, na=False) |
        view["event_name"].str.lower().str.contains(qq, na=False) |
        view["owner"].str.lower().str.contains(qq, na=False) |
        view["notes"].str.lower().str.contains(qq, na=False)
    ]

st.divider()

# Add
st.subheader("Add task")
with st.form("add_task"):
    scope_in = st.selectbox("Scope", SCOPE, index=0)
    event_id = ""
    if scope_in == "Event":
        if events.empty:
            st.error("No events. Add events first.")
            st.stop()
        pick = st.selectbox("Event", [f"{r['event_name']} ({r['event_id']})" for _, r in events.iterrows()])
        event_id = pick.split("(")[-1].replace(")", "").strip()

    task_name = st.text_input("Task name")
    due_date  = st.text_input("Due date (YYYY-MM-DD)", value=str(date.today()))
    owner     = st.text_input("Owner")
    status_in = st.selectbox("Status", TASK_STATUS, index=0)
    priority  = st.text_input("Priority (optional)")
    category  = st.text_input("Category (optional)")
    notes     = st.text_area("Notes (optional)")
    add = st.form_submit_button("Add")

if add:
    base = read_csv("data/tasks.csv", TASK_COLS)
    new_id = str(next_int_id(base, "task_id"))
    row = {
        "task_id": new_id,
        "scope": scope_in,
        "event_id": event_id if scope_in == "Event" else "",
        "task_name": task_name.strip(),
        "due_date": due_date.strip(),
        "owner": owner.strip(),
        "status": status_in.strip(),
        "priority": priority.strip(),
        "category": category.strip(),
        "notes": notes.strip(),
    }
    base = pd.concat([base, pd.DataFrame([row])], ignore_index=True)
    write_csv("data/tasks.csv", base, f"Add task {new_id}")
    st.success("Added.")
    st.rerun()

st.subheader("Edit / Delete tasks")
if view.empty:
    st.info("No tasks.")
else:
    # show editor
    show = view.copy()
    show["delete"] = False
    edited = st.data_editor(
        show[["task_id","scope","event_name","event_id","task_name","due_date","owner","status","priority","category","notes","delete"]],
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "status": st.column_config.SelectboxColumn("status", options=TASK_STATUS),
            "scope": st.column_config.SelectboxColumn("scope", options=SCOPE),
            "delete": st.column_config.CheckboxColumn("delete"),
        }
    )

    c1,c2 = st.columns(2)
    with c1:
        if st.button("Save changes"):
            base = read_csv("data/tasks.csv", TASK_COLS)
            # remove any rows being edited by task_id then add edited rows back
            base = base[~base["task_id"].isin(edited["task_id"].astype(str))].copy()
            out = pd.concat([base, edited.drop(columns=["delete","event_name"], errors="ignore")], ignore_index=True)
            write_csv("data/tasks.csv", out, "Update tasks")
            st.success("Saved.")
            st.rerun()

    with c2:
        if st.button("Delete checked"):
            to_del = edited[edited["delete"] == True]
            if to_del.empty:
                st.warning("No tasks checked.")
            else:
                base = read_csv("data/tasks.csv", TASK_COLS)
                out = base[~base["task_id"].isin(to_del["task_id"].astype(str))].copy()
                write_csv("data/tasks.csv", out, "Delete tasks")
                st.success("Deleted.")
                st.rerun()
