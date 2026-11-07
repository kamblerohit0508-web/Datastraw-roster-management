"""Deterministic roster generation and validation for the assessment prototype."""

from collections import Counter, defaultdict
from datetime import date, timedelta


PROCESS_NAMES = ["Customer Support", "Abandoned Cart Conversion", "Non-Delivery Reports", "Retention", "Order Operations"]
PODS = ["Pod North", "Pod South", "Pod East", "Pod West"]
BRAND_NAMES = ["Aster & Oak", "Beacon Outfitters", "Cedar Lane", "Dune & Coast", "Everline Market",
               "Fable House", "Grove Goods", "Harbor & Hearth", "Indigo Market"]


def make_sample_data():
    employees = []
    for i in range(30):
        employees.append({
            "id": f"E{i+1:02d}",
            "name": ["Aarav", "Diya", "Kabir", "Meera", "Ishaan", "Anaya", "Arjun", "Sara", "Dev", "Kiara"][i % 10] + f" " + ["Shah", "Rao", "Nair", "Kapoor", "Iyer", "Mehta"][i % 6],
            "pod": PODS[i % 4],
            "skills": [],
            "weekly_off": i % 7,
            "max_shifts_per_week": 6,
            "holiday_eligible": i % 3 == 0 or i >= 24,
            "preferred_days_off": [],
        })

    brands = [{"id": f"B{i+1:02d}", "name": BRAND_NAMES[i], "pod": PODS[i % 4]} for i in range(len(BRAND_NAMES))]
    requirements, assignments = [], []
    core_employee_index = 0
    backup_pool = employees[24:]
    for bi, brand in enumerate(brands):
        process_count = 2 if bi < 6 else 3
        for pi in range(process_count):
            process = PROCESS_NAMES[(bi + pi) % len(PROCESS_NAMES)]
            req_id = f"R{len(requirements)+1:02d}"
            # Seven brands use single-person minimum lanes; two busy brands need larger crews.
            required = 2 if (bi, pi) == (4, 1) else 3 if (bi, pi) == (7, 0) else 1
            operating_days = [0, 1, 2, 3, 4, 5] if (bi + pi) % 4 == 0 else [0, 1, 2, 3, 4]
            requirements.append({"id": req_id, "brand_id": brand["id"], "process": process,
                                 "required": required, "operating_days": operating_days,
                                 "operates_on_holidays": (bi + pi) % 5 == 0})
            # Give each lane a dedicated core team, then rotate the shared backup pool.
            lane_staff = employees[core_employee_index:core_employee_index + required]
            core_employee_index += required
            lane_staff += backup_pool
            for employee in lane_staff:
                if process not in employee["skills"]:
                    employee["skills"].append(process)
                assignments.append({"employee_id": employee["id"], "brand_id": brand["id"], "process": process})

    # Add a public holiday in the sample month only when it falls within that month.
    return {
        "employees": employees,
        "brands": brands,
        "processes": PROCESS_NAMES,
        "pods": PODS,
        "requirements": requirements,
        "assignments": assignments,
        "unavailability": [],
        "holidays": [],
        "planned_leave": [],
        "comp_offs": [],
        "pod_leads": {pod: f"{pod} Lead" for pod in PODS},
        "manual_overrides": [],
    }


def _days(year, month):
    last = (date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)).day
    return [date(year, month, day) for day in range(1, last + 1)]


def _employee_by_id(data):
    return {e["id"]: e for e in data["employees"]}


def _brand_by_id(data):
    return {b["id"]: b for b in data["brands"]}


