---
name: rt-sprint-setup
description: >
  Sets up a new triage sprint for a GitHub repository. Queries GitHub for open issues matching a scope
  (labels, date range, keywords), cross-references against already-triaged issues to find only new work,
  and creates a sprint queue. Use when starting a new round of issue triage or when coming back after weeks/months.
---

# Sprint Setup

Initialize a new triage sprint: define scope, discover issues, build the processing queue.

## When to Use

- Starting a new triage session for a repo
- Coming back after weeks/months and wanting to process only new issues
- Scoping a focused sprint (e.g., only `area-Diagnostics-coreclr` issues)

## When Not to Use

- Processing individual issues (use `rt-triage-issue`)
- Running the loop (use `rt-triage-loop`)

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| repo | Yes | Repository in `owner/repo` format |
| scope | No | Additional GitHub search qualifiers (labels, keywords). Added to repo's default scope from config. |
| since | No | Only issues opened/updated since this date (ISO 8601). Default: date of the last completed sprint for this repo. |
| platform | No | Override platform detection. Default: auto-detect (`windows` or `linux`). |
| include_closed | No | Also include recently closed issues for review (default: false) |

## Workflow

### Step 0: Bookkeeping

Invoke `rt-bookkeeping` to pull the triage repo and flush any pending `.progress/` from prior sessions.

### Step 1: Load Configuration

1. Read `config/repos.json` and find the entry for the requested repo.
2. If not found, tell the user to run `rt-add-repo` first.

### Step 2: Determine "Since" Date

1. If `since` is provided, use it.
2. Otherwise, scan `runs/` for completed sprints for this repo.
3. Find the most recent one and use its `started_at` as the since date.
4. If no prior sprints exist, fetch ALL open issues (first-time run).

### Step 3: Query GitHub for Issues

1. Use GitHub MCP tools: `list_issues` or `search_issues` for the repo.
2. Apply scope filters: the repo's `default_query` from config + any user-provided `scope`.
3. If `since` is set, filter to issues created or updated after that date.
4. Exclude pull requests — only issues.
5. Collect: issue number, title, labels, created date, state.

### Step 4: Cross-Reference with Existing Triage Data

1. Scan `issues/<owner>-<repo>/*/report.json` in the triage repo.
2. Build a set of already-triaged issue numbers.
3. For each already-triaged issue, check:
   - Is the GitHub issue still open? If closed, note it but don't re-queue.
   - Has the issue been updated since last triage? If so, flag for re-triage.
   - Is it `platform-blocked` and we're now on the right platform? Add to queue.
4. Separate issues into: **new** (never triaged), **updated** (triaged but changed), **platform-unblocked** (blocked but now on right platform), **already-done** (triaged and unchanged).

### Step 5: Build the Sprint Queue

1. Create the queue as an array of issue numbers.
2. Order: platform-unblocked issues first (at the end of array = processed first), then new issues oldest-to-newest (newest at the end = processed first).
3. Updated issues go between the two groups.

### Step 6: Create the Sprint Run Record

1. Generate a run ID: `<YYYY-MM-DD>_<repo-name>_<platform>` (e.g., `2026-02-16_diagnostics_windows`).
2. If that ID already exists (multiple sprints same day), append `_2`, `_3`, etc.
3. Create `runs/<run_id>/run.json`:

```json
{
  "id": "<run_id>",
  "repo": "<owner/repo>",
  "platform": "<any|windows|linux|macos>",
  "started_at": "<ISO 8601 UTC>",
  "ended_at": null,
  "status": "in-progress",
  "scope": "<search query used>",
  "since": "<since date or null>",
  "queue": [1234, 1235, 1240, ...],
  "queue_original_size": 47,
  "processed": [],
  "stats": {
    "new_issues": 35,
    "updated_issues": 5,
    "platform_unblocked": 7,
    "already_done": 120,
    "total_open": 165
  }
}
```

4. Create `runs/<run_id>/log.md` with a human-readable sprint plan.

### Step 7: Commit and Report

1. Commit the new run files to the triage repo.
2. Push to the remote. If the push fails (e.g., remote is ahead), ask the user whether to rebase and retry or skip the push.
3. Display a summary to the user:

```
Sprint created: 2026-02-16_diagnostics_windows
Repository: dotnet/diagnostics
Platform: windows
Since: 2026-01-15 (last sprint)

Queue: 47 issues to process
  - 35 new issues
  - 5 updated since last triage
  - 7 platform-unblocked (were linux-blocked, now on linux)
  
Already triaged: 120 issues (unchanged, skipped)

Ready to go! Run: "triage the next issue" or "run the triage loop"
```

## Validation

- [ ] `runs/<run_id>/run.json` exists with valid queue
- [ ] `runs/<run_id>/log.md` exists
- [ ] Queue does not contain already-triaged unchanged issues
- [ ] Platform-blocked issues are correctly identified
- [ ] Sprint record committed to triage repo

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Repo not in config | Run `rt-add-repo` first |
| Massive queue on first run | Consider adding `scope` to filter by label/area |
| Date parsing issues | Always use ISO 8601 format |
| Duplicate sprint IDs | Auto-append `_2`, `_3`, etc. |
