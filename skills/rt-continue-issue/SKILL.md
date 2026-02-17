---
name: rt-continue-issue
description: >
  Loads all prior context for a specific issue and presents a briefing to the developer. Reads the existing
  JSON report, captain's log, reproduction artifacts, fix branches, and latest GitHub comments. Does NOT
  autonomously investigate — instead primes the conversation so the developer can ask followups, try things,
  and direct the investigation interactively. Use when you want to pick up where you left off on an issue.
---

# Continue Issue

Load all prior context for an issue and brief the developer for an interactive investigation session.

## When to Use

- Picking up a previously triaged issue for hands-on work
- Reviewing what was done before and deciding next steps
- Starting an interactive debugging or code review session on a specific issue

## When Not to Use

- First-time triage of an issue (use `rt-triage-issue`)
- Batch processing (use `rt-triage-loop`)
- Fully automated re-investigation (use `rt-triage-issue` with the issue number)

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| issue_number | Yes | The issue number to continue working on |
| repo | No | Repository in `owner/repo` format (default: infer from existing reports) |
| workspace | No | Path to workspace root (default: parent of triage repo) |

## Workflow

### Step 0: Ensure Triage Repo Is Up to Date

If you have not already fetched and pulled the triage repo during this session, do so now:

1. `git fetch` and `git pull` in the triage repo root (`D:\git\work`).
2. If you have already done this earlier in the session (or remember doing so), skip this step.

### Step 1: Locate and Load Prior Work

Before doing anything else, gather ALL context:

**a) Infer repo if not provided:**
- Search `issues/*/issue_number/report.json` across all repo directories in the triage repo.
- If found in exactly one, use that repo. If ambiguous, ask the user.

**b) GitHub Issue (live):**
- Use GitHub MCP tools to fetch the FULL issue: title, body, labels, ALL comments.
- Note any comments added since `fetched_at_utc` in the last report — these are NEW context.

**c) Existing JSON report:**
- Read `issues/<owner>-<repo>/<issue_number>/report.json`.

**d) Captain's log:**
- Read `issues/<owner>-<repo>/<issue_number>/log.md` in full.
- This is the best source of "what happened when" — understand the full investigation arc.

**e) Existing Markdown report:**
- Read `issues/<owner>-<repo>/<issue_number>/report.md`.

**f) Reproduction folder:**
- Check if `<workspace>/repros/issue_<issue_number>/` exists.
- If so, inventory its contents: repro apps, dumps, artifacts, logs, scripts.
- Check committed repro source in `issues/<owner>-<repo>/<issue_number>/repro/` too.

**g) Fix branches:**
- Check if a branch named `issue_<issue_number>` exists in the source repo(s).
- If so, review the diff against main to understand the candidate fix.

**h) Open PRs:**
- Check for open PRs referencing this issue.

### Step 2: Present Briefing

Present a clear, structured briefing to the developer. This is the **primary output** of this skill. Include:

1. **Issue summary** — Title, category, link, key details from the body
2. **Current triage status** — Status, staleness, affected repo, platforms
3. **Investigation history** — What was attempted across all sessions (from log.md)
4. **Reproduction status** — Was it reproduced? What repro artifacts exist? Where?
5. **Fix status** — Is there a candidate fix? Branch name, confidence, what it changes
6. **Open PRs** — Any PRs already addressing this issue
7. **New activity** — Any GitHub comments or changes since the last session
8. **Suggested next steps** — Based on current state, what are the logical things to try next

### Step 3: Wait for the Developer

**STOP HERE.** Do not autonomously investigate, reproduce, or fix anything.

The developer is now in the driver's seat. Wait for them to:
- Ask questions about the issue or prior work
- Request specific actions ("try reproducing with X", "look at function Y", "check if Z was fixed")
- Direct the investigation in a particular direction
- Ask you to run commands, read code, build repros, etc.

Follow the developer's lead. When they ask you to do something, do it and report back. This is an interactive session, not an automated triage run.

### Step 4: Update Reports (when the developer says they're done)

When the developer indicates the session is over (or asks you to save progress):

**JSON update:**
- Overwrite `report.json` in place with any updated triage status, observations, or fix info.
- Set `manually_investigated` to `true`.
- Write atomically (`.tmp` then rename).

**Captain's log — append a new session entry to `log.md`:**
- Do NOT overwrite previous entries — append only.
- Add a new `## <timestamp> — <platform> — manual investigation` section.
- Record: what was attempted, what was discovered, what changed.

**Markdown update:**
- Overwrite `report.md` with the latest findings.
- Clearly mark what is NEW from this session vs. carried over from prior work.

### Step 5: Commit

Commit with message: `continue: <owner>/<repo>#<number> — <summary of new findings>`

## Validation

- [ ] All prior context was loaded and presented in the briefing
- [ ] Developer was NOT preempted — no autonomous investigation
- [ ] When saving: session entry appended to `log.md` (not overwriting prior entries)
- [ ] When saving: `manually_investigated` set to `true`
- [ ] Source repos back on main branch
- [ ] Results committed to triage repo

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Jumping into investigation without being asked | STOP after the briefing — wait for developer direction |
| Missing new GitHub comments | Compare `fetched_at_utc` with comment dates |
| Can't find the repo | Provide `repo` explicitly if auto-detection fails |
| Repro folder is huge | Don't re-read dumps — summarize what files exist |
| Forgetting to save | Remind the developer to save progress before ending the session |