def validate_configuration(data):
    """Return configuration problems before scheduling or accepting edited data."""
    problems = []

    def duplicates(values):
        seen, repeated = set(), set()
        for value in values:
            key = str(value).strip().casefold()
            if key in seen:
                repeated.add(str(value))
            seen.add(key)
        return sorted(repeated)

    for label, values in (("employee ID", [e.get("id", "") for e in data["employees"]]),
                          ("employee name", [e.get("name", "") for e in data["employees"]]),
                          ("brand ID", [b.get("id", "") for b in data["brands"]]),
                          ("brand name", [b.get("name", "") for b in data["brands"]]),
                          ("process name", data["processes"]), ("pod name", data["pods"])):
        for value in duplicates(values):
            problems.append({"type": "Invalid configuration", "detail": f"Duplicate {label}: {value}."})

    employee_ids = {e["id"] for e in data["employees"]}
    brand_ids = {b["id"] for b in data["brands"]}
    process_names = set(data["processes"])
    for employee in data["employees"]:
        if employee.get("pod") not in data["pods"]:
            problems.append({"type": "Invalid configuration", "detail": f"{employee.get('name', employee.get('id'))} references an unknown pod."})
        if not isinstance(employee.get("weekly_off"), int) or employee["weekly_off"] not in range(7):
            problems.append({"type": "Invalid configuration", "detail": f"{employee.get('name', employee.get('id'))} has an invalid weekly off."})
        if not isinstance(employee.get("max_shifts_per_week"), int) or employee["max_shifts_per_week"] < 1:
            problems.append({"type": "Invalid configuration", "detail": f"{employee.get('name', employee.get('id'))} must have a positive weekly shift limit."})
        if any(not isinstance(day, int) or day not in range(7) for day in employee.get("preferred_days_off", [])):
            problems.append({"type": "Invalid configuration", "detail": f"{employee.get('name', employee.get('id'))} has an invalid preferred day off."})
    for brand in data["brands"]:
        if brand.get("pod") not in data["pods"]:
            problems.append({"type": "Invalid configuration", "detail": f"{brand.get('name', brand.get('id'))} references an unknown pod."})
    for pod in data["pods"]:
        if not data.get("pod_leads", {}).get(pod, "").strip():
            problems.append({"type": "Invalid configuration", "detail": f"{pod} needs a pod lead."})
    lanes = set()
    for requirement in data["requirements"]:
        lane = (requirement.get("brand_id"), requirement.get("process"))
        if lane in lanes:
            problems.append({"type": "Invalid configuration", "detail": f"Duplicate coverage lane: {lane[0]} / {lane[1]}."})
        lanes.add(lane)
        if lane[0] not in brand_ids or lane[1] not in process_names:
            problems.append({"type": "Invalid configuration", "detail": f"Coverage lane references an unknown brand or process: {lane[0]} / {lane[1]}."})
        if not isinstance(requirement.get("required"), int) or requirement["required"] < 1:
            problems.append({"type": "Invalid configuration", "detail": f"Coverage for {lane[0]} / {lane[1]} must be at least one employee."})
        days = requirement.get("operating_days", [])
        if not days or len(set(days)) != len(days) or any(not isinstance(day, int) or day not in range(7) for day in days):
            problems.append({"type": "Invalid configuration", "detail": f"Operating days are invalid for {lane[0]} / {lane[1]}."})
    seen_assignments = set()
    for assignment in data["assignments"]:
        key = (assignment.get("employee_id"), assignment.get("brand_id"), assignment.get("process"))
        if key in seen_assignments:
            problems.append({"type": "Invalid configuration", "detail": f"Duplicate employee assignment: {key[0]} / {key[1]} / {key[2]}."})
        seen_assignments.add(key)
        if key[0] not in employee_ids or key[1] not in brand_ids or key[2] not in process_names:
            problems.append({"type": "Invalid configuration", "detail": f"Employee assignment references an unknown employee, brand, or process: {key}."})
    for bucket in ("planned_leave", "unavailability", "comp_offs"):
        seen_dates = set()
        for item in data.get(bucket, []):
            try:
                date.fromisoformat(item.get("date", ""))
            except (TypeError, ValueError):
                problems.append({"type": "Invalid configuration", "detail": f"Invalid date in {bucket}: {item.get('date')}."})
            if item.get("employee_id") not in employee_ids:
                problems.append({"type": "Invalid configuration", "detail": f"{bucket} references unknown employee {item.get('employee_id')}."})
            key = (item.get("employee_id"), item.get("date"))
            if key in seen_dates:
                problems.append({"type": "Invalid configuration", "detail": f"Duplicate {bucket} date for employee {key[0]}: {key[1]}."})
            seen_dates.add(key)
    seen_holidays = set()
    for holiday in data.get("holidays", []):
        try:
            date.fromisoformat(holiday)
        except (TypeError, ValueError):
            problems.append({"type": "Invalid configuration", "detail": f"Invalid public holiday date: {holiday}."})
        if holiday in seen_holidays:
            problems.append({"type": "Invalid configuration", "detail": f"Duplicate public holiday date: {holiday}."})
        seen_holidays.add(holiday)
    return problems


