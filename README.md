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
| Persistence | SQLite JSON snapshot in `data/rosterflow.db`, loaded at startup and saved after each Streamlit run |
| Workflow helpers | Lifecycle, employee calendar, conflict severity, and change helpers in `roster_workflow.py` |
| Session state | Streamlit Session State for active UI values; durable app data is saved in SQLite |
| Tests | `unittest` cases in `tests/` |
| Dependencies | `requirements.txt` |

No login system, API key, or external service is required. SQLite is appropriate for local assessment use. The local database is excluded from Git. For public deployment, use persistent storage supported by the host or migrate to a managed database; a local SQLite file on ephemeral hosting is not durable.

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

The assessment demo starts with a valid monthly roster. Mark a scheduled employee unavailable on a working date. The existing row becomes invalid, coverage falls below the requirement, and the validation center reports the gap with severity, cause, headcount, and backup candidates. Assigning a backup triggers validation again.

## Roster workflow, editing, and history

Generated rosters start as **DRAFT**. The user can validate and move a roster to **REVIEW**. Publishing is enabled only from Review and only when mandatory validation conflicts are resolved; soft preference warnings do not block it. Generation, review, publication, and direct schedule edits create dated history entries with a version number, source, summary, status, and coverage percentage.

The roster page includes an employee-by-day monthly grid with WORK, OFF, LEAVE, HOLIDAY, COMP-OFF, UNAVAILABLE, and CONFLICT labels. Direct employee/day status edits revalidate immediately and return the roster to Draft. The latest direct schedule edit can be undone; the restored roster is validated again. Existing assignee adjustment and backup recovery controls remain available.

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

Start the app with `python -m streamlit run app.py`; install dependencies from `requirements.txt`. No API keys or environment variables are required for the assessment prototype. SQLite stores state in `data/rosterflow.db`, and `.gitignore` excludes the database directory and `*.db` files. For a host with an ephemeral filesystem, configure a persistent volume or replace local SQLite with a managed database before relying on saved state. The app has no authentication or role-based access, so use fictional assessment data for a public demo and do not treat this prototype as a production workforce system.

### Demo workflow

1. Open Overview and verify the sample counts.
2. Select a month in Roster and generate a roster.
3. Review the Monthly employee grid and coverage views.
4. Use the recovery controls to mark an employee unavailable, inspect the gap and backup suggestions, assign a backup, and revalidate.
5. Make a direct employee/day change; inspect the validation result and undo it.
6. Restart Streamlit and confirm the saved workspace and roster are restored.
7. Validate and move the roster to Review, then publish it after mandatory conflicts are resolved. Inspect version history.

## Assessment questions

1. **How are employees, brands, processes, pods, and relationships modelled?** As separate records connected by employee-to-brand/process eligibility assignments. Brands and employees each belong to a pod; each pod has a lead.
2. **How does the system generate a roster and determine whether it satisfies constraints?** It expands each operating lane into daily slots, uses deterministic augmenting-path matching, then runs a separate validator over every working row and coverage requirement.
3. **How are single-resource and multi-resource brands handled?** Every lane has a headcount requirement. A one-person lane receives one distinct employee; multi-person lanes receive the requested number of distinct eligible people. Additional eligible staff can serve as backups.
4. **What happens when the only employee for a brand is unavailable?** The row is flagged, coverage falls below the requirement, and no backup is suggested if no other eligible employee exists. The gap remains visible for an operations decision.
5. **How are conflicting requirements or insufficient staffing handled?** Overlaps and constraint violations are invalidated for coverage counting; any remaining shortage is shown with its affected lane, date, reason, and feasible backups where available.
6. **Which parts are automated and which remain human-controlled? Why?** Generation, hard-constraint validation, coverage reporting, and backup eligibility are automated. An operations manager chooses whether to change an assignment or accept an unresolved gap; the app does not silently invent staff.
7. **What would change if the company doubled in size?** Keep the domain model and validation contracts, move session data to a persistent database, add indexed queries and role-based access, and benchmark the scheduler before introducing a solver.
8. **What would improve with one more week?** Replace the local snapshot with deployment-backed storage, add authentication and access control, provide complete audit/restore controls, support time-window and rest rules, and run a hosted end-to-end walkthrough.

## Limitations and future work

- SQLite persistence is a single local JSON snapshot and is suitable for the local assessment prototype, not concurrent production use.
- A shift is one daily lane assignment; start/end time, minimum rest, split shifts, and hour totals are not modelled.
- Weekly offs repeat on one weekday; the cap uses ISO weeks.
- Pod removal, process renaming, and complete audit/restore history are not implemented.
- Direct schedule edits support daily statuses and validation; they do not model shift times, split shifts, or working hours.
- Export is CSV only. Deployment has not been configured or verified in this repository.
- All directory data is synthetic and should not be represented as Datastraw employee or client data.

See [ASSESSMENT_AUDIT.md](ASSESSMENT_AUDIT.md) for requirement-by-requirement status and evidence.
