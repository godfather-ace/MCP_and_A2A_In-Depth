"""
Automobile Service Center MCP Server
======================================
Tools provided:
    - list_vehicles            : List all vehicles in the service center
    - get_vehicle_details      : Get full info for a specific vehicle (by VIN or reg)
    - register_vehicle         : Register a new vehicle for service
    - create_service_job       : Create a new service/repair job for a vehicle
    - list_service_jobs        : List jobs (filter by status / priority)
    - update_service_job       : Update job status, technician, and notes
    - check_parts_inventory    : Check availability of spare parts
    - update_parts_inventory   : Add or consume parts stock
    - log_diagnostic_report    : Log OBD / diagnostic results for a vehicle
    - schedule_appointment     : Book a service appointment for a customer
    - list_appointments        : View upcoming appointments
    - generate_invoice_summary : Summarise charges for a completed job
    - log_safety_check         : Record pre-/post-service safety inspection
"""

import json
from datetime import datetime, timedelta
from typing import Any

from mcp.server.fastmcp import FastMCP

# ──────────────────────────────────────────────────────────────
# In-memory data store  (swap for SQLite / PostgreSQL in prod)
# ──────────────────────────────────────────────────────────────

VEHICLES: dict[str, dict] = {
    "MH12AB1234": {
        "vin": "1HGBH41JXMN109186",
        "make": "Honda", "model": "City", "year": 2021,
        "fuel": "petrol", "odometer_km": 42500,
        "owner": "Arjun Sharma", "phone": "9876543210",
        "color": "Pearl White",
    },
    "KA03CD5678": {
        "vin": "WBAWL73579P178456",
        "make": "BMW", "model": "3 Series", "year": 2022,
        "fuel": "petrol", "odometer_km": 18700,
        "owner": "Priya Nair", "phone": "9123456780",
        "color": "Mineral Grey",
    },
    "TN09EF9012": {
        "vin": "2T1BURHE0JC034522",
        "make": "Toyota", "model": "Innova Crysta", "year": 2020,
        "fuel": "diesel", "odometer_km": 75300,
        "owner": "Ravi Kumar", "phone": "9988776655",
        "color": "Silky Silver",
    },
    "DL01GH3456": {
        "vin": "3VWFE21C04M000001",
        "make": "Maruti Suzuki", "model": "Swift", "year": 2023,
        "fuel": "petrol", "odometer_km": 8200,
        "owner": "Sneha Verma", "phone": "9001234567",
        "color": "Cerulean Blue",
    },
}

SERVICE_JOBS: dict[str, dict] = {
    "SJ-001": {
        "reg": "MH12AB1234", "type": "periodic_service",
        "description": "30,000 km periodic service — oil, filter, brake check",
        "status": "in_progress", "priority": "medium",
        "technician": "Mohan", "bay": "Bay 2",
        "parts_used": ["OIL-5W30-4L", "OIL-FILTER-H"],
        "labour_hours": 2.5, "notes": "", "created": "2025-05-19",
    },
    "SJ-002": {
        "reg": "KA03CD5678", "type": "repair",
        "description": "Suspension noise — front left strut inspection",
        "status": "pending", "priority": "high",
        "technician": "Raju", "bay": "",
        "parts_used": [], "labour_hours": 0, "notes": "", "created": "2025-05-20",
    },
    "SJ-003": {
        "reg": "TN09EF9012", "type": "body_work",
        "description": "Rear bumper dent & repaint",
        "status": "pending", "priority": "low",
        "technician": "", "bay": "Body Shop",
        "parts_used": [], "labour_hours": 0, "notes": "", "created": "2025-05-20",
    },
}
_sj_counter = 4

APPOINTMENTS: list[dict] = [
    {
        "id": "APT-001", "reg": "DL01GH3456",
        "owner": "Sneha Verma", "phone": "9001234567",
        "date": "2025-05-22", "time": "10:00",
        "service_type": "first_free_service", "status": "confirmed",
    },
]
_apt_counter = 2