def _unavailable(data, employee_id, day):
    key = day.isoformat()
    if any(x["employee_id"] == employee_id and x["date"] == key for x in data.get("unavailability", [])):
        return True
    if any(x["employee_id"] == employee_id and x["date"] == key for x in data.get("planned_leave", [])):
        return True
    if any(x["employee_id"] == employee_id and x["date"] == key for x in data.get("comp_offs", [])):
        return True
    return False


def _eligible_for_requirement(data, req):
    return [a["employee_id"] for a in data["assignments"]
            if a["brand_id"] == req["brand_id"] and a["process"] == req["process"]]


def build_roster(data, year, month, mode="Balanced"):
    """Build a deterministic daily roster, honoring hard constraints before preferences."""
    employees = _employee_by_id(data)
    brands = _brand_by_id(data)
    assignments = []
    monthly_load = Counter()
    weekly_load = Counter()
    active_week = None
    for day in _days(year, month):
        week_key = day.isocalendar()[:2]
        if week_key != active_week:
            weekly_load = Counter()
            active_week = week_key
        # Expand each lane into staffing slots, then use augmenting-path matching.
        # This can move an earlier flexible assignment to preserve a specialist
        # for a lane with fewer alternatives later in the day.
        slots = []
        for req in data["requirements"]:
            holiday = day.isoformat() in data.get("holidays", [])
            if day.weekday() not in req["operating_days"] or (holiday and not req.get("operates_on_holidays", False)):
                continue
            candidates = []
            for employee_id in dict.fromkeys(_eligible_for_requirement(data, req)):
                employee = employees.get(employee_id)
                if not employee or day.weekday() == employee["weekly_off"] or _unavailable(data, employee_id, day):
                    continue
                if holiday and not employee.get("holiday_eligible", False):
                    continue
                if weekly_load[employee_id] < employee["max_shifts_per_week"]:
                    candidates.append(employee_id)
            if mode == "Standard":
                candidates.sort()
            else:
                candidates.sort(key=lambda eid: (
                    day.weekday() in employees[eid].get("preferred_days_off", []),
                    monthly_load[eid], weekly_load[eid], eid,
                ))
            for _ in range(req["required"]):
                slots.append({"requirement": req, "candidates": candidates})
        if mode == "Smart":
            slots.sort(key=lambda slot: (len(slot["candidates"]), -slot["requirement"]["required"],
                                         slot["requirement"]["brand_id"], slot["requirement"]["process"]))
        else:
            slots.sort(key=lambda slot: (-slot["requirement"]["required"], len(slot["candidates"]),
                                         slot["requirement"]["brand_id"], slot["requirement"]["process"]))

        employee_slot = {}
        slot_employee = {}

        def place(slot_index, seen):
            for employee_id in slots[slot_index]["candidates"]:
                if employee_id in seen:
                    continue
                seen.add(employee_id)
                previous_slot = employee_slot.get(employee_id)
                if previous_slot is None or place(previous_slot, seen):
                    employee_slot[employee_id] = slot_index
                    slot_employee[slot_index] = employee_id
                    return True
            return False

        for slot_index in range(len(slots)):
            place(slot_index, set())
        for slot_index, employee_id in slot_employee.items():
            req = slots[slot_index]["requirement"]
            assignments.append({"date": day.isoformat(), "employee_id": employee_id,
                                "brand_id": req["brand_id"], "process": req["process"], "status": "Working"})
            monthly_load[employee_id] += 1
            weekly_load[employee_id] += 1

    # Explicit status rows make the employee calendar easy to review.
    scheduled = {(x["employee_id"], x["date"]) for x in assignments}
    for day in _days(year, month):
        for employee in data["employees"]:
            if (employee["id"], day.isoformat()) in scheduled:
                continue
            if day.isoformat() in data.get("holidays", []):
                status = "Holiday"
            elif any(x["employee_id"] == employee["id"] and x["date"] == day.isoformat() for x in data.get("planned_leave", [])):
                status = "Leave"
            elif any(x["employee_id"] == employee["id"] and x["date"] == day.isoformat() for x in data.get("comp_offs", [])):
                status = "Comp-Off"
            elif any(x["employee_id"] == employee["id"] and x["date"] == day.isoformat() for x in data.get("unavailability", [])):
                status = "Unavailable"
            elif employee["weekly_off"] == day.weekday():
                status = "Weekly Off"
            else:
                status = "Available"
            assignments.append({"date": day.isoformat(), "employee_id": employee["id"],
                                "brand_id": "", "process": "", "status": status})
    return assignments


