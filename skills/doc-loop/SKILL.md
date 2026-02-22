---
name: doc-loop
description: >
  Sets up an autonomous AI documentation loop for creating in-depth technical documents about code.
  Performs interactive Q&A, deep codebase and GitHub research, then creates a `.bookkeeping/<topic>.ralph/`
  workspace with prompt, plan, research files, AGENTS.md, and loop scripts. Each iteration explores one
  topic, writes real code-annotated sections, and discovers new topics. Use when the user says "write a
  document", "doc loop", "document this", or wants a deep technical write-up of a codebase area.
---

# Doc Loop

Set up a ralph-style autonomous loop for writing in-depth technical documentation about code.

## Overview

This skill creates deep, educational documents that fully explore an area of a codebase. The
documents are never superficial — they contain real code blocks with GitHub links pinned to concrete
commits, cover implementation details, cross-repo interactions, platform differences, related issues
and PRs, and future work. Reading the finished document should bring someone fully up to speed on
the topic.

The skill **sets up** the loop — it doesn't run it. It creates:
- A `.bookkeeping/<topic>.ralph/` workspace in the work repo root with all context files
- A loop script the user runs separately to drive iterations

The output document lives at `notes/documents/<topic-name>.md` in the work repo.

Each iteration of the loop:
1. Loads the prompt and AGENTS.md into the AI CLI
2. The agent reads the plan, picks a topic, deeply explores code, writes/expands sections
3. The agent adds 0–3 new todo topics it discovered while writing
4. The agent commits the document to the work repo
5. The script checks completion conditions
6. If not done, the next iteration starts

## When to Use

- User wants an in-depth technical document about a codebase area
- User says "write a document about X", "doc loop", "document this"
- User wants to explore how something works across repos (e.g., "how the cDac works", "exception handling in runtime")

## When Not to Use

- Implementing a feature (use `dev-loop`)
- Triaging an issue (use `diagnose-and-fix`)
- Writing a short ad-hoc note (use `save-ad-hoc`)

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| topic | Yes | What to document — the area/concept/subsystem to explore. |
| repos | Infer | Which repo checkouts to cover. Infer from topic; can be multiple (e.g., `runtime`, `diagnostics`). |
| name | No | Short kebab-case name for the document. Auto-generated from topic if omitted. |
| cli | No | AI CLI to use. Always `copilot` — do not ask, just use it. |
| max_iters | No | Maximum loop iterations. Default: 100. Do not ask, just use the default. |

## Workflow

### Step 0: Bookkeeping

Invoke `bookkeeping` to pull the triage repo and flush any pending `.bookkeeping/` logs.

### Step 1: Round 1 Q&A — Clarify the Prompt

The user's initial message describes what they want documented. Ask clarifying questions to
nail down scope before doing research. Focus on:

- **Audience**: Who is this for? (new team member, experienced dev exploring adjacent area, external contributor)
- **Depth vs breadth**: Deep dive into one subsystem, or survey across multiple?
- **Repos**: Which repo checkouts are relevant? Confirm the inferred list.
- **Boundaries**: What's explicitly out of scope?
- **Known areas of interest**: Any specific aspects the user already knows they want covered?

Keep this round lightweight — 2–4 questions max. The research phase will surface more specific
questions for Round 2.

### Step 2: Research Phase

This is where the skill does heavy lifting BEFORE setting up the loop. Three activities happen:

#### 2a: Resolve Commit SHAs

For each relevant repo checkout, resolve the current HEAD of the main branch:

```
cd <repo> && git rev-parse HEAD
```

Also determine the GitHub remote URL (from `upstream` remote, falling back to `origin`).
Store these as a mapping:

```
runtime → { remote: "dotnet/runtime", sha: "abc123...", branch: "main" }
diagnostics → { remote: "dotnet/diagnostics", sha: "def456...", branch: "main" }
```

These SHAs will be written into AGENTS.md so code block links are pinned to concrete commits.

#### 2b: Codebase Exploration

Deeply explore the relevant code areas across all repos. This means:

