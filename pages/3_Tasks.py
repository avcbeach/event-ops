import pandas as pd
import streamlit as st
from datetime import date

from lib.data_store import read_csv, write_csv

# --------------------------------------------------
# SCHEMAS
# --------------------------------------------------
TASK_COLS  = ["task_id","scope","event_id","task_name","due_date","owner","status","priority","category","notes"]
EVENT_COLS = ["event_id","event_name","location","start_date","end_date","status"]

TASK_STATUS = ["Not started","In progress","Done","Blocked"]
SCOPE = ["General","Event"]

# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def next_int_id(df, col):
    if df.empty or col not in df.columns:
        return 1
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    return int(s.max()) + 1 if not s.empty else 1

def open_event(eid):
    st.session_state["selected_event_id"] = eid
    st.switch_page("pages/2_Event_Detail.py")

# --------------------------------------------------
# PAGE
# --------------------------------------------------
st.title("Tasks")

events = read_csv("data/events.csv", EVENT_COLS)
tasks  = read_csv("data/tasks.csv", TASK_COLS)

# normalize scope (safe)
tasks["scope"] = tasks["scope"].astype(str).fillna("")
blank = tasks["scope"].str.strip().eq("")
tasks.loc[blank & tasks["event_id"].astype(str).str.strip().ne(""), "scope"] = "Event"
tasks.loc[blank & tasks["event_id"].astype(str).str.strip().eq(""), "scope"] = "General"

# enrich event name
tasks = tasks.merge(
    events[["event_id","event_name"]],
    on="event_id",
    how="left"
)
tasks["event_name"] = tasks["event_name"].fillna("")

# --------------------------------------------------
# HANDLE NAV FROM HOMEPAGE (CLICKING A TASK)
# --------------------------------------------------
nav_task_id = st.session_state.pop("selected_task_id", None)
if nav_task_id:
    st.session_state["current_task_id"] = str(nav_task_id)

# --------------------------------------------------
# FILTERS (TOP)
# --------------------------------------------------
st.subheader("Filters")

c1, c2, c3 = st.columns([2,1.2,1.8])
with c1:
    q = st.text_input("Search", "")
with c2:
    scope = st.selectbox("Scope", ["All"] + SCOPE, index=0)
with c3:
    status = st.selectbox("Status", ["All"] + TASK_STATUS, index=0)

view = tasks.copy()

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

# --------------------------------------------------
# TASK DETAILS BLOCK (UNDER TABLE)
# --------------------------------------------------
st.divider()
st.subheader("Task details")

current_id = st.session_state.get("current_task_id")

if not current_id or tasks.empty:
    st.info("Select a task to view details.")
else:
    row = tasks[tasks["task_id"].astype(str) == str(current_id)]
    if row.empty:
        st.info("Selected task not found.")
    else:
        t = row.iloc[0]

        # display card-like block
        left, right = st.columns([3,2])

        with left:
            st.markdown(f"### 📝 {t['task_name']}")
            st.write(f"**Task ID:** {t['task_id']}")
            st.write(f"**Scope:** {t['scope']}")

            if str(t["event_id"]).strip():
                st.write(f"**Event:** {t['event_name']}  \n**Event ID:** {t['event_id']}")
                if st.button("Open event page", key=f"open_event_{t['event_id']}"):
                    open_event(t["event_id"])
            else:
                st.write("**Event:** (General task)")

            st.write(f"**Due date:** {t['due_date']}")
            st.write(f"**Owner:** {t['owner']}")
            st.write(f"**Status:** {t['status']}")

        with right:
            st.write(f"**Priority:** {t['priority']}")
            st.write(f"**Category:** {t['category']}")
            st.write("**Notes:**")
            st.write(t["notes"] if str(t["notes"]).strip() else "—")

        # quick edit (optional, but very useful)
        with st.expander("Quick update this task"):
            with st.form(f"quick_update_{t['task_id']}"):
                new_status = st.selectbox("Status", TASK_STATUS, index=TASK_STATUS.index(t["status"]) if t["status"] in TASK_STATUS else 0)
                new_owner = st.text_input("Owner", value=str(t["owner"]))
                new_due = st.text_input("Due date (YYYY-MM-DD)", value=str(t["due_date"]))
                new_priority = st.text_input("Priority", value=str(t["priority"]))
                new_category = st.text_input("Category", value=str(t["category"]))
                new_notes = st.text_area("Notes", value=str(t["notes"]))

                save_one = st.form_submit_button("Save this task")

            if save_one:
                base = read_csv("data/tasks.csv", TASK_COLS)
                mask = base["task_id"].astype(str) == str(t["task_id"])
                base.loc[mask, "status"] = new_status
                base.loc[mask, "owner"] = new_owner
                base.loc[mask, "due_date"] = new_due
                base.loc[mask, "priority"] = new_priority
                base.loc[mask, "category"] = new_category
                base.loc[mask, "notes"] = new_notes

                write_csv("data/tasks.csv", base, f"Quick update task {t['task_id']}")
                st.success("Task updated.")
                st.rerun()

