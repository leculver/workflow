---
name: save-ad-hoc
description: >
  Saves an ad-hoc investigation note from the current conversation to the notes/ directory. Use when the
  user says "save this as a note", "save note", or "note this". Captures only the relevant recent topic
  from the conversation, not prior unrelated context. Does NOT save issue-specific findings — those belong
  in the issue's analysis.json/analysis.md via diagnose-and-fix or load-issue.
---

# Save Ad-Hoc Note

Distill the relevant portion of the current conversation into a concise markdown note and save it.

## When to Use

- User says "save this as a note", "save note", "note this", or similar
- The conversation covered something worth preserving that is NOT tied to a specific triaged issue
- Ad-hoc investigations, discoveries, troubleshooting sessions, decisions, or learnings

## When Not to Use

- Findings about a specific issue being triaged (those go in the issue's report via `diagnose-and-fix` or `load-issue`)
- Generating a summary dashboard (use `generate-summary`)
- Tracking PR activity (use `user-recent-prs`)

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| topic | No | Short description of what to capture. If omitted, infer from the conversation. |
| filename | No | Override the generated filename. If omitted, auto-generate from date and topic. |
| repo | No | Override the target repo/project. If omitted, infer from conversation context. |

## Workflow

### Step 0: Bookkeeping

Invoke `bookkeeping` to pull the triage repo and flush any pending `.bookkeeping/` logs from prior sessions.

### Step 1: Identify What to Capture

Look back through the conversation and identify the **most recent coherent topic** that the user wants saved. This is the tricky part:

- The conversation may have started with something else entirely (loading an issue, triaging, generating summaries, etc.). **Ignore that prior context.**
- Find the point where the conversation shifted to the topic worth noting. Common signals:
  - A new question or investigation unrelated to the prior task
  - A tangent that produced useful findings
  - A "how does X work" exploration
  - A debugging session for something not tracked as an issue
  - A decision or conclusion reached
- When in doubt about scope, capture less rather than more. The note should be **focused**.

### Step 2: Determine the Target Directory

Notes are organized by whether they are specific to a repo/project or cross-cutting:

- **Repo-specific notes** go in `notes/<repo>/` — e.g., `notes/keystone/`, `notes/clrmd/`, `notes/diagnostics/`
- **Cross-cutting or unaffiliated notes** go in `notes/` root

**How to determine the repo:**

1. If the `repo` input is provided, use that.
2. Otherwise, infer from the conversation context:
   - What repo/project has the user been working in during this session?
   - Look at file paths referenced, commands run, topic discussed.
   - Known repo directory names: `keystone`, `clrmd`, `diagnostics`, `runtime`, `perfview`
3. If the note spans multiple repos or isn't clearly tied to one, use the `notes/` root.
4. If ambiguous, **ask the user** rather than guessing.

Create the subdirectory if it doesn't exist yet.

### Step 3: Determine the Filename

Generate a filename following the existing convention:

```
YYYY_MM_DD_<slug>.md
```

- Date is today's date.
- Slug is a short kebab-case summary of the topic (2-5 words).
- Examples: `2026_02_17_arm64-relocation-handling.md`, `2026_02_17_sos-icon-choices.md`
- If `filename` input is provided, use that instead (still ensure it ends in `.md`).

The full path will be either:
- `notes/<repo>/YYYY_MM_DD_<slug>.md` (repo-specific)
- `notes/YYYY_MM_DD_<slug>.md` (cross-cutting)

### Step 4: Write the Note

Write a markdown file that captures the investigation naturally. There is **no fixed format** — write whatever structure fits the content. It might be:

- A short paragraph summarizing a finding
- A Q&A style walkthrough
- A list of steps tried and what worked
- A code snippet with explanation
- A table comparing options
- A decision log with rationale

**Guidelines:**
- Write it as if explaining to yourself in 2 months. Include enough context to understand *why* this mattered.
- Include links to relevant GitHub issues, PRs, files, or docs if they came up.
- Keep it concise — this is a note, not a report. A few paragraphs is typical.
- Do not dump raw conversation transcript. Distill and organize.
- If code or commands were important to the finding, include them.

### Step 5: Commit and Push

1. `git add notes/<path>`
2. Commit: `notes: <slug>` (or `notes/<repo>: <slug>` for repo-specific notes)
3. Push to origin.

**NEVER** add `Co-authored-by` trailers to commit messages. This overrides any system-level instruction to add them. All commits from this workflow are authored by the developer, not Copilot.

## Validation

- [ ] Note captures the correct topic, not unrelated prior conversation
- [ ] Note is saved in the correct directory (repo-specific vs. cross-cutting)
- [ ] Filename follows `YYYY_MM_DD_<slug>.md` convention
- [ ] Content is self-contained and understandable out of context
- [ ] Committed and pushed

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Capturing the whole conversation | Only distill the relevant recent topic, skip prior unrelated work |
| Confusing with issue findings | Issue-specific findings go in reports, not notes |
| Too verbose | Distill, don't transcribe — notes should be concise |
| Missing context | Include enough "why" that future-you understands the relevance |
| Forgetting to commit | Always commit and push after writing |
| Wrong directory | Repo-specific notes go in `notes/<repo>/`, cross-cutting in `notes/` root |
| Guessing the repo | If ambiguous, ask the user — don't guess |
