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
| `blocked` | Issue is understood but blocked on an external dependency, upstream fix, or unreleased package. Use `blocked_reason` and `blocked_url` to explain what it's waiting on. |
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

## triage.actionability

Derived from `status`, `fix.has_candidate`, and `requires_platform`. Do not set manually — compute it during triage.

| Rating | Criteria |
|--------|----------|
| **High** 🔴 | `status=reproduced` AND `fix.has_candidate=true` |
| **Medium** 🟡 | `status=reproduced` AND `fix.has_candidate=false` |
| **Medium** 🟡 | `status=still-relevant` (feature request, unaddressed) |
| **Medium** 🟡 | `status=not-reproduced` (worth retrying) |
| **Medium** 🟡 | `status=platform-blocked` AND `requires_platform` includes `windows` or `linux` (we have these machines) |
| **Low** ⚪ | `status=platform-blocked` AND `requires_platform` is only `macos`, `arm`, `arm64`, or other (we don't have these) |
| **Low** ⚪ | `status=needs-info` |
| **Low** ⚪ | `status=blocked` |
| **Low** ⚪ | `status=stale` |
| **Low** ⚪ | `status=already-fixed` |
| **Low** ⚪ | `status=already-implemented` |
| **Low** ⚪ | `status=by-design` |
| **Low** ⚪ | `status=duplicate` |
| **Low** ⚪ | `status=wont-fix` |
| **Low** ⚪ | `status=error` |

## triage.requires_platform

Array of one or more: `any`, `windows`, `linux`, `macos`

- Use `["any"]` when the issue is not platform-specific and should reproduce everywhere.
- Use specific platforms (e.g., `["linux"]`, `["windows", "linux"]`) when reproduction requires those platforms.
- Do NOT combine `any` with specific platforms — if it's `any`, that's the only entry.
