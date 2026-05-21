"""
Industrial MCP Server
================================
Tools provided:
    - list_machines          : List all machines and their status
    - get_machine_status     : Get detailed status of a specific machine
    - update_machine_status  : Update machine status (idle/running/maintenance/fault)
    - create_work_order      : Create a new work order
    - list_work_orders       : List work orders (optionally filter by status)
    - update_work_order      : Update work order status and notes
    - check_inventory        : Check stock level of a spare part / material
    - update_inventory       : Add or consume inventory items
    - log_safety_incident    : Log a safety incident or near-miss
    - get_maintenance_schedule: Return upcoming maintenance tasks
"""
import json
from datetime import datetime, timedelta
from mcp.server.fastmcp import FastMCP

# ──────────────────────────────────────────────
# In-memory "database" (replace with real DB)
# ──────────────────────────────────────────────
MACHINES: dict[str, dict] = {
    "CNC-001": {"name": "CNC Milling Machine",  "status": "idle",        "location": "Bay A", "last_service": "2025-03-10"},
    "CNC-002": {"name": "CNC Lathe",            "status": "running",     "location": "Bay A", "last_service": "2025-04-01"},
    "WLD-001": {"name": "MIG Welder",           "status": "idle",        "location": "Bay B", "last_service": "2025-02-20"},
    "PRS-001": {"name": "Hydraulic Press (50T)","status": "maintenance", "location": "Bay C", "last_service": "2025-05-01"},
    "DRL-001": {"name": "Radial Drill Press",   "status": "fault",       "location": "Bay B", "last_service": "2025-01-15"},
}

WORK_ORDERS: dict[str, dict] = {
    "WO-1001": {"title": "Shaft fabrication",      "machine": "CNC-002", "status": "in_progress", "priority": "high",   "notes": "", "created": "2025-05-18"},
    "WO-1002": {"title": "Gear housing repair",    "machine": "PRS-001", "status": "pending",     "priority": "medium", "notes": "", "created": "2025-05-19"},
    "WO-1003": {"title": "Bracket batch (x50)",    "machine": "CNC-001", "status": "pending",     "priority": "low",    "notes": "", "created": "2025-05-20"},
}
_wo_counter = 1004

INVENTORY: dict[str, dict] = {
    "BRG-6205":  {"name": "Ball Bearing 6205",   "qty": 24,  "unit": "pcs",  "reorder_level": 10},
    "HYD-OIL-46":{"name": "Hydraulic Oil ISO 46","qty": 200, "unit": "litre","reorder_level": 50},
    "END-MILL-8": {"name": "End Mill 8mm",      "qty": 6,   "unit": "pcs",  "reorder_level": 5},
    "WLD-WIRE-1": {"name": "MIG Wire ER70S-6 1mm","qty": 15, "unit": "kg",   "reorder_level": 5},
    "SAFETY-GLOVE":{"name":"Cut-Resistant Gloves","qty": 30, "unit": "pairs","reorder_level": 10},
}

SAFETY_LOG: list[dict] = []

MAINTENANCE_SCHEDULE: list[dict] = [
    {"machine": "CNC-001", "task": "Spindle lubrication",        "due": "2025-05-25", "interval_days": 30},
    {"machine": "CNC-002", "task": "Chuck jaw inspection",       "due": "2025-05-28", "interval_days": 30},
    {"machine": "WLD-001", "task": "Wire feed roller check",     "due": "2025-06-01", "interval_days": 60},
    {"machine": "PRS-001", "task": "Hydraulic fluid change",     "due": "2025-05-22", "interval_days": 90},
    {"machine": "DRL-001", "task": "Quill bearing replacement",  "due": "2025-05-21", "interval_days": 180},
]

# ──────────────────────────────────────────────
# MCP Server
# ──────────────────────────────────────────────
server = FastMCP(
    name="IndustrialWorkshopMCP",
    instructions=(
        "You are an industrial workshop assistant. "
        "Use the provided tools to manage machines, work orders, "
        "inventory, safety logs, and maintenance schedules."
    ),
)

VALID_MACHINE_STATUSES = {"idle", "running", "maintenance", "fault"}
VALID_WO_STATUSES      = {"pending", "in_progress", "on_hold", "completed", "cancelled"}
VALID_PRIORITIES       = {"low", "medium", "high", "critical"}


# ── 1. Machines ───────────────────────────────