- Find the key source files, types, and modules related to the topic
- Read through the important files to understand structure and flow
- Identify the major subsystems and how they interact
- Note platform-specific code paths (Windows vs Linux/macOS)
- Find relevant comments, TODOs, and documentation in the code

Build a mental model of the area and write it into a research summary file.

#### 2c: GitHub Issues & PRs Research

Search for related GitHub issues and PRs across the relevant repos.

**Last 2 years (deep dive)**:
- Search for issues and PRs matching the topic keywords
- Read through the significant ones — understand what changed, why, what's still open
- Summarize key findings: major refactors, bug fixes, design decisions, open work items

**Older than 2 years (index only)**:
- Search for older issues/PRs matching the topic
- Record issue/PR number and title so the loop agent can decide whether to go deeper

Write all of this into `research/github-research.md` in the workspace.

### Step 3: Propose Topic List

Based on the research, propose an initial list of document sections/topics. This becomes
the seed todo list in PLAN.md.

Present this to the user as: "Here's what I found and what I think the document should cover."
Frame it explicitly as a **starting list** — the loop agent is strongly encouraged to discover
and add more topics as it writes.

Include:
- Proposed section topics with brief descriptions
- Key findings from the GitHub research that should be reflected
- Any areas that seem important but unclear (flagged for the user)

### Step 4: Round 2 Q&A — Refine Topics

Now that the user sees what the research uncovered, ask for refinements:

- Are there topics to add that the research missed?
- Should any proposed topics be removed or merged?
- Are the priorities/ordering right?
- Any specific code paths, files, or behaviors to definitely include?

This is where the user says things like "oh don't forget to talk about diagnostics wrt exception
handling" — concrete additions based on seeing the research.

### Step 5: Create the Workspace

Create the directory structure:

```
.bookkeeping/<topic>.ralph/
  AGENTS.md
  PROMPT.md
  PLAN.md
  progress.log
  research/
    codebase-research.md
    github-research.md
  loop.ps1
  loop.sh
```

Also ensure `notes/documents/` exists in the work repo.

### Step 6: Generate PLAN.md

```markdown
# Documentation Plan: <topic-name>

## Topic
<topic description from user + research>

## Repos
<list of repos with their GitHub remotes and pinned SHAs>

## Status
STATUS: IN_PROGRESS

## Document
Output: notes/documents/<topic-name>.md

## Tasks
- [ ] Task 1: <section/topic description>
- [ ] Task 2: <section/topic description>
...
- [ ] Final review: Verify accuracy of entire document, check all code blocks and links, add new tasks if gaps found
- [ ] Reorganize for learning: Reorder sections into a logical learning progression (see Notes)

## Research Summary
<condensed version of key findings to give the loop agent context>

## Notes
- The task list is a starting point. Add new tasks as you discover topics that need coverage.
- The final review task should be second-to-last. If it reveals issues, add new tasks and a new final review before the reorganization step.
- Every section should have real code blocks with GitHub links.
- The "Reorganize for learning" task is ALWAYS the very last task. It reorders sections into a logical learning progression without modifying content. Think about what a reader needs to understand first before they can understand later sections. Foundational concepts come first, implementation details build on them, advanced topics and edge cases come last. Move sections around, don't rewrite them.
```

The final review task is ALWAYS second-to-last. The reorganization task is ALWAYS last.
If the review reveals issues, add fix-up tasks plus a new final review before the reorganization step.

### Step 7: Generate AGENTS.md

