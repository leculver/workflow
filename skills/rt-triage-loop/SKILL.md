---
name: rt-triage-loop
description: >
  Runs the triage loop: repeatedly invokes rt-triage-issue for the current sprint until the queue is empty
  or a limit is reached. Generates the platform-appropriate loop script (bat/sh) or drives the loop directly.
  Use when you want to process multiple issues in one session.
---

# Triage Loop

Run the issue triage loop: process issues from the sprint queue one at a time until done or stopped.

## When to Use

- Processing multiple issues from a sprint queue in one session
- Running unattended triage overnight
- Generating a loop script to run independently

## When Not to Use

- Triaging a single specific issue (use `rt-triage-issue`)
- Setting up the sprint (use `rt-sprint-setup` first)

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| repo | Yes | Repository in `owner/repo` format |
| count | No | Max issues to process (default: all remaining in queue) |
| timeout_minutes | No | Stop after this many minutes (default: unlimited) |
| model | No | Copilot model to use (default: `claude-opus-4.6`) |
| generate_script | No | If true, generate a bat/sh script instead of running directly (default: false) |

## Workflow

### Step 0: Ensure Triage Repo Is Up to Date

If you have not already fetched and pulled the triage repo during this session, do so now:

1. `git fetch` and `git pull` in the triage repo root (`D:\git\work`).
2. If you have already done this earlier in the session (or remember doing so), skip this step.

### Step 1: Find Active Sprint

1. Read `config/repos.json` to validate the repo.
2. Scan `runs/` for the most recent `in-progress` sprint for this repo.
3. If none found, tell the user to run `rt-sprint-setup` first.
4. Read the sprint's `run.json` and check the queue.

### Step 2a: Generate Script (if generate_script is true)

Generate a loop script appropriate for the current platform:

**Windows (`triage-loop.bat`):**
```batch
@echo off
setlocal
set "TRIAGE_REPO=<path to triage repo>"
set "DONE_FILE=%TRIAGE_REPO%\runs\<run_id>\done.txt"

:loop
if exist "%DONE_FILE%" goto :done
powershell -NoProfile -Command "copilot --prompt 'Triage the next issue from the sprint for <repo>' --allow-all --model '<model>'"
if not exist "%DONE_FILE%" timeout /t 1 /nobreak >nul
goto :loop

:done
echo Done. Sprint complete.
```

**Linux (`triage-loop.sh`):**
```bash
#!/usr/bin/env bash
set -euo pipefail
TRIAGE_REPO="<path to triage repo>"
DONE_FILE="$TRIAGE_REPO/runs/<run_id>/done.txt"

while [[ ! -f "$DONE_FILE" ]]; do
  copilot --prompt "Triage the next issue from the sprint for <repo>" \
    --allow-all --model "<model>"
  [[ -f "$DONE_FILE" ]] || sleep 1
done
echo "Done. Sprint complete."
```

Write the script to the sprint's run directory: `runs/<run_id>/triage-loop.bat` or `.sh`.

### Step 2b: Run Directly (if generate_script is false)

1. Enter a loop:
   a. Read the sprint queue from `run.json`.
   b. If queue is empty, mark sprint complete and stop.
   c. If `count` limit reached or `timeout_minutes` exceeded, stop.
   d. Pop the last issue from the queue.
   e. Invoke the `rt-triage-issue` workflow for that issue.
   f. Move the issue number from `queue` to `processed` in `run.json`.
   g. Update `run.json` and commit.
   h. Repeat.

2. When the loop ends (queue empty, count reached, or timeout):
   - If queue is empty, set sprint `status` to `completed` and `ended_at` to now.
   - Write `runs/<run_id>/done.txt` with completion stats.
   - Commit the final state.

### Step 3: Report

Display progress summary:
```
Sprint: 2026-02-16_diagnostics_windows
Processed: 12 issues this session
Remaining: 35 issues in queue
Statuses: 5 reproduced, 3 stale, 2 already-fixed, 1 platform-blocked, 1 error

Next: "continue the triage loop" or "generate the summary"
```

## Validation

- [ ] Active sprint exists for the repo
- [ ] Queue is being correctly decremented
- [ ] Processed issues are tracked in `run.json`
- [ ] Sprint marked complete when queue empties
- [ ] Generated scripts have correct paths and are executable

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| No active sprint | Run `rt-sprint-setup` first |
| Script has wrong paths | Always use absolute paths in generated scripts |
| Copilot crashes mid-loop | The sentinel file pattern ensures restart picks up where it left off |
| Timeout not honored | Check elapsed time after each issue, not during |
