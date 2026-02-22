---
name: diagnose-and-fix
description: >
  Full-loop issue investigation: fetches a GitHub issue, classifies it, reproduces the bug, proposes a fix,
  runs targeted tests, and writes structured reports. Use when the user says "diagnose", "fix", "triage",
  "work on", or "investigate" an issue. Always attempts reproduction AND a fix — the goal is a working
  fix candidate, not just classification. Do NOT use when the user says "load", "continue", or "pick up"
  an issue — that is load-issue. Reads repo config from config/repos.json.
---

# Diagnose and Fix

Investigate a single GitHub issue end-to-end: classify, reproduce, fix, test, and report.

**The primary goal is a working fix candidate.** Classification is a preliminary step, not the finish line.
If you stop after classifying the issue without attempting reproduction and a fix, you have not completed this skill.

## When to Use

- Processing the next issue from a sprint queue
- Investigating a specific issue by number
- Re-investigating an issue after new information

## When Not to Use

- Continuing deep investigation on a previously triaged issue (use `load-issue`)
- Batch processing multiple issues (just run `diagnose-and-fix` repeatedly)

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| repo | Yes | Repository in `owner/repo` format (e.g., `dotnet/diagnostics`) |
| issue_number | No | Specific issue to investigate. If omitted, pick next from sprint queue. |
| workspace | No | Path to the workspace root where repo checkouts and repros live (default: parent of triage repo) |

## Workflow

### Step 0: Bookkeeping

Invoke `bookkeeping` to pull the triage repo and flush any pending `.bookkeeping/` logs from prior sessions.

### Step 1: Load Configuration

1. Read `config/repos.json` from the triage repo root.
2. Find the entry for the requested `repo`.
3. Load area classification rules, local paths, debugger paths, and dump env vars.
4. **Also load `related_repos`** — these are repos where the root cause or fix may live. Note their local checkout paths.
5. **Load `coding_guidelines`** — if the repo has a `coding_guidelines` array, load it. These are repo-specific rules about preferred APIs, patterns, and conventions that must be followed when writing fixes.
6. **Load local tools** — read `config/local-tools.json` via `local-tools` (action: `list`). This puts tool paths in context so you don't need to search for them during reproduction or fix attempts.
7. If the repo is not configured, stop and tell the user to run `add-repo` first.

### Step 2: Select the Issue

**If `issue_number` is provided:** Use that issue directly.

**If not provided:**
1. Look for an active sprint run in `runs/` for this repo and platform.
2. Find the most recent `run.json` where `status` is `in-progress`.
3. Read its `queue` array and pick the last entry (pop from end).
4. If no active sprint or empty queue, tell the user to run `find-untriaged` to discover untriaged issues, or provide an issue number directly.
5. Update the run's queue (remove the selected issue) and save.

### Step 3: Fetch Issue Details

1. Use GitHub MCP tools to fetch the full issue: title, body, labels, assignees, all comments.
2. Check for open PRs that reference this issue.
3. Write `issues/<owner>-<repo>/<issue_number>/github.json` with the raw API responses:
   ```json
   {
     "issue": {
       "fetched_at": "<ISO 8601 timestamp>",
       "data": { /* raw API response from issue_read(get) */ }
     },
     "comments": {
       "fetched_at": "<ISO 8601 timestamp>",
       "data": [ /* raw API response from issue_read(get_comments) */ ]
     }
   }
   ```
4. Record `assignees` — the list of GitHub usernames assigned to the issue at fetch time.

### Step 4: Check Prior Work