PARTS_INVENTORY: dict[str, dict] = {
    "OIL-5W30-4L":    {"name": "Engine Oil 5W-30 (4 L)",         "qty": 30,  "unit": "can",  "price_inr": 950,   "reorder_level": 10},
    "OIL-FILTER-H":   {"name": "Oil Filter — Honda compatible",  "qty": 18,  "unit": "pcs",  "price_inr": 320,   "reorder_level": 5},
    "AIR-FILTER-T":   {"name": "Air Filter — Toyota Innova",     "qty": 7,   "unit": "pcs",  "price_inr": 680,   "reorder_level": 3},
    "BRAKE-PAD-F":    {"name": "Front Brake Pads (set of 4)",    "qty": 12,  "unit": "set",  "price_inr": 1800,  "reorder_level": 4},
    "SPARK-PLUG-NGK": {"name": "NGK Spark Plug Iridium",         "qty": 40,  "unit": "pcs",  "price_inr": 420,   "reorder_level": 8},
    "STRUT-BMW-FL":   {"name": "Front-Left Strut Assembly — BMW","qty": 2,   "unit": "pcs",  "price_inr": 14500, "reorder_level": 1},
    "COOLANT-1L":     {"name": "Coolant / Antifreeze (1 L)",     "qty": 25,  "unit": "bottle","price_inr": 280,  "reorder_level": 10},
    "TIMING-BELT-MZ": {"name": "Timing Belt — Maruti 1.2L",     "qty": 4,   "unit": "pcs",  "price_inr": 1200,  "reorder_level": 2},
    "WIPER-BLADE-24": {"name": "Wiper Blade 24-inch",            "qty": 20,  "unit": "pcs",  "price_inr": 350,   "reorder_level": 6},
    "BATTERY-65AH":   {"name": "Car Battery 65 Ah MF",           "qty": 5,   "unit": "pcs",  "price_inr": 5200,  "reorder_level": 2},
}

DIAGNOSTIC_LOGS: list[dict] = []
SAFETY_CHECKS:   list[dict] = []

LABOUR_RATE_PER_HOUR = 500   # INR

VALID_JOB_STATUSES  = {"pending", "in_progress", "awaiting_parts", "quality_check", "completed", "cancelled"}
VALID_JOB_TYPES     = {"periodic_service", "repair", "body_work", "detailing", "inspection", "tyre_service", "electrical"}
VALID_PRIORITIES    = {"low", "medium", "high", "critical"}
VALID_APT_STATUSES  = {"confirmed", "rescheduled", "completed", "cancelled"}


# ──────────────────────────────────────────────────────────────
# MCP Server
# ──────────────────────────────────────────────────────────────

mcp = FastMCP(
    name="AutoServiceCenterMCP",
    instructions=(
        "You are an automobile service center assistant. "
        "Help manage vehicles, service jobs, spare-parts inventory, "
        "customer appointments, diagnostics, and safety inspections."
    ),
)


# ── 1. Vehicles ───────────────────────────────────────────────

@mcp.tool()
def list_vehicles(make_filter: str = "") -> str:
    """
    List all vehicles currently registered at the service center.

    Args:
        make_filter: Optional make name to filter (e.g. 'Honda', 'BMW').

    Returns:
        JSON array of vehicles with registration, make, model, owner, and odometer.
    """
    result = []
    for reg, v in VEHICLES.items():
        if make_filter and v["make"].lower() != make_filter.lower():
            continue
        result.append({"reg": reg, **v})
    return json.dumps(result, indent=2)


@mcp.tool()
def get_vehicle_details(reg: str) -> str:
    """
    Get complete details for a vehicle by registration number.

    Args:
        reg: Vehicle registration number, e.g. MH12AB1234.

    Returns:
        JSON object with full vehicle and owner details, or an error.
    """
    v = VEHICLES.get(reg.upper())
    if not v:
        return json.dumps({"error": f"Vehicle '{reg}' not found."})
    return json.dumps({"reg": reg.upper(), **v}, indent=2)


