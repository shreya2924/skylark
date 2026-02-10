"""
Core operations: roster, assignments, drone inventory, conflict detection.
Uses sheets_sync for read/write; normalizes "–" for empty assignment.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import re

import sheets_sync

EMPTY = "–"

def _parse_list(s: str) -> List[str]:
    if pd.isna(s) or str(s).strip() in ("", EMPTY):
        return []
    return [x.strip() for x in re.split(r"[,;]", str(s)) if x.strip()]

def _has_skill_or_cert(holder_list: List[str], required: str) -> bool:
    req = _parse_list(required)
    if not req:
        return True
    holder_set = {x.strip().lower() for x in holder_list}
    return any(r.strip().lower() in holder_set for r in req)

def _date_parse(d: str) -> Optional[datetime]:
    if pd.isna(d) or str(d).strip() in ("", EMPTY):
        return None
    s = str(d).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None

def _overlap(s1: str, e1: str, s2: str, e2: str) -> bool:
    a, b = _date_parse(s1), _date_parse(e1)
    c, d = _date_parse(s2), _date_parse(e2)
    if not all([a, b, c, d]):
        return False
    return not (b < c or d < a)

# --- Roster ---

def get_pilots(
    skill: Optional[str] = None,
    certification: Optional[str] = None,
    location: Optional[str] = None,
    status: Optional[str] = None,
) -> pd.DataFrame:
    df = sheets_sync.read_pilot_roster()
    if skill:
        df = df[df.apply(lambda r: _has_skill_or_cert(_parse_list(r.get("skills", "")), skill), axis=1)]
    if certification:
        df = df[df.apply(lambda r: _has_skill_or_cert(_parse_list(r.get("certifications", "")), certification), axis=1)]
    if location:
        loc = str(location).strip().lower()
        df = df[df["location"].astype(str).str.strip().str.lower() == loc]
    if status:
        st = str(status).strip()
        df = df[df["status"].astype(str).str.strip() == st]
    return df.reset_index(drop=True)

def get_current_assignments() -> pd.DataFrame:
    df = sheets_sync.read_pilot_roster()
    return df[df["current_assignment"].astype(str).str.strip() != EMPTY].reset_index(drop=True)

def update_pilot_status(pilot_id: str, new_status: str) -> None:
    """Update pilot status and sync to sheet. Allowed: Available, On Leave, Unavailable, Assigned."""
    allowed = {"Available", "On Leave", "Unavailable", "Assigned"}
    new_status = str(new_status).strip()
    if new_status not in allowed:
        raise ValueError(f"Status must be one of {allowed}")
    df = sheets_sync.read_pilot_roster()
    pid = str(pilot_id).strip()
    mask = df["pilot_id"].astype(str).str.strip() == pid
    if not mask.any():
        raise ValueError(f"Pilot not found: {pilot_id}")
    df.loc[mask, "status"] = new_status
    if new_status != "Assigned":
        df.loc[mask, "current_assignment"] = EMPTY
    sheets_sync.write_pilot_roster(df)

# --- Assignments & matching ---

def get_missions() -> pd.DataFrame:
    return sheets_sync.read_missions()

def match_pilots_to_project(project_id: str) -> List[Dict[str, Any]]:
    """Return pilots who match project location, skills, certs and are available (or explicitly include assigned)."""
    missions = sheets_sync.read_missions()
    proj = missions[missions["project_id"].astype(str).str.strip() == str(project_id).strip()]
    if proj.empty:
        return []
    proj = proj.iloc[0]
    loc = str(proj.get("location", "")).strip()
    req_skills = str(proj.get("required_skills", "")).strip()
    req_certs = str(proj.get("required_certs", "")).strip()
    start = proj.get("start_date")
    end = proj.get("end_date")

    pilots = sheets_sync.read_pilot_roster()
    available = pilots[
        (pilots["status"].astype(str).str.strip().str.lower() == "available")
        & (pilots["location"].astype(str).str.strip().str.lower() == loc.lower())
    ]
    out = []
    for _, r in available.iterrows():
        skills_ok = _has_skill_or_cert(_parse_list(r.get("skills", "")), req_skills)
        certs_ok = _has_skill_or_cert(_parse_list(r.get("certifications", "")), req_certs)
        avail_from = _date_parse(r.get("available_from"))
        start_d = _date_parse(start)
        available_in_time = (start_d is None or avail_from is None) or avail_from <= start_d
        if skills_ok and certs_ok and available_in_time:
            out.append({
                "pilot_id": r["pilot_id"],
                "name": r["name"],
                "skills": r.get("skills", ""),
                "certifications": r.get("certifications", ""),
                "location": r["location"],
                "status": r["status"],
            })
    return out

def assign_pilot_to_project(pilot_id: str, project_id: str) -> None:
    """Assign pilot to project; update roster and sync. Raises if double-book (overlapping dates)."""
    missions = sheets_sync.read_missions()
    proj = missions[missions["project_id"].astype(str).str.strip() == str(project_id).strip()]
    if proj.empty:
        raise ValueError(f"Project not found: {project_id}")
    proj_row = proj.iloc[0]
    proj_name = str(proj_row.get("project_id", project_id))
    new_start, new_end = proj_row["start_date"], proj_row["end_date"]

    df = sheets_sync.read_pilot_roster()
    pid = str(pilot_id).strip()
    mask = df["pilot_id"].astype(str).str.strip() == pid
    if not mask.any():
        raise ValueError(f"Pilot not found: {pilot_id}")
    current_assign = df.loc[mask, "current_assignment"].iloc[0]
    if str(current_assign).strip() != EMPTY:
        existing = missions[missions["project_id"].astype(str).str.strip() == str(current_assign).strip()]
        if not existing.empty:
            ex = existing.iloc[0]
            if _overlap(ex["start_date"], ex["end_date"], new_start, new_end):
                raise ValueError(
                    f"Double-booking: {pid} is already on {current_assign} with overlapping dates. "
                    "Unassign first or choose a different pilot."
                )
    df.loc[mask, "status"] = "Assigned"
    df.loc[mask, "current_assignment"] = proj_name
    sheets_sync.write_pilot_roster(df)

def unassign_pilot(pilot_id: str) -> None:
    df = sheets_sync.read_pilot_roster()
    pid = str(pilot_id).strip()
    mask = df["pilot_id"].astype(str).str.strip() == pid
    if not mask.any():
        raise ValueError(f"Pilot not found: {pilot_id}")
    df.loc[mask, "status"] = "Available"
    df.loc[mask, "current_assignment"] = EMPTY
    sheets_sync.write_pilot_roster(df)

# --- Drone inventory ---

def get_drones(
    capability: Optional[str] = None,
    status: Optional[str] = None,
    location: Optional[str] = None,
) -> pd.DataFrame:
    df = sheets_sync.read_drone_fleet()
    if capability:
        df = df[df.apply(lambda r: _has_skill_or_cert(_parse_list(r.get("capabilities", "")), capability), axis=1)]
    if status:
        st = str(status).strip()
        df = df[df["status"].astype(str).str.strip() == st]
    if location:
        loc = str(location).strip().lower()
        df = df[df["location"].astype(str).str.strip().str.lower() == loc]
    return df.reset_index(drop=True)

def get_maintenance_due() -> pd.DataFrame:
    df = sheets_sync.read_drone_fleet()
    today = datetime.now().date()
    def is_due(val):
        d = _date_parse(val)
        return d is not None and d.date() <= today
    return df[df["maintenance_due"].apply(is_due)].reset_index(drop=True)

def update_drone_status(drone_id: str, new_status: str) -> None:
    allowed = {"Available", "Maintenance", "Deployed"}
    new_status = str(new_status).strip()
    if new_status not in allowed:
        raise ValueError(f"Drone status must be one of {allowed}")
    df = sheets_sync.read_drone_fleet()
    did = str(drone_id).strip()
    mask = df["drone_id"].astype(str).str.strip() == did
    if not mask.any():
        raise ValueError(f"Drone not found: {drone_id}")
    df.loc[mask, "status"] = new_status
    if new_status == "Available":
        df.loc[mask, "current_assignment"] = EMPTY
    sheets_sync.write_drone_fleet(df)

# --- Conflict detection ---

def check_pilot_double_booking() -> List[Dict[str, Any]]:
    """Pilots assigned to overlapping project date ranges."""
    pilots = sheets_sync.read_pilot_roster()
    missions = sheets_sync.read_missions()
    assigned = pilots[pilots["current_assignment"].astype(str).str.strip() != EMPTY]
    conflicts = []
    for _, p in assigned.iterrows():
        pid, name, assign = p["pilot_id"], p["name"], p["current_assignment"]
        projs = missions[missions["project_id"].astype(str).str.strip() == str(assign).strip()]
        if projs.empty:
            continue
        p1 = projs.iloc[0]
        s1, e1 = p1["start_date"], p1["end_date"]
        for _, p2 in missions.iterrows():
            if str(p2["project_id"]).strip() == str(assign).strip():
                continue
            if _overlap(s1, e1, p2["start_date"], p2["end_date"]):
                # Check if same pilot is also assigned to p2 (e.g. via another source)
                other = assigned[assigned["current_assignment"].astype(str).str.strip() == str(p2["project_id"]).strip()]
                if not other.empty and (other["pilot_id"] == pid).any():
                    conflicts.append({
                        "pilot_id": pid,
                        "pilot_name": name,
                        "project_a": assign,
                        "project_b": p2["project_id"],
                        "dates_a": (s1, e1),
                        "dates_b": (p2["start_date"], p2["end_date"]),
                    })
    return conflicts

def check_skill_cert_mismatch() -> List[Dict[str, Any]]:
    """Pilots assigned to a project that requires skills/certs they don't have."""
    pilots = sheets_sync.read_pilot_roster()
    missions = sheets_sync.read_missions()
    mismatches = []
    for _, p in pilots.iterrows():
        assign = p.get("current_assignment", "")
        if str(assign).strip() == EMPTY:
            continue
        projs = missions[missions["project_id"].astype(str).str.strip() == str(assign).strip()]
        if projs.empty:
            continue
        proj = projs.iloc[0]
        req_skills = str(proj.get("required_skills", "")).strip()
        req_certs = str(proj.get("required_certs", "")).strip()
        skills_ok = _has_skill_or_cert(_parse_list(p.get("skills", "")), req_skills)
        certs_ok = _has_skill_or_cert(_parse_list(p.get("certifications", "")), req_certs)
        if not skills_ok or not certs_ok:
            mismatches.append({
                "pilot_id": p["pilot_id"],
                "pilot_name": p["name"],
                "project": assign,
                "missing_skills": req_skills if not skills_ok else None,
                "missing_certs": req_certs if not certs_ok else None,
            })
    return mismatches

