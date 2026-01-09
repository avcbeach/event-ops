import os
import streamlit as st

st.write("OWNER:", os.getenv("GITHUB_OWNER"))
st.write("REPO:", os.getenv("GITHUB_REPO"))

import calendar
import pandas as pd
import streamlit as st
from datetime import date, datetime, timedelta

from lib.data_store import read_csv

st.set_page_config(page_title="Event Ops", layout="wide")
st.title("🏐 Event Operations Dashboard")

EVENT_COLS = ["event_id","event_name","location","start_date","end_date","status"]
TASK_COLS  = ["task_id","scope","event_id","task_name","due_date","owner","status","priority","category","notes"]

def parse_date(s):
    try:
        return datetime.strptime(str(s), "%Y-%m-%d").date()
    except Exception:
        return None

def overlaps(day, start, end):
    return bool(start and end and start <= day <= end)

def safe(x):
    return "" if pd.isna(x) else str(x)

def short_label(text, max_len=95):
    t = (text or "").strip()
    return t if len(t) <= max_len else t[:max_len-1] + "…"

def popover_or_expander(label: str):
    if hasattr(st, "popover"):
        return st.popover(label)
    return st.expander(label)

def open_event(eid: str):
    st.session_state["selected_event_id"] = eid
    st.switch_page("pages/2_Event_Detail.py")

def open_task(tid: str):
    st.session_state["selected_task_id"] = tid
    st.switch_page("pages/3_Tasks.py")

# ---- load from GitHub ----
events = read_csv("data/events.csv", EVENT_COLS)
tasks  = read_csv("data/tasks.csv", TASK_COLS)

today = date.today()

# normalize scope
if not tasks.empty:
    tasks["scope"] = tasks["scope"].astype(str).fillna("")
    blank = tasks["scope"].str.strip().eq("")
    tasks.loc[blank & tasks["event_id"].astype(str).str.strip().ne(""), "scope"] = "Event"
    tasks.loc[blank & tasks["event_id"].astype(str).str.strip().eq(""), "scope"] = "General"

# parse dates
if not events.empty:
    events["start"] = events["start_date"].apply(parse_date)
    events["end"] = events["end_date"].apply(parse_date)
else:
    events["start"] = []
    events["end"] = []

if not tasks.empty:
    tasks["due"] = tasks["due_date"].apply(parse_date)
else:
    tasks["due"] = []

# join event name into tasks
if not tasks.empty and not events.empty:
    tasks = tasks.merge(events[["event_id","event_name"]], on="event_id", how="left")
    tasks["event_name"] = tasks["event_name"].fillna("")
else:
    tasks["event_name"] = ""

# quick summary
ongoing = events[(events["start"].notna()) & (events["end"].notna()) & (events["start"] <= today) & (events["end"] >= today)] if not events.empty else pd.DataFrame()
upcoming = events[(events["start"].notna()) & (events["start"] > today) & (events["start"] <= today + timedelta(days=14))] if not events.empty else pd.DataFrame()
overdue = tasks[(tasks["due"].notna()) & (tasks["due"] < today) & (tasks["status"].astype(str).str.lower() != "done")] if not tasks.empty else pd.DataFrame()

c1,c2,c3,c4 = st.columns(4)
c1.metric("Total events", len(events))
c2.metric("Ongoing events", len(ongoing))
c3.metric("Upcoming (14 days)", len(upcoming))
c4.metric("Overdue tasks", len(overdue))

st.divider()

# ---- calendar ----
st.subheader("🗓️ Monthly calendar")

m1,m2,m3 = st.columns([2,2,6])
with m1:
    year = st.number_input("Year", 2000, 2100, value=today.year, step=1)
with m2:
    month = st.selectbox("Month", list(range(1,13)), index=today.month-1)
with m3:
    st.caption("Click day = agenda. Click event/task name = open. “+more” shows full list.")

cal = calendar.Calendar(firstweekday=0)
weeks = cal.monthdatescalendar(int(year), int(month))

def events_for_day(d):
    if events.empty: return events.iloc[0:0]
    mask = events.apply(lambda r: overlaps(d, r["start"], r["end"]), axis=1)
    out = events[mask].copy()
    if not out.empty:
        out = out.sort_values(["start_date","event_name"], na_position="last")
    return out

def tasks_for_day(d):
    if tasks.empty or "due" not in tasks.columns: return tasks.iloc[0:0]
    out = tasks[tasks["due"] == d].copy()
    if not out.empty:
        out = out.sort_values(["scope","event_name","task_name"], na_position="last")
    return out

dow = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
hdr = st.columns(7)
for i,n in enumerate(dow):
    hdr[i].markdown(f"**{n}**")

MAX_E = 3
MAX_T = 2