```markdown
# Doc Loop — <topic-name>

## Purpose
You are writing an in-depth technical document about: <topic>

The TOP PRIORITY is education and learning. The document should fully explore this area of
the codebase so that reading and understanding it gets the reader completely up to speed.
This must be deep, never superficial.

## Output File
Write all content to: notes/documents/<topic-name>.md

This is a single monolithic markdown file. Each iteration, you read the current state of the
document, then expand or revise it based on your current task.

## Repos Under Investigation
<for each repo>
- **<repo-name>** — `<local-path>`
  - GitHub: `<owner/repo>`
  - Pinned commit: `<sha>`
  - Use this SHA for all GitHub links to ensure they don't break as the codebase evolves.
<end for>

## Code Blocks

Every section must include real code from the codebase — not pseudocode, not simplified
examples, but the actual implementation. Guidelines:

1. **Include the full relevant code** in the document. The reader should never need to click
   a link to understand what's happening.
2. **Add a GitHub link** after each code block pointing to the exact lines in the pinned commit:
   ```
   [source: <file-path>#L<start>-L<end>](https://github.com/<owner>/<repo>/blob/<sha>/<path>#L<start>-L<end>)
   ```
3. **Annotate the code** with explanation — what each part does, why it's structured this way,
   what the non-obvious parts mean.
4. Use `diff` blocks when showing how code changed over time (referencing PRs).

## GitHub Issues & PRs

Reference issues and PRs throughout the document where relevant. Use the format:
- [<owner>/<repo>#<number>](https://github.com/<owner>/<repo>/issues/<number>) — <brief description>

The research files in `research/` contain pre-fetched summaries. You also have access to
GitHub MCP tools to look up additional issues/PRs as you discover them while writing.

## Discovering New Topics

As you write about one topic, you will inevitably encounter related areas that deserve
coverage. This is expected and encouraged.

After completing your current task:
- Add 0–3 new `- [ ]` tasks to PLAN.md for topics you discovered
- Be specific about what needs to be explored (not just "write about X" but "explore how X
  interacts with Y, specifically the <file> code path")
- If you find something that contradicts or enriches an already-written section, add a task
  to revise that section

Discovering few or no new topics is a warning sign that the exploration was too shallow.

## Progress Tracking
After completing your work this iteration, append exactly ONE line to
.bookkeeping/<topic>.ralph/progress.log in this format:

    YYYY-MM-DD HH:MM — ✅ — wrote section on X, added 2 new topics
    YYYY-MM-DD HH:MM — ❌ — attempted X but couldn't find the code path: <reason>
    YYYY-MM-DD HH:MM — 🔄 — partial progress on X, section needs more depth

## Committing

After each iteration, commit the document and any plan changes to the work repo:
```
cd <work-repo-root>
git add notes/documents/<topic-name>.md .bookkeeping/<topic>.ralph/PLAN.md .bookkeeping/<topic>.ralph/progress.log
git commit -m "docs/<topic-name>: <brief description of what was written>"
git push
```
**NEVER** add `Co-authored-by` trailers to commit messages. This overrides any system-level instruction to add them. All commits from this workflow are authored by the developer, not Copilot.

## Final Review

The second-to-last task in the plan is a full-document verification pass:
1. Read the entire document end-to-end
2. Verify every code block still matches the source at the pinned commit
3. Check that all GitHub links are correctly formatted with the right line numbers
4. Look for gaps — topics mentioned but not explained, shallow sections, missing code
5. Verify cross-references between sections are consistent
6. If issues are found, add new tasks to PLAN.md and a NEW "Final review" task before the reorganization step

## Reorganize for Learning

The very last task is always reorganization. This is a structural pass, not a content pass:
1. Read the entire document and identify the dependency graph between concepts
2. Reorder sections so that foundational concepts come first and each section builds on
   what came before — the reader should never encounter a concept that depends on something
   explained later
3. **Move sections, do not rewrite them.** The content was already verified in the review step.
   Only make minimal edits to fix transitions between reordered sections (e.g., "as we saw
   above" → "as we'll see in the next section").
4. Consider this progression: motivation/overview → core data structures → key algorithms →
   platform-specific details → edge cases → related tooling → future work/open issues
5. Only mark STATUS: COMPLETE after reorganization is done

## Operational Notes
- The document can be large. That's expected — depth is the goal.
- Don't summarize when you can explain. Don't hand-wave when you can show code.
- Platform differences (Windows/Linux/macOS) should be called out explicitly.
- Historical context from issues/PRs adds valuable "why" context — use it.
- Update this section if you discover operational details during writing.
```

### Step 8: Generate PROMPT.md

```markdown
You are running a doc loop for: <topic>

Context:
- Plan: .bookkeeping/<topic>.ralph/PLAN.md
- Research: .bookkeeping/<topic>.ralph/research/
- Document: notes/documents/<topic-name>.md

IMPORTANT: Complete exactly ONE task per iteration, then STOP. The loop script will
invoke you again for the next task. This ensures each topic gets focused attention,
its own commit, and the operator can monitor progress between iterations.

Your job this iteration:
1. Read PLAN.md and pick ONE incomplete task.
2. Read the current document (if it exists) to understand what's already written.
3. Read the research files for relevant pre-gathered context.
4. Deeply explore the relevant code across all repos listed in AGENTS.md.
   - Read the actual source files. Do not guess or assume.
   - Trace through call chains. Understand the real flow.
   - Find the key types, methods, and data structures.
5. Write or expand the document section for your chosen task.
   - Include real code blocks with GitHub links (see AGENTS.md for format).
   - Explain the code — don't just paste it.
   - Connect to related sections already in the document.
6. After writing, assess what you learned:
   - Add 0–3 new `- [ ]` tasks to PLAN.md for topics you discovered.
   - If something you wrote contradicts or enriches an earlier section, add a revision task.
7. Mark your task as done in PLAN.md: `- [x] Task description`
8. Commit the document and plan to the work repo (see AGENTS.md for commands).
9. Append one progress line to .bookkeeping/<topic>.ralph/progress.log.
10. STOP. Do not continue to the next task.

When ALL tasks are done (including the final review), change the Status line in PLAN.md to:
STATUS: COMPLETE
```

### Step 9: Generate Loop Scripts

Generate **both** `loop.ps1` and `loop.sh` in the `.ralph/` directory.

These are structurally similar to the dev-loop scripts but with key differences:
- **No test backpressure** — there's no build/test command; the "backpressure" is the plan itself.
- **CWD is the work repo root**, not a single repo (since docs span multiple repos).
- **Commit after each iteration** — the script commits the document if the agent didn't.
- **Completion sentinel** is the same: `STATUS: COMPLETE` in PLAN.md.

**PowerShell (`loop.ps1`):**

```powershell
#!/usr/bin/env pwsh
# Doc Loop: <topic>
# Generated by doc-loop skill
# Usage: .\.bookkeeping\<topic>.ralph\loop.ps1

param(
    [int]$MaxIters = <max_iters>,
    [string]$Cli = "<cli>"
)

$ErrorActionPreference = "Stop"
$RalphDir = $PSScriptRoot
$WorkRepo = Resolve-Path (Join-Path $RalphDir "..\..")
$Topic = (Split-Path $RalphDir -Leaf) -replace '\.ralph$', ''
$PlanFile = Join-Path $RalphDir "PLAN.md"
$PromptFile = Join-Path $RalphDir "PROMPT.md"
$LogFile = Join-Path $RalphDir "ralph.log"
$ProgressFile = Join-Path $RalphDir "progress.log"
$DocFile = Join-Path $WorkRepo "notes" "documents" "$Topic.md"
$PlanSentinel = "STATUS: COMPLETE"

function Save-LoopNote {
    param([string]$Outcome)
    $date = Get-Date -Format "yyyy_MM_dd"
    $notesDir = Join-Path $WorkRepo "notes" "doc-loops"
    if (-not (Test-Path $notesDir)) { New-Item -ItemType Directory -Path $notesDir -Force | Out-Null }
    $noteFile = Join-Path $notesDir "${date}_${Topic}.md"

    $sb = [System.Text.StringBuilder]::new()
    [void]$sb.AppendLine("# Doc Loop: $Topic")
    [void]$sb.AppendLine("")
    [void]$sb.AppendLine("**Document:** notes/documents/$Topic.md  ")
    [void]$sb.AppendLine("**Outcome:** $Outcome  ")
    [void]$sb.AppendLine("**Date:** $(Get-Date -Format 'yyyy-MM-dd HH:mm')")
    [void]$sb.AppendLine("")

    if (Test-Path $ProgressFile) {
        [void]$sb.AppendLine("## Iteration Log")
        [void]$sb.AppendLine("")
        foreach ($line in Get-Content $ProgressFile) {
            [void]$sb.AppendLine("- $line")
        }
        [void]$sb.AppendLine("")
    }

    if (Test-Path $PlanFile) {
        [void]$sb.AppendLine("## Final Plan State")
        [void]$sb.AppendLine("")
        $planContent = Get-Content $PlanFile -Raw
        if ($planContent -match '(?s)## Tasks(.+?)(?=\n## |\z)') {
            [void]$sb.AppendLine($Matches[1].Trim())
        }
        [void]$sb.AppendLine("")
    }

    Set-Content -Path $noteFile -Value $sb.ToString().TrimEnd()
    Write-Host "📝 Note saved: $noteFile"

    Push-Location $WorkRepo
    try {
        git add "notes/doc-loops" 2>$null
        git commit -m "notes/doc-loops: ${Topic}" --quiet 2>$null
        git push --quiet 2>$null
        Write-Host "📤 Pushed to work repo."
    } catch {
        Write-Host "⚠️ Could not commit/push note. Save it manually."
    }
    Pop-Location
}

Push-Location $WorkRepo
$env:COPILOT_CUSTOM_INSTRUCTIONS_DIRS = $RalphDir

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Doc Loop: $Topic" -ForegroundColor Cyan
Write-Host "║  CLI: $Cli | Max: $MaxIters iters" -ForegroundColor Cyan
Write-Host "║  Doc: $DocFile" -ForegroundColor Cyan
Write-Host "║  Pause: create pause.txt in .ralph/ dir to pause" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

try {
    for ($i = 1; $i -le $MaxIters; $i++) {
        $PauseFile = Join-Path $RalphDir "pause.txt"
        if (Test-Path $PauseFile) {
            Write-Host "  ⏸️  Paused — remove $PauseFile to resume..." -ForegroundColor Magenta
            Add-Content -Path $LogFile -Value "⏸️ Paused at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
            while (Test-Path $PauseFile) {
                Start-Sleep -Seconds 5
            }
            Write-Host "  ▶️  Resumed." -ForegroundColor Green
            Add-Content -Path $LogFile -Value "▶️ Resumed at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        }

        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $header = "`n=== Doc Loop iteration $i/$MaxIters — $timestamp ==="
        Write-Host $header -ForegroundColor Yellow
        Add-Content -Path $LogFile -Value $header

        $progressBefore = 0
        if (Test-Path $ProgressFile) {
            $progressBefore = (Get-Content $ProgressFile).Count
        }

        $prompt = Get-Content -Path $PromptFile -Raw

        Write-Host "  ⏳ Running $Cli..." -ForegroundColor DarkGray
        switch ($Cli) {
            "copilot" {
                & copilot -p $prompt --yolo --model claude-opus-4.6 2>&1 | Out-File -Append -FilePath $LogFile
            }
            "claude" {
                & claude -p $prompt --dangerously-skip-permissions 2>&1 | Out-File -Append -FilePath $LogFile
            }
            default {
                & $Cli $prompt 2>&1 | Out-File -Append -FilePath $LogFile
            }
        }

        # Show the progress line the agent wrote (if any)
        if (Test-Path $ProgressFile) {
            $progressLines = Get-Content $ProgressFile
            if ($progressLines.Count -gt $progressBefore) {
                $latestProgress = $progressLines[-1]
                Write-Host "  $latestProgress" -ForegroundColor White
            } else {
                Write-Host "  (no progress line written by agent)" -ForegroundColor DarkGray
            }
        }

        # Safety commit — if the agent didn't commit, do it now
        Push-Location $WorkRepo
        $dirty = git status --porcelain "notes/documents/$Topic.md" ".bookkeeping/$Topic.ralph/PLAN.md" ".bookkeeping/$Topic.ralph/progress.log" 2>$null
        if ($dirty) {
            git add "notes/documents/$Topic.md" ".bookkeeping/$Topic.ralph/PLAN.md" ".bookkeeping/$Topic.ralph/progress.log" 2>$null
            git commit -m "docs/${Topic}: auto-commit after iteration $i" --quiet 2>$null
            git push --quiet 2>$null
            Write-Host "  📤 Auto-committed iteration $i" -ForegroundColor DarkGray
        }
        Pop-Location

        # Check completion
        if (Test-Path $PlanFile) {
            $planContent = Get-Content -Path $PlanFile -Raw
            if ($planContent -match [regex]::Escape($PlanSentinel)) {
                Write-Host "`n✅ Document complete. Stopping." -ForegroundColor Green
                Add-Content -Path $LogFile -Value "`n✅ Completed at iteration $i"
                Save-LoopNote "✅ Completed ($i iterations)"
                exit 0
            }

            $done = ([regex]::Matches($planContent, '- \[x\]')).Count
            $remaining = ([regex]::Matches($planContent, '- \[ \]')).Count
            Write-Host "  📊 Topics: $done done, $remaining remaining" -ForegroundColor DarkCyan
        }

        # Show document size
        if (Test-Path $DocFile) {
            $docSize = (Get-Item $DocFile).Length
            $docLines = (Get-Content $DocFile).Count
            $docKB = [math]::Round($docSize / 1024, 1)
            Write-Host "  📄 Document: $docLines lines, ${docKB}KB" -ForegroundColor DarkCyan
        }
    }

    Write-Host "`n❌ Max iterations ($MaxIters) reached without completion." -ForegroundColor Red
    Add-Content -Path $LogFile -Value "`n❌ Max iterations reached"
    Save-LoopNote "❌ Max iterations ($MaxIters) reached"
    exit 1
} finally {
    Pop-Location
    Remove-Item Env:\COPILOT_CUSTOM_INSTRUCTIONS_DIRS -ErrorAction SilentlyContinue
}
```

**Bash (`loop.sh`):**

```bash
#!/usr/bin/env bash
# Doc Loop: <topic>
# Generated by doc-loop skill
# Usage: .bookkeeping/<topic>.ralph/loop.sh

