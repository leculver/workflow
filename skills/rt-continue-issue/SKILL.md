---
name: rt-continue-issue
description: >
  Loads all prior context for a specific issue and enters interactive investigation mode. Reads the existing
  JSON report, markdown summary, reproduction artifacts, fix branches, and latest GitHub comments. Use when
  you want to do a deep dive on a previously triaged issue, continue debugging, or refine a fix.
---

# Continue Issue

Resume investigation on a previously triaged issue with full context loaded.

## When to Use

- Deep diving into a previously triaged issue
- Continuing debugging after initial automated triage
- Refining or testing a fix candidate
- Re-investigating after new comments appear on the issue

## When Not to Use

- First-time triage of an issue (use `rt-triage-issue`)
- Batch processing (use `rt-triage-loop`)

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| issue_number | Yes | The issue number to continue working on |
| repo | No | Repository in `owner/repo` format (default: infer from existing reports) |
| workspace | No | Path to workspace root (default: parent of triage repo) |

## Workflow

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
- Read the captain's log at `issues/<owner>-<repo>/<issue_number>/log.md` to understand the full investigation arc across sessions.
- This is the best source of "what happened when" — read the whole thing.

**d) Existing Markdown report:**
- Read `issues/<owner>-<repo>/<issue_number>/report.md`.

**e) Reproduction folder:**
- Check if `<workspace>/repros/issue_<issue_number>/` exists.
- If so, inventory its contents: repro apps, dumps, artifacts, logs, scripts.
- Understand what was already attempted.

**f) Fix branches:**
- Check if a branch named `issue_<issue_number>` exists in the source repo(s).
- If so, review the diff against main to understand the candidate fix.

**g) Open PRs:**
- Check for open PRs referencing this issue.

### Step 2: Present Context Summary

Before proceeding, present a clear summary:
- Current triage status and category
- What reproduction was attempted and the outcome
- Whether a fix candidate exists and its confidence level
- NEW: Any comments/activity since last triage
- What remains to be done or investigated

Ask the user what direction to take, or proceed with the most logical next step.

### Step 3: Continue Investigation

Based on prior work and current state, continue where we left off:

- **Not reproduced?** Try again with new approach, different inputs, or new information from comments.
- **Reproduced but no fix?** Deepen root cause analysis, attempt a fix.
- **Fix exists but low confidence?** Run more tests, refine the fix.
- **Platform-blocked?** If now on the right platform, attempt reproduction.
- **Stale/already-fixed?** Verify and update status if needed.
- **Feature request?** Check if implementation has landed since last check.

Follow the same [reproduction rules](../rt-triage-issue/references/reproduction-rules.md) and record all steps.

### Step 4: Update Reports with Versioning

**JSON update:**
- Overwrite `report.json` in place — it is always the current source of truth.
- Set `manually_investigated` to `true` (this was touched by a developer).
- Write atomically (`.tmp` then rename).

**Captain's log — append a new session entry to `log.md`:**
- Do NOT overwrite previous entries — append only.
- Add a new `## <timestamp> — <platform> — manual investigation` section.
- Record: what was attempted, what was discovered, what changed.
- Clearly distinguish new findings from prior work.

**Markdown update:**
- Overwrite `report.md` with the latest findings.
- Clearly mark what is NEW from this session vs. carried over from prior work.
- Use a `## Session: <date>` section header for new findings.

### Step 5: Commit

Commit with message: `continue: <owner>/<repo>#<number> — <summary of new findings>`

## Validation

- [ ] New session entry appended to `log.md` (not overwriting prior entries)
- [ ] `manually_investigated` set to `true`
- [ ] New observations appended (not replacing old ones)
- [ ] `report.md` clearly distinguishes new vs. prior work
- [ ] Source repos back on main branch
- [ ] Results committed to triage repo

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Overwriting prior work | `report.json` is overwritten (that's fine), but NEVER overwrite `log.md` — append only |
| Missing new GitHub comments | Compare `fetched_at_utc` with comment dates |
| Can't find the repo | Provide `repo` explicitly if auto-detection fails |
| Repro folder is huge | Don't re-read dumps or large artifacts — summarize what's there |