for week in weeks:
    cols = st.columns(7, gap="small")
    for i, d in enumerate(week):
        in_month = (d.month == month)
        with cols[i]:
            with st.container(border=True):
                if not in_month:
                    st.caption(str(d.day))
                    st.caption(" ")
                    continue

                label = f"{d.day} ⭐" if d == today else str(d.day)
                if st.button(label, key=f"day_{d.isoformat()}"):
                    st.session_state["agenda_date"] = d.isoformat()

                ev = events_for_day(d)
                td = tasks_for_day(d)

                if ev.empty and td.empty:
                    st.caption(" ")
                    continue

                if not ev.empty:
                    st.caption("Events")
                    shown = ev.head(MAX_E)
                    for _, r in shown.iterrows():
                        eid = safe(r["event_id"]).strip()
                        name = safe(r["event_name"]).strip() or "(No name)"
                        loc = safe(r["location"]).strip()
                        text = name if not loc else f"{name} — {loc}"
                        if st.button(short_label(text), key=f"ev_{d.isoformat()}_{eid}"):
                            open_event(eid)

                    rem = len(ev) - len(shown)
                    if rem > 0:
                        with popover_or_expander(f"+{rem} more events"):
                            for _, r in ev.iloc[MAX_E:].iterrows():
                                eid = safe(r["event_id"]).strip()
                                name = safe(r["event_name"]).strip() or "(No name)"
                                loc = safe(r["location"]).strip()
                                status = safe(r["status"]).strip()
                                text = name if not loc else f"{name} — {loc}"
                                if status:
                                    text = f"{text} [{status}]"
                                if st.button(short_label(text, 120), key=f"evp_{d.isoformat()}_{eid}"):
                                    open_event(eid)

                if not td.empty:
                    st.caption("Tasks due")
                    shown = td.head(MAX_T)
                    for _, r in shown.iterrows():
                        tid = safe(r["task_id"]).strip()
                        tname = safe(r["task_name"]).strip() or "(No task)"
                        scope = safe(r["scope"]).strip()
                        evname = safe(r.get("event_name","")).strip()
                        owner = safe(r["owner"]).strip()
                        status = safe(r["status"]).strip()

                        if scope.lower() == "general":
                            text = f"{tname} (General)"
                        else:
                            text = tname if not evname else f"{tname} — {evname}"

                        meta = []
                        if owner: meta.append(owner)
                        if status: meta.append(status)
                        if meta:
                            text = f"{text} [{', '.join(meta)}]"

                        if st.button(short_label(text, 120), key=f"tk_{d.isoformat()}_{tid}"):
                            open_task(tid)

                    rem = len(td) - len(shown)
                    if rem > 0:
                        with popover_or_expander(f"+{rem} more tasks"):
                            for _, r in td.iloc[MAX_T:].iterrows():
                                tid = safe(r["task_id"]).strip()
                                tname = safe(r["task_name"]).strip() or "(No task)"
                                scope = safe(r["scope"]).strip()
                                evname = safe(r.get("event_name","")).strip()
                                owner = safe(r["owner"]).strip()
                                status = safe(r["status"]).strip()

                                if scope.lower() == "general":
                                    text = f"{tname} (General)"
                                else:
                                    text = tname if not evname else f"{tname} — {evname}"

                                meta = []
                                if owner: meta.append(f"Owner: {owner}")
                                if status: meta.append(status)
                                if meta:
                                    text = f"{text} ({' | '.join(meta)})"

                                if st.button(short_label(text, 140), key=f"tkp_{d.isoformat()}_{tid}"):
                                    open_task(tid)

st.divider()

# ---- agenda ----
st.subheader("📌 Day agenda")
agenda_iso = st.session_state.get("agenda_date", "")
agenda_day = parse_date(agenda_iso) if agenda_iso else None

if not agenda_day:
    st.info("Click a day number to view agenda.")
else:
    st.write(f"Selected day: **{agenda_day.isoformat()}**")

    st.markdown("### Events")
    ev = events_for_day(agenda_day)
    if ev.empty:
        st.info("No events on this day.")
    else:
        for _, r in ev.iterrows():
            eid = safe(r["event_id"]).strip()
            name = safe(r["event_name"]).strip() or "(No name)"
            loc = safe(r["location"]).strip()
            status = safe(r["status"]).strip()
            dates = f"{safe(r['start_date'])} → {safe(r['end_date'])}"
            left,right = st.columns([6,1])
            with left:
                meta = []
                if loc: meta.append(loc)
                if status: meta.append(status)
                meta.append(dates)
                st.write(f"**{name}** — " + " | ".join(meta))
            with right:
                if st.button("Open", key=f"ag_ev_{agenda_day.isoformat()}_{eid}"):
                    open_event(eid)

    st.markdown("### Tasks due")
    td = tasks_for_day(agenda_day)
    if td.empty:
        st.info("No tasks due on this day.")
    else:
        for _, r in td.iterrows():
            tid = safe(r["task_id"]).strip()
            tname = safe(r["task_name"]).strip()
            scope = safe(r["scope"]).strip()
            evname = safe(r.get("event_name","")).strip()
            owner = safe(r["owner"]).strip()
            status = safe(r["status"]).strip()
            left,right = st.columns([6,1])
            with left:
                meta = []
                meta.append("General" if scope.lower()=="general" else "Event")
                if evname and scope.lower()!="general":
                    meta.append(evname)
                if owner: meta.append(f"Owner: {owner}")
                if status: meta.append(status)
                st.write(f"**{tname}** — " + " | ".join(meta))
            with right:
                if st.button("Open", key=f"ag_tk_{agenda_day.isoformat()}_{tid}"):
                    open_task(tid)
