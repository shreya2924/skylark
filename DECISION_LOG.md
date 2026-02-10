# Decision Log — Skylark Ops Coordinator Agent

A short note on the choices we made while building this, and how we read the brief.

---

## What we assumed

**Data and sheets**  
We treated the pilot roster, drone fleet, and missions as the single source of truth. For conflict checks (e.g. overlapping dates), we assume roster assignments use the same IDs as in missions (PRJ001, PRJ002, etc.). The sample data had “Project-A” in one place—we kept that in mind; in a full setup, sticking to project_id everywhere keeps conflicts accurate.  

Google Sheets “2-way sync” here means: we *read* everything from Sheets when it’s configured, and we *write* back pilot status/assignments to the Pilot Roster and drone status to the Drone Fleet. Missions are read-only from the agent’s side; we didn’t add create/update for missions in this version. Empty assignments are normalized to a dash (–) so CSV and Sheets stay consistent.

**Conversation without an LLM**  
We wanted the agent to work out of the box without API keys or internet. So we went with intent-style handling (keywords and a bit of regex) instead of a full LLM. The downside is that phrasing has to be somewhat recognizable; the upside is it runs anywhere and stays predictable. If we had more time, we’d add an optional LLM layer for more natural, open-ended chat.

---

## Trade-offs we’re aware of

**Intent-based vs LLM**  
We chose “good enough” understanding so the prototype is self-contained. Users need to phrase things in a natural but fairly standard way (e.g. “Who is available?”, “Set P001 status to On Leave”). We’re okay with that for a first version.

**One worksheet per Sheet**  
We assume each Google Sheet has one main tab (the default “Sheet1”). If you use multiple tabs, we’d need to extend config (or the UI) to pick which sheet name to use.

**Double-booking**  
Each pilot has only one `current_assignment` in the roster. So “double booking” really shows up when we *try* to assign the same pilot to a second project whose dates overlap with the first. We block that at assign-time and also run conflict checks so we can report overlapping projects and who’s on what.

---

## How we read “urgent reassignments”

We took **urgent reassignments** to mean: *when a project needs coverage quickly (e.g. someone’s unavailable or a drone is in maintenance), the agent should suggest who else can take it, which drones fit, and what might get in the way.*

So we added a single flow: you say something like *“Urgent reassignment for PRJ002”* and the agent returns in one go:

- **Suggested pilots** — available, right location, right skills/certs, and free by the project start date  
- **Suggested drones** — available, same location, right capabilities  
- **Conflicts** — double-booking, skill/cert mismatches, drones in maintenance, location mismatches  

That way the coordinator gets one screen of “here’s who and what you can use, and here’s what to fix” before confirming anything. No extra back-and-forth.

---

## What we’d do next with more time

- **Optional LLM** — Plug in OpenAI (or a local model) for freer conversation and follow-up questions while keeping the current intent flow as fallback.  
- **Missions in the agent** — Let the agent create or update mission rows and sync those back to Sheets, not just read them.  
- **Audit trail** — Log every status and assignment change (who, when, what) for accountability.  
- **Tests** — Unit tests for `ops` and `sheets_sync`, plus a few integration tests with mocked Sheets.  
- **Smarter matching** — Factor in things like pilot preference, travel, or drone–pilot fit when suggesting assignments.

---

Thanks for reading. If something here doesn’t match what you had in mind, we’re happy to adjust.
