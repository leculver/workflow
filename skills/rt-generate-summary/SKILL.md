---
name: rt-generate-summary
description: >
  Generates a triage summary dashboard from all issue reports for a repository. Produces a timestamped
  markdown summary with tables grouped by status and area, links to reports and GitHub issues, and PR
  cross-references. Shows diff from previous summary. Use after a triage sprint or anytime you want a
  status overview.
---

# Generate Summary

Build a comprehensive triage summary dashboard from all issue report data.

## When to Use

- After completing a triage sprint
- When you want an overview of all triaged issues
- To generate a shareable status report
- To see what changed since the last summary

## When Not to Use

- Querying status of a single issue (use `rt-triage-status`)
- Triaging issues (use `rt-triage-issue`)

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| repo | Yes | Repository in `owner/repo` format |
| format | No | `full` (default) or `brief` (stats only) |
| output | No | Output path override (default: `summaries/<repo>/<date>.md`) |

## Workflow

### Step 0: Bookkeeping

Invoke `rt-bookkeeping` to pull the triage repo and flush any pending `.progress/` from prior sessions.

### Step 1: Read All Issue Reports

1. Glob for `issues/<owner>-<repo>/*/report.json` in the triage repo.
2. For each report, extract:
   - `issue.number`, `issue.title`, `issue.state`, `issue.url`, `issue.labels`
   - `issue.manually_investigated`
   - `triage.category`, `triage.status`, `triage.status_reason`, `triage.affected_repo`
   - `triage.staleness`, `triage.requires_platform`
   - `fix.has_candidate`
3. Check which `report.md` files exist for linking.
4. Truncate `status_reason` to first sentence, cap at 150 chars.

### Step 2: Fetch Open PRs

1. Use GitHub MCP tools: `list_pull_requests` for the repo, state=open.
2. Extract PR number, title, author.
3. Parse PR bodies for linked issues using patterns: `fixes #N`, `closes #N`, `resolves #N`, and general `#N` references.
4. Build a map: `{issue_number: [pr_numbers]}` and PR details.

### Step 3: Categorize Issues into Sections

**Section 1 — Should Be Closed:**
Issues with status in: `already-fixed`, `already-implemented`, `by-design`, `stale`, `wont-fix`, `duplicate`.
Count how many of these are still open vs already closed on GitHub. Display the header as:
`## Issues That Should Be Closed (N issues open, M already closed)`
Only list the **still-open** issues in the table. Omit already-closed issues from the display since they need no action.

**Section 2 — By Area:**
Everything else (not in Section 1, not docs), classified using the area rules from `config/repos.json`. Sort area subsections by issue count descending. Issues not matching any area go in "Other / General".

**Section 3 — Documentation Issues:**
Issues with category `docs` that are NOT in Section 1. Single combined table (not split by area).

### Step 4: Generate Markdown

Use this table format for all sections:

```
| Issue | GitHub | Title | State | Act | Open PR | Fix | 🔍 | Status | Summary |
```

Column details:
- **Issue**: Link to local `report.md` (relative path from the summary file, e.g., `../../issues/<owner>-<repo>/<N>/report.md`)
- **GitHub**: Link to the GitHub issue page
- **Title**: Issue title (escape `|` as `&#124;`)
- **State**: 🔵 Open / 🔴 Closed (use blue/red for colorblind accessibility)
- **Act**: Actionability — 🔴 High / 🟡 Medium / ⚪ Low (derived from `triage.actionability`)
- **Open PR**: Link to PR if one exists for this issue
- **Fix**: ✅ if `fix.has_candidate` is true
- **🔍**: 🔍 if `manually_investigated` is true
- **Status**: Triage status value
- **Summary**: First sentence of `status_reason`, max 150 chars

Include before the issue sections (in this order):
1. **Overview stats table**: Total issues, open/closed counts, fix candidates, manually investigated, by-status breakdown.
2. **Changes Since Last Summary**: What's new since the prior summary (only if a prior summary exists). See Step 5.
3. **Open Pull Requests table**: All open PRs with linked issues.

See [summary format reference](references/summary-format.md) for the full template.

### Step 5: Compare with Previous Summary

1. Find the most recent existing summary in `summaries/<owner>-<repo>/`.
2. If one exists, compute a brief diff:
   - How many new issues since last summary
   - Issues whose status changed
   - New fix candidates
3. Append a "Changes Since Last Summary" section.

### Step 6: Write and Commit

1. Write to `summaries/<owner>-<repo>/<YYYY-MM-DD>.md`.
2. Also write/overwrite `summaries/<owner>-<repo>/latest.md` as a copy.
3. Optionally write to a custom `output` path if provided.
4. Commit: `summary: <owner>/<repo> — <date> (<N> issues)`
5. Push to the remote. If the push fails (e.g., remote is ahead), ask the user whether to rebase and retry or skip the push.

## Validation

- [ ] Summary file exists and has proper markdown table formatting
- [ ] No blank lines between table header separator and first data row
- [ ] All issue numbers in reports appear in the summary
- [ ] PR cross-references are accurate
- [ ] Timestamped copy saved in `summaries/`
- [ ] Committed to triage repo

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Blank line in markdown table | Ensure no `\n\n` between header separator and first row |
| `|` in issue titles | Escape as `&#124;` |
| Large PR list | Paginate the GitHub API call (perPage=100) |
| Missing report.md links | Check file existence before linking |
