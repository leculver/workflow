# Summary Format Reference

## Section Order

The summary follows this exact section order:

1. **Overview** — Stats table with counts
2. **Changes Since Last Summary** — What's new (only if a prior summary exists)
3. **Open Pull Requests** — All open PRs with linked issues
4. **Issues That Should Be Closed** — Stale, already-fixed, by-design, etc.
5. **Blocked Issues** — Issues blocked on external dependencies, upstream fixes, or unreleased packages
6. **Area sections** — One section per area (e.g., SOS, dotnet-dump), sorted by issue count descending. Only issues NOT in the "should close", "blocked", or "docs" sections.
7. **Documentation Issues** — All docs issues in a single flat table (not split by area)

## Full Template

```markdown
# <Repo> Issues Summary

*Generated: <YYYY-MM-DD>*

## Overview

| Metric | Count |
|--------|-------|
| Total Issues Analyzed | N |
| 🔵 Open | N |
| 🔴 Closed | N |
| ✅ Have Fix Candidate | N |
| 🔍 Manually Investigated | N |
| Should Be Closed | N |
| Blocked | N |
| Documentation Issues | N |

## Changes Since Last Summary

- N new issues triaged
- N new fix candidates

## Open Pull Requests

| PR | Author | Title | Linked Issues |
|----|--------|-------|---------------|
| [#NNN](url) | author | title | [#N](url), ... |

## Issues That Should Be Closed (N issues open, M already closed)

| Issue | GitHub | Title | State | Act | Assignees | Open PR | Fix | 🔍 | Status | Summary |
|-------|--------|-------|-------|-----|-----------|---------|-----|-----|--------|---------|
| [N](path) | [#N](url) | title | 🔵 Open | 🟡 | user1, user2 | | | | status | reason |

(Only list issues that are still open on GitHub. Omit already-closed issues.)

## Blocked Issues (N issues)

| Issue | GitHub | Title | State | Act | Assignees | Blocked On | Summary |
|-------|--------|-------|-------|-----|-----------|------------|---------|
| [N](path) | [#N](url) | title | 🔵 Open | ⚪ | user1 | [reason](url) | summary |

(Issues blocked on external dependencies, upstream fixes, or unreleased packages. Not actionable until the blocker resolves.)

## <Area Name> (N issues)

(same table format, one section per area, sorted by count desc)

## Documentation Issues

(same table format, single combined section — not split by area)
```

## Table Rules

- CRITICAL: No blank line between header separator row (`|---|---|...`) and the first data row.
- Use 🔵 Open / 🔴 Closed for state (accessibility: avoid red/green, user is colorblind).
- Use ✅ for fix candidates.
- Use 🔍 for manually investigated issues.
- Escape `|` in titles with `&#124;`.
- Truncate summary to first sentence, max 150 chars.