set -euo pipefail

MAX_ITERS="${1:-<max_iters>}"
CLI="${2:-<cli>}"

RALPH_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK_REPO="$(cd "$RALPH_DIR/../.." && pwd)"
TOPIC="$(basename "$RALPH_DIR" .ralph)"
PLAN_FILE="$RALPH_DIR/PLAN.md"
PROMPT_FILE="$RALPH_DIR/PROMPT.md"
LOG_FILE="$RALPH_DIR/ralph.log"
PROGRESS_FILE="$RALPH_DIR/progress.log"
DOC_FILE="$WORK_REPO/notes/documents/$TOPIC.md"
PLAN_SENTINEL="STATUS: COMPLETE"

save_note() {
    local outcome="$1"
    local date_slug
    date_slug=$(date "+%Y_%m_%d")
    local notes_dir="$WORK_REPO/notes/doc-loops"
    mkdir -p "$notes_dir"
    local note_file="$notes_dir/${date_slug}_${TOPIC}.md"

    {
        echo "# Doc Loop: $TOPIC"
        echo ""
        echo "**Document:** notes/documents/$TOPIC.md  "
        echo "**Outcome:** $outcome  "
        echo "**Date:** $(date '+%Y-%m-%d %H:%M')"
        echo ""

        if [ -f "$PROGRESS_FILE" ]; then
            echo "## Iteration Log"
            echo ""
            while IFS= read -r line; do
                echo "- $line"
            done < "$PROGRESS_FILE"
            echo ""
        fi

        if [ -f "$PLAN_FILE" ]; then
            echo "## Final Plan State"
            echo ""
            sed -n '/^## Tasks/,/^## /{ /^## Tasks/d; /^## [^T]/d; p; }' "$PLAN_FILE"
            echo ""
        fi
    } > "$note_file"

    echo "📝 Note saved: $note_file"

    cd "$WORK_REPO" || return
    git add "notes/doc-loops" 2>/dev/null
    git commit -m "notes/doc-loops: ${TOPIC}" --quiet 2>/dev/null
    git push --quiet 2>/dev/null && echo "📤 Pushed to work repo." || echo "⚠️ Could not push note."
    cd "$WORK_REPO"
}

