import pandas as pd
import streamlit as st
from datetime import datetime

from lib.data_store import read_csv, write_csv

EVENT_COLS = ["event_id","event_name","location","start_date","end_date","status"]
TASK_COLS  = ["task_id","scope","event_id","task_name","due_date","owner","status","priority","category","notes"]
FILE_COLS  = ["file_id","event_id","title","link","notes","updated_at"]
RPT_COLS   = ["report_id","event_id","title","link","notes","updated_at"]

TASK_STATUS = ["Not started","In progress","Done","Blocked"]
EVENT_STATUS = ["Planned","Open","Confirmed","Ongoing","Completed","Cancelled"]

def now_iso():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

def next_int_id(df, col):
    if df.empty or col not in df.columns:
        return 1
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    return int(s.max()) + 1 if not s.empty else 1

st.title("Event Detail")

eid = st.session_state.get("selected_event_id", "")
if not eid:
    st.warning("No event selected. Go to Event Manager and open an event.")
    st.stop()

events = read_csv("data/events.csv", EVENT_COLS)
tasks  = read_csv("data/tasks.csv", TASK_COLS)
files  = read_csv("data/event_files.csv", FILE_COLS)
reports= read_csv("data/event_reports.csv", RPT_COLS)

# normalize scope
tasks["scope"] = tasks["scope"].astype(str).fillna("")
blank = tasks["scope"].str.strip().eq("")
tasks.loc[blank & tasks["event_id"].astype(str).str.strip().ne(""), "scope"] = "Event"
tasks.loc[blank & tasks["event_id"].astype(str).str.strip().eq(""), "scope"] = "General"

event_row = events[events["event_id"].astype(str) == str(eid)]
if event_row.empty:
    st.error(f"Event not found: {eid}")
    st.stop()

e = event_row.iloc[0]

st.subheader(f"{e['event_name']} ({e['event_id']})")
st.write(f"📍 {e['location']} | 🗓️ {e['start_date']} → {e['end_date']} | ✅ {e['status']}")

tab1, tab2, tab3, tab4 = st.tabs(["Event info", "Tasks", "Files", "Reports"])

with tab1:
    st.subheader("Edit event info")
    with st.form("edit_event"):
        name = st.text_input("event_name", value=e["event_name"])
        loc  = st.text_input("location", value=e["location"])
        sd   = st.text_input("start_date (YYYY-MM-DD)", value=e["start_date"])
        ed   = st.text_input("end_date (YYYY-MM-DD)", value=e["end_date"])
        status = st.selectbox("status", EVENT_STATUS, index=EVENT_STATUS.index(e["status"]) if e["status"] in EVENT_STATUS else 0)
        save = st.form_submit_button("Save event info")

    if save:
        events.loc[events["event_id"] == eid, "event_name"] = name.strip()
        events.loc[events["event_id"] == eid, "location"] = loc.strip()
        events.loc[events["event_id"] == eid, "start_date"] = sd.strip()
        events.loc[events["event_id"] == eid, "end_date"] = ed.strip()
        events.loc[events["event_id"] == eid, "status"] = status.strip()
        write_csv("data/events.csv", events, f"Update event {eid}")
        st.success("Saved.")
        st.rerun()

with tab2:
    st.subheader("Event tasks")

    ev_tasks = tasks[(tasks["scope"].str.lower() == "event") & (tasks["event_id"] == eid)].copy()

    st.markdown("### Add task")
    with st.form("add_task"):
        task_name = st.text_input("task_name")
        due_date  = st.text_input("due_date (YYYY-MM-DD)")
        owner     = st.text_input("owner")
        status    = st.selectbox("status", TASK_STATUS, index=0)
        priority  = st.text_input("priority (optional)")
        category  = st.text_input("category (optional)")
        notes     = st.text_area("notes (optional)")
        add = st.form_submit_button("Add task")

    if add:
        new_id = str(next_int_id(tasks, "task_id"))
        new_row = {
            "task_id": new_id,
            "scope": "Event",
            "event_id": eid,
            "task_name": task_name.strip(),
            "due_date": due_date.strip(),
            "owner": owner.strip(),
            "status": status.strip(),
            "priority": priority.strip(),
            "category": category.strip(),
            "notes": notes.strip(),
        }
        tasks = pd.concat([tasks, pd.DataFrame([new_row])], ignore_index=True)
        write_csv("data/tasks.csv", tasks, f"Add task {new_id} for {eid}")
        st.success("Task added.")
        st.rerun()

    st.markdown("### Edit tasks")
    if ev_tasks.empty:
        st.info("No tasks yet.")
    else:
        ev_tasks2 = ev_tasks.copy()
        ev_tasks2["delete"] = False

        edited = st.data_editor(
            ev_tasks2[["task_id","task_name","due_date","owner","status","priority","category","notes","delete"]],
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "status": st.column_config.SelectboxColumn("status", options=TASK_STATUS),
                "delete": st.column_config.CheckboxColumn("delete"),
            }
        )

        c1,c2 = st.columns(2)
        with c1:
            if st.button("Save changes", key="save_tasks"):
                # write back edits
                keep = tasks[~((tasks["scope"].str.lower()=="event") & (tasks["event_id"]==eid) & (tasks["task_id"].isin(edited["task_id"].astype(str))))].copy()
                out = pd.concat([keep, edited.drop(columns=["delete"])], ignore_index=True)
                write_csv("data/tasks.csv", out, f"Update tasks for {eid}")
                st.success("Saved.")
                st.rerun()

        with c2:
            if st.button("Delete checked", key="del_tasks"):
                to_del = edited[edited["delete"] == True]
                if to_del.empty:
                    st.warning("No tasks checked.")
                else:
                    out = tasks[~tasks["task_id"].isin(to_del["task_id"].astype(str))].copy()
                    write_csv("data/tasks.csv", out, f"Delete tasks for {eid}")
                    st.success(f"Deleted {len(to_del)} task(s).")
                    st.rerun()

