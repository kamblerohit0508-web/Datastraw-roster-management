# RosterFlow — Smart Roster Management System

RosterFlow is a workforce planning assessment prototype for Datastraw Technologies. It models employees, pods, brands, processes, lane-specific coverage rules, and monthly availability, then generates and validates a roster.

## Problem

Operations teams need to meet different coverage targets across brands and processes while respecting employee assignments, weekly offs, leave, comp-offs, holidays, and workload limits. This app makes those constraints visible, reports impossible coverage, and lets an operations manager respond when availability changes.

## Features

- 30 fictional employees, 9 fictional brands, 5 processes, and 4 pods with pod leads. Seven brands use single-person minimum lanes; two brands demonstrate two- and three-person staffing.
- Employee directory editing plus add/remove actions; employee-to-brand/process eligibility can be edited without changing source code.
- Brand and process lanes with independent headcount, operating weekdays, and public-holiday behavior.
- Weekly offs, max shifts per ISO week, preferred days off, planned leave, comp-offs, ad-hoc unavailability, and public holidays.
- Standard, Balanced, and Smart deterministic roster modes.
- Company, pod, brand, process, and employee roster views, plus brand/day coverage heatmap and CSV export.
- Validation for duplicate/invalid configuration, employee overlaps, weekly caps, unavailable people, unauthorized assignments, assignments on closed lanes, and coverage gaps.
- Change workflow that records an employee as unavailable, revalidates the existing roster, recommends eligible backups, and revalidates after reassignment.
- Manual assignee adjustment with availability, lane eligibility, daily overlap, holiday, and weekly-cap checks.

## Architecture

| Area | Implementation |
|---|---|
| UI | Streamlit in `app.py` |
| Sample operating model | `make_sample_data()` in `roster_engine.py` |
| Scheduling and validation | Pure Python functions in `roster_engine.py` |
| Session state | Streamlit Session State; edits are held for the current session only |
| Tests | `unittest` cases in `tests/test_roster_engine.py` |
| Dependencies | `requirements.txt` |

There is no database, login system, API key, or external service in this prototype. No information is persisted after the session or process ends.

## Data model

- **Employee:** ID, name, home pod, process skills, repeating weekly off, max shifts per week, holiday-work eligibility, and optional preferred days off.
- **Pod:** name and lead. Employees and brands have a pod relationship.
- **Brand:** ID, name, and owning pod.
- **Process:** a reusable operational work type such as Customer Support or Non-Delivery Reports.
- **Employee assignment:** the employee is eligible for a specific brand/process lane. An employee can be eligible for more than one lane.
- **Coverage requirement:** one brand/process lane, required headcount, operating weekdays, and holiday operation flag.
- **Availability:** planned leave, comp-off, dated unavailability, and global public holidays.
- **Roster row:** date, employee, lane, and status. Working rows are validated against the model; non-working rows make the employee calendar reviewable.

## Scheduling and validation

The scheduler walks the month one day at a time, expands each active lane into staffing slots, and uses deterministic augmenting-path matching. Matching can move a flexible person to another slot to preserve a scarce specialist for a lane with fewer eligible employees. Each person receives at most one assignment per day.

Mandatory rules are applied before preferences: lane eligibility, operating calendar, weekly off, leave, comp-off, unavailability, holiday eligibility, daily uniqueness, and weekly shift cap. Standard mode follows stable ordering. Balanced mode favors eligible employees with lower monthly and weekly loads while considering preferred days off. Smart mode orders lanes by candidate scarcity and then balances eligible staff. Preferences are soft and never make an invalid schedule valid.

The validator independently checks the roster. Invalid rows do not count toward coverage. A coverage gap includes its date, lane, required headcount, assigned headcount, shortage, cause summary, and available backup candidates. A roster can be generated with gaps; the app calls those out rather than inventing staffing.

## Conflict handling

