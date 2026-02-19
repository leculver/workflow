---
name: dev-loop
description: >
  Sets up an autonomous AI coding loop for feature implementation. Creates a `.bookkeeping/<feature>.ralph/`
  workspace with prompt, plan, specs, AGENTS.md, and a loop script (PowerShell + Bash) that repeatedly
  invokes an AI CLI until tests pass or the plan is complete. Use when the user says "start a loop",
  "ralph loop", "loop on this", "dev loop", or wants to autonomously build a feature in a repo.
---

# Dev Loop

Set up a ralph-style autonomous coding loop for implementing a feature in a repo.

## Overview

This skill **sets up** a loop — it doesn't run it. It creates:
- A `.bookkeeping/<feature>.ralph/` workspace with all context files
- A loop script the user runs separately to drive iterations

Each iteration of the loop:
1. Loads the prompt and AGENTS.md into the AI CLI
2. The agent reads the plan, picks a task, implements, tests, commits
3. The script checks completion conditions
4. If not done, the next iteration starts

## When to Use

- User wants to implement a feature autonomously via an AI loop
- User says "start a loop", "ralph loop", "dev loop", "loop on this"
- User wants to set up iterative AI-driven development on a project

## When Not to Use

- Triaging or investigating a GitHub issue (use `diagnose-and-fix`)
- One-off coding tasks that don't need iteration
- Saving notes (use `save-ad-hoc`)

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| goal | Yes | What outcome is needed (the JTBD). |
| repo | Infer | Target repository directory name (e.g., `keystone`, `clrmd`). Infer from conversation context. |
| feature | No | Short kebab-case name for the feature. Auto-generated from goal if omitted. |
| cli | No | AI CLI to use: `copilot` (default), `claude`, `codex`, `opencode`, `goose`. |
| mode | No | `PLANNING`, `BUILDING`, or `BOTH` (default). |
| test_cmd | No | Backpressure command (e.g., `dotnet test`, `npm test`). Infer from repo if possible. |
| max_iters | No | Maximum loop iterations. Default: 100. |

## Workflow

### Step 0: Bookkeeping

Invoke `bookkeeping` to pull the triage repo and flush any pending `.bookkeeping/` logs.

### Step 1: Collect Inputs

Gather the inputs listed above. For anything not provided:

1. **goal** — ask the user, this is required.
2. **repo** — infer from conversation (what repo has the user been working in?). If ambiguous, ask.
3. **feature** — derive from goal as kebab-case slug (2-5 words). Confirm with user.
4. **cli** — default to `copilot`. Only ask if the user mentioned a different CLI.
5. **mode** — default to `BOTH`. Only ask if the user has a preference.
6. **test_cmd** — infer from the repo:
   - C# / .NET → `dotnet test`
   - Node.js → `npm test`
   - Go → `go test ./...`
   - Python → `pytest`
   - If unsure, ask.
7. **max_iters** — default to 100.

### Step 2: Create the Workspace

Create the directory structure:

```
<repo>/.bookkeeping/<feature>.ralph/
  AGENTS.md
  PROMPT.md
  PLAN.md
  progress.log
  specs/
```

If `.bookkeeping/` doesn't exist in the target repo, create it. It should already be gitignored
(our repos have `**/.bookkeeping/` or `.bookkeeping/` in `.gitignore`). Verify and add if missing.

### Step 3: Generate Specs

Break the goal into topics of concern. Each topic becomes a spec file in `specs/`.

- Keep specs short (a few paragraphs each) and testable.
- 1 topic = 1 file, named `<topic>.md`.
- If the goal is simple enough for a single spec, that's fine — don't over-engineer.
- Read relevant source code in the target repo to understand existing structure before writing specs.

Example:
```
specs/
  data-model.md
  ui-layout.md
  persistence.md
```

### Step 4: Generate PLAN.md

Create the initial implementation plan:

```markdown
# Implementation Plan: <feature>

## Goal
<goal description>

## Status
STATUS: IN_PROGRESS

## Tasks
- [ ] Task 1 description
- [ ] Task 2 description
- [ ] Task 3 description
...

## Notes
<any relevant context, constraints, or decisions>
```

