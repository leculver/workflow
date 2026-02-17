---
name: rt-triage-issue
description: >
  Core issue triage engine. Triages a single GitHub issue: fetches details, categorizes as bug/feature/docs/question,
  attempts reproduction and fix, writes structured JSON report and markdown summary. Use when the user says
  "triage" or "work on" an issue. Use when processing issues from a sprint queue, or pass a specific issue
  number to triage on demand. Do NOT use when the user says "load", "continue", or "pick up" an issue —
  that is rt-load-issue. Reads repo config from config/repos.json.
---

# Triage Issue

Triage a single GitHub issue end-to-end: fetch, categorize, reproduce, attempt fix, and report.

## When to Use

- Processing the next issue from a sprint queue
- Triaging a specific issue by number
- Re-triaging an issue after new information

## When Not to Use

- Continuing deep investigation on a previously triaged issue (use `rt-load-issue`)
- Batch processing multiple issues (use `rt-triage-loop`)
- Reprocessing platform-blocked issues on a different OS (use `rt-platform-reprocess`)

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| repo | Yes | Repository in `owner/repo` format (e.g., `dotnet/diagnostics`) |
| issue_number | No | Specific issue to triage. If omitted, pick next from sprint queue. |
| skip_repro | No | Skip reproduction attempt (default: false) |
| skip_fix | No | Skip fix attempt (default: false) |
| workspace | No | Path to the workspace root where repo checkouts and repros live (default: parent of triage repo) |

## Workflow

### Step 0: Ensure Triage Repo Is Up to Date

If you have not already fetched and pulled the triage repo during this session, do so now:

1. `git fetch` and `git pull` in the triage repo root (`D:\git\work`).
2. If you have already done this earlier in the session (or remember doing so), skip this step.

### Step 1: Load Configuration

1. Read `config/repos.json` from the triage repo root.
2. Find the entry for the requested `repo`.
3. Load area classification rules, local paths, debugger paths, and dump env vars.
4. If the repo is not configured, stop and tell the user to run `rt-add-repo` first.

### Step 2: Select the Issue

**If `issue_number` is provided:** Use that issue directly.

**If not provided:**
1. Look for an active sprint run in `runs/` for this repo and platform.
2. Find the most recent `run.json` where `status` is `in-progress`.
3. Read its `queue` array and pick the last entry (pop from end).
4. If no active sprint or empty queue, tell the user to run `rt-sprint-setup` first.
5. Update the run's queue (remove the selected issue) and save.

### Step 3: Fetch Issue Details

1. Use GitHub MCP tools to fetch the full issue: title, body, labels, all comments.
2. Check for open PRs that reference this issue.
3. Record `fetched_at_utc` timestamp.

### Step 4: Check Prior Work

1. Check if `issues/<owner>-<repo>/<issue_number>/report.json` exists.
2. If it does, read it — this issue was previously triaged.
3. Check if `repros/issue_<issue_number>/` exists in the workspace.
4. Summarize what's known before proceeding.

### Step 5: Triage

Analyze the issue and determine:

1. **Category**: bug, feature-request, question, or docs. Read the issue body, labels, and comments carefully.
2. **Status**: See [triage categories](references/triage-categories.md) for the full list.
3. **Staleness**: Is this issue current, outdated, or superseded?
4. **Area**: Classify using the area rules from `config/repos.json`.
5. **Platform requirements**: Which platforms are needed to reproduce/investigate?

For feature requests, check if the feature has already been implemented in the current codebase. Don't attempt to build features that already exist.

For bugs, check if the bug has already been fixed since the issue was filed.

### Step 6: Reproduce (unless skip_repro)

Follow the [reproduction rules](references/reproduction-rules.md):

1. Create `<workspace>/repros/issue_<NUMBER>/` if it doesn't exist.
2. Ensure the source repo is on the main branch.
3. Write a minimal repro (console app, unit test, or script).
4. Set dump capture environment variables from config.
5. Run the repro and record all steps in the JSON.
6. All dump files must use the `.dmp` extension (rename Linux core dumps if needed).
7. Dumps are NOT committed (too large). Instead, commit the repro source and a `repro.sh`/`repro.bat` script to regenerate them. See [reproduction rules](references/reproduction-rules.md) for details.
8. If reproduction requires a different platform, set status to `platform-blocked` and note which platform.