def check_drone_maintenance_assigned() -> List[Dict[str, Any]]:
    """Drones in Maintenance but still have an assignment (or flagged as deployed)."""
    df = sheets_sync.read_drone_fleet()
    return df[
        (df["status"].astype(str).str.strip().str.lower() == "maintenance")
        & (df["current_assignment"].astype(str).str.strip() != EMPTY)
    ].to_dict("records")

def check_location_mismatch() -> List[Dict[str, Any]]:
    """Pilot and their assigned project in different locations."""
    pilots = sheets_sync.read_pilot_roster()
    missions = sheets_sync.read_missions()
    mismatches = []
    for _, p in pilots.iterrows():
        assign = p.get("current_assignment", "")
        if str(assign).strip() == EMPTY:
            continue
        projs = missions[missions["project_id"].astype(str).str.strip() == str(assign).strip()]
        if projs.empty:
            continue
        proj = projs.iloc[0]
        ploc = str(p.get("location", "")).strip().lower()
        mloc = str(proj.get("location", "")).strip().lower()
        if ploc != mloc:
            mismatches.append({
                "pilot_id": p["pilot_id"],
                "pilot_name": p["name"],
                "pilot_location": p["location"],
                "project": assign,
                "project_location": proj["location"],
            })
    return mismatches