def validate_roster(data, roster):
    employees = _employee_by_id(data)
    brands = _brand_by_id(data)
    work = [x for x in roster if x["status"] == "Working"]
    by_date_employee = defaultdict(list)
    by_date_lane = Counter()
    allowed_lanes = {(a["employee_id"], a["brand_id"], a["process"]) for a in data["assignments"]}
    requirements = {(r["brand_id"], r["process"]): r for r in data["requirements"]}
    for row in work:
        by_date_employee[(row["date"], row["employee_id"])].append(row)
    issues = []
    invalid_rows = set()
    weekly_groups = defaultdict(list)
    for (day_key, employee_id), rows in by_date_employee.items():
        if len(rows) > 1:
            issues.append({"type": "Employee overlap", "date": day_key,
                           "employee": employees.get(employee_id, {}).get("name", employee_id),
                           "detail": "Employee is assigned to more than one process on the same day."})
            invalid_rows.update(id(row) for row in rows)
        day = date.fromisoformat(day_key)
        holiday_ineligible = day_key in data.get("holidays", []) and employee_id in employees and not employees[employee_id].get("holiday_eligible", False)
        if employee_id in employees and (employees[employee_id]["weekly_off"] == day.weekday() or _unavailable(data, employee_id, day) or holiday_ineligible):
            issues.append({"type": "Unavailable employee", "date": day_key,
                           "employee": employees[employee_id]["name"],
                           "detail": "Employee is scheduled on a weekly off, leave, holiday, or unavailable date."})
            invalid_rows.update(id(row) for row in rows)
        for row in rows:
            if employee_id not in employees:
                issues.append({"type": "Unknown employee", "date": day_key, "employee": employee_id,
                               "detail": "Roster row references an employee missing from the directory."})
                invalid_rows.add(id(row))
            elif (employee_id, row["brand_id"], row["process"]) not in allowed_lanes:
                issues.append({"type": "Unauthorized assignment", "date": day_key,
                               "employee": employees[employee_id]["name"],
                               "detail": f"Employee is not assigned to {row['brand_id']} / {row['process']}."})
                invalid_rows.add(id(row))
            else:
                requirement = requirements.get((row["brand_id"], row["process"]))
                closed_day = requirement is None or day.weekday() not in requirement["operating_days"]
                closed_holiday = day_key in data.get("holidays", []) and not (requirement or {}).get("operates_on_holidays", False)
                if closed_day or closed_holiday:
                    issues.append({"type": "Outside operating calendar", "date": day_key,
                                   "employee": employees[employee_id]["name"],
                                   "detail": "Employee is assigned to a lane when that lane is closed."})
                    invalid_rows.add(id(row))
                else:
                    weekly_groups[(employee_id, day.isocalendar()[:2])].append(row)

    # The weekly cap is also validated after manual edits.
    for (employee_id, week_key), rows in weekly_groups.items():
        limit = employees[employee_id]["max_shifts_per_week"]
        ordered = sorted(rows, key=lambda row: (row["date"], row["brand_id"], row["process"]))
        if len(ordered) > limit:
            for row in ordered[limit:]:
                invalid_rows.add(id(row))
            issues.append({"type": "Weekly shift limit", "week": f"{week_key[0]}-W{week_key[1]:02d}",
                           "employee": employees[employee_id]["name"], "assigned": len(ordered), "limit": limit,
                           "detail": "Employee is assigned more shifts than the configured weekly limit."})

    weekly_load_by_day = defaultdict(int)
    for (employee_id, week_key), rows in weekly_groups.items():
        for row in rows:
            weekly_load_by_day[(employee_id, week_key)] += 1

    # Only valid assignments contribute to meeting a coverage target.
    for row in work:
        day = date.fromisoformat(row["date"])
        employee_id = row["employee_id"]
        if id(row) in invalid_rows or employee_id not in employees:
            continue
        if day.isoformat() in data.get("holidays", []) and not employees[employee_id].get("holiday_eligible", False):
            continue
        by_date_lane[(row["date"], row["brand_id"], row["process"])] += 1
    for day in _days_from_roster(roster):
        for req in data["requirements"]:
            holiday = day.isoformat() in data.get("holidays", [])
            if day.weekday() not in req["operating_days"] or (holiday and not req.get("operates_on_holidays", False)):
                continue
            assigned = by_date_lane[(day.isoformat(), req["brand_id"], req["process"])]
            if assigned < req["required"]:
                eligible_ids = _eligible_for_requirement(data, req)
                candidates = [employees[eid]["name"] for eid in eligible_ids if eid in employees
                              and employees[eid]["weekly_off"] != day.weekday()
                              and not _unavailable(data, eid, day)
                              and (not holiday or employees[eid].get("holiday_eligible", False))
                              and weekly_load_by_day[(eid, day.isocalendar()[:2])] < employees[eid]["max_shifts_per_week"]
                              and not by_date_employee[(day.isoformat(), eid)]]
                brand = brands.get(req["brand_id"], {"name": req["brand_id"]})
                unavailable_people = [employees[eid]["name"] for eid in eligible_ids if eid in employees
                                      and _unavailable(data, eid, day)]
                reason = (", ".join(unavailable_people) + " unavailable") if unavailable_people else "Not enough eligible staff are available for this lane."
                issues.append({"type": "Coverage gap", "date": day.isoformat(), "brand": brand["name"],
                               "process": req["process"], "required": req["required"], "assigned": assigned,
                               "available": assigned + len(candidates), "affected_employee": ", ".join(unavailable_people),
                               "shortage": req["required"] - assigned, "reason": reason,
                               "backup_candidates": candidates[:5]})
    # Preferences are deliberately reported as warnings and never invalidate coverage.
    for row in work:
        employee = employees.get(row["employee_id"])
        if employee and date.fromisoformat(row["date"]).weekday() in employee.get("preferred_days_off", []):
            issues.append({"type": "Preference warning", "date": row["date"], "employee": employee["name"],
                           "detail": "Employee is scheduled on a preferred day off; mandatory coverage took priority."})
    return {"issues": issues}


def _days_from_roster(roster):
    values = sorted({x["date"] for x in roster})
    return [date.fromisoformat(x) for x in values]


def roster_summary(data, roster):
    if roster is None:
        return {"assignments": 0, "covered": 0, "gaps": 0}
    result = validate_roster(data, roster)
    days = _days_from_roster(roster)
    holidays = set(data.get("holidays", []))
    operational = sum(1 for day in days for req in data["requirements"]
                      if day.weekday() in req["operating_days"]
                      and (day.isoformat() not in holidays or req.get("operates_on_holidays", False)))
    gaps = sum(1 for issue in result["issues"] if issue["type"] == "Coverage gap")
    covered = max(0, operational - gaps)
    return {"assignments": sum(1 for x in roster if x["status"] == "Working"),
            "covered": covered, "gaps": gaps, "operational": operational,
            "coverage_percent": round(100 * covered / operational) if operational else 100}
