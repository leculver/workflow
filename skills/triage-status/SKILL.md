---
name: triage-status
description: >
  Shows the current status of triage work: sprint progress, issue counts by status/category/area, fix
  candidates, platform-blocked items, and cross-sprint history. Use when you want a quick overview of
  where things stand, what needs attention, or filtering issues by criteria.
---

# Triage Status

Query and display the current state of triage work across sprints and repos.

## When to Use

- Checking how many issues are left in the current sprint
- Finding all reproduced bugs without fix candidates
- Getting a cross-sprint history view
- Finding issues that need attention (errors, platform-blocked, needs-info)
- Quick stats before generating a full summary

## When Not to Use

- Generating the full formatted summary dashboard (use `generate-summary`)
- Triaging issues (use `triage-issue`)

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| repo | No | Filter to a specific repo (default: all configured repos) |
| filter | No | Filter expression: status, category, or keyword (e.g., `reproduced`, `platform-blocked`, `has-fix`, `no-fix`, `needs-attention`) |
| sprint | No | Specific sprint run ID to query (default: latest for each repo) |
| detail | No | `stats` (default), `list` (show issue numbers and titles), or `full` (show status_reason too) |

## Workflow

### Step 0: Bookkeeping

Invoke `bookkeeping` to pull the triage repo and flush any pending `.progress/` from prior sessions.

### Step 1: Gather Data

1. Read `config/repos.json` to get the list of configured repos.
2. If `repo` is specified, filter to just that repo.
3. For each repo:
   a. Read all `issues/<owner>-<repo>/*/report.json` files.
   b. Read all sprint runs from `runs/` for this repo.

### Step 2: Compute Statistics

For each repo, compute:

```
Total issues triaged: N
By status:
  reproduced:        N  (N with fix, N without)
  not-reproduced:    N
  needs-info:        N
  platform-blocked:  N  (N windows, N linux, N macos)
  blocked:           N  (external dependency, upstream fix, unreleased package)
  stale:             N
  already-fixed:     N
  already-implemented: N
  still-relevant:    N
  by-design:         N
  duplicate:         N
  wont-fix:          N
  error:             N

By category:
  bug:              N
  feature-request:  N
  question:         N
  docs:             N

Fix candidates:     N / N total (N% of bugs)
Manually investigated: N
```

### Step 3: Sprint Status (if applicable)

If there's an active sprint:
```
Active Sprint: <run_id>
  Started:    <date>
  Queue:      N remaining of N original
  Processed:  N this sprint
  Last issue: #NNNN (<title>)
```

If `sprint` is specified, show that sprint's details.

### Step 4: Apply Filters

If `filter` is provided, show matching issues:

| Filter | Matches |
|--------|---------|
| `reproduced` | status == reproduced |
| `not-reproduced` | status == not-reproduced |
| `platform-blocked` | status == platform-blocked |
| `blocked` | status == blocked (external dependency, upstream fix) |
| `needs-attention` | status in (error, needs-info, platform-blocked) |
| `has-fix` | fix.has_candidate == true |
| `no-fix` | status == reproduced AND fix.has_candidate == false |
| `stale` | staleness == stale OR status == stale |
| `should-close` | status in (already-fixed, already-implemented, by-design, stale, wont-fix, duplicate) |
| Any other text | Search in title and status_reason |

### Step 5: Display Results

**`stats` detail level:** Show the statistics tables above.

**`list` detail level:** Add a list of matching issues:
```
#5632  Detect createdump collected dumps in SOS                [reproduced] [has-fix]
#5706  Terminal cursor visibility not restored on exit          [reproduced] [has-fix]
#3102  dotnet-dump analyze crashes on Alpine                    [reproduced] [investigating]
```

**`full` detail level:** Add the status_reason for each:
```
#5632  Detect createdump collected dumps in SOS
       Status: reproduced | Fix: 0.92 confidence | Branch: issue_5632
       Feature implemented and verified on native Linux...
```

### Step 6: Cross-Sprint History

If no specific sprint or repo filter, show the big picture:
```
Sprint History:
  dotnet/diagnostics:
    2026-02-14 windows  165 issues  completed
    2026-02-15 linux     27 issues  completed
    2026-02-16 windows   47 issues  in-progress (12 done, 35 remaining)
  microsoft/clrmd:
    2026-01-20 windows   45 issues  completed
```

## Validation

- [ ] Statistics are consistent (counts add up)
- [ ] Filters correctly match expected issues
- [ ] Active sprint status is accurate

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Stale data after triage | Re-read the JSON files, don't cache |
| Counting issues twice | Each issue appears once per repo, deduplicate by number |