### Step 7: Attempt Fix (unless skip_fix)

Attempt a fix in any of these cases:
- The bug was **reproduced** and the root cause is understood.
- The bug was **not reproduced** but the root cause is obvious from code inspection (e.g., clear null check missing, off-by-one, wrong condition). The fix should still be proposed — it helps the developer understand the issue even without a repro.
- A **feature request** has a straightforward implementation path.

Do NOT attempt a fix if:
- The issue is too vague to understand what the fix should be.
- The fix would require major architectural changes or is highly speculative.

When creating a fix:
1. Create a branch `issue_<NUMBER>` in the appropriate repo.
2. Make the fix, run targeted tests if possible.
3. Record the fix details (summary, confidence, branch, diff) in the JSON.
4. Set `fix.confidence` lower for fixes without reproduction (e.g., 0.4–0.6 vs. 0.8+ for reproduced fixes).
5. Push the branch to `origin` (the user's fork), NOT `upstream`.
6. Do NOT include `Co-authored-by: Copilot` in fix commit messages — these are proposed fixes authored by the developer.
7. Return to the main branch when done.

### Step 8: Write Reports

1. **Write JSON report** to `issues/<owner>-<repo>/<issue_number>/report.json`:
   - Follow the [JSON schema](references/json-schema.md).
   - This is always the single source of truth — overwrite in place.
   - Write atomically (`.tmp` then rename).
   - Set `manually_investigated` to `false` (automated triage).

3. **Append to captain's log** at `issues/<owner>-<repo>/<issue_number>/log.md`:
   - Append a timestamped session entry (do NOT overwrite previous entries).
   - Record: session date/time, platform, what was attempted, what was discovered, what changed.
   - Format:
     ```markdown
     ## <ISO 8601 timestamp> — <platform> — automated triage
     
     **Actions:** <what was done>
     **Findings:** <what was discovered>
     **Status change:** <old status> → <new status> (if changed)
     **Fix:** <fix summary if any>
     ```
   - If this is the first session, create the file with a `# Log: <repo>#<issue_number>` header.

4. **Write Markdown report** to `issues/<owner>-<repo>/<issue_number>/report.md`:
   - Explain the issue, triage status, category, staleness.
   - Full accounting of investigation and reproduction attempts.
   - Describe any fix candidate.
   - Write atomically.

### Step 9: Commit Results

1. Stage the new/updated files in the triage repo:
   - `issues/<owner>-<repo>/<issue_number>/report.json`
   - `issues/<owner>-<repo>/<issue_number>/report.md`
   - `issues/<owner>-<repo>/<issue_number>/repro/` (repro source code and regeneration script — NOT dumps)
   - `issues/<owner>-<repo>/<issue_number>/log.md`
   - Updated `runs/*/run.json` (if queue was modified)
2. Commit with message: `triage: <owner>/<repo>#<number> — <status> (<category>)`
3. Example: `triage: dotnet/diagnostics#5632 — reproduced (feature-request)`
4. Push to the remote. If the push fails (e.g., remote is ahead), ask the user whether to rebase and retry or skip the push.

## Validation

- [ ] `report.json` is valid JSON matching the schema
- [ ] `report.md` exists and has content
- [ ] Session entry appended to `log.md`
- [ ] Sprint queue was updated (issue removed) if processing from queue
- [ ] Source repos are back on main branch
- [ ] Results committed to triage repo

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Repo not in config | Run `rt-add-repo` first |
| No active sprint | Run `rt-sprint-setup` first |
| Left source repo on wrong branch | Always `git checkout main` when done |
| Lost context from prior sessions | Append to `log.md`, never overwrite it |
| Full test suite run | Only run targeted tests — full suite takes 50+ min |