@mcp.tool()
def register_vehicle(
    reg: str,
    vin: str,
    make: str,
    model: str,
    year: int,
    fuel: str,
    odometer_km: int,
    owner: str,
    phone: str,
    color: str = "",
) -> str:
    """
    Register a new vehicle at the service center.

    Args:
        reg:          Registration number (unique), e.g. MH12XY9999.
        vin:          17-character Vehicle Identification Number.
        make:         Manufacturer name, e.g. Honda.
        model:        Model name, e.g. City.
        year:         Manufacturing year.
        fuel:         petrol | diesel | electric | hybrid | cng.
        odometer_km:  Current odometer reading in kilometres.
        owner:        Owner's full name.
        phone:        Owner's contact number.
        color:        Vehicle colour (optional).

    Returns:
        Confirmation message.
    """
    key = reg.upper()
    if key in VEHICLES:
        return f"Error: Vehicle '{reg}' is already registered."
    VEHICLES[key] = {
        "vin": vin, "make": make, "model": model, "year": year,
        "fuel": fuel, "odometer_km": odometer_km,
        "owner": owner, "phone": phone, "color": color,
    }
    return f"✅ Vehicle {key} ({year} {make} {model}) registered under {owner}."


# ── 2. Service Jobs ───────────────────────────────────────────

@mcp.tool()
def create_service_job(
    reg: str,
    job_type: str,
    description: str,
    priority: str = "medium",
    technician: str = "",
    bay: str = "",
) -> str:
    """
    Create a new service or repair job for a vehicle.

    Args:
        reg:         Vehicle registration number.
        job_type:    One of: periodic_service | repair | body_work | detailing |
                    inspection | tyre_service | electrical.
        description: Detailed description of work to be done.
        priority:    low | medium | high | critical (default: medium).
        technician:  Assigned technician name (optional).
        bay:         Workshop bay assignment (optional).

    Returns:
        Confirmation with new job ID.
    """
    global _sj_counter
    key = reg.upper()
    if key not in VEHICLES:
        return f"Error: Vehicle '{reg}' not found. Register it first."
    if job_type not in VALID_JOB_TYPES:
        return f"Error: Invalid job type '{job_type}'. Choose from: {', '.join(VALID_JOB_TYPES)}."
    if priority not in VALID_PRIORITIES:
        return f"Error: Invalid priority '{priority}'. Use: {', '.join(VALID_PRIORITIES)}."
    job_id = f"SJ-{_sj_counter:03d}"
    _sj_counter += 1
    SERVICE_JOBS[job_id] = {
        "reg": key, "type": job_type, "description": description,
        "status": "pending", "priority": priority,
        "technician": technician, "bay": bay,
        "parts_used": [], "labour_hours": 0, "notes": "",
        "created": datetime.now().strftime("%Y-%m-%d"),
    }
    v = VEHICLES[key]
    return (
        f"✅ Service job {job_id} created for {key} "
        f"({v['year']} {v['make']} {v['model']}) — {job_type} [{priority}]."
    )


@mcp.tool()
def list_service_jobs(status_filter: str = "", priority_filter: str = "") -> str:
    """
    List service jobs with optional status and priority filters.

    Args:
        status_filter:   Optional. One of: pending | in_progress | awaiting_parts |
                        quality_check | completed | cancelled.
        priority_filter: Optional. One of: low | medium | high | critical.

    Returns:
        JSON array of matching service jobs.
    """
    result = []
    for job_id, job in SERVICE_JOBS.items():
        if status_filter   and job["status"]   != status_filter:
            continue
        if priority_filter and job["priority"] != priority_filter:
            continue
        result.append({"id": job_id, **job})
    return json.dumps(result, indent=2)


