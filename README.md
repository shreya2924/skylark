# 🛸 Skylark Drones — Operations Coordinator AI Agent

> A conversational AI agent that coordinates pilot roster, assignments, drone inventory, and conflict detection with **2-way Google Sheets sync**.

**Tech stack:** Python · Streamlit · Google Sheets API · Pandas

---

## Architecture overview

The system is layered: the **UI** talks to an **agent** that interprets intent and calls **ops**; **ops** reads/writes data via **sheets_sync**, which uses either **Google Sheets** or **local CSV**.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  LAYER 1: PRESENTATION                                                    │
│  app.py (Streamlit)                                                       │
│  • Chat UI, sidebar quick actions, styled layout                          │
│  • User message → agent.handle_message() → display reply                  │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼─────────────────────────────────────────┐
│  LAYER 2: CONVERSATIONAL AGENT                                            │
│  agent.py                                                                 │
│  • Intent detection (keywords / regex)                                   │
│  • Maps natural language → ops + sheets_sync calls                       │
│  • Formats responses (tables, bullets, errors)                            │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼─────────────────────────────────────────┐
│  LAYER 3: BUSINESS LOGIC                                                  │
│  ops.py                                                                   │
│  • Roster: get_pilots(), update_pilot_status(), get_current_assignments()│
│  • Assignments: match_pilots_to_project(), assign/unassign (with checks)  │
│  • Drone inventory: get_drones(), get_maintenance_due(), update_drone_*   │
│  • Conflicts: double-booking, skill/cert mismatch, location, maintenance│
│  • Urgent reassignment: suggest_urgent_reassignment(project_id)          │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼─────────────────────────────────────────┐
│  LAYER 4: DATA ACCESS                                                     │
│  sheets_sync.py + config.py                                               │
│  • read_pilot_roster | read_drone_fleet | read_missions                   │
│  • write_pilot_roster | write_drone_fleet (2-way sync)                    │
│  • config: .env, use_google_sheets() → credentials + sheet IDs             │
└────────────────────────────────┬─────────────────────────────────────────┘
                                  │
              ┌───────────────────┴───────────────────┐
              ▼                                       ▼
    ┌─────────────────────┐               ┌─────────────────────┐
    │  Google Sheets      │               │  Local CSV (data/)   │
    │  • Pilot Roster     │               │  • pilot_roster.csv   │
    │  • Drone Fleet      │               │  • drone_fleet.csv   │
    │  • Missions         │               │  • missions.csv      │
    │  (when .env set)    │               │  (fallback)          │
    └─────────────────────┘               └─────────────────────┘
```

### Component summary

| Component   | Role |
|------------|------|
| **app.py** | Streamlit entry point; chat + sidebar; sends user input to agent and renders replies. |
| **agent.py** | Conversational layer: intent detection, calls to ops/sheets_sync, response formatting. |
| **ops.py** | Core operations: roster, assignments, drones, conflicts, urgent reassignment. |
| **sheets_sync.py** | Read/write pilots, drones, missions; 2-way sync to Sheets or CSV. |
| **config.py** | Env and paths; decides Sheets vs local CSV. |
| **data/*.csv** | Default data when Google Sheets is not configured. |

---

## Features

| Area | Capabilities |
|------|----------------|
| **Roster** | Query by skill, certification, location, status; view assignments; update pilot status (syncs to Sheet). |
| **Assignments** | Match pilots to project; track assignments; assign/unassign with double-booking check. |
| **Drone inventory** | Query by capability, location, status; maintenance due; update drone status (syncs to Sheet). |
| **Conflicts** | Double-booking, skill/cert mismatch, drone in maintenance assigned, pilot–project location mismatch. |
| **Urgent reassignment** | Suggest pilots and drones for a project and list conflicts to resolve. |

---

## Quick start

```bash
git clone https://github.com/dbpr0415/skylark.git
cd skylark
pip install -r requirements.txt
streamlit run app.py
```

Open the URL shown (e.g. http://localhost:8501). Without `.env`, the app uses local CSVs in `data/`.

---

## Google Sheets setup (2-way sync)

1. **Google Cloud:** Enable Google Sheets API; create a **Service Account** and download its JSON key.
2. Save the JSON as `credentials.json` in the project root (or set `GOOGLE_CREDENTIALS_JSON` in `.env`).
3. Create three Google Sheets (e.g. “Pilot Roster”, “Drone Fleet”, “Missions”) and paste in the CSV data from `data/` (first row = header).
4. Share each sheet with the **service account email** (from the JSON) with **Editor** access.
5. Copy each sheet’s ID from the URL: `https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit`.
6. Create `.env` (see `.env.example`) and set:
   - `GOOGLE_CREDENTIALS_JSON=credentials.json`
   - `PILOT_SHEET_ID=...`
   - `DRONE_SHEET_ID=...`
   - `MISSIONS_SHEET_ID=...`

Pilot and drone status/assignment updates will then sync back to the sheets.

---

## Deploy (Streamlit Community Cloud)

1. Push the repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io), connect the repo, set **Main file path** to `app.py`.
3. In **Secrets**, add the same variables as in `.env` (sheet IDs and credentials). Without them, the app runs with local CSV data only.

---

## Sample prompts

- *Who is available?* / *Pilots with Mapping skill in Bangalore*
- *Current assignments*
- *Set P001 status to On Leave*
- *Match pilots to PRJ001* / *Assign P003 to PRJ001*
- *Drones due for maintenance* / *Update D002 to Available*
- *Any conflicts?*
- *Urgent reassignment for PRJ002*
- *Help*

---

## Repository structure

```
skylark/
├── app.py              # Streamlit UI
├── agent.py             # Conversational agent
├── ops.py               # Business logic (roster, assignments, drones, conflicts)
├── sheets_sync.py       # Google Sheets / CSV I/O
├── config.py            # Config and env
├── requirements.txt     # Dependencies
├── .env.example         # Env template (copy to .env)
├── data/                # Local CSV fallback
│   ├── pilot_roster.csv
│   ├── drone_fleet.csv
│   └── missions.csv
├── .streamlit/
│   └── config.toml      # Streamlit theme
├── README.md            # This file
└── DECISION_LOG.md      # Assumptions, trade-offs, “urgent reassignments”
```

---

## License & attribution

Built for the Skylark Drones Operations Coordinator assignment. See `DECISION_LOG.md` for design decisions and interpretation of requirements.
