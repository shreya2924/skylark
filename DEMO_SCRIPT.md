# Video demo script — test cases for Skylark Ops Coordinator

Use this while recording to show the project works. Run the app (local or Streamlit URL), then follow the steps in order. Keep the video under **3–5 minutes** if possible.

---

## Before you start

- Have the app open (Streamlit: your deployed URL, or local `streamlit run app.py`).
- If you use Google Sheets: have the **Pilot Roster** sheet open in another tab so you can show the 2-way sync at the end.
- Speak briefly at the start: *"This is the Skylark Drone Operations Coordinator. I’ll run a few test cases to show roster, assignments, drones, conflicts, and urgent reassignment."*

---

## Test case 1: Roster — who is available?

**What you say:** *"First, let’s see who is available."*

**What you do:** Type in chat:

```
Who is available?
```

**Expected:** A table of pilots with status "Available" (e.g. Arjun, Rohit). No errors.

---

## Test case 2: Current assignments

**What you say:** *"Now let’s check current assignments."*

**What you do:** Type:

```
Current assignments
```

**Expected:** A table showing pilots who are assigned (e.g. Neha – Project-A). If none, it shows "No data" or empty — that’s fine.

---

## Test case 3: Update pilot status (and 2-way sync)

**What you say:** *"I’ll set P001 to On Leave. This should sync back to Google Sheets."*

**What you do:** Type:

```
Set P001 status to On Leave
```

**Expected:** Reply like *"Updated P001 status to On Leave and synced to sheet."*

**If you use Sheets:** Switch to the Pilot Roster sheet, refresh — P001’s status should be "On Leave" and current_assignment empty. Say: *"You can see it updated in the sheet."*

---

## Test case 4: Match pilots to a project

**What you say:** *"Let’s see which pilots match project PRJ001."*

**What you do:** Type:

```
Match pilots to PRJ001
```

**Expected:** A list of pilots who match (location Bangalore, skill Mapping, cert DGCA, available). At least one name (e.g. Arjun) if data allows.

---

## Test case 5: Drone fleet and maintenance

**What you say:** *"Check the drone fleet and which are due for maintenance."*

**What you do:** Type:

```
Show drone fleet
```

**Expected:** Table of drones (D001–D004) with model, capabilities, status, location.

Then type:

```
Drones due for maintenance
```

**Expected:** Drones whose maintenance_due date is past or soon (e.g. D002 if maintenance_due is 2026-02-01).

---

## Test case 6: Conflicts

**What you say:** *"Let’s run conflict detection."*

**What you do:** Type:

```
Any conflicts?
```

**Expected:** Either *"No conflicts detected"* or a list of issues (double booking, skill/cert mismatch, drone in maintenance but assigned, location mismatch). Both are valid.

---

## Test case 7: Urgent reassignment

**What you say:** *"Finally, urgent reassignment for project PRJ002."*

**What you do:** Type:

```
Urgent reassignment for PRJ002
```

**Expected:** Suggested pilots, suggested drones, and a conflicts summary. Shows the agent can suggest who and what to use for an urgent project.

---

## Test case 8: Help

**What you do:** Type:

```
Help
```

**Expected:** A short help message with example prompts and what the agent can do.

---

## End of video

**What you say:** *"So we’ve checked roster, assignments, drone inventory, conflicts, urgent reassignment, and status updates syncing to the sheet. That’s the Skylark Operations Coordinator. Thanks for watching."*

---

## Quick checklist (for you)

- [ ] Test 1: Who is available  
- [ ] Test 2: Current assignments  
- [ ] Test 3: Set P001 to On Leave (+ show Sheets if used)  
- [ ] Test 4: Match pilots to PRJ001  
- [ ] Test 5: Drone fleet + maintenance due  
- [ ] Test 6: Any conflicts?  
- [ ] Test 7: Urgent reassignment for PRJ002  
- [ ] Test 8: Help  

Record in one take or cut between test cases — both are fine. Keep the camera/screen clear so the chat and replies are readable.