@server.tool()
def list_machines(status_filter: str = "") -> str:
    """
    List all workshop machines.

    Args:
        status_filter: Optional. Filter by status: idle | running | maintenance | fault.
                    Leave empty to list all machines.

    Returns:
        JSON array of machines with id, name, status, and location.
    """
    result = []
    for machine_id, info in MACHINES.items():
        if status_filter and info["status"] != status_filter:
            continue
        result.append({"id": machine_id, **info})
    return json.dumps(result, indent=2)


@server.tool()
def get_machine_status(machine_id: str) -> str:
    """
    Get full details for a specific machine.

    Args:
        machine_id: Machine identifier, e.g. CNC-001.

    Returns:
        JSON object with all machine details, or an error message.
    """
    machine = MACHINES.get(machine_id.upper())
    if not machine:
        return json.dumps({"error": f"Machine '{machine_id}' not found."})
    return json.dumps({"id": machine_id.upper(), **machine}, indent=2)


@server.tool()
def update_machine_status(machine_id: str, new_status: str, notes: str = "") -> str:
    """
    Update the operational status of a machine.

    Args:
        machine_id: Machine identifier, e.g. CNC-001.
        new_status: One of: idle | running | maintenance | fault.
        notes:      Optional notes about the status change.

    Returns:
        Confirmation message or error.
    """
    mid = machine_id.upper()
    if mid not in MACHINES:
        return f"Error: Machine '{machine_id}' not found."
    if new_status not in VALID_MACHINE_STATUSES:
        return f"Error: Invalid status '{new_status}'. Use: {', '.join(VALID_MACHINE_STATUSES)}."
    old_status = MACHINES[mid]["status"]
    MACHINES[mid]["status"] = new_status
    return (
        f"✅ Machine {mid} status updated: {old_status} → {new_status}."
        + (f" Notes: {notes}" if notes else "")
    )


# ── 2. Work Orders ────────────────────────────

@server.tool()
def list_work_orders(status_filter: str = "") -> str:
    """
    List work orders, optionally filtered by status.

    Args:
        status_filter: Optional. One of: pending | in_progress | on_hold | completed | cancelled.

    Returns:
        JSON array of work orders.
    """
    result = []
    for wo_id, info in WORK_ORDERS.items():
        if status_filter and info["status"] != status_filter:
            continue
        result.append({"id": wo_id, **info})
    return json.dumps(result, indent=2)


@server.tool()
def create_work_order(
    title: str,
    machine_id: str,
    priority: str = "medium",
    notes: str = "",
) -> str:
    """
    Create a new work order for a machine.

    Args:
        title:      Short description of the work to be done.
        machine_id: Target machine identifier, e.g. CNC-001.
        priority:   low | medium | high | critical (default: medium).
        notes:      Any additional instructions or context.

    Returns:
        Confirmation with the new work order ID.
    """
    global _wo_counter
    mid = machine_id.upper()
    if mid not in MACHINES:
        return f"Error: Machine '{machine_id}' not found."
    if priority not in VALID_PRIORITIES:
        return f"Error: Invalid priority '{priority}'. Use: {', '.join(VALID_PRIORITIES)}."
    wo_id = f"WO-{_wo_counter}"
    _wo_counter += 1
    WORK_ORDERS[wo_id] = {
        "title":    title,
        "machine":  mid,
        "status":   "pending",
        "priority": priority,
        "notes":    notes,
        "created":  datetime.now().strftime("%Y-%m-%d"),
    }
    return f"✅ Work order {wo_id} created: '{title}' on {mid} [{priority} priority]."


@server.tool()
def update_work_order(wo_id: str, new_status: str, notes: str = "") -> str:
    """
    Update the status of an existing work order.

    Args:
        wo_id:      Work order identifier, e.g. WO-1001.
        new_status: One of: pending | in_progress | on_hold | completed | cancelled.
        notes:      Optional progress notes to append.

    Returns:
        Confirmation message or error.
    """
    wid = wo_id.upper()
    if wid not in WORK_ORDERS:
        return f"Error: Work order '{wo_id}' not found."
    if new_status not in VALID_WO_STATUSES:
        return f"Error: Invalid status '{new_status}'. Use: {', '.join(VALID_WO_STATUSES)}."
    old_status = WORK_ORDERS[wid]["status"]
    WORK_ORDERS[wid]["status"] = new_status
    if notes:
        existing = WORK_ORDERS[wid]["notes"]
        WORK_ORDERS[wid]["notes"] = f"{existing} | {notes}" if existing else notes
    return f"✅ Work order {wid} updated: {old_status} → {new_status}." + (f" Notes added." if notes else "")


# ── 3. Inventory ──────────────────────────────