@mcp.tool()
def update_service_job(
    job_id: str,
    new_status: str,
    technician: str = "",
    labour_hours: float = -1,
    parts_used: str = "",
    notes: str = "",
) -> str:
    """
    Update a service job's status, technician, hours, parts, and notes.

    Args:
        job_id:       Job identifier, e.g. SJ-001.
        new_status:   pending | in_progress | awaiting_parts | quality_check |
                    completed | cancelled.
        technician:   Reassign/set technician (optional).
        labour_hours: Total labour hours logged so far; -1 = no change.
        parts_used:   Comma-separated part IDs added in this update, e.g.
                    'BRAKE-PAD-F,OIL-5W30-4L' (optional).
        notes:        Progress notes to append (optional).

    Returns:
        Confirmation or error message.
    """
    jid = job_id.upper()
    if jid not in SERVICE_JOBS:
        return f"Error: Service job '{job_id}' not found."
    if new_status not in VALID_JOB_STATUSES:
        return f"Error: Invalid status '{new_status}'. Use: {', '.join(VALID_JOB_STATUSES)}."
    job = SERVICE_JOBS[jid]
    old_status = job["status"]
    job["status"] = new_status
    if technician:
        job["technician"] = technician
    if labour_hours >= 0:
        job["labour_hours"] = labour_hours
    if parts_used:
        new_parts = [p.strip().upper() for p in parts_used.split(",") if p.strip()]
        job["parts_used"].extend(new_parts)
    if notes:
        job["notes"] = f"{job['notes']} | {notes}".lstrip(" | ")
    return (
        f"✅ Job {jid} updated: {old_status} → {new_status}."
        + (f" Technician: {technician}." if technician else "")
        + (f" Labour: {labour_hours}h." if labour_hours >= 0 else "")
        + (f" Parts added: {parts_used}." if parts_used else "")
    )


# ── 3. Parts Inventory ────────────────────────────────────────

@mcp.tool()
def check_parts_inventory(part_id: str = "") -> str:
    """
    Check spare-parts inventory. Returns all parts or a specific item.

    Args:
        part_id: Optional part identifier, e.g. BRAKE-PAD-F.
                Leave empty to list all items.

    Returns:
        JSON with stock levels, unit prices, and low-stock alerts.
    """
    if part_id:
        pid = part_id.upper()
        item = PARTS_INVENTORY.get(pid)
        if not item:
            return json.dumps({"error": f"Part '{part_id}' not found."})
        return json.dumps({
            "id": pid, **item,
            "low_stock": item["qty"] <= item["reorder_level"],
        }, indent=2)
    result = []
    for pid, item in PARTS_INVENTORY.items():
        result.append({"id": pid, **item, "low_stock": item["qty"] <= item["reorder_level"]})
    return json.dumps(result, indent=2)


@mcp.tool()
def update_parts_inventory(part_id: str, quantity_change: int, reason: str = "") -> str:
    """
    Add or consume parts from stock.

    Args:
        part_id:         Part identifier, e.g. SPARK-PLUG-NGK.
        quantity_change: Positive = stock received; negative = parts consumed.
        reason:          Optional reason, e.g. 'Used in SJ-002', 'Purchase order #44'.

    Returns:
        Confirmation with updated stock level or error.
    """
    pid = part_id.upper()
    if pid not in PARTS_INVENTORY:
        return f"Error: Part '{part_id}' not found."
    item = PARTS_INVENTORY[pid]
    new_qty = item["qty"] + quantity_change
    if new_qty < 0:
        return (
            f"Error: Insufficient stock for {item['name']}. "
            f"Available: {item['qty']} {item['unit']}, requested: {abs(quantity_change)}."
        )
    item["qty"] = new_qty
    direction = "Received" if quantity_change > 0 else "Consumed"
    alert = " ⚠️ LOW STOCK — raise purchase order." if new_qty <= item["reorder_level"] else ""
    return (
        f"✅ {direction} {abs(quantity_change)} {item['unit']} of {item['name']}. "
        f"Stock now: {new_qty} {item['unit']}.{alert}"
        + (f" Reason: {reason}." if reason else "")
    )


