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
| repo | No | Repository in `owner/repo` format. If omitted, check if there's only one configured repo with triaged issues — use that. If multiple, ask the user. |
| format | No | `full` (default) or `brief` (stats only) |
| output | No | Output path override (default: `summaries/<repo>/<date>.md`) |

## Implementation Strategy

**Use the reference Python script**, not PowerShell loops or inline `python -c`.

The generation involves reading hundreds of JSON files, classifying issues, and building markdown tables. PowerShell `ConvertFrom-Json` in a loop is extremely slow for this and will hang. Python f-strings with inline quoting also cause issues in `-c` mode.

Instead:
1. Use PowerShell/tools to **gather data** (glob report.json files, fetch PRs via GitHub MCP).
2. Write two temp JSON files: one for reports, one for PRs.
3. Run [generate-summary.py](references/generate-summary.py) with the repo, triage root, and those temp files as arguments.
4. Clean up temp files.

## Workflow

### Step 0: Bookkeeping

Invoke `rt-bookkeeping` to pull the triage repo and flush any pending `.progress/` from prior sessions.

### Step 1: Select Repository

1. If `repo` is provided, use it.
2. If not, read `config/repos.json` and check which repos have triaged issues (glob `issues/<owner>-<repo>/*/report.json`).
3. If only one repo has issues, use that.
4. If multiple, ask the user which repo to summarize.

### Step 2: Read All Issue Reports

1. Glob for `issues/<owner>-<repo>/*/report.json` in the triage repo.
2. **Use a single Python script to process all reports** — do NOT loop over JSON files in PowerShell (it's too slow for hundreds of files).
3. For each report, extract:
   - `issue.number`, `issue.title`, `issue.state`, `issue.url`, `issue.labels`, `issue.assignees`
   - `issue.manually_investigated`
   - `triage.category`, `triage.status`, `triage.status_reason`, `triage.affected_repo`
   - `triage.staleness`, `triage.requires_platform`
   - `fix.has_candidate`
3. Check which `report.md` files exist for linking.
4. Truncate `status_reason` to first sentence, cap at 150 chars.

### Step 3: Fetch Open PRs

1. Use GitHub MCP tools: `list_pull_requests` for the repo, state=open, perPage=100.
2. Extract PR number, title, author, html_url.
3. Parse PR bodies AND titles for linked issues using ALL these patterns:
   - `fixes #N`, `closes #N`, `resolves #N` (case-insensitive)
   - `(#N)` in title
   - `https://github.com/<owner>/<repo>/issues/N` (full URL in body)
   - Bare `#N` references in the body (but only if N is a plausible issue number)
4. Build a map: `{issue_number: [pr_numbers]}` and PR details.
5. Write to a temp JSON file for the Python script: `[{"number": N, "url": "...", "title": "...", "author": "...", "linked_issues": [N, ...]}, ...]`

### Step 4: Categorize Issues into Sections

**Section 1 — Should Be Closed:**
Issues with status in: `already-fixed`, `already-implemented`, `by-design`, `stale`, `wont-fix`, `duplicate`.
Count how many of these are still open vs already closed on GitHub. Display the header as:
`## Issues That Should Be Closed (N issues open, M already closed)`
Only list the **still-open** issues in the table. Omit already-closed issues from the display since they need no action.

**Section 2 — By Area:**
Everything else (not in Section 1, not docs), classified using the area rules from `config/repos.json`. Sort area subsections by issue count descending. Issues not matching any area go in "Other / General".

**Section 3 — Documentation Issues:**
Issues with category `docs` that are NOT in Section 1. Single combined table (not split by area).

### Step 5: Generate Markdown

Use this table format for all sections:

```
| Issue | GitHub | Title | State | Act | Assignees | Open PR | Fix | 🔍 | Status | Summary |
```

Column details:
- **Issue**: Link to local `report.md` (relative path from the summary file, e.g., `../../issues/<owner>-<repo>/<N>/report.md`)
- **GitHub**: Link to the GitHub issue page
- **Title**: Issue title (escape `|` as `&#124;`)
- **State**: 🔵 Open / 🔴 Closed (use blue/red for colorblind accessibility)
- **Act**: Actionability — 🔴 High / 🟡 Medium / ⚪ Low (derived from `triage.actionability`)
- **Assignees**: Comma-separated GitHub usernames from `issue.assignees`
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

### Step 6: Compare with Previous Summary

1. Find the most recent dated summary (e.g., `2026-02-16.md`) in `summaries/<owner>-<repo>/`.
2. If one exists, extract issue numbers from it (parse `[#N](url)` links) and diff against current issue numbers:
   - How many **new** issues since last summary
   - How many **new fix candidates** among the new issues
3. Do NOT attempt to detect status changes — that requires the old report.json data which we don't snapshot. Just diff the issue number sets.

### Step 7: Run the Script and Write Output

1. Write the reports data to a temp JSON file: `[{"number": N, "has_report_md": bool, "data": <report.json>}, ...]`
2. Run the reference script:
   ```
   python <triage_root>/.agents/skills/rt-generate-summary/references/generate-summary.py <owner/repo> <triage_root> <reports_tmp> <prs_tmp>
   ```
3. The script writes to `summaries/<owner>-<repo>/<YYYY-MM-DD>.md` and `summaries/<owner>-<repo>/latest.md`.
4. Clean up temp JSON files.
5. Optionally copy to a custom `output` path if provided.
6. Commit: `summary: <owner>/<repo> — <date> (<N> issues)`
7. Push to the remote. If the push fails (e.g., remote is ahead), ask the user whether to rebase and retry or skip the push.
8. Do NOT include `Co-authored-by: Copilot` in commit messages.

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
| PowerShell ConvertFrom-Json loop hangs | Do NOT loop over hundreds of JSON files in PowerShell — use the Python script |
| Python f-string quoting in `-c` mode | Do NOT use `python -c` with complex f-strings — write a temp `.py` file or use the reference script |
| No repo provided by user | Auto-detect from triaged issues; ask if ambiguous |
| "Status changed" diff requires old data | Only diff issue number sets between summaries, don't try to detect status changes |