def check_pilot_drone_location_mismatch() -> List[Dict[str, Any]]:
    """Pilot and assigned drone in different locations (same project). Edge case."""
    pilots = sheets_sync.read_pilot_roster()
    drones = sheets_sync.read_drone_fleet()
    missions = sheets_sync.read_missions()
    mismatches = []
    for _, p in pilots.iterrows():
        assign = p.get("current_assignment", "")
        if str(assign).strip() == EMPTY:
            continue
        ploc = str(p.get("location", "")).strip().lower()
        # Drones assigned to same project
        assigned_drones = drones[
            (drones["current_assignment"].astype(str).str.strip() == str(assign).strip())
        ]
        for _, d in assigned_drones.iterrows():
            dloc = str(d.get("location", "")).strip().lower()
            if ploc != dloc:
                mismatches.append({
                    "pilot_id": p["pilot_id"],
                    "pilot_name": p["name"],
                    "pilot_location": p["location"],
                    "drone_id": d.get("drone_id"),
                    "drone_location": d.get("location"),
                    "project": assign,
                })
    return mismatches

def run_all_conflicts() -> Dict[str, List]:
    return {
        "double_booking": check_pilot_double_booking(),
        "skill_cert_mismatch": check_skill_cert_mismatch(),
        "drone_maintenance_assigned": check_drone_maintenance_assigned(),
        "location_mismatch": check_location_mismatch(),
        "pilot_drone_location_mismatch": check_pilot_drone_location_mismatch(),
    }