# ── 4. Diagnostics ────────────────────────────────────────────

@mcp.tool()
def log_diagnostic_report(
    reg: str,
    job_id: str,
    dtc_codes: str,
    technician: str,
    summary: str,
    battery_voltage: float = 0.0,
    engine_temp_c: float = 0.0,
) -> str:
    """
    Log an OBD-II / diagnostic scan report for a vehicle.

    Args:
        reg:             Vehicle registration number.
        job_id:          Associated service job ID.
        dtc_codes:       Comma-separated DTC fault codes, e.g. 'P0301,P0420'.
                        Use 'NONE' if no faults found.
        technician:      Technician who performed the scan.
        summary:         Human-readable diagnostic summary.
        battery_voltage: Battery voltage reading in volts (optional).
        engine_temp_c:   Engine coolant temperature in °C (optional).

    Returns:
        Confirmation with diagnostic log ID.
    """
    key = reg.upper()
    if key not in VEHICLES:
        return f"Error: Vehicle '{reg}' not found."
    diag_id = f"DIAG-{len(DIAGNOSTIC_LOGS) + 1:04d}"
    codes = [c.strip() for c in dtc_codes.split(",") if c.strip()]
    entry = {
        "id":              diag_id,
        "reg":             key,
        "job_id":          job_id.upper(),
        "timestamp":       datetime.now().isoformat(timespec="seconds"),
        "dtc_codes":       codes,
        "fault_count":     0 if codes == ["NONE"] else len(codes),
        "battery_voltage": battery_voltage,
        "engine_temp_c":   engine_temp_c,
        "technician":      technician,
        "summary":         summary,
    }
    DIAGNOSTIC_LOGS.append(entry)
    fault_msg = (
        f" ⚠️ {entry['fault_count']} DTC fault(s) found: {', '.join(codes)}."
        if entry["fault_count"] > 0 else " ✅ No fault codes detected."
    )
    return f"✅ Diagnostic report {diag_id} logged for {key}.{fault_msg}"


# ── 5. Appointments ───────────────────────────────────────────

@mcp.tool()
def schedule_appointment(
    reg: str,
    owner: str,
    phone: str,
    date: str,
    time: str,
    service_type: str,
) -> str:
    """
    Book a service appointment for a customer.

    Args:
        reg:          Vehicle registration (need not be pre-registered).
        owner:        Customer name.
        phone:        Customer contact number.
        date:         Appointment date in YYYY-MM-DD format.
        time:         Appointment time in HH:MM (24-hour) format.
        service_type: Brief description, e.g. 'periodic_service', 'tyre_rotation',
                    'AC service', 'general check-up'.

    Returns:
        Confirmation with appointment ID.
    """
    global _apt_counter
    apt_id = f"APT-{_apt_counter:03d}"
    _apt_counter += 1
    APPOINTMENTS.append({
        "id":           apt_id,
        "reg":          reg.upper(),
        "owner":        owner,
        "phone":        phone,
        "date":         date,
        "time":         time,
        "service_type": service_type,
        "status":       "confirmed",
    })
    return (
        f"✅ Appointment {apt_id} confirmed for {owner} ({reg.upper()}) "
        f"on {date} at {time} — {service_type}."
    )


@mcp.tool()
def list_appointments(date_filter: str = "") -> str:
    """
    List upcoming service appointments.

    Args:
        date_filter: Optional date in YYYY-MM-DD to see only that day's appointments.

    Returns:
        JSON array of appointments sorted by date and time.
    """
    result = [
        a for a in APPOINTMENTS
        if (not date_filter or a["date"] == date_filter)
        and a["status"] not in {"completed", "cancelled"}
    ]
    result.sort(key=lambda x: (x["date"], x["time"]))
    return json.dumps(result, indent=2)


# ── 6. Invoice Summary ────────────────────────────────────────

