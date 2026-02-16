# Triage Categories

## triage.category

| Value | Meaning |
|-------|---------|
| `bug` | Reported defect |
| `feature-request` | Enhancement/suggestion |
| `question` | User needs help, not a bug |
| `docs` | Documentation issue |

## triage.status

| Value | Meaning |
|-------|---------|
| `reproduced` | Confirmed the bug |
| `not-reproduced` | Tried but couldn't trigger it |
| `needs-info` | Can't reproduce, issue lacks detail |
| `platform-blocked` | Requires a different OS to reproduce |
| `stale` | Issue is outdated or no longer applies |
| `already-fixed` | The fix landed since the issue was filed |
| `already-implemented` | Feature request already exists |
| `still-relevant` | Feature request is valid and unaddressed |
| `by-design` | Behavior is intentional |
| `duplicate` | Duplicate of another issue |
| `wont-fix` | Valid but not worth fixing |
| `error` | Our automation hit an internal failure |

## triage.staleness

| Value | Meaning |
|-------|---------|
| `active` | Issue is current |
| `stale` | Issue is outdated |
| `superseded` | Replaced by another issue (set `superseded_by`) |

## triage.requires_platform

Array of one or more: `windows`, `linux`, `macos`
