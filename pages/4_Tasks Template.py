import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

from lib.data_store import read_csv, write_csv

TPL_COLS  = ["template_id","scope","template_name","task_name","due_offset_days","default_owner","category","priority"]
EVENT_COLS = ["event_id","event_name","location","start_date","end_date","status"]
TASK_COLS  = ["task_id","scope","event_id","task_name","due_date","owner","status","priority","category","notes"]

SCOPE = ["Event","General"]

def next_int_id(df, col):
    if df.empty or col not in df.columns:
        return 1
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    return int(s.max()) + 1 if not s.empty else 1

st.title("Task Templates")

tpl = read_csv("data/task_templates.csv", TPL_COLS)
events = read_csv("data/events.csv", EVENT_COLS)
tasks  = read_csv("data/tasks.csv", TASK_COLS)

# normalize template scope
tpl["scope"] = tpl["scope"].astype(str).fillna("")
tpl.loc[tpl["scope"].str.strip().eq(""), "scope"] = "Event"

st.subheader("Add template row")
with st.form("add_tpl"):
    scope = st.selectbox("Scope", SCOPE, index=0)
    template_name = st.text_input("template_name", value="AVC Standard")
    task_name = st.text_input("task_name")
    due_offset_days = st.number_input("due_offset_days", value=0, step=1,
        help="Event template: relative to event start_date. General template: relative to today when applied.")
    owner = st.text_input("default_owner (optional)")
    category = st.text_input("category (optional)")
    priority = st.text_input("priority (optional)")
    add = st.form_submit_button("Add row")

if add:
    base = read_csv("data/task_templates.csv", TPL_COLS)
    new_id = str(next_int_id(base, "template_id"))
    row = {
        "template_id": new_id,
        "scope": scope,
        "template_name": template_name.strip(),
        "task_name": task_name.strip(),
        "due_offset_days": str(int(due_offset_days)),
        "default_owner": owner.strip(),
        "category": category.strip(),
        "priority": priority.strip(),
    }
    base = pd.concat([base, pd.DataFrame([row])], ignore_index=True)
    write_csv("data/task_templates.csv", base, f"Add template row {new_id}")
    st.success("Added.")
    st.rerun()

st.divider()
st.subheader("View / Edit templates")

if tpl.empty:
    st.info("No templates yet.")
else:
    tpl2 = tpl.copy()
    tpl2["delete"] = False
    edited = st.data_editor(tpl2, use_container_width=True, num_rows="dynamic",
                            column_config={"delete": st.column_config.CheckboxColumn("delete")})

    c1,c2 = st.columns(2)
    with c1:
        if st.button("Save changes"):
            out = edited.drop(columns=["delete"], errors="ignore")
            write_csv("data/task_templates.csv", out, "Update templates")
            st.success("Saved.")
            st.rerun()
    with c2:
        if st.button("Delete checked"):
            to_del = edited[edited["delete"] == True]
            out = tpl[~tpl["template_id"].isin(to_del["template_id"].astype(str))].copy()
            write_csv("data/task_templates.csv", out, "Delete template rows")
            st.success("Deleted.")
            st.rerun()

st.divider()
st.subheader("Apply template (General tasks only)")
st.caption("This applies General templates into tasks.csv (useful for office work). Event templates are applied inside Event Detail later if you want.")

general_templates = sorted([x for x in tpl[tpl["scope"].str.lower()=="general"]["template_name"].unique().tolist() if str(x).strip()])
if not general_templates:
    st.info("No General templates yet.")
else:
    tname = st.selectbox("Template", general_templates)
    if st.button("Apply now (creates tasks due today+offset)"):
        base_tasks = read_csv("data/tasks.csv", TASK_COLS)
        new_id = next_int_id(base_tasks, "task_id")

        rows = tpl[(tpl["scope"].str.lower()=="general") & (tpl["template_name"]==tname)].copy()
        today = datetime.today().date()

        out_rows = []
        for _, r in rows.iterrows():
            offset = int(pd.to_numeric(r["due_offset_days"], errors="coerce") or 0)
            due = today + timedelta(days=offset)
            out_rows.append({
                "task_id": str(new_id),
                "scope": "General",
                "event_id": "",
                "task_name": r["task_name"],
                "due_date": due.isoformat(),
                "owner": r["default_owner"],
                "status": "Not started",
                "priority": r["priority"],
                "category": r["category"],
                "notes": f"From template: {tname}",
            })
            new_id += 1

        base_tasks = pd.concat([base_tasks, pd.DataFrame(out_rows)], ignore_index=True)
        write_csv("data/tasks.csv", base_tasks, f"Apply General template {tname}")
        st.success("Applied.")
        st.rerun()
