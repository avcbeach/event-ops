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
# CSS: COMPACT MONTH GRID (NO BIG EMPTY BOXES)
# --------------------------------------------------
st.markdown("""
<style>
.day {
  padding: 6px 6px 8px 6px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fff;
}
.day.empty {
  background: #fafafa;
  border-style: dashed;
  opacity: 0.85;
}
.day.off {
  background: #ffffff;
  border: none;
  padding: 6px;
  opacity: 0.35;
}
.daynum button {
  width: 100%;
  padding: 2px 6px;
  border-radius: 8px;
  text-align: left;
  font-weight: 600;
  font-size: 14px;
}
.counters {
  margin-top: 6px;
  font-size: 12px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.badge {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 999px;
  line-height: 1.2;
  white-space: nowrap;
}

/* Legend colors */
.b-ev { background:#e8f1ff; color:#1e40af; }     /* planned/upcoming event */
.b-on { background:#e9f7ef; color:#065f46; }     /* ongoing event */
.b-tk { background:#fef3c7; color:#92400e; }     /* tasks due */
.b-od { background:#fee2e2; color:#991b1b; }     /* overdue tasks */

.small-note { color:#6b7280; font-size:12px; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def parse_date(s):
    try:
        return datetime.strptime(str(s), "%Y-%m-%d").date()
    except Exception:
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

# normalize scope
tasks["scope"] = tasks["scope"].astype(str).fillna("")
blank = tasks["scope"].str.strip().eq("")
tasks.loc[blank & tasks["event_id"].astype(str).str.strip().ne(""), "scope"] = "Event"
tasks.loc[blank & tasks["event_id"].astype(str).str.strip().eq(""), "scope"] = "General"

# parse dates
events["start"] = events["start_date"].apply(parse_date)
events["end"]   = events["end_date"].apply(parse_date)
tasks["due"]    = tasks["due_date"].apply(parse_date)

# merge event names into tasks
tasks = tasks.merge(events[["event_id","event_name"]], on="event_id", how="left")
tasks["event_name"] = tasks["event_name"].fillna("")

# --------------------------------------------------
# HELPERS FOR VIEWS
# --------------------------------------------------
def events_for_day(d):
    if events.empty:
        return events.iloc[0:0]
    mask = events.apply(lambda r: overlaps(d, r["start"], r["end"]), axis=1)
    return events[mask].copy()

def tasks_for_day(d):
    if tasks.empty:
        return tasks.iloc[0:0]
    return tasks[tasks["due"] == d].copy()

# --------------------------------------------------
# 1) DASHBOARD INFO
# --------------------------------------------------
st.subheader("Dashboard")

ongoing = events[(events["start"].notna()) & (events["end"].notna()) & (events["start"] <= today) & (events["end"] >= today)]
upcoming_14 = events[(events["start"].notna()) & (events["start"] > today) & (events["start"] <= today + timedelta(days=14))]
overdue = tasks[(tasks["due"].notna()) & (tasks["due"] < today) & (tasks["status"].astype(str).str.lower() != "done")]

c1,c2,c3,c4 = st.columns(4)
c1.metric("Total events", len(events))
c2.metric("Ongoing", len(ongoing))
c3.metric("Upcoming (14 days)", len(upcoming_14))
c4.metric("Overdue tasks", len(overdue))

st.divider()

# --------------------------------------------------
# 3) CALENDAR (MONTH VIEW)
# --------------------------------------------------
st.subheader("Calendar")

m1,m2 = st.columns([2,2])
with m1:
    year = st.number_input("Year", 2000, 2100, value=today.year, step=1)
with m2:
    month = st.selectbox("Month", list(range(1,13)), index=today.month-1)

st.markdown("<div class='small-note'>Month view shows counts only. Click a day number to update Day agenda above.</div>", unsafe_allow_html=True)

cal = calendar.Calendar(firstweekday=0)
weeks = cal.monthdatescalendar(int(year), int(month))

dow = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
hdr = st.columns(7)
for i, name in enumerate(dow):
    hdr[i].markdown(f"**{name}**")

for week in weeks:
    cols = st.columns(7, gap="small")
    for i, d in enumerate(week):
        with cols[i]:
            if d.month != month:
                st.markdown(f"<div class='day off'>{d.day}</div>", unsafe_allow_html=True)
                continue

            ev_d = events_for_day(d)
            td_d = tasks_for_day(d)

            ev_ongoing = ev_d[ev_d["status"].astype(str).str.lower() == "ongoing"]
            ev_other = ev_d[ev_d["status"].astype(str).str.lower() != "ongoing"]

            td_over = td_d[(td_d["status"].astype(str).str.lower() != "done") & (td_d["due"].notna()) & (td_d["due"] < today)]

            is_empty = (len(ev_d) == 0 and len(td_d) == 0)
            st.markdown(f"<div class='day {'empty' if is_empty else ''}'>", unsafe_allow_html=True)

            # day number clickable
            if st.button(f"{d.day}{' ⭐' if d == today else ''}", key=f"day_{d.isoformat()}"):
                st.session_state["agenda_date"] = d.isoformat()
                st.rerun()

            if not is_empty:
                parts = []
                if len(ev_other) > 0:
                    parts.append(f"<span class='badge b-ev'>🟦 E {len(ev_other)}</span>")
                if len(ev_ongoing) > 0:
                    parts.append(f"<span class='badge b-on'>🟩 E {len(ev_ongoing)}</span>")
                if len(td_d) > 0:
                    parts.append(f"<span class='badge b-tk'>🟨 T {len(td_d)}</span>")
                if len(td_over) > 0:
                    parts.append(f"<span class='badge b-od'>🔴 {len(td_over)}</span>")

                st.markdown("<div class='counters'>" + "".join(parts) + "</div>", unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# --------------------------------------------------
# 2) DAY AGENDA
# --------------------------------------------------
st.subheader("Day agenda")

default_agenda = st.session_state.get("agenda_date")
if isinstance(default_agenda, str):
    default_agenda = parse_date(default_agenda)

agenda_day = st.date_input("Select date", value=default_agenda or today)
st.session_state["agenda_date"] = agenda_day.isoformat()

st.markdown(f"**Selected date:** {agenda_day.isoformat()}")

# Events
st.markdown("### 🏐 Events")
ev = events_for_day(agenda_day)
if ev.empty:
    st.info("No events.")
else:
    ev["is_ongoing"] = (ev["status"].astype(str).str.lower() == "ongoing").astype(int)
    ev = ev.sort_values(["is_ongoing","start_date","event_name"], ascending=[False, True, True])
    for _, r in ev.iterrows():
        icon = "🟩" if str(r["status"]).lower() == "ongoing" else "🟦"
        line = f"{icon} {r['event_name']} — {r['location']} ({r['start_date']} → {r['end_date']})"
        if st.button(line, key=f"ag_ev_{agenda_day.isoformat()}_{r['event_id']}"):
            open_event(r["event_id"])

# Tasks due
st.markdown("### 📝 Tasks due")
td = tasks_for_day(agenda_day)
if td.empty:
    st.info("No tasks.")
else:
    td["is_over"] = ((td["status"].astype(str).str.lower() != "done") & (td["due"].notna()) & (td["due"] < today)).astype(int)
    td = td.sort_values(["is_over","scope","event_name","task_name"], ascending=[False, True, True, True])

    for _, r in td.iterrows():
        overdue_icon = "🔴" if r["is_over"] == 1 else "🟨"
        scope = "General" if str(r["scope"]).lower() == "general" else (r["event_name"] or "Event")
        owner = f" — {r['owner']}" if str(r["owner"]).strip() else ""
        status = f" [{r['status']}]" if str(r["status"]).strip() else ""
        line = f"{overdue_icon} {r['task_name']} — {scope}{owner}{status}"
        if st.button(line, key=f"ag_tk_{agenda_day.isoformat()}_{r['task_id']}"):
            open_task(r["task_id"])

st.divider()

# --------------------------------------------------
# 4) LEGENDS (AT THE BOTTOM)
# --------------------------------------------------
st.subheader("Legends")

l1,l2,l3,l4 = st.columns(4)
l1.markdown("<span class='badge b-ev'>🟦 Event (planned / upcoming)</span>", unsafe_allow_html=True)
l2.markdown("<span class='badge b-on'>🟩 Event (ongoing)</span>", unsafe_allow_html=True)
l3.markdown("<span class='badge b-tk'>🟨 Tasks due</span>", unsafe_allow_html=True)
l4.markdown("<span class='badge b-od'>🔴 Overdue tasks</span>", unsafe_allow_html=True)