For `PLANNING` mode, leave tasks empty — the first iteration will generate them.
For `BUILDING` or `BOTH` mode, populate initial tasks from the specs.

### Step 5: Generate AGENTS.md

Write an `AGENTS.md` in the `.ralph/` directory. This file is loaded automatically by copilot
via the `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` environment variable (set by the loop script).

Contents should include:

```markdown
# Dev Loop — <feature>

## Project
<brief description of the repo and what it does>

## Build & Test (Backpressure)
Run these commands to validate changes:
```
<build_cmd>
<test_cmd>
```

Always run the backpressure commands after making changes. If tests fail, fix them before
moving to the next task.

## Progress Tracking
After completing your work this iteration, append exactly ONE line to
.bookkeeping/<feature>.ralph/progress.log in this format:

    YYYY-MM-DD HH:MM — ✅ — implemented X and tests pass
    YYYY-MM-DD HH:MM — ❌ — attempted X but tests fail: <reason>
    YYYY-MM-DD HH:MM — 🔄 — partial progress on X, continuing next iteration

Use ✅ when the task is done and tests pass, ❌ when something failed, 🔄 when
work is in progress but not complete. Keep descriptions short (one sentence max).
Do NOT skip this step. Do NOT write more than one line per iteration.

## Operational Notes
- <any relevant project conventions, gotchas, or patterns>
- Update this section if you discover new operational details during implementation.
```

If the repo already has an `AGENTS.md` or `CLAUDE.md` in its root, read it first and avoid
duplicating information. Reference it in the generated AGENTS.md if useful.

### Step 6: Generate PROMPT.md

Write `PROMPT.md` — this is the prompt loaded each iteration. Create TWO variants and
write the appropriate one based on mode.

**For PLANNING mode** (or first phase of BOTH):

```markdown
You are running a dev loop (PLANNING phase) for: <goal>

Read the codebase and the specs in .bookkeeping/<feature>.ralph/specs/.

Your job:
1. Analyze the codebase to understand existing structure.
2. Read each spec file for requirements.
3. Update .bookkeeping/<feature>.ralph/PLAN.md with a prioritized task list.
4. Do NOT implement anything. Do NOT commit code.
5. If requirements are unclear, write clarifying questions into PLAN.md.
6. Append one progress line to .bookkeeping/<feature>.ralph/progress.log (see AGENTS.md for format).

When the plan is complete and ready for implementation, change the Status line to:
STATUS: PLAN_COMPLETE
```

**For BUILDING mode** (or second phase of BOTH):

```markdown
You are running a dev loop (BUILDING phase) for: <goal>

Context:
- Specs: .bookkeeping/<feature>.ralph/specs/
- Plan: .bookkeeping/<feature>.ralph/PLAN.md

IMPORTANT: Complete exactly ONE task per iteration, then STOP. The loop script will
invoke you again for the next task. This ensures each task gets its own commit,
its own backpressure check, and the operator can monitor progress between iterations.

Your job this iteration:
1. Read PLAN.md and pick ONE incomplete task. Tasks are listed in suggested order but you may reorder based on dependencies, complexity, or what makes sense given the current state of the code.
2. Investigate relevant code — do NOT assume files are missing without checking.
3. Implement that ONE task.
4. Run the backpressure commands (build + test) from AGENTS.md.
5. If tests fail, fix them before stopping.
6. Mark the task as done in PLAN.md: `- [x] Task description`
7. Add any operational learnings to the Notes section of PLAN.md.
8. Commit with a clear message describing what was implemented.
9. Append one progress line to .bookkeeping/<feature>.ralph/progress.log (see AGENTS.md for format).
10. STOP. Do not continue to the next task.

When ALL tasks are done and tests pass, change the Status line in PLAN.md to:
STATUS: COMPLETE
```

For `BOTH` mode, write the BUILDING prompt. The loop script handles the mode transition
(see Step 7).

### Step 7: Generate Loop Scripts

Generate **both** `loop.ps1` and `loop.sh` in the `.ralph/` directory.