# --- Urgent reassignments ---

def suggest_urgent_reassignment(project_id: str, reason: str = "") -> Dict[str, Any]:
    """
    For an urgent project: find best available pilots and drones; flag conflicts.
    reason can be e.g. 'pilot unavailable', 'drone in maintenance'.
    """
    missions = sheets_sync.read_missions()
    proj = missions[missions["project_id"].astype(str).str.strip() == str(project_id).strip()]
    if proj.empty:
        return {"error": f"Project not found: {project_id}"}
    proj = proj.iloc[0]
    loc = str(proj.get("location", "")).strip()
    req_skills = str(proj.get("required_skills", "")).strip()
    req_certs = str(proj.get("required_certs", "")).strip()
    req_cap = req_skills  # map skill to capability: Mapping->RGB/LiDAR, Inspection->RGB, Thermal->Thermal

    pilots = match_pilots_to_project(project_id)
    drones = get_drones(location=loc, status="Available")
    # Filter drones by capability overlap
    cap_map = {"mapping": "rgb lidar", "inspection": "rgb", "survey": "rgb", "thermal": "thermal"}
    need_caps = [cap_map.get(s.strip().lower(), s.strip().lower()) for s in _parse_list(req_skills)]
    def drone_ok(d):
        caps = " ".join(_parse_list(d.get("capabilities", ""))).lower()
        return any(n in caps for n in need_caps) if need_caps else True
    drones = drones[drones.apply(drone_ok, axis=1)]

    maintenance_due = get_drones(status="Maintenance")
    conflicts = run_all_conflicts()

    return {
        "project_id": project_id,
        "reason": reason,
        "suggested_pilots": pilots,
        "suggested_drones": drones.to_dict("records") if not drones.empty else [],
        "maintenance_due_count": len(maintenance_due),
        "conflicts": conflicts,
    }
