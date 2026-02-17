---
name: user-recent-prs
description: >
  Fetches the authenticated user's recent pull requests from GitHub and writes a sorted markdown table
  to a specified file. Can create a new file or append only new PRs to an existing one. Extracts linked
  issues from PR titles and bodies. Use when you want a quick recap of your recent PR activity across repos.
---

# User Recent PRs

Query GitHub for the authenticated user's recent pull requests and produce a markdown summary table.

## When to Use

- Building a recap of your recent PR activity
- Populating a status report or diagnostics notes file
- Updating an existing file with only the PRs created since it was last generated

## When Not to Use

- Searching for PRs by other authors (use GitHub search tools directly)
- Triaging or investigating issues (use `rt-triage-issue`)

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| user | No | GitHub username to query. If omitted, resolves from `git config user.email` / `user.name`. |
| since | Yes | Start date for the query in ISO 8601 format (e.g., `2026-02-02`) or a natural-language duration (e.g., `2 weeks ago`). Only PRs created on or after this date are included. |
| output | Yes | Absolute path to the markdown file to write or update (e.g., `D:\git\work\notes\2026_02_16_diag.md`). |

## Workflow

### Step 0: Ensure Triage Repo Is Up to Date

If you have not already fetched and pulled the triage repo during this session, do so now:

1. `git fetch` and `git pull` in the triage repo root (`D:\git\work`).
2. If you have already done this earlier in the session (or remember doing so), skip this step.

### Step 1: Resolve the GitHub Username

1. If `user` input is provided, use it directly as the GitHub login.
2. Otherwise, run `git config user.email` to get the local email.
3. Use `search_users` to find the GitHub login matching that email or name.
4. If no match, fall back to `git config user.name` and search again.

### Step 2: Fetch Pull Requests

1. Use `search_pull_requests` with query `author:<login> created:>=<since>`, sorted by `created` ascending, `perPage: 100`.
2. If results are paginated (more than 100), fetch subsequent pages until all PRs are collected.
3. For each PR, extract:
   - **Repo**: Derive `owner/repo` from the PR's `html_url`.
   - **Number**: The PR number.
   - **Title**: The PR title.
   - **Created date/time**: `YYYY-MM-DD HH:MM` in UTC, used for both sorting and the Timestamp column.

### Step 3: Extract Linked Issues

For each PR, scan the **title** and **body** for issue references:

| Pattern | Example | Result |
|---------|---------|--------|
| `fixes #N`, `closes #N`, `resolves #N`, `issue #N` | `fixes #123` | `[#123](https://github.com/owner/repo/issues/123)` (same repo) |
| `(#N)` in title or body | `Fix foo (#123)` | `[#123](https://github.com/owner/repo/issues/123)` (same repo) |
| `fixes owner/repo#N` | `fixes dotnet/runtime#456` | `[dotnet/runtime#456](https://github.com/dotnet/runtime/issues/456)` |
| `https://github.com/owner/repo/issues/N` | URL in body | `[#N](URL)` if same repo, `[owner/repo#N](URL)` if different |

**Deduplication**: Remove duplicate references. Filter out self-references where the issue number equals the PR number within the same repo.

**Format**: Render each reference as a markdown link. Use `[#N](https://github.com/owner/repo/issues/N)` for same-repo issues. Use `[owner/repo#N](https://github.com/owner/repo/issues/N)` for cross-repo references. PR numbers are also linked: `[#N](https://github.com/owner/repo/pull/N)`.

### Step 4: Fetch Status for Issues and PRs

For each linked issue, use `issue_read` (method: `get`) to determine its state. For each PR, use `pull_request_read` (method: `get`) to determine its state and whether it was merged.

**Status icons** (colorblind-friendly, no color dependency):

| Item | State | Icon | Meaning |
|------|-------|------|---------|
| Issue | Open | 🟢 | Issue is open |
| Issue | Closed as completed/fixed | ☑️ | Issue closed as completed |
| Issue | Closed for other reason | ⚪ | Issue closed not-planned / won't fix / other |
| PR | Open | 🟢 | PR is open |
| PR | Merged | ☑️ | PR was merged |
| PR | Closed without merge | ⛔ | PR closed without merging |

Append the icon directly after the link text, inside the markdown link's display portion. Examples:
- `[#42 ☑️](https://github.com/owner/repo/issues/42)`
- `[#123 ☑️](https://github.com/owner/repo/pull/123)`

To determine issue close reason: check the `state_reason` field from the GitHub API. If `state_reason` is `completed`, use ☑️. If `state_reason` is `not_planned` or any other closed reason, use ⚪.

### Step 5: Sort Results

Sort all PRs by **Created date** ascending (oldest first).

### Step 6: Check for Existing Content

1. If `output` file exists and is non-empty:
   a. Parse the existing markdown table to find PR numbers already present.
   b. Filter the fetched PRs to only those **not** already in the file.
   c. If no new PRs, report that the file is already up to date and stop.
   d. Otherwise, proceed to append only the new rows.
2. If the file does not exist or is empty, generate the full table.

### Step 7: Write Output

**New file or empty file** — Write a complete markdown table:

```markdown
# Pull requests from <login> since <since>

| Timestamp | Repo | Issues Linked | PR# | PR Title |
|-----------|------|---------------|-----|----------|
| 2026-02-14 19:35 | owner/repo | [#42 ☑️](https://github.com/owner/repo/issues/42), [owner2/repo2#99 🟢](https://github.com/owner2/repo2/issues/99) | [#123 ☑️](https://github.com/owner/repo/pull/123) | Fix the thing |

Fetched at 2026-02-16 19:05 UTC. Covers 2026-02-02 to 2026-02-16.
```

**Existing file with content** — Append new rows to the end of the existing table. Do **not** rewrite the header or title. Insert new rows sorted into the correct position by date, or append at the end if all new PRs are newer than existing ones. Update the footer with the new fetch time and date range. Maintain the same column format.

After writing, display a summary: how many PRs were written (total and new), across how many repos.

## Validation

- [ ] All PRs from the queried date range appear in the output
- [ ] PRs are sorted by created date ascending (oldest first)
- [ ] Timestamp column shows `YYYY-MM-DD HH:MM` in UTC
- [ ] Linked issues are markdown links: `[#N icon](url)` for same-repo, `[owner/repo#N icon](url)` for cross-repo
- [ ] PR numbers are markdown links with status icon to the pull request page
- [ ] Status icons are correct: 🟢 open, ☑️ closed-completed, ⚪ closed-other for issues; 🟢 open, ☑️ merged, ⛔ closed-unmerged for PRs
- [ ] Self-references (PR# == issue#) are excluded from Issues Linked
- [ ] Existing file rows are preserved; only new PRs are appended
- [ ] Table renders correctly as markdown

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| GitHub username not found from email | Fall back to `git config user.name` search |
| PR body is null or empty | Treat as no linked issues; don't error |
| Pagination missed | Always check `total_count` and fetch additional pages if `items` < total |
| Duplicate issue refs in body | Deduplicate before writing |
| Self-referencing issue number | Exclude refs where issue# == PR# in same repo |
| `|` in PR titles | Escape as `&#124;` in the markdown table |
| Appending to malformed table | Parse conservatively; if table can't be parsed, append after last line |
| API rate limits fetching statuses | Batch requests by repo; use parallel calls where possible |
| Issue `state_reason` missing | Older issues may lack `state_reason`; treat closed without `state_reason` as ⚪ |