with tab3:
    st.subheader("Files (links)")
    ev_files = files[files["event_id"] == eid].copy()

    with st.form("add_file"):
        title = st.text_input("title")
        link  = st.text_input("link (Google Drive / OneDrive)")
        notes = st.text_area("notes (optional)")
        addf = st.form_submit_button("Add file link")

    if addf:
        fid = str(next_int_id(files, "file_id"))
        row = {
            "file_id": fid,
            "event_id": eid,
            "title": title.strip(),
            "link": link.strip(),
            "notes": notes.strip(),
            "updated_at": now_iso(),
        }
        files = pd.concat([files, pd.DataFrame([row])], ignore_index=True)
        write_csv("data/event_files.csv", files, f"Add file link {fid} for {eid}")
        st.success("Added.")
        st.rerun()

    if ev_files.empty:
        st.info("No files yet.")
    else:
        ev_files2 = ev_files.copy()
        ev_files2["delete"] = False
        edited = st.data_editor(ev_files2, use_container_width=True, num_rows="dynamic",
                                column_config={"delete": st.column_config.CheckboxColumn("delete")})
        c1,c2 = st.columns(2)
        with c1:
            if st.button("Save changes", key="save_files"):
                keep = files[~((files["event_id"]==eid) & (files["file_id"].isin(edited["file_id"].astype(str))))].copy()
                edited["updated_at"] = now_iso()
                out = pd.concat([keep, edited.drop(columns=["delete"])], ignore_index=True)
                write_csv("data/event_files.csv", out, f"Update files for {eid}")
                st.success("Saved.")
                st.rerun()
        with c2:
            if st.button("Delete checked", key="del_files"):
                to_del = edited[edited["delete"]==True]
                out = files[~files["file_id"].isin(to_del["file_id"].astype(str))].copy()
                write_csv("data/event_files.csv", out, f"Delete files for {eid}")
                st.success("Deleted.")
                st.rerun()

with tab4:
    st.subheader("Reports (links)")
    ev_r = reports[reports["event_id"] == eid].copy()

    with st.form("add_report"):
        title = st.text_input("title", key="r_title")
        link  = st.text_input("link", key="r_link")
        notes = st.text_area("notes (optional)", key="r_notes")
        addr = st.form_submit_button("Add report link")

    if addr:
        rid = str(next_int_id(reports, "report_id"))
        row = {
            "report_id": rid,
            "event_id": eid,
            "title": title.strip(),
            "link": link.strip(),
            "notes": notes.strip(),
            "updated_at": now_iso(),
        }
        reports = pd.concat([reports, pd.DataFrame([row])], ignore_index=True)
        write_csv("data/event_reports.csv", reports, f"Add report link {rid} for {eid}")
        st.success("Added.")
        st.rerun()

    if ev_r.empty:
        st.info("No reports yet.")
    else:
        ev_r2 = ev_r.copy()
        ev_r2["delete"] = False
        edited = st.data_editor(ev_r2, use_container_width=True, num_rows="dynamic",
                                column_config={"delete": st.column_config.CheckboxColumn("delete")})
        c1,c2 = st.columns(2)
        with c1:
            if st.button("Save changes", key="save_reports"):
                keep = reports[~((reports["event_id"]==eid) & (reports["report_id"].isin(edited["report_id"].astype(str))))].copy()
                edited["updated_at"] = now_iso()
                out = pd.concat([keep, edited.drop(columns=["delete"])], ignore_index=True)
                write_csv("data/event_reports.csv", out, f"Update reports for {eid}")
                st.success("Saved.")
                st.rerun()
        with c2:
            if st.button("Delete checked", key="del_reports"):
                to_del = edited[edited["delete"]==True]
                out = reports[~reports["report_id"].isin(to_del["report_id"].astype(str))].copy()
                write_csv("data/event_reports.csv", out, f"Delete reports for {eid}")
                st.success("Deleted.")
                st.rerun()