**PowerShell (`loop.ps1`):**

```powershell
#!/usr/bin/env pwsh
# Dev Loop: <feature>
# Generated by dev-loop skill
# Usage: .\.bookkeeping\<feature>.ralph\loop.ps1

param(
    [ValidateSet("planning", "building")]
    [string]$Mode = "<default_mode>",
    [int]$MaxIters = <max_iters>,
    [string]$Cli = "<cli>"
)

$ErrorActionPreference = "Stop"
$RalphDir = $PSScriptRoot
$RepoRoot = Resolve-Path (Join-Path $RalphDir "..\..")
$RepoName = Split-Path $RepoRoot -Leaf
$Feature = (Split-Path $RalphDir -Leaf) -replace '\.ralph$', ''
$PlanFile = Join-Path $RalphDir "PLAN.md"
$PromptFile = Join-Path $RalphDir "PROMPT.md"
$LogFile = Join-Path $RalphDir "ralph.log"
$ProgressFile = Join-Path $RalphDir "progress.log"
$TestCmd = "<test_cmd>"
$PlanSentinel = "STATUS: COMPLETE"
$PlanReadySentinel = "STATUS: PLAN_COMPLETE"
$WorkRepo = "<work_repo_root>"

function Save-LoopNote {
    param([string]$Outcome)
    $date = Get-Date -Format "yyyy_MM_dd"
    $notesDir = Join-Path $WorkRepo "notes" $RepoName
    if (-not (Test-Path $notesDir)) { New-Item -ItemType Directory -Path $notesDir -Force | Out-Null }
    $noteFile = Join-Path $notesDir "${date}_${Feature}.md"

    $sb = [System.Text.StringBuilder]::new()
    [void]$sb.AppendLine("# Dev Loop: $Feature")
    [void]$sb.AppendLine("")
    [void]$sb.AppendLine("**Repo:** $RepoName  ")
    [void]$sb.AppendLine("**Outcome:** $Outcome  ")
    [void]$sb.AppendLine("**Date:** $(Get-Date -Format 'yyyy-MM-dd HH:mm')")
    [void]$sb.AppendLine("")

    # Progress log
    if (Test-Path $ProgressFile) {
        [void]$sb.AppendLine("## Iteration Log")
        [void]$sb.AppendLine("")
        foreach ($line in Get-Content $ProgressFile) {
            [void]$sb.AppendLine("- $line")
        }
        [void]$sb.AppendLine("")
    }

    # Plan summary
    if (Test-Path $PlanFile) {
        [void]$sb.AppendLine("## Final Plan State")
        [void]$sb.AppendLine("")
        $planContent = Get-Content $PlanFile -Raw
        # Extract tasks section
        if ($planContent -match '(?s)## Tasks(.+?)(?=\n## |\z)') {
            [void]$sb.AppendLine($Matches[1].Trim())
        }
        [void]$sb.AppendLine("")
    }

    Set-Content -Path $noteFile -Value $sb.ToString().TrimEnd()
    Write-Host "📝 Note saved: $noteFile"

    # Commit and push from work repo
    Push-Location $WorkRepo
    try {
        git add "notes/$RepoName" 2>$null
        git commit -m "notes/${RepoName}: ${Feature}" --quiet 2>$null
        git push --quiet 2>$null
        Write-Host "📤 Pushed to work repo."
    } catch {
        Write-Host "⚠️ Could not commit/push note. Save it manually."
    }
    Pop-Location
}

Push-Location $RepoRoot
$env:COPILOT_CUSTOM_INSTRUCTIONS_DIRS = $RalphDir

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Dev Loop: $Feature" -ForegroundColor Cyan
Write-Host "║  Repo: $RepoName | CLI: $Cli | Max: $MaxIters iters" -ForegroundColor Cyan
Write-Host "║  Mode: $Mode" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

try {
    for ($i = 1; $i -le $MaxIters; $i++) {
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $header = "`n=== Dev Loop iteration $i/$MaxIters ($Mode) — $timestamp ==="
        Write-Host $header -ForegroundColor Yellow
        Add-Content -Path $LogFile -Value $header

        # Snapshot progress.log line count before this iteration
        $progressBefore = 0
        if (Test-Path $ProgressFile) {
            $progressBefore = (Get-Content $ProgressFile).Count
        }

        # Read prompt
        $prompt = Get-Content -Path $PromptFile -Raw

        # Run the CLI (output goes to log file only — keep console clean)
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

        # Check completion
        if (Test-Path $PlanFile) {
            $planContent = Get-Content -Path $PlanFile -Raw
            if ($planContent -match [regex]::Escape($PlanSentinel)) {
                Write-Host "`n✅ Plan marked COMPLETE. Stopping." -ForegroundColor Green
                Add-Content -Path $LogFile -Value "`n✅ Completed at iteration $i"
                Save-LoopNote "✅ Completed ($i iterations)"
                exit 0
            }
            # In BOTH mode: transition from planning to building
            if ($Mode -eq "planning" -and $planContent -match [regex]::Escape($PlanReadySentinel)) {
                Write-Host "  📋 Plan ready. Switching to BUILDING mode." -ForegroundColor Cyan
                Add-Content -Path $LogFile -Value "`n📋 Switching to building at iteration $i"
                $Mode = "building"
                $buildingPrompt = Join-Path $RalphDir "PROMPT.building.md"
                if (Test-Path $buildingPrompt) {
                    Copy-Item $buildingPrompt $PromptFile -Force
                }
                (Get-Content $PlanFile -Raw) -replace 'STATUS: PLAN_COMPLETE', 'STATUS: IN_PROGRESS' |
                    Set-Content $PlanFile
            }

            # Show plan task counts
            $done = ([regex]::Matches($planContent, '- \[x\]')).Count
            $remaining = ([regex]::Matches($planContent, '- \[ \]')).Count
            Write-Host "  📊 Tasks: $done done, $remaining remaining" -ForegroundColor DarkCyan
        }

        # Run backpressure (tests)
        if ($TestCmd -and $Mode -eq "building") {
            Write-Host "  🧪 Running tests: $TestCmd" -ForegroundColor DarkGray
            Add-Content -Path $LogFile -Value "`nBackpressure: $TestCmd"
            try {
                Invoke-Expression $TestCmd 2>&1 | Out-File -Append -FilePath $LogFile
                Add-Content -Path $LogFile -Value "Backpressure: PASSED"
                Write-Host "  🧪 Tests: PASSED" -ForegroundColor Green
            } catch {
                Add-Content -Path $LogFile -Value "Backpressure: FAILED — $($_.Exception.Message)"
                Write-Host "  🧪 Tests: FAILED" -ForegroundColor Red
            }
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
# Dev Loop: <feature>
# Generated by dev-loop skill
# Usage: .bookkeeping/<feature>.ralph/loop.sh

set -euo pipefail

MODE="${1:-<default_mode>}"
MAX_ITERS="${2:-<max_iters>}"
CLI="${3:-<cli>}"

RALPH_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$RALPH_DIR/../.." && pwd)"
REPO_NAME="$(basename "$REPO_ROOT")"
FEATURE="$(basename "$RALPH_DIR" .ralph)"
PLAN_FILE="$RALPH_DIR/PLAN.md"
PROMPT_FILE="$RALPH_DIR/PROMPT.md"
LOG_FILE="$RALPH_DIR/ralph.log"
PROGRESS_FILE="$RALPH_DIR/progress.log"
TEST_CMD="<test_cmd>"
PLAN_SENTINEL="STATUS: COMPLETE"
PLAN_READY_SENTINEL="STATUS: PLAN_COMPLETE"
WORK_REPO="<work_repo_root>"

save_note() {
    local outcome="$1"
    local date_slug
    date_slug=$(date "+%Y_%m_%d")
    local notes_dir="$WORK_REPO/notes/$REPO_NAME"
    mkdir -p "$notes_dir"
    local note_file="$notes_dir/${date_slug}_${FEATURE}.md"

    {
        echo "# Dev Loop: $FEATURE"
        echo ""
        echo "**Repo:** $REPO_NAME  "
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

    # Commit and push from work repo
    cd "$WORK_REPO" || return
    git add "notes/$REPO_NAME" 2>/dev/null
    git commit -m "notes/${REPO_NAME}: ${FEATURE}" --quiet 2>/dev/null
    git push --quiet 2>/dev/null && echo "📤 Pushed to work repo." || echo "⚠️ Could not push note."
    cd "$REPO_ROOT"
}

cd "$REPO_ROOT"
export COPILOT_CUSTOM_INSTRUCTIONS_DIRS="$RALPH_DIR"

cleanup() {
    unset COPILOT_CUSTOM_INSTRUCTIONS_DIRS
}
trap cleanup EXIT

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Dev Loop: $FEATURE"
echo "║  Repo: $REPO_NAME | CLI: $CLI | Max: $MAX_ITERS iters"
echo "║  Mode: $MODE"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

for i in $(seq 1 "$MAX_ITERS"); do
    TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
    echo -e "\n\033[33m=== Dev Loop iteration $i/$MAX_ITERS ($MODE) — $TIMESTAMP ===\033[0m"
    echo "=== Dev Loop iteration $i/$MAX_ITERS ($MODE) — $TIMESTAMP ===" >> "$LOG_FILE"

    # Snapshot progress.log line count before this iteration
    PROGRESS_BEFORE=0
    if [ -f "$PROGRESS_FILE" ]; then
        PROGRESS_BEFORE=$(wc -l < "$PROGRESS_FILE")
    fi

    PROMPT=$(cat "$PROMPT_FILE")

    # Run the CLI (output goes to log file only — keep console clean)
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

    # Check completion
    if [ -f "$PLAN_FILE" ]; then
        if grep -Fq "$PLAN_SENTINEL" "$PLAN_FILE"; then
            echo -e "\n\033[32m✅ Plan marked COMPLETE. Stopping.\033[0m"
            echo "✅ Completed at iteration $i" >> "$LOG_FILE"
            save_note "✅ Completed ($i iterations)"
            exit 0
        fi
        # In BOTH mode: transition from planning to building
        if [ "$MODE" = "planning" ] && grep -Fq "$PLAN_READY_SENTINEL" "$PLAN_FILE"; then
            echo "  📋 Plan ready. Switching to BUILDING mode."
            echo "📋 Switching to building at iteration $i" >> "$LOG_FILE"
            MODE="building"
            if [ -f "$RALPH_DIR/PROMPT.building.md" ]; then
                cp "$RALPH_DIR/PROMPT.building.md" "$PROMPT_FILE"
            fi
            sed -i 's/STATUS: PLAN_COMPLETE/STATUS: IN_PROGRESS/' "$PLAN_FILE"
        fi

        # Show plan task counts
        DONE=$(grep -c '^\- \[x\]' "$PLAN_FILE" 2>/dev/null || true)
        REMAINING=$(grep -c '^\- \[ \]' "$PLAN_FILE" 2>/dev/null || true)
        echo "  📊 Tasks: $DONE done, $REMAINING remaining"
    fi

    # Run backpressure (tests)
    if [ -n "$TEST_CMD" ] && [ "$MODE" = "building" ]; then
        echo "  🧪 Running tests: $TEST_CMD"
        echo "Backpressure: $TEST_CMD" >> "$LOG_FILE"
        if bash -lc "$TEST_CMD" >> "$LOG_FILE" 2>&1; then
            echo "Backpressure: PASSED" >> "$LOG_FILE"
            echo -e "  🧪 Tests: \033[32mPASSED\033[0m"
        else
            echo "Backpressure: FAILED" >> "$LOG_FILE"
            echo -e "  🧪 Tests: \033[31mFAILED\033[0m"
        fi
    fi
done

echo -e "\n\033[31m❌ Max iterations ($MAX_ITERS) reached without completion.\033[0m"
echo "❌ Max iterations reached" >> "$LOG_FILE"
save_note "❌ Max iterations ($MAX_ITERS) reached"
exit 1
```

### Step 8: Handle BOTH Mode

When mode is `BOTH`:

1. Write the **planning** prompt as `PROMPT.md` and the **building** prompt as `PROMPT.building.md`.
2. Set the default mode to `planning` in the loop scripts.
3. The loop script auto-transitions: when it detects `STATUS: PLAN_COMPLETE` in PLAN.md,
   it swaps `PROMPT.md` ← `PROMPT.building.md` and switches to building mode.

### Step 9: Report to User

Tell the user what was created and how to use it. Example output:

```
✅ Dev loop workspace created:

  keystone/.bookkeeping/workflow-viewer.ralph/
    AGENTS.md          — project context and backpressure commands
    PROMPT.md          — loaded each iteration (currently: planning)
    PROMPT.building.md — swapped in automatically after planning
    PLAN.md            — implementation plan (STATUS: IN_PROGRESS)
    specs/             — 3 spec files
    loop.ps1           — PowerShell loop script
    loop.sh            — Bash loop script

To start the loop:
  cd keystone
  .\.bookkeeping\workflow-viewer.ralph\loop.ps1

To start in building mode directly:
  .\.bookkeeping\workflow-viewer.ralph\loop.ps1 -Mode building

To monitor progress:
  Get-Content .\.bookkeeping\workflow-viewer.ralph\progress.log -Tail 20

To see full output:
  Get-Content .\.bookkeeping\workflow-viewer.ralph\ralph.log -Tail 50

To stop: Ctrl+C
```

## Saving Progress as a Note

When the loop completes (or the user asks to save progress), convert `progress.log` into a
markdown note using the `save-ad-hoc` skill conventions:

1. Read `progress.log` — each line is a timestamped summary of one iteration.
2. Read `PLAN.md` — shows final task status.
3. Write a note to `notes/<repo>/YYYY_MM_DD_<feature>.md` containing:
   - The goal
   - The progress log (formatted as a markdown list)
   - Final plan status (tasks completed vs remaining)
   - Any notable learnings from PLAN.md's Notes section
4. Commit and push the note.

This can happen automatically when the loop exits with `STATUS: COMPLETE`, or manually
when the user says "save" during a session that loaded the `.ralph/` workspace.

## Resuming an Existing Loop

If a `.bookkeeping/<feature>.ralph/` workspace already exists when this skill is invoked:

1. **Do NOT overwrite** — treat it as a resume.
2. Read the current PLAN.md to assess progress.
3. Read `progress.log` for iteration history.
4. Show a status briefing: how many tasks done vs remaining, last progress lines.
4. Ask the user what they want to do:
   - **Continue** — just re-run the loop script (no changes needed)
   - **Update specs** — modify specs, regenerate prompt
   - **Regenerate script** — update CLI, max_iters, test_cmd, etc.
   - **Reset** — start over (confirm before deleting)

## Validation

- [ ] `.bookkeeping/<feature>.ralph/` directory created with all files
- [ ] AGENTS.md contains build/test commands
- [ ] PROMPT.md references specs and plan correctly
- [ ] PLAN.md has initial task list (or is empty for planning-only)
- [ ] Loop scripts are executable and use correct paths
- [ ] `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` is set in loop scripts
- [ ] `.bookkeeping/` is gitignored in target repo
- [ ] AGENTS.md includes progress tracking instructions
- [ ] Mode transition (BOTH) works: planning → building

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| AGENTS.md not loaded | Verify `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` points to the `.ralph/` directory |
| Copilot can't see code | CWD must be repo root, not the `.ralph/` directory |
| Loop never completes | Check that the prompt instructs the agent to write `STATUS: COMPLETE` |
| No progress.log entries | Agent may have skipped the step — check AGENTS.md has the progress tracking section |
| Tests not running | Verify `test_cmd` is correct and runs from repo root |
| Overwriting existing workspace | Always check for existing `.ralph/` and offer resume |
| .bookkeeping/ committed to git | Verify `.gitignore` includes `.bookkeeping/` |
| PROMPT.md not swapped in BOTH mode | Ensure `PROMPT.building.md` exists alongside `PROMPT.md` |
| Loop script CWD wrong | Scripts use `$PSScriptRoot`/`dirname $0` to resolve paths relative to themselves |
