---
name: load-issue
description: >
  Loads all prior context for a specific issue and presents a briefing to the developer. Use when the user
  says "load", "continue", or "pick up" an issue. Reads the existing JSON report, captain's log, reproduction
  artifacts, fix branches, and latest GitHub comments. Does NOT autonomously investigate — instead primes the
  conversation so the developer can ask followups, try things, and direct the investigation interactively.
  Do NOT use when the user says "triage", "diagnose", "fix", "work on", or "investigate" an issue — that is diagnose-and-fix.
---

# Continue Issue

Load all prior context for an issue and brief the developer for an interactive investigation session.

## When to Use

- Picking up a previously triaged issue for hands-on work
- Reviewing what was done before and deciding next steps
- Starting an interactive debugging or code review session on a specific issue

## When Not to Use

- First-time triage of an issue (use `diagnose-and-fix`)
- Batch processing (run `diagnose-and-fix` repeatedly)
- Fully automated re-investigation (use `diagnose-and-fix` with the issue number)

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| issue_number | Yes | The issue number to continue working on |
| repo | No | Repository in `owner/repo` format (default: infer from existing reports) |
| workspace | No | Path to workspace root (default: parent of triage repo) |

## Workflow

### Step 0: Bookkeeping

Invoke `bookkeeping` to pull the triage repo and flush any pending `.progress/` from prior sessions.

### Step 1: Locate and Load Prior Work

Before doing anything else, gather ALL context:

**a) Load configuration:**
- Read `config/repos.json` from the triage repo root.
- Find the entry for the issue's repo and load its `related_repos` with their local checkout paths.
- These related repos are part of the investigation scope — the root cause or fix may live in any of them.
- **Load `coding_guidelines`** — if the repo has a `coding_guidelines` array, load it and include in the briefing. These must be followed when writing or modifying code during the session.
- **Load local tools** — read `config/local-tools.json` via `local-tools` (action: `list`). This puts tool paths in context for the interactive session so you can launch debuggers, analyzers, etc. without searching.

**b) Infer repo if not provided:**
- Search `issues/*/issue_number/report.json` across all repo directories in the triage repo.
- If found in exactly one, use that repo. If ambiguous, ask the user.

**b) GitHub Issue (live):**
- Use GitHub MCP tools to fetch the FULL issue: title, body, labels, ALL comments.
- Note any comments added since `fetched_at_utc` in the last report — these are NEW context.

**c) Existing JSON report:**
- Read `issues/<owner>-<repo>/<issue_number>/report.json`.

**d) Captain's log:**
- Read `issues/<owner>-<repo>/<issue_number>/log.md` in full.
- This is the best source of "what happened when" — understand the full investigation arc.

**e) Existing Markdown report:**
- Read `issues/<owner>-<repo>/<issue_number>/report.md`.

**f) Reproduction folder:**
- Check if `<workspace>/repros/issue_<issue_number>/` exists.
- If so, inventory its contents: repro apps, dumps, artifacts, logs, scripts.
- Check committed repro source in `issues/<owner>-<repo>/<issue_number>/repro/` too.

**g) Fix branches:**
- Check if a branch named `issue_<issue_number>` exists in the source repo **and all related repos** (from `related_repos` in config). The fix may have been created in a different repo than where the issue was filed.
- If found, review the diff against main to understand the candidate fix.
- Note which repo each fix branch is in — this is important context for the developer.

**h) Check out fix branches:**
- If a fix branch was found in Step 1g, **check it out** in the appropriate repo so the developer starts on the fix code.
- Use `fix_repo` from `report.json` (if set) to determine which repo checkout to switch. If `fix_repo` is empty, use the issue's own repo checkout.
- If fix branches exist in **multiple** related repos, check them all out.
- This lets the developer immediately see, build, and test the fix without manual branch switching.
- Record which repos were switched so they can be restored to main in Step 5.

**i) Open PRs:**
- Check for open PRs referencing this issue — in the issue's repo **and** related repos.
- **Track which fix branches have open PRs** — this controls push behavior later (see Step 5).

### Step 2: Present Briefing

Present a clear, structured briefing to the developer. This is the **primary output** of this skill. Include:

1. **Issue summary** — Title, category, link, key details from the body
2. **Current triage status** — Status, staleness, affected repo, platforms, actionability
3. **Cross-repo context** — List the related repos and their local paths. If `affected_repo` differs from the issue's repo, highlight this — the root cause is elsewhere. Remind the developer (and yourself) that investigation and fixes should follow the code wherever it leads across these repos.
4. **Investigation history** — What was attempted across all sessions (from log.md)
5. **Reproduction status** — Was it reproduced? What repro artifacts exist? Where?
6. **Fix status** — Is there a candidate fix? Which repo is the branch in? Branch name, confidence, what it changes. Note that the fix branch has been checked out and is ready to build/test.
7. **Open PRs** — Any PRs already addressing this issue (across all related repos)
8. **New activity** — Any GitHub comments or changes since the last session
9. **Suggested next steps** — Based on current state, what are the logical things to try next