# --------------------------------------------------
# TASK TABLE (FIRST)
# --------------------------------------------------
st.divider()
st.subheader("Task list")

if view.empty:
    st.info("No tasks found.")
else:
    table = view.copy()
    table["delete"] = False

    edited = st.data_editor(
        table[[
            "task_id","scope","event_name","event_id",
            "task_name","due_date","owner",
            "status","priority","category","notes","delete"
        ]],
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "status": st.column_config.SelectboxColumn("status", options=TASK_STATUS),
            "scope": st.column_config.SelectboxColumn("scope", options=SCOPE),
            "delete": st.column_config.CheckboxColumn("delete"),
        }
    )

    c1, c2, c3 = st.columns([1,1,2])

    with c1:
        if st.button("Save changes"):
            base = read_csv("data/tasks.csv", TASK_COLS)
            # remove rows being replaced
            base = base[~base["task_id"].astype(str).isin(edited["task_id"].astype(str))].copy()
            out = pd.concat(
                [base, edited.drop(columns=["delete","event_name"], errors="ignore")],
                ignore_index=True
            )
            write_csv("data/tasks.csv", out, "Update tasks")
            st.success("Tasks updated.")
            st.rerun()

    with c2:
        if st.button("Delete checked"):
            to_del = edited[edited["delete"] == True]
            if to_del.empty:
                st.warning("No tasks selected.")
            else:
                base = read_csv("data/tasks.csv", TASK_COLS)
                out = base[~base["task_id"].astype(str).isin(to_del["task_id"].astype(str))].copy()
                write_csv("data/tasks.csv", out, "Delete tasks")
                st.success(f"Deleted {len(to_del)} task(s).")
                st.rerun()

    with c3:
        # selector for detail view (table-first, details right after)
        options = edited["task_id"].astype(str).tolist()
        default_id = st.session_state.get("current_task_id")
        if default_id not in options:
            default_id = options[0] if options else None

        selected_id = st.selectbox(
            "Show details for task",
            options=options,
            index=options.index(default_id) if default_id in options else 0,
            key="task_detail_picker"
        )
        st.session_state["current_task_id"] = selected_id

# --------------------------------------------------
# ADD TASK (BOTTOM)
# --------------------------------------------------
st.divider()
st.subheader("Add new task")

with st.form("add_task"):
    scope_in = st.selectbox("Scope", SCOPE, index=0)

    event_id = ""
    if scope_in == "Event":
        if events.empty:
            st.warning("No events available.")
        else:
            pick = st.selectbox(
                "Event",
                [f"{r['event_name']} ({r['event_id']})" for _, r in events.iterrows()]
            )
            event_id = pick.split("(")[-1].replace(")", "").strip()

    task_name = st.text_input("Task name")
    due_date  = st.text_input("Due date (YYYY-MM-DD)", value=str(date.today()))
    owner     = st.text_input("Owner")
    status_in = st.selectbox("Status", TASK_STATUS, index=0)
    priority  = st.text_input("Priority (optional)")
    category  = st.text_input("Category (optional)")
    notes     = st.text_area("Notes (optional)")

    add = st.form_submit_button("Add task")

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
    st.success("Task added.")
    st.session_state["current_task_id"] = new_id
    st.rerun()
