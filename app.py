import calendar
import pandas as pd
import streamlit as st
from datetime import date, datetime, timedelta

from lib.data_store import read_csv

# --------------------------------------------------
# CLEAR NAV STATE
# --------------------------------------------------
st.session_state.pop("selected_task_id", None)
st.session_state.pop("selected_event_id", None)

# --------------------------------------------------
# PAGE
# --------------------------------------------------
st.set_page_config(page_title="Event Ops", layout="wide")
st.title("🏐 Event Operations Dashboard")

EVENT_COLS = ["event_id","event_name","location","start_date","end_date","status"]
TASK_COLS  = ["task_id","scope","event_id","task_name","due_date","owner","status","priority","category","notes"]

# --------------------------------------------------
# CSS (COMPACT CALENDAR)
# --------------------------------------------------
st.markdown("""
<style>
.day-cell {
    height: 80px;
    padding: 6px;
    border-radius: 8px;
    border: 1px solid #e5e7eb;
    background: #fff;
}
.day-num {
    font-weight: 600;
    font-size: 14px;
}
.indicators {
    margin-top: 6px;
    font-size: 13px;
}
.dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 4px;
}
.ev { background:#3b82f6; }
.ev-on { background:#16a34a; }
.tk { background:#f59e0b; }
.tk-over { background:#dc2626; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def parse_date(s):
    try:
        return datetime.strptime(str(s), "%Y-%m-%d").date()
    except:
        return None

def overlaps(d, s, e):
    return bool(s and e and s <= d <= e)

def open_event(eid):
    st.session_state["selected_event_id"] = eid
    st.switch_page("pages/2_Event_Detail.py")

def open_task(tid):
    st.session_state["selected_task_id"] = tid
    st.switch_page("pages/3_Tasks.py")

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------
events = read_csv("data/events.csv", EVENT_COLS)
tasks  = read_csv("data/tasks.csv", TASK_COLS)

today = date.today()

tasks["scope"] = tasks["scope"].astype(str).fillna("")
tasks.loc[tasks["scope"].eq(""), "scope"] = "General"

events["start"] = events["start_date"].apply(parse_date)
events["end"]   = events["end_date"].apply(parse_date)
tasks["due"]    = tasks["due_date"].apply(parse_date)

# --------------------------------------------------
# SUMMARY
# --------------------------------------------------
c1,c2,c3 = st.columns(3)
c1.metric("Events", len(events))
c2.metric("Tasks", len(tasks))
c3.metric("Overdue", len(tasks[(tasks["due"] < today) & (tasks["status"]!="Done")]))

st.divider()
st.subheader("🗓️ Calendar")

# --------------------------------------------------
# CALENDAR CONTROLS
# --------------------------------------------------
m1,m2 = st.columns(2)
with m1:
    year = st.number_input("Year", 2000, 2100, today.year)
with m2:
    month = st.selectbox("Month", list(range(1,13)), index=today.month-1)

cal = calendar.Calendar()
weeks = cal.monthdatescalendar(year, month)

# --------------------------------------------------
# CALENDAR GRID (COMPACT)
# --------------------------------------------------
for week in weeks:
    cols = st.columns(7)
    for i, d in enumerate(week):
        with cols[i]:
            st.markdown("<div class='day-cell'>", unsafe_allow_html=True)

            if d.month == month:
                if st.button(str(d.day), key=f"d_{d}"):
                    st.session_state["agenda_date"] = d.isoformat()
            else:
                st.markdown(f"<div class='day-num'>{d.day}</div>", unsafe_allow_html=True)

            # counts
            ev_today = events[events.apply(lambda r: overlaps(d, r["start"], r["end"]), axis=1)]
            tk_today = tasks[tasks["due"] == d]
            tk_over  = tk_today[(tk_today["status"]!="Done") & (d < today)]

            st.markdown("<div class='indicators'>", unsafe_allow_html=True)

            for _ in range(len(ev_today)):
                st.markdown("<span class='dot ev'></span>", unsafe_allow_html=True)

            for _ in range(len(tk_today)):
                st.markdown("<span class='dot tk'></span>", unsafe_allow_html=True)

            for _ in range(len(tk_over)):
                st.markdown("<span class='dot tk-over'></span>", unsafe_allow_html=True)

            st.markdown("</div></div>", unsafe_allow_html=True)

# --------------------------------------------------
# AGENDA (MAIN CONTENT)
# --------------------------------------------------
st.divider()
st.subheader("📌 Day agenda")

agenda_iso = st.session_state.get("agenda_date")
agenda_day = parse_date(agenda_iso) if agenda_iso else None

if not agenda_day:
    st.info("Click a day to view agenda.")
else:
    st.write(f"**{agenda_day}**")

    st.markdown("### Events")
    ev = events[events.apply(lambda r: overlaps(agenda_day, r["start"], r["end"]), axis=1)]
    if ev.empty:
        st.info("No events.")
    else:
        for _, r in ev.iterrows():
            if st.button(r["event_name"], key=f"ag_ev_{r['event_id']}"):
                open_event(r["event_id"])

    st.markdown("### Tasks")
    td = tasks[tasks["due"] == agenda_day]
    if td.empty:
        st.info("No tasks.")
    else:
        for _, r in td.iterrows():
            if st.button(r["task_name"], key=f"ag_tk_{r['task_id']}"):
                open_task(r["task_id"])
