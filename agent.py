"""
Conversational agent: interprets user intent and calls ops, returns natural language.
Works without OpenAI; uses OPENAI_API_KEY if set for richer replies.
"""
import re
from typing import Tuple, Optional
import pandas as pd

import config
import ops
import sheets_sync

def _df_to_markdown(df: pd.DataFrame, max_rows: int = 20) -> str:
    if df is None or df.empty:
        return "_No data._"
    try:
        return df.head(max_rows).to_markdown(index=False)
    except Exception:
        return df.head(max_rows).to_string()

def _list_to_bullets(items: list) -> str:
    if not items:
        return "_None._"
    return "\n".join(f"- {x}" for x in items)

def handle_message(user_text: str) -> str:
    """Process one user message and return agent reply. Handles errors gracefully."""
    text = (user_text or "").strip().lower()
    if not text:
        return "You can ask me about pilot roster, assignments, drones, conflicts, or urgent reassignments. What do you need?"

    try:
        return _handle_message_impl(text)
    except Exception as e:
        return f"Something went wrong while processing your request. Please try again or rephrase. (Details: {e})"

def _handle_message_impl(text: str) -> str:
    """Inner implementation; raises on unexpected errors."""
    # --- Roster ---
    if re.search(r"show (all )?pilots|list (all )?pilots|(all )?pilots roster", text):
        df = sheets_sync.read_pilot_roster()
        return f"**Pilot roster:**\n\n{_df_to_markdown(df)}"

    if re.search(r"who (is|are) (available|on leave|unavailable)", text) or "pilot availability" in text:
        status = "Available"
        if "on leave" in text:
            status = "On Leave"
        elif "unavailable" in text:
            status = "Unavailable"
        df = ops.get_pilots(status=status)
        return f"**Pilots ({status}):**\n\n{_df_to_markdown(df)}"

    if re.search(r"pilots? (with )?skill", text) or "certification" in text or "cert" in text:
        skill = cert = loc = None
        if "skill" in text:
            for s in ["mapping", "survey", "inspection", "thermal"]:
                if s in text:
                    skill = s
                    break
        if "cert" in text or "certification" in text:
            cert = "DGCA"  # default filter
            if "night" in text:
                cert = "Night Ops"
        if "bangalore" in text or "mumbai" in text:
            loc = "Bangalore" if "bangalore" in text else "Mumbai"
        df = ops.get_pilots(skill=skill, certification=cert, location=loc)
        return f"**Matching pilots:**\n\n{_df_to_markdown(df)}"

    if re.search(r"current assignment|who('s| is) assigned|assignments?", text):
        df = ops.get_current_assignments()
        return f"**Current assignments:**\n\n{_df_to_markdown(df)}"

    if re.search(r"(set|update|mark|change|put).* (pilot )?status", text) or re.search(r"(pilot )?status.* (to )?(available|on leave|unavailable)", text):
        # e.g. "set P001 status to On Leave"
        pid = None
        for x in ["p001", "p002", "p003", "p004"]:
            if x in text:
                pid = x.upper()
                break
        if not pid:
            return "Please specify a pilot ID (e.g. P001) to update status."
        new_status = "Available"
        if "on leave" in text:
            new_status = "On Leave"
        elif "unavailable" in text:
            new_status = "Unavailable"
        try:
            ops.update_pilot_status(pid, new_status)
            return f"Updated **{pid}** status to **{new_status}** and synced to sheet."
        except Exception as e:
            return f"Could not update: {e}"

    # --- Missions / projects ---
    if "project" in text or "mission" in text:
        if "list" in text or "show" in text or "all" in text or "missions" in text:
            df = ops.get_missions()
            return f"**Missions:**\n\n{_df_to_markdown(df)}"
        if "match" in text or "suggest" in text or "who can" in text:
            for pid in ["prj001", "prj002", "prj003"]:
                if pid in text:
                    suggestions = ops.match_pilots_to_project(pid.upper())
                    if not suggestions:
                        return f"No available pilots match project **{pid.upper()}** (location, skills, certs)."
                    return f"**Pilots matching {pid.upper()}:**\n\n" + _list_to_bullets([f"{s['name']} ({s['pilot_id']})" for s in suggestions])
            return "Specify a project ID (e.g. PRJ001) to get pilot suggestions."
        if "assign" in text:
            # "assign P001 to PRJ001"
            pid = None
            prj = None
            for x in ["p001", "p002", "p003", "p004"]:
                if x in text:
                    pid = x.upper()
                    break
            for x in ["prj001", "prj002", "prj003"]:
                if x in text:
                    prj = x.upper()
                    break
            if not pid or not prj:
                return "Say e.g. 'Assign P001 to PRJ001' with pilot and project IDs."
            try:
                ops.assign_pilot_to_project(pid, prj)
                return f"Assigned **{pid}** to **{prj}**. Roster updated and synced."
            except Exception as e:
                return f"Assignment failed: {e}"
        if "unassign" in text:
            pid = None
            for x in ["p001", "p002", "p003", "p004"]:
                if x in text:
                    pid = x.upper()
                    break
            if not pid:
                return "Specify a pilot ID (e.g. P001) to unassign."
            try:
                ops.unassign_pilot(pid)
                return f"Unassigned **{pid}**. Status set to Available and synced."
            except Exception as e:
                return f"Unassign failed: {e}"

    # --- Drones ---
    if "drone" in text or "fleet" in text or "inventory" in text:
        if "maintenance" in text or "due" in text:
            df = ops.get_maintenance_due()
            return f"**Drones due for maintenance:**\n\n{_df_to_markdown(df)}"
        if "available" in text or "status" in text:
            cap = loc = None
            if "thermal" in text:
                cap = "Thermal"
            if "rgb" in text or "lidar" in text:
                cap = "RGB" if "rgb" in text else "LiDAR"
            if "bangalore" in text or "mumbai" in text:
                loc = "Bangalore" if "bangalore" in text else "Mumbai"
            df = ops.get_drones(capability=cap, location=loc, status="Available")
            return f"**Available drones:**\n\n{_df_to_markdown(df)}"
        if "update" in text or "set" in text or "mark" in text:
            did = None
            for x in ["d001", "d002", "d003", "d004"]:
                if x in text:
                    did = x.upper()
                    break
            if not did:
                return "Specify a drone ID (e.g. D001) to update status."
            new_status = "Available"
            if "maintenance" in text:
                new_status = "Maintenance"
            elif "deployed" in text:
                new_status = "Deployed"
            try:
                ops.update_drone_status(did, new_status)
                return f"Updated drone **{did}** to **{new_status}** and synced to sheet."
            except Exception as e:
                return f"Update failed: {e}"
        df = sheets_sync.read_drone_fleet()
        return f"**Drone fleet:**\n\n{_df_to_markdown(df)}"

    # --- Conflicts ---
    if "conflict" in text or "double" in text or "mismatch" in text or "issue" in text or "problem" in text:
        all_c = ops.run_all_conflicts()
        parts = []
        if all_c["double_booking"]:
            parts.append("**Double booking:**\n" + _list_to_bullets([str(x) for x in all_c["double_booking"]]))
        if all_c["skill_cert_mismatch"]:
            parts.append("**Skill/cert mismatch:**\n" + _list_to_bullets([str(x) for x in all_c["skill_cert_mismatch"]]))
        if all_c["drone_maintenance_assigned"]:
            parts.append("**Drone in maintenance but assigned:**\n" + _list_to_bullets([str(x) for x in all_c["drone_maintenance_assigned"]]))
        if all_c["location_mismatch"]:
            parts.append("**Pilot–project location mismatch:**\n" + _list_to_bullets([str(x) for x in all_c["location_mismatch"]]))
        if all_c.get("pilot_drone_location_mismatch"):
            parts.append("**Pilot and drone in different locations:**\n" + _list_to_bullets([str(x) for x in all_c["pilot_drone_location_mismatch"]]))
        if not any(all_c.values()):
            return "No conflicts detected."
        return "\n\n".join(parts) if parts else "No conflicts detected."

    # --- Urgent reassignment ---
    if "urgent" in text or "reassign" in text:
        prj = None
        for x in ["prj001", "prj002", "prj003"]:
            if x in text:
                prj = x.upper()
                break
        if not prj:
            return "Specify a project ID (e.g. PRJ002) for urgent reassignment suggestions."
        result = ops.suggest_urgent_reassignment(prj, reason="Urgent reassignment requested")
        if "error" in result:
            return result["error"]
        lines = [
            f"**Urgent reassignment for {prj}**",
            "",
            "**Suggested pilots:** " + (", ".join(f"{p['name']} ({p['pilot_id']})" for p in result["suggested_pilots"]) or "None"),
            "**Suggested drones:** " + (", ".join(d.get("drone_id", d.get("drone_id", "")) for d in result["suggested_drones"]) or "None"),
            "",
            "**Conflicts to resolve:** " + str(result["conflicts"]),
        ]
        return "\n".join(lines)

    # --- Greeting / help ---
    if any(w in text for w in ["hello", "hi", "hey", "help"]):
        return (
            "**Skylark Operations Coordinator**\n\n"
            "I can help with:\n"
            "- **Roster:** Who's available, on leave; filter by skill/cert/location; update pilot status (syncs to Google Sheet)\n"
            "- **Assignments:** List assignments, match pilots to projects, assign or unassign\n"
            "- **Drones:** List fleet, filter by capability/location, maintenance due, update drone status (syncs to sheet)\n"
            "- **Conflicts:** Double-booking, skill/cert mismatch, drone in maintenance, location mismatch\n"
            "- **Urgent reassignment:** Suggest pilots and drones for a project and show conflicts\n\n"
            "Try: *Who is available?* | *Pilots with Mapping skill in Bangalore* | *Current assignments* | *Drones due for maintenance* | *Conflicts?* | *Urgent reassignment for PRJ002*"
        )

    return (
        "I didn't quite get that. You can ask about **pilots** (availability, skills, status), **assignments**, **drones** (fleet, maintenance), **conflicts**, or **urgent reassignment** for a project. "
        "Say **help** for examples."
    )
