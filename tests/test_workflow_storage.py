import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import storage
from roster_engine import build_roster, make_sample_data, validate_roster
from roster_workflow import (
    can_publish, classify_issues, employee_month_grid, make_history_entry,
    set_roster_status, undo_roster_change,
)


class StorageTests(unittest.TestCase):
    def test_workspace_survives_close_and_reopen(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(storage, "DB_PATH", Path(folder) / "roster.sqlite3"):
                payload = {"workspace_data": make_sample_data(), "roster": [{"date": "2026-11-02"}]}
                storage.save_workspace(payload)
                loaded = storage.load_workspace()
                self.assertEqual(loaded, payload)
                self.assertEqual(storage.load_workspace(), payload)

    def test_employee_and_availability_edits_persist(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(storage, "DB_PATH", Path(folder) / "roster.sqlite3"):
                data = make_sample_data()
                data["employees"][0]["name"] = "Updated Employee"
                data["planned_leave"].append({"employee_id": "E01", "date": "2026-11-14", "kind": "Leave"})
                storage.save_workspace({"workspace_data": data})
                restored = storage.load_workspace()["workspace_data"]
                self.assertEqual(restored["employees"][0]["name"], "Updated Employee")
                self.assertEqual(restored["planned_leave"][0]["date"], "2026-11-14")


class RosterWorkflowTests(unittest.TestCase):
    def test_manual_change_validates_and_can_be_undone(self):
        data = make_sample_data()
        roster = build_roster(data, 2026, 11)
        working = next(row for row in roster if row["status"] == "Working")
        stack = []
        before = set_roster_status(roster, working["employee_id"], working["date"], "OFF")
        stack.append(before)
        self.assertTrue(validate_roster(data, roster)["issues"])
        restored = undo_roster_change(stack)
        roster[:] = restored
        self.assertEqual(validate_roster(data, roster)["issues"], [])

    def test_manual_work_on_leave_is_blocked_from_publish(self):
        data = make_sample_data()
        roster = build_roster(data, 2026, 11)
        row = next(item for item in roster if item["status"] == "Working")
        data["planned_leave"].append({"employee_id": row["employee_id"], "date": row["date"], "kind": "Leave"})
        set_roster_status(roster, row["employee_id"], row["date"], "Working", row["brand_id"], row["process"])
        issues = validate_roster(data, roster)["issues"]
        self.assertTrue(any(issue["type"] == "Unavailable employee" for issue in issues))
        self.assertFalse(can_publish(issues))

    def test_history_versioning_severity_and_month_grid(self):
        data = make_sample_data()
        roster = build_roster(data, 2026, 11)
        first = make_history_entry([], roster, "November 2026", "DRAFT", "scheduler", "Generated", 100)
        history = [first]
        next_entry = make_history_entry(history, roster, "November 2026", "REVIEW", "user", "Validated", 100)
        self.assertEqual((history[0]["version"], next_entry["version"]), (1, 2))
        issues = classify_issues([{"type": "Coverage gap"}, {"type": "Preference warning"}])
        self.assertEqual([item["severity"] for item in issues], ["CRITICAL", "WARNING"])
        self.assertFalse(can_publish([{"type": "Coverage gap"}]))
        self.assertTrue(can_publish([{"type": "Preference warning"}]))
        grid = employee_month_grid(data, roster, 2026, 11, issues=[])
        self.assertEqual(len(grid), 30)
        self.assertIn("Nov 1", grid[0])


if __name__ == "__main__":
    unittest.main()