cd "$WORK_REPO"
export COPILOT_CUSTOM_INSTRUCTIONS_DIRS="$RALPH_DIR"

cleanup() {
    unset COPILOT_CUSTOM_INSTRUCTIONS_DIRS
}
trap cleanup EXIT

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Doc Loop: $TOPIC"
echo "║  CLI: $CLI | Max: $MAX_ITERS iters"
echo "║  Doc: $DOC_FILE"
echo "║  Pause: create pause.txt in .ralph/ dir to pause"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

for i in $(seq 1 "$MAX_ITERS"); do
    PAUSE_FILE="$RALPH_DIR/pause.txt"
    if [ -f "$PAUSE_FILE" ]; then
        echo -e "  \033[35m⏸️  Paused — remove $PAUSE_FILE to resume...\033[0m"
        echo "⏸️ Paused at $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
        while [ -f "$PAUSE_FILE" ]; do
            sleep 5
        done
        echo -e "  \033[32m▶️  Resumed.\033[0m"
        echo "▶️ Resumed at $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
    fi

    TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
    echo -e "\n\033[33m=== Doc Loop iteration $i/$MAX_ITERS — $TIMESTAMP ===\033[0m"
    echo "=== Doc Loop iteration $i/$MAX_ITERS — $TIMESTAMP ===" >> "$LOG_FILE"

    PROGRESS_BEFORE=0
    if [ -f "$PROGRESS_FILE" ]; then
        PROGRESS_BEFORE=$(wc -l < "$PROGRESS_FILE")
    fi

    PROMPT=$(cat "$PROMPT_FILE")

    echo "  ⏳ Running $CLI..."
    case "$CLI" in
        copilot)
            copilot -p "$PROMPT" --yolo --model claude-opus-4.6 >> "$LOG_FILE" 2>&1
            ;;
        claude)
            claude -p "$PROMPT" --dangerously-skip-permissions >> "$LOG_FILE" 2>&1
            ;;
        *)
            $CLI "$PROMPT" >> "$LOG_FILE" 2>&1
            ;;
    esac

    # Show the progress line the agent wrote (if any)
    if [ -f "$PROGRESS_FILE" ]; then
        PROGRESS_AFTER=$(wc -l < "$PROGRESS_FILE")
        if [ "$PROGRESS_AFTER" -gt "$PROGRESS_BEFORE" ]; then
            echo "  $(tail -1 "$PROGRESS_FILE")"
        else
            echo "  (no progress line written by agent)"
        fi
    fi

    # Safety commit — if the agent didn't commit, do it now
    cd "$WORK_REPO"
    if git status --porcelain "notes/documents/$TOPIC.md" ".bookkeeping/$TOPIC.ralph/PLAN.md" ".bookkeeping/$TOPIC.ralph/progress.log" 2>/dev/null | grep -q .; then
        git add "notes/documents/$TOPIC.md" ".bookkeeping/$TOPIC.ralph/PLAN.md" ".bookkeeping/$TOPIC.ralph/progress.log" 2>/dev/null
        git commit -m "docs/${TOPIC}: auto-commit after iteration $i" --quiet 2>/dev/null
        git push --quiet 2>/dev/null
        echo "  📤 Auto-committed iteration $i"
    fi

    # Check completion
    if [ -f "$PLAN_FILE" ]; then
        if grep -Fq "$PLAN_SENTINEL" "$PLAN_FILE"; then
            echo -e "\n\033[32m✅ Document complete. Stopping.\033[0m"
            echo "✅ Completed at iteration $i" >> "$LOG_FILE"
            save_note "✅ Completed ($i iterations)"
            exit 0
        fi

        DONE=$(grep -c '^\- \[x\]' "$PLAN_FILE" 2>/dev/null || true)
        REMAINING=$(grep -c '^\- \[ \]' "$PLAN_FILE" 2>/dev/null || true)
        echo "  📊 Topics: $DONE done, $REMAINING remaining"
    fi

    # Show document size
    if [ -f "$DOC_FILE" ]; then
        DOC_LINES=$(wc -l < "$DOC_FILE")
        DOC_KB=$(du -k "$DOC_FILE" | cut -f1)
        echo "  📄 Document: $DOC_LINES lines, ${DOC_KB}KB"
    fi
