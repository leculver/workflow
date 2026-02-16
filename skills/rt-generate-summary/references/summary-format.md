# Summary Format Reference

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
| Documentation Issues | N |

## Open Pull Requests

| PR | Author | Title | Linked Issues |
|----|--------|-------|---------------|
| [#NNN](url) | author | title | [#N](url), ... |

## Issues That Should Be Closed

| Issue | GitHub | Title | State | Open PR | Fix | 🔍 | Status | Summary |
|-------|--------|-------|-------|---------|-----|-----|--------|---------|
| [N](path) | [#N](url) | title | 🔵 Open | | | | status | reason |

## Documentation Issues

(same table format)

## <Area Name> (N issues)

(same table format, one section per area, sorted by count desc)

## Changes Since Last Summary

- N new issues triaged
- N issues changed status
- N new fix candidates
```

## Table Rules

- CRITICAL: No blank line between header separator row (`|---|---|...`) and the first data row.
- Use 🔵 Open / 🔴 Closed for state (accessibility: avoid red/green).
- Use ✅ for fix candidates.
- Use 🔍 for manually investigated issues.
- Escape `|` in titles with `&#124;`.
- Truncate summary to first sentence, max 150 chars.