@server.tool()
def check_inventory(part_id: str = "") -> str:
    """
    Check inventory levels. Returns all items or a specific part.

    Args:
        part_id: Optional part/material identifier, e.g. BRG-6205.
                Leave empty to list all inventory items.

    Returns:
        JSON with stock levels and reorder alerts.
    """
    if part_id:
        pid = part_id.upper()
        item = INVENTORY.get(pid)
        if not item:
            return json.dumps({"error": f"Part '{part_id}' not found in inventory."})
        low_stock = item["qty"] <= item["reorder_level"]
        return json.dumps({"id": pid, **item, "low_stock_alert": low_stock}, indent=2)

    result = []
    for pid, item in INVENTORY.items():
        result.append({
            "id":               pid,
            **item,
            "low_stock_alert":  item["qty"] <= item["reorder_level"],
        })
    return json.dumps(result, indent=2)


@server.tool()
def update_inventory(part_id: str, quantity_change: int, reason: str = "") -> str:
    """
    Add or consume inventory stock.

    Args:
        part_id:         Part identifier, e.g. END-MILL-8.
        quantity_change: Positive to add stock, negative to consume.
        reason:          Optional reason (e.g. 'Used in WO-1001', 'Stock replenishment').

    Returns:
        Confirmation with updated stock level or error.
    """
    pid = part_id.upper()
    if pid not in INVENTORY:
        return f"Error: Part '{part_id}' not found in inventory."
    item = INVENTORY[pid]
    new_qty = item["qty"] + quantity_change
    if new_qty < 0:
        return f"Error: Insufficient stock. Current: {item['qty']} {item['unit']}, requested: {abs(quantity_change)}."
    item["qty"] = new_qty
    direction = "Added" if quantity_change > 0 else "Consumed"
    alert = " ⚠️ LOW STOCK — reorder advised." if new_qty <= item["reorder_level"] else ""
    return (
        f"✅ {direction} {abs(quantity_change)} {item['unit']} of {item['name']}. "
        f"New stock: {new_qty} {item['unit']}.{alert}"
        + (f" Reason: {reason}" if reason else "")
    )


# ── 4. Safety ─────────────────────────────────

@server.tool()
def log_safety_incident(
    incident_type: str,
    location: str,
    description: str,
    reported_by: str,
    severity: str = "low",
) -> str:
    """
    Log a safety incident or near-miss in the workshop.

    Args:
        incident_type: e.g. 'near-miss', 'injury', 'equipment-damage', 'fire-hazard'.
        location:      Where it occurred, e.g. 'Bay B', 'CNC-001'.
        description:   What happened.
        reported_by:   Name or ID of the person reporting.
        severity:      low | medium | high | critical (default: low).

    Returns:
        Confirmation with incident log ID.
    """
    if severity not in VALID_PRIORITIES:
        return f"Error: Invalid severity '{severity}'. Use: low, medium, high, critical."
    incident_id = f"INC-{len(SAFETY_LOG) + 1:04d}"
    entry = {
        "id":            incident_id,
        "timestamp":     datetime.now().isoformat(timespec="seconds"),
        "type":          incident_type,
        "location":      location,
        "description":   description,
        "reported_by":   reported_by,
        "severity":      severity,
    }
    SAFETY_LOG.append(entry)
    alert = " 🚨 CRITICAL — escalate to safety officer immediately!" if severity == "critical" else ""
    return f"✅ Safety incident logged as {incident_id} [{severity} severity].{alert}"


# ── 5. Maintenance Schedule ───────────────────

@server.tool()
def get_maintenance_schedule(days_ahead: int = 30) -> str:
    """
    Return upcoming maintenance tasks within the specified time window.

    Args:
        days_ahead: How many calendar days ahead to look (default: 30).

    Returns:
        JSON array of maintenance tasks sorted by due date.
    """
    cutoff = datetime.now() + timedelta(days=days_ahead)
    upcoming = []
    for task in MAINTENANCE_SCHEDULE:
        due_dt = datetime.strptime(task["due"], "%Y-%m-%d")
        days_remaining = (due_dt - datetime.now()).days
        is_overdue = days_remaining < 0
        upcoming.append({
            **task,
            "days_remaining": days_remaining,
            "overdue":        is_overdue,
        })
    upcoming.sort(key=lambda x: x["due"])
    filtered = [t for t in upcoming if datetime.strptime(t["due"], "%Y-%m-%d") <= cutoff]
    return json.dumps(filtered, indent=2)


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────
if __name__ == "__main__":
    server.run()