# Datastraw assessment audit

Audit performed against the pasted assessment brief and the project currently in this folder. Status reflects implemented and observed behavior, not planned features.

| Requirement | Status | Evidence / location | Remaining work |
|---|---|---|---|
| Framework and architecture identified | PASS | Streamlit UI in `app.py`; scheduling and validation in `roster_engine.py`; tests in `tests/test_roster_engine.py` | Split the UI into smaller modules if the prototype grows. |
| 30+ employees, multiple brands/processes/pods | PASS | `make_sample_data()` creates 30 employees, 9 fictional brands, 5 processes, 4 pods; seven brands use single-person minimum lanes and two demonstrate larger crews | Replace fictional records with approved operational data before real use. |
| Pod leads | PASS | Sample `pod_leads`; editable pod lead table in People & operations | Support deleting pods after reassignment. |
| Employee directory and CRUD | PASS | Employee editor plus add/remove forms in `app.py` | Add audit history and restore/undo for removals. |
| Brand management | PASS | Brand directory editor plus add/remove forms | Add undo and deletion safeguards. |
| Process management | PARTIAL | Add/remove process and lane configuration in `app.py` | Add process rename and preserve audit history. |
| Employee to brand/process assignments | PASS | Editable relationship table; lane team selection when adding a lane | Add clearer assignment validation feedback before roster generation. |
| Weekly offs and shift limits | PASS | Generator and validator in `roster_engine.py`; employee editor | Add rest-period, hours, and rotating-week rules. |
| Planned leave, comp-offs, unavailability | PASS | Availability form in `app.py`; `_unavailable()` and Comp-Off rows in `roster_engine.py` | Add approval states and range-based leave entry. |
| Public holidays and lane-specific calendars | PASS | Global holiday dates plus per-lane weekdays/holiday operation | Add a country/region holiday calendar import. |
| Preferences vs mandatory constraints | PASS | Preferred days off are a soft scheduler input; validator reports preference warnings | Add preference weights and explain trade-offs in the UI. |
| Monthly roster generation | PASS | Standard, Balanced, and Smart modes in `build_roster()` | Add comparison/undo for alternate generated rosters. |
| Scheduling correctness and impossible coverage | PASS | Deterministic augmenting-path matcher; 13 unit tests include impossible staffing and constraint cases | Validate larger and more varied real-world rule sets. |
| Conflict detection and coverage validation | PASS | `validate_roster()` checks overlaps, weekly caps, availability, eligibility, operating days, and coverage | Add issue severity and richer cause details for every conflict type. |
| Manual roster editing | PASS | Assignee replacement plus direct employee/day status edits revalidate immediately; latest direct status change can be undone | Status changes are daily; shift hours and time windows are not modelled. |
| Availability changes after generation | PASS | Browser demo: marked Meera Kapoor unavailable on 2027-03-01; app showed the 1/2 gap and Kiara Mehta as backup; Conflicts then showed no conflicts after assignment | Improve before/after messaging and show the exact resolved coverage count after every action. |
| Company/pod/brand/process/employee roster views | PASS | Existing views remain; monthly employee-by-day grid added to roster screen | Wide months require horizontal scrolling in the data grid. |
| Sample data complexity | PASS | 9 brands, 21 lanes, seven single-person minimum brands, one two-person lane, one three-person lane, shared cross-trained reserve pool | Tune synthetic staffing ratios to match any clarified client scenario. |
| Export | PASS | Company roster CSV download | Excel/PDF export is optional and not implemented. |
| Professional operations UI | PARTIAL | Neutral dashboard, blue primary accent, coverage heatmap, conflict/recovery views | Improve desktop density, smaller-screen layout, keyboard accessibility, and status color legend. |
| Generation progress | PARTIAL | Honest Streamlit spinner during the quick deterministic calculation | No staged progress is shown because the calculation is effectively instantaneous. |
| Persistent storage and deployment | PARTIAL | SQLite workspace snapshot; connection closes cleanly; tests reload it in a separate process; separate Streamlit process on port 8504 loaded the saved roster, 30 employees, 100% coverage, version history, and change history | Local SQLite is not suitable for ephemeral or concurrent production deployment. Add hosted persistence, auth, migrations, and deployment configuration. |
| Draft/review/publish workflow | PASS | Roster screen shows DRAFT/REVIEW/PUBLISHED, validates before review, and disables publishing while mandatory conflicts remain | No separate reviewer identity or approval record. |
| Roster history/versioning | PASS | History entries record version, timestamp, month, state, source, summary, coverage, and assignment count; stored in SQLite | History is metadata snapshots, not a full diff of every roster row. |
| Conflict severity/details | PASS | Validation screen displays severity, date/week, brand/process, required/available/assigned/shortage, employee, cause, and backup/resolution text | Severity mapping is rule-based; richer per-rule severity configuration is not available. |
| AI scheduling | PARTIAL | No AI is used; core scheduling is deterministic | AI explanations are optional and should only be added after core persistence and audit features. |
| README and assessment answers | PASS | `README.md` covers overview, model, algorithm, validation, setup, limits, and all eight questions | Add screenshot and live deployment/repository links when available. |
| End-to-end demo | PASS | Browser opened dashboard, generated March 2027, showed heatmap, recorded unavailability, showed gap/backup, and validated recovery | Run the same walkthrough once on the final presentation-sized desktop viewport. |

## Release assessment

**Assessment readiness: core assessment workflow is functional; production deployment still needs work.** The scheduler and recovery flow remain covered by the engine suite. SQLite persistence, draft/review/publish, version history, daily status editing/undo, conflict details, and a monthly employee grid are implemented. Persistence was checked with tests and a separate Streamlit process restart. Authentication, concurrent-user storage, deployment configuration, full roster-diff history, and a recorded walkthrough remain outstanding. Data is fictional sample data.

## Verification performed

- `.venv-x64\Scripts\python.exe -m unittest discover -s tests -v`: 19 tests passed after these changes.
- Parsed changed Python modules with Python's AST parser.
- In the running app at `http://127.0.0.1:8502`, generated a November 2026 roster, confirmed zero coverage gaps, opened the employee-by-day grid, moved the roster from Draft to Review to Published, applied a daily status change, observed the validation message, and used Undo.
- Restarted the app in a separate Streamlit process on port 8504 and confirmed it loaded the saved roster, 30 employees, 100% coverage, and saved history entries. The separate Python process also confirmed the saved DRAFT state after the manual edit was undone.
- Existing unavailable employee → backup → revalidation behavior remains covered by engine tests and prior browser walkthrough.
- Checked that employee, brand/process, and pod management screens render in the browser.