done

echo -e "\n\033[31m❌ Max iterations ($MAX_ITERS) reached without completion.\033[0m"
echo "❌ Max iterations reached" >> "$LOG_FILE"
save_note "❌ Max iterations ($MAX_ITERS) reached"
exit 1
```

### Step 10: Report to User

Tell the user what was created and how to use it:

```
✅ Doc loop workspace created:

  .bookkeeping/<topic>.ralph/
    AGENTS.md          — document writing guidelines, repo SHAs, code block format
    PROMPT.md          — loaded each iteration
    PLAN.md            — topic list (STATUS: IN_PROGRESS)
    research/          — pre-fetched codebase and GitHub research
    loop.ps1           — PowerShell loop script
    loop.sh            — Bash loop script

  Output: notes/documents/<topic-name>.md

To start the loop:
  .\.bookkeeping\<topic>.ralph\loop.ps1

To monitor progress:
  Get-Content .\.bookkeeping\<topic>.ralph\progress.log -Tail 20

To see full output:
  Get-Content .\.bookkeeping\<topic>.ralph\ralph.log -Tail 50

To stop: Ctrl+C

To pause between iterations:
  echo "paused" > .\.bookkeeping\<topic>.ralph\pause.txt
  # ... review the document, make edits ...
  Remove-Item .\.bookkeeping\<topic>.ralph\pause.txt
