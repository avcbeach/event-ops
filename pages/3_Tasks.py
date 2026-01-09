import pandas as pd
import streamlit as st
from datetime import date

from lib.data_store import read_csv, write_csv

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
TASK_COLS  = ["task_id","scope","event_id","task_name","due_date","owner","status","priority","category","notes"]
EVENT_COLS = ["event_id","event_name","location","start_date","end_date","status"]

TASK_STATUS = ["Not started","In progress","Done","Blocked"]
SCOPE = ["General","Event"]

# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def next_int_id(df, col):
    if df.empty:
        return 1
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    return int(s.max()) + 1 if not s.empty else 1

def open_event(eid):
    st.session_state["selected_event_id"] = eid
    st.switch_page("pages/2_Event_Detail.py")

def mark_done(task_id):
    base = read_csv("data/tasks.csv", TASK_COLS)
    base.loc[base["task_id"].astype(str) == str(task_id), "status"] = "Done"
    write_csv("data/tasks.csv", base, f"Mark task {task_id} done")

# --------------------------------------------------
# PAGE
# --------------------------------------------------
st.title("📝 Tasks")

events = read_csv("data/events.csv", EVENT_COLS)
tasks  = read_csv("data/tasks.csv", TASK_COLS)

# normalize scope
tasks["scope"] = tasks["scope"].astype(str).fillna("")
tasks.loc[tasks["scope"].str.strip() == "", "scope"] = "General"

# enrich event name
tasks = tasks.merge(
    events[["event_id","event_name"]],
    on="event_id",
    how="left"
)
tasks["event_name"] = tasks["event_name"].fillna("")

# --------------------------------------------------
# FILTERS
# --------------------------------------------------
st.subheader("Filters")

c1, c2, c3 = st.columns([2,1.2,1.8])
with c1:
    q = st.text_input("Search", "")
with c2:
    scope = st.selectbox("Scope", ["All"] + SCOPE)
with c3:
    status = st.selectbox("Status", ["All"] + TASK_STATUS)

view = tasks.copy()

if scope != "All":
    view = view[view["scope"] == scope]

if status != "All":
    view = view[view["status"] == status]

if q.strip():
    qq = q.lower()
    view = view[
        view["task_name"].str.lower().str.contains(qq, na=False) |
        view["event_name"].str.lower().str.contains(qq, na=False) |
        view["owner"].str.lower().str.contains(qq, na=False)
    ]

# sort
today = date.today().isoformat()
view["is_done"] = view["status"] == "Done"
view = view.sort_values(["is_done","due_date","task_name"])

st.divider()

# --------------------------------------------------
# TASK LIST (CLICK → POPUP)
# --------------------------------------------------
st.subheader("Task list")

if view.empty:
    st.info("No tasks found.")
else:
    for _, r in view.iterrows():
        task_id = str(r["task_id"])
        is_done = r["status"] == "Done"
        overdue = (str(r["due_date"]) < today) and not is_done

        icon = "✅" if is_done else ("🔴" if overdue else "🟨")
        scope_label = "General" if r["scope"] == "General" else r["event_name"]

        with st.container(border=True):
            left, right = st.columns([6,1])

            with left:
                if st.button(
                    f"{icon} {r['task_name']} — {scope_label}",
                    key=f"open_{task_id}",
                ):
                    st.session_state["popup_task_id"] = task_id
                    st.session_state["show_task_popup"] = True

                st.caption(f"Due: {r['due_date']} | Owner: {r['owner']} | Status: {r['status']}")

            with right:
                if not is_done:
                    if st.button("✔ Done", key=f"done_{task_id}"):
                        mark_done(task_id)
                        st.success("Task marked as done.")
                        st.rerun()

# --------------------------------------------------
# TASK DETAIL POPUP (MODAL)
# --------------------------------------------------
if st.session_state.get("show_task_popup"):
    task_id = st.session_state.get("popup_task_id")

    row = tasks[tasks["task_id"].astype(str) == str(task_id)]
    if not row.empty:
        t = row.iloc[0]

        @st.dialog("📝 Task details")
        def task_dialog():
            left, right = st.columns([3,2])

            with left:
                st.markdown(f"### {t['task_name']}")
                st.write(f"**Task ID:** {t['task_id']}")
                st.write(f"**Scope:** {t['scope']}")
                if t["scope"] == "Event":
                    st.write(f"**Event:** {t['event_name']}")
                    if st.button("Open event"):
                        open_event(t["event_id"])

                st.write(f"**Due date:** {t['due_date']}")
                st.write(f"**Owner:** {t['owner']}")
                st.write(f"**Status:** {t['status']}")

            with right:
                st.write(f"**Priority:** {t['priority']}")
                st.write(f"**Category:** {t['category']}")
                st.write("**Notes:**")
                st.write(t["notes"] if str(t["notes"]).strip() else "—")

            st.divider()

            c1, c2 = st.columns(2)
            with c1:
                if t["status"] != "Done":
                    if st.button("✔ Mark as Done"):
                        mark_done(t["task_id"])
                        st.session_state["show_task_popup"] = False
                        st.success("Task completed.")
                        st.rerun()

            with c2:
                if st.button("Close"):
                    st.session_state["show_task_popup"] = False
                    st.rerun()

        task_dialog()

# --------------------------------------------------
# ADD TASK
# --------------------------------------------------
st.divider()
st.subheader("Add new task")

with st.form("add_task"):
    scope_in = st.selectbox("Scope", SCOPE)

    event_id = ""
    if scope_in == "Event" and not events.empty:
        pick = st.selectbox(
            "Event",
            [f"{r['event_name']} ({r['event_id']})" for _, r in events.iterrows()]
        )
        event_id = pick.split("(")[-1].replace(")", "").strip()

    task_name = st.text_input("Task name")
    due_date  = st.text_input("Due date (YYYY-MM-DD)", value=str(date.today()))
    owner     = st.text_input("Owner")
    status_in = st.selectbox("Status", TASK_STATUS)
    notes     = st.text_area("Notes")

    add = st.form_submit_button("Add task")

if add:
    base = read_csv("data/tasks.csv", TASK_COLS)
    new_id = str(next_int_id(base,"task_id"))

    row = {
        "task_id": new_id,
        "scope": scope_in,
        "event_id": event_id if scope_in=="Event" else "",
        "task_name": task_name,
        "due_date": due_date,
        "owner": owner,
        "status": status_in,
        "priority": "",
        "category": "",
        "notes": notes,
    }

    base = pd.concat([base, pd.DataFrame([row])], ignore_index=True)
    write_csv("data/tasks.csv", base, f"Add task {new_id}")
    st.success("Task added.")
    st.rerun()
