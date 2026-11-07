import calendar
from copy import deepcopy
from datetime import date, datetime

import pandas as pd
import streamlit as st

from storage import load_workspace, save_workspace
from roster_workflow import can_publish, classify_issues, employee_month_grid, make_history_entry, set_roster_status, undo_roster_change
from roster_engine import (
    build_roster,
    make_sample_data,
    roster_summary,
    validate_configuration,
    validate_roster,
)
st.set_page_config(page_title="Smart Roster Management System | RosterFlow", page_icon="◷", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
:root { --ink:#17231f; --muted:#75817b; --line:#e7ece8; --green:#176b52; --blue:#315bd6; --mint:#e8f4ee; }
.stApp { background:#f7f9f7; color:var(--ink); font-family:'DM Sans',sans-serif; }
[data-testid="stSidebar"] { background:#fff; border-right:1px solid var(--line); }
h1,h2,h3 { font-family:'Manrope',sans-serif !important; letter-spacing:-.035em; }
.hero { background:linear-gradient(112deg,#1e3150,#315bd6 76%,#4977ed); border-radius:16px; padding:26px 30px; color:white; margin:2px 0 22px; }
.hero h1 {color:white!important;font-size:32px!important;margin:0 0 7px!important;}
.hero p {color:#c9e0d5;margin:0;font-size:14px;}
.eyebrow {text-transform:uppercase;letter-spacing:.14em;font-size:10px;font-weight:700;color:#c5d4ff;margin-bottom:10px;}
.section-note { color:#75817b; font-size:13px; margin-top:-8px; }
div[data-testid="stMetric"] {background:white;border:1px solid var(--line);padding:15px 17px;border-radius:14px;}
div[data-testid="stMetricLabel"] p {font-size:12px!important;color:#75817b!important;}
div[data-testid="stMetricValue"] {font-family:'Manrope',sans-serif;font-size:26px!important;}
.callout {background:#fff;border:1px solid var(--line);border-left:4px solid #d89438;border-radius:10px;padding:13px 16px;margin:8px 0;color:#49564f;font-size:13px;}
.ok {border-left-color:#25835f}.bad {border-left-color:#c84e4e}
.stButton>button[kind="primary"] {background:#315bd6;border-color:#315bd6;border-radius:9px;font-weight:700;}
/* Improve text contrast across the app */
:root {
    --ink: #17231f;
    --muted: #52615a;
}

.stApp {
    color: var(--ink);
}

/* Sidebar navigation and labels */
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
    color: #26342e !important;
}

/* Captions and helper text */
[data-testid="stCaptionContainer"],
.stCaption,
small {
    color: #52615a !important;
}

/* Form labels and tab names */
.stApp label,
.stTabs [role="tab"] {
    color: #26342e !important;
}

/* Keep text on the blue hero panel readable */
.hero p {
    color: #e6f1ed !important;
}

.eyebrow {
    color: #e0e8ff !important;
}
</style>
""", unsafe_allow_html=True)


def init_state():
    if "workspace_data" not in st.session_state:
        saved = load_workspace()

        if saved:
            st.session_state.workspace_data = saved["workspace_data"]
            st.session_state.roster = saved.get("roster")
            st.session_state.roster_month = saved.get("roster_month")
            st.session_state.roster_history = saved.get("roster_history", [])
            st.session_state.change_history = saved.get("change_history", [])
            st.session_state.roster_state = saved.get("roster_state", "DRAFT" if saved.get("roster") else "EMPTY")
            st.session_state.undo_stack = saved.get("undo_stack", [])
        else:
            st.session_state.workspace_data = make_sample_data()

    st.session_state.setdefault("roster", None)
    st.session_state.setdefault("roster_month", None)
    st.session_state.setdefault("notice", "")
    st.session_state.setdefault("roster_history", [])
    st.session_state.setdefault("change_history", [])
    st.session_state.setdefault("roster_state", "EMPTY")
    st.session_state.setdefault("undo_stack", [])

init_state()
data = st.session_state.workspace_data


def persist_and_rerun():
    save_workspace({
        "workspace_data": st.session_state.workspace_data,
        "roster": st.session_state.roster,
        "roster_month": st.session_state.roster_month,
        "roster_history": st.session_state.roster_history,
        "change_history": st.session_state.change_history,
        "roster_state": st.session_state.roster_state,
        "undo_stack": st.session_state.undo_stack,
    })
    st.rerun()


page = st.sidebar.radio("WORKSPACE", ["Overview", "Roster", "People & operations", "Coverage & conflicts"], label_visibility="visible")
st.sidebar.markdown("---")
st.sidebar.markdown("**ROSTERFLOW**  ·  Workforce planning")
st.sidebar.caption("Smart Roster Management System · Internship Assessment Prototype")
if st.session_state.roster_history:
    st.sidebar.markdown("---")
    st.sidebar.markdown("**RECENT ROSTERS**")
    for item in reversed(st.session_state.roster_history[-3:]):
        st.sidebar.caption(f'{item.get("month", "Roster")} · {item.get("status", item.get("mode", "Saved"))}')
if st.session_state.change_history:
    st.sidebar.markdown("**RECENT CHANGES**")
    for item in reversed(st.session_state.change_history[-3:]):
        st.sidebar.caption(item)

today = date.today()
month_names = list(calendar.month_name)[1:]
default_month = today.month
default_year = today.year

if page == "Overview":
    st.markdown('<div class="hero"><div class="eyebrow">Monthly workforce planning</div><h1>Plan coverage with confidence.</h1><p>Build a roster around real availability, surface coverage gaps, and recover when plans change.</p></div>', unsafe_allow_html=True)
    summary = roster_summary(data, st.session_state.roster)
    m1,m2,m3,m4,m5,m6 = st.columns(6)
    m1.metric("Employees", len(data["employees"]))
    m2.metric("Brands", len(data["brands"]))
    m3.metric("Processes", len(data["processes"]))
    m4.metric("Pods", len(data["pods"]))
    m5.metric("Coverage", f'{summary["coverage_percent"]}%' if st.session_state.roster is not None else "—")
    m6.metric("Critical gaps", summary["gaps"] if st.session_state.roster is not None else "—")
    st.markdown("### Operations at a glance")
    st.markdown('<p class="section-note">A connected view of the teams and the roster health for your selected month.</p>', unsafe_allow_html=True)
    left,right=st.columns([1.1,.9],gap="large")
    with left:
        st.markdown("#### Brand coverage model")
        brand_rows=[]
        for b in data["brands"]:
            lanes=[r for r in data["requirements"] if r["brand_id"]==b["id"]]
            staff={e["id"] for a in data["assignments"] if a["brand_id"]==b["id"] for e in data["employees"] if a["employee_id"]==e["id"]}
            brand_rows.append({"Brand":b["name"],"Pod":b["pod"],"Pod lead":data.get("pod_leads",{}).get(b["pod"],"—"),"Processes":len(lanes),"Assigned team":len(staff)})
        st.dataframe(pd.DataFrame(brand_rows),hide_index=True,width="stretch",height=360)
    with right:
        st.markdown("#### Roster health")
        if st.session_state.roster is None:
            st.markdown('<div class="callout">No roster generated yet. Choose a month and generate a roster to review staffing and coverage.</div>',unsafe_allow_html=True)
        else:
            validation=validate_roster(data,st.session_state.roster)
            st.metric("Scheduled assignments",summary["assignments"])
            st.metric("Coverage days met",f'{summary["covered"]:,}')
            st.metric("Conflict items",len(validation["issues"]))
            if validation["issues"]: st.warning("There are coverage or scheduling issues to review.")
            else: st.success("All configured coverage requirements are met.")
        st.markdown("#### How it works")
        st.markdown("1. Set monthly staffing and availability.\n2. Generate a roster with the deterministic scheduler.\n3. Review conflicts and adjust assignments.\n4. Revalidate after any change.")

elif page == "Roster":
    st.markdown('<div class="hero"><div class="eyebrow">Roster generator</div><h1>One plan. Every team.</h1><p>Generate a monthly view, inspect assignments, and make changes with immediate validation.</p></div>', unsafe_allow_html=True)
    c1,c2,c3,c4=st.columns([1,1,1.25,1.75])
    with c1: selected_month=st.selectbox("Roster month",month_names,index=default_month-1)
    with c2: selected_year=st.number_input("Year",min_value=2024,max_value=2035,value=default_year,step=1)
    month_num=month_names.index(selected_month)+1
    with c3: generation_mode=st.selectbox("Generation mode",["Standard","Balanced","Smart"],index=1)
    with c4: st.caption({"Standard":"Apply mandatory constraints.","Balanced":"Balance weekly and monthly workload.","Smart":"Prioritize lanes with fewer eligible staff."}[generation_mode])
    if st.button("Generate monthly roster",type="primary"):
        configuration_issues=validate_configuration(data)
        if configuration_issues:
            st.error("Fix the operating model before generating a roster.")
            st.dataframe(pd.DataFrame(configuration_issues),hide_index=True,width="stretch")
        else:
            with st.spinner("Generating and validating the monthly roster…"):
                st.session_state.roster=build_roster(data,int(selected_year),month_num,mode=generation_mode)
                validation=validate_roster(data,st.session_state.roster)
            st.session_state.roster_mode=generation_mode
            st.session_state.roster_month=(int(selected_year),month_num)
            label=f"{selected_month} {int(selected_year)}"
            st.session_state.roster_state="DRAFT"
            st.session_state.roster_history.append(make_history_entry(
                st.session_state.roster_history, st.session_state.roster, label, "DRAFT",
                "scheduler", f"Generated using {generation_mode} mode", roster_summary(data, st.session_state.roster)["coverage_percent"]))
            if validation["issues"]:
                st.warning(f'Roster generated with {len(validation["issues"])} validation finding(s). Review conflicts before publishing.')
            else:
                st.success("Roster generated and validated. No conflicts found.")
    roster=st.session_state.roster
    if roster is not None:
        y,m=st.session_state.roster_month
        if (y,m)!=(int(selected_year),month_num): st.info("The visible roster is for a different month. Generate again to create this month.")
        else:
            validation=validate_roster(data,roster)
            s=roster_summary(data,roster)
            a,b,c=st.columns(3); a.metric("Assigned shifts",s["assignments"]); b.metric("Coverage requirements met",f'{s["covered"]:,}'); c.metric("Coverage gaps",s["gaps"])
            validation=validate_roster(data, roster)
            state_col, review_col, publish_col = st.columns([1, 1, 1])
            state_col.markdown(f"**Roster state: {st.session_state.roster_state}**")
            if st.session_state.roster_state == "PUBLISHED":
                state_col.caption("This version is published. Any subsequent edit returns it to Draft.")
            if review_col.button("Validate and move to Review", disabled=st.session_state.roster_state == "PUBLISHED", key="review_roster"):
                st.session_state.roster_state = "REVIEW"
                st.session_state.roster_history.append(make_history_entry(
                    st.session_state.roster_history, roster, f"{calendar.month_name[m]} {y}", "REVIEW",
                    "user", "Validated for review", s["coverage_percent"]))
                persist_and_rerun()
            critical = [issue for issue in validation["issues"] if issue.get("type") != "Preference warning"]
            if publish_col.button("Publish roster", disabled=not can_publish(validation["issues"]) or st.session_state.roster_state != "REVIEW", key="publish_roster"):
                st.session_state.roster_state = "PUBLISHED"
                st.session_state.roster_history.append(make_history_entry(
                    st.session_state.roster_history, roster, f"{calendar.month_name[m]} {y}", "PUBLISHED",
                    "user", "Published validated roster", s["coverage_percent"]))
                persist_and_rerun()
            if critical and st.session_state.roster_state == "REVIEW":
                st.warning(f"Publishing is disabled while {len(critical)} mandatory conflict(s) remain.")
            with st.expander("Roster version history", expanded=False):
                if st.session_state.roster_history:
                    st.dataframe(pd.DataFrame(st.session_state.roster_history), hide_index=True, width="stretch")
                else:
                    st.caption("No roster versions recorded yet.")
            table=[]
            for row in roster:
                emp=next(e for e in data["employees"] if e["id"]==row["employee_id"])
                br=next((x for x in data["brands"] if x["id"]==row["brand_id"]),None)
                table.append({"Date":row["date"],"Day":date.fromisoformat(row["date"]).strftime("%a"),"Employee":emp["name"],"Pod":emp["pod"],"Brand":br["name"] if br else "—","Process":row["process"] or "—","Status":row["status"]})
            df=pd.DataFrame(table)
            work_df=df[df["Status"]=="Working"].copy()
            with st.expander("Manual roster adjustment · change an assignee"):
                st.caption("Choose an existing shift and an eligible, available employee. The app revalidates the roster after the change.")
                working_rows=[row for row in roster if row["status"]=="Working"]
                if not working_rows:
                    st.info("There are no working assignments to adjust.")
                else:
                    labels=[]
                    for row in working_rows:
                        emp=next(e for e in data["employees"] if e["id"]==row["employee_id"])
                        brand=next((b for b in data["brands"] if b["id"]==row["brand_id"]),None)
                        labels.append(f'{row["date"]} · {emp["name"]} · {brand["name"] if brand else row["brand_id"]} / {row["process"]}')
                    with st.form("manual_assignment_form"):
                        selected_assignment=st.selectbox("Shift to change",labels,key="manual_shift")
                        selected_index=labels.index(selected_assignment)
                        selected_row=working_rows[selected_index]
                        lane_employees=[a["employee_id"] for a in data["assignments"] if a["brand_id"]==selected_row["brand_id"] and a["process"]==selected_row["process"]]
                        day=date.fromisoformat(selected_row["date"])
                        weekly_counts={}
                        for row in roster:
                            if row["status"]=="Working" and date.fromisoformat(row["date"]).isocalendar()[:2]==day.isocalendar()[:2]:
                                weekly_counts[row["employee_id"]]=weekly_counts.get(row["employee_id"],0)+1
                        occupied={row["employee_id"] for row in roster if row["date"]==selected_row["date"] and row["status"]=="Working"}
                        candidates=[]
                        for employee in data["employees"]:
                            eid=employee["id"]
                            unavailable=any(x["employee_id"]==eid and x["date"]==selected_row["date"] for bucket in ("planned_leave","unavailability","comp_offs") for x in data.get(bucket,[]))
                            holiday_block=selected_row["date"] in data.get("holidays",[]) and (not employee.get("holiday_eligible",False) or not next((req.get("operates_on_holidays",False) for req in data["requirements"] if req["brand_id"]==selected_row["brand_id"] and req["process"]==selected_row["process"]),False))
                            if eid in lane_employees and eid not in occupied - {selected_row["employee_id"]} and eid!=selected_row["employee_id"] and employee["weekly_off"]!=day.weekday() and not unavailable and not holiday_block and weekly_counts.get(eid,0)<employee["max_shifts_per_week"]:
                                candidates.append(employee)
                        replacement_options={e["name"]:e["id"] for e in candidates}
                        replacement_name=st.selectbox("Replace with",list(replacement_options),key="manual_replacement") if replacement_options else None
                        save_manual=st.form_submit_button("Apply change and revalidate",disabled=not replacement_options)
                    if save_manual and replacement_name:
                        new_id=replacement_options[replacement_name]
                        old_id=selected_row["employee_id"]
                        selected_row.update({"employee_id":new_id})
                        old_status=next((row for row in roster if row["employee_id"]==old_id and row["date"]==selected_row["date"] and row is not selected_row and row["status"]!="Working"),None)
                        if old_status: old_status.update({"status":"Available","brand_id":"","process":""})
                        new_status=next((row for row in roster if row["employee_id"]==new_id and row["date"]==selected_row["date"] and row is not selected_row and row["status"]!="Working"),None)
                        if new_status: roster.remove(new_status)
                        st.session_state.roster=roster
                        st.session_state.roster_state="DRAFT"
                        result=validate_roster(data,roster)
                        st.session_state.notice=f"Changed the assignee to {replacement_name}; {len(result['issues'])} roster finding(s) remain."
                        st.session_state.change_history.append(f'{datetime.now().strftime("%H:%M")} · {replacement_name} assigned to {selected_row["process"]}')
                        st.session_state.roster_history.append(make_history_entry(
                            st.session_state.roster_history, roster, f"{calendar.month_name[m]} {y}", "DRAFT",
                            "manual edit", f"Assigned {replacement_name} to {selected_row['process']}", roster_summary(data, roster)["coverage_percent"]))
                        persist_and_rerun()
            if st.session_state.notice:
                st.info(st.session_state.notice)
                st.session_state.notice = ""
            with st.expander("Direct employee/day adjustment and undo"):
                employee_names = {employee["name"]: employee["id"] for employee in data["employees"]}
                day_keys = sorted({row["date"] for row in roster})
                with st.form("direct_schedule_form"):
                    chosen_employee = st.selectbox("Employee", sorted(employee_names), key="direct_employee")
                    chosen_day = st.selectbox("Roster date", day_keys, key="direct_date")
                    selected_status = st.selectbox("New status", ["WORK", "OFF", "LEAVE", "HOLIDAY", "COMP-OFF", "UNAVAILABLE"], key="direct_status")
                    lane_options = {f"{brand['name']} · {req['process']}": (brand["id"], req["process"])
                                    for req in data["requirements"] for brand in data["brands"] if req["brand_id"] == brand["id"]}
                    lane_label = st.selectbox("Work assignment", list(lane_options), key="direct_lane") if selected_status == "WORK" else None
                    direct_submit = st.form_submit_button("Apply schedule change and validate")
                if direct_submit:
                    status_values = {"WORK": "Working", "OFF": "Weekly Off", "LEAVE": "Leave", "HOLIDAY": "Holiday",
                                     "COMP-OFF": "Comp-Off", "UNAVAILABLE": "Unavailable"}
                    previous = deepcopy(roster)
                    brand_id, process = lane_options[lane_label] if lane_label else ("", "")
                    set_roster_status(roster, employee_names[chosen_employee], chosen_day, status_values[selected_status], brand_id, process)
                    st.session_state.undo_stack.append(previous)
                    st.session_state.roster = roster
                    st.session_state.roster_state = "DRAFT"
                    impact = validate_roster(data, roster)
                    st.session_state.notice = f"Saved {chosen_employee}'s {selected_status} status for {chosen_day}. Validation found {len(impact['issues'])} issue(s)."
                    st.session_state.change_history.append(f"{datetime.now().strftime('%H:%M')} · {chosen_employee} set to {selected_status} on {chosen_day}")
                    st.session_state.roster_history.append(make_history_entry(
                        st.session_state.roster_history, roster, f"{calendar.month_name[m]} {y}", "DRAFT", "manual edit",
                        f"{chosen_employee}: {selected_status} on {chosen_day}", roster_summary(data, roster)["coverage_percent"]))
                    persist_and_rerun()
                if st.session_state.undo_stack and st.button("Undo latest schedule change", key="undo_schedule"):
                    st.session_state.roster = undo_roster_change(st.session_state.undo_stack)
                    st.session_state.roster_state = "DRAFT"
                    impact = validate_roster(data, st.session_state.roster)
                    st.session_state.notice = f"Latest schedule change undone. Validation found {len(impact['issues'])} issue(s)."
                    st.session_state.change_history.append(f"{datetime.now().strftime('%H:%M')} · schedule change undone")
                    persist_and_rerun()
            view_overview,view_grid,view_company,view_pods,view_brands,view_processes,view_employees=st.tabs(["Overview","Monthly employee grid","Company","Pods","Brands","Processes","Employees"])
            with view_overview:
                st.markdown("#### Brand coverage heatmap")
                gap_keys={(i.get("date"),i.get("brand"),i.get("process")) for i in validation["issues"] if i["type"]=="Coverage gap"}
                heat=[]
                all_days=[date(y,m,d) for d in range(1,calendar.monthrange(y,m)[1]+1)]
                for brand in data["brands"]:
                    row={"Brand":brand["name"]}
                    for weekday in range(7):
                        lanes=[r for r in data["requirements"] if r["brand_id"]==brand["id"] and weekday in r["operating_days"]]
                        lane_days=[(d,req) for d in all_days if d.weekday()==weekday for req in lanes
                                   if d.isoformat() not in data["holidays"] or req.get("operates_on_holidays",False)]
                        total=len(lane_days)
                        missed=sum(1 for d,req in lane_days if (d.isoformat(),brand["name"],req["process"]) in gap_keys)
                        row[calendar.day_abbr[weekday]]=round(100*(total-missed)/total) if total else None
                    heat.append(row)
                heat_df=pd.DataFrame(heat).set_index("Brand")
                def coverage_cell(value):
                    if pd.isna(value): return ""
                    if value >= 100: return "background-color: #e3f2e9; color: #176b52; font-weight: 600"
                    return "background-color: #fde8e7; color: #a13e3e; font-weight: 600"
                st.dataframe(heat_df.style.map(coverage_cell).format("{:.0f}%",na_rep="—"),width="stretch")
                st.caption("Coverage by brand and weekday across the selected month. Blank cells mean no configured operations.")
            with view_grid:
                st.markdown("#### Employee schedule by day")
                grid = employee_month_grid(data, roster, y, m, validation["issues"])
                st.dataframe(pd.DataFrame(grid), hide_index=True, width="stretch", height=560)
                st.caption("WORK, OFF, LEAVE, HOLIDAY, COMP-OFF, UNAVAILABLE, and CONFLICT show each employee's daily status.")
                if validation["issues"]: st.warning(f'{len(validation["issues"])} validation finding(s) need attention.')
                else: st.success("All configured requirements are covered.")
            with view_company:
                st.markdown("#### Company-wide roster")
                st.dataframe(df,hide_index=True,width="stretch",height=440)
                st.download_button("Download roster CSV",df.to_csv(index=False).encode("utf-8"),file_name=f"roster_{y}_{m:02d}.csv",mime="text/csv",key="csv_company")
            with view_pods:
                selected_pod=st.selectbox("Pod",sorted(work_df["Pod"].unique()),key="view_pod")
                pod_df=df[df["Pod"]==selected_pod]
                st.dataframe(pod_df,hide_index=True,width="stretch",height=440)
            with view_brands:
                selected_brand=st.selectbox("Brand",sorted(work_df["Brand"].unique()),key="view_brand")
                brand_df=df[df["Brand"]==selected_brand]
                st.dataframe(brand_df,hide_index=True,width="stretch",height=440)
            with view_processes:
                selected_process=st.selectbox("Process",sorted(data["processes"]),key="view_process")
                process_df=df[df["Process"]==selected_process]
                st.dataframe(process_df,hide_index=True,width="stretch",height=440)
            with view_employees:
                selected_emp=st.selectbox("Employee",sorted(df["Employee"].unique()),key="view_employee")
                employee_df=df[df["Employee"]==selected_emp]
                st.dataframe(employee_df,hide_index=True,width="stretch",height=440)
            with st.expander("Change handling · mark someone unavailable"):
                e_by_name={e["name"]:e["id"] for e in data["employees"]}
                names=sorted(e_by_name)
                selected_employee=st.selectbox("Employee",names,key="unavail_employee")
                selected_day=st.date_input("Unavailable date",value=date(y,m,1),min_value=date(y,m,1),max_value=date(y,m,calendar.monthrange(y,m)[1]))
                if st.button("Mark unavailable and revalidate",key="mark_unavailable"):
                    emp_id=e_by_name[selected_employee]
                    if not any(x["employee_id"]==emp_id and x["date"]==selected_day.isoformat() for x in data["unavailability"]):
                        data["unavailability"].append({"employee_id":emp_id,"date":selected_day.isoformat(),"kind":"Unplanned unavailability"})
                    issues=validate_roster(data,st.session_state.roster)["issues"]
                    relevant=[i for i in issues if i.get("date")==selected_day.isoformat()]
                    st.session_state.notice=f"Unavailable date recorded for {selected_employee}. The existing plan was checked; {len(relevant)} issue(s) need review on {selected_day.isoformat()}."
                    st.session_state.change_history.append(f'{datetime.now().strftime("%H:%M")} · {selected_employee} unavailable')
                    persist_and_rerun()
                if st.session_state.notice:
                    st.success(st.session_state.notice)
                    impact=[i for i in validate_roster(data,st.session_state.roster)["issues"] if i.get("date")==selected_day.isoformat()]
                    if impact:
                        st.dataframe(pd.DataFrame(impact),hide_index=True,width="stretch")
                        gaps=[i for i in impact if i["type"]=="Coverage gap" and i.get("backup_candidates")]
                        if gaps:
                            chosen_gap=st.selectbox("Coverage gap to repair",gaps,format_func=lambda x:f'{x["brand"]} · {x["process"]} ({x["assigned"]}/{x["required"]})')
                            candidate=st.selectbox("Available backup",chosen_gap["backup_candidates"])
                            if st.button("Assign backup and revalidate",type="primary",key="assign_backup"):
                                new_id=e_by_name[candidate]
                                for row in st.session_state.roster:
                                    if row["date"]==chosen_gap["date"] and row["brand_id"]==next(b["id"] for b in data["brands"] if b["name"]==chosen_gap["brand"]) and row["process"]==chosen_gap["process"] and row["status"]=="Working":
                                        invalid=next((x for x in data["unavailability"] if x["employee_id"]==row["employee_id"] and x["date"]==row["date"]),None)
                                        if invalid:
                                            row.update({"status":"Unavailable","brand_id":"","process":""})
                                backup_row=next((row for row in st.session_state.roster if row["date"]==chosen_gap["date"] and row["employee_id"]==new_id and row["status"]!="Working"),None)
                                if backup_row:
                                    backup_row.update({"brand_id":next(b["id"] for b in data["brands"] if b["name"]==chosen_gap["brand"]),
                                                       "process":chosen_gap["process"],"status":"Working"})
                                else:
                                    st.session_state.roster.append({"date":chosen_gap["date"],"employee_id":new_id,
                                        "brand_id":next(b["id"] for b in data["brands"] if b["name"]==chosen_gap["brand"]),
                                        "process":chosen_gap["process"],"status":"Working"})
                                remaining=validate_roster(data,st.session_state.roster)["issues"]
                                st.session_state.roster_state="DRAFT"
                                st.session_state.notice="Backup assigned. Coverage restored." if not any(x.get("date")==selected_day.isoformat() for x in remaining) else "Backup assigned; review the remaining validation findings."
                                st.session_state.change_history.append(f'{datetime.now().strftime("%H:%M")} · {candidate} assigned')
                                st.session_state.roster_history.append(make_history_entry(
                                    st.session_state.roster_history, st.session_state.roster, f"{calendar.month_name[m]} {y}", "DRAFT",
                                    "backup assignment", f"Assigned {candidate} to resolve {chosen_gap['brand']} / {chosen_gap['process']}",
                                    roster_summary(data, st.session_state.roster)["coverage_percent"]))
                                persist_and_rerun()
                    if st.button("Regenerate roster with current availability",key="regen_after_change"):
                        st.session_state.roster=build_roster(data,y,m)
                        st.session_state.notice="Roster regenerated with the updated availability."
                        persist_and_rerun()
            if st.session_state.notice and roster is None: st.success(st.session_state.notice)

elif page == "People & operations":
    st.markdown('<div class="hero"><div class="eyebrow">Operating model</div><h1>People, pods & coverage rules.</h1><p>Review the sample operating model and change roster inputs for this assessment prototype.</p></div>', unsafe_allow_html=True)
    tabs=st.tabs(["Employees","Brands & processes","Pods & rules","Availability"])
    with tabs[0]:
        st.markdown("#### Employee directory")
        edf=pd.DataFrame([{ "ID":e["id"],"Name":e["name"],"Pod":e["pod"],"Skills":", ".join(e["skills"]),"Weekly off":calendar.day_name[e["weekly_off"]],"Preferred days off":[calendar.day_name[d] for d in e.get("preferred_days_off",[])],"Max shifts / week":e["max_shifts_per_week"],"Holiday work": "Eligible" if e.get("holiday_eligible",False) else "Off"} for e in data["employees"]])
        changed_employees=st.data_editor(edf,hide_index=True,width="stretch",height=450,
            disabled=["ID","Skills"],key="employee_editor",
            column_config={"Pod":st.column_config.SelectboxColumn(options=data["pods"],required=True),
                           "Weekly off":st.column_config.SelectboxColumn(options=list(calendar.day_name),required=True),
                           "Preferred days off":st.column_config.MultiselectColumn(options=list(calendar.day_name)),
                           "Max shifts / week":st.column_config.NumberColumn(min_value=1,max_value=7,step=1),
                           "Holiday work":st.column_config.SelectboxColumn(options=["Off","Eligible"],required=True)})
        for _,row in changed_employees.iterrows():
            employee=next(e for e in data["employees"] if e["id"]==row["ID"])
            employee.update({"name":str(row["Name"]),"pod":str(row["Pod"]),
                             "weekly_off":list(calendar.day_name).index(row["Weekly off"]),
                             "preferred_days_off":[list(calendar.day_name).index(day) for day in (row["Preferred days off"] or [])],
                             "max_shifts_per_week":int(row["Max shifts / week"]),
                             "holiday_eligible":row["Holiday work"]=="Eligible"})
        st.caption("Edit names, pods, weekly offs, soft preferred days off, workload limits, and holiday eligibility. Mandatory availability and coverage rules always take priority.")
        with st.form("add_employee_form"):
            st.markdown("##### Add an employee")
            new_name=st.text_input("Employee name",key="new_employee_name")
            new_pod=st.selectbox("Home pod",data["pods"],key="new_employee_pod")
            new_weekly_off=st.selectbox("Weekly off",list(calendar.day_name),key="new_employee_weekly_off")
            new_preferred_off=st.multiselect("Preferred days off (soft preference)",list(calendar.day_name),key="new_employee_preferred_off")
            new_max_shifts=st.number_input("Maximum shifts per week",min_value=1,max_value=7,value=6,key="new_employee_max_shifts")
            new_brands=st.multiselect("Brand access",[b["name"] for b in data["brands"]],key="new_employee_brands")
            new_processes=st.multiselect("Process skills",data["processes"],key="new_employee_processes")
            add_employee=st.form_submit_button("Add employee")
        if add_employee:
            if not new_name.strip() or not new_brands or not new_processes:
                st.error("Enter a name and assign at least one brand and process.")
            elif any(e["name"].casefold()==new_name.strip().casefold() for e in data["employees"]):
                st.error("An employee with that name already exists.")
            else:
                new_id=f"E{max([int(e['id'][1:]) for e in data['employees'] if e['id'][1:].isdigit()] or [0])+1:02d}"
                employee={"id":new_id,"name":new_name.strip(),"pod":new_pod,"skills":list(new_processes),
                          "weekly_off":list(calendar.day_name).index(new_weekly_off),
                          "preferred_days_off":[list(calendar.day_name).index(day) for day in new_preferred_off],
                          "max_shifts_per_week":int(new_max_shifts),"holiday_eligible":False}
                data["employees"].append(employee)
                brand_ids={b["name"]:b["id"] for b in data["brands"]}
                for brand_name in new_brands:
                    for process in new_processes:
                        data["assignments"].append({"employee_id":new_id,"brand_id":brand_ids[brand_name],"process":process})
                st.success(f"Added {new_name.strip()} ({new_id}) and updated their brand/process assignments.")
        if data["employees"]:
            with st.form("remove_employee_form"):
                employee_to_remove=st.selectbox("Remove employee",[e["name"] for e in data["employees"]],key="remove_employee_select")
                remove_employee=st.form_submit_button("Remove employee")
            if remove_employee:
                removed=next(e for e in data["employees"] if e["name"]==employee_to_remove)
                data["employees"].remove(removed)
                data["assignments"]=[a for a in data["assignments"] if a["employee_id"]!=removed["id"]]
                for bucket in ("planned_leave","unavailability","comp_offs"):
                    data[bucket]=[x for x in data.get(bucket,[]) if x["employee_id"]!=removed["id"]]
                if st.session_state.roster is not None:
                    st.session_state.roster=[row for row in st.session_state.roster if row["employee_id"]!=removed["id"]]
                st.warning(f"Removed {removed['name']} from this session. Regenerate the roster to rebuild coverage.")
    with tabs[1]:
        rdf=pd.DataFrame([{ "Brand":next(b["name"] for b in data["brands"] if b["id"]==r["brand_id"]),"Process":r["process"],"Required staff":r["required"],"Operating days":[calendar.day_abbr[d] for d in r["operating_days"]],"Holiday coverage":"Yes" if r.get("operates_on_holidays",False) else "No","Pod":next(b["pod"] for b in data["brands"] if b["id"]==r["brand_id"])} for r in data["requirements"]])
        st.markdown("#### Brand and process coverage requirements")
        changed_requirements=st.data_editor(rdf,hide_index=True,width="stretch",height=450,
            disabled=["Brand","Process","Pod"],key="requirements_editor",
            column_config={"Required staff":st.column_config.NumberColumn(min_value=1,max_value=10,step=1),
                           "Operating days":st.column_config.MultiselectColumn(options=list(calendar.day_abbr),required=True),
                           "Holiday coverage":st.column_config.SelectboxColumn(options=["No","Yes"],required=True)})
        for index,row in changed_requirements.iterrows():
            data["requirements"][index]["required"]=int(row["Required staff"])
            data["requirements"][index]["operating_days"]=[list(calendar.day_abbr).index(day) for day in row["Operating days"]]
            data["requirements"][index]["operates_on_holidays"]=row["Holiday coverage"]=="Yes"
        st.caption("Set staffing need, operating weekdays, and public holiday behavior independently for each brand/process lane.")
        with st.form("add_lane_form"):
            st.markdown("##### Add a process lane to a brand")
            lane_brand=st.selectbox("Brand",[b["name"] for b in data["brands"]],key="new_lane_brand")
            lane_process=st.selectbox("Process",data["processes"],key="new_lane_process")
            lane_team=st.multiselect("Eligible employees",[e["name"] for e in data["employees"]],key="new_lane_team")
            lane_required=st.number_input("Minimum daily staff",min_value=1,max_value=10,value=1,key="new_lane_required")
            lane_days=st.multiselect("Operating weekdays",list(calendar.day_abbr),default=list(calendar.day_abbr[:5]),key="new_lane_days")
            lane_holidays=st.checkbox("Operate on public holidays",key="new_lane_holidays")
            add_lane=st.form_submit_button("Add coverage lane")
        if add_lane:
            brand=next(b for b in data["brands"] if b["name"]==lane_brand)
            if any(r["brand_id"]==brand["id"] and r["process"]==lane_process for r in data["requirements"]):
                st.error("That brand already has a coverage lane for this process.")
            elif not lane_team or not lane_days:
                st.error("Select at least one eligible employee and one operating weekday.")
            else:
                data["requirements"].append({"id":f"R{len(data['requirements'])+1:02d}","brand_id":brand["id"],"process":lane_process,
                    "required":int(lane_required),"operating_days":[list(calendar.day_abbr).index(day) for day in lane_days],"operates_on_holidays":lane_holidays})
                employee_ids={e["name"]:e["id"] for e in data["employees"]}
                for name in lane_team:
                    relation={"employee_id":employee_ids[name],"brand_id":brand["id"],"process":lane_process}
                    if relation not in data["assignments"]: data["assignments"].append(relation)
                st.success(f"Added {lane_brand} / {lane_process} coverage with {len(lane_team)} eligible employee(s).")
        st.markdown("#### Brand directory")
        bdf=pd.DataFrame([{"Brand":b["name"],"Pod":b["pod"]} for b in data["brands"]])
        changed_brands=st.data_editor(bdf,hide_index=True,width="stretch",key="brand_editor",
            column_config={"Brand":st.column_config.TextColumn(required=True),"Pod":st.column_config.SelectboxColumn(options=data["pods"],required=True)})
        for index,row in changed_brands.iterrows():
            data["brands"][index]["name"]=str(row["Brand"]).strip()
            data["brands"][index]["pod"]=row["Pod"]
        with st.form("add_brand_form"):
            st.markdown("##### Add a brand and its first coverage lane")
            new_brand_name=st.text_input("Brand name",key="new_brand_name")
            new_brand_pod=st.selectbox("Owning pod",data["pods"],key="new_brand_pod")
            new_brand_process=st.selectbox("Initial process",data["processes"],key="new_brand_process")
            new_brand_staff=st.multiselect("Eligible employees",[e["name"] for e in data["employees"]],key="new_brand_staff")
            new_brand_required=st.number_input("Daily headcount",min_value=1,max_value=10,value=1,key="new_brand_required")
            new_brand_days=st.multiselect("Operating weekdays",list(calendar.day_abbr),default=list(calendar.day_abbr[:5]),key="new_brand_days")
            new_brand_holidays=st.checkbox("Operate on public holidays",key="new_brand_holidays")
            add_brand=st.form_submit_button("Add brand and lane")
        if add_brand:
            if not new_brand_name.strip() or not new_brand_staff or not new_brand_days:
                st.error("Enter a name, select eligible employees, and choose operating weekdays.")
            elif any(b["name"].casefold()==new_brand_name.strip().casefold() for b in data["brands"]):
                st.error("A brand with that name already exists.")
            else:
                brand_id=f"B{max([int(b['id'][1:]) for b in data['brands'] if b['id'][1:].isdigit()] or [0])+1:02d}"
                data["brands"].append({"id":brand_id,"name":new_brand_name.strip(),"pod":new_brand_pod})
                data["requirements"].append({"id":f"R{len(data['requirements'])+1:02d}","brand_id":brand_id,"process":new_brand_process,
                    "required":int(new_brand_required),"operating_days":[list(calendar.day_abbr).index(day) for day in new_brand_days],"operates_on_holidays":new_brand_holidays})
                employee_ids={e["name"]:e["id"] for e in data["employees"]}
                for name in new_brand_staff:
                    data["assignments"].append({"employee_id":employee_ids[name],"brand_id":brand_id,"process":new_brand_process})
                st.success(f"Added {new_brand_name.strip()} with {len(new_brand_staff)} eligible employee(s).")
        if data["brands"]:
            with st.form("remove_brand_form"):
                brand_to_remove=st.selectbox("Remove brand",[b["name"] for b in data["brands"]],key="remove_brand_select")
                remove_brand=st.form_submit_button("Remove brand")
            if remove_brand:
                removed=next(b for b in data["brands"] if b["name"]==brand_to_remove)
                data["brands"].remove(removed)
                data["requirements"]=[r for r in data["requirements"] if r["brand_id"]!=removed["id"]]
                data["assignments"]=[a for a in data["assignments"] if a["brand_id"]!=removed["id"]]
                if st.session_state.roster is not None: st.session_state.roster=[r for r in st.session_state.roster if r["brand_id"]!=removed["id"]]
                st.warning(f"Removed {removed['name']} and its coverage lanes from this session.")
        st.markdown("#### Employee to brand/process assignments")
        employee_name_by_id={e["id"]:e["name"] for e in data["employees"]}
        brand_name_by_id={b["id"]:b["name"] for b in data["brands"]}
        assignment_rows=[{"Employee":employee_name_by_id.get(a["employee_id"],""),"Brand":brand_name_by_id.get(a["brand_id"],""),"Process":a["process"]} for a in data["assignments"]]
        assignment_edit=st.data_editor(pd.DataFrame(assignment_rows),hide_index=True,width="stretch",height=330,num_rows="dynamic",key="assignment_editor",
            column_config={"Employee":st.column_config.SelectboxColumn(options=list(employee_name_by_id.values()),required=True),
                           "Brand":st.column_config.SelectboxColumn(options=list(brand_name_by_id.values()),required=True),
                           "Process":st.column_config.SelectboxColumn(options=data["processes"],required=True)})
        employee_id_by_name={name:eid for eid,name in employee_name_by_id.items()}
        brand_id_by_name={name:bid for bid,name in brand_name_by_id.items()}
        data["assignments"]=[{"employee_id":employee_id_by_name[row["Employee"]],"brand_id":brand_id_by_name[row["Brand"]],"process":row["Process"]}
            for _,row in assignment_edit.iterrows() if row["Employee"] in employee_id_by_name and row["Brand"] in brand_id_by_name and row["Process"] in data["processes"]]
        with st.form("remove_process_form"):
            process_to_remove=st.selectbox("Remove process and its lanes",data["processes"],key="remove_process_select")
            remove_process=st.form_submit_button("Remove process")
        if remove_process:
            data["processes"].remove(process_to_remove)
            data["requirements"]=[r for r in data["requirements"] if r["process"]!=process_to_remove]
            data["assignments"]=[a for a in data["assignments"] if a["process"]!=process_to_remove]
            for employee in data["employees"]: employee["skills"]=[skill for skill in employee["skills"] if skill!=process_to_remove]
            if st.session_state.roster is not None: st.session_state.roster=[r for r in st.session_state.roster if r["process"]!=process_to_remove]
            st.warning(f"Removed {process_to_remove} and its lanes from this session.")
        st.markdown("#### Process directory")
        process_df=pd.DataFrame({"Process":data["processes"]})
        st.dataframe(process_df,hide_index=True,width="stretch")
        with st.form("add_process_form"):
            new_process_name=st.text_input("New process name",key="new_process_name")
            add_process=st.form_submit_button("Add process")
        if add_process:
            if not new_process_name.strip() or new_process_name.strip().casefold() in {p.casefold() for p in data["processes"]}:
                st.error("Enter a new, unique process name.")
            else:
                data["processes"].append(new_process_name.strip())
                st.success(f"Added process {new_process_name.strip()}. Add a coverage lane and employee assignments to use it.")
    with tabs[2]:
        st.markdown("#### Pods and pod leads")
        pod_rows=[{"Pod":pod,"Pod lead":data.get("pod_leads",{}).get(pod,"")} for pod in data["pods"]]
        pod_edit=st.data_editor(pd.DataFrame(pod_rows),hide_index=True,width="stretch",key="pod_lead_editor",
                                column_config={"Pod":st.column_config.TextColumn(disabled=True),"Pod lead":st.column_config.TextColumn(required=True)})
        for _,row in pod_edit.iterrows(): data.setdefault("pod_leads",{})[row["Pod"]]=str(row["Pod lead"]).strip()
        st.markdown("#### Working rules and soft preferences")
        st.caption("Employee weekly offs and shift limits are mandatory. Preferred days off are soft and may be overridden to keep coverage valid.")
        st.info("Assign schedules from the Employees tab. Operating calendars and lane staffing levels are edited under Brands & processes.")
        with st.form("rename_pod_form"):
            pod_to_rename=st.selectbox("Pod to rename",data["pods"],key="rename_pod_select")
            renamed_pod=st.text_input("New pod name",value=pod_to_rename,key="renamed_pod_name")
            rename_pod=st.form_submit_button("Rename pod")
        if rename_pod:
            if not renamed_pod.strip() or (renamed_pod.strip().casefold()!=pod_to_rename.casefold() and renamed_pod.strip().casefold() in {p.casefold() for p in data["pods"]}):
                st.error("Enter a unique pod name.")
            else:
                data["pods"]=[renamed_pod.strip() if pod==pod_to_rename else pod for pod in data["pods"]]
                for employee in data["employees"]:
                    if employee["pod"]==pod_to_rename: employee["pod"]=renamed_pod.strip()
                for brand in data["brands"]:
                    if brand["pod"]==pod_to_rename: brand["pod"]=renamed_pod.strip()
                lead=data.get("pod_leads",{}).pop(pod_to_rename,"")
                data["pod_leads"][renamed_pod.strip()]=lead
                st.success(f"Renamed pod to {renamed_pod.strip()}.")
        with st.form("add_pod_form"):
            st.markdown("##### Add a pod")
            new_pod_name=st.text_input("Pod name",key="new_pod_name")
            new_pod_lead=st.text_input("Pod lead",key="new_pod_lead")
            add_pod=st.form_submit_button("Add pod")
        if add_pod:
            if not new_pod_name.strip() or not new_pod_lead.strip() or new_pod_name.strip().casefold() in {p.casefold() for p in data["pods"]}:
                st.error("Enter a unique pod name and a lead.")
            else:
                data["pods"].append(new_pod_name.strip())
                data.setdefault("pod_leads",{})[new_pod_name.strip()]=new_pod_lead.strip()
                st.success(f"Added {new_pod_name.strip()} with lead {new_pod_lead.strip()}.")
    with tabs[3]:
        st.markdown("#### Planned leave, holidays & exceptions")
        if data["unavailability"] or data["planned_leave"] or data.get("comp_offs"):
            rows=[]
            for bucket,kind in (("planned_leave","Planned leave"),("unavailability","Unplanned unavailability"),("comp_offs","Comp-Off")):
                for item in data.get(bucket,[]):
                    emp=next((e for e in data["employees"] if e["id"]==item["employee_id"]),None)
                    if emp: rows.append({"Employee":emp["name"],"Date":item["date"],"Type":item.get("kind",kind)})
            st.dataframe(pd.DataFrame(rows),hide_index=True,width="stretch")
        else: st.info("No planned leave or ad-hoc unavailable dates are configured in the sample data.")
        with st.form("availability_form"):
            e_names={e["name"]:e["id"] for e in data["employees"]}
            leave_employee=st.selectbox("Employee leave",sorted(e_names))
            leave_date=st.date_input("Leave date",value=date.today(),key="planned_leave_date")
            availability_type=st.selectbox("Availability exception",["Planned leave","Comp-Off","Unplanned unavailability"],key="availability_type")
            add_holiday=st.checkbox("Also add a public holiday",value=False)
            holiday_date=st.date_input("Public holiday",value=date.today(),key="holiday_date")
            leave_submit=st.form_submit_button("Save availability dates")
        if leave_submit:
            bucket={"Planned leave":"planned_leave","Comp-Off":"comp_offs","Unplanned unavailability":"unavailability"}[availability_type]
            leave_item={"employee_id":e_names[leave_employee],"date":leave_date.isoformat(),"kind":availability_type}
            data.setdefault(bucket,[])
            if leave_item not in data[bucket]: data[bucket].append(leave_item)
            if add_holiday and holiday_date.isoformat() not in data["holidays"]: data["holidays"].append(holiday_date.isoformat())
            if st.session_state.roster is not None:
                st.session_state.roster_state="DRAFT"
                checks=validate_roster(data,st.session_state.roster)["issues"]
                affected=[issue for issue in checks if issue.get("date")==leave_date.isoformat()]
                st.success(f"Saved {availability_type.lower()}. The current roster was revalidated: {len(affected)} finding(s) on {leave_date.isoformat()}.")
                if affected: st.dataframe(pd.DataFrame(affected),hide_index=True,width="stretch")
            else: st.success(f"Saved {availability_type.lower()} for this session. Generate a roster to apply it.")
        st.caption("Public holidays are global dates; lane-level holiday operation and employee holiday eligibility are checked independently.")

else:
    st.markdown('<div class="hero"><div class="eyebrow">Validation center</div><h1>Find the gaps before they find you.</h1><p>Coverage is checked against requirements for every operating day. The app reports shortages instead of hiding them.</p></div>', unsafe_allow_html=True)
    if st.session_state.roster is None:
        st.info("Generate a roster first to see coverage validation.")
    else:
        result=validate_roster(data,st.session_state.roster)
        if not result["issues"]: st.success("No conflicts found. Configured process coverage is met for every scheduled operating day.")
        else:
            st.warning(f'{len(result["issues"])} coverage or scheduling issue(s) need attention.')
            issue_rows=[]
            for issue in classify_issues(result["issues"]):
                issue_rows.append({"Severity":issue["severity"],"Type":issue.get("type"),"Date":issue.get("date", issue.get("week", "")),
                                   "Brand":issue.get("brand", "—"),"Process":issue.get("process", "—"),
                                   "Required":issue.get("required", "—"),"Available":issue.get("available", issue.get("assigned", "—")),
                                   "Assigned":issue.get("assigned", "—"),"Shortage":issue.get("shortage", "—"),
                                   "Employee":issue.get("employee", issue.get("affected_employee", "—")),
                                   "Cause":issue.get("reason", issue.get("detail", "")),
                                   "Suggested resolution":", ".join(issue.get("backup_candidates", [])) or "Review staffing or eligibility"})
            st.dataframe(pd.DataFrame(issue_rows),hide_index=True,width="stretch")
        st.markdown("#### Recovery suggestions")
        if result["issues"]:
            for issue in result["issues"][:12]:
                if issue["type"]=="Coverage gap":
                    suggestions=issue.get("backup_candidates",[])
                    st.markdown(f'<div class="callout bad"><b>{issue["brand"]} · {issue["process"]} · {issue["date"]}</b><br>Required {issue["required"]}, assigned {issue["assigned"]}. '+("Available backup: "+", ".join(suggestions) if suggestions else "No eligible backup is currently available.")+"</div>",unsafe_allow_html=True)
        else: st.caption("When a coverage gap exists, eligible employees with matching skills, availability, and no conflicting assignment are suggested.")

save_workspace(
    {
        "workspace_data": st.session_state.workspace_data,
        "roster": st.session_state.roster,
        "roster_month": st.session_state.roster_month,
        "roster_history": st.session_state.roster_history,
        "change_history": st.session_state.change_history,
        "roster_state": st.session_state.roster_state,
        "undo_stack": st.session_state.undo_stack,
    }
)
