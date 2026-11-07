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
| Manual roster editing | PARTIAL | Manual assignee replacement and backup assignment revalidate the roster | Add direct day/status editing and undo for manual overrides. |
| Availability changes after generation | PASS | Browser demo: marked Meera Kapoor unavailable on 2027-03-01; app showed the 1/2 gap and Kiara Mehta as backup; Conflicts then showed no conflicts after assignment | Improve before/after messaging and show the exact resolved coverage count after every action. |
| Company/pod/brand/process/employee roster views | PASS | Roster tabs in `app.py` | Add a compact employee-by-day grid; current views are tabular. |
| Sample data complexity | PASS | 9 brands, 21 lanes, seven single-person minimum brands, one two-person lane, one three-person lane, shared cross-trained reserve pool | Tune synthetic staffing ratios to match any clarified client scenario. |
| Export | PASS | Company roster CSV download | Excel/PDF export is optional and not implemented. |
| Professional operations UI | PARTIAL | Neutral dashboard, blue primary accent, coverage heatmap, conflict/recovery views | Improve desktop density, smaller-screen layout, keyboard accessibility, and status color legend. |
| Generation progress | PARTIAL | Honest Streamlit spinner during the quick deterministic calculation | No staged progress is shown because the calculation is effectively instantaneous. |
| Persistent storage and deployment | PARTIAL | No hardcoded local data path or secret is required; `requirements.txt` is pinned | Session data disappears on restart; add an external persistent database, auth, authorization, migrations, and deployment configuration. |
| AI scheduling | PARTIAL | No AI is used; core scheduling is deterministic | AI explanations are optional and should only be added after core persistence and audit features. |
| README and assessment answers | PASS | `README.md` covers overview, model, algorithm, validation, setup, limits, and all eight questions | Add screenshot and live deployment/repository links when available. |
| End-to-end demo | PASS | Browser opened dashboard, generated March 2027, showed heatmap, recorded unavailability, showed gap/backup, and validated recovery | Run the same walkthrough once on the final presentation-sized desktop viewport. |

## Release assessment

**Assessment readiness: NEEDS WORK for production use; core assessment demo is functional.** The schedule engine and recovery flow are covered by 13 passing tests and the March 2027 browser walkthrough. The main submission and operational gaps are persistent storage, authentication, publish/approval controls, audit/undo, a public deployment, repository publication, and a recorded walkthrough. The data currently consists only of fictional sample records.

## Verification performed

- `python -m unittest discover -s tests -v`: 14 tests passed under the project's Python 3.13 x64 virtual environment.
- Parsed `app.py`, `roster_engine.py`, and the test module with Python's AST parser.
- Opened the app at `http://127.0.0.1:8502`, generated the March 2027 roster, confirmed zero starting coverage gaps, and exercised the unavailable employee → backup → revalidation path.
- Checked that employee, brand/process, and pod management screens render in the browser.