The assessment demo starts with a valid monthly roster. Mark a scheduled employee unavailable on a working date. The existing row becomes invalid, the coverage display falls (for example, 1/2), and the validation center reports the coverage gap. The app suggests a person already eligible for that lane who is available, not already assigned that day, and still within the weekly limit. Assigning that backup triggers validation again.

## AI usage

No AI service is used. Roster correctness, eligibility, validation, and backup selection are deterministic. A future version could use AI to explain a conflict in plain language, but any such explanation would remain advisory.

## Setup

On this Windows ARM computer, use the installed Python 3.13 x64 runtime. Python 3.15 ARM64 currently has no compatible PyArrow wheel for this Streamlit setup.

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe" -m venv .venv-x64
& ".\.venv-x64\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv-x64\Scripts\python.exe" -m streamlit run app.py
```

Open the local URL printed by Streamlit (normally `http://localhost:8501`). To run the engine tests:

```powershell
& ".\.venv-x64\Scripts\python.exe" -m unittest discover -s tests -v
```

The app does not read environment variables. `.env.example` documents that no keys are required; do not add secrets to the repository.

## Deployment notes

The app can be packaged as a Streamlit application with `app.py` as its entry point and `requirements.txt` for dependencies. It does not hardcode a local file path or require a localhost URL to run after deployment. However, this version is **not production-ready**: it has no persistent database, user authentication, access control, audit log, approval/publish process, or backup/restore. Session State is temporary and must be replaced with persistent storage before operational use. No repository or deployment configuration is included yet.

## Assessment questions

1. **How are employees, brands, processes, pods, and relationships modelled?** As separate records connected by employee-to-brand/process eligibility assignments. Brands and employees each belong to a pod; each pod has a lead.
2. **How does the system generate a roster and determine whether it satisfies constraints?** It expands each operating lane into daily slots, uses deterministic augmenting-path matching, then runs a separate validator over every working row and coverage requirement.
3. **How are single-resource and multi-resource brands handled?** Every lane has a headcount requirement. A one-person lane receives one distinct employee; multi-person lanes receive the requested number of distinct eligible people. Additional eligible staff can serve as backups.
4. **What happens when the only employee for a brand is unavailable?** The row is flagged, coverage falls below the requirement, and no backup is suggested if no other eligible employee exists. The gap remains visible for an operations decision.
5. **How are conflicting requirements or insufficient staffing handled?** Overlaps and constraint violations are invalidated for coverage counting; any remaining shortage is shown with its affected lane, date, reason, and feasible backups where available.
6. **Which parts are automated and which remain human-controlled? Why?** Generation, hard-constraint validation, coverage reporting, and backup eligibility are automated. An operations manager chooses whether to change an assignment or accept an unresolved gap; the app does not silently invent staff.
7. **What would change if the company doubled in size?** Keep the domain model and validation contracts, move session data to a persistent database, add indexed queries and role-based access, and benchmark the scheduler before introducing a solver.
8. **What would improve with one more week?** Persistent database-backed CRUD, richer shift/time-window and rest rules, undoable overrides, approval/publish workflow, fairness metrics, accessibility/responsive polish, and a broader end-to-end test suite.

## Limitations and future work

- Changes live in the current Streamlit session and are lost on restart.
- A shift is one daily lane assignment; start/end time, minimum rest, split shifts, and hour totals are not modelled.
- Weekly offs repeat on one weekday; the cap uses ISO weeks.
- Employee CRUD and brand/process lane management are present, but pod removal, process renaming, and full audit history are not.
- The manual editor changes an assignee on an existing lane; it is not a full spreadsheet cell editor.
- Export is CSV only. No screenshots, sample credentials, live URL, public repository, or demo recording are included.
- All directory data is synthetic and should not be represented as Datastraw employee or client data.

See [ASSESSMENT_AUDIT.md](ASSESSMENT_AUDIT.md) for requirement-by-requirement status and evidence.
