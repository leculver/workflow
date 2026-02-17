---
name: rt-bookkeeping
description: >
  Flushes in-progress investigation notes (.progress/) into captain's logs and reports, and pulls the
  triage repo. Called by other skills at startup, or standalone via "clean up", "flush progress", or
  "bookkeeping". Handles concurrent sessions gracefully via rename-before-flush.
---

# Bookkeeping

Pull the triage repo, then scan for and flush any `.progress/` directories across all issues.

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

### Step 2: Scan for .progress/ Directories

1. Glob for `issues/*/.progress/*.md` across all issue directories (or filtered to `repo` if provided).
2. If none found, stop — nothing to flush. Report "No pending progress to flush."

### Step 3: Flush Each Issue's Progress

For each issue directory that has a `.progress/` folder with `.md` files:

**a) Claim the files (rename before reading):**

For each `.md` file in `.progress/`:
1. Rename it from `<name>.md` to `<name>.flushing.md`.
2. If the rename fails (file doesn't exist), another session already claimed it. Skip it silently.

**b) Read and aggregate:**

1. Read all `.flushing.md` files in chronological order (sort by filename, which is timestamp-based).
2. Combine their contents into a single session block.

**c) Append to captain's log:**

1. Read the existing `log.md` for this issue.
2. Append a new session entry:
   ```markdown
   ## <current ISO 8601 timestamp> — <platform> — flushed from .progress/

   <combined contents of all .flushing.md files, in order>
   ```
3. Write `log.md`.

**d) Update report.json if applicable:**

1. Read the existing `report.json`.
2. If any `.flushing.md` file contains structured updates (status changes, new observations, fix info), apply them.
3. Most progress notes are freeform — don't force-parse them. Only update `report.json` if there are clear, explicit status changes noted in the progress.
4. Write atomically (`.tmp` then rename).

**e) Clean up:**

1. Delete all `.flushing.md` files.
2. If `.progress/` is now empty, leave the empty directory (it's gitignored anyway).

### Step 4: Commit

If any log.md or report.json files were updated:

1. `git add` the changed files.
2. Commit: `bookkeeping: flush progress for <owner>/<repo>#<number>` (one commit per issue, or batch if multiple).
3. Push to origin.

Do NOT include `Co-authored-by: Copilot` in commit messages.

## Concurrent Session Safety

Multiple Copilot sessions may be running simultaneously. The rename-before-flush pattern provides lightweight coordination:

- **Writer (rt-load-issue):** Appends to `.progress/<timestamp>.md`. If the file disappeared (was renamed by a flush), the writer should create a new `.progress/<new-timestamp>.md` and continue. No data is lost — the old content was already claimed by the flusher.
- **Flusher (this skill):** Renames `.md` → `.flushing.md` before reading. If the rename fails, another flusher got there first. Skip and move on.
- **No locking required.** Worst case: a progress note written between rename and delete is lost. This is acceptable — these are investigation notes, not transactions.
- **Partial flushes are fine.** If this skill crashes mid-flush, `.flushing.md` files remain on disk. The next bookkeeping run will pick them up and finish the job.

## Validation

- [ ] All `.progress/*.md` files were renamed before reading
- [ ] Contents appended to `log.md` (not overwriting prior entries)
- [ ] `.flushing.md` files deleted after successful append
- [ ] Changes committed and pushed
- [ ] No interference with concurrent sessions writing to .progress/

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| File disappeared during rename | Another session flushed it — skip silently |
| `.flushing.md` files left behind from crash | Pick them up on next run — they're already claimed |
| Overwriting log.md | Always append, never overwrite |
| Committing .progress/ files | `.progress/` is in `.gitignore` — only `log.md` and `report.json` are committed |
| Large number of issues with progress | Batch commits if flushing more than 3 issues |
