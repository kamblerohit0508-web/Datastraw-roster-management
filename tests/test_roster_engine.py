from copy import deepcopy
from datetime import date
import unittest

from roster_engine import build_roster, make_sample_data, validate_configuration, validate_roster


class RosterEngineTests(unittest.TestCase):
    def setUp(self):
        self.data = make_sample_data()

    def test_sample_data_matches_assessment_scale(self):
        self.assertEqual(len(self.data["employees"]), 30)
        self.assertEqual(len(self.data["brands"]), 9)
        self.assertEqual(len(self.data["processes"]), 5)
        self.assertEqual(len(self.data["pods"]), 4)
        brand_requirements = {brand["id"]: [req["required"] for req in self.data["requirements"] if req["brand_id"] == brand["id"]]
                              for brand in self.data["brands"]}
        self.assertEqual(sum(all(count == 1 for count in requirements) for requirements in brand_requirements.values()), 7)
        self.assertIn(2, [count for values in brand_requirements.values() for count in values])
        self.assertIn(3, [count for values in brand_requirements.values() for count in values])
        self.assertEqual(validate_configuration(self.data), [])

    def test_configuration_validation_catches_duplicate_and_invalid_rules(self):
        self.data["employees"].append(dict(self.data["employees"][0]))
        self.data["requirements"][0]["required"] = 0
        details = " ".join(issue["detail"] for issue in validate_configuration(self.data))
        self.assertIn("Duplicate employee ID", details)
        self.assertIn("must be at least one employee", details)

    def test_all_generation_modes_cover_sample_month_without_conflicts(self):
        for mode in ("Standard", "Balanced", "Smart"):
            with self.subTest(mode=mode):
                roster = build_roster(self.data, 2026, 11, mode)
                self.assertEqual(validate_roster(self.data, roster)["issues"], [])
                working = [row for row in roster if row["status"] == "Working"]
                self.assertTrue(working)

    def test_generator_respects_weekly_offs_leave_holidays_and_unavailability(self):
        employee_id = self.data["employees"][0]["id"]
        chosen_day = date(2026, 11, 3)  # Tuesday
        self.data["planned_leave"].append({"employee_id": employee_id, "date": chosen_day.isoformat(), "kind": "Leave"})
        self.data["holidays"].append(date(2026, 11, 4).isoformat())
        self.data["unavailability"].append({"employee_id": employee_id, "date": date(2026, 11, 5).isoformat(), "kind": "Unavailable"})
        roster = build_roster(self.data, 2026, 11)
        scheduled = {(row["employee_id"], row["date"]) for row in roster if row["status"] == "Working"}
        self.assertNotIn((employee_id, chosen_day.isoformat()), scheduled)
        holiday = date(2026, 11, 4).isoformat()
        requirements = {(req["brand_id"], req["process"]): req for req in self.data["requirements"]}
        employees = {employee["id"]: employee for employee in self.data["employees"]}
        for row in roster:
            if row["status"] == "Working" and row["date"] == holiday:
                self.assertTrue(requirements[(row["brand_id"], row["process"])]["operates_on_holidays"])
                self.assertTrue(employees[row["employee_id"]]["holiday_eligible"])
        self.assertNotIn((employee_id, date(2026, 11, 5).isoformat()), scheduled)
        self.assertEqual(validate_roster(self.data, roster)["issues"], [])

    def test_comp_off_is_honored_as_a_mandatory_day_off(self):
        employee_id = self.data["employees"][0]["id"]
        comp_off_date = date(2026, 11, 3).isoformat()
        self.data["comp_offs"].append({"employee_id": employee_id, "date": comp_off_date})
        roster = build_roster(self.data, 2026, 11)
        self.assertNotIn((employee_id, comp_off_date), {
            (row["employee_id"], row["date"]) for row in roster if row["status"] == "Working"
        })
        self.assertTrue(any(row["employee_id"] == employee_id and row["date"] == comp_off_date
                            and row["status"] == "Comp-Off" for row in roster))
        self.assertEqual(validate_roster(self.data, roster)["issues"], [])

    def test_validator_rejects_work_on_a_closed_lane_day(self):
        roster = build_roster(self.data, 2026, 11)
        row = next(row for row in roster if row["status"] == "Working")
        requirement = next(req for req in self.data["requirements"]
                           if req["brand_id"] == row["brand_id"] and req["process"] == row["process"])
        closed_day = next(day for day in range(7) if day not in requirement["operating_days"])
        row["date"] = next(date(2026, 11, day).isoformat() for day in range(1, 8)
                            if date(2026, 11, day).weekday() == closed_day)
        self.assertTrue(any(issue["type"] == "Outside operating calendar"
                            for issue in validate_roster(self.data, roster)["issues"]))

    def test_backup_suggestions_respect_weekly_shift_limits(self):
        roster = build_roster(self.data, 2026, 11)
        selected = next(row for row in roster if row["status"] == "Working")
        employee_id = selected["employee_id"]
        selected_week = date.fromisoformat(selected["date"]).isocalendar()[:2]
        self.data["unavailability"].append({"employee_id": employee_id, "date": selected["date"], "kind": "Unplanned"})
        issues = validate_roster(self.data, roster)["issues"]
        brand_name = next(brand["name"] for brand in self.data["brands"] if brand["id"] == selected["brand_id"])
        gap = next(issue for issue in issues if issue["type"] == "Coverage gap" and issue["date"] == selected["date"]
                   and issue["brand"] == brand_name and issue["process"] == selected["process"])
        counts = {}
        for row in roster:
            if row["status"] == "Working" and date.fromisoformat(row["date"]).isocalendar()[:2] == selected_week:
                counts[row["employee_id"]] = counts.get(row["employee_id"], 0) + 1
        eligible_names = {employee["name"]: employee for employee in self.data["employees"]}
        for name in gap["backup_candidates"]:
            employee = eligible_names[name]
            self.assertLess(counts.get(employee["id"], 0), employee["max_shifts_per_week"])

    def test_preferences_are_soft_and_reported_as_warnings(self):
        roster = build_roster(self.data, 2026, 11, "Standard")
        employee_id = self.data["employees"][0]["id"]
        work_row = next(row for row in roster if row["status"] == "Working"
                        and row["employee_id"] == employee_id)
        employee = next(item for item in self.data["employees"] if item["id"] == employee_id)
        employee["preferred_days_off"] = [date.fromisoformat(work_row["date"]).weekday()]
        result = validate_roster(self.data, roster)
        self.assertTrue(any(issue["type"] == "Preference warning" for issue in result["issues"]))
        self.assertFalse(any(issue["type"] == "Coverage gap" for issue in result["issues"]))

    def test_balanced_mode_avoids_preferred_day_off_when_staffing_allows(self):
        data = {
            "employees": [
                {"id": "E01", "name": "Preferred Staff", "pod": "Pod A", "skills": ["Support"],
                 "weekly_off": 6, "max_shifts_per_week": 7, "holiday_eligible": True, "preferred_days_off": [1]},
                {"id": "E02", "name": "Flexible Staff", "pod": "Pod A", "skills": ["Support"],
                 "weekly_off": 6, "max_shifts_per_week": 7, "holiday_eligible": True, "preferred_days_off": []},
            ],
            "brands": [{"id": "B01", "name": "Brand A", "pod": "Pod A"}],
            "processes": ["Support"], "pods": ["Pod A"],
            "requirements": [{"id": "R01", "brand_id": "B01", "process": "Support", "required": 1,
                              "operating_days": [1], "operates_on_holidays": False}],
            "assignments": [{"employee_id": "E01", "brand_id": "B01", "process": "Support"},
                            {"employee_id": "E02", "brand_id": "B01", "process": "Support"}],
            "unavailability": [], "planned_leave": [], "comp_offs": [], "holidays": [],
        }
        standard = build_roster(data, 2026, 11, "Standard")
        balanced = build_roster(data, 2026, 11, "Balanced")
        standard_tuesday = next(row for row in standard if row["status"] == "Working" and row["date"] == "2026-11-03")
        balanced_tuesday = next(row for row in balanced if row["status"] == "Working" and row["date"] == "2026-11-03")
        self.assertEqual(standard_tuesday["employee_id"], "E01")
        self.assertEqual(balanced_tuesday["employee_id"], "E02")

    def test_unavailable_employee_creates_visible_gap_and_backup(self):
        roster = build_roster(self.data, 2026, 11)
        data = deepcopy(self.data)
        working = next(row for row in roster if row["status"] == "Working")
        data["unavailability"].append({"employee_id": working["employee_id"], "date": working["date"], "kind": "Unplanned"})
        issues = validate_roster(data, roster)["issues"]
        gaps = [issue for issue in issues if issue["type"] == "Coverage gap" and issue["date"] == working["date"]
                and issue["brand"] == next(brand["name"] for brand in data["brands"] if brand["id"] == working["brand_id"])
                and issue["process"] == working["process"]]
        self.assertEqual(len(gaps), 1)
        self.assertTrue(gaps[0]["backup_candidates"])
        self.assertGreaterEqual(gaps[0]["available"], gaps[0]["assigned"] + len(gaps[0]["backup_candidates"]))
        self.assertTrue(gaps[0]["affected_employee"])

    def test_assigning_suggested_backup_restores_coverage(self):
        roster = build_roster(self.data, 2026, 11)
        data = deepcopy(self.data)
        selected = None
        for row in roster:
            if row["status"] != "Working":
                continue
            candidate_data = deepcopy(data)
            candidate_data["unavailability"].append({"employee_id": row["employee_id"], "date": row["date"], "kind": "Unplanned"})
            issues = validate_roster(candidate_data, roster)["issues"]
            brand_name = next(b["name"] for b in data["brands"] if b["id"] == row["brand_id"])
            gap = next((i for i in issues if i["type"] == "Coverage gap" and i["date"] == row["date"]
                        and i["brand"] == brand_name and i["process"] == row["process"] and i["backup_candidates"]), None)
            if gap:
                selected = (row, candidate_data, gap)
                break
        self.assertIsNotNone(selected, "Sample data should provide a replaceable assignment.")
        row, data, gap = selected
        unavailable_id = row["employee_id"]
        brand_id, process = row["brand_id"], row["process"]
        for existing in roster:
            if existing["date"] == row["date"] and existing["employee_id"] == unavailable_id and existing["status"] == "Working":
                existing.update({"status": "Unavailable", "brand_id": "", "process": ""})
        backup_id = next(e["id"] for e in data["employees"] if e["name"] == gap["backup_candidates"][0])
        backup_row = next(existing for existing in roster if existing["date"] == row["date"]
                          and existing["employee_id"] == backup_id and existing["status"] != "Working")
        backup_row.update({"brand_id": brand_id, "process": process, "status": "Working"})
        self.assertEqual(sum(existing["date"] == row["date"] and existing["employee_id"] == backup_id for existing in roster), 1)
        remaining = [i for i in validate_roster(data, roster)["issues"] if i.get("date") == row["date"]]
        self.assertFalse(any(i["type"] in {"Coverage gap", "Unavailable employee", "Employee overlap"} for i in remaining))

    def test_impossible_staffing_is_reported_with_no_false_coverage(self):
        roster = build_roster(self.data, 2026, 11)
        requirement = self.data["requirements"][0]
        requirement["required"] = 40
        result = validate_roster(self.data, roster)
        matching = [i for i in result["issues"] if i["type"] == "Coverage gap" and i["process"] == requirement["process"]]
        self.assertTrue(matching)
        self.assertTrue(all(i["assigned"] < i["required"] for i in matching))

    def test_validator_catches_manual_weekly_limit_breach(self):
        roster = build_roster(self.data, 2026, 11)
        work = [row for row in roster if row["status"] == "Working"]
        employee_id = work[0]["employee_id"]
        employee = next(e for e in self.data["employees"] if e["id"] == employee_id)
        employee["max_shifts_per_week"] = 1
        issues = validate_roster(self.data, roster)["issues"]
        self.assertTrue(any(issue["type"] == "Weekly shift limit" and issue["employee"] == employee["name"] for issue in issues))

    def test_manual_overlap_and_unauthorized_assignment_are_flagged(self):
        roster = build_roster(self.data, 2026, 11)
        first = next(row for row in roster if row["status"] == "Working")
        duplicate = dict(first)
        duplicate["process"] = self.data["processes"][-1]
        duplicate["brand_id"] = self.data["brands"][-1]["id"]
        roster.append(duplicate)
        types = {issue["type"] for issue in validate_roster(self.data, roster)["issues"]}
        self.assertIn("Employee overlap", types)
        self.assertIn("Unauthorized assignment", types)


if __name__ == "__main__":
    unittest.main()