1. Check if `issues/<owner>-<repo>/<issue_number>/analysis.json` exists.
2. If it does, read it — this issue was previously triaged.
3. **Platform reprocess check:** If the prior report has `triage.status == "platform-blocked"` and `triage.requires_platform` matches the current OS, this is a platform reprocess. In this case:
   - Preserve all prior observations — append new findings, don't replace prior work.
   - Prefix new reproduction steps with `[<current platform> pass]` to distinguish from prior platform attempts.
   - Proceed to reproduction (Step 6) even though the issue was previously triaged — the point is to retry on the correct platform.
   - If reproduction succeeds, update status from `platform-blocked` to `reproduced` (or the appropriate new status).
   - If still blocked (e.g., needs macOS and we're on Linux), keep `platform-blocked` but update `requires_platform` to reflect only the remaining platforms.
4. Check if `repros/issue_<issue_number>/` exists in the workspace.
5. Summarize what's known before proceeding.

### Step 5: Classify (quick — do not stop here)

Quickly classify the issue. This is a **preliminary step** — spend most of your effort on reproduction and fixing.

1. **Category**: bug, feature-request, question, or docs.
2. **Status** (initial): See [triage categories](references/triage-categories.md).
3. **Staleness**: active, stale, or superseded.
4. **Area**: Classify using the area rules from `config/repos.json`.
5. **Platform requirements**: Which platforms are needed to reproduce?
6. **Blocked**: If the issue depends on an external fix, unreleased package, or upstream change, set status to `blocked` with `blocked_reason` and optionally `blocked_url`.
7. **Affected repo**: Determine where the root cause actually lives. Set `affected_repo` to the repo where the bug or missing feature actually is. If the root cause spans multiple repos, set `affected_repo` to the primary one and note the others in `status_reason`.
8. **Actionability**: Derive from the fields above using the rules in [triage categories](references/triage-categories.md) (`triage.actionability` section). Do not set manually — compute it from status, fix candidate, and platform requirements.

**Cross-repo investigation:** Do NOT limit analysis to the issue's repo. Follow the code across repo boundaries using the `related_repos` local paths loaded in Step 1. The issue's repo is where the bug was *reported*, not necessarily where it *lives*.

For feature requests, check if the feature has already been implemented in the current codebase — including related repos.

For bugs, check if the bug has already been fixed since the issue was filed — including in related repos.

**Do NOT write reports yet.** Proceed directly to Step 6.

### Step 6: Reproduce

**Always attempt reproduction.** Only skip if one of these is true:
- The issue is a **question** or **docs** category (no bug to reproduce).
- The status is **already-fixed**, **already-implemented**, **by-design**, **duplicate**, **stale**, or **wont-fix** (nothing to reproduce).
- The issue is **platform-blocked** and cannot be reproduced on the current OS.

Follow the [reproduction rules](references/reproduction-rules.md):

1. Create `<workspace>/repros/issue_<NUMBER>/` if it doesn't exist.
2. Ensure the source repo (and any related repos needed) are on their main branches.
3. Write a minimal repro (console app, unit test, or script). The repro may reference or build against code from any of the local repo checkouts.
4. Set dump capture environment variables from config.
5. Run the repro and record all steps in the JSON.
6. All dump files must use the `.dmp` extension (rename Linux core dumps if needed).
7. Dumps are NOT committed (too large). Instead, commit the repro source and a `repro.sh`/`repro.bat` script to regenerate them. See [reproduction rules](references/reproduction-rules.md) for details.
8. If reproduction requires a different platform, set status to `platform-blocked` and note which platform.

### Step 7: Fix and Test

**Always attempt a fix** after reproduction (or even without it if the root cause is clear). Only skip if:
- The issue is a **question** category.
- The issue is **needs-info** and the root cause is completely unclear.
- The fix would require major architectural changes that are highly speculative.

Attempt a fix in any of these cases:
- The bug was **reproduced** and the root cause is understood.
- The bug was **not reproduced** but the root cause is obvious from code inspection (e.g., clear null check missing, off-by-one, wrong condition). The fix should still be proposed — it helps the developer understand the issue even without a repro.
- A **feature request** has a straightforward implementation path.

When creating a fix:
1. **Follow `coding_guidelines`** from the repo config (loaded in Step 1). These define preferred APIs, patterns, and conventions for this codebase. Violations will be caught in code review.
2. **Create the branch in the repo where the fix belongs**, not necessarily the issue's repo. Use `affected_repo` from Step 5 to determine this. For example, a `dotnet/diagnostics` issue whose root cause is in `dotnet/runtime` gets a fix branch in the runtime checkout. If the fix spans multiple repos, create branches in each.
3. Branch name: `issue_<NUMBER>` (using the original issue number, even in a different repo).
4. Make the fix.
5. **Run targeted tests** to validate the fix. Do NOT skip testing. Run the tests most relevant to the changed code. Avoid full test suites (they can take 50+ minutes), but always run *something*.
6. Record the fix details (summary, confidence, branch, diff) in the JSON. If the fix is in a different repo than the issue, note which repo the branch is in (e.g., `"branch": "issue_1837"`, `"fix_repo": "dotnet/runtime"`).
7. Set `fix.confidence` lower for fixes without reproduction (e.g., 0.4-0.6 vs. 0.8+ for reproduced fixes).
8. Push the branch to `origin` (the user's fork), NOT `upstream`. Do this for each repo where a branch was created.
9. Do NOT include `Co-authored-by: Copilot` in fix commit messages — these are proposed fixes authored by the developer.
10. **Use only standard US keyboard ASCII characters** in source code and code comments. Do not use em-dashes, smart quotes, or other Unicode punctuation in code. Use `--` instead of `—`, straight quotes instead of curly quotes, etc. This applies only to code changes, not to markdown reports or log entries.
11. Return all repos to their main branches when done.

### Step 8: Completion Self-Check

**Before writing reports, verify you completed the full loop.** Answer each question:

1. ✅ Did I **classify** the issue (category, status, area)?
2. ✅ Did I **attempt reproduction**? If not, is the reason one of the valid skip conditions from Step 6?
3. ✅ Did I **attempt a fix**? If not, is the reason one of the valid skip conditions from Step 7?
4. ✅ Did I **run tests** on my fix? If I have a fix candidate but didn't test it, go back to Step 7.

If you skipped reproduction or fixing, you MUST document the specific reason in the report. "I ran out of time" or "I focused on classification" are NOT valid reasons.

### Step 9: Write Reports

1. **Update `github.json`** at `issues/<owner>-<repo>/<issue_number>/github.json`:
   - Should already exist from Step 3. If not, write it now with the fetched issue and comments data.
   - Write atomically (`.tmp` then rename).

2. **Write analysis report** to `issues/<owner>-<repo>/<issue_number>/analysis.json`:
   - Follow the [JSON schema](references/json-schema.md).
   - This is always the single source of truth — overwrite in place.
   - Write atomically (`.tmp` then rename).
   - Set `manually_investigated` to `false` (automated triage).
   - **Append a log entry** to the `log` array (do NOT overwrite previous entries):
     ```json
     {
       "heading": "<ISO 8601 timestamp> — <platform> — automated triage",
       "body": "**Actions:** <what was done>\n**Findings:** <what was discovered>\n**Status change:** <old> → <new>\n**Fix:** <fix summary if any>"
     }
     ```
   - If this is the first session, initialize the `log` array with this entry.
   - If `analysis.json` already exists (re-triage), read it first and append to the existing `log` array.

3. **Write Markdown report** to `issues/<owner>-<repo>/<issue_number>/analysis.md`:

   The analysis.md is **not just a triage record** — it is a **learning document**. The reader is a developer who wants to understand the codebase through the lens of this issue. Every report should leave the reader knowing more about how the code works than they did before. Keep all triage/status/fix information, but shift the center of gravity toward explaining the code.

   **Required sections (in order):**

   - **Header block:** Issue title, GitHub link, state, labels, dates (same as today).
   - **Triage table:** Category, status, affected repo, platforms, fix branch, confidence (same as today).
   - **Summary:** 2-3 paragraph overview of the issue AND what you learned about the code. Not just "what's broken" — explain what the code is *trying to do* and why it matters.
   - **How the Code Works:** This is the new heart of the report. Explain the relevant subsystem, module, or component the issue touches. Walk through the architecture:
     - What are the key types, classes, or functions involved?
     - What is the call chain or data flow for the affected scenario?
     - How do the pieces fit together? What are the important interfaces or abstractions?
     - What design decisions or tradeoffs does the code make?
     - If the code spans multiple repos, explain how they interact.
     - Use code snippets, call chains, and diagrams (ASCII is fine) to illustrate.
     - Cite specific file paths and line numbers so the reader can follow along.
     - This section should be useful even to someone who doesn't care about the bug — it should teach the reader about this part of the codebase.
   - **Root Cause / Issue Analysis:** What specifically is broken or missing, and why. Reference the architecture you just explained. This should flow naturally from the "How the Code Works" section — "now that you understand how X works, here's what goes wrong when Y happens."
   - **Fix Details:** What was changed and why. Explain the fix in terms of the architecture, not just as a diff. Include diffs for precision, but narrate the reasoning.
   - **Investigation Trail:** Observations and reproduction steps (same as today).
   - **Artifacts:** Dump files, repro code, etc. (same as today).
   - **Key Comments:** Notable GitHub comments (same as today).
   - **Log:** Investigation history is stored in `analysis.json` under the `log` array — no separate file.

   **Tone and depth guidelines:**
   - Write as if explaining to a teammate who is smart but unfamiliar with this part of the code.
   - Err on the side of too much context rather than too little.
   - Don't just name types — explain what they do and how they relate to each other.
   - When you read surrounding code to understand the issue, share what you learned, not just what's broken.
   - If you discover interesting design patterns, constraints, or historical context, include it.

   Write atomically (`.tmp` then rename).

### Step 10: Commit Results

1. Stage the new/updated files in the triage repo:
   - `issues/<owner>-<repo>/<issue_number>/github.json`
   - `issues/<owner>-<repo>/<issue_number>/analysis.json`
   - `issues/<owner>-<repo>/<issue_number>/analysis.md`
   - `issues/<owner>-<repo>/<issue_number>/repro/` (repro source code and regeneration script — NOT dumps)
   - Updated `runs/*/run.json` (if queue was modified)
2. Commit with message: `triage: <owner>/<repo>#<number> — <status> (<category>)`
3. Example: `triage: dotnet/diagnostics#5632 — reproduced (feature-request)`
4. Push to the remote. If the push fails (e.g., remote is ahead), ask the user whether to rebase and retry or skip the push.
5. Do NOT include `Co-authored-by: Copilot` in commit messages (applies to both triage repo commits and fix branch commits).

## Validation

- [ ] `github.json` is valid JSON with raw API data and `fetched_at` timestamps
- [ ] `analysis.json` is valid JSON matching the schema, with log entry appended
- [ ] `analysis.md` exists and has content
- [ ] Reproduction was attempted (or a valid skip reason is documented)
- [ ] Fix was attempted (or a valid skip reason is documented)
- [ ] Tests were run against any fix candidate
- [ ] Sprint queue was updated (issue removed) if processing from queue
- [ ] Source repos are back on main branch (all repos touched, not just the issue's repo)
- [ ] Results committed to triage repo

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Stopped after classification | Classification is Step 5 — you must continue through Steps 6-8 (reproduce, fix, self-check) |
| Skipped repro without valid reason | Always attempt reproduction unless category is question/docs or status is terminal (already-fixed, stale, etc.) |
| Skipped fix without valid reason | Always attempt a fix if root cause is understood or obvious from code inspection |
| Fix candidate but no tests run | Always run targeted tests against your fix before writing reports |
| Repo not in config | Run `add-repo` first |
| No active sprint | Run `find-untriaged` to discover untriaged issues |
| Left source repo on wrong branch | Always `git checkout main` in every repo touched when done |
| Lost context from prior sessions | Append to `analysis.json` `log` array, never overwrite prior entries |
| Full test suite run | Only run targeted tests — full suite takes 50+ min |
| Fix created in wrong repo | Use `affected_repo` to determine where the root cause is — the issue's repo is where it was reported, not necessarily where the fix belongs |
| Investigation limited to one repo | Follow the code across repo boundaries using `related_repos` local paths — stack traces, function calls, and shared interfaces often cross repos |
