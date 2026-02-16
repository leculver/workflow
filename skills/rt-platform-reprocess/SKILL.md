---
name: rt-platform-reprocess
description: >
  Finds and reprocesses issues that were marked platform-blocked on a different OS. Scans existing triage
  reports for issues requiring the current platform, builds a targeted queue, and re-triages them with
  full context from the prior platform pass. Use when switching from Windows to Linux (or vice versa)
  to pick up issues that couldn't be investigated before.
---

# Platform Reprocess

Re-triage platform-blocked issues now that you're on the right OS.

## When to Use

- Switching from Windows to Linux to process linux-blocked issues
- Switching from Linux to Windows to process windows-blocked issues
- After setting up a new platform environment
- When an issue's platform requirements change

## When Not to Use

- First-time triage (use `rt-sprint-setup` + `rt-triage-issue`)
- General re-triage of all issues (use `rt-sprint-setup` with appropriate scope)

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| repo | Yes | Repository in `owner/repo` format |
| platform | No | Target platform override (default: auto-detect current OS) |
| include_partial | No | Also include issues that have a platform component but weren't fully blocked (default: false) |
| workspace | No | Path to workspace root (default: parent of triage repo) |

## Workflow

### Step 1: Detect Platform

1. Auto-detect current platform: `windows`, `linux`, or `macos`.
2. If `platform` override is provided, use that instead.
3. Read `config/repos.json` for the repo configuration.

### Step 2: Scan for Platform-Blocked Issues

1. Read all `issues/<owner>-<repo>/*/report.json` files.
2. Collect issues matching these criteria:
   - `triage.status == "platform-blocked"` AND `triage.requires_platform` contains current platform
   - OR (if `include_partial`): `triage.requires_platform` contains current platform, regardless of status

3. For each candidate, also check:
   - Is the GitHub issue still open? (Skip closed issues unless they need verification.)
   - Was this issue already processed on the current platform? Check `log.md` for platform-specific session entries.

### Step 3: Build Platform Queue

1. Create a targeted queue of issue numbers.
2. Order: purely platform-blocked first (most actionable), then partial-platform issues.
3. Report the queue size:

```
Platform reprocess: linux
Repository: dotnet/diagnostics

Found 7 platform-blocked issues needing linux:
  #1031  dotnet-dump on Alpine Linux              [platform-blocked → linux]
  #1145  lldb SOS plugin crashes on Ubuntu         [platform-blocked → linux]
  ...

Found 3 additional issues with linux component:
  #5632  Detect createdump dumps in SOS            [reproduced, needs linux verification]
  ...

Total: 10 issues to reprocess. Proceed?
```

### Step 4: Create Platform Sprint

1. Create a sprint run specifically for platform reprocessing:
   - Run ID: `<date>_<repo>_<platform>_reprocess`
   - Set `scope` to indicate this is a platform reprocess run.
2. Write `runs/<run_id>/run.json` with the platform queue.

### Step 5: Process Issues

For each issue in the queue, invoke the `rt-triage-issue` workflow with these modifications:

**Context preservation:**
- Read the existing `report.json` from the prior platform pass.
- Preserve all prior observations — append, don't replace.
- Keep prior reproduction steps in the JSON (prefix with `[<prior platform> pass]`).
- Add new steps prefixed with `[<current platform> pass]`.

**Status update:**
- Update `triage.status` to reflect the new platform result.
- Update `environment.os` to the current platform.
- If the issue was `platform-blocked` and is now reproduced, the status becomes `reproduced`.
- If it's still blocked (e.g., needs macOS and we're on linux), keep `platform-blocked` but update `requires_platform`.

**Report update:**
- In `report.md`, add a `## <Platform> Pass` section with new findings.
- Clearly mark what's from this pass vs. prior passes.

### Step 6: Commit and Report

1. Commit each processed issue: `platform-reprocess: <owner>/<repo>#<number> — <status> (<platform>)`
2. When queue is empty:
   - Mark the platform sprint as completed.
   - Show summary:

```
Platform reprocess complete: linux
  Processed: 10 issues
  Results: 4 reproduced, 2 already-fixed, 1 needs-info, 3 still platform-blocked (macos)
```

## Validation

- [ ] Prior observations preserved in updated reports
- [ ] New observations clearly marked with platform prefix
- [ ] Status correctly updated for platform-specific findings
- [ ] `environment.os` reflects current platform
- [ ] Source repos back on main branch
- [ ] All results committed

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Overwriting prior platform's work | Always append to observations, never replace |
| Issue closed since last triage | Check GitHub state before processing |
| Missing repo checkout on new platform | Verify local paths exist in Step 1 |
| macOS issues on Linux | Keep platform-blocked, update requires_platform to just `macos` |
