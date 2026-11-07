"""Small, deterministic helpers for roster lifecycle and employee calendars."""

from copy import deepcopy
import calendar
from datetime import date, datetime


def classify_issues(issues):
    classified = []
    for issue in issues:
        item = dict(issue)
        item["severity"] = "WARNING" if item.get("type") == "Preference warning" else "CRITICAL"
        classified.append(item)
    return classified


def can_publish(issues):
    return not any(issue.get("type") != "Preference warning" for issue in issues)


def employee_month_grid(data, roster, year, month, issues=()):
    """Build a rectangular employee-by-day calendar suitable for a DataFrame."""
    days = [date(year, month, day) for day in range(1, calendar.monthrange(year, month)[1] + 1)]
    by_employee_day = {(row["employee_id"], row["date"]): row for row in roster}
    employee_by_name = {employee["name"]: employee["id"] for employee in data["employees"]}
    affected = set()
    for issue in issues:
        day_key = issue.get("date")
        employee_id = issue.get("employee_id") or employee_by_name.get(issue.get("employee"))
        if employee_id and day_key:
            affected.add((employee_id, day_key))
        if issue.get("type") == "Coverage gap" and day_key:
            brand = next((item for item in data["brands"] if item["name"] == issue.get("brand")), {})
            for row in roster:
                if row.get("date") == day_key and row.get("brand_id") == brand.get("id") and row.get("process") == issue.get("process"):
                    affected.add((row["employee_id"], day_key))
    labels = {
        "Working": "WORK", "Weekly Off": "OFF", "Leave": "LEAVE",
        "Holiday": "HOLIDAY", "Comp-Off": "COMP-OFF",
        "Unavailable": "UNAVAILABLE", "Available": "OFF",
    }
    result = []
    for employee in data["employees"]:
        item = {"Employee": employee["name"], "ID": employee["id"], "Pod": employee["pod"]}
        for day in days:
            key = (employee["id"], day.isoformat())
            row = by_employee_day.get(key)
            status = labels.get(row["status"], row["status"].upper() if row else "—") if row else "—"
            if key in affected:
                status = "CONFLICT"
            item[f"{day.strftime('%b')} {day.day}"] = status
        result.append(item)
    return result


def make_history_entry(history, roster, month_label, status, source, summary, coverage):
    version = max((item.get("version", 0) for item in history), default=0) + 1
    return {
        "version": version, "month": month_label, "status": status,
        "source": source, "summary": summary, "coverage": coverage,
        "assignments": sum(row.get("status") == "Working" for row in roster),
        "created_at": datetime.now().isoformat(timespec="minutes"),
    }


def set_roster_status(roster, employee_id, day_key, status, brand_id="", process=""):
    """Update one employee/day row, returning the prior snapshot for undo."""
    before = deepcopy(roster)
    row = next((item for item in roster if item["employee_id"] == employee_id and item["date"] == day_key), None)
    if row is None:
        row = {"date": day_key, "employee_id": employee_id, "brand_id": "", "process": "", "status": "Available"}
        roster.append(row)
    row.update({"status": status, "brand_id": brand_id if status == "Working" else "",
                "process": process if status == "Working" else ""})
    return before


def undo_roster_change(change_stack):
    if not change_stack:
        return None
    return change_stack.pop()