### Step 3: Interactive Investigation

**STOP after the briefing.** Do not autonomously investigate, reproduce, or fix anything.

The developer is now in the driver's seat. Wait for them to:
- Ask questions about the issue or prior work
- Request specific actions ("try reproducing with X", "look at function Y", "check if Z was fixed")
- Direct the investigation in a particular direction
- Ask you to run commands, read code, build repros, etc.

Follow the developer's lead. When they ask you to do something, do it and report back. This is an interactive session, not an automated triage run.

**Cross-repo scope:** When investigating or building fixes during this session, you have full access to all related repos loaded in Step 1. Do NOT confine yourself to the issue's repo:
- If the developer asks you to look at code, follow it across repo boundaries. A diagnostics issue may need you to read runtime or ClrMD source.
- If the developer asks you to fix something, create the fix branch in whichever repo the change belongs in — use the `related_repos` local paths.
- If the developer asks you to run tests, run them in the repo where the code change was made.
- When reporting findings, be explicit about which repo you're looking at so the developer maintains context.

**Code changes:** When writing or modifying source code (including comments in code), use only standard US keyboard ASCII characters. No em-dashes, smart quotes, or other Unicode punctuation in code. Use `--` instead of `—`, straight quotes instead of curly quotes, etc. This restriction applies only to code changes, not to markdown reports or log entries.

**Ongoing progress capture:** As you work, periodically append findings to a progress file:

1. Create `issues/<owner>-<repo>/<issue_number>/.progress/` if it doesn't exist.
2. At the start of the session, create a file named `<ISO-8601-timestamp>.md` (e.g., `2026-02-17T13-30-00Z.md`).
3. Append to this file as you go — key findings, commands run, code read, conclusions reached. Write in the same style as a captain's log entry.
4. **If your progress file disappears** (renamed by `bookkeeping` flushing from another session), create a new one with a fresh timestamp and continue. The prior content was already captured.
5. This file is gitignored and local-only. It exists as a safety net so that if the session ends without an explicit save, the next `bookkeeping` run will flush it into `log.md`.

### Step 4: Update Reports (when the developer says they're done)

When the developer indicates the session is over (or asks you to save progress):

**JSON update:**
- Overwrite `report.json` in place with any updated triage status, observations, or fix info.
- Set `manually_investigated` to `true`.
- Write atomically (`.tmp` then rename).

**Captain's log — append a new session entry to `log.md`:**
- Do NOT overwrite previous entries — append only.
- Add a new `## <timestamp> — <platform> — manual investigation` section.
- Record: what was attempted, what was discovered, what changed.

**Markdown update:**
- Overwrite `report.md` with the latest findings.
- Clearly mark what is NEW from this session vs. carried over from prior work.

### Step 5: Commit

**Triage repo:** Commit and push triage repo changes (report.json, report.md, log.md) as usual.

Commit with message: `continue: <owner>/<repo>#<number> — <summary of new findings>`

**Fix branches:** Commit fix branch changes locally, but **do NOT push fix branches that have an open PR** unless the developer explicitly asks (e.g., "push it", "update the PR"). Pushing to a branch with an open PR triggers notifications and review activity — the developer should control when that happens.

- If the fix branch has **no open PR**: push to `origin` automatically.
- If the fix branch has **an open PR**: commit locally only. Mention in the briefing or when saving that the branch has unpushed commits and the developer can say "push" when ready.

Do NOT include `Co-authored-by: Copilot` in commit messages.

## Validation

- [ ] All prior context was loaded and presented in the briefing
- [ ] Developer was NOT preempted — no autonomous investigation
- [ ] When saving: session entry appended to `log.md` (not overwriting prior entries)
- [ ] When saving: `manually_investigated` set to `true`
- [ ] Source repos back on main branch (all repos touched, not just the issue's repo)
- [ ] Results committed to triage repo

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Jumping into investigation without being asked | STOP after the briefing — wait for developer direction |
| Missing new GitHub comments | Compare `fetched_at_utc` with comment dates |
| Can't find the repo | Provide `repo` explicitly if auto-detection fails |
| Repro folder is huge | Don't re-read dumps — summarize what files exist |
| Forgetting to save | Remind the developer to save progress before ending the session |
| Investigation limited to one repo | Use `related_repos` local paths to follow code and build fixes across repo boundaries |
| Fix branch in wrong repo | Check all related repos for existing branches; create new branches where the code change belongs |