@mcp.tool()
def generate_invoice_summary(job_id: str) -> str:
    """
    Generate a cost summary for a completed (or in-progress) service job.

    Args:
        job_id: Service job identifier, e.g. SJ-001.

    Returns:
        JSON invoice summary with parts cost, labour cost, and total (INR).
    """
    jid = job_id.upper()
    if jid not in SERVICE_JOBS:
        return json.dumps({"error": f"Job '{job_id}' not found."})
    job = SERVICE_JOBS[jid]
    v   = VEHICLES.get(job["reg"], {})

    parts_breakdown = []
    parts_total = 0
    for pid in job["parts_used"]:
        part = PARTS_INVENTORY.get(pid)
        if part:
            parts_breakdown.append({
                "part_id":   pid,
                "name":      part["name"],
                "unit":      part["unit"],
                "price_inr": part["price_inr"],
            })
            parts_total += part["price_inr"]

    labour_cost = round(job["labour_hours"] * LABOUR_RATE_PER_HOUR, 2)
    subtotal    = parts_total + labour_cost
    gst         = round(subtotal * 0.18, 2)
    total       = round(subtotal + gst, 2)

    return json.dumps({
        "job_id":       jid,
        "reg":          job["reg"],
        "vehicle":      f"{v.get('year','')} {v.get('make','')} {v.get('model','')}".strip(),
        "owner":        v.get("owner", "—"),
        "job_type":     job["type"],
        "status":       job["status"],
        "technician":   job["technician"],
        "labour_hours": job["labour_hours"],
        "labour_cost":  labour_cost,
        "parts":        parts_breakdown,
        "parts_total":  parts_total,
        "subtotal":     subtotal,
        "gst_18pct":    gst,
        "total_inr":    total,
    }, indent=2)


# ── 7. Safety Checks ──────────────────────────────────────────

@mcp.tool()
def log_safety_check(
    reg: str,
    job_id: str,
    check_type: str,
    technician: str,
    brakes_ok: bool,
    lights_ok: bool,
    tyres_ok: bool,
    fluid_levels_ok: bool,
    remarks: str = "",
) -> str:
    """
    Record a pre-service or post-service safety inspection.

    Args:
        reg:             Vehicle registration number.
        job_id:          Associated service job ID.
        check_type:      'pre_service' or 'post_service'.
        technician:      Technician performing the check.
        brakes_ok:       True if brakes pass inspection.
        lights_ok:       True if all lights are functional.
        tyres_ok:        True if tyre pressure and condition are acceptable.
        fluid_levels_ok: True if all fluid levels are within range.
        remarks:         Additional observations (optional).

    Returns:
        Confirmation with safety check ID and overall pass/fail.
    """
    key = reg.upper()
    if key not in VEHICLES:
        return f"Error: Vehicle '{reg}' not found."
    check_id = f"SC-{len(SAFETY_CHECKS) + 1:04d}"
    passed   = all([brakes_ok, lights_ok, tyres_ok, fluid_levels_ok])
    entry = {
        "id":              check_id,
        "reg":             key,
        "job_id":          job_id.upper(),
        "timestamp":       datetime.now().isoformat(timespec="seconds"),
        "check_type":      check_type,
        "technician":      technician,
        "brakes_ok":       brakes_ok,
        "lights_ok":       lights_ok,
        "tyres_ok":        tyres_ok,
        "fluid_levels_ok": fluid_levels_ok,
        "overall_pass":    passed,
        "remarks":         remarks,
    }
    SAFETY_CHECKS.append(entry)
    status_icon = "✅ PASSED" if passed else "❌ FAILED"
    failed_items = [
        item for item, ok in [
            ("Brakes", brakes_ok), ("Lights", lights_ok),
            ("Tyres", tyres_ok), ("Fluid levels", fluid_levels_ok),
        ] if not ok
    ]
    fail_msg = f" Issues: {', '.join(failed_items)}." if failed_items else ""
    return f"{status_icon} Safety {check_type} check {check_id} logged for {key}.{fail_msg}"


# ──────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()