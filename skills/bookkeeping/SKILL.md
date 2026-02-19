---
name: bookkeeping
description: >
  Flushes in-progress investigation notes (.bookkeeping/) into captain's logs and reports, checks
  deletion reminders, and pulls the triage repo. Called by other skills at startup, or standalone
  via "clean up", "flush progress", or "bookkeeping". Handles concurrent sessions gracefully via
  rename-before-flush.
---

# Bookkeeping

Pull the triage repo, run the bookkeeping processor, flush logs, and check deletion reminders.

## When to Use

- **Automatically** — every other skill should invoke this as its Step 0 instead of doing its own git pull.
- **Manually** — user says "clean up", "flush progress", "bookkeeping", or "save all progress".

## When Not to Use

- This skill is infrastructure. There's no reason to skip it.

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| repo | No | Limit flush to a specific repo in `owner/repo` format (default: all configured repos) |

## Workflow

### Step 1: Pull Triage Repo

1. `git fetch` and `git pull` in the triage repo root.
2. If you have already done this earlier in the session (or remember doing so), skip this step.

### Step 1.5: Ensure config/user.json

1. Check if `config/user.json` exists in the triage repo root.
2. If missing, generate it by running: `gh api user --jq '{login: .login, name: .name}'` and writing the output to `config/user.json`.
3. If it already exists, skip this step.

This file is gitignored (machine-specific) and provides the GitHub username for skills that need it (e.g., generate-summary filters PRs by author).

### Step 2: Run Bookkeeping Processor

Run the Python script to scan for `.log` and `.delete` files in one pass:

```
python .agents/skills/bookkeeping/scripts/bookkeeping.py <repo_root> [--issues-only <owner-repo>]
```

Pass `--issues-only <owner-repo>` if `repo` input was provided (converted to `owner-repo` format with hyphen).

The script handles:
- **`.log` files** in per-issue `.bookkeeping/` directories — renames to `.flushing.log` (claim-before-read), reads content, returns structured data.
- **`.delete` files** in root `.bookkeeping/` — checks for expired deletion reminders and returns any that are past due.

The script outputs JSON to stdout with two sections: `logs` and `expired_deletions`.

### Step 3: Process Log Results

If the script returned any `logs` entries:

For each issue in the `logs` array:

**a) Append to captain's log:**

1. Read the existing `log.md` for this issue.
2. Append a new session entry:
   ```markdown
   ## <current ISO 8601 timestamp> — <platform> — flushed from .bookkeeping/

   <combined contents of all .log files for this issue, in chronological order>
   ```
3. Write `log.md`.

**b) Update report.json if applicable:**

1. Read the existing `report.json`.
2. If any log file contains structured updates (status changes, new observations, fix info), apply them.
3. Most progress notes are freeform — don't force-parse them. Only update `report.json` if there are clear, explicit status changes noted in the progress.
4. Write atomically (`.tmp` then rename).

**c) Clean up:**

1. Delete all `.flushing.log` files (paths are in the script output).
2. If `.bookkeeping/` is now empty, leave the empty directory (it's gitignored anyway).

### Step 4: Process Deletion Reminders

If the script returned any `expired_deletions` entries:

For each expired item, **ask the user** whether to delete it. Present:
- The path to the file/directory
- When it was ingested (`ingested_at`)
- When the reminder was due (`delete_after`)

Based on the user's response:
- **Delete**: Remove the file/directory and remove the entry from the corresponding `.delete` file in `.bookkeeping/`.
- **Extend**: Ask how long to extend, update `delete_after` in the `.delete` file.
- **Skip**: Do nothing — the reminder will fire again next time bookkeeping runs.

**Important:** Do NOT delete files without asking. This is a reminder system, not enforcement.

### Step 5: Commit

If any log.md or report.json files were updated:

1. `git add` the changed files.
2. Commit: `bookkeeping: flush progress for <owner>/<repo>#<number>` (one commit per issue, or batch if multiple).
3. Push to origin.

Do NOT include `Co-authored-by: Copilot` in commit messages.

## Concurrent Session Safety

Multiple Copilot sessions may be running simultaneously. The rename-before-flush pattern provides lightweight coordination:

- **Writer (load-issue):** Appends to `.bookkeeping/<timestamp>.log`. If the file disappeared (was renamed by a flush), the writer should create a new `.bookkeeping/<new-timestamp>.log` and continue. No data is lost — the old content was already claimed by the flusher.
- **Flusher (this skill):** The Python script renames `.log` → `.flushing.log` before reading. If the rename fails, another flusher got there first. Skip and move on.
- **No locking required.** Worst case: a progress note written between rename and delete is lost. This is acceptable — these are investigation notes, not transactions.
- **Partial flushes are fine.** If this skill crashes mid-flush, `.flushing.log` files remain on disk. The next bookkeeping run will pick them up and finish the job.

## `.delete` File Format

`.delete` files live in the root `.bookkeeping/` directory (e.g., `.bookkeeping/dumps.delete`). Each is a JSON array of tracked items:

```json
[
  {
    "path": "D:\\work\\dumps\\2026-02-19_crash-analysis.dmp",
    "ingested_at": "2026-02-19T16:00:00Z",
    "file_timestamp": "2026-02-18T10:30:00Z",
    "delete_after": "2026-03-19T16:00:00Z"
  }
]
```

Fields:
- `path` — absolute path to the file or directory to delete
- `ingested_at` — when the item was added to tracking
- `file_timestamp` — creation/modification time of the file at time of ingestion
- `delete_after` — timestamp after which the reminder fires (checked by the Python script)

Items with no `delete_after` (retained forever) should not be added to `.delete` files at all.

## Validation

- [ ] All `.bookkeeping/*.log` files were renamed before reading (handled by Python script)
- [ ] Contents appended to `log.md` (not overwriting prior entries)
- [ ] `.flushing.log` files deleted after successful append
- [ ] Expired deletion reminders presented to user (not auto-deleted)
- [ ] Changes committed and pushed
- [ ] No interference with concurrent sessions writing to .bookkeeping/

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| File disappeared during rename | Another session flushed it — skip silently (handled by script) |
| `.flushing.log` files left behind from crash | Pick them up on next run — they're already claimed |
| Overwriting log.md | Always append, never overwrite |
| Committing .bookkeeping/ files | `.bookkeeping/` is in `.gitignore` — only `log.md` and `report.json` are committed |
| Large number of issues with progress | Batch commits if flushing more than 3 issues |
| Auto-deleting expired files | NEVER auto-delete — always ask the user first |