```

## Resuming an Existing Loop

If a `.bookkeeping/<topic>.ralph/` workspace already exists when this skill is invoked:

1. **Do NOT overwrite** — treat it as a resume.
2. Read the current PLAN.md to assess progress.
3. Read `progress.log` for iteration history.
4. Read the current document to see what's been written.
5. Show a status briefing: topics done vs remaining, last progress lines, document size.
6. Ask the user what they want to do:
   - **Continue** — just re-run the loop script
   - **Add topics** — add new tasks to PLAN.md
   - **Regenerate script** — update CLI, max_iters, etc.
   - **Reset** — start over (confirm before deleting)

## Validation

- [ ] `.bookkeeping/<topic>.ralph/` directory created with all files
- [ ] AGENTS.md contains pinned commit SHAs for all repos
- [ ] AGENTS.md has code block formatting guidelines with GitHub link template
- [ ] PROMPT.md references plan and research correctly
- [ ] PLAN.md has initial topic list with final review as last task
- [ ] Research files contain codebase and GitHub research summaries
- [ ] Loop scripts use work repo root as CWD
- [ ] Loop scripts commit document after each iteration (safety net)
- [ ] `notes/documents/` directory exists
- [ ] `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` is set in loop scripts

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Shallow sections with no code | AGENTS.md strongly emphasizes real code blocks — check early iterations |
| GitHub links use wrong SHA | Verify SHAs were pinned at setup and AGENTS.md template is correct |
| Agent doesn't discover new topics | AGENTS.md warns this is a sign of shallow exploration |
| Document gets incoherent across iterations | Final review task catches this; consider adding mid-document review tasks for very large docs |
| Agent forgets to commit | Loop script has safety commit after each iteration |
| AGENTS.md not loaded | Verify `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` points to the `.ralph/` directory |
| Loop runs in wrong CWD | Scripts use work repo root, not a single repo checkout |
| Overwriting existing workspace | Always check for existing `.ralph/` and offer resume |
